"""Run the ARC-AGI-3 boss (external #4), offline on the official ARCEngine games."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.arc_boss.runner import run_arc


def _ints(raw):
    return [int(x) for x in raw.split(",") if x.strip()] if raw else None


def _strs(raw):
    return [x.strip() for x in raw.split(",") if x.strip()] if raw else None


def main() -> None:
    result = run_arc(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        games=_strs(os.getenv("ARC_GAMES")),
        seeds=_ints(os.getenv("ARC_SEEDS")),
        variant_names=_strs(os.getenv("ARC_VARIANTS")),
        budget=int(os.getenv("ARC_BUDGET", "40")),
        batch_id=os.getenv("ARC_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
