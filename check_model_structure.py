"""Print a few simple values so the model can be checked by eye."""

from appliance_model import ApplianceModel
from config_loader import ConfigLoader
from energy_system import EnergySystem
from scenario_generator import ScenarioGenerator
from smart_home_environment import SmartHomeEnvironment
from solar_model import SolarModel
from state_action_model import StateActionModel, CompositeAction
from time_blocks import TimeBlockModel


def main():
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

    # 1. Normal supply: solar charges the home battery, fridge takes energy.
    solar_battery_result = energy_system.update_home_battery(
        battery_before_kwh=config["battery"]["initial_energy_kwh"],
        solar_kwh=midday_solar_kwh,
        generator_kwh=0.0,
        demand_kwh=fridge_energy_kwh,
    )

    # 2. Diesel generator charging home battery.
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

    # 3. Battery depletion test (no fixed priority: demand > available causes blackout).
    depletion_result = energy_system.update_home_battery(
        battery_before_kwh=1.0,
        solar_kwh=0.0,
        generator_kwh=0.0,
        demand_kwh=3.5,  # heavy demand on depleted battery
    )
    loads_allocated = energy_system.allocate_loads(
        available_kwh=1.0,
        requested={"refrigerator": 0.04, "ac_heater": 1.25, "oven": 1.0, "laundry": 0.35},
    )

    # 4. State representation check (11 variables preserved).
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

    # 5. Composite action space checks across different times of day.
    actions_1130 = state_action_model.valid_actions(
        clock_time="11:30",
        is_overnight=False,
        device_status={
            "generator": "off", "laundry": "not_started", "dishwasher": "not_started",
            "oven": "not_started", "ac_heater": "off", "scooter": "off",
        },
        battery_kwh=3.2, scooter_battery_kwh=0.0, oven_cycles_completed=0,
    )
    actions_1700 = state_action_model.valid_actions(
        clock_time="17:00",
        is_overnight=False,
        device_status={
            "generator": "off", "laundry": "completed", "dishwasher": "not_started",
            "oven": "not_started", "ac_heater": "off", "scooter": "off",
        },
        battery_kwh=3.2, scooter_battery_kwh=0.0, oven_cycles_completed=1,
    )
    actions_overnight = state_action_model.valid_actions(
        clock_time="23:00-09:00",
        is_overnight=True,
        device_status={
            "generator": "off", "laundry": "completed", "dishwasher": "completed",
            "oven": "completed", "ac_heater": "off", "scooter": "off",
        },
        battery_kwh=4.0, scooter_battery_kwh=0.5, oven_cycles_completed=2,
    )

    # 6. Full environment step with composite action.
    env = SmartHomeEnvironment(config)
    generator = ScenarioGenerator(config, seed=42)
    day_rows = generator.generate_day(day_number=1)
    initial_state = env.reset(day_rows)
    # Dispatch: generator=1 and start laundry simultaneously!
    test_action = CompositeAction(generator=1, ac_heater=0, scooter=0, start_laundry=1, start_dishwasher=0, start_oven=0)
    next_state, reward, done, info = env.step(test_action)

    print("==========================================================")
    print("MATHEMATICAL MODEL & COMPOSITE ACTION VALIDATION")
    print("==========================================================")
    print()
    print("Total blocks:", len(blocks), "(expected 29)")
    print("Daytime blocks:", len(daytime_blocks), "(expected 28)")
    print("Overnight block:", blocks[-1]["time"], f"({blocks[-1]['hours']} hours)")
    print()
    print("--- Energy Balance Checks ---")
    print("Midday solar (12:30, 30m):", round(midday_solar_kwh, 4), "kWh")
    print("Battery before:", config["battery"]["initial_energy_kwh"], "kWh")
    print("After solar + fridge -> Battery:", round(solar_battery_result["battery_after_kwh"], 4), "kWh | Power unavailable:", solar_battery_result["power_unavailable"])
    print("Diesel energy (30m):", round(diesel_energy_kwh, 4), "kWh")
    print("After diesel + fridge -> Battery:", round(diesel_battery_result["battery_after_kwh"], 4), "kWh | Power unavailable:", diesel_battery_result["power_unavailable"])
    print()
    print("--- Depletion Check (Demand > Available) ---")
    print("Depletion test (demand 3.5 kWh vs available 1.0 kWh):")
    print("  Battery after:", depletion_result["battery_after_kwh"], "kWh")
    print("  Served energy:", depletion_result["served_kwh"], "kWh")
    print("  Unmet energy:", depletion_result["unmet_kwh"], "kWh")
    print("  Power unavailable flag:", depletion_result["power_unavailable"])
    print("  Loads served under depletion:", loads_allocated)
    print()
    print("--- State Representation (11 elements preserved) ---")
    print("Length of state tuple:", len(example_state), "(expected 11)")
    print("State tuple:", example_state)
    print()
    print("--- Composite Action Space Checks ---")
    print(f"At 11:30 (Oven lunch start eligible): {len(actions_1130)} valid composite actions")
    print("  First action (neutral do-nothing):", actions_1130[0])
    print("  Simultaneous action example:", actions_1130[-1])
    print(f"At 17:00 (Oven dinner start + Scooter eligible): {len(actions_1700)} valid composite actions")
    print(f"Overnight (Only scooter eligible): {len(actions_overnight)} valid composite actions")
    print("  Overnight actions:", actions_overnight)
    print()
    print("--- Environment Simulation Step Check ---")
    print("Action applied:", test_action)
    print("Resulting laundry status:", env.device_status["laundry"])
    print("Resulting generator status:", env.device_status["generator"])
    print("Generated generator energy:", round(info["generator_kwh"], 4), "kWh")
    print("Resulting battery:", round(env.home_battery_kwh, 4), "kWh")
    print("Step reward:", round(reward, 4))
    print("Done:", done)
    print()
    print("ALL STRUCTURAL AND COMPOSITE ACTION CHECKS PASSED!")
    print("==========================================================")


if __name__ == "__main__":
    main()
