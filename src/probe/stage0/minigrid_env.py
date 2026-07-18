"""MiniGrid helpers for the external Stage 0 benchmark."""

from __future__ import annotations

import json

import gymnasium as gym
import minigrid  # noqa: F401
from minigrid.core.constants import IDX_TO_COLOR, IDX_TO_OBJECT


MINIGRID_ENV_ID = "MiniGrid-GoToObject-6x6-N2-v0"
ACTION_NAMES = {
    0: "left",
    1: "right",
    2: "forward",
    3: "pickup",
    4: "drop",
    5: "toggle",
    6: "done",
}
DIRECTION_NAMES = {0: "east", 1: "south", 2: "west", 3: "north"}
_HIDDEN_OBJECTS = {"unseen", "empty", "wall", "agent"}


def make_env():
    return gym.make(MINIGRID_ENV_ID)


def structured_observation(obs: dict) -> dict:
    image = obs["image"]
    front_cell = image[3][6]
    return {
        "mission": obs["mission"],
        "direction": int(obs["direction"]),
        "image_shape": list(image.shape),
        "visible_nonzero_cells": int((image != 0).sum()),
        "front_cell": front_cell.tolist(),
        "front_object": int(front_cell[0]),
        "front_color": int(front_cell[1]),
        "front_state": int(front_cell[2]),
    }


def raw_observation_text(obs: dict) -> str:
    serializable = {
        "direction": int(obs["direction"]),
        "mission": obs["mission"],
        "image": obs["image"].tolist(),
    }
    return json.dumps(serializable)


def parse_mission_target(mission: str) -> tuple[str, str]:
    tokens = mission.strip().rstrip(".").split()
    return tokens[-2], tokens[-1]


def target_directly_ahead(obs: dict) -> bool:
    image = obs["image"]
    agent_col = image.shape[0] // 2
    agent_row = image.shape[1] - 1
    front = image[agent_col][agent_row - 1]
    front_object = IDX_TO_OBJECT.get(int(front[0]), "")
    front_color = IDX_TO_COLOR.get(int(front[1]), "")
    target_color, target_type = parse_mission_target(obs["mission"])
    return front_object == target_type and front_color == target_color


def target_bearing(obs: dict) -> tuple[int, int] | None:
    image = obs["image"]
    agent_col = image.shape[0] // 2
    agent_row = image.shape[1] - 1
    target_color, target_type = parse_mission_target(obs["mission"])
    for col in range(image.shape[0]):
        for row in range(image.shape[1]):
            if (
                IDX_TO_OBJECT.get(int(image[col][row][0]), "") == target_type
                and IDX_TO_COLOR.get(int(image[col][row][1]), "") == target_color
            ):
                return agent_row - row, col - agent_col
    return None


def readable_observation(obs: dict) -> str:
    image = obs["image"]
    view_cols, view_rows = image.shape[0], image.shape[1]
    agent_col = view_cols // 2
    agent_row = view_rows - 1
    direction = int(obs["direction"])

    visible = []
    for col in range(view_cols):
        for row in range(view_rows):
            object_name = IDX_TO_OBJECT.get(int(image[col][row][0]), "unknown")
            if object_name in _HIDDEN_OBJECTS:
                continue
            color_name = IDX_TO_COLOR.get(int(image[col][row][1]), "unknown")
            forward = agent_row - row
            lateral = col - agent_col
            visible.append((f"{color_name} {object_name}", forward, lateral))

    ahead_name = IDX_TO_OBJECT.get(int(image[agent_col][agent_row - 1][0]), "unknown")

    lines = [
        f"Mission: {obs['mission']}.",
        f"You face {DIRECTION_NAMES.get(direction, direction)}.",
        f"The cell directly ahead is {ahead_name}.",
    ]

    if visible:
        described = []
        for name, forward, lateral in visible:
            if lateral == 0:
                side = ""
            elif lateral > 0:
                side = f" and {lateral} to your right"
            else:
                side = f" and {abs(lateral)} to your left"
            if forward > 0:
                described.append(f"a {name} {forward} ahead{side}")
            else:
                described.append(f"a {name} beside you{side}")
        lines.append("You can see " + "; ".join(described) + ".")
    else:
        lines.append(
            "You can see no objects ahead. Your view only shows what is in front of you, "
            "so the target may be behind you; turn to look around."
        )

    return " ".join(lines)
