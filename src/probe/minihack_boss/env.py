from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

import gym
import minihack  # noqa: F401  registers the MiniHack environments on import
import numpy as np


OBS_KEYS = ("tty_chars", "chars", "colors", "message", "blstats")


def make_env(env_id: str, seed: int):
    env = gym.make(env_id, observation_keys=OBS_KEYS)
    try:
        env.seed(seed)
    except Exception:
        pass
    return env


def action_labels(env) -> list[str]:
    acts = getattr(env, "actions", None)
    if acts is None:
        acts = getattr(getattr(env, "unwrapped", env), "actions", None)
    labels = []
    for a in acts or []:
        labels.append(getattr(a, "name", str(a)))
    return labels


def _decode_message(obs: dict) -> str:
    msg = obs.get("message")
    if msg is None:
        return ""
    try:
        raw = bytes(int(c) for c in np.asarray(msg).ravel() if int(c) != 0)
        return raw.decode("ascii", "ignore").strip()
    except Exception:
        return ""


def describe(obs: dict) -> dict:
    tty = obs.get("tty_chars")
    lines: list[str] = []
    if tty is not None:
        for row in np.asarray(tty):
            lines.append("".join(chr(int(c)) for c in row).rstrip())
        while lines and not lines[-1].strip():
            lines.pop()
    return {"screen": "\n".join(lines), "message": _decode_message(obs)}
