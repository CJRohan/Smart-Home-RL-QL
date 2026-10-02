import itertools
from typing import NamedTuple


class CompositeAction(NamedTuple):
    """Joint dispatch decision for one 30-minute period."""
    generator: int
    ac_heater: int
    scooter: int
    start_laundry: int
    start_dishwasher: int
    start_oven: int


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
        'not_started', 'running_1', 'running_2', 'running_3', or 'completed'.
        Tasks are non-preemptible by choice; remaining time is preserved during outages.
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

    def valid_actions(
        self,
        clock_time,
        is_overnight,
        device_status,
        battery_kwh=0.0,
        scooter_battery_kwh=0.0,
        oven_cycles_completed=0,
    ):
        """Return all physically permitted composite action vectors for this period.

        Decisions are made simultaneously. Fixed-duration tasks are triggered once
        and run to completion without voluntary pausing.

        Every sub-actuator option list begins with 0, ensuring that the first item
        in the Cartesian product is always CompositeAction(0, 0, 0, 0, 0, 0).
        """
        battery_capacity = self.config["battery"]["capacity_kwh"]
        if is_overnight or battery_kwh >= battery_capacity:
            gen_options = [0]
        else:
            gen_options = [0, 1]

        ac_options = [0] if is_overnight else [0, 1]

        scooter_capacity = self.config["appliances"]["scooter"]["battery_capacity_kwh"]
        can_scooter = (
            (is_overnight or clock_time >= self.config["appliances"]["scooter"]["earliest_start"])
            and scooter_battery_kwh < scooter_capacity
        )
        scooter_options = [0, 1] if can_scooter else [0]

        laundry_options = [0, 1] if (not is_overnight and device_status["laundry"] == "not_started") else [0]

        can_start_dw = (
            not is_overnight
            and clock_time >= self.config["appliances"]["dishwasher"]["earliest_start"]
            and device_status["dishwasher"] == "not_started"
        )
        dw_options = [0, 1] if can_start_dw else [0]

        can_start_oven = (
            not is_overnight
            and clock_time in self.config["appliances"]["oven"]["allowed_start_times"]
            and device_status["oven"] == "not_started"
            and oven_cycles_completed < self.config["appliances"]["oven"]["required_cycles"]
        )
        oven_options = [0, 1] if can_start_oven else [0]

        actions = [
            CompositeAction(g, ac, sc, l, dw, ov)
            for g, ac, sc, l, dw, ov in itertools.product(
                gen_options,
                ac_options,
                scooter_options,
                laundry_options,
                dw_options,
                oven_options,
            )
        ]
        return actions
