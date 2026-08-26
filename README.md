# Smart Home Mathematical Model — discussion draft

This folder is intentionally **before** the scenario-generation and Reinforcement Learning stages.

It uses the same complete `config.json` as the 1,000-case build, then turns the physical model into small numbered Python files. It does not generate random days, train Q-learning, make results, or recommend a final algorithm.

## Read in this order

1. `research_question.md` — the problem we are trying to answer.
2. `notation.md` — every symbol used in the equations.
3. `mathematical_model.md` — energy flow, decisions, constraints, and objective.
4. `config.json` — the complete parameters also used by the 1,000-case build.
5. `config_loader.py` — class that reads the parameter file.
6. `time_blocks.py` — class that creates 28 daytime blocks and one overnight block.
7. `solar_model.py` — class that calculates solar energy from month and time multipliers.
8. `appliance_model.py` — class that calculates appliance demand and permitted times.
9. `energy_system.py` — class for generator, home battery, unmet demand and scooter battery.
10. `state_action_model.py` — class for the discrete state and period-dependent valid actions.
11. `scenario_generator.py` — class that creates reproducible random solar and appliance-demand days.
12. `smart_home_environment.py` — class that applies actions, pauses/resumes tasks, and performs the energy balance.
13. `q_learning_agent.py` — basic tabular Q-learning written without an RL library.
14. `train_q_learning.py` — a separate training loop; it is included but has not been run.
15. `model_notes.md` — configuration decisions separated from assumptions.
16. `check_model_structure.py` — visible printouts, not experimental results.
17. `modelling_questions.md` — choices to resolve before training.

## The simple picture

```
solar panel  ─┐
              ├──> home battery ───> household appliances
diesel gen. ─┘
```

There is no external electricity grid. Solar and the diesel generator only charge the battery; appliances draw from the battery.

## Not included yet

- randomly generated scenarios or real-data import;
- a Q-table, Q-learning, PPO, or any other RL library;
- rewards with chosen numerical weights;
- training, testing, charts, or claimed performance.

Scenario generation and a basic Q-learning implementation are now included for code review. No scenario files, trained Q-table, or results are included in this package.

The reward, state, and Q-learning sections in `config.json` are used by the model classes. Remaining modelling choices are explicitly separated under `assumptions_to_confirm_before_training`.

## Optional small check

Run:

`python check_model_structure.py`

It prints a few values so they can be checked by eye. It does not create data or claim an experimental result.
