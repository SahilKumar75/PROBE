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
        self.confirmed: dict[str, str] = {}
        self.ruled_out: dict[str, set[str]] = {}

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _revise_from_last(self, history: list[dict]) -> str:
        if not history:
            return "none"
        last = history[-1]
        cue, key, reward = last["cue"], last["key"], last["reward"]
        self.ruled_out.setdefault(cue, set())
        if reward == 1:
            self.confirmed[cue] = key
            self.ruled_out[cue] = set()
            return "none"
        if self.confirmed.get(cue) == key:
            del self.confirmed[cue]
            self.ruled_out[cue] = {key}
            return f"{cue} was confirmed as {key} but just failed; the rule changed, so the belief for {cue} is revised"
        self.ruled_out[cue].add(key)
        return "none"

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        cues, keys = obs["cues"], obs["keys"]
        for cue in cues:
            self.ruled_out.setdefault(cue, set())

        signal = self._revise_from_last(history)
        cue = obs["cue"]
        confirmed_text = json.dumps(self.confirmed) if self.confirmed else "none yet"
        ruled_text = "; ".join(f"{c}: {sorted(self.ruled_out[c])}" for c in cues if self.ruled_out[c]) or "none"
        current_ruled = sorted(self.ruled_out.get(cue, set()))

        system = (
            "You act using an explicit, revised belief about the hidden color to key rule. "
            "Reply only with a JSON object."
        )
        prompt = (
            f"Each color ({', '.join(cues)}) maps to one key from ({', '.join(keys)}). "
            "Reward 1 for correct, 0 for wrong. The mapping can change mid game.\n"
            f"Confirmed mappings so far: {confirmed_text}\n"
            f"Keys already ruled out (wrong) per color: {ruled_text}\n"
            f"Revision signal: {signal}\n"
            f"Current cue: {cue}\n"
            f"Keys already ruled out for {cue}: {current_ruled}\n"
            f"If {cue} is already confirmed, use that key. Otherwise pick a key that is not ruled out for {cue}.\n"
            'Reply with one JSON object with keys: "action" (one key letter), "note" (short reasoning).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        action = parsed.get("action")
        if isinstance(action, str) and action.strip().upper() in set(keys):
            key = action.strip().upper()
        else:
            key = _parse_key(text, keys)

        note = f"confirmed={json.dumps(self.confirmed)} | ruled_out={{{ruled_text}}} | signal={signal}"
        return key, note
