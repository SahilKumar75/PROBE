from __future__ import annotations

import json

from probe.rule_shift.agents import _default_client, _extract_json, _parse_key


def _history_text(history: list[dict], window: int = 12) -> str:
    recent = history[-window:]
    if not recent:
        return "none yet"
    return "; ".join(
        f"{e['color']} {e['shape']}->{e['key']}={'correct' if e['reward'] else 'wrong'}"
        for e in recent
    )


class MultiFactorBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        colors, shapes, keys = obs["colors"], obs["shapes"], obs["keys"]
        system = "You map a color and shape to a key. Reply with exactly one key letter."
        prompt = (
            f"Colors are {colors}, shapes are {shapes}, keys are {keys}. "
            "Each (color, shape) pair has one correct key. The correct key can depend on BOTH the color and the shape, "
            "not just one of them, so do not assume the color alone or the shape alone decides it.\n"
            f"Recent history: {_history_text(history)}\n"
            f"Current: color={obs['color']}, shape={obs['shape']}\n"
            f"Reply with one key letter from {keys}."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _parse_key(text, keys), ""


class MultiFactorProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.confirmed: dict[tuple[str, str], str] = {}
        self.ruled_out: dict[tuple[str, str], set[str]] = {}

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _revise_from_last(self, history: list[dict]) -> None:
        if not history:
            return
        last = history[-1]
        combo = (last["color"], last["shape"])
        key, reward = last["key"], last["reward"]
        self.ruled_out.setdefault(combo, set())
        if reward == 1:
            self.confirmed[combo] = key
            self.ruled_out[combo] = set()
        elif self.confirmed.get(combo) == key:
            del self.confirmed[combo]
            self.ruled_out[combo] = {key}
        else:
            self.ruled_out[combo].add(key)

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        self._revise_from_last(history)
        combo = (obs["color"], obs["shape"])
        self.ruled_out.setdefault(combo, set())

        confirmed_text = "; ".join(f"{c} {s}={k}" for (c, s), k in self.confirmed.items()) or "none yet"
        current_ruled = sorted(self.ruled_out[combo])

        system = (
            "You act using an explicit belief about the hidden (color, shape) to key rule, where the key can depend on "
            "both features. Reply only with a JSON object."
        )
        prompt = (
            f"Keys are {keys}. Each (color, shape) pair maps to one key, and the key can depend on BOTH features. "
            "Track each pair separately; do not assume the color alone or the shape alone decides the key.\n"
            f"Confirmed pairs so far: {confirmed_text}\n"
            f"Current pair: color={obs['color']}, shape={obs['shape']}\n"
            f"Keys already ruled out for this pair: {current_ruled}\n"
            "If this exact pair is confirmed, use that key. Otherwise pick a key not ruled out for this pair.\n"
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

        note = f"confirmed={confirmed_text} | current_ruled_out={current_ruled}"
        return key, note
