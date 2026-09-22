# Model notes

This repository contains configuration, scenario generation, a physical single-day environment and basic tabular Q-learning. Regression tests have been run, but no formal dataset or trained policy is produced by this update.

Read `feedback_implementation.md` for the professor feedback, exact bin intervals, priority rules, energy examples and verification.

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

Refrigerator and TV are automatic loads. Other devices remain controlled through one valid switch action or do_nothing per decision block. State includes time/day, battery bin, generator status, task progress and four forecast/demand summaries. Scooter charge is represented through demand rather than a separate state bin.

Supply priority is refrigerator, laundry, dishwasher, oven, TV, AC, scooter. Within-group ordering and scooter placement are assumptions. Fixed tasks need a complete time slice or pause without consuming energy; lower priorities wait when a higher requested load is undersupplied. A paused task retains its duration and resumes through an on action. Overnight permits fridge and scooter, includes morning solar, and forces the generator off. The generator also switches off at charge-time battery fullness.

The next stage is review of `modelling_questions.md`, formal scenario generation and training. No learning performance is claimed.
