from __future__ import annotations

import csv
import json
import os
import statistics
import uuid
from pathlib import Path

from probe.minihack_boss.agents import MiniHackBaselineAgent, MiniHackProbeAgent
from probe.minihack_boss.env import action_labels, describe, make_env


VARIANTS = {
    "baseline_mh": MiniHackBaselineAgent,
    "probe_mh": MiniHackProbeAgent,
}

TRACE_FIELDS = ["run_id", "variant", "env_id", "seed", "step", "action", "reward", "done", "note"]


def _play(variant, env_id, seed, budget, run_id) -> dict:
    env = make_env(env_id, seed)
    reset = env.reset()
    obs = reset[0] if isinstance(reset, tuple) else reset
    actions = action_labels(env)
    agent = VARIANTS[variant]()
    history: list[dict] = []
    rows: list[dict] = []
    total_reward = 0.0
    steps = 0
    success = False

    for step in range(budget):
        idx, note = agent.act(describe(obs), actions, history)
        obs, reward, done, info = env.step(idx)
        total_reward += float(reward)
        steps = step + 1
        if float(reward) > 0:
            success = True
        rows.append(
            {
                "run_id": run_id,
                "variant": variant,
                "env_id": env_id,
                "seed": seed,
                "step": step,
                "action": actions[idx] if idx < len(actions) else str(idx),
                "reward": float(reward),
                "done": bool(done),
                "note": note,
            }
        )
        history.append({"action": actions[idx] if idx < len(actions) else str(idx)})
        if done:
            break

    try:
        env.close()
    except Exception:
        pass
    return {"seed": seed, "variant": variant, "success": 1.0 if success else 0.0, "reward": total_reward, "steps": steps, "rows": rows}


def run_minihack(
    output_dir: Path,
    trace_dir: Path,
    env_id: str = "MiniHack-MazeWalk-9x9-v0",
    seeds: list[int] | None = None,
    variant_names: list[str] | None = None,
    budget: int = 50,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(10))
    selected = variant_names or list(VARIANTS.keys())

    summaries: dict[str, dict] = {}
    for variant in selected:
        results = [_play(variant, env_id, seed, budget, run_id) for seed in seeds]
        results.sort(key=lambda r: r["seed"])
        all_rows = [row for r in results for row in r["rows"]]

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"minihack_{variant}_{run_id}{batch_suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

        summaries[variant] = {
            "run_id": run_id,
            "variant": variant,
            "env_id": env_id,
            "episodes": len(results),
            "budget": budget,
            "success_rate": statistics.mean(r["success"] for r in results),
            "mean_reward": statistics.mean(r["reward"] for r in results),
            "mean_steps": statistics.mean(r["steps"] for r in results),
            "trace_file": str(trace_path),
        }

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"minihack_summary_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
