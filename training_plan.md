# Training and evaluation plan

The first experiment is a reproducible pilot of the current single-day model. A completed run proves the pipeline works; it does not prove that 1,000 episodes are enough to learn a good schedule.

## Run the experiment

From the repository directory:

```bash
python train_q_learning.py
```

Defaults are 1,000 training cases and 1,000 separate evaluation cases, taken from `config.json`, one pass over training cases, and base seed 42. Each case is an independently generated June day with 29 time blocks, so the default performs 29,000 Q updates. Cases are saved before the first update. Every run gets a new folder under `./outputs` beside the script, even when launched from another directory.

```bash
python train_q_learning.py --train-cases 1000 --test-cases 1000 --epochs 1 --seed 42
```

`--epochs 10` reuses the same 1,000 training cases for ten shuffled passes (10,000 episodes, 290,000 updates). It does not generate 10,000 distinct days. The base seed determines separate training-data, evaluation-data, action-exploration, shuffle and random-baseline seeds, all saved in the manifest. Changing the base seed changes both data and training randomness, so comparisons intended to isolate training randomness should later use fixed data and independent agent seeds.

Each scenario has a reporting ID such as `train_0001`. Inside the RL state its day is always 1: these are independent single-day episodes. Using a unique case number as the state's day would prevent the agent from sharing knowledge across otherwise equivalent situations.

## What is saved

Example folder name: `outputs/20260922T150000_123456Z_qlearning_June_train1000_test1000_epochs1_seed42/`.

| Output | Contents and purpose |
|---|---|
| `config_snapshot.json` | Exact physical parameters, bins, rewards and learning settings used. CLI counts and seeds are recorded in the manifest. |
| `source/` | Python source snapshot for this run, excluding local tests. |
| `run_manifest.json` | Successful completion marker; UTC start/end, all seeds, actual case/episode/update counts, Python/platform, Q-table size, source and dataset SHA-256 hashes, stage runtimes and update throughput. |
| `training_cases.json` and `.csv` | All generated training inputs, 1,000 cases / 29,000 time rows by default. JSON preserves per-case structure; CSV is convenient for inspection. |
| `evaluation_cases.json` and `.csv` | Separate generated inputs never used for Q updates. Same evaluation cases used for every comparison policy. |
| `training_episodes.csv` | One row per training episode: case ID, pass, epsilon, reward, physical outcomes, completion flags, mean absolute TD error, Q-table size and elapsed training seconds. |
| `q_table.json` | Learned state/action values, update visit counts, state-encoding/version metadata. Readable and reloadable, without unsafe pickle files. |
| `evaluation_episodes.csv` | One row per evaluation day and policy: 4,000 rows for default settings. |
| `evaluation_steps.jsonl` | Every evaluation decision: 116,000 lines by default. Includes state, action, reward, battery before/after, solar/generator energy, per-appliance requested/served/unmet energy, switches and task progress. This may be a few hundred MB. |
| `evaluation_summary.json` | Per-policy means, sample standard deviations, medians, 10th/90th order-statistic percentiles, approximate mean confidence intervals, and paired reward differences against each baseline. |
| `summary.md` | Readable comparison table, state-coverage warning, training/evaluation timing and interpretation limits. |

The manifest is written only after successful completion. A folder without it is an incomplete run. Existing run folders are never overwritten. `outputs/`, local tests and the existing private explanation stay ignored by Git. No commit or upload is performed by the runner.

To reload for analysis in Python:

```python
from train_q_learning import load_agent, greedy_action
config, agent = load_agent("outputs/<run-folder>")
# Use SmartHomeEnvironment(config), then greedy_action(agent, state, valid_actions).
```

## Runtime measurement

Wall-clock durations use `time.perf_counter()`. The manifest separates dataset generation plus saving, training, and evaluation plus detailed trace writing, including each policy's evaluation time. Total duration includes setup and saving other artifacts and ends immediately before writing the final manifest. Training throughput is Q updates divided by training seconds. These are elapsed machine timings, not simulated generator operating hours. File writing, hardware and background processes affect comparisons.

## How learning and evaluation differ

Training uses epsilon-greedy exploration, with epsilon decreasing linearly from 1.0 to 0.10 across all training episodes. At epsilon 1.0 every decision explores; at 0.10 about 10% explore. Learning rate alpha = 0.15 controls how much each new target changes an old Q value. Discount gamma = 0.98 weights later rewards. Those are hyperparameters, not scores. The current gamma is per decision block, including the longer overnight block.

Evaluation freezes the final Q-table: no updates and no exploratory actions. It selects the largest Q value among valid actions. Equal values use the existing action-list order, with `do_nothing` first. Missing state/action entries have value zero, including when other actions have learned negative values. This is the existing zero-initialisation convention; it can make untried actions appear optimistic. Coverage diagnostics expose that risk.

Comparison policies use the same simulator, priorities, initial batteries, daily inputs and one-switch-per-block restriction:

