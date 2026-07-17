"""External Stage 0 runner for MiniGrid."""

from __future__ import annotations

from collections import defaultdict
import csv
import json
import statistics
import uuid
from pathlib import Path

from probe.constants import STAGE0_EPISODES_PER_SEED, STAGE0_SEEDS
from probe.stage0.minigrid_env import (
    ACTION_NAMES,
    MINIGRID_ENV_ID,
    make_env,
    raw_observation_text,
    structured_observation,
)
from probe.stage0.minigrid_policies import (
    heuristic_minigrid_policy,
    llm_minigrid_policy,
    random_minigrid_policy,
)
from probe.stage0.tracing import TraceLogger, TraceRow, dump_json


VARIANTS = {
    "random_policy": random_minigrid_policy,
    "heuristic_policy": heuristic_minigrid_policy,
    "plain_llm_agent": llm_minigrid_policy,
}


def run_stage0_minigrid(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    episode_ids: list[int] | None = None,
    variant_names: list[str] | None = None,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds or list(range(STAGE0_SEEDS))
    episode_ids = episode_ids or list(range(STAGE0_EPISODES_PER_SEED))
    selected_variants = variant_names or list(VARIANTS.keys())
    summaries: dict[str, dict] = {}

    for variant_name in selected_variants:
        policy = VARIANTS[variant_name]
        rows: list[TraceRow] = []
        per_seed = defaultdict(lambda: {"episodes": 0, "successes": 0, "steps": [], "timeouts": 0})
        success_count = 0
        cumulative_rewards: list[float] = []
        steps_to_success: list[int] = []
        timeout_count = 0

        for seed in seeds:
            for episode_id in episode_ids:
                env = make_env()
                obs, info = env.reset(seed=seed * 1000 + episode_id)
                history: list[dict] = []
                cumulative_reward = 0.0
                done = False
                step_id = 0
                success = False
                truncated = False
                failure_reason = ""

                while not done:
                    if variant_name in {"heuristic_policy", "plain_llm_agent"}:
                        action = policy(obs, history)
                    else:
                        action = policy(obs)

                    next_obs, reward, terminated, truncated, info = env.step(action)
                    done = bool(terminated or truncated)
                    cumulative_reward += float(reward)
                    success = bool(terminated and reward > 0)
                    if truncated and not success:
                        failure_reason = "step_budget_exhausted"

                    rows.append(
                        TraceRow(
                            run_id=run_id,
                            variant_name=variant_name,
                            env_id=MINIGRID_ENV_ID,
                            seed=seed,
                            episode_id=episode_id,
                            step_id=step_id,
                            mission_text=obs["mission"],
                            raw_observation=raw_observation_text(obs),
                            structured_observation=str(structured_observation(obs)),
                            chosen_action=ACTION_NAMES[action],
                            action_source=variant_name,
                            reward=int(reward),
                            done=done,
                            truncated=bool(truncated),
                            cumulative_reward=int(cumulative_reward),
                            step_count=step_id + 1,
                            success=success,
                            failure_reason=failure_reason,
                            notes="",
                        )
                    )

                    history.append(
                        {
                            "observation": structured_observation(obs),
                            "action": ACTION_NAMES[action],
                            "reward": reward,
                            "terminated": terminated,
                            "truncated": truncated,
                        }
                    )
                    obs = next_obs
                    step_id += 1

                per_seed[seed]["episodes"] += 1
                per_seed[seed]["steps"].append(step_id)
                cumulative_rewards.append(cumulative_reward)
                if success:
                    success_count += 1
                    per_seed[seed]["successes"] += 1
                    steps_to_success.append(step_id)
                else:
                    timeout_count += 1
                    per_seed[seed]["timeouts"] += 1

                env.close()

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"stage0_minigrid_{variant_name}_{run_id}{batch_suffix}.csv"
        TraceLogger(trace_path).write_rows(rows)

        summaries[variant_name] = {
            "run_id": run_id,
            "batch_id": batch_id,
            "variant_name": variant_name,
            "env_id": MINIGRID_ENV_ID,
            "seed_ids": seeds,
            "episode_ids": episode_ids,
            "total_episodes": len(seeds) * len(episode_ids),
            "success_rate": success_count / (len(seeds) * len(episode_ids)),
            "median_steps_to_success": statistics.median(steps_to_success) if steps_to_success else None,
            "average_cumulative_reward": statistics.mean(cumulative_rewards) if cumulative_rewards else 0.0,
            "fraction_step_budget_exhausted": timeout_count / (len(seeds) * len(episode_ids)),
            "per_seed_summary": {
                str(seed): {
                    "episodes": data["episodes"],
                    "successes": data["successes"],
                    "success_rate": data["successes"] / data["episodes"] if data["episodes"] else 0.0,
                    "avg_steps": statistics.mean(data["steps"]) if data["steps"] else 0.0,
                    "timeouts": data["timeouts"],
                }
                for seed, data in per_seed.items()
            },
            "trace_file": str(trace_path),
        }

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"stage0_minigrid_summary_{run_id}{batch_suffix}.json"
    dump_json(summaries, summary_path)
    return {
        "run_id": run_id,
        "batch_id": batch_id,
        "summary_file": str(summary_path),
        "variants": summaries,
    }


def aggregate_stage0_minigrid_batches(summary_files: list[Path], output_path: Path) -> dict:
    aggregated: dict[str, dict] = {}

    for summary_file in summary_files:
        with summary_file.open("r", encoding="utf-8") as handle:
            batch_data = json.load(handle)

        for variant_name, variant_data in batch_data.items():
            entry = aggregated.setdefault(
                variant_name,
                {
                    "variant_name": variant_name,
                    "env_id": variant_data["env_id"],
                    "total_episodes": 0,
                    "successes": 0,
                    "cumulative_rewards": [],
                    "steps_to_success": [],
                    "timeouts": 0,
                    "per_seed_summary": defaultdict(lambda: {"episodes": 0, "successes": 0, "steps": [], "timeouts": 0}),
                    "batch_summaries": [],
                    "trace_files": [],
                    "summary_files": [],
                },
            )

            total_episodes = int(variant_data["total_episodes"])
            successes = int(round(variant_data["success_rate"] * total_episodes))
            timeouts = int(round(variant_data["fraction_step_budget_exhausted"] * total_episodes))
            avg_reward = float(variant_data["average_cumulative_reward"])

            entry["total_episodes"] += total_episodes
            entry["successes"] += successes
            entry["timeouts"] += timeouts
            entry["cumulative_rewards"].extend([avg_reward] * total_episodes)
            if variant_data["median_steps_to_success"] is not None:
                entry["steps_to_success"].append(float(variant_data["median_steps_to_success"]))
            entry["batch_summaries"].append(variant_data.get("batch_id"))
            entry["trace_files"].append(variant_data["trace_file"])
            entry["summary_files"].append(str(summary_file))

            for seed, seed_data in variant_data["per_seed_summary"].items():
                seed_entry = entry["per_seed_summary"][seed]
                seed_entry["episodes"] += int(seed_data["episodes"])
                seed_entry["successes"] += int(seed_data["successes"])
                seed_entry["timeouts"] += int(seed_data["timeouts"])
                if seed_data["avg_steps"]:
                    seed_entry["steps"].append(float(seed_data["avg_steps"]))

    final: dict[str, dict] = {}
    for variant_name, data in aggregated.items():
        final[variant_name] = {
            "variant_name": variant_name,
            "env_id": data["env_id"],
            "total_episodes": data["total_episodes"],
            "success_rate": data["successes"] / data["total_episodes"] if data["total_episodes"] else 0.0,
            "median_steps_to_success": statistics.median(data["steps_to_success"]) if data["steps_to_success"] else None,
            "average_cumulative_reward": statistics.mean(data["cumulative_rewards"]) if data["cumulative_rewards"] else 0.0,
            "fraction_step_budget_exhausted": data["timeouts"] / data["total_episodes"] if data["total_episodes"] else 0.0,
            "per_seed_summary": {
                seed: {
                    "episodes": seed_data["episodes"],
                    "successes": seed_data["successes"],
                    "success_rate": seed_data["successes"] / seed_data["episodes"] if seed_data["episodes"] else 0.0,
                    "avg_steps": statistics.mean(seed_data["steps"]) if seed_data["steps"] else 0.0,
                    "timeouts": seed_data["timeouts"],
                }
                for seed, seed_data in data["per_seed_summary"].items()
            },
            "batch_ids": data["batch_summaries"],
            "trace_files": data["trace_files"],
            "summary_files": data["summary_files"],
        }

    dump_json(final, output_path)
    return final
