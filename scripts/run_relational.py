"""Run the relational world internal boss (Boss I5)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.relational.runner import run_relational


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_relational(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("RELATIONAL_SEEDS")),
        episodes_per_seed=int(os.getenv("RELATIONAL_EPISODES", "5")),
        variant_names=os.getenv("RELATIONAL_VARIANTS", "").split(",") if os.getenv("RELATIONAL_VARIANTS") else None,
        horizon=int(os.getenv("RELATIONAL_HORIZON", "24")),
        batch_id=os.getenv("RELATIONAL_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
