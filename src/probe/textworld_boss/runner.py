from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
import statistics
import uuid
from pathlib import Path

from probe.textworld_boss.agents import TWBaselineAgent, TWProbe2Agent, TWProbe3Agent, TWProbe4Agent, TWProbe5Agent, TWProbeAgent, TWReflexionAgent
from probe.textworld_boss.env import clean_observation, make_game, start


VARIANTS = {
    "baseline_tw": TWBaselineAgent,
    "reflexion_tw": TWReflexionAgent,
    "probe_tw": TWProbeAgent,
    "probe2_tw": TWProbe2Agent,
    "probe3_tw": TWProbe3Agent,
    "probe4_tw": TWProbe4Agent,
    "probe5_tw": TWProbe5Agent,
}

TRACE_FIELDS = ["run_id", "variant", "seed", "step", "command", "reward", "score", "max_score", "won", "note"]


def _play(variant, game_file, seed, budget, run_id) -> dict:
    env = start(game_file)
    obs = clean_observation(env.reset())
    agent = VARIANTS[variant]()
    history: list[dict] = []
    rows: list[dict] = []
    won = False
    score = obs["score"]
    max_score = obs["max_score"]
    steps = 0

    for step in range(budget):
        command, note = agent.act(obs, history)
        game_state, reward, done = env.step(command)
        obs = clean_observation(game_state)
        score = obs["score"]
        won = bool(getattr(game_state, "won", False)) or score >= max_score
        steps = step + 1
        rows.append(
            {
                "run_id": run_id,
                "variant": variant,
                "seed": seed,
                "step": step,
                "command": command,
                "reward": float(reward),
                "score": score,
                "max_score": max_score,
                "won": won,
                "note": note,
            }
        )
        history.append({"cmd": command, "feedback": obs["description"][:120]})
        if done or won:
            break

    print(f"[{variant}] seed {seed}: won={won} score={score}/{max_score} steps={steps}", flush=True)
    return {"seed": seed, "variant": variant, "won": won, "score": score, "max_score": max_score, "steps": steps, "rows": rows}


def run_textworld(
    output_dir: Path,
    trace_dir: Path,
    seeds: list[int] | None = None,
    variant_names: list[str] | None = None,
    budget: int = 30,
    nb_rooms: int = 4,
    nb_objects: int = 6,
    quest_length: int = 4,
    batch_id: str | None = None,
) -> dict:
    run_id = uuid.uuid4().hex[:8]
    seeds = seeds if seeds is not None else list(range(10))
    selected = variant_names or list(VARIANTS.keys())
    workers = int(os.getenv("TEXTWORLD_MAX_WORKERS", "1"))

    games = {seed: make_game(seed, nb_rooms=nb_rooms, nb_objects=nb_objects, quest_length=quest_length) for seed in seeds}

    summaries: dict[str, dict] = {}
    for variant in selected:
        print(f"=== running {variant}: {len(seeds)} seeds, budget {budget}, {workers} workers ===", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_play, variant, games[seed], seed, budget, run_id) for seed in seeds]
            results = [future.result() for future in futures]

        results.sort(key=lambda r: r["seed"])
        all_rows = [row for r in results for row in r["rows"]]

        batch_suffix = f"_{batch_id}" if batch_id else ""
        trace_path = trace_dir / f"textworld_{variant}_{run_id}{batch_suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)

        summaries[variant] = {
            "run_id": run_id,
            "variant": variant,
            "games": len(results),
            "budget": budget,
            "quest_length": quest_length,
            "solve_rate": statistics.mean(1.0 if r["won"] else 0.0 for r in results),
            "mean_score_fraction": statistics.mean(r["score"] / r["max_score"] for r in results),
            "mean_steps_if_solved": statistics.mean([r["steps"] for r in results if r["won"]]) if any(r["won"] for r in results) else None,
            "trace_file": str(trace_path),
        }
        print(f"=== {variant} DONE: solve_rate {summaries[variant]['solve_rate']:.3f} ({sum(1 for r in results if r['won'])}/{len(results)}) ===", flush=True)

    batch_suffix = f"_{batch_id}" if batch_id else ""
    summary_path = output_dir / f"textworld_summary_{run_id}{batch_suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
