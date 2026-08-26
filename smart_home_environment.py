"""The physical RL environment: actions change switches, then energy is balanced."""

from appliance_model import ApplianceModel
from energy_system import EnergySystem
from state_action_model import StateActionModel


class SmartHomeEnvironment:
    """Runs one generated day. Solar and diesel charge the home battery."""

    def __init__(self, config):
        self.config = config
        self.appliances = ApplianceModel(config)
        self.energy_system = EnergySystem(config)
        self.state_actions = StateActionModel(config)

    def reset(self, scenario):
        """Start a new daily episode using one saved/generated scenario."""
        self.scenario = scenario
        self.period = 0
        self.home_battery_kwh = self.config["battery"]["initial_energy_kwh"]
        self.scooter_battery_kwh = 0.0
        self.device_status = {
            "generator": "off",
            "laundry": "not_started",
            "dishwasher": "not_started",
            "oven": "not_started",
            "ac_heater": "off",
            "scooter": "off",
        }
        self.oven_cycles_completed = 0
        self.total_reward = 0.0
        self.finished = False
        return self.state()

    def state(self):
        """Build the discrete state for the current period."""
        row = self.scenario[min(self.period, len(self.scenario) - 1)]
        return self.state_actions.build_state(
            current_day=row["day_number"],
            current_time_block=row["block"],
            battery_kwh=self.home_battery_kwh,
            generator_is_on=self.device_status["generator"] == "on",
            task_status={name: self.device_status[name] for name in ("laundry", "dishwasher", "oven")},
            next_period_solar_kwh=self._next_period_solar(),
            later_solar_until_sunset_kwh=self._later_solar_until_sunset(),
            mandatory_next_period_kwh=self._mandatory_next_period_demand(),
            future_demand_until_09_00_kwh=self._future_demand_until_morning(),
        )

    def valid_actions(self):
        row = self.scenario[self.period]
        return self.state_actions.valid_actions(
            row["time"], row["is_overnight"], self.device_status
        )

    def step(self, action):
        """Apply one valid action, run one energy period, then return RL values."""
        if self.finished:
            raise RuntimeError("This day is finished. Call reset before step.")
        if action not in self.valid_actions():
            raise ValueError(f"{action} is not valid in this period")

        state_before = self.state()
        row = self.scenario[self.period]
        self._apply_action(action)
        active = self._active_devices(row)
        demand_kwh = self._demand_kwh(row, active)

        # Solar charges the home battery first. Diesel charges it only when on.
        solar_kwh = row["actual_solar_kwh"]
        generator_kwh = self.energy_system.generator_energy_kwh(
            self.device_status["generator"] == "on",
            row["hours"],
            min(self.config["battery"]["capacity_kwh"], self.home_battery_kwh + solar_kwh),
        )
        result = self.energy_system.update_home_battery(
            self.home_battery_kwh, solar_kwh, generator_kwh, demand_kwh
        )
        self.home_battery_kwh = result["battery_after_kwh"]

        # If all loads have power, running tasks use one period of their remaining time.
        if not result["power_unavailable"]:
            self._advance_running_tasks()
            if active["scooter"]:
                scooter_energy = row["scooter_actual_kw"] * row["hours"]
                self.scooter_battery_kwh = self.energy_system.update_scooter_battery(
                    self.scooter_battery_kwh, scooter_energy
                )

        if self.scooter_battery_kwh >= self.config["appliances"]["scooter"]["battery_capacity_kwh"]:
            self.device_status["scooter"] = "off"

        # Stop the generator automatically when the home battery is full.
        if self.home_battery_kwh >= self.config["battery"]["capacity_kwh"]:
            self.device_status["generator"] = "off"

        reward = self._reward(row, active, generator_kwh, result["power_unavailable"])
        self.total_reward += reward
        self.period += 1
        self.finished = self.period == len(self.scenario)
        next_state = self.state()
        return next_state, reward, self.finished, {
            "action": action,
            "solar_kwh": solar_kwh,
            "generator_kwh": generator_kwh,
            "demand_kwh": demand_kwh,
            **result,
        }

    def _apply_action(self, action):
        if action == "do_nothing":
            return
        appliance, command = action.rsplit("_", 1)
        if appliance in ("laundry", "dishwasher", "oven"):
            status = self.device_status[appliance]
            if command == "off" and status.startswith("running_"):
                self.device_status[appliance] = status.replace("running_", "paused_")
            elif command == "on":
                if status == "not_started":
                    duration = self.config["appliances"][appliance]["duration_periods"]
                    self.device_status[appliance] = f"running_{duration}"
                elif status.startswith("paused_"):
                    self.device_status[appliance] = status.replace("paused_", "running_")
            return
        self.device_status[appliance] = "on" if command == "on" else "off"

    def _active_devices(self, row):
        return {
            "refrigerator": True,
            "tv_pc": not row["is_overnight"] and self.appliances.tv_pc_should_be_on(row["time"]),
            "laundry": self.device_status["laundry"].startswith("running_"),
            "dishwasher": self.device_status["dishwasher"].startswith("running_"),
            "oven": self.device_status["oven"].startswith("running_"),
            "ac_heater": self.device_status["ac_heater"] == "on" and not row["is_overnight"],
            "scooter": (
                self.device_status["scooter"] == "on"
                and self.scooter_battery_kwh < self.config["appliances"]["scooter"]["battery_capacity_kwh"]
                and self.appliances.scooter_can_charge(row["time"], row["is_overnight"])
            ),
        }

    def _demand_kwh(self, row, active):
        total = 0.0
        for appliance, is_active in active.items():
            if is_active:
                total += row[f"{appliance}_actual_kw"] * row["hours"]
        return total

    def _advance_running_tasks(self):
        for appliance in ("laundry", "dishwasher", "oven"):
            status = self.device_status[appliance]
            if not status.startswith("running_"):
                continue
            remaining = int(status.split("_")[1]) - 1
            if remaining > 0:
                self.device_status[appliance] = f"running_{remaining}"
            elif appliance == "oven" and self.oven_cycles_completed == 0:
                self.oven_cycles_completed = 1
                self.device_status[appliance] = "not_started"
            else:
                self.device_status[appliance] = "completed"

    def _next_period_solar(self):
        next_index = self.period + 1
        return 0.0 if next_index >= len(self.scenario) else self.scenario[next_index]["predicted_solar_kwh"]

    def _later_solar_until_sunset(self):
        # Sum after the next 30-minute period, stopping before the overnight block.
        return sum(row["predicted_solar_kwh"] for row in self.scenario[self.period + 2:] if not row["is_overnight"])

    def _mandatory_next_period_demand(self):
        next_index = self.period + 1
        if next_index >= len(self.scenario):
            return 0.0
        row = self.scenario[next_index]
        demand = row["refrigerator_actual_kw"] * row["hours"]
        if not row["is_overnight"] and self.appliances.tv_pc_should_be_on(row["time"]):
            demand += row["tv_pc_actual_kw"] * row["hours"]
        if not row["is_overnight"]:
            for appliance in ("laundry", "dishwasher", "oven"):
                if self.device_status[appliance].startswith("running_"):
                    demand += row[f"{appliance}_actual_kw"] * row["hours"]
        return demand

    def _future_demand_until_morning(self):
        # Use a comfort-aware forecast: include scheduled TV,
        # optional AC/heater through 23:00, fridge, remaining fixed tasks, and scooter need.
        demand = 0.0
        for row in self.scenario[self.period + 2:]:
            demand += row["refrigerator_actual_kw"] * row["hours"]
            if not row["is_overnight"]:
                demand += row["ac_heater_actual_kw"] * row["hours"]
                if self.appliances.tv_pc_should_be_on(row["time"]):
                    demand += row["tv_pc_actual_kw"] * row["hours"]
        for appliance in ("laundry", "dishwasher", "oven"):
            status = self.device_status[appliance]
            if status.startswith("running_") or status.startswith("paused_"):
                remaining = int(status.split("_")[1])
                demand += remaining * 0.5 * self.config["appliances"][appliance]["power_kw"]
        demand += max(0.0, self.config["appliances"]["scooter"]["battery_capacity_kwh"] - self.scooter_battery_kwh)
        return demand

    def _reward(self, row, active, generator_kwh, power_unavailable):
        values = self.config["reward_values"]
        reward = values["generator_cost_per_operating_hour"] * (
            generator_kwh / self.config["generator"]["power_kw"]
        )
        if active["ac_heater"] and not power_unavailable:
            reward += values["ac_heater_comfort_per_served_period"]
        if power_unavailable:
            reward += values["battery_depleted_and_appliances_stop"]
        if row["is_overnight"]:
            for appliance, reward_name in (("laundry", "missed_laundry_deadline"), ("dishwasher", "missed_dishwasher_deadline")):
                if self.device_status[appliance] != "completed":
                    reward += values[reward_name]
            if self.oven_cycles_completed < self.config["appliances"]["oven"]["required_cycles"]:
                reward += values["missed_oven_cycle"] * (self.config["appliances"]["oven"]["required_cycles"] - self.oven_cycles_completed)
            reward += values["scooter_shortfall_per_kwh"] * max(0.0, self.config["appliances"]["scooter"]["battery_capacity_kwh"] - self.scooter_battery_kwh)
        return reward
