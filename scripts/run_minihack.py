"""Run the MiniHack external boss (Stage 3). Linux only; see MINIHACK_CODESPACE.md."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.minihack_boss.runner import run_minihack


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_minihack(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        env_id=os.getenv("MINIHACK_ENV", "MiniHack-MazeWalk-9x9-v0"),
        seeds=_parse_int_list(os.getenv("MINIHACK_SEEDS")),
        variant_names=os.getenv("MINIHACK_VARIANTS", "").split(",") if os.getenv("MINIHACK_VARIANTS") else None,
        budget=int(os.getenv("MINIHACK_BUDGET", "50")),
        batch_id=os.getenv("MINIHACK_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
