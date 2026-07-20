from __future__ import annotations

import json

from probe.relational.env import KEYS
from probe.rule_shift.agents import _default_client, _extract_json, _parse_key


def _other_key(key: str) -> str:
    for candidate in KEYS:
        if candidate != key:
            return candidate
    return key


def _history_text(history: list[dict], window: int = 12) -> str:
    recent = history[-window:]
    if not recent:
        return "none yet"
    return "; ".join(
        f"({e['item_a']},{e['item_b']})->{e['key']}={'correct' if e['reward'] else 'wrong'}"
        for e in recent
    )


class RelationalBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        system = "You map two colored items to a key. Reply with exactly one key letter."
        prompt = (
            f"Keys are {keys}. You see two colored items. The correct key depends on the two items, and it may depend "
            "on the relationship between them (for example whether the two colors are the same or different) rather "
            "than on the specific colors. Use the history to infer the rule.\n"
            f"Recent history: {_history_text(history)}\n"
            f"Current: item_a={obs['item_a']}, item_b={obs['item_b']}\n"
            f"Reply with one key letter from {keys}."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _parse_key(text, keys), ""


class RelationalProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = {"same": "unknown", "different": "unknown"}

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _update(self, history: list[dict]) -> None:
        if not history:
            return
        last = history[-1]
        correct = last["key"] if last["reward"] == 1 else _other_key(last["key"])
        self.belief[last["relation"]] = correct

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        self._update(history)
        relation = "same" if obs["item_a"] == obs["item_b"] else "different"

        system = (
            "You act using an explicit belief about a relational rule: the key depends on whether the two items are "
            "the same or different. Reply only with a JSON object."
        )
        prompt = (
            f"Keys are {keys}. The correct key is decided by the relation between the two items, either they are the "
            "same color or different colors.\n"
            f"Your belief: same -> {self.belief['same']}, different -> {self.belief['different']}.\n"
            f"Current: item_a={obs['item_a']}, item_b={obs['item_b']}. These are {relation}.\n"
            f"If the {relation} case is already known in your belief, use that key. Otherwise pick a key to learn it.\n"
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

        note = f"belief same={self.belief['same']} different={self.belief['different']} | relation={relation}"
        return key, note
