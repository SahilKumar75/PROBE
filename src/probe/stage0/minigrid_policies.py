"""Baseline policies for MiniGrid Stage 0."""

from __future__ import annotations

import random

import os

from probe.stage0.groq_client import GroqClient
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
    recent_history = history[-2:]
    direction = int(obs["direction"])
    front_cell = obs["image"][3][6].tolist()
    prompt = (
        "You control an agent in MiniGrid.\n"
        "Choose exactly one action from this list: left, right, forward, pickup, drop, toggle, done.\n"
        "Return only the action word and nothing else.\n\n"
        f"Mission: {obs['mission']}\n"
        f"Direction: {direction}\n"
        f"Front cell encoding: {front_cell}\n"
        f"Visible grid shape: {list(obs['image'].shape)}\n"
        f"Recent history: {recent_history}\n"
    )
    system = (
        "You are selecting one valid MiniGrid action. "
        "Return only one word from: left, right, forward, pickup, drop, toggle, done."
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
    first_token = text.split()[0] if text else ""
    if first_token not in action_map:
        return 6
    return action_map[first_token]
