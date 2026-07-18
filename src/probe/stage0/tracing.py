"""Trace logging helpers for Stage 0 runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path


TRACE_FIELDS = [
    "run_id",
    "variant_name",
    "env_id",
    "seed",
    "episode_id",
    "step_id",
    "mission_text",
    "raw_observation",
    "structured_observation",
    "chosen_action",
    "action_source",
    "reward",
    "done",
    "truncated",
    "cumulative_reward",
    "step_count",
    "success",
    "failure_reason",
    "notes",
]


@dataclass
class TraceRow:
    run_id: str
    variant_name: str
    env_id: str
    seed: int
    episode_id: int
    step_id: int
    mission_text: str
    raw_observation: str
    structured_observation: str
    chosen_action: str
    action_source: str
    reward: float
    done: bool
    truncated: bool
    cumulative_reward: float
    step_count: int
    success: bool
    failure_reason: str
    notes: str

    def as_csv_row(self) -> dict:
        return asdict(self)


class TraceLogger:
    """Append-only CSV logger for per-step traces."""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write_rows(self, rows: list[TraceRow]) -> None:
        file_exists = self.output_path.exists()
        with self.output_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRACE_FIELDS)
            if not file_exists:
                writer.writeheader()
            for row in rows:
                writer.writerow(row.as_csv_row())


def dump_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
