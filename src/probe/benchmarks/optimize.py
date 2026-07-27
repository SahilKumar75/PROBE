from __future__ import annotations

import statistics
import time

from probe.bench_induction.env import InductionEnv, LEVELS as INDUCTION_LEVELS
from probe.bench_adaptation.env import AdaptationEnv, LEVELS as ADAPTATION_LEVELS
from probe.benchmarks.solvers import SOLVERS


def _make_env(benchmark: str, level: str, seed: int):
    if benchmark == "induction":
        return InductionEnv(level=level, seed=seed)
    return AdaptationEnv(level=level, seed=seed)


def _run_episode(env, solver) -> dict:
    solver.reset()
    obs = env.reset()
    rewards: list[int] = []
    segments: list[int] = []
    mem_max = 0
    start = time.perf_counter()
    for _ in range(env.horizon):
        key = solver.act(obs)
        next_obs, reward, done, info = env.step(key)
        solver.update(info["cue"], key, reward)
        rewards.append(reward)
        segments.append(info.get("segment", 0))
        mem_max = max(mem_max, solver.memory())
        obs = next_obs
        if done:
            break
    elapsed = time.perf_counter() - start

    n = len(rewards)
    tail = rewards[max(0, n - n // 4):]
    overall = statistics.mean(rewards) if rewards else 0.0
    asymptotic = statistics.mean(tail) if tail else 0.0
    wrong = sum(1 for r in rewards if r == 0)
    return {
        "overall_acc": overall,
        "asymptotic_acc": asymptotic,
        "wrong": wrong,
        "memory_max": mem_max,
        "steps": n,
        "us_per_step": 1e6 * elapsed / n if n else 0.0,
    }


def evaluate(benchmark: str, level: str, solver_name: str, seeds: int) -> dict:
    levels = INDUCTION_LEVELS if benchmark == "induction" else ADAPTATION_LEVELS
    probe_env = _make_env(benchmark, level, 0)
    n_cues = getattr(probe_env, "n_cues", None) or getattr(probe_env, "n_combos")
    n_keys = len(probe_env.keys)
    segments = 1 if benchmark == "induction" else (probe_env.n_shifts + 1)
    wrong_bound = segments * n_cues * (n_keys - 1)
    memory_bound = n_cues * n_keys

    records = []
    for seed in range(seeds):
        env = _make_env(benchmark, level, seed)
        solver = SOLVERS[solver_name](seed=seed)
        records.append(_run_episode(env, solver))

    def mean(field):
        return statistics.mean(r[field] for r in records)

    return {
        "benchmark": benchmark,
        "level": level,
        "solver": solver_name,
        "n_cues": n_cues,
        "n_keys": n_keys,
        "overall_acc": mean("overall_acc"),
        "asymptotic_acc": mean("asymptotic_acc"),
        "wrong": mean("wrong"),
        "wrong_bound": wrong_bound,
        "memory_max": mean("memory_max"),
        "memory_bound": memory_bound,
        "us_per_step": mean("us_per_step"),
    }


def report(seeds: int = 200) -> list[dict]:
    rows = []
    for benchmark, levels in (("induction", INDUCTION_LEVELS), ("adaptation", ADAPTATION_LEVELS)):
        for level in levels:
            for solver_name in SOLVERS:
                rows.append(evaluate(benchmark, level, solver_name, seeds))
    return rows


def _assertions(rows: list[dict]) -> list[tuple[str, bool, str]]:
    idx = {(r["benchmark"], r["level"], r["solver"]): r for r in rows}
    combos = sorted({(r["benchmark"], r["level"]) for r in rows})
    checks = []
    for benchmark, level in combos:
        p = idx[(benchmark, level, "probe_core")]
        g = idx[(benchmark, level, "greedy_history")]
        m = idx[(benchmark, level, "memoryless")]
        tag = f"{benchmark}/{level}"
        checks.append((f"{tag}: exploration <= elimination optimum", p["wrong"] <= p["wrong_bound"] + 1e-6,
                       f"wrong={p['wrong']:.1f} bound={p['wrong_bound']}"))
        checks.append((f"{tag}: memory <= O(cues*keys)", p["memory_max"] <= p["memory_bound"] + 1e-6,
                       f"mem={p['memory_max']:.1f} bound={p['memory_bound']}"))
        dominates = p["overall_acc"] >= g["overall_acc"] - 1e-9 and g["overall_acc"] >= m["overall_acc"] - 1e-9
        checks.append((f"{tag}: probe_core dominates baselines", dominates,
                       f"probe={p['overall_acc']:.2f} greedy={g['overall_acc']:.2f} memoryless={m['overall_acc']:.2f}"))
    return checks


def main(seeds: int = 200) -> None:
    rows = report(seeds)
    header = f"{'benchmark':<11}{'level':<9}{'solver':<16}{'overall':>8}{'asympt':>8}{'wrong':>8}{'bound':>7}{'mem':>7}{'membnd':>8}{'us/step':>9}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['benchmark']:<11}{r['level']:<9}{r['solver']:<16}"
            f"{r['overall_acc']:>8.3f}{r['asymptotic_acc']:>8.3f}"
            f"{r['wrong']:>8.1f}{r['wrong_bound']:>7d}{r['memory_max']:>7.1f}{r['memory_bound']:>8d}{r['us_per_step']:>9.2f}"
        )
    print("\nInvariants that must always hold (no API):")
    all_pass = True
    for name, ok, detail in _assertions(rows):
        all_pass = all_pass and ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({detail})")
    print("\nALL PASS" if all_pass else "\nSOME FAILED")

    weak = sorted((r for r in rows if r["solver"] == "probe_core"), key=lambda r: r["asymptotic_acc"])[:3]
    print("\nOptimization targets (lowest probe_core asymptotic accuracy, room to improve):")
    for r in weak:
        print(f"  {r['benchmark']}/{r['level']}: asymptotic={r['asymptotic_acc']:.3f} recovery cost wrong={r['wrong']:.1f}")


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
