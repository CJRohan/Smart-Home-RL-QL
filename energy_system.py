"""Model generator, home battery, appliance supply and scooter battery."""


class EnergySystem:
    """Moves solar and generator energy through the home battery."""

    def __init__(self, config):
        self.config = config

    def generator_energy_kwh(self, generator_on, block_hours, battery_energy_kwh):
        if not generator_on:
            return 0.0

        generator = self.config["generator"]
        battery_size = self.config["battery"]["capacity_kwh"]
        wanted_energy = generator["power_kw"] * block_hours

        # Generator must stop when the home battery becomes full.
        empty_space = max(0.0, battery_size - battery_energy_kwh)
        return min(wanted_energy, empty_space)

    def update_home_battery(
        self,
        battery_before_kwh,
        solar_kwh,
        generator_kwh,
        demand_kwh,
    ):
        battery_size = self.config["battery"]["capacity_kwh"]

        # First, solar and generator put energy into the home battery.
        energy_before_loads = battery_before_kwh + solar_kwh + generator_kwh

        # The battery cannot hold more than its maximum size.
        curtailed_kwh = max(0.0, energy_before_loads - battery_size)
        available_kwh = min(battery_size, energy_before_loads)

        # Second, appliances take energy from the home battery.
        # If total demand fits in available energy, all appliances are served.
        # If battery is depleted (demand > available), all appliances stop.
        if demand_kwh <= available_kwh:
            served_kwh = demand_kwh
            unmet_kwh = 0.0
            battery_after_kwh = available_kwh - demand_kwh
            power_unavailable = False
        else:
            served_kwh = 0.0
            unmet_kwh = demand_kwh
            battery_after_kwh = 0.0
            power_unavailable = True

        return {
            "battery_after_kwh": battery_after_kwh,
            "served_kwh": served_kwh,
            "unmet_kwh": unmet_kwh,
            "curtailed_kwh": curtailed_kwh,
            "power_unavailable": power_unavailable,
        }

    def update_scooter_battery(self, scooter_before_kwh, supplied_charging_kwh):
        scooter_size = self.config["appliances"]["scooter"]["battery_capacity_kwh"]

        # Scooter accepts energy until it is full. Then charging stops.
        empty_space = max(0.0, scooter_size - scooter_before_kwh)
        accepted_kwh = min(supplied_charging_kwh, empty_space)
        return scooter_before_kwh + accepted_kwh

    def allocate_loads(self, available_kwh, requested):
        """No fixed priority. Total demand is served if battery energy is sufficient.

        If battery is depleted (demand > available), all appliances stop.
        """
        total_demand = sum(requested.values())
        if total_demand <= available_kwh:
            return {name: val for name, val in requested.items()}
        return {name: 0.0 for name in requested}
