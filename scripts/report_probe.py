"""Print a Stage 0 comparison report for the latest probe_agent run."""

from __future__ import annotations

import collections
import csv
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SUCCESS = 0.59


def main() -> None:
    traces = sorted(
        (ROOT / "traces").glob("stage0_minigrid_probe_agent_*.csv"),
        key=os.path.getmtime,
    )
    if not traces:
        print("no probe_agent trace found; run the probe agent first")
        sys.exit(1)

    trace = traces[-1]
    rows = list(csv.DictReader(trace.open()))
    episodes: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for row in rows:
        episodes[(row["seed"], row["episode_id"])].append(row)

    total = len(episodes)
    successes = sum(1 for steps in episodes.values() if steps[-1]["success"] == "True")
    actions = collections.Counter(row["chosen_action"] for row in rows)
    blocked_done = sum(1 for row in rows if "overrode_done=True" in row["notes"])

    failures: collections.Counter = collections.Counter()
    for steps in episodes.values():
        last = steps[-1]
        if last["success"] == "True":
            continue
        if last["truncated"] == "True":
            failures["timeout"] += 1
        elif last["chosen_action"] == "done":
            failures["premature_done"] += 1
        else:
            failures["other"] += 1

    print(f"trace: {trace.name}")
    print(f"episodes: {total}")
    print(f"PROBE success: {successes}/{total} = {successes / total:.3f}   (plain baseline: {BASELINE_SUCCESS})")
    print(f"failures: {dict(failures)}")
    print(f"actions: {dict(actions)}")
    print(f"done blocked by verify gate: {blocked_done}")


if __name__ == "__main__":
    main()
