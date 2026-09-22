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

`B_{t+1} = B_after_charge − Σ served_{a,t}`

If the desired appliance energy is greater than the battery energy, the difference is unmet demand:

`U_t = D_t − Σ served_{a,t}`

`U_t > 0` represents a battery-depletion / power-unavailability event. The detailed rule for which appliance loses supply first remains a modelling choice.

## 6. Scooter battery

Scooter charging is allowed only from 17:00 onwards in the daily example, including overnight.

`z_{t+1} = min(z_max, z_t + E_scooter,t)`

When `z_t = z_max`, scooter charging stops automatically. For the example scooter: charging power is 0.3 kW and full capacity is 2 kWh.

## 7. Scheduling constraints

The environment enforces these rules:

- fixed-duration tasks retain remaining duration when paused; only fully supplied periods reduce it;
- a completed fixed-duration task stops automatically;
- dishwasher cannot start before its allowed time;
- new oven cycles can start at the configured times; paused cycles can resume later during daytime;
- TV/PC runs only in its permitted windows;
- normal appliances and generator do not run after 23:00;
- refrigerator continues overnight;
- scooter may charge overnight;
- generator stops when the home battery becomes full.

## 8. Objective (not numerical yet)

The model should maximise a score that rewards desired behaviour and penalises undesired behaviour:

`maximise: household comfort + completed tasks − generator-use cost − missed-deadline cost − unmet-demand cost − wasted-energy cost`

The reward includes generator duration, missed deadlines, uncharged scooter, AC/heater comfort, and a strong penalty for battery depletion. The numerical values are stored in `config.json`.

## 9. What an RL agent would eventually choose

At each time block, the agent would choose permitted decisions such as:

- start laundry, dishwasher, or oven when allowed;
- run / stop AC-heater;
- start / stop scooter charging after 17:00;
- turn generator on / off.

The mathematical model above decides the physical result of that decision: energy flow, battery level, task progress, and whether there is a power shortfall.
