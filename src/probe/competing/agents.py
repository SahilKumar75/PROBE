from __future__ import annotations

import json

from probe.competing.env import KEYS
from probe.rule_shift.agents import _default_client, _extract_json, _parse_key


def _history_text(history: list[dict], window: int = 12) -> str:
    recent = history[-window:]
    if not recent:
        return "none yet"
    return "; ".join(
        f"{e['color']} {e['shape']}->{e['key']}={'correct' if e['reward'] else 'wrong'}"
        for e in recent
    )


def _other_key(key: str) -> str:
    for candidate in KEYS:
        if candidate != key:
            return candidate
    return key


class CompetingBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        system = "You map a color and shape to a key. Reply with exactly one key letter."
        prompt = (
            f"Keys are {keys}. The correct key is decided by one hidden feature, either the color or the shape, "
            "but you do not know which. Early on both features may look equally predictive; later evidence reveals "
            "which one truly decides. Use the history to infer the deciding feature.\n"
            f"Recent history: {_history_text(history)}\n"
            f"Current: color={obs['color']}, shape={obs['shape']}\n"
            f"Reply with one key letter from {keys}."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _parse_key(text, keys), ""


class CompetingProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.color_map: dict[str, str] = {}
        self.shape_map: dict[str, str] = {}
        self.color_alive = True
        self.shape_alive = True

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _update(self, history: list[dict]) -> None:
        if not history:
            return
        last = history[-1]
        correct = last["key"] if last["reward"] == 1 else _other_key(last["key"])
        color, shape = last["color"], last["shape"]
        if color in self.color_map and self.color_map[color] != correct:
            self.color_alive = False
        self.color_map[color] = correct
        if shape in self.shape_map and self.shape_map[shape] != correct:
            self.shape_alive = False
        self.shape_map[shape] = correct

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        keys = obs["keys"]
        self._update(history)
        color, shape = obs["color"], obs["shape"]

        color_pred = self.color_map.get(color, "?") if self.color_alive else "falsified"
        shape_pred = self.shape_map.get(shape, "?") if self.shape_alive else "falsified"

        system = (
            "You maintain two competing hypotheses about which feature decides the key, color or shape, "
            "and you keep both alive until one is contradicted. Reply only with a JSON object."
        )
        prompt = (
            f"Keys are {keys}. Exactly one hidden feature decides the key, color or shape.\n"
            f"Hypothesis color-decides: {'alive' if self.color_alive else 'FALSIFIED'}, learned {json.dumps(self.color_map)}\n"
            f"Hypothesis shape-decides: {'alive' if self.shape_alive else 'FALSIFIED'}, learned {json.dumps(self.shape_map)}\n"
            f"Current: color={color}, shape={shape}. Color hypothesis predicts {color_pred}, shape hypothesis predicts {shape_pred}.\n"
            "If only one hypothesis is still alive, use its prediction. If both are alive and agree, use that key. "
            "If both are alive but disagree, pick one to test so the wrong hypothesis gets contradicted.\n"
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

        note = (
            f"color[{'alive' if self.color_alive else 'dead'}]={json.dumps(self.color_map)} | "
            f"shape[{'alive' if self.shape_alive else 'dead'}]={json.dumps(self.shape_map)}"
        )
        return key, note
