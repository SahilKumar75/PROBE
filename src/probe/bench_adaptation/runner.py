from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import math
import os
import statistics
import uuid
from pathlib import Path

from probe.benchmarks.agents import VARIANTS
from probe.bench_adaptation.env import AdaptationEnv, LEVELS


TRACE_FIELDS = [
    "run_id",
    "variant",
    "level",
    "seed",
    "episode",
    "step",
    "segment",
    "phase",
    "cue",
    "cue_text",
    "chosen_key",
    "correct_key",
    "old_correct_key",
    "reward",
    "shifted_now",
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
    env = AdaptationEnv(level=level, seed=seed * 1000 + episode)
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
                "segment": info["segment"],
                "phase": "pre" if info["segment"] == 0 else "post",
                "cue": info["cue"],
                "cue_text": info["cue_text"],
                "chosen_key": key,
                "correct_key": info["correct_key"],
                "old_correct_key": info["old_correct_key"],
                "reward": reward,
                "shifted_now": info["shifted_now"],
                "note": note,
            }
        )
        history.append({"cue": info["cue"], "cue_text": info["cue_text"], "key": key, "reward": reward})
        obs = next_obs
        if done:
            break
    return rows


def _episode_metrics(rows: list[dict]) -> dict:
    pre = [r for r in rows if r["phase"] == "pre"]
    post = [r for r in rows if r["phase"] == "post"]
    pre_acc = statistics.mean(r["reward"] for r in pre) if pre else 0.0
    post_acc = statistics.mean(r["reward"] for r in post) if post else 0.0
    repeated_error = sum(
        1 for r in post if r["chosen_key"] == r["old_correct_key"] and r["chosen_key"] != r["correct_key"]
    )
    by_segment: dict = defaultdict(list)
    for r in post:
        by_segment[r["segment"]].append(r)
    recoveries = []
    for seg_rows in by_segment.values():
        recovery = len(seg_rows)
        for index, r in enumerate(seg_rows):
            if r["reward"] == 1:
                recovery = index
                break
        recoveries.append(recovery)
    recovery_mean = statistics.mean(recoveries) if recoveries else 0.0
    return {
        "pre_acc": pre_acc,
        "post_acc": post_acc,
        "repeated_error": repeated_error,
        "recovery_steps": recovery_mean,
    }


def run_adaptation(
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
    post_by_variant: dict[str, list[float]] = {}

    for variant in selected:
        tasks = [(seed, ep) for seed in seeds for ep in range(episodes_per_seed)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_episode, variant, seed, ep, level, run_id) for seed, ep in tasks]
            episodes = [future.result() for future in futures]

        episodes.sort(key=lambda ep_rows: (ep_rows[0]["seed"], ep_rows[0]["episode"]))
        all_rows = [row for ep_rows in episodes for row in ep_rows]
        per_episode = [_episode_metrics(ep_rows) for ep_rows in episodes]
        pre = [m["pre_acc"] for m in per_episode]
        post = [m["post_acc"] for m in per_episode]
        post_by_variant[variant] = post

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"adaptation_{variant}_{level}_{run_id}{batch_suffix}.csv"
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
            "pre_shift_accuracy": _ci95(pre),
            "post_shift_accuracy": _ci95(post),
            "repeated_error_mean": statistics.mean(m["repeated_error"] for m in per_episode),
            "recovery_steps_mean": statistics.mean(m["recovery_steps"] for m in per_episode),
            "model_call_skip_rate": (sum(1 for r in all_rows if r["note"].startswith("cached")) / len(all_rows)) if all_rows else 0.0,
            "trace_file": str(trace_path),
        }

    gaps: dict[str, list[float]] = {}
    if "probe" in post_by_variant:
        for other in ("baseline", "reflexion"):
            if other in post_by_variant:
                gaps[f"probe_minus_{other}"] = _gap_ci(post_by_variant[other], post_by_variant["probe"])

    result = {"run_id": run_id, "level": level, "variants": summaries, "post_shift_gaps": gaps}
    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"adaptation_summary_{level}_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    return {"summary_file": str(summary_path), **result}
