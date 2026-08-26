"""Calculate appliance demand and check permitted operating times."""


class ApplianceModel:
    """Contains the simple appliance rules from config.json."""

    def __init__(self, config):
        self.config = config

    def energy_kwh(self, appliance_name, block_hours, is_on, noise=0.0):
        if not is_on:
            return 0.0

        power_kw = self.config["appliances"][appliance_name]["power_kw"]

        # Appliance energy = power x time x small variation.
        # Later, noise can be randomly selected from -15% to +15%.
        return power_kw * block_hours * (1 + noise)

    def time_is_inside(self, clock_time, start_time, end_time):
        return start_time <= clock_time < end_time

    def tv_pc_should_be_on(self, clock_time):
        # TV/PC follows the fixed windows written in config.json.
        windows = self.config["appliances"]["tv_pc"]["schedule"]

        for start, end in windows:
            if self.time_is_inside(clock_time, start, end):
                return True

        return False

    def scooter_can_charge(self, clock_time, is_overnight):
        scooter = self.config["appliances"]["scooter"]

        if is_overnight:
            return scooter["overnight_allowed"]

        return clock_time >= scooter["earliest_start"]
