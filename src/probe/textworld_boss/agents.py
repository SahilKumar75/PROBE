from __future__ import annotations

import re

from probe.rule_shift.agents import _default_client, _extract_json


def _numbered(admissible: list[str]) -> str:
    return "\n".join(f"{index}: {command}" for index, command in enumerate(admissible))


def _select(text: str, admissible: list[str]) -> str:
    if not admissible:
        return "look"
    match = re.search(r"\d+", text)
    if match:
        index = int(match.group())
        if 0 <= index < len(admissible):
            return admissible[index]
    low = text.lower()
    for command in admissible:
        if command.lower() in low:
            return command
    return admissible[0]


def _recent(history: list[dict], window: int = 6) -> list[str]:
    return [h["cmd"] for h in history[-window:]]


class TWBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        system = "You play a text adventure game. Reply with only the number of the command to take."
        prompt = (
            f"Objective: {obs['objective']}\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Available commands:\n{_numbered(commands)}\n"
            "Reply with just the number of the best command to progress toward the objective."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _select(text, commands), ""


class TWProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet"
        self.tried_here: dict[str, set[str]] = {}

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state_key = obs["description"][:200]
        tried = self.tried_here.setdefault(state_key, set())
        avoid = sorted(c for c in tried if c in commands)

        system = (
            "You play a text adventure game while keeping an explicit running belief about the world and a plan toward "
            "the objective. Reply only with a JSON object."
        )
        prompt = (
            f"Objective: {obs['objective']}\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Your current belief and plan: {self.belief}\n"
            f"Recent actions: {_recent(history)}\n"
            f"From this location you have already tried, without progress: {avoid or 'nothing yet'}. "
            "If you keep returning to the same location, you are in a loop; pick a command you have not tried here.\n"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (a short updated statement of what you now know about the '
            'world and your current plan to reach the objective), "command_number" (the integer of the command to take).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        number = parsed.get("command_number")
        if isinstance(number, int) and 0 <= number < len(commands):
            command = commands[number]
        else:
            command = _select(text, commands)

        if command in tried:
            untried = [c for c in commands if c not in tried]
            if untried:
                command = untried[0]
        tried.add(command)
        return command, f"belief={self.belief[:150]}"
