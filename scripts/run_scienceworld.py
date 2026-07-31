"""Run the ScienceWorld boss (external #5)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.scienceworld_boss.runner import run_scienceworld


def _ints(raw):
    return [int(x) for x in raw.split(",") if x.strip()] if raw else None


def _strs(raw):
    return [x.strip() for x in raw.split(",") if x.strip()] if raw else None


def main() -> None:
    result = run_scienceworld(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        tasks=_strs(os.getenv("SW_TASKS")),
        variations=_ints(os.getenv("SW_VARS")),
        variant_names=_strs(os.getenv("SW_VARIANTS")),
        budget=int(os.getenv("SW_BUDGET", "35")),
        batch_id=os.getenv("SW_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
