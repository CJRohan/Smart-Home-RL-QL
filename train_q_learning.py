#!/usr/bin/env python3
"""Save daily scenarios, train tabular Q-learning, evaluate frozen policies.

Run `python train_q_learning.py`; uses only the Python standard library.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from config_loader import ConfigLoader
from q_learning_agent import QLearningAgent
from scenario_generator import ScenarioGenerator
from smart_home_environment import SmartHomeEnvironment
from state_action_model import CompositeAction

ROOT = Path(__file__).resolve().parent
TOL = 1e-9


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate_cases(config, count, seed, split):
    generator = ScenarioGenerator(config, seed)
    # Case identity is metadata, NOT the day within the episode in the RL state.
    for i in range(count):
        yield dict(case_id=f"{split}_{i + 1:06d}", rows=generator.generate_day(day_number=1))


def save_cases(folder, split, cases):
    """Stream scenarios to disk; never retain the full training set in memory."""
    with gzip.open(folder / f"{split}_cases.jsonl.gz", "wt", encoding="utf-8") as data, \
            gzip.open(folder / f"{split}_cases.csv.gz", "wt", newline="", encoding="utf-8") as table:
        writer = None
        for case in cases:
            data.write(json.dumps(case, allow_nan=False) + "\n")
            for row in case["rows"]:
                record = dict(case_id=case["case_id"], **row)
                if writer is None:
                    writer = csv.DictWriter(table, fieldnames=list(record))
                    writer.writeheader()
                writer.writerow(record)


def read_cases(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def file_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            h.update(chunk)
    return h.hexdigest()


def greedy_action(agent, state, actions):
    # Stable ties make evaluation reproducible. Unknown Q values remain zero.
    return max(actions, key=lambda action: agent.value(state, action))


def load_agent(run_folder):
    """Restore the saved policy and the exact configuration used by its run."""
    run_folder = Path(run_folder)
    config = json.loads((run_folder / "config_snapshot.json").read_text(encoding="utf-8"))
    saved = json.loads((run_folder / "q_table.json").read_text(encoding="utf-8"))
    if saved["format_version"] != 1:
        raise ValueError("Unsupported Q-table format")
    agent = QLearningAgent(config)
    agent.q_table = {
        (
            tuple(entry["state"]),
            CompositeAction(*entry["action"]) if isinstance(entry["action"], (list, tuple)) else entry["action"]
        ): entry["value"]
        for entry in saved["entries"]
    }
    return config, agent


def rule_action(env, actions):
    """Heuristic rule-based dispatcher selecting a valid CompositeAction."""
    row = env.scenario[env.period]
    time = row["time"]
    is_overnight = row["is_overnight"]
    want_gen = int(env.home_battery_kwh < 4.0 and not is_overnight)
    want_ac = int(env.home_battery_kwh > 6.0 and not is_overnight)
    want_scooter = int(
        (is_overnight or time >= env.config["appliances"]["scooter"]["earliest_start"])
        and env.scooter_battery_kwh < env.config["appliances"]["scooter"]["battery_capacity_kwh"]
    )
    want_laundry = int(env.device_status["laundry"] == "not_started" and not is_overnight)
    want_dw = int(
        env.device_status["dishwasher"] == "not_started"
        and time >= env.config["appliances"]["dishwasher"]["earliest_start"]
        and not is_overnight
    )
    want_oven = int(
        env.device_status["oven"] == "not_started"
        and time in env.config["appliances"]["oven"]["allowed_start_times"]
        and not is_overnight
        and env.oven_cycles_completed < env.config["appliances"]["oven"]["required_cycles"]
    )
    desired = CompositeAction(want_gen, want_ac, want_scooter, want_laundry, want_dw, want_oven)
    if desired in actions:
        return desired
    return actions[0]


def run_episode(config, case, agent, policy, rng, epsilon=0.0, visits=None, trace=None):
    env = SmartHomeEnvironment(config)
    state = env.reset(case["rows"])
    metrics = dict(case_id=case["case_id"], policy=policy, return_total=0.0,
                   generator_kwh=0.0, generator_runtime_hours=0.0,
                   solar_kwh=0.0, curtailed_solar_kwh=0.0,
                   requested_kwh=0.0, served_kwh=0.0, unmet_kwh=0.0,
                   shortage_blocks=0, ac_fully_served_hours=0.0,
                   unseen_state_steps=0, unlearned_action_steps=0)
    for name in config["appliances"]:
        metrics[f"{name}_unmet_kwh"] = 0.0
    td_errors = []
    while not env.finished:
        actions = env.valid_actions()
        known = any((state, action) in agent.q_table for action in actions)
        if policy == "training":
            action = agent.choose_action(state, actions, epsilon)
        elif policy == "q_learning":
            action = greedy_action(agent, state, actions)
        elif policy == "random":
            action = rng.choice(actions)
        elif policy == "rule_based":
            action = rule_action(env, actions)
        elif policy == "do_nothing":
            action = actions[0]
        else:
            raise ValueError(f"Unknown policy: {policy}")
        unlearned = (state, action) not in agent.q_table
        row = case["rows"][env.period]
        before = env.home_battery_kwh
        next_state, reward, done, info = env.step(action)
        if policy == "training":
            next_actions = [actions[0]] if done else env.valid_actions()
            td_errors.append(abs(agent.learn(state, action, reward, next_state, next_actions, done)))
            visits[(state, action)] += 1
        metrics["return_total"] += reward
        for key in ("generator_kwh", "generator_runtime_hours", "solar_kwh", "served_kwh", "unmet_kwh"):
            metrics[key] += info[key]
        metrics["curtailed_solar_kwh"] += info["curtailed_kwh"]
        metrics["requested_kwh"] += info["demand_kwh"]
        metrics["shortage_blocks"] += int(info["unmet_kwh"] > TOL)
        metrics["unseen_state_steps"] += int(not known)
        metrics["unlearned_action_steps"] += int(unlearned)
        for name in config["appliances"]:
            metrics[f"{name}_unmet_kwh"] += info["unmet_by_appliance_kwh"][name]
        if (info["requested_by_appliance_kwh"]["ac_heater"] > 0
                and info["unmet_by_appliance_kwh"]["ac_heater"] <= TOL):
            metrics["ac_fully_served_hours"] += row["hours"]
        if trace is not None:
            detail = dict(case_id=case["case_id"], policy=policy, block=row["block"],
                          time=row["time"], hours=row["hours"], state=list(state),
                          reward=reward, battery_before_kwh=before, **info,
                          device_status_after=dict(env.device_status),
                          oven_cycles_completed=env.oven_cycles_completed,
                          scooter_battery_kwh=env.scooter_battery_kwh)
            trace.write(json.dumps(detail, allow_nan=False) + "\n")
        state = next_state
    metrics.update(
        laundry_completed=int(env.device_status["laundry"] == "completed"),
        dishwasher_completed=int(env.device_status["dishwasher"] == "completed"),
        oven_cycles_completed=env.oven_cycles_completed,
        oven_all_cycles_completed=int(env.oven_cycles_completed >= config["appliances"]["oven"]["required_cycles"]),
        scooter_shortfall_kwh=max(0.0, config["appliances"]["scooter"]["battery_capacity_kwh"] - env.scooter_battery_kwh),
        final_battery_kwh=env.home_battery_kwh,
        unseen_state_fraction=metrics["unseen_state_steps"] / len(case["rows"]),
        unlearned_action_fraction=metrics["unlearned_action_steps"] / len(case["rows"]),
        mean_abs_td_error=statistics.mean(td_errors) if td_errors else None)
    metrics["scooter_full"] = int(metrics["scooter_shortfall_kwh"] <= TOL)
    metrics["all_daily_tasks_completed"] = int(all(metrics[key] for key in (
        "laundry_completed", "dishwasher_completed", "oven_all_cycles_completed", "scooter_full")))
    metrics["daily_success"] = int(metrics["all_daily_tasks_completed"] and metrics["refrigerator_unmet_kwh"] <= TOL)
    return metrics


def distribution(values):
    values = sorted(values)
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    half_width = 1.96 * sd / math.sqrt(len(values))
    return dict(mean=mean, sample_sd=sd, median=statistics.median(values),
                p10=values[int(.1 * (len(values) - 1))], p90=values[int(.9 * (len(values) - 1))],
                mean_ci95_normal=[mean - half_width, mean + half_width] if len(values) > 1 else None)


def summarize(rows):
    summaries = {key: distribution([row[key] for row in rows]) for key, value in rows[0].items()
                 if isinstance(value, (int, float))}
    for key in ("laundry_completed", "dishwasher_completed", "oven_all_cycles_completed",
                "scooter_full", "all_daily_tasks_completed", "daily_success"):
        stats = summaries[key]
        n, proportion, z = len(rows), stats["mean"], 1.96
        denominator = 1 + z * z / n
        centre = (proportion + z * z / (2 * n)) / denominator
        half_width = z * math.sqrt(proportion * (1 - proportion) / n + z * z / (4 * n * n)) / denominator
        stats.pop("mean_ci95_normal")
        stats["proportion_ci95_wilson"] = [max(0.0, centre - half_width), min(1.0, centre + half_width)]
    return summaries


def train(train_episodes=None, *, test_cases=None, seed=None, output_root=None, command_args=None):
    """Save a complete pilot run and return (agent, output_directory)."""
    started = time.perf_counter()
    utc_start = datetime.now(timezone.utc)
    config = ConfigLoader().load()
    train_episodes = config["experiment"]["training_episodes"] if train_episodes is None else train_episodes
    test_cases = config["experiment"]["test_instances"] if test_cases is None else test_cases
    seed = config["experiment"]["seed"] if seed is None else seed
    if min(train_episodes, test_cases) < 1:
        raise ValueError("Training episodes and test cases must be positive")
    folder = (Path(output_root) if output_root is not None else ROOT / "outputs") / (
        f"{utc_start.strftime('%Y%m%dT%H%M%S_%fZ')}_qlearning_{config['experiment']['month']}"
        f"_episodes{train_episodes}_test{test_cases}_seed{seed}")
    folder.mkdir(parents=True, exist_ok=False)
    effective_args = ["--train-episodes", str(train_episodes), "--test-cases", str(test_cases),
                      "--seed", str(seed)]
    if output_root is not None:
        effective_args.extend(["--output-root", str(output_root)])
    supplied_args = list(command_args) if command_args is not None else effective_args
    invocation = dict(arguments=supplied_args, arguments_text=subprocess.list2cmdline(supplied_args),
                      effective_arguments=effective_args,
                      command=subprocess.list2cmdline(["python", "train_q_learning.py", *supplied_args]),
                      effective_command=subprocess.list2cmdline(["python", "train_q_learning.py", *effective_args]),
                      python_executable=sys.executable,
                      invocation_type="command_line" if command_args is not None else "python_function")
    write_json(folder / "invocation.json", invocation)
    (folder / "run_command.txt").write_text(invocation["command"] + "\n", encoding="utf-8")
    timings = {}
    seeds = dict(training_data=seed, evaluation_data=seed + 1, agent=seed + 2,
                 random_baseline=seed + 4)
    write_json(folder / "config_snapshot.json", config)
    source_dir = folder / "source"
    source_dir.mkdir()
    source_hashes = {}
    for source in sorted(ROOT.glob("*.py")):
        if source.name.startswith("test"):
            continue
        data = source.read_bytes()
        (source_dir / source.name).write_bytes(data)
        source_hashes[source.name] = hashlib.sha256(data).hexdigest()
    stage = time.perf_counter()
    training = generate_cases(config, train_episodes, seeds["training_data"], "train")
    evaluation = list(generate_cases(config, test_cases, seeds["evaluation_data"], "evaluation"))
    save_cases(folder, "training", training)
    save_cases(folder, "evaluation", evaluation)
    timings["generation_and_dataset_write_seconds"] = time.perf_counter() - stage
    # Both datasets have been saved before any Q update.
    agent = QLearningAgent(config, seed=seeds["agent"])
    visits = Counter()
    start_epsilon = config["q_learning_parameters"]["epsilon_start"]
    end_epsilon = config["q_learning_parameters"]["epsilon_end"]
    stage = time.perf_counter()
    with (folder / "training_episodes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = None
        for index, case in enumerate(read_cases(folder / "training_cases.jsonl.gz")):
            epsilon = start_epsilon + (end_epsilon - start_epsilon) * index / max(1, train_episodes - 1)
            metrics = run_episode(config, case, agent, "training", None, epsilon, visits)
            metrics.update(episode=index + 1, epsilon=epsilon,
                           q_table_entries=len(agent.q_table), elapsed_training_seconds=time.perf_counter() - stage)
            if writer is None:
                writer = csv.DictWriter(stream, fieldnames=list(metrics))
                writer.writeheader()
            writer.writerow(metrics)
            if (index + 1) % max(100, train_episodes // 100) == 0 or index + 1 == train_episodes:
                print(f"Training {index + 1}/{train_episodes}: epsilon={epsilon:.3f}, Q entries={len(agent.q_table)}", flush=True)
    timings["training_seconds"] = time.perf_counter() - stage
    write_json(folder / "q_table.json", dict(format_version=1, state_encoding="composite_single_day_state_v2",
        config_file="config_snapshot.json", entries=[dict(state=list(state), action=list(action) if isinstance(action, tuple) else action, value=value,
                                                          visits=visits[(state, action)])
        for (state, action), value in sorted(agent.q_table.items())]))
    frozen = dict(agent.q_table)
    evaluations = []
    policy_timings = {}
    with gzip.open(folder / "evaluation_steps.jsonl.gz", "wt", encoding="utf-8", compresslevel=6) as trace:
        for policy in ("q_learning", "rule_based", "random", "do_nothing"):
            stage = time.perf_counter()
            rng = random.Random(seeds["random_baseline"])
            for case in evaluation:
                evaluations.append(run_episode(config, case, agent, policy, rng, trace=trace))
            policy_timings[policy] = time.perf_counter() - stage
            print(f"Evaluated {policy}: {test_cases} held-out days", flush=True)
    if agent.q_table != frozen:
        raise RuntimeError("Evaluation must not change Q values")
    timings["evaluation_including_trace_write_seconds"] = sum(policy_timings.values())
    write_csv(folder / "evaluation_episodes.csv", evaluations)
    grouped = {policy: [row for row in evaluations if row["policy"] == policy] for policy in policy_timings}
    summaries = {policy: summarize(rows) for policy, rows in grouped.items()}
    comparisons = {policy: distribution([q["return_total"] - baseline["return_total"]
                    for q, baseline in zip(grouped["q_learning"], grouped[policy])])
                   for policy in ("rule_based", "random", "do_nothing")}
    write_json(folder / "evaluation_summary.json", dict(policies=summaries,
        paired_return_difference_qlearning_minus_baseline=comparisons,
        uncertainty_note="Intervals across held-out days for ONE fitted policy, not across training seeds. Continuous metrics use normal-approximation mean intervals (unreliable for small samples); binary completion/success rates use Wilson intervals."))
    summary = ["# Single-day Q-learning pilot", "", "Command: `" + invocation["command"] + "`", "",
               f"Training: {train_episodes} independently generated days, each used once = {train_episodes} episodes.",
               f"Evaluation: {test_cases} independent cases, identical for every policy.", "",
               "| Policy | Mean return | Daily success | Generator h/day | Unmet kWh/day |",
               "|---|---:|---:|---:|---:|"]
    for policy, stats in summaries.items():
        summary.append(f"| {policy} | {stats['return_total']['mean']:.3f} | "
                       f"{stats['daily_success']['mean']:.1%} | {stats['generator_runtime_hours']['mean']:.3f} | "
                       f"{stats['unmet_kwh']['mean']:.3f} |")
    summary.extend(["", "Daily success = laundry, dishwasher, both oven cycles and full scooter completed, with no fridge shortfall.",
                    "Inspect task completion alongside unmet energy: never starting a task hides it from energy-shortfall metrics.",
                    f"Q-policy unseen-state fraction: {summaries['q_learning']['unseen_state_fraction']['mean']:.1%}.",
                    "Unknown Q values default to zero. Greedy ties use valid-action order (do_nothing first).", "",
                    "This is a synthetic June pilot, not evidence of convergence or real-world performance.",
                    "The compact state omits some device history and demand summaries use future realised appliance powers: this is an idealised-information experiment.",
                    "See training_plan.md in the repository for definitions, limitations and next experiments.", "",
                    f"Training runtime: {timings['training_seconds']:.3f} seconds.",
                    f"Evaluation plus trace writing: {timings['evaluation_including_trace_write_seconds']:.3f} seconds."])
    (folder / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    dataset_hashes = {name: file_sha256(folder / name)
                      for name in ("training_cases.jsonl.gz", "evaluation_cases.jsonl.gz")}
    timings["training_updates_per_second"] = sum(visits.values()) / timings["training_seconds"]
    timings["total_seconds_before_manifest_write"] = time.perf_counter() - started
    write_json(folder / "run_manifest.json", dict(status="completed", invocation=invocation, started_utc=utc_start.isoformat(),
        completed_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
        platform=platform.platform(), training_cases=train_episodes, evaluation_cases=test_cases,
        scenario_sampling="fresh_independent_day_per_episode", scenario_uses=1, dataset_format="jsonl.gz",
        training_episodes=train_episodes, training_updates=sum(visits.values()), seeds=seeds,
        q_table_entries=len(agent.q_table), unique_states=len({state for state, _ in agent.q_table}),
        single_visit_state_action_fraction=sum(count == 1 for count in visits.values()) / len(visits),
        timings=timings, evaluation_seconds_by_policy=policy_timings, source_sha256=source_hashes,
        dataset_sha256=dataset_hashes,
        evaluation_exploration_epsilon=0.0, evaluation_tie_break="first valid action with maximal Q",
        limitation="One training seed; compact state aliases physical histories; demand summaries use future realised powers."))
    print(f"Saved run: {folder}", flush=True)
    return agent, folder


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-episodes", type=positive_int, default=None, help="Fresh single-day episodes (default: config, 100000)")
    parser.add_argument("--test-cases", type=positive_int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-root", type=Path, default=None, help="Default: outputs beside this script")
    args = parser.parse_args()
    train(args.train_episodes, test_cases=args.test_cases,
          seed=args.seed, output_root=args.output_root, command_args=sys.argv[1:])
