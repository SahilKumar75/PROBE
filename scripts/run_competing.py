"""Run the competing hypotheses internal boss (Boss I2)."""

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


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_competing(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("COMPETING_SEEDS")),
        episodes_per_seed=int(os.getenv("COMPETING_EPISODES", "5")),
        variant_names=os.getenv("COMPETING_VARIANTS", "").split(",") if os.getenv("COMPETING_VARIANTS") else None,
        horizon=int(os.getenv("COMPETING_HORIZON", "30")),
        shift_step=int(os.getenv("COMPETING_SHIFT", "10")),
        batch_id=os.getenv("COMPETING_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
