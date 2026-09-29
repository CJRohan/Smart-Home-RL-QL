# Single-day Q-learning pilot

Command: `python train_q_learning.py --train-cases 8000 --test-cases 2000 --epochs 10 --seed 42`

Training: 8000 unique cases x 10 passes = 80000 episodes.
Evaluation: 2000 independent cases, identical for every policy.

| Policy | Mean return | Daily success | Generator h/day | Unmet kWh/day |
|---|---:|---:|---:|---:|
| q_learning | -112.523 | 0.0% | 1.565 | 0.000 |
| rule_based | -8.483 | 100.0% | 5.419 | 0.000 |
| random | -113.036 | 0.7% | 2.309 | 0.395 |
| do_nothing | -140.000 | 0.0% | 0.000 | 0.000 |

Daily success = laundry, dishwasher, both oven cycles and full scooter completed, with no fridge shortfall.
Inspect task completion alongside unmet energy: never starting a task hides it from energy-shortfall metrics.
Q-policy unseen-state fraction: 0.0%.
Unknown Q values default to zero. Greedy ties use valid-action order (do_nothing first).

This is a synthetic June pilot, not evidence of convergence or real-world performance.
The compact state omits some device history and demand summaries use future realised appliance powers: this is an idealised-information experiment.
See training_plan.md in the repository for definitions, limitations and next experiments.

Training runtime: 361.357 seconds.
Evaluation plus trace writing: 52.993 seconds.
