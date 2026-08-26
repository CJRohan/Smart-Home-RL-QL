"""Build the Q-learning state and list valid actions for one period.

This module defines the design only. It does not generate scenarios or train Q-learning.
"""


class StateActionModel:
    """Turns physical information into a small, discrete RL state."""

    def __init__(self, config):
        self.config = config

    def bin_number(self, energy_kwh, upper_bounds):
        """Return 0 for the first bin, 1 for the second bin, and so on."""
        for number, upper_bound in enumerate(upper_bounds):
            if energy_kwh <= upper_bound:
                return number

        # The last configured bound is deliberately very large.
        return len(upper_bounds) - 1

    def build_state(
        self,
        current_day,
        current_time_block,
        battery_kwh,
        generator_is_on,
        task_status,
        next_period_solar_kwh,
        later_solar_until_sunset_kwh,
        mandatory_next_period_kwh,
        future_demand_until_09_00_kwh,
    ):
        """Create the discrete state used later as a Q-table key.

        task_status is a small dictionary. Each fixed task stores one of:
        'not_started', 'running_1', 'running_2', 'running_3',
        'paused_1', 'paused_2', 'paused_3', or 'completed'.
        A paused task keeps its remaining duration and can later be resumed.
        """
        state_definition = self.config["state_definition"]

        battery_bin = self.bin_number(
            battery_kwh,
            state_definition["battery_level_bin_upper_bounds_kwh"],
        )
        next_solar_bin = self.bin_number(
            next_period_solar_kwh,
            state_definition["next_period_solar_bin_upper_bounds_kwh"],
        )
        later_solar_bin = self.bin_number(
            later_solar_until_sunset_kwh,
            state_definition["remaining_day_solar_bin_upper_bounds_kwh"],
        )
        mandatory_demand_bin = self.bin_number(
            mandatory_next_period_kwh,
            state_definition["mandatory_energy_next_period_bin_upper_bounds_kwh"],
        )
        future_demand_bin = self.bin_number(
            future_demand_until_09_00_kwh,
            state_definition["future_energy_until_09_00_bin_upper_bounds_kwh"],
        )

        # A tuple is small and can later be used directly as a Q-table key.
        # Scooter battery is represented through future energy demand, not its own bin.
        return (
            current_day,
            current_time_block,
            battery_bin,
            int(generator_is_on),
            task_status["laundry"],
            task_status["dishwasher"],
            task_status["oven"],
            next_solar_bin,
            later_solar_bin,
            mandatory_demand_bin,
            future_demand_bin,
        )

    def valid_actions(self, clock_time, is_overnight, device_status):
        """Return only actions that make sense in this exact period.

        device_status stores 'on'/'off' for generator, AC/heater, and scooter.
        Fixed tasks store 'not_started', 'running_1', 'paused_1', etc., or 'completed'.
        An already-on device receives only an off action. A completed task receives no action.
        Refrigerator and TV/PC are automatic, so they are not part of the action list.
        """
        # The agent must also be able to make no switch change in this period.
        actions = ["do_nothing"]

        self._add_generator_actions(actions, is_overnight, device_status["generator"])
        self._add_fixed_task_actions(actions, "laundry", not is_overnight, device_status["laundry"])
        self._add_fixed_task_actions(
            actions,
            "dishwasher",
            clock_time >= self.config["appliances"]["dishwasher"]["earliest_start"] and not is_overnight,
            device_status["dishwasher"],
        )
        self._add_fixed_task_actions(
            actions,
            "oven",
            clock_time in self.config["appliances"]["oven"]["allowed_start_times"] and not is_overnight,
            device_status["oven"],
        )
        self._add_switch_actions(actions, "ac_heater", not is_overnight, device_status["ac_heater"])

        scooter_can_start = is_overnight or clock_time >= self.config["appliances"]["scooter"]["earliest_start"]
        self._add_switch_actions(actions, "scooter", scooter_can_start, device_status["scooter"])

        return actions

    def _add_generator_actions(self, actions, is_overnight, status):
        if status == "on":
            actions.append("generator_off")
        elif status == "off" and not is_overnight:
            actions.append("generator_on")

    def _add_fixed_task_actions(self, actions, appliance, can_start, status):
        if status == "on" or status.startswith("running_"):
            actions.append(f"{appliance}_off")
        elif (status == "not_started" or status.startswith("paused_")) and can_start:
            actions.append(f"{appliance}_on")

    def _add_switch_actions(self, actions, appliance, can_start, status):
        if status == "on":
            actions.append(f"{appliance}_off")
        elif status == "off" and can_start:
            actions.append(f"{appliance}_on")
