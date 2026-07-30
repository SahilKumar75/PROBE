"""Offline glue to the official ARC-AGI-3 harness.

Uses the real arc_agi SDK in OFFLINE mode (no network, no key): an Arcade scans
our environment_files/ for games and a LocalEnvironmentWrapper loads each game
class from local source. Running on the official harness (rather than poking the
game objects directly) keeps the evaluation credible and identical in shape to
what the remote benchmark would do.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from arc_agi import Arcade, LocalEnvironmentWrapper, OperationMode

ENV_DIR = Path(__file__).resolve().parent / "environment_files"

_LOGGER = logging.getLogger("arc_boss")
_LOGGER.addHandler(logging.NullHandler())


def list_games() -> list[str]:
    arc = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(ENV_DIR))
    return [e.game_id for e in arc.get_environments()]


def make_env(game_id: str, seed: int = 0) -> LocalEnvironmentWrapper:
    """Return a fresh LocalEnvironmentWrapper for game_id (call reset() after)."""
    arc = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(ENV_DIR))
    info = next((e for e in arc.get_environments() if e.game_id == game_id), None)
    if info is None:
        raise ValueError(f"game {game_id!r} not found in {ENV_DIR}")
    # scorecard_id is only a tracking label offline; a fresh uuid is fine.
    return LocalEnvironmentWrapper(info, _LOGGER, str(uuid.uuid4()), seed=seed)
