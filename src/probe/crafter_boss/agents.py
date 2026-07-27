from __future__ import annotations

import re

from probe.crafter_boss.env import ACTIONS
from probe.rule_shift.agents import _default_client, _extract_json


TIPS = (
    "Use 'do' to collect or attack whatever is directly in front of you, so move toward a resource first. "
    "Progression: collect wood, place_table, make_wood_pickaxe, collect stone, make_stone_pickaxe, place_furnace, "
    "collect coal and iron, make iron tools. Drink water and eat cows to keep vitals up."
)


def _numbered(actions: list[str]) -> str:
    return "\n".join(f"{i}: {a}" for i, a in enumerate(actions))


def _select(text: str, actions: list[str]) -> int:
    match = re.search(r"\d+", text)
    if match:
        index = int(match.group())
        if 0 <= index < len(actions):
            return index
    low = text.lower()
    for i, a in enumerate(actions):
        if a in low:
            return i
    return 0


def _recent(history: list[dict], window: int = 8) -> list[str]:
    return [h["action"] for h in history[-window:]]


class CrafterBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        system = "You play Crafter, a survival game. Unlock as many achievements as possible. Reply with only the number of the action."
        prompt = (
            f"Vitals: {obs['vitals']}\n"
            f"Inventory: {obs['resources']}\n"
            f"Achievements unlocked: {obs['achievements']}\n"
            f"Nearby: {obs['nearby']}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(ACTIONS)}\n"
            "Reply with the number of the best action."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _select(text, ACTIONS), ""


class CrafterProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet"

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        system = (
            "You play Crafter while keeping an explicit running belief about your situation and a plan through the "
            "achievement tech tree. Reply only with a JSON object."
        )
        prompt = (
            f"Vitals: {obs['vitals']}\n"
            f"Inventory: {obs['resources']}\n"
            f"Achievements unlocked: {obs['achievements']}\n"
            f"Nearby: {obs['nearby']}\n"
            f"Your current belief and plan: {self.belief}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(ACTIONS)}\n"
            'Reply with one JSON object with keys: "belief" (a short updated statement of your situation and your '
            'current next sub goal in the tech tree), "action_number" (the integer of the action to take).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        number = parsed.get("action_number")
        if isinstance(number, int) and 0 <= number < len(ACTIONS):
            index = number
        else:
            index = _select(text, ACTIONS)
        return index, f"belief={self.belief[:150]}"


class CrafterReflexionAgent:
    def __init__(self, client=None):
        self._client = client
        self.reflection = "none yet"

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        system = (
            "You play Crafter. Reason briefly, keep a short running self reflection of what you have learned about the "
            "game, then choose an action. Reply only with a JSON object."
        )
        prompt = (
            f"Vitals: {obs['vitals']}\n"
            f"Inventory: {obs['resources']}\n"
            f"Achievements unlocked: {obs['achievements']}\n"
            f"Nearby: {obs['nearby']}\n"
            f"Your running self reflection: {self.reflection}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(ACTIONS)}\n"
            'Reply with one JSON object with keys: "thought" (brief reasoning), "reflection" (your updated lesson), '
            '"action_number" (the integer of the action to take).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        reflection = parsed.get("reflection")
        if isinstance(reflection, str) and reflection.strip():
            self.reflection = reflection.strip()[:400]
        number = parsed.get("action_number")
        if isinstance(number, int) and 0 <= number < len(ACTIONS):
            index = number
        else:
            index = _select(text, ACTIONS)
        return index, f"reflection={self.reflection[:150]}"
