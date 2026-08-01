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


STAGNATION_WINDOW = 12
STAGNATION_DISTINCT = 4


class MiniHackProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet; I need to locate the goal and a path to it"
        self.mechanics = "unknown; I do not yet know how the obstacles here work, so I must discover it by trying to interact with things"
        self.blocked: dict[str, set[int]] = {}
        self.prev_screen: str | None = None
        self.prev_key: str | None = None
        self.prev_index: int | None = None
        self.recent_keys: list[str] = []
        self.steps = 0

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _stagnant(self) -> bool:
        window = self.recent_keys[-STAGNATION_WINDOW:]
        return len(window) >= STAGNATION_WINDOW and len(set(window)) <= STAGNATION_DISTINCT

    def act(self, obs: dict, actions: list[str], history: list[dict]) -> tuple[int, str]:
        screen = obs["screen"]
        key = screen[:400]
        self.steps += 1
        if self.prev_screen is not None and screen == self.prev_screen and self.prev_index is not None:
            self.blocked.setdefault(self.prev_key, set()).add(self.prev_index)
        blocked = self.blocked.setdefault(key, set())
        avoid = sorted(actions[i] for i in blocked if i < len(actions))
        self.recent_keys.append(key)

        experiment = self._stagnant() or (self.mechanics.startswith("unknown") and self.steps % STAGNATION_WINDOW == 0)
        contradiction = ""
        if experiment:
            contradiction = (
                "CONTRADICTION: your plan has not made progress recently, so your belief about the path is falsified. "
                "The way forward is probably not just walking around an obstacle. Form a NEW mechanics hypothesis about "
                "this level (for example, water may need to be acted on rather than avoided; a boulder next to you may be "
                "pushable by walking into it, which can fill water and make a crossing). Then choose an EXPERIMENTAL "
                "action that directly tests one mechanic, even if it does not look like immediate progress toward the goal.\n"
            )

        system = (
            "You play a NetHack level. Keep two explicit beliefs: a layout belief (where the goal is and your plan), and "
            "a mechanics belief (how this world works and how to get past obstacles). When progress stalls, treat it as "
            "evidence your belief is wrong, revise it, and act to test a mechanic rather than repeating navigation. Reply "
            "only with a JSON object."
        )
        prompt = (
            f"Message: {obs['message'] or 'none'}\n"
            f"Screen:\n{screen}\n\n"
            f"Layout belief and plan: {self.belief}\n"
            f"Mechanics belief (how this world works, and what you have ruled out): {self.mechanics}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Directions that hit a wall from this exact spot (the view did not change): {avoid or 'none'}.\n"
            f"{contradiction}"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(actions)}\n"
            'Reply with one JSON object with keys: "belief" (layout and your next move), "mechanics" (your updated theory '
            'of how to get past obstacles here, and what you have ruled out), and "action_number" (the integer action).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        mech = parsed.get("mechanics")
        if isinstance(mech, str) and mech.strip():
            self.mechanics = mech.strip()[:400]
        number = parsed.get("action_number")
        if isinstance(number, int) and 0 <= number < len(actions):
            index = number
        else:
            index = _select(text, actions)

        if not experiment and index in blocked:
            untried = [i for i in range(len(actions)) if i not in blocked]
            if untried:
                index = untried[0]

        self.prev_screen = screen
        self.prev_key = key
        self.prev_index = index
        tag = " | EXPERIMENT" if experiment else ""
        return index, f"belief={self.belief[:80]} | mech={self.mechanics[:80]}{tag}"


class MiniHackProbeAAgent(MiniHackProbeAgent):
    """PROBE-A on MiniHack: Round 1 core (inherited) + the adaptive instruments.

    Adds per docs/PROBE_A_SPEC.md: an ACTION LEDGER (per-action tallies of
    moved / blocked / message outcomes, aggregated across the episode and
    injected once it carries signal), a global 3-step COOLDOWN on an action
    whose last use changed nothing (the per-spot blocked memory already
    inherited only covers the current tile), and an explored-count novelty
    line. Actions are named, so the systematic probe phase never fires.
    """

    def __init__(self, client=None):
        super().__init__(client)
        self.ledger: dict[str, dict] = {}
        self.cooldown: dict[int, int] = {}

    def act(self, obs: dict, actions: list[str], history: list[dict]) -> tuple[int, str]:
        # ledger update for the PREVIOUS action
        if self.prev_index is not None and self.prev_key is not None:
            name = actions[self.prev_index] if self.prev_index < len(actions) else str(self.prev_index)
            entry = self.ledger.setdefault(name, {"moved": 0, "blocked": 0})
            if obs["screen"] == (self.prev_screen or ""):
                entry["blocked"] += 1
            else:
                entry["moved"] += 1
        # cooldown tick + assignment
        self.cooldown = {a: t - 1 for a, t in self.cooldown.items() if t - 1 > 0}
        if self.prev_index is not None and obs["screen"] == (self.prev_screen or ""):
            self.cooldown[self.prev_index] = 3

        ledger_lines = [
            f"{n}: moved x{e['moved']}, blocked x{e['blocked']}"
            for n, e in sorted(self.ledger.items(), key=lambda kv: -(kv[1]["moved"] + kv[1]["blocked"]))[:8]
        ]
        explored = len(set(self.recent_keys))
        extra = ""
        if ledger_lines:
            extra = (
                f"\nACTION LEDGER (observed this episode): {' | '.join(ledger_lines)}"
                f"\nDistinct views explored: {explored}. On cooldown (just did nothing): "
                f"{sorted(actions[i] for i in self.cooldown if i < len(actions)) or 'none'}."
            )
        obs = dict(obs)
        obs["message"] = (obs.get("message") or "none") + extra

        index, note = super().act(obs, actions, history)
        # respect cooldown outside experiments: pick a non-cooled alternative
        if index in self.cooldown and not self._stagnant():
            open_idx = [i for i in range(len(actions)) if i not in self.cooldown]
            if open_idx:
                index = open_idx[0]
                self.prev_index = index
        return index, "A|" + note
