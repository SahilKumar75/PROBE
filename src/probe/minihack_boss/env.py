from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

import gymnasium as gym
import minihack  # noqa: F401  registers the MiniHack environments on import
import numpy as np


OBS_KEYS = ("tty_chars", "chars", "colors", "message", "blstats")


def make_env(env_id: str):
    return gym.make(env_id, observation_keys=OBS_KEYS)


def action_labels(env) -> list[str]:
    acts = getattr(env, "actions", None)
    if acts is None:
        acts = getattr(getattr(env, "unwrapped", env), "actions", None)
    return [getattr(a, "name", str(a)) for a in (acts or [])]


def _decode_message(obs: dict) -> str:
    msg = obs.get("message")
    if msg is None:
        return ""
    try:
        raw = bytes(int(c) for c in np.asarray(msg).ravel() if int(c) != 0)
        return raw.decode("ascii", "ignore").strip()
    except Exception:
        return ""


def _lines_from_grid(grid) -> str:
    lines = []
    for row in np.asarray(grid):
        lines.append("".join(chr(int(c)) for c in row).rstrip())
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def describe(obs: dict) -> dict:
    tty = obs.get("tty_chars")
    if tty is not None:
        screen = _lines_from_grid(tty)
    elif obs.get("chars") is not None:
        screen = _lines_from_grid(obs["chars"])
    else:
        screen = ""
    return {"screen": screen, "message": _decode_message(obs)}
