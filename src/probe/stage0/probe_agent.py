from __future__ import annotations

import json
import os

from probe.stage0.groq_client import GroqClient
from probe.stage0.minigrid_env import (
    parse_mission_target,
    readable_observation,
    target_bearing,
    target_directly_ahead,
)
from probe.stage0.ollama_client import OllamaClient
from probe.stage0.openrouter_client import OpenRouterClient


ACTION_WORD_TO_IDX = {"left": 0, "right": 1, "forward": 2, "done": 6}
IDX_TO_ACTION_WORD = {0: "left", 1: "right", 2: "forward", 6: "done"}
TURN_ACTIONS = {0, 1}


def _approach_action(obs: dict) -> int:
    bearing = target_bearing(obs)
    if bearing is None:
        return 1
    forward, lateral = bearing
    if lateral > 0:
        return 1
    if lateral < 0:
        return 0
    if forward > 0:
        return 2
    return 1


def _default_client():
    if os.getenv("OPENROUTER_API_KEY"):
        return OpenRouterClient()
    if os.getenv("GROQ_API_KEY"):
        return GroqClient()
    return OllamaClient()


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _first_action_word(text: str) -> str:
    for token in text.lower().split():
        cleaned = token.strip(".,!?:;'\"()[]{}*`")
        if cleaned in ACTION_WORD_TO_IDX:
            return cleaned
    return "forward"


class ProbeAgent:
    def __init__(self, client=None, force_forward_after: int = 4):
        self._client = client
        self.belief = "unknown, target not yet located"
        self.recent_actions: list[str] = []
        self.force_forward_after = force_forward_after

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        verified_ahead = target_directly_ahead(obs)
        target_color, target_type = parse_mission_target(obs["mission"])
        ahead_status = "IS" if verified_ahead else "is NOT"
        system = (
            "You are PROBE, an agent that navigates a gridworld by keeping an explicit belief "
            "about where the target is and checking it before acting. Reply only with a JSON object."
        )
        prompt = (
            "Actions: left (turn 90 degrees left), right (turn 90 degrees right), "
            "forward (move one cell forward), done (declare you have arrived).\n"
            f"The cell directly ahead {ahead_status} the {target_color} {target_type}. "
            f"Choose done only when the cell directly ahead is the {target_color} {target_type}. "
            "If it is not, you have not arrived, so navigate with left, right, or forward. "
            "Your view shows only what is ahead; if the target is not visible it may be behind you, so turn to search.\n\n"
            f"{readable_observation(obs)}\n"
            f"Your previous belief about the target: {self.belief}\n"
            f"Your recent actions: {self.recent_actions[-6:]}\n\n"
            "Reply with one JSON object with these keys: "
            '"belief" (short phrase for where the target is relative to you), '
            '"contradiction" (short note if the latest view contradicts your previous belief, else none), '
            '"action" (one of left, right, forward, done).'
        )
        text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        parsed = _extract_json(text)

        self.belief = str(parsed.get("belief", self.belief))
        contradiction = str(parsed.get("contradiction", "none"))

        action_word = parsed.get("action")
        if not isinstance(action_word, str) or action_word.lower() not in ACTION_WORD_TO_IDX:
            action_word = _first_action_word(text)
        action = ACTION_WORD_TO_IDX.get(action_word.lower(), 2)

        overrode_done = False
        if action == 6 and not verified_ahead:
            action = _approach_action(obs)
            overrode_done = True

        forced_forward = False
        recent = self.recent_actions[-self.force_forward_after:]
        if (
            action in TURN_ACTIONS
            and len(recent) >= self.force_forward_after
            and all(entry in ("left", "right") for entry in recent)
        ):
            action = 2
            forced_forward = True

        self.recent_actions.append(IDX_TO_ACTION_WORD[action])

        note = (
            f"belief={self.belief} | contradiction={contradiction} | "
            f"verified_ahead={verified_ahead} | overrode_done={overrode_done} | "
            f"forced_forward={forced_forward}"
        )
        return action, note
