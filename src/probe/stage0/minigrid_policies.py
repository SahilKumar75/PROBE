"""Baseline policies for MiniGrid Stage 0."""

from __future__ import annotations

import random

import os

from probe.stage0.groq_client import GroqClient
from probe.stage0.minigrid_env import readable_observation
from probe.stage0.ollama_client import OllamaClient
from probe.stage0.openrouter_client import OpenRouterClient


def random_minigrid_policy(obs: dict) -> int:
    _ = obs
    return random.randint(0, 6)


def heuristic_minigrid_policy(obs: dict, history: list[dict]) -> int:
    """Simple rule-based baseline for Stage 0 MiniGrid.

    Strategy:
    - move forward if the front cell contains an object
    - otherwise sweep by turning to search
    - occasionally move forward when the front cell is empty
    """
    _ = history
    image = obs["image"]
    front_cell = image[3][6]
    object_idx = int(front_cell[0])

    # In MiniGrid encodings, non-zero object ids indicate something visible ahead.
    if object_idx not in (0, 1):  # not unseen and not empty
        return 2

    # If the front cell looks empty, sweep and occasionally advance.
    if random.random() < 0.3:
        return 2
    return random.choice((0, 1))


def llm_minigrid_policy(obs: dict, history: list[dict], client=None) -> int:
    """Real LLM-backed baseline using Groq or Ollama."""
    if client is None:
        if os.getenv("OPENROUTER_API_KEY"):
            client = OpenRouterClient()
        elif os.getenv("GROQ_API_KEY"):
            client = GroqClient()
        else:
            client = OllamaClient()
    recent_actions = [entry["action"] for entry in history[-5:]]
    system = (
        "You control an agent in a MiniGrid gridworld with a partial, forward facing view. "
        "Reply with exactly one action word and nothing else."
    )
    prompt = (
        "Actions: left (turn 90 degrees left), right (turn 90 degrees right), "
        "forward (move one cell forward), done (declare you have arrived).\n"
        "You succeed only by moving into a cell next to the target object named in the mission, then replying done. "
        "Replying done when you are not next to the target ends the episode as a failure. "
        "Replying toggle, pickup, or drop also ends the episode, so never use them.\n\n"
        f"{readable_observation(obs)}\n"
        f"Recent actions: {recent_actions}\n\n"
        "Reply with one action word: left, right, forward, or done."
    )
    text = client.generate_text(system_instruction=system, user_prompt=prompt).strip().lower()

    action_map = {
        "left": 0,
        "right": 1,
        "forward": 2,
        "pickup": 3,
        "drop": 4,
        "toggle": 5,
        "done": 6,
    }
    for token in text.split():
        cleaned = token.strip(".,!?:;'\"()[]*`").lower()
        if cleaned in action_map:
            return action_map[cleaned]
    return 2
