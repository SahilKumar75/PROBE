from __future__ import annotations

import json
import os

from probe.stage0.groq_client import GroqClient
from probe.stage0.ollama_client import OllamaClient
from probe.stage0.openrouter_client import OpenRouterClient


def _default_client():
    if os.getenv("OPENROUTER_API_KEY"):
        return OpenRouterClient()
    if os.getenv("GROQ_API_KEY"):
        return GroqClient()
    return OllamaClient()


def _parse_key(text: str, keys: list[str]) -> str:
    valid = set(keys)
    for token in text.upper().split():
        cleaned = token.strip(".,:;'\"()[]{}*`")
        if cleaned in valid:
            return cleaned
    return keys[0]


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _history_text(history: list[dict], window: int = 10) -> str:
    recent = history[-window:]
    if not recent:
        return "none yet"
    return "; ".join(
        f"{entry['cue']}->{entry['key']}={'correct' if entry['reward'] else 'wrong'}"
        for entry in recent
    )


class BaselineRuleAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        cues, keys = obs["cues"], obs["keys"]
        system = "You map a color cue to a key. Reply with exactly one key letter."
        prompt = (
            f"Each color ({', '.join(cues)}) has one correct key from ({', '.join(keys)}). "
            "You get 1 for correct and 0 for wrong. The hidden mapping may change during the game; "
            "if your recent answers started failing, the rule changed and you must relearn it.\n"
            f"Recent history: {_history_text(history)}\n"
            f"Current cue: {obs['cue']}\n"
            f"Reply with one key letter from {', '.join(keys)}."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _parse_key(text, keys), ""


class ProbeRuleAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief: dict[str, str] = {}

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        cues, keys = obs["cues"], obs["keys"]
        if not self.belief:
            self.belief = {cue: "unknown" for cue in cues}

        contradiction_signal = "none"
        if history:
            last = history[-1]
            if self.belief.get(last["cue"]) == last["key"] and last["reward"] == 0:
                contradiction_signal = (
                    f"last step you believed {last['cue']} maps to {last['key']} "
                    "but it was wrong, so that belief is falsified and must be revised"
                )

        system = (
            "You track an explicit belief about the hidden color to key rule, revise it when contradicted, "
            "and then act. Reply only with a JSON object."
        )
        prompt = (
            f"Each color ({', '.join(cues)}) has one correct key from ({', '.join(keys)}). "
            "Reward 1 for correct, 0 for wrong. The hidden mapping may change mid game. "
            "When a belief is contradicted, revise that entry.\n"
            f"Your current rule belief: {json.dumps(self.belief)}\n"
            f"Contradiction signal: {contradiction_signal}\n"
            f"Recent history: {_history_text(history)}\n"
            f"Current cue: {obs['cue']}\n"
            'Reply with one JSON object with keys: "belief" (an object mapping each color to a key or the word unknown), '
            '"contradiction" (a short note or none), "action" (one key letter).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        new_belief = parsed.get("belief")
        if isinstance(new_belief, dict):
            valid = set(keys)
            for cue in cues:
                value = str(new_belief.get(cue, "unknown")).strip().upper()
                self.belief[cue] = value if value in valid else "unknown"

        action = parsed.get("action")
        if isinstance(action, str) and action.strip().upper() in set(keys):
            key = action.strip().upper()
        else:
            key = _parse_key(text, keys)

        note = (
            f"belief={json.dumps(self.belief)} | "
            f"contradiction={parsed.get('contradiction', 'none')} | signal={contradiction_signal}"
        )
        return key, note
