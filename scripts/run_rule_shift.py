"""Run the rule-shift internal boss (BossI3)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.rule_shift.runner import run_rule_shift


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def _opt_int(name: str) -> int | None:
    raw = os.getenv(name)
    return int(raw) if raw else None


def main() -> None:
    result = run_rule_shift(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("RULE_SHIFT_SEEDS")),
        episodes_per_seed=int(os.getenv("RULE_SHIFT_EPISODES", "5")),
        variant_names=os.getenv("RULE_SHIFT_VARIANTS", "").split(",") if os.getenv("RULE_SHIFT_VARIANTS") else None,
        n_symbols=int(os.getenv("RULE_SHIFT_SYMBOLS", "3")),
        horizon=_opt_int("RULE_SHIFT_HORIZON"),
        shift_step=_opt_int("RULE_SHIFT_SHIFT"),
        batch_id=os.getenv("RULE_SHIFT_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
