from __future__ import annotations

import json

from probe.rule_shift.agents import _default_client, _extract_json, _parse_key


def _history_text(history: list[dict], window: int = 10) -> str:
    recent = history[-window:]
    if not recent:
        return "none yet"
    return "; ".join(
        f"{entry['cue_text']}->{entry['key']}={'correct' if entry['reward'] else 'wrong'}"
        for entry in recent
    )


class BaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        system = "You map a cue to a key. Reply with exactly one key letter."
        prompt = (
            f"Each cue maps to one correct key from ({', '.join(keys)}); reward 1 for correct, 0 for wrong. "
            "The hidden rule can change during the game; if recent answers started failing, the rule changed and you relearn it.\n"
            f"Cue space: {obs['space_text']}\n"
            f"Recent history: {_history_text(history)}\n"
            f"Current cue: {obs['cue_text']}\n"
            f"Reply with one key letter from {', '.join(keys)}."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _parse_key(text, keys), ""


class ReflexionAgent:
    def __init__(self, client=None):
        self._client = client
        self.reflection = "none yet"

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        system = (
            "You reason before acting and keep a short running self reflection of what you have learned about the "
            "rule, then choose a key. Reply only with a JSON object."
        )
        prompt = (
            f"Each cue maps to one correct key from ({', '.join(keys)}); reward 1 for correct, 0 for wrong. "
            "The hidden rule can change mid game.\n"
            f"Cue space: {obs['space_text']}\n"
            f"Your running self reflection: {self.reflection}\n"
            f"Recent history: {_history_text(history)}\n"
            f"Current cue: {obs['cue_text']}\n"
            'Reply with one JSON object with keys: "thought" (brief reasoning), "reflection" (your updated lesson '
            'about the rule so far), "action" (one key letter).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        reflection = parsed.get("reflection")
        if isinstance(reflection, str) and reflection.strip():
            self.reflection = reflection.strip()[:400]
        action = parsed.get("action")
        if isinstance(action, str) and action.strip().upper() in set(keys):
            key = action.strip().upper()
        else:
            key = _parse_key(text, keys)
        return key, f"reflection={self.reflection[:150]}"


class ProbeAgent:
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
            return f"{last['cue_text']} was confirmed as {key} but just failed; the rule changed, so its belief is revised"
        self.ruled_out[cue].add(key)
        return "none"

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        cue = obs["cue"]
        self.ruled_out.setdefault(cue, set())

        signal = self._revise_from_last(history)
        confirmed_text = json.dumps(self.confirmed) if self.confirmed else "none yet"
        current_ruled = sorted(self.ruled_out.get(cue, set()))
        confirmed_here = self.confirmed.get(cue)

        system = (
            "You act using an explicit, revised belief about the hidden cue to key rule. Reply only with a JSON object."
        )
        prompt = (
            f"Each cue maps to one key from ({', '.join(keys)}); reward 1 for correct, 0 for wrong. "
            "The mapping can change mid game.\n"
            f"Cue space: {obs['space_text']}\n"
            f"Confirmed cue to key mappings so far: {confirmed_text}\n"
            f"Revision signal: {signal}\n"
            f"Current cue: {obs['cue_text']}\n"
            f"This cue is currently confirmed as: {confirmed_here or 'not yet'}\n"
            f"Keys already ruled out for this cue: {current_ruled}\n"
            "If this cue is confirmed, use that key. Otherwise pick a key that is not ruled out for it.\n"
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

        note = f"confirmed={len(self.confirmed)} ruled_out={current_ruled} signal={signal}"
        return key, note


VARIANTS = {
    "baseline": BaselineAgent,
    "reflexion": ReflexionAgent,
    "probe": ProbeAgent,
}
