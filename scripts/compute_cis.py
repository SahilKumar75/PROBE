"""Recompute mean and 95 percent confidence intervals for every boss from the saved traces."""

from __future__ import annotations

import collections
import csv
import glob
import math
import os
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TR = ROOT / "traces"


def latest(pattern: str) -> str | None:
    files = sorted(glob.glob(str(TR / pattern)), key=os.path.getmtime)
    return files[-1] if files else None


def rows(path: str) -> list[dict]:
    return list(csv.DictReader(open(path)))


def group(path: str, keys: tuple[str, ...]) -> dict:
    d = collections.defaultdict(list)
    for r in rows(path):
        d[tuple(r[k] for k in keys)].append(r)
    return d


def mean_ci(vals: list[float]) -> tuple[float, float]:
    m = statistics.mean(vals)
    se = statistics.pstdev(vals) / math.sqrt(len(vals)) if len(vals) > 1 else 0.0
    return m, 1.96 * se


def gap(base: list[float], probe: list[float]) -> tuple[float, float, str]:
    bm, bh = mean_ci(base)
    pm, ph = mean_ci(probe)
    d = pm - bm
    sed = math.sqrt((bh / 1.96) ** 2 + (ph / 1.96) ** 2) if bh or ph else 0.0
    lo, hi = d - 1.96 * sed, d + 1.96 * sed
    return d, 1.96 * sed, ("significant" if (lo > 0 or hi < 0) else "ns")


def phase_vals(ep, phase, third=False):
    out = []
    for steps in ep.values():
        rs = [int(r["reward"]) for r in steps if r.get("phase") == phase]
        if not rs:
            continue
        if third:
            rs = rs[-max(1, len(rs) // 3):]
        out.append(sum(rs) / len(rs))
    return out


def frac_vals(ep, third=None):
    out = []
    for steps in ep.values():
        rs = [int(r["reward"]) for r in steps]
        if third == "early":
            rs = rs[: max(1, len(rs) // 3)]
        elif third == "late":
            rs = rs[-max(1, len(rs) // 3):]
        out.append(sum(rs) / len(rs))
    return out


def report(name, base, probe):
    bm, bh = mean_ci(base)
    pm, ph = mean_ci(probe)
    d, dh, sig = gap(base, probe)
    print(f"{name:34} base {bm:.3f}+/-{bh:.3f}  probe {pm:.3f}+/-{ph:.3f}  gap {d:+.3f}+/-{dh:.3f} [{d-dh:+.3f},{d+dh:+.3f}] {sig}")


def main():
    # I1 multifactor
    b = group(latest("multifactor_baseline_mf_*mf1*.csv"), ("seed", "episode"))
    p = group(latest("multifactor_probe_mf_*mf1*.csv"), ("seed", "episode"))
    report("I1 multifactor overall", frac_vals(b), frac_vals(p))
    report("I1 multifactor asymptote", frac_vals(b, "late"), frac_vals(p, "late"))

    # I2 competing
    b = group(latest("competing_baseline_ch_*ch1*.csv"), ("seed", "episode"))
    p = group(latest("competing_probe_ch_*ch1*.csv"), ("seed", "episode"))
    report("I2 competing ambiguous", phase_vals(b, "ambiguous"), phase_vals(p, "ambiguous"))
    report("I2 competing disambiguating", phase_vals(b, "disambiguating"), phase_vals(p, "disambiguating"))
    report("I2 competing disambig late", phase_vals(b, "disambiguating", True), phase_vals(p, "disambiguating", True))

    # I3 rule shift, three sizes
    for size in ("ci3", "ci6", "ci9"):
        b = group(latest(f"rule_shift_baseline_rule_*{size}*.csv"), ("seed", "episode"))
        p = group(latest(f"rule_shift_probe_rule_*{size}*.csv"), ("seed", "episode"))
        report(f"I3 rule shift {size} pre", phase_vals(b, "pre"), phase_vals(p, "pre"))
        report(f"I3 rule shift {size} post", phase_vals(b, "post"), phase_vals(p, "post"))

    # I4 probe or progress
    b = group(latest("probe_progress_baseline_pp_*pp1*.csv"), ("seed", "episode"))
    p = group(latest("probe_progress_probe_pp_*pp1*.csv"), ("seed", "episode"))
    rps = lambda ep: [sum(float(r["reward"]) for r in s) / len(s) for s in ep.values()]
    report("I4 probe or progress reward/step", rps(b), rps(p))

    # I5 relational
    b = group(latest("relational_baseline_rel_*rel1*.csv"), ("seed", "episode"))
    p = group(latest("relational_probe_rel_*rel1*.csv"), ("seed", "episode"))
    report("I5 relational overall", frac_vals(b), frac_vals(p))
    report("I5 relational early", frac_vals(b, "early"), frac_vals(p, "early"))
    report("I5 relational asymptote", frac_vals(b, "late"), frac_vals(p, "late"))

    # I6 mixed
    b = group(latest("mixed_baseline_mix_*mix1*.csv"), ("seed", "episode"))
    p = group(latest("mixed_probe_mix_*mix1*.csv"), ("seed", "episode"))
    report("I6 mixed pre", phase_vals(b, "pre"), phase_vals(p, "pre"))
    report("I6 mixed post", phase_vals(b, "post"), phase_vals(p, "post"))
    report("I6 mixed post late", phase_vals(b, "post", True), phase_vals(p, "post", True))

    # External TextWorld (per game solved)
    b = group(latest("textworld_baseline_tw_*tw1*.csv"), ("seed",))
    p = group(latest("textworld_probe_tw_*tw1*.csv"), ("seed",))
    solved = lambda ep: [1.0 if any(r["won"] == "True" for r in s) else 0.0 for s in ep.values()]
    report("TextWorld solve rate", solved(b), solved(p))

    # External Crafter (max achievements per seed)
    b = group(latest("crafter_baseline_cf_*cf1*.csv"), ("seed",))
    p = group(latest("crafter_probe_cf_*cf1*.csv"), ("seed",))
    ach = lambda ep: [max(int(r["achievements"]) for r in s) for s in ep.values()]
    report("Crafter mean achievements", ach(b), ach(p))


if __name__ == "__main__":
    main()
