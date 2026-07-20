from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
import statistics
import uuid
from pathlib import Path

from probe.rule_shift.agents import BaselineRuleAgent, ProbeRuleAgent
from probe.rule_shift.env import RuleShiftEnv


VARIANTS = {
    "baseline_rule": BaselineRuleAgent,
    "probe_rule": ProbeRuleAgent,
}

TRACE_FIELDS = [
    "run_id",
    "variant",
    "seed",
    "episode",
    "step",
    "phase",
    "cue",
    "chosen_key",
    "correct_key",
    "old_correct_key",
    "reward",
    "shifted_now",
    "note",
]


def _run_episode(variant: str, seed: int, episode: int, n_symbols: int, horizon, shift_step, run_id: str) -> list[dict]:
    env = RuleShiftEnv(n_symbols=n_symbols, horizon=horizon, shift_step=shift_step, seed=seed * 1000 + episode)
    obs = env.reset()
    agent = VARIANTS[variant]()
    history: list[dict] = []
    rows: list[dict] = []
    initial_rule: dict[str, str] = {}

    for step in range(env.horizon):
        key, note = agent.act(obs, history)
        next_obs, reward, done, info = env.step(key)
        if step == 0:
            initial_rule = info["rule_before_step"]
        rows.append(
            {
                "run_id": run_id,
                "variant": variant,
                "seed": seed,
                "episode": episode,
                "step": step,
                "phase": "pre" if step < env.shift_step else "post",
                "cue": info["cue"],
                "chosen_key": key,
                "correct_key": info["correct_key"],
                "old_correct_key": initial_rule.get(info["cue"], ""),
                "reward": reward,
                "shifted_now": info["shifted_now"],
                "note": note,
            }
        )
        history.append({"cue": info["cue"], "key": key, "reward": reward})
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
    recovery = len(post)
    for index, r in enumerate(post):
        if r["reward"] == 1:
            recovery = index
            break
    return {
        "pre_acc": pre_acc,
        "post_acc": post_acc,
        "repeated_error": repeated_error,
        "recovery_steps": recovery,
        "total_reward": sum(r["reward"] for r in rows),
    }


def run_rule_shift(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    episodes_per_seed: int = 5,
    variant_names: list[str] | None = None,
    n_symbols: int = 3,
    horizon: int | None = None,
    shift_step: int | None = None,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(10))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("RULE_SHIFT_MAX_WORKERS", "8"))
    effective_horizon = horizon if horizon is not None else 8 * n_symbols
    effective_shift = shift_step if shift_step is not None else effective_horizon // 2
    summaries: dict[str, dict] = {}

    for variant in selected:
        tasks = [(seed, ep) for seed in seeds for ep in range(episodes_per_seed)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_run_episode, variant, seed, ep, n_symbols, horizon, shift_step, run_id)
                for seed, ep in tasks
            ]
            episodes = [future.result() for future in futures]

        episodes.sort(key=lambda ep_rows: (ep_rows[0]["seed"], ep_rows[0]["episode"]))
        all_rows = [row for ep_rows in episodes for row in ep_rows]
        per_episode = [_episode_metrics(ep_rows) for ep_rows in episodes]

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"rule_shift_{variant}_{run_id}{batch_suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

        summaries[variant] = {
            "run_id": run_id,
            "batch_id": batch_id,
            "variant": variant,
            "episodes": len(episodes),
            "n_symbols": n_symbols,
            "horizon": effective_horizon,
            "shift_step": effective_shift,
            "pre_shift_accuracy": statistics.mean(m["pre_acc"] for m in per_episode),
            "post_shift_accuracy": statistics.mean(m["post_acc"] for m in per_episode),
            "repeated_error_mean": statistics.mean(m["repeated_error"] for m in per_episode),
            "recovery_steps_mean": statistics.mean(m["recovery_steps"] for m in per_episode),
            "total_reward_mean": statistics.mean(m["total_reward"] for m in per_episode),
            "trace_file": str(trace_path),
        }

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"rule_shift_summary_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
