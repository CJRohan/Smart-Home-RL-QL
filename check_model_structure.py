"""Print a few simple values so the model can be checked by eye."""

from appliance_model import ApplianceModel
from config_loader import ConfigLoader
from energy_system import EnergySystem
from solar_model import SolarModel
from state_action_model import StateActionModel
from time_blocks import TimeBlockModel


def main():
    # Make one object from each small part of the mathematical model.
    config = ConfigLoader().load()
    time_model = TimeBlockModel(config)
    solar_model = SolarModel(config)
    appliance_model = ApplianceModel(config)
    energy_system = EnergySystem(config)
    state_action_model = StateActionModel(config)

    blocks = time_model.build()
    daytime_blocks = [block for block in blocks if not block["is_overnight"]]

    # Use midday as one easy example that can be checked by eye.
    midday_solar_kwh = solar_model.energy_kwh("12:30", 0.5)
    fridge_energy_kwh = appliance_model.energy_kwh("refrigerator", 0.5, True)

    # First example: solar charges the home battery.
    solar_battery_result = energy_system.update_home_battery(
        battery_before_kwh=config["battery"]["initial_energy_kwh"],
        solar_kwh=midday_solar_kwh,
        generator_kwh=0.0,
        demand_kwh=fridge_energy_kwh,
    )

    # Second example: diesel generator also charges the same home battery.
    diesel_energy_kwh = energy_system.generator_energy_kwh(
        generator_on=True,
        block_hours=0.5,
        battery_energy_kwh=config["battery"]["initial_energy_kwh"],
    )
    diesel_battery_result = energy_system.update_home_battery(
        battery_before_kwh=config["battery"]["initial_energy_kwh"],
        solar_kwh=0.0,
        generator_kwh=diesel_energy_kwh,
        demand_kwh=fridge_energy_kwh,
    )

    example_state = state_action_model.build_state(
        current_day=1,
        current_time_block=16,
        battery_kwh=3.2,
        generator_is_on=False,
        task_status={
            "laundry": "completed",
            "dishwasher": "not_started",
            "oven": "running_1",
        },
        next_period_solar_kwh=0.35,
        later_solar_until_sunset_kwh=2.8,
        mandatory_next_period_kwh=1.04,
        future_demand_until_09_00_kwh=3.3,
    )
    example_actions = state_action_model.valid_actions(
        clock_time="17:00",
        is_overnight=False,
        device_status={
            "generator": "off",
            "laundry": "completed",
            "dishwasher": "not_started",
            "oven": "running_1",
            "ac_heater": "off",
            "scooter": "off",
        },
    )

    print("MATHEMATICAL MODEL - VALUES TO CHECK BY EYE")
    print()
    print("Total blocks:", len(blocks), "(expected 29)")
    print("Daytime blocks:", len(daytime_blocks), "(expected 28)")
    print("Overnight block:", blocks[-1])
    print()
    print("June solar at 12:30 for 30 minutes:", round(midday_solar_kwh, 4), "kWh")
    print("Fridge energy for 30 minutes:", round(fridge_energy_kwh, 4), "kWh")
    print("Battery before:", config["battery"]["initial_energy_kwh"], "kWh")
    print("Battery after solar and fridge:", round(solar_battery_result["battery_after_kwh"], 4), "kWh")
    print("Diesel generator energy for 30 minutes:", round(diesel_energy_kwh, 4), "kWh")
    print("Battery after diesel and fridge:", round(diesel_battery_result["battery_after_kwh"], 4), "kWh")
    print("Unmet energy in solar example:", round(solar_battery_result["unmet_kwh"], 4), "kWh")
    print()
    print("Example state tuple:", example_state)
    print("Valid actions at 17:00 in that example:", example_actions)
    print()
    print("This is only a visible model check.")
    print("No scenarios were generated and no RL was trained.")


if __name__ == "__main__":
    main()
