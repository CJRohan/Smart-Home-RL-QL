# Notation — the labels used in the model

The model uses time blocks: 28 half-hour blocks from 09:00 to 23:00 plus one combined overnight block from 23:00 to 09:00.

| Symbol | Caveman-English meaning | Unit |
|---|---|---|
| `t` | current time block | block number |
| `T` | all time blocks in the day | set of blocks |
| `Δt` | length of the current time block | hours |
| `B_t` | energy inside the home battery at start of block `t` | kWh |
| `B_max` | biggest amount the home battery can hold | kWh |
| `S_t` | solar energy produced in block `t` | kWh |
| `G_t` | generator energy sent to the battery in block `t` | kWh |
| `g_t` | generator switch: `1` means on, `0` means off | 0 or 1 |
| `P_g` | fixed generator power | kW |
| `E_{a,t}` | energy wanted by appliance `a` in block `t` | kWh |
| `x_{a,t}` | appliance decision: `1` means appliance `a` is running, `0` means not running | 0 or 1 |
| `P_a` | power of appliance `a` while it runs | kW |
| `r_{a,t}` | remaining run time of a fixed-duration task | hours |
| `D_t` | total appliance energy demand in block `t` | kWh |
| `U_t` | energy demand that cannot be supplied | kWh |
| `C_t` | solar/generator energy that cannot fit in a full battery | kWh |
| `z_t` | scooter energy stored at start of block `t` | kWh |
| `z_max` | scooter battery capacity | kWh |

Appliance label `a` can be one of: laundry, dishwasher, oven, refrigerator, TV/PC, AC/heater, scooter.
