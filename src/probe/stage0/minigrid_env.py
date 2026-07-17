"""MiniGrid helpers for the external Stage 0 benchmark."""

from __future__ import annotations

import json

import gymnasium as gym
import minigrid  # noqa: F401


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
