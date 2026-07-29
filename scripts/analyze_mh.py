from __future__ import annotations

import csv
import glob
import re
from collections import Counter, defaultdict


def load(variant: str):
    rows = []
    for path in glob.glob(f"traces/minihack_{variant}_*mhc*.csv"):
        with open(path, newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def per_episode(rows):
    eps = defaultdict(list)
    for r in rows:
        eps[(r["run_id"], r["seed"])].append(r)
    for k in eps:
        eps[k].sort(key=lambda r: int(r["step"]))
    return eps


def summarize(variant: str):
    rows = load(variant)
    if not rows:
        print(f"{variant}: no traces found")
        return
    eps = per_episode(rows)
    actions = Counter(r["action"] for r in rows)
    solved, failed = [], []
    for k, ep in eps.items():
        won = any(float(r["reward"]) > 0 for r in ep)
        (solved if won else failed).append(ep)
    print(f"\n===== {variant}  episodes={len(eps)}  solved={len(solved)} =====")
    print("top actions:", actions.most_common(6))
    mean_steps = sum(len(ep) for ep in eps.values()) / len(eps)
    print(f"mean steps/ep: {mean_steps:.0f}")

    def final_note(ep):
        for r in reversed(ep):
            if r["note"].strip():
                return r["note"].strip()
        return ""

    print("--- SOLVED final notes (up to 3) ---")
    for ep in solved[:3]:
        print("  ", final_note(ep)[:220])
    print("--- FAILED final notes (up to 3) ---")
    for ep in failed[:3]:
        print("  ", final_note(ep)[:220])

    keys = ["water", "boulder", "bridge", "push", "river", "rule", "block", "fill"]
    notetext = " ".join(r["note"].lower() for r in rows)
    hits = {k: len(re.findall(k, notetext)) for k in keys}
    print("mechanic word hits in notes:", hits)


for v in ["probe_mh", "reflexion_mh"]:
    summarize(v)
