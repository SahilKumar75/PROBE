from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
import statistics
import uuid
from pathlib import Path

from probe.competing.agents import CompetingBaselineAgent, CompetingProbeAgent
from probe.competing.env import CompetingHypothesesEnv


VARIANTS = {
    "baseline_ch": CompetingBaselineAgent,
    "probe_ch": CompetingProbeAgent,
}

TRACE_FIELDS = ["run_id", "variant", "seed", "episode", "step", "phase", "color", "shape", "chosen_key", "correct_key", "reward", "true_feature", "note"]


def _run_episode(variant, seed, episode, horizon, shift_step, run_id) -> list[dict]:
    env = CompetingHypothesesEnv(horizon=horizon, shift_step=shift_step, seed=seed * 1000 + episode)
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
                "true_feature": info["true_feature"],
                "note": note,
            }
        )
        history.append({"color": info["color"], "shape": info["shape"], "key": key, "reward": reward})
        obs = next_obs
        if done:
            break
    return rows


def _episode_metrics(rows: list[dict]) -> dict:
    dis = [r for r in rows if r["phase"] == "disambiguating"]
    amb = [r for r in rows if r["phase"] == "ambiguous"]
    third = max(1, len(dis) // 3)
    return {
        "ambiguous_acc": statistics.mean(r["reward"] for r in amb) if amb else 0.0,
        "disambig_acc": statistics.mean(r["reward"] for r in dis) if dis else 0.0,
        "disambig_late_acc": statistics.mean(r["reward"] for r in dis[-third:]) if dis else 0.0,
    }


def run_competing(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    episodes_per_seed: int = 5,
    variant_names: list[str] | None = None,
    horizon: int = 30,
    shift_step: int = 10,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(10))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("COMPETING_MAX_WORKERS", "8"))
    summaries: dict[str, dict] = {}

    for variant in selected:
        tasks = [(seed, ep) for seed in seeds for ep in range(episodes_per_seed)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_run_episode, variant, seed, ep, horizon, shift_step, run_id)
                for seed, ep in tasks
            ]
            episodes = [future.result() for future in futures]

        episodes.sort(key=lambda ep_rows: (ep_rows[0]["seed"], ep_rows[0]["episode"]))
        all_rows = [row for ep_rows in episodes for row in ep_rows]
        per_episode = [_episode_metrics(ep_rows) for ep_rows in episodes]

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"competing_{variant}_{run_id}{batch_suffix}.csv"
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
            "shift_step": shift_step,
            "ambiguous_accuracy": statistics.mean(m["ambiguous_acc"] for m in per_episode),
            "disambiguating_accuracy": statistics.mean(m["disambig_acc"] for m in per_episode),
            "disambiguating_late_accuracy": statistics.mean(m["disambig_late_acc"] for m in per_episode),
            "trace_file": str(trace_path),
        }

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"competing_summary_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
