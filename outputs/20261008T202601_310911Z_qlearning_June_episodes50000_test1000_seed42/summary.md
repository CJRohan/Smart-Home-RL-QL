# Single-day Q-learning pilot

Command: `python train_q_learning.py --train-episodes 50000 --test-cases 1000 --seed 42`

Training: 50000 independently generated days, each used once = 50000 episodes.
Evaluation: 1000 independent cases, identical for every policy.

| Policy | Mean return | Daily success | Generator h/day | Unmet kWh/day |
|---|---:|---:|---:|---:|
| q_learning | 8.011 | 54.6% | 2.218 | 0.057 |
| rule_based | 19.803 | 100.0% | 1.133 | 0.000 |
| random | -41.833 | 13.5% | 3.292 | 0.783 |
| do_nothing | -140.000 | 0.0% | 0.000 | 0.000 |

Daily success = laundry, dishwasher, both oven cycles and full scooter completed, with no fridge shortfall.
Inspect task completion alongside unmet energy: never starting a task hides it from energy-shortfall metrics.
Q-policy unseen-state fraction: 0.0%.
Unknown Q values default to zero. Greedy ties use valid-action order (do_nothing first).

This is a synthetic June pilot, not evidence of convergence or real-world performance.
The compact state omits some device history and demand summaries use future realised appliance powers: this is an idealised-information experiment.
See training_plan.md in the repository for definitions, limitations and next experiments.

Training runtime: 66.306 seconds.
Evaluation plus trace writing: 6.522 seconds.
