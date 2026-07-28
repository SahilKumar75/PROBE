from __future__ import annotations

import re

from probe.rule_shift.agents import _default_client, _extract_json


TIPS = (
    "The map uses NetHack symbols: @ is you, . is floor, # is a corridor, | and - are walls, "
    "> is the downstairs you usually need to reach, + is a door, } is lava or water, "
    "{ is a fountain, and letters are creatures. "
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
        self.blocked: dict[str, set[int]] = {}
        self.prev_screen: str | None = None
        self.prev_key: str | None = None
        self.prev_index: int | None = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, actions: list[str], history: list[dict]) -> tuple[int, str]:
        screen = obs["screen"]
        key = screen[:400]
        if self.prev_screen is not None and screen == self.prev_screen and self.prev_index is not None:
            self.blocked.setdefault(self.prev_key, set()).add(self.prev_index)
        blocked = self.blocked.setdefault(key, set())
        avoid = sorted(actions[i] for i in blocked if i < len(actions))

        system = "You play a NetHack level. Reach the goal. Reply with only the number of the action."
        prompt = (
            f"Message: {obs['message'] or 'none'}\n"
            f"Screen:\n{screen}\n\n"
            f"Recent actions: {_recent(history)}\n"
            f"Directions that hit a wall from this exact spot (the view did not change): {avoid or 'none'}. "
            "Do not repeat those; if a direction does not move you, it is a wall, so try a different one.\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(actions)}\n"
            "Reply with the number of the best action."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        index = _select(text, actions)
        if index in blocked:
            untried = [i for i in range(len(actions)) if i not in blocked]
            if untried:
                index = untried[0]
        self.prev_screen = screen
        self.prev_key = key
        self.prev_index = index
        return index, ""


class MiniHackReflexionAgent:
    def __init__(self, client=None):
        self._client = client
        self.reflection = "none yet"
        self.blocked: dict[str, set[int]] = {}
        self.prev_screen: str | None = None
        self.prev_key: str | None = None
        self.prev_index: int | None = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, actions: list[str], history: list[dict]) -> tuple[int, str]:
        screen = obs["screen"]
        key = screen[:400]
        if self.prev_screen is not None and screen == self.prev_screen and self.prev_index is not None:
            self.blocked.setdefault(self.prev_key, set()).add(self.prev_index)
        blocked = self.blocked.setdefault(key, set())
        avoid = sorted(actions[i] for i in blocked if i < len(actions))

        system = (
            "You play a NetHack level. Reason briefly, keep a short running self reflection of what you have learned "
            "about this level, then choose an action. Reply only with a JSON object."
        )
        prompt = (
            f"Message: {obs['message'] or 'none'}\n"
            f"Screen:\n{screen}\n\n"
            f"Your running self reflection: {self.reflection}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Directions that hit a wall from this exact spot (the view did not change): {avoid or 'none'}. "
            "Do not repeat those; if a direction does not move you, it is a wall, so try a different one.\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(actions)}\n"
            'Reply with one JSON object with keys: "thought" (brief reasoning), "reflection" (your updated lesson '
            'about this level), and "action_number" (the integer of the action to take).'
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
        if isinstance(number, int) and 0 <= number < len(actions):
            index = number
        else:
            index = _select(text, actions)

        if index in blocked:
            untried = [i for i in range(len(actions)) if i not in blocked]
            if untried:
                index = untried[0]

        self.prev_screen = screen
        self.prev_key = key
        self.prev_index = index
        return index, f"reflection={self.reflection[:150]}"


class MiniHackProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet; I need to locate the goal and a path to it"
        self.blocked: dict[str, set[int]] = {}
        self.prev_screen: str | None = None
        self.prev_key: str | None = None
        self.prev_index: int | None = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, actions: list[str], history: list[dict]) -> tuple[int, str]:
        screen = obs["screen"]
        key = screen[:400]
        if self.prev_screen is not None and screen == self.prev_screen and self.prev_index is not None:
            self.blocked.setdefault(self.prev_key, set()).add(self.prev_index)
        blocked = self.blocked.setdefault(key, set())
        avoid = sorted(actions[i] for i in blocked if i < len(actions))

        system = (
            "You play a NetHack level while keeping an explicit running belief about the layout, where the goal is, "
            "and your plan to reach it. Update the belief when the screen contradicts it. Reply only with a JSON object."
        )
        prompt = (
            f"Message: {obs['message'] or 'none'}\n"
            f"Screen:\n{screen}\n\n"
            f"Your current belief and plan: {self.belief}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Directions that hit a wall from this exact spot (the view did not change): {avoid or 'none'}. "
            "Do not repeat those; if a direction does not move you, it is a wall, so try a different one.\n"
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

        if index in blocked:
            untried = [i for i in range(len(actions)) if i not in blocked]
            if untried:
                index = untried[0]

        self.prev_screen = screen
        self.prev_key = key
        self.prev_index = index
        return index, f"belief={self.belief[:150]}"
