"""Boss I7: stress regression suite. Re-run every internal boss at small scale and confirm PROBE still beats the baseline on each primary metric."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.competing.runner import run_competing
from probe.mixed.runner import run_mixed
from probe.multifactor.runner import run_multifactor
from probe.probe_progress.runner import run_probe_progress
from probe.relational.runner import run_relational
from probe.rule_shift.runner import run_rule_shift


def main() -> None:
    episodes = int(os.getenv("REGRESSION_EPISODES", "1"))
    outputs, traces = ROOT / "outputs", ROOT / "traces"
    common = {"output_dir": outputs, "trace_dir": traces, "episodes_per_seed": episodes, "batch_id": "regress"}

    checks = []

    r = run_multifactor(**common)["variants"]
    checks.append(("I1 multifactor", "late_accuracy", r["baseline_mf"]["late_accuracy"], r["probe_mf"]["late_accuracy"]))

    r = run_competing(**common)["variants"]
    checks.append(("I2 competing", "disambiguating_accuracy", r["baseline_ch"]["disambiguating_accuracy"], r["probe_ch"]["disambiguating_accuracy"]))

    r = run_rule_shift(**common)["variants"]
    checks.append(("I3 rule_shift", "pre_shift_accuracy", r["baseline_rule"]["pre_shift_accuracy"], r["probe_rule"]["pre_shift_accuracy"]))

    r = run_probe_progress(**common)["variants"]
    checks.append(("I4 probe_progress", "reward_per_step", r["baseline_pp"]["reward_per_step"], r["probe_pp"]["reward_per_step"]))

    r = run_relational(**common)["variants"]
    checks.append(("I5 relational", "overall_accuracy", r["baseline_rel"]["overall_accuracy"], r["probe_rel"]["overall_accuracy"]))

    r = run_mixed(**common)["variants"]
    checks.append(("I6 mixed", "post_shift_accuracy", r["baseline_mix"]["post_shift_accuracy"], r["probe_mix"]["post_shift_accuracy"]))

    print(f"{'boss':20} {'metric':26} {'base':>7} {'probe':>7}  verdict")
    passed = 0
    for name, metric, base, probe in checks:
        ok = probe >= base
        passed += 1 if ok else 0
        print(f"{name:20} {metric:26} {base:7.3f} {probe:7.3f}  {'PASS' if ok else 'REGRESSION'}")
    print(f"\nregression suite: {passed}/{len(checks)} bosses PROBE >= baseline")


if __name__ == "__main__":
    main()
