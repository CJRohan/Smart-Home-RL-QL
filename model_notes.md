# Model notes: configuration choices and assumptions

This folder is a code-review package. It contains configuration, scenario generation, a physical environment, and basic tabular Q-learning. It contains no generated scenario files, trained Q-table, evaluation data, or results.

## Model configuration

- Generator operating cost: `-10` per operating hour.
- Missed oven deadline/cycle: `-30`.
- AC/heater served operation: `+2` per 30-minute period.
- Battery state bins: `0-1`, `1-2.5`, `2.5-4`, `4-6`, and `6-10` kWh.
- State includes current day/time, current battery bin, generator status, running fixed-duration appliances and remaining time, ongoing/remaining tasks, and the four forecast/demand summaries below.
- The four summaries are: solar in the next period; solar after that until sunset; mandatory energy in the next period; and demand after that until 09:00 tomorrow.
- Mandatory next-period-demand bins have upper bounds `0.5, 1, 1.5, 2, >2` kWh.
- Future-demand bins have upper bounds `1, 1.5, 2, 3, 4.5, >4.5` kWh.
- Scooter battery level is not a separate state variable.
- Available actions depend on time, device status, and task completion. An on device can only be turned off; a completed task has no action.

## Implemented for review

- `config.json` contains the reward values and state bins.
- `state_action_model.py` creates the discrete state tuple and lists valid actions for an example time and device status.
- `scenario_generator.py`, `smart_home_environment.py`, and `q_learning_agent.py` provide the next code layers, but have not been used to produce results.
- Refrigerator and TV/PC are treated as automatic loads, not RL-controlled actions.
- Generator, laundry, dishwasher, oven, AC/heater, and scooter are treated as controllable devices.

## Assumptions, clearly separated in config.json

- The two solar forecast variables use the same five bin upper bounds as the battery: `1, 2.5, 4, 6, 10` kWh.
- Refrigerator and TV/PC are automatic rather than actions selected by RL.
- A running fixed-duration appliance has an available `off` action. It pauses and preserves its remaining time; a later `on` action resumes it.
- The first implementation lets the agent select one valid switch action, or `do_nothing`, per 30-minute period. This is a simplifying action-space assumption.
- The model will use one day initially; `current_day` is included so it can extend to multi-day scheduling later.

## Next build step

The next step is scenario generation and the physical RL environment. No learning result is being claimed at this stage.
