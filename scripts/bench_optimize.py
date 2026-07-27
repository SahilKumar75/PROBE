"""Run the no API internal optimization harness (deterministic solvers, no LLM)."""

from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from probe.benchmarks.optimize import main


if __name__ == "__main__":
    main(int(os.getenv("BENCH_OPT_SEEDS", "300")))
