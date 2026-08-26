"""Calculate solar energy using the configured monthly and time tables."""


class SolarModel:
    """Calculates predicted or varied solar energy for a time block."""

    def __init__(self, config):
        self.config = config

    def energy_kwh(self, clock_time, block_hours, solar_noise=0.0):
        month = self.config["experiment"]["month"]
        solar = self.config["solar"]

        # Example for June: this reads 210 watts per square metre.
        peak_w_per_m2 = solar["monthly_maximum"][month]["peak_w_per_m2"]

        # Read the strength of the sun at this exact time.
        time_multiplier = solar["time_multiplier"].get(clock_time, 0.0)

        # Watts/m2 x panel m2 = watts. Divide by 1000 to get kW.
        peak_panel_kw = peak_w_per_m2 * solar["panel_area_m2"] / 1000

        # Power x time = energy. Later, solar noise can be -20% to 0%.
        predicted_kwh = peak_panel_kw * time_multiplier * block_hours
        actual_kwh = predicted_kwh * solar["weather_coefficient"] * (1 + solar_noise)

        return max(0.0, actual_kwh)

    def overnight_energy_kwh(self, solar_noise=0.0):
        # The overnight block includes the following morning.
        # Add the supplied 04:30 to 08:30 half-hour values together.
        morning_times = [
            "04:30", "05:00", "05:30", "06:00", "06:30",
            "07:00", "07:30", "08:00", "08:30",
        ]

        total = 0.0
        for time in morning_times:
            total += self.energy_kwh(time, 0.5, solar_noise)

        return total
