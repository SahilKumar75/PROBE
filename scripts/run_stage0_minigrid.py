"""Run the Stage 0 external MiniGrid evaluation."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.stage0.minigrid_runner import run_stage0_minigrid


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_stage0_minigrid(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("STAGE0_BATCH_SEEDS")),
        episode_ids=_parse_int_list(os.getenv("STAGE0_BATCH_EPISODES")),
        variant_names=os.getenv("STAGE0_VARIANTS", "").split(",") if os.getenv("STAGE0_VARIANTS") else None,
        batch_id=os.getenv("STAGE0_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
