"""Agents for the ARC-AGI-3 boss: baseline, reflexion, probe.

The environment is a 64x64 grid game with 7 unnamed actions plus RESET. The
agent is NOT told what any action does or what the goal is; it must infer both
by acting and watching the grid and score change. This is PROBE's exact thesis
(rules and goals emerge only through interaction), so the ARC probe agent runs
the Round 1 mechanics: a rule belief about what the actions do and what wins,
stagnation-as-contradiction when nothing advances, and active experimentation
to test an untried action.

Every agent returns (action_id, coord, note):
  - action_id: int 1..7 (RESET=0 is left to the harness, not chosen as a move)
  - coord: (x, y) for ACTION6 (a complex click), else None
  - note: a short trace string (belief/rule/reflection)
"""

from __future__ import annotations

from probe.rule_shift.agents import _default_client, _extract_json

STAGNATION_STEPS = 8


def _recent(history: list[dict], n: int = 8) -> str:
    if not history:
        return "none yet"
    return "; ".join(f"{h['action']}->{h['effect']}" for h in history[-n:])


def _parse_action(parsed: dict, available: list[int]) -> tuple[int, tuple[int, int] | None]:
    """Pull an action id (and optional coord for ACTION6) from a parsed reply."""
    aid = parsed.get("action")
    if isinstance(aid, str):
        aid = aid.upper().replace("ACTION", "").strip()
        aid = int(aid) if aid.isdigit() else None
    if not isinstance(aid, int) or aid not in available:
        aid = next((a for a in available if a != 0), available[0])
    coord = None
    if aid == 6:
        x, y = parsed.get("x"), parsed.get("y")
        coord = (int(x) if isinstance(x, int) else 32, int(y) if isinstance(y, int) else 32)
    return aid, coord


