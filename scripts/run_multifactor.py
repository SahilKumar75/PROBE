"""Run the multi-factor rule internal boss (Boss I1)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.multifactor.runner import run_multifactor


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def _opt_int(name: str) -> int | None:
    raw = os.getenv(name)
    return int(raw) if raw else None


def main() -> None:
    result = run_multifactor(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("MULTIFACTOR_SEEDS")),
        episodes_per_seed=int(os.getenv("MULTIFACTOR_EPISODES", "5")),
        variant_names=os.getenv("MULTIFACTOR_VARIANTS", "").split(",") if os.getenv("MULTIFACTOR_VARIANTS") else None,
        n_colors=int(os.getenv("MULTIFACTOR_COLORS", "3")),
        n_shapes=int(os.getenv("MULTIFACTOR_SHAPES", "2")),
        n_keys=int(os.getenv("MULTIFACTOR_KEYS", "3")),
        horizon=_opt_int("MULTIFACTOR_HORIZON"),
        batch_id=os.getenv("MULTIFACTOR_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
