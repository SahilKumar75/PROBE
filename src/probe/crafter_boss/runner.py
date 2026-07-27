from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
import statistics
import uuid
from pathlib import Path

from probe.crafter_boss.agents import ACTIONS, CrafterBaselineAgent, CrafterProbeAgent, CrafterReflexionAgent
from probe.crafter_boss.env import describe, id_to_name, make_env


VARIANTS = {
    "baseline_cf": CrafterBaselineAgent,
    "reflexion_cf": CrafterReflexionAgent,
    "probe_cf": CrafterProbeAgent,
}

TRACE_FIELDS = ["run_id", "variant", "seed", "step", "action", "reward", "achievements", "note"]


def _play(variant, seed, budget, run_id) -> dict:
    env = make_env(seed)
    env.reset()
    idmap = id_to_name(env)
    agent = VARIANTS[variant]()
    _, reward, done, info = env.step(ACTIONS.index("noop"))
    obs = describe(info, idmap)
    history: list[dict] = []
    rows: list[dict] = []
    total_reward = 0.0
    steps = 0

    for step in range(budget):
        action_index, note = agent.act(obs, history)
        _, reward, done, info = env.step(action_index)
        obs = describe(info, idmap)
        total_reward += float(reward)
        unlocked = sum(1 for v in info["achievements"].values() if v > 0)
        steps = step + 1
        rows.append(
            {
                "run_id": run_id,
                "variant": variant,
                "seed": seed,
                "step": step,
                "action": ACTIONS[action_index],
                "reward": float(reward),
                "achievements": unlocked,
                "note": note,
            }
        )
        history.append({"action": ACTIONS[action_index]})
        if done:
            break

    final_unlocked = sorted(k for k, v in info["achievements"].items() if v > 0)
    print(f"  [{variant}] seed {seed}: achievements={len(final_unlocked)} reward={total_reward:.2f} steps={steps}", flush=True)
    return {"seed": seed, "variant": variant, "achievements": len(final_unlocked), "unlocked": final_unlocked, "reward": total_reward, "steps": steps, "rows": rows}


def run_crafter(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    variant_names: list[str] | None = None,
    budget: int = 60,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(8))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("CRAFTER_MAX_WORKERS", "4"))

    summaries: dict[str, dict] = {}
    for variant in selected:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_play, variant, seed, budget, run_id) for seed in seeds]
            results = [future.result() for future in futures]

        results.sort(key=lambda r: r["seed"])
        all_rows = [row for r in results for row in r["rows"]]
        achievement_union = sorted({a for r in results for a in r["unlocked"]})

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"crafter_{variant}_{run_id}{batch_suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

        summaries[variant] = {
            "run_id": run_id,
            "variant": variant,
            "episodes": len(results),
            "budget": budget,
            "mean_achievements": statistics.mean(r["achievements"] for r in results),
            "mean_reward": statistics.mean(r["reward"] for r in results),
            "mean_steps": statistics.mean(r["steps"] for r in results),
            "achievement_union": achievement_union,
            "trace_file": str(trace_path),
        }

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"crafter_summary_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
