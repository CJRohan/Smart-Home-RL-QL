"""Create reproducible random daily solar and appliance-demand scenarios."""

import csv
import random
from pathlib import Path

from appliance_model import ApplianceModel
from solar_model import SolarModel
from time_blocks import TimeBlockModel


class ScenarioGenerator:
    """Creates the input day that a future RL episode will use."""

    def __init__(self, config, seed=None):
        self.config = config
        self.random = random.Random(config["experiment"]["seed"] if seed is None else seed)
        self.time_model = TimeBlockModel(config)
        self.solar_model = SolarModel(config)
        self.appliance_model = ApplianceModel(config)

    def generate_day(self, day_number=1):
        """Make one day with solar and appliance variation from config.json."""
        rows = []
        for block in self.time_model.build():
            solar_noise = self.random.uniform(
                self.config["solar"]["actual_noise_low"],
                self.config["solar"]["actual_noise_high"],
            )
            if block["is_overnight"]:
                predicted_solar_kwh = self.solar_model.overnight_energy_kwh(0.0)
                actual_solar_kwh = self.solar_model.overnight_energy_kwh(solar_noise)
            else:
                predicted_solar_kwh = self.solar_model.energy_kwh(block["time"], block["hours"], 0.0)
                actual_solar_kwh = self.solar_model.energy_kwh(block["time"], block["hours"], solar_noise)

            row = {
                "day_number": day_number,
                **block,
                "predicted_solar_kwh": predicted_solar_kwh,
                "actual_solar_kwh": actual_solar_kwh,
            }
            for name, values in self.config["appliances"].items():
                noise = self.random.uniform(
                    self.config["appliance_noise"]["low"],
                    self.config["appliance_noise"]["high"],
                )
                row[f"{name}_actual_kw"] = values["power_kw"] * (1 + noise)
            rows.append(row)

        return rows

    def generate_days(self, number_of_days):
        """Make several independent days. This method does not train anything."""
        return [self.generate_day(day_number + 1) for day_number in range(number_of_days)]

    def save_csv(self, days, path):
        """Optionally save generated scenarios so another algorithm can reuse them."""
        rows = [row for day in days for row in day]
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return output
