from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import json
import math
import os
import statistics
import uuid
from pathlib import Path

from probe.benchmarks.agents import VARIANTS
from probe.bench_induction.env import InductionEnv, LEVELS


TRACE_FIELDS = [
    "run_id",
    "variant",
    "level",
    "seed",
    "episode",
    "step",
    "cue",
    "cue_text",
    "chosen_key",
    "correct_key",
    "reward",
    "note",
]


def _ci95(values: list[float]) -> list[float]:
    n = len(values)
    if n < 2:
        return [statistics.mean(values) if values else 0.0, 0.0]
    mean = statistics.mean(values)
    half = 1.96 * statistics.stdev(values) / math.sqrt(n)
    return [mean, half]


def _gap_ci(a: list[float], b: list[float]) -> list[float]:
    diff = statistics.mean(b) - statistics.mean(a)
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    return [diff, diff - 1.96 * se, diff + 1.96 * se]


def _run_episode(variant: str, seed: int, episode: int, level: str, run_id: str) -> list[dict]:
    env = InductionEnv(level=level, seed=seed * 1000 + episode)
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
                "level": level,
                "seed": seed,
                "episode": episode,
                "step": step,
                "cue": info["cue"],
                "cue_text": info["cue_text"],
                "chosen_key": key,
                "correct_key": info["correct_key"],
                "reward": reward,
                "note": note,
            }
        )
        history.append({"cue": info["cue"], "cue_text": info["cue_text"], "key": key, "reward": reward})
        obs = next_obs
        if done:
            break
    return rows


def _episode_metrics(rows: list[dict]) -> dict:
    half = len(rows) // 2
    overall = statistics.mean(r["reward"] for r in rows) if rows else 0.0
    asymptotic = statistics.mean(r["reward"] for r in rows[half:]) if rows[half:] else 0.0
    return {"overall_acc": overall, "asymptotic_acc": asymptotic}


def run_induction(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    episodes_per_seed: int = 1,
    variant_names: list[str] | None = None,
    level: str = "hardest",
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(20))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("BENCH_MAX_WORKERS", "8"))
    if level not in LEVELS:
        raise ValueError(f"unknown level {level}; options {list(LEVELS)}")

    summaries: dict[str, dict] = {}
    asymptotic_by_variant: dict[str, list[float]] = {}

    for variant in selected:
        tasks = [(seed, ep) for seed in seeds for ep in range(episodes_per_seed)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_episode, variant, seed, ep, level, run_id) for seed, ep in tasks]
            episodes = [future.result() for future in futures]

        episodes.sort(key=lambda ep_rows: (ep_rows[0]["seed"], ep_rows[0]["episode"]))
        all_rows = [row for ep_rows in episodes for row in ep_rows]
        per_episode = [_episode_metrics(ep_rows) for ep_rows in episodes]
        overall = [m["overall_acc"] for m in per_episode]
        asymptotic = [m["asymptotic_acc"] for m in per_episode]
        asymptotic_by_variant[variant] = asymptotic

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"induction_{variant}_{level}_{run_id}{batch_suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

        summaries[variant] = {
            "run_id": run_id,
            "batch_id": batch_id,
            "variant": variant,
            "level": level,
            "episodes": len(episodes),
            "overall_accuracy": _ci95(overall),
            "asymptotic_accuracy": _ci95(asymptotic),
            "model_call_skip_rate": (sum(1 for r in all_rows if r["note"].startswith("cached")) / len(all_rows)) if all_rows else 0.0,
            "trace_file": str(trace_path),
        }

    gaps: dict[str, list[float]] = {}
    if "probe" in asymptotic_by_variant:
        for other in ("baseline", "reflexion"):
            if other in asymptotic_by_variant:
                gaps[f"probe_minus_{other}"] = _gap_ci(asymptotic_by_variant[other], asymptotic_by_variant["probe"])

    result = {"run_id": run_id, "level": level, "variants": summaries, "asymptotic_gaps": gaps}
    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"induction_summary_{level}_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    return {"summary_file": str(summary_path), **result}
