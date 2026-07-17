"""Evaluation runner for Stage 0."""

from __future__ import annotations

from collections import defaultdict
import statistics
import uuid
from pathlib import Path

from probe.constants import STAGE0_EPISODES_PER_SEED, STAGE0_SEEDS
from probe.stage0.boss_i0 import BossI0
from probe.stage0.policies import plain_llm_agent, random_policy
from probe.stage0.tracing import TraceLogger, TraceRow, dump_json


VARIANTS = {
    "random_policy": random_policy,
    "plain_llm_agent": plain_llm_agent,
}


def run_stage0(output_dir: Path, trace_dir: Path) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = list(range(STAGE0_SEEDS))
    summaries: dict[str, dict] = {}

    for variant_name, policy in VARIANTS.items():
        rows: list[TraceRow] = []
        per_seed = defaultdict(lambda: {"episodes": 0, "successes": 0, "steps": [], "timeouts": 0})
        success_count = 0
        cumulative_rewards: list[int] = []
        steps_to_success: list[int] = []
        timeout_count = 0

        for seed in seeds:
            for episode_id in range(STAGE0_EPISODES_PER_SEED):
                env = BossI0(seed=seed * 1000 + episode_id)
                obs = env.reset()
                history: list[dict] = []
                cumulative_reward = 0
                truncated = False
                failure_reason = ""
                done = False
                step_id = 0

                while not done:
                    if variant_name == "plain_llm_agent":
                        action = policy(obs, history)
                    else:
                        action = policy(obs)

                    result = env.step(action)
                    done = bool(result["done"])
                    reward = int(result["reward"])
                    cumulative_reward += reward
                    success = reward == 1
                    truncated = done and not success
                    if truncated:
                        failure_reason = "step_budget_exhausted"

                    rows.append(
                        TraceRow(
                            run_id=run_id,
                            variant_name=variant_name,
                            env_id="BossI0",
                            seed=seed,
                            episode_id=episode_id,
                            step_id=step_id,
                            mission_text="",
                            raw_observation=str(obs),
                            structured_observation=str(obs),
                            chosen_action=action,
                            action_source=variant_name,
                            reward=reward,
                            done=done,
                            truncated=truncated,
                            cumulative_reward=cumulative_reward,
                            step_count=result["step_count"],
                            success=success,
                            failure_reason=failure_reason,
                            notes="",
                        )
                    )

                    history.append({"observation": obs, "action": action, "result": result})
                    obs = {"position": result["position"], "target_here": result["target_here"]}
                    step_id += 1

                per_seed[seed]["episodes"] += 1
                per_seed[seed]["steps"].append(result["step_count"])
                cumulative_rewards.append(cumulative_reward)
                if success:
                    success_count += 1
                    per_seed[seed]["successes"] += 1
                    steps_to_success.append(result["step_count"])
                else:
                    timeout_count += 1
                    per_seed[seed]["timeouts"] += 1

        trace_path = trace_dir / f"stage0_{variant_name}_{run_id}.csv"
        TraceLogger(trace_path).write_rows(rows)

        summaries[variant_name] = {
            "run_id": run_id,
            "variant_name": variant_name,
            "env_id": "BossI0",
            "total_episodes": STAGE0_SEEDS * STAGE0_EPISODES_PER_SEED,
            "success_rate": success_count / (STAGE0_SEEDS * STAGE0_EPISODES_PER_SEED),
            "median_steps_to_success": statistics.median(steps_to_success) if steps_to_success else None,
            "average_cumulative_reward": statistics.mean(cumulative_rewards) if cumulative_rewards else 0.0,
            "fraction_step_budget_exhausted": timeout_count / (STAGE0_SEEDS * STAGE0_EPISODES_PER_SEED),
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

    summary_path = output_dir / f"stage0_summary_{run_id}.json"
    dump_json(summaries, summary_path)
    return {
        "run_id": run_id,
        "summary_file": str(summary_path),
        "variants": summaries,
    }
