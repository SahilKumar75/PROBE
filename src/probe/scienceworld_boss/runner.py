"""Runner for the ScienceWorld boss (external #5).

One ScienceWorldEnv (one JVM) per process, reused across episodes via load().
py4j is not safe to share across threads, so this runner is serial; parallelism
comes from the chunked launcher (separate processes over disjoint variations),
the same pattern as TextWorld/tatsu and MiniHack/NLE.

Score is ScienceWorld's native 0-100 partial credit; solve = score 100. The
final score of an episode is the MAX score seen (the env can drop the score
after an irreversible mistake, but credit earned is credit earned).
"""

from __future__ import annotations

import csv
import json
import statistics
import uuid
from pathlib import Path

from scienceworld import ScienceWorldEnv

from probe.scienceworld_boss.agents import VARIANTS

TRACE_FIELDS = ["run_id", "variant", "task", "variation", "step", "command", "score", "done", "note"]


def _play(env, variant, task, variation, budget, run_id):
    env.load(task, variation, "easy", generateGoldPath=False)
    obs, info = env.reset()
    agent = VARIANTS[variant]()
    task_desc = env.get_task_description()
    history: list[dict] = []
    rows: list[dict] = []
    best = 0
    score = 0

    for step in range(budget):
        packed = {
            "task": task_desc,
            "obs": obs,
            "inventory": env.inventory(),
            "score": score,
        }
        command, note = agent.act(packed, history)
        obs, reward, done, info = env.step(command)
        score = max(0, int(info.get("score", 0)))
        best = max(best, score)
        rows.append({
            "run_id": run_id, "variant": variant, "task": task, "variation": variation,
            "step": step, "command": command, "score": score, "done": done, "note": note,
        })
        history.append({"cmd": command, "fb": (obs or "")[:80]})
        if done or score >= 100:
            break

    print(f"[{variant}] {task} var {variation}: best {best} steps {len(rows)}", flush=True)
    return {"task": task, "variation": variation, "variant": variant, "best": best,
            "solved": best >= 100, "steps": len(rows), "rows": rows}


def run_scienceworld(*, output_dir, trace_dir, tasks=None, variations=None,
                     variant_names=None, budget=35, batch_id=None) -> dict:
    run_id = uuid.uuid4().hex[:8]
    tasks = tasks or ["chemistry-mix", "change-the-state-of-matter-of"]
    selected = variant_names or list(VARIANTS.keys())

    env = ScienceWorldEnv("", envStepLimit=budget + 5)

    summaries: dict[str, dict] = {}
    for variant in selected:
        results = []
        for task in tasks:
            # the test-variation list is only valid after the task is loaded
            env.load(task, 0, "easy", generateGoldPath=False)
            variation_ids = variations if variations is not None else sorted(env.get_variations_test())[:10]
            max_var = env.get_max_variations(task)
            var_ids = [v for v in variation_ids if v < max_var] or [0]
            print(f"=== {variant} / {task}: {len(var_ids)} variations, budget {budget} ===", flush=True)
            for v in var_ids:
                results.append(_play(env, variant, task, v, budget, run_id))

        all_rows = [row for r in results for row in r["rows"]]
        suffix = f"_{batch_id}" if batch_id else ""
        trace_path = Path(trace_dir) / f"scienceworld_{variant}_{run_id}{suffix}.csv"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=TRACE_FIELDS)
            w.writeheader()
            w.writerows(all_rows)

        per_task = {}
        for task in tasks:
            tr = [r for r in results if r["task"] == task]
            if tr:
                per_task[task] = {
                    "mean_score": statistics.mean(r["best"] for r in tr),
                    "solve_rate": statistics.mean(1.0 if r["solved"] else 0.0 for r in tr),
                    "n": len(tr),
                }
        summaries[variant] = {
            "run_id": run_id, "variant": variant, "budget": budget,
            "mean_score": statistics.mean(r["best"] for r in results),
            "solve_rate": statistics.mean(1.0 if r["solved"] else 0.0 for r in results),
            "episodes": len(results), "per_task": per_task, "trace_file": str(trace_path),
        }
        print(f"=== {variant} DONE: mean score {summaries[variant]['mean_score']:.1f}, "
              f"solve {summaries[variant]['solve_rate']:.2f} ===", flush=True)

    suffix = f"_{batch_id}" if batch_id else ""
    summary_path = Path(output_dir) / f"scienceworld_summary_{run_id}{suffix}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as h:
        json.dump(summaries, h, indent=2)
    return {"run_id": run_id, "summary_file": str(summary_path), "variants": summaries}