- **Random:** uniformly chooses a valid action with a saved seed.
- **Do nothing:** never changes a switch. Automatic fridge/TV still run; fixed tasks usually remain unfinished. This is a sanity reference, not an acceptable home controller.
- **Rule based:** first switches on the generator below 4 kWh if possible, otherwise starts/resumes oven, dishwasher, laundry and scooter in that order when allowed; turns AC off below 4 kWh or on above 6 kWh. The generator otherwise follows automatic stopping. These fixed thresholds are illustrative and were not tuned using evaluation results. This heuristic is not an optimum or an upper bound.

## Scores that matter

There is no universal single Q-learning accuracy score. This is a control problem, so **R-squared is not an appropriate primary metric**. R-squared, MAE and RMSE would apply to a separate numerical forecasting model, for example predicting measured solar generation. Q values estimate long-term returns, not a labelled correct appliance schedule.

| Measure | Interpretation |
|---|---|
| Total episode return | Sum of all 29 rewards, higher is better under the configured objective. Can be negative. Report mean, spread and low-performing days. This undiscounted reporting score is distinct from the discounted Q-learning target. |
| Task completion rates | Fraction of days with laundry completed, dishwasher completed, both oven cycles completed, and scooter full. Binary columns average to rates. |
| Daily success rate | All four requirements above, plus no refrigerator energy shortfall (within 1e-9 kWh reporting tolerance). This definition does not require uninterrupted optional AC/TV. |
| Unmet energy and shortage blocks | Requested energy not supplied, in kWh, and count of affected blocks; also per appliance, particularly fridge. Lower is better. An overnight block is ten hours, so block counts alone are not outage duration. |
| Generator energy/runtime | kWh/day and operating hours/day; lower is desirable only while maintaining service. No fuel-litre or carbon claim is possible without conversion data. |
| Solar curtailment | Solar energy that cannot enter the battery. Generator output is capped first, so current curtailed energy is solar. Lower is generally desirable, but terminal stored energy must also be inspected. |
| AC service and scooter shortfall | Fully supplied AC hours/day and scooter energy still missing at the end. Interpret comfort alongside generator use. |
| State/action coverage | Fraction of evaluation decisions with no learned valid action at that state, and fraction choosing an unlearned state/action pair. Lower indicates better coverage, not necessarily better policy quality. |
| TD error and visit counts | Training diagnostics: TD error = reward + gamma × best next Q − old Q (terminal target excludes next Q). A lower absolute error is not proof of useful behaviour or convergence. |
| Runtime/sample efficiency | Wall time and number of interactions required to reach useful held-out performance. |

Never judge solely by unmet energy or generator use: a controller that never starts required tasks can look efficient while failing the household. Return also combines preferences through arbitrary reward weights; physical service metrics make the tradeoffs visible.

The report includes paired return differences: for each evaluation day subtract baseline return from Q-policy return, then summarise. Positive means Q-learning did better under the reward objective. Approximate 95% mean intervals use mean ± 1.96 × sample SD / sqrt(n). They describe variability across held-out days for this single trained policy, not uncertainty across independent training runs. Normal mean intervals are unreliable for tiny samples. Binary completion/success rates instead use Wilson 95% intervals, which remain within [0, 1]. Formal reporting should also measure variation across training seeds.

## next possible steps

1. **Pipeline pilot:** run the defaults, check energy conservation and output counts, inspect a good day and a failure day. Measure whether the current learned policy actually improves on useful baselines. Do not interpret a completed run as convergence.
2. **Resolve model information issues:** future-demand summaries currently read future realised appliance powers. Replace these with forecasts available at decision time, or explicitly retain the idealised-information assumption. Review omitted AC/scooter switch history and oven-cycle count in the state, future-demand bin saturation, and the overnight aggregation. The runner keeps current physical and reward rules intact.
3. **Improve training under a fixed protocol:** add a separate validation set and periodic frozen-policy evaluation before tuning episode count, epsilon schedule, learning rate, bins or rewards. A moving average of exploratory training return is useful, but does not replace validation. Keep a fresh final test set untouched by those choices; once this pilot's evaluation outcomes guide revisions, treat them as development evidence.
4. **Repeat with several training seeds:** for example five independent fits on fixed datasets, reporting variation across fits and days. One thousand evaluation days do not substitute for multiple trained policies.
5. **Increase training only when evidence supports it:** compare more distinct training days versus more passes over the saved 1,000 days, inspect coverage and validation curves. Sparse tabular states may need simplification or more visits. A constant learning rate and finite episodes do not establish theoretical Q-learning convergence.
6. **Strengthen comparisons and realism:** compare to a better deadline-aware heuristic and, later, an optimisation benchmark with matched information/constraints. Then test different months and lower-solar conditions; calibrate the solar/noise assumptions. Multi-day recurrence comes after single-day correctness and useful performance are established.

Evaluation guidance: [Stable-Baselines3 evaluation recommendations](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html) and [Agarwal et al., reliable RL evaluation](https://arxiv.org/abs/2108.13264). They motivate separate evaluation and uncertainty reporting; the physical metrics above are specific to this home scheduling problem.
