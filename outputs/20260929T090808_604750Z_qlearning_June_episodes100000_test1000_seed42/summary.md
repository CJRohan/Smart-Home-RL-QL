# Single-day Q-learning pilot

Command: `python train_q_learning.py`

Training: 100000 independently generated days, each used once = 100000 episodes.
Evaluation: 1000 independent cases, identical for every policy.

| Policy | Mean return | Daily success | Generator h/day | Unmet kWh/day |
|---|---:|---:|---:|---:|
| q_learning | -75.320 | 0.0% | 2.272 | 0.040 |
| rule_based | -8.474 | 100.0% | 5.422 | 0.000 |
| random | -113.307 | 0.6% | 2.330 | 0.391 |
| do_nothing | -140.000 | 0.0% | 0.000 | 0.000 |

Daily success = laundry, dishwasher, both oven cycles and full scooter completed, with no fridge shortfall.
Inspect task completion alongside unmet energy: never starting a task hides it from energy-shortfall metrics.
Q-policy unseen-state fraction: 0.2%.
Unknown Q values default to zero. Greedy ties use valid-action order (do_nothing first).

This is a synthetic June pilot, not evidence of convergence or real-world performance.
The compact state omits some device history and demand summaries use future realised appliance powers: this is an idealised-information experiment.
See training_plan.md in the repository for definitions, limitations and next experiments.

Training runtime: 92.970 seconds.
Evaluation plus trace writing: 4.768 seconds.
