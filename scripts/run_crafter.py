"""Run the Crafter external boss (Stage 4 external benchmark)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.crafter_boss.runner import run_crafter


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_crafter(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("CRAFTER_SEEDS")),
        variant_names=os.getenv("CRAFTER_VARIANTS", "").split(",") if os.getenv("CRAFTER_VARIANTS") else None,
        budget=int(os.getenv("CRAFTER_BUDGET", "60")),
        batch_id=os.getenv("CRAFTER_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
