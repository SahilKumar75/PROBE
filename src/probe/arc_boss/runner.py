"""Runner for the ARC-AGI-3 boss (external #4).

The ARCEngine example games have fixed levels, so an episode is deterministic
given the game; variance across seeds comes from the LLM's sampling. A seed is
therefore one independent LLM attempt at a fixed game, and solve_rate is a
pass@1 rate over the model's stochasticity. Report per game.

Like the other bosses this is serial per process (concurrency is done with the
chunked launcher), and it logs a full per-step trace plus a summary JSON.
"""

from __future__ import annotations

import csv
import json
import os
import statistics
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from arcengine import GameAction

from probe.arc_boss.agents import VARIANTS
from probe.arc_boss.env import make_env
from probe.arc_boss.interp import describe

TRACE_FIELDS = ["run_id", "variant", "game", "seed", "step", "action", "score", "state", "won", "note"]


def _play(variant, game_id, seed, budget, run_id) -> dict:
    env = make_env(game_id, seed=seed)
    frame = env.reset()
    agent = VARIANTS[variant]()
    history: list[dict] = []
    rows: list[dict] = []
    prev_small = None
    won = False
    score = 0
    state = "NOT_FINISHED"

    for step in range(budget):
        score = int(getattr(frame, "levels_completed", 0))
        state = str(getattr(frame, "state", "NOT_FINISHED"))
        won = "WIN" in state
        if won or "GAME_OVER" in state:
            break
        available = list(getattr(frame, "available_actions", [1, 2, 3, 4, 5, 6, 7]))
        obs_text, prev_small = describe(frame.frame, available, state, score, prev_small)

        if hasattr(agent, "observe_score"):
            agent.observe_score(score)
        action_id, coord, note = agent.act(obs_text, available, history)

        data = {"x": coord[0], "y": coord[1]} if (action_id == 6 and coord) else None
        frame = env.step(GameAction.from_id(action_id), data=data)

        new_score = int(getattr(frame, "levels_completed", 0))
        effect = _effect(prev_small, frame, new_score, score)
        history.append({"action": f"ACTION{action_id}", "effect": effect})
        rows.append({
            "run_id": run_id, "variant": variant, "game": game_id, "seed": seed,
            "step": step, "action": f"ACTION{action_id}", "score": new_score,
            "state": str(getattr(frame, "state", "")), "won": "WIN" in str(getattr(frame, "state", "")),
            "note": note,
        })

    # final read after the loop's last step
    score = int(getattr(frame, "levels_completed", score))
    won = "WIN" in str(getattr(frame, "state", state))
    print(f"[{variant}] {game_id} seed {seed}: won={won} score={score} steps={len(rows)}", flush=True)
    return {"seed": seed, "game": game_id, "variant": variant, "won": won, "score": score, "steps": len(rows), "rows": rows}


def _effect(prev_small, frame, new_score, old_score) -> str:
    if new_score > old_score:
        return f"score rose to {new_score}"
    try:
        from probe.arc_boss.interp import downsample, _to_grid
        cur = downsample(_to_grid(frame.frame))
        if prev_small is not None and cur.shape == prev_small.shape and int((cur != prev_small).sum()) == 0:
            return "NOTHING changed"
        return "grid changed"
    except Exception:
        return "grid changed"


def run_arc(*, output_dir, trace_dir, games=None, seeds=None, variant_names=None, budget=40, batch_id=None) -> dict:
    run_id = uuid.uuid4().hex[:8]
    games = games or ["simple_maze", "merge", "complex_maze"]
    seeds = seeds if seeds is not None else list(range(10))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("ARC_MAX_WORKERS", "1"))

    summaries: dict[str, dict] = {}
    for variant in selected:
        tasks = [(g, s) for g in games for s in seeds]
        print(f"=== running {variant}: {len(games)} games x {len(seeds)} seeds = {len(tasks)}, budget {budget}, {workers} workers ===", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_play, variant, g, s, budget, run_id) for g, s in tasks]
            results = [f.result() for f in futures]
        results.sort(key=lambda r: (r["game"], r["seed"]))
        all_rows = [row for r in results for row in r["rows"]]

        suffix = f"_{batch_id}" if batch_id else ""
        trace_path = Path(trace_dir) / f"arc_{variant}_{run_id}{suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=TRACE_FIELDS)
            w.writeheader(); w.writerows(all_rows)

        per_game = {}
        for g in games:
            gr = [r for r in results if r["game"] == g]
            per_game[g] = {"solve_rate": statistics.mean(1.0 if r["won"] else 0.0 for r in gr), "n": len(gr)}
        summaries[variant] = {
            "run_id": run_id, "variant": variant, "games": games, "n_per_game": len(seeds),
            "budget": budget, "solve_rate": statistics.mean(1.0 if r["won"] else 0.0 for r in results),
            "per_game": per_game, "trace_file": str(trace_path),
        }
        print(f"=== {variant} DONE: overall solve_rate {summaries[variant]['solve_rate']:.3f} | " + ", ".join(f"{g} {per_game[g]['solve_rate']:.2f}" for g in games) + " ===", flush=True)

    suffix = f"_{batch_id}" if batch_id else ""
    summary_path = Path(output_dir) / f"arc_summary_{run_id}{suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as h:
        json.dump(summaries, h, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
