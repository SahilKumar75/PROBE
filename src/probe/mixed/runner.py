from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
import statistics
import uuid
from pathlib import Path

from probe.mixed.env import MixedEnv
from probe.multifactor.agents import MultiFactorBaselineAgent, MultiFactorProbeAgent


VARIANTS = {
    "baseline_mix": MultiFactorBaselineAgent,
    "probe_mix": MultiFactorProbeAgent,
}

TRACE_FIELDS = ["run_id", "variant", "seed", "episode", "step", "phase", "color", "shape", "chosen_key", "correct_key", "reward", "note"]


def _run_episode(variant, seed, episode, n_colors, n_shapes, n_keys, horizon, shift_step, run_id) -> list[dict]:
    env = MixedEnv(n_colors=n_colors, n_shapes=n_shapes, n_keys=n_keys, horizon=horizon, shift_step=shift_step, seed=seed * 1000 + episode)
    obs = env.reset()
    agent = VARIANTS[variant]()
    history: list[dict] = []
    rows: list[dict] = []
    for step in range(env.horizon):
        key, note = agent.act(obs, history)
        next_obs, reward, done, info = env.step(key)
        rows.append(
            {
                "run_id": run_id,
                "variant": variant,
                "seed": seed,
                "episode": episode,
                "step": step,
                "phase": info["phase"],
                "color": info["color"],
                "shape": info["shape"],
                "chosen_key": key,
                "correct_key": info["correct_key"],
                "reward": reward,
                "note": note,
            }
        )
        history.append({"color": info["color"], "shape": info["shape"], "key": key, "reward": reward})
        obs = next_obs
        if done:
            break
    return rows


def _episode_metrics(rows: list[dict]) -> dict:
    pre = [r for r in rows if r["phase"] == "pre"]
    post = [r for r in rows if r["phase"] == "post"]
    third = max(1, len(post) // 3)
    return {
        "pre_acc": statistics.mean(r["reward"] for r in pre) if pre else 0.0,
        "post_acc": statistics.mean(r["reward"] for r in post) if post else 0.0,
        "post_late_acc": statistics.mean(r["reward"] for r in post[-third:]) if post else 0.0,
    }


def run_mixed(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    episodes_per_seed: int = 5,
    variant_names: list[str] | None = None,
    n_colors: int = 3,
    n_shapes: int = 2,
    n_keys: int = 3,
    horizon: int | None = None,
    shift_step: int | None = None,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(10))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("MIXED_MAX_WORKERS", "8"))
    summaries: dict[str, dict] = {}

    for variant in selected:
        tasks = [(seed, ep) for seed in seeds for ep in range(episodes_per_seed)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_run_episode, variant, seed, ep, n_colors, n_shapes, n_keys, horizon, shift_step, run_id)
                for seed, ep in tasks
            ]
            episodes = [future.result() for future in futures]

        episodes.sort(key=lambda ep_rows: (ep_rows[0]["seed"], ep_rows[0]["episode"]))
        all_rows = [row for ep_rows in episodes for row in ep_rows]
        per_episode = [_episode_metrics(ep_rows) for ep_rows in episodes]

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"mixed_{variant}_{run_id}{batch_suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

        summaries[variant] = {
            "run_id": run_id,
            "variant": variant,
            "episodes": len(episodes),
            "n_combos": n_colors * n_shapes,
            "horizon": episodes[0][-1]["step"] + 1 if episodes else 0,
            "pre_shift_accuracy": statistics.mean(m["pre_acc"] for m in per_episode),
            "post_shift_accuracy": statistics.mean(m["post_acc"] for m in per_episode),
            "post_shift_late_accuracy": statistics.mean(m["post_late_acc"] for m in per_episode),
            "trace_file": str(trace_path),
        }

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"mixed_summary_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
