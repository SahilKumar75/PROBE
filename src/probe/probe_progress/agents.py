from __future__ import annotations

from probe.rule_shift.agents import _default_client, _extract_json


def _parse_action(text: str, actions: list[str]) -> str:
    action_map = {a.lower(): a for a in actions}
    normalized = text.strip().lower().replace(" ", "_")
    for token in normalized.split():
        token = token.strip(".,:;'\"()[]{}*`")
        if token in action_map:
            return action_map[token]
    low = text.lower().replace(" ", "_")
    for action in actions:
        if action.lower() in low:
            return action
    if "probe" in low:
        return "probe"
    for target in ["t1", "t2", "t3"]:
        if target in low:
            return f"commit_{target.upper()}"
    return "safe"


def _history_text(history: list[dict], window: int = 12) -> str:
    recent = history[-window:]
    if not recent:
        return "none yet"
    return "; ".join(f"{e['action']}={e['reward']:+g}" for e in recent)


class ProbeProgressBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        actions = obs["actions"]
        status = f"known, it is {obs['known_target']}" if obs["revealed"] else "unknown"
        system = "You choose one action per step to maximize total reward over the whole game. Reply with exactly one action name."
        prompt = (
            f"Available actions: {actions}. You do not know in advance what each action does; learn from the rewards you receive.\n"
            f"You have {obs['horizon']} steps total, this is step {obs['step']}. Hidden target status: {status}.\n"
            f"Recent history (action=reward): {_history_text(history)}\n"
            f"Reply with exactly one action name from {actions}."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _parse_action(text, actions), ""


class ProbeProgressAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        actions = obs["actions"]
        known = obs["revealed"]
        status = f"KNOWN, it is {obs['known_target']}" if known else "UNKNOWN"
        system = (
            "You choose one action per step to maximize total reward over the whole game, and you reason explicitly "
            "about what you do not yet know. Reply only with a JSON object."
        )
        prompt = (
            f"Available actions: {actions}. Learn what each does from the rewards you receive.\n"
            f"You have {obs['horizon']} steps total, this is step {obs['step']}.\n"
            f"Your belief about the hidden target: {status}.\n"
            "If the target is UNKNOWN, an action that reveals information about it is valuable even if its immediate "
            "reward is low, because once you know the target you can act well for every remaining step. Spending one "
            "step to remove that uncertainty is usually worth it early. If the target is KNOWN, exploit it.\n"
            f"Recent history (action=reward): {_history_text(history)}\n"
            'Reply with one JSON object with keys: "action" (one action name), "note" (short reasoning).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        parsed = _extract_json(text)
        action = parsed.get("action")
        if isinstance(action, str) and action.strip() in actions:
            chosen = action.strip()
        else:
            chosen = _parse_action(text, actions)
        return chosen, f"target={status} | {parsed.get('note', '')[:60]}"