class ARCBaselineAgent:
    """Plain history, no structured belief. Picks an action from the grid."""

    def __init__(self, client=None):
        self._client = client

    def _c(self):
        return self._client or _default_client()

    def act(self, obs_text: str, available: list[int], history: list[dict]):
        system = (
            "You control a character in a grid puzzle. You are not told what the actions do or what the goal is. "
            "Figure it out by acting and observing. Reply only with a JSON object."
        )
        prompt = (
            f"{obs_text}\n"
            f"Recent actions and their effects: {_recent(history)}\n"
            'Reply with one JSON object: {"action": <integer id from the available actions>} '
            '(for action 6 also give integer "x" and "y" in 0..63).'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        aid, coord = _parse_action(_extract_json(text), available)
        return aid, coord, "baseline"


class ARCReflexionAgent:
    """Reason plus a running self-reflection, but no structured rule belief."""

    def __init__(self, client=None):
        self._client = client
        self.reflection = "no lessons yet"

    def _c(self):
        return self._client or _default_client()

    def act(self, obs_text: str, available: list[int], history: list[dict]):
        system = (
            "You control a character in a grid puzzle with unknown actions and an unknown goal. Keep a running "
            "reflection of lessons learned so far, then act. Reply only with a JSON object."
        )
        prompt = (
            f"{obs_text}\n"
            f"Recent actions and their effects: {_recent(history)}\n"
            f"Your reflection so far: {self.reflection}\n"
            'Reply with one JSON object: {"reflection": "updated lessons", "action": <integer id> } '
            '(for action 6 also give integer "x" and "y" in 0..63).'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        parsed = _extract_json(text)
        refl = parsed.get("reflection")
        if isinstance(refl, str) and refl.strip():
            self.reflection = refl.strip()[:400]
        aid, coord = _parse_action(parsed, available)
        return aid, coord, f"reflection={self.reflection[:70]}"


class ARCProbeAgent:
    """Round 1: rule belief + stagnation-as-contradiction + active experimentation.

    Belief is split into a mechanics belief (what each action does, what the
    goal seems to be, what wins) and ruled-out actions. When the score has not
    risen and the grid stops changing, the plan is declared falsified and the
    agent is forced to experiment with an untried action, which is exactly what
    a passive reflection loop cannot do.
    """

    def __init__(self, client=None):
        self._client = client
        self.mechanics = "unknown; I do not yet know what any action does or what the goal is, so I must probe each action and watch the grid and score"
        self.last_score = 0
        self.steps_since_gain = 0
        self.steps_since_change = 0
        self.tried: set[int] = set()

    def _c(self):
        return self._client or _default_client()

    def act(self, obs_text: str, available: list[int], history: list[dict]):
        # stagnation signals: no score gain, and the last action changed nothing
        last_effect = history[-1]["effect"] if history else ""
        if "NOTHING changed" in last_effect:
            self.steps_since_change += 1
        else:
            self.steps_since_change = 0

        experiment = (
            self.mechanics.startswith("unknown")
            or self.steps_since_gain >= STAGNATION_STEPS
            or self.steps_since_change >= 3
        )
        untried = [a for a in available if a not in self.tried and a != 0]
        contradiction = ""
        if experiment:
            contradiction = (
                "CONTRADICTION: your actions are not advancing the game (no score gain, or the grid stopped "
                "changing), so your belief about what the actions do or what the goal is has been falsified. Form a "
                "NEW hypothesis about the mechanics, then choose an EXPERIMENTAL action that tests it: prefer an "
                f"action you have not tried yet {untried or 'none left, try a different one'}.\n"
            )

        system = (
            "You control a character in a grid puzzle with unknown actions and an unknown goal. Keep one explicit "
            "belief: the MECHANICS, meaning what each action does, what the goal appears to be, and what raises the "
            "score. When nothing advances, treat it as evidence your mechanics belief is wrong, revise it, and act "
            "to test it. Reply only with a JSON object."
        )
        prompt = (
            f"{obs_text}\n"
            f"Recent actions and their effects: {_recent(history)}\n"
            f"Your mechanics belief (what the actions do, the goal, what wins): {self.mechanics}\n"
            f"Actions you have already tried: {sorted(self.tried) or 'none yet'}.\n"
            f"{contradiction}"
            'Reply with one JSON object: {"mechanics": "your updated theory of what the actions do and how to win", '
            '"action": <integer id from the available actions>} (for action 6 also give integer "x" and "y" in 0..63).'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        parsed = _extract_json(text)
        mech = parsed.get("mechanics")
        if isinstance(mech, str) and mech.strip():
            self.mechanics = mech.strip()[:400]
        aid, coord = _parse_action(parsed, available)

        # anti-repeat: outside experiment mode, avoid re-picking a tried action that led nowhere
        if not experiment and aid in self.tried and untried:
            aid, coord = untried[0], (None if untried[0] != 6 else (32, 32))
        self.tried.add(aid)
        tag = " | EXPERIMENT" if experiment else ""
        return aid, coord, f"mechanics={self.mechanics[:80]}{tag}"

    def observe_score(self, score: int) -> None:
        """Called by the runner each step so stagnation tracks real score gains."""
        if score > self.last_score:
            self.steps_since_gain = 0
        else:
            self.steps_since_gain += 1
        self.last_score = score


class ARCProbe52Agent(ARCProbeAgent):
    """probe5.2-style adds for ARC: anti-loop cooldown + budget-aware efficiency.

    ARC frames are fully observable (the whole grid is visible every step), so
    probe5.2's room map is meaningless here. What ports is the anti-loop: an
    action that just produced "NOTHING changed" goes on cooldown for a few
    steps instead of being re-spammed (the smoke showed ACTION2 chosen many
    times in a row), plus a budget line in the prompt so every move counts.
    Inherits the Round 1 mechanics (rule belief, stagnation-as-contradiction,
    active experimentation) from ARCProbeAgent.
    """

    COOLDOWN = 4

    def __init__(self, client=None):
        super().__init__(client)
        self.cooldown: dict[int, int] = {}
        self.last_aid: int | None = None

    def act(self, obs_text: str, available: list[int], history: list[dict]):
        # tick cooldowns down each step
        self.cooldown = {a: t - 1 for a, t in self.cooldown.items() if t - 1 > 0}
        # if the PREVIOUS action changed nothing, put it on cooldown
        if history and self.last_aid is not None and "NOTHING changed" in history[-1]["effect"]:
            self.cooldown[self.last_aid] = self.COOLDOWN

        open_actions = [a for a in available if a not in self.cooldown and a != 0]
        obs_text = (
            obs_text
            + "\nYou have a limited move budget, so every action must count. These actions just did NOTHING and are "
            + f"on cooldown, do not pick them: {sorted(self.cooldown) or 'none'}."
        )
        aid, coord, note = super().act(obs_text, open_actions or available, history)
        if aid in self.cooldown and open_actions:
            aid = open_actions[0]
            coord = (32, 32) if aid == 6 else None
        self.last_aid = aid
        return aid, coord, note + f" | cd={sorted(self.cooldown)}"


class ARCProbe53Agent(ARCProbeAgent):
    """Probe 5.3 for ARC: an ACTION LEDGER (positive memory of what each action
    actually did) plus novelty-based stagnation, applying the TextWorld lessons.

    Diagnosis of the 0/30 floor: the delta evidence was in the observation each
    step, but nothing accumulated it, so the model re-derived (and hallucinated)
    the mechanics every step; and the score-based stagnation trigger kept it in
    permanent EXPERIMENT mode under the terminal reward, rewriting a fantasy
    theory each step (the TextWorld thrash again). Fixes:
      1. Ledger: aggregate per-action outcomes from the FULL history (the
         harness emits facts like "moved '8' right" / "NOTHING changed" /
         "changed 5 cells") and print the table each step. Deterministic
         bookkeeping the model should never have to re-derive.
      2. Dead actions: an action tried >=3 times that only ever produced
         NOTHING is listed as useless and excluded from experiments.
      3. Novelty stagnation: progress = the grid changed or the score rose;
         experiment fires only after 4 steps with NO grid change (not on a
         score drought, which is permanent under terminal reward).
    """

    def act(self, obs_text: str, available: list[int], history: list[dict]):
        # ---- ledger from full history ----
        from collections import Counter, defaultdict
        outcomes: dict[str, Counter] = defaultdict(Counter)
        for h in history:
            outcomes[h["action"]][h["effect"].split(" to ")[0]] += 1

        # ---- systematic probe phase: complete the ledger BEFORE planning ----
        # 5.3.1 failure: the agent only ever used ledger-confirmed actions
        # (44x down + 33x up, left and right tried once each), an exploration
        # collapse. So first give EVERY available action two deterministic
        # tries (no model call, no hallucination, cheaper), then plan with a
        # complete ledger. This is PROBE's probe-all-sensors-first move.
        live_now = [a for a in available if a != 0]
        under = [a for a in live_now if sum(outcomes[f"ACTION{a}"].values()) < 2]
        if under:
            aid = min(under, key=lambda a: sum(outcomes[f"ACTION{a}"].values()))
            self.tried.add(aid)
            self.last_aid = aid
            return aid, ((32, 32) if aid == 6 else None), f"PROBING action {aid} (ledger incomplete)"
        ledger_lines = []
        for act_name in sorted(outcomes):
            c = outcomes[act_name]
            top = ", ".join(f"{eff} x{n}" for eff, n in c.most_common(3))
            ledger_lines.append(f"{act_name}: {top}")
        ledger = " | ".join(ledger_lines) or "no data yet"
        # cooldown, not a permanent ban: direction actions are context-dependent
        # (into a wall = nothing, in a corridor = moves), so a permanent
        # only-ever-nothing ban cripples navigation (the 5.3 failure). An action
        # whose LAST use did nothing sits out a few steps, then returns.
        self.cooldown = {a: t - 1 for a, t in getattr(self, "cooldown", {}).items() if t - 1 > 0}
        if history and getattr(self, "last_aid", None) is not None and "NOTHING changed" in history[-1]["effect"]:
            self.cooldown[self.last_aid] = 3
        dead = sorted(self.cooldown)

        # ---- novelty stagnation (grid change or score = progress) ----
        last_effect = history[-1]["effect"] if history else ""
        if "NOTHING changed" in last_effect:
            self.steps_since_change += 1
        else:
            self.steps_since_change = 0
        experiment = self.steps_since_change >= 4 or not history

        live = [a for a in available if a not in dead and a != 0]
        untried = [a for a in live if a not in self.tried]
        contradiction = ""
        if experiment:
            contradiction = (
                "CONTRADICTION: the grid has stopped changing, so your current approach is falsified. Using the "
                "LEDGER, pick the action most likely to move things forward, or an untried live action "
                f"{untried or '(none untried)'}. Never pick a useless action.\n"
            )

        system = (
            "You control a character in a grid puzzle with unknown actions and an unknown goal. You are given a "
            "LEDGER of what each action has actually done so far: treat it as ground truth physics, do not invent "
            "mechanics that contradict it. Typical games: a movable symbol must reach a special cell. Form your "
            "mechanics belief FROM the ledger, plan with it, and act. Reply only with a JSON object."
        )
        prompt = (
            f"{obs_text}\n"
            f"ACTION LEDGER (observed facts): {ledger}\n"
            f"On cooldown (just did nothing, skip briefly): {dead or 'none'}\n"
            f"Recent actions and their effects: {_recent(history)}\n"
            f"Your mechanics belief: {self.mechanics}\n"
            f"{contradiction}"
            'Reply with one JSON object: {"mechanics": "belief grounded in the ledger", '
            '"action": <integer id from the available actions>} (for action 6 also give integer "x" and "y").'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        parsed = _extract_json(text)
        mech = parsed.get("mechanics")
        if isinstance(mech, str) and mech.strip():
            self.mechanics = mech.strip()[:400]
        aid, coord = _parse_action(parsed, live or available)

        if aid in dead and live:
            aid = (untried or live)[0]
            coord = (32, 32) if aid == 6 else None
        self.last_aid = aid
        self.tried.add(aid)
        tag = " | EXPERIMENT" if experiment else ""
        return aid, coord, f"mech={self.mechanics[:60]} | dead={dead}{tag}"


VARIANTS = {
    "baseline_arc": ARCBaselineAgent,
    "reflexion_arc": ARCReflexionAgent,
    "probe_arc": ARCProbeAgent,
    "probe52_arc": ARCProbe52Agent,
    "probe53_arc": ARCProbe53Agent,
}
