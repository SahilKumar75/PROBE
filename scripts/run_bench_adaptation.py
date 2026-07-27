"""Run the non-stationary rule adaptation benchmark (internal, v2)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.bench_adaptation.runner import run_adaptation


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_adaptation(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("BENCH_SEEDS")),
        episodes_per_seed=int(os.getenv("BENCH_EPISODES", "1")),
        variant_names=os.getenv("BENCH_VARIANTS", "").split(",") if os.getenv("BENCH_VARIANTS") else None,
        level=os.getenv("BENCH_LEVEL", "hardest"),
        batch_id=os.getenv("BENCH_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
