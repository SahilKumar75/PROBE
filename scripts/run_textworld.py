"""Run the TextWorld external boss (Stage 1 external benchmark)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.textworld_boss.runner import run_textworld


def _parse_int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    result = run_textworld(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
        seeds=_parse_int_list(os.getenv("TEXTWORLD_SEEDS")),
        variant_names=os.getenv("TEXTWORLD_VARIANTS", "").split(",") if os.getenv("TEXTWORLD_VARIANTS") else None,
        budget=int(os.getenv("TEXTWORLD_BUDGET", "30")),
        nb_rooms=int(os.getenv("TEXTWORLD_ROOMS", "4")),
        nb_objects=int(os.getenv("TEXTWORLD_OBJECTS", "6")),
        quest_length=int(os.getenv("TEXTWORLD_QUEST", "4")),
        batch_id=os.getenv("TEXTWORLD_BATCH_ID"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
