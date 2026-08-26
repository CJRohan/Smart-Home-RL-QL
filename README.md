# Smart Home Appliance Scheduling with Q-Learning

This project models an off-grid home with solar generation, a diesel generator, a home battery, and household appliances. Its aim is to learn when devices should run and when the generator should operate, while reducing generator use and meeting energy-task requirements.

## Current status

The model structure, scenario generator, environment, state/action design, and a basic tabular Q-learning agent are implemented. The project has not yet generated a formal dataset, trained a final policy, or reported experimental results.

## Energy flow

```text
solar panel  ─┐
              ├──> home battery ───> household appliances
diesel gen. ─┘
```

There is no external electricity grid. Solar and diesel energy charge the home battery. Appliances draw energy from the battery.

## Project files

| File | Purpose |
|---|---|
| `config.json` | Physical parameters, appliances, reward values, state bins, and explicit assumptions. |
| `time_blocks.py` | Creates 28 half-hour daytime periods and one 10-hour overnight period. |
| `solar_model.py` | Calculates solar energy from month, panel area, time multipliers, and variation. |
| `appliance_model.py` | Calculates appliance demand and permitted operating periods. |
| `energy_system.py` | Applies generator charging, battery limits, curtailed energy, and unavailable-power logic. |
| `scenario_generator.py` | Creates reproducible daily solar and appliance-demand scenarios. |
| `state_action_model.py` | Builds discrete Q-learning states and lists valid actions for each period. |
| `smart_home_environment.py` | Applies actions, pauses/resumes fixed-duration tasks, and performs each time-step energy balance. |
| `q_learning_agent.py` | Basic tabular Q-learning implementation using only the Python standard library. |
| `train_q_learning.py` | Training loop; included for the next stage and not run as part of this repository update. |
| `check_model_structure.py` | Prints a small visible check of time blocks, solar, diesel, battery, state, and actions. |
| `model_notes.md` | Configuration decisions and modelling assumptions. |
| `modelling_questions.md` | Remaining questions to resolve before formal experiments. |

## State and actions

The state includes time, battery bin, generator status, fixed-task progress, solar forecasts, mandatory next-period demand, and future demand to the next morning. Scooter charge is represented through energy demand rather than a separate scooter-battery bin.

Actions are limited to those that make sense in the current period. For example, a completed task cannot start again, a running fixed-duration task can be paused, and a paused task can later resume. The initial action-space simplification is one valid switch action, or `do_nothing`, per 30-minute period.

## Quick check

The project has no external Python dependencies. From the repository folder, run:

```bash
python check_model_structure.py
```

This is a structural check only. It does not generate files, train an agent, or report model performance.

## Next stage

1. Generate and save reproducible training and test scenarios.
2. Review the remaining assumptions in `model_notes.md` and `modelling_questions.md`.
3. Run the basic Q-learning training loop.
4. Evaluate the learned policy on the saved test scenarios.
