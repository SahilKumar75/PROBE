from __future__ import annotations

import tempfile
from pathlib import Path

import textworld
from textworld import EnvInfos, GameOptions


INFOS = EnvInfos(
    admissible_commands=True,
    description=True,
    inventory=True,
    objective=True,
    won=True,
    lost=True,
    max_score=True,
    score=True,
)


def make_game(seed: int, nb_rooms: int = 4, nb_objects: int = 6, quest_length: int = 4) -> str:
    workdir = Path(tempfile.mkdtemp(prefix="twgame_"))
    options = GameOptions()
    options.nb_rooms = nb_rooms
    options.nb_objects = nb_objects
    options.quest_length = quest_length
    options.seeds = seed
    options.path = str(workdir / "game.z8")
    game_file, _ = textworld.make(options)
    return game_file


def start(game_file: str):
    return textworld.start(game_file, request_infos=INFOS)


def clean_observation(game_state) -> dict:
    return {
        "objective": (game_state.objective or "").strip(),
        "description": (game_state.feedback or game_state.description or "").strip(),
        "inventory": (game_state.inventory or "").strip(),
        "admissible": list(game_state.admissible_commands or []),
        "score": int(game_state.score or 0),
        "max_score": int(game_state.max_score or 1),
    }
