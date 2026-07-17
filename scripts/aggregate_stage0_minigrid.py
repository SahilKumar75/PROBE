"""Aggregate batched Stage 0 MiniGrid summary files."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.stage0.minigrid_runner import aggregate_stage0_minigrid_batches


def main() -> None:
    raw_files = os.getenv("STAGE0_SUMMARY_FILES", "")
    if not raw_files:
        raise SystemExit("STAGE0_SUMMARY_FILES is required")
    summary_files = [Path(item.strip()) for item in raw_files.split(",") if item.strip()]
    output_path = Path(os.getenv("STAGE0_AGGREGATE_OUTPUT", ROOT / "outputs" / "stage0_minigrid_aggregate.json"))
    result = aggregate_stage0_minigrid_batches(summary_files=summary_files, output_path=output_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
