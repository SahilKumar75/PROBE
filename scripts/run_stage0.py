"""Run the Stage 0 internal boss evaluation."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.stage0.runner import run_stage0


def main() -> None:
    result = run_stage0(
        output_dir=ROOT / "outputs",
        trace_dir=ROOT / "traces",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
