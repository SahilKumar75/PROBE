from __future__ import annotations

import re

from probe.rule_shift.agents import _default_client, _extract_json


HIDDEN = (
    "You are not told the objective. Your score rises when you do the right things. "
    "You must infer from the score feedback what this world rewards, and pursue it."
)

STAGNATION_STEPS = 8


def _numbered(admissible: list[str]) -> str:
    return "\n".join(f"{index}: {command}" for index, command in enumerate(admissible))


def _select(text: str, admissible: list[str]) -> str:
    if not admissible:
        return "look"
    match = re.search(r"\d+", text or "")
    if match:
        index = int(match.group())
        if 0 <= index < len(admissible):
            return admissible[index]
    low = (text or "").lower()
    for command in admissible:
        if command.lower() in low:
            return command
    return admissible[0]


def _recent(history: list[dict], window: int = 6) -> list[str]:
    return [h["cmd"] for h in history[-window:]]


class TWBaselineAgent:
    def __init__(self, client=None):
        self._client = client
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
        system = "You play a text adventure game. Reply with only the number of the command to take."
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {obs['score']} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Recent actions: {_recent(history)}\n"
            f"From this location you have already tried, without progress: {avoid or 'nothing yet'}. "
            "If you keep returning to the same location, you are in a loop; pick a command you have not tried here.\n"
            f"Available commands:\n{_numbered(commands)}\n"
            "Reply with just the number of the best command to raise your score."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        command = _select(text, commands)
        if command in tried:
            untried = [c for c in commands if c not in tried]
            if untried:
                command = untried[0]
        tried.add(command)
        return command, ""


class TWReflexionAgent:
    def __init__(self, client=None):
        self._client = client
        self.reflection = "none yet"
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
            "You play a text adventure game. Reason briefly, keep a short running self reflection of what you have "
            "learned about what this world rewards, then choose a command. Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {obs['score']} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Your running self reflection: {self.reflection}\n"
            f"Recent actions: {_recent(history)}\n"
            f"From this location you have already tried, without progress: {avoid or 'nothing yet'}.\n"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "thought" (brief reasoning), "reflection" (your updated lesson about '
            'what raises the score here), and "command_number" (the integer of the command to take).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        reflection = parsed.get("reflection")
        if isinstance(reflection, str) and reflection.strip():
            self.reflection = reflection.strip()[:400]
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
        return command, f"reflection={self.reflection[:150]}"


class TWProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet"
        self.rule = "unknown; I do not yet know what earns score, so I must discover it by trying different kinds of actions and watching the score"
        self.tried_here: dict[str, set[str]] = {}
        self.last_score = 0
        self.steps_since_gain = 0

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state_key = obs["description"][:200]
        tried = self.tried_here.setdefault(state_key, set())
        avoid = sorted(c for c in tried if c in commands)

        score = int(obs.get("score", 0))
        if score > self.last_score:
            self.steps_since_gain = 0
        else:
            self.steps_since_gain += 1
        self.last_score = score

        experiment = self.steps_since_gain >= STAGNATION_STEPS or self.rule.startswith("unknown")
        contradiction = ""
        if experiment:
            contradiction = (
                "CONTRADICTION: the score has not risen recently, so your belief about what this world rewards is "
                "falsified. Form a NEW rule hypothesis about what earns score (for example a specific object must be "
                "taken, combined, or delivered somewhere). Then choose an EXPERIMENTAL command that tests that rule, "
                "a kind of action you have not tried here, even if it does not obviously help.\n"
            )

        system = (
            "You play a text adventure game. Keep two explicit beliefs: a situation belief (where you are and your "
            "plan) and a rule belief (what this world rewards and how the score rises). When the score stalls, treat "
            "it as evidence your rule belief is wrong, revise it, and act to test the rule. Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what earns score, and what you have ruled out): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"From this location you have already tried, without progress: {avoid or 'nothing yet'}.\n"
            f"{contradiction}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next step), "rule" (your updated theory of '
            'what raises the score here, and what you have ruled out), and "command_number" (the integer command).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        rule = parsed.get("rule")
        if isinstance(rule, str) and rule.strip():
            self.rule = rule.strip()[:400]
        number = parsed.get("command_number")
        if isinstance(number, int) and 0 <= number < len(commands):
            command = commands[number]
        else:
            command = _select(text, commands)

        if not experiment and command in tried:
            untried = [c for c in commands if c not in tried]
            if untried:
                command = untried[0]
        tried.add(command)
        tag = " | EXPERIMENT" if experiment else ""
        return command, f"belief={self.belief[:70]} | rule={self.rule[:70]}{tag}"
