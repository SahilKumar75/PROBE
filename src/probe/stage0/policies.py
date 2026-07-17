"""Baseline policies for Stage 0."""

from __future__ import annotations

import random


def random_policy(obs: dict) -> str:
    """Return a uniformly random valid action."""
    _ = obs
    return random.choice(("move_left", "move_right"))


def plain_llm_agent(obs: dict, history: list[dict]) -> str:
    """Placeholder heuristic until the real LLM client is wired in."""
    _ = history
    if obs["target_here"]:
        return "move_left"
    if obs["position"] <= 1:
        return "move_right"
    return random_policy(obs)
