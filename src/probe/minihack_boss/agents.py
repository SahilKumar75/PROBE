from __future__ import annotations

import re

from probe.rule_shift.agents import _default_client, _extract_json


TIPS = (
    "The map uses NetHack symbols: @ is you, . is floor, # is a corridor, | and - are walls, "
    "> is the downstairs you usually need to reach, + is a door, and letters are creatures. "
    "Move toward your goal one step at a time and use the compass directions."
)


def _numbered(actions: list[str]) -> str:
    return "\n".join(f"{i}: {a}" for i, a in enumerate(actions))


def _select(text: str, actions: list[str]) -> int:
    match = re.search(r"\d+", text or "")
    if match:
        idx = int(match.group())
        if 0 <= idx < len(actions):
            return idx
    low = (text or "").lower()
    for i, a in enumerate(actions):
        if a.lower() in low:
            return i
    return 0


def _recent(history: list[dict], window: int = 8) -> list[str]:
    return [h["action"] for h in history[-window:]]


class MiniHackBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, actions: list[str], history: list[dict]) -> tuple[int, str]:
        system = "You play a NetHack level. Reach the goal. Reply with only the number of the action."
        prompt = (
            f"Message: {obs['message'] or 'none'}\n"
            f"Screen:\n{obs['screen']}\n\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(actions)}\n"
            "Reply with the number of the best action."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _select(text, actions), ""


class MiniHackProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet; I need to locate the goal and a path to it"

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, actions: list[str], history: list[dict]) -> tuple[int, str]:
        system = (
            "You play a NetHack level while keeping an explicit running belief about the layout, where the goal is, "
            "and your plan to reach it. Update the belief when the screen contradicts it. Reply only with a JSON object."
        )
        prompt = (
            f"Message: {obs['message'] or 'none'}\n"
            f"Screen:\n{obs['screen']}\n\n"
            f"Your current belief and plan: {self.belief}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(actions)}\n"
            'Reply with one JSON object with keys: "belief" (a short updated statement of the layout, where the goal '
            'is, and your next move) and "action_number" (the integer of the action to take).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        number = parsed.get("action_number")
        if isinstance(number, int) and 0 <= number < len(actions):
            index = number
        else:
            index = _select(text, actions)
        return index, f"belief={self.belief[:150]}"
