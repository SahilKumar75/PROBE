from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
import statistics
import uuid
from pathlib import Path

from probe.probe_progress.agents import ProbeProgressAgent, ProbeProgressBaselineAgent
from probe.probe_progress.env import ProbeOrProgressEnv


VARIANTS = {
    "baseline_pp": ProbeProgressBaselineAgent,
    "probe_pp": ProbeProgressAgent,
}

TRACE_FIELDS = ["run_id", "variant", "seed", "episode", "step", "action", "reward", "revealed", "note"]


def _run_episode(variant, seed, episode, horizon, run_id) -> list[dict]:
    env = ProbeOrProgressEnv(horizon=horizon, seed=seed * 1000 + episode)
    obs = env.reset()
    agent = VARIANTS[variant]()
    history: list[dict] = []
    rows: list[dict] = []
    for step in range(env.horizon):
        action, note = agent.act(obs, history)
        next_obs, reward, done, info = env.step(action)
        rows.append(
            {
                "run_id": run_id,
                "variant": variant,
                "seed": seed,
                "episode": episode,
                "step": step,
                "action": action,
                "reward": reward,
                "revealed": info["revealed"],
                "note": note,
            }
        )
        history.append({"action": action, "reward": reward})
        obs = next_obs
        if done:
            break
    return rows


def _episode_metrics(rows: list[dict], horizon: int) -> dict:
    total = sum(r["reward"] for r in rows)
    probed = any(r["action"] == "probe" for r in rows)
    steps_to_probe = next((r["step"] for r in rows if r["action"] == "probe"), horizon)
    return {
        "total_reward": total,
        "reward_per_step": total / len(rows),
        "probed": 1 if probed else 0,
        "steps_to_probe": steps_to_probe,
    }


def run_probe_progress(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    episodes_per_seed: int = 5,
    variant_names: list[str] | None = None,
    horizon: int = 20,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(10))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("PROBE_PROGRESS_MAX_WORKERS", "8"))
    summaries: dict[str, dict] = {}

    for variant in selected:
        tasks = [(seed, ep) for seed in seeds for ep in range(episodes_per_seed)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_episode, variant, seed, ep, horizon, run_id) for seed, ep in tasks]
            episodes = [future.result() for future in futures]

        episodes.sort(key=lambda ep_rows: (ep_rows[0]["seed"], ep_rows[0]["episode"]))
        all_rows = [row for ep_rows in episodes for row in ep_rows]
        per_episode = [_episode_metrics(ep_rows, horizon) for ep_rows in episodes]

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"probe_progress_{variant}_{run_id}{batch_suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

        summaries[variant] = {
            "run_id": run_id,
            "variant": variant,
            "episodes": len(episodes),
            "horizon": horizon,
            "reward_per_step": statistics.mean(m["reward_per_step"] for m in per_episode),
            "total_reward_mean": statistics.mean(m["total_reward"] for m in per_episode),
            "fraction_probed": statistics.mean(m["probed"] for m in per_episode),
            "mean_steps_to_probe": statistics.mean(m["steps_to_probe"] for m in per_episode),
            "trace_file": str(trace_path),
        }

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"probe_progress_summary_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
