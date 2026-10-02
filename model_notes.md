# Model notes

This repository contains configuration, scenario generation, a physical single-day environment and basic tabular Q-learning. The training runner generates reproducible pilot datasets and a learned Q-table; this is not yet a final validated policy.

See `training_plan.md` for the reproducible training pilot, saved outputs and evaluation protocol.

## Configuration retained

- London supplied solar table, June first; 10 square metre panel.
- Battery capacity 10 kWh, initially 5 kWh; generator 5 kW.
- Generator cost -10 per operating hour, missed oven cycle -30, served AC comfort +2 per period, shortage penalty -100 per affected block.
- Battery upper bounds: 1, 2.5, 4, 6, 10 kWh.
- Mandatory-demand upper bounds: 0.5, 1, 1.5, 2, 100 kWh.
- Future-demand upper bounds: 1, 1.5, 2, 3, 4.5, 100 kWh.
- Next-period solar upper bounds: 0.2, 0.4, 0.6, 0.8, 100 kWh.
- Rest-of-day solar upper bounds: 2, 4, 6, 9, 100 kWh.
- Zero solar shares the first bin; final bins catch all larger values.

## Environment rules and assumptions

Refrigerator and TV are automatic loads. Controllable devices (generator, AC, scooter, and fixed task triggers) are controlled simultaneously through a composite action vector per 30-minute decision block. State includes time/day, battery bin, generator status, task progress and four forecast/demand summaries (11 variables total).

Supply priority has been removed. Total demand is served whenever available battery energy is sufficient. If total demand exceeds available energy, the battery is depleted, all appliances stop, and the RL agent receives a high penalty (-100). Fixed tasks are non-preemptible by choice; remaining time is preserved during an outage and resumes when energy is restored. Overnight permits fridge and scooter, includes morning solar, and forces the generator off. The generator also switches off at charge-time battery fullness.
