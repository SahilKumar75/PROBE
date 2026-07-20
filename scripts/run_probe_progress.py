"""Run the probe-or-progress internal boss (Boss I4)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.probe_progress.runner import run_probe_progress


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_probe_progress(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("PROBE_PROGRESS_SEEDS")),
        episodes_per_seed=int(os.getenv("PROBE_PROGRESS_EPISODES", "5")),
        variant_names=os.getenv("PROBE_PROGRESS_VARIANTS", "").split(",") if os.getenv("PROBE_PROGRESS_VARIANTS") else None,
        horizon=int(os.getenv("PROBE_PROGRESS_HORIZON", "20")),
        batch_id=os.getenv("PROBE_PROGRESS_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
