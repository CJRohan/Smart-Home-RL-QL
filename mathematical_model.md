# Mathematical model — first discussion version

This is a **model outline**, not yet a training environment. The equations show what must be represented before choosing an RL algorithm.

## 1. Time blocks

Split one day into blocks `t ∈ T`.

- Daytime: 09:00–23:00 in 30-minute blocks (`Δt = 0.5` hours).
- Overnight: one combined 23:00–09:00 block (`Δt = 10` hours).

The different overnight duration matters: a device running overnight uses energy for 10 hours, not 30 minutes.

## 2. Solar energy

For each time block:

`S_t = A × I_month × m_t × Δt × w_t`

Where:

- `A` is solar-panel area;
- `I_month` is the maximum solar output for the selected month;
- `m_t` is the supplied multiplier for time of day;
- `w_t` is weather/solar variation.

For the configured daily example: `A = 10 m²`, June maximum output is `210 W/m²`, and `w_t` may reduce solar by up to 20%. Solar is zero outside the solar-production timetable.

## 3. Appliance demand

For each appliance that is on:

`E_{a,t} = x_{a,t} × P_a × Δt × (1 + ε_{a,t})`

`ε_{a,t}` is the appliance variation, between `−0.15` and `+0.15` in the configured example.

The total demand is:

`D_t = Σ E_{a,t}`

The refrigerator is normally always on. TV/PC has availability windows. Laundry, dishwasher and oven are fixed-duration tasks. AC/heater and scooter charging can be controlled, subject to their rules.

## 4. Generator energy

The generator has a fixed power. When it is on:

`G_t = g_t × P_g × Δt`

Generator power is 5 kW. Actual G_t is capped to the empty battery space after solar charging. Runtime is G_t / 5 hours. The generator switch turns off when charging fills the battery, before appliance consumption, and is forced off overnight.

## 5. Home-battery balance

First calculate the energy trying to enter the battery:

`incoming_t = S_t + G_t`

Then battery energy after charging is capped:

`B_after_charge = min(B_max, B_t + incoming_t)`

Extra energy cannot be stored:

`C_t = max(0, B_t + incoming_t − B_max)`

Then appliances use the battery:

If the total desired appliance demand is within available battery energy (`D_t <= B_after_charge`):
- All requested appliances are served: `served_{a,t} = E_{a,t}`
- Next battery energy: `B_{t+1} = B_after_charge - D_t`
- Unmet demand: `U_t = 0`

If the desired appliance energy exceeds available battery energy (`D_t > B_after_charge`):
- The battery is depleted: all appliances stop (`served_{a,t} = 0` for all appliances)
- `B_{t+1} = 0`
- `U_t = D_t`
- A severe battery depletion penalty is applied to the RL agent. There is no fixed supply priority or artificial load-shedding rule.

## 6. Scooter battery

Scooter charging is allowed only from 17:00 onwards in the daily example, including overnight.

`z_{t+1} = min(z_max, z_t + E_scooter,t)`

When `z_t = z_max`, scooter charging stops automatically. For the example scooter: charging power is 0.3 kW and full capacity is 2 kWh.

## 7. Scheduling constraints

The environment enforces these physical rules:

- fixed-duration tasks are non-preemptible by choice: once started, they run to completion;
- if interrupted by a battery-depletion outage, remaining duration is preserved and the task continues in subsequent periods when power is available;
- completed fixed-duration tasks stop automatically;
- dishwasher cannot start before its allowed time (20:00);
- oven cycles can start at the configured meal times (11:30 and 17:00);
- TV/PC runs only in its permitted windows;
- normal appliances, AC, and generator do not run after 23:00;
- refrigerator continues overnight;
- scooter may charge overnight;
- generator stops when the home battery becomes full.

## 8. Objective

The model maximises a cumulative return that rewards desired behaviour and penalises undesired behaviour:

`maximise: appliance service rewards + AC comfort - generator-use cost - missed-deadline cost - battery-depletion penalty`

To resolve temporal credit assignment, required fixed-duration tasks (oven, laundry, dishwasher) yield immediate per-period service rewards whenever active and fully supplied, while retaining midnight penalties if deadlines are missed. The numerical reward values are configured in `config.json`.

## 9. Composite action dispatch

At each 30-minute time block, the agent chooses a composite joint action vector simultaneously:

`a_t = (u_gen, u_ac, u_scooter, u_start_laundry, u_start_dishwasher, u_start_oven)`

This allows starting the generator and appliances simultaneously to prevent battery depletion, providing true multi-variable microgrid control.
