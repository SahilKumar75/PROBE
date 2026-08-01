"""Agents for the ScienceWorld boss (external #5).

ScienceWorld states the GOAL (e.g. "boil water") but hides the DYNAMICS: what
heats, what conducts, what a device needs before it works. The agent must run
experiments to discover the mechanics, which is PROBE's hidden-rule regime.

Actions are FREEFORM text (the env parses commands like "open door to kitchen",
"activate stove", "use thermometer on substance"); there is no small admissible
list, so agents write the command themselves from the observation.

Four conditions mirror the TextWorld line for comparability:
  - SWBaselineAgent   plain history
  - SWReflexionAgent  running self-reflection, no structured belief
  - SWProbeAgent      probe1-style single rule belief + stagnation experiment
  - SWProbe52Agent    probe5.2-style: map memory + soft-cap anti-loop + efficiency

Every agent returns (command, note).
"""

from __future__ import annotations

import re

from probe.rule_shift.agents import _default_client, _extract_json

STAGNATION_STEPS = 6

TEMPLATES = (
    "look around; go LOC; open DOOR; pick up OBJ; put OBJ in CONTAINER; activate OBJ; "
    "deactivate OBJ; use OBJ on OBJ2; pour LIQ into CONTAINER; mix CONTAINER; read OBJ; "
    "focus on OBJ; wait1"
)


def _recent(history: list[dict], n: int = 6) -> str:
    if not history:
        return "none yet"
    return " | ".join(f"{h['cmd']} -> {h['fb'][:60]}" for h in history[-n:])


def _command_of(parsed: dict, text: str) -> str:
    cmd = parsed.get("command")
    if isinstance(cmd, str) and cmd.strip():
        return cmd.strip()[:80]
    line = (text or "").strip().splitlines()[-1] if text else ""
    return (line[:80] or "look around")


def _is_sensing(cmd: str) -> bool:
    return cmd.lower().startswith(("look", "read", "examine", "inventory"))


class SWBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _c(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        system = (
            "You are an agent in a science simulator. Achieve the task. Reply only with a JSON object "
            'like {"command": "<one action>"}.'
        )
        prompt = (
            f"Task: {obs['task']}\n"
            f"Score so far: {obs['score']} of 100.\n"
            f"Observation: {obs['obs'][:700]}\n"
            f"Inventory: {obs['inventory'][:200]}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Action formats: {TEMPLATES}\n"
            'Reply with one JSON object: {"command": "<the single best next action>"}.'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _command_of(_extract_json(text), text), "baseline"


class SWReflexionAgent:
    def __init__(self, client=None):
        self._client = client
        self.reflection = "no lessons yet"

    def _c(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        system = (
            "You are an agent in a science simulator. Keep a short running reflection of lessons learned, "
            'then act. Reply only with a JSON object like {"reflection": "...", "command": "..."}.'
        )
        prompt = (
            f"Task: {obs['task']}\n"
            f"Score so far: {obs['score']} of 100.\n"
            f"Observation: {obs['obs'][:700]}\n"
            f"Inventory: {obs['inventory'][:200]}\n"
            f"Your reflection so far: {self.reflection}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Action formats: {TEMPLATES}\n"
            'Reply with one JSON object: {"reflection": "updated lessons", "command": "<next action>"}.'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        parsed = _extract_json(text)
        refl = parsed.get("reflection")
        if isinstance(refl, str) and refl.strip():
            self.reflection = refl.strip()[:400]
        return _command_of(parsed, text), f"reflection={self.reflection[:70]}"


class SWProbeAgent:
    """probe1-style: single situation belief + rule belief, stagnation experiment."""

    def __init__(self, client=None):
        self._client = client
        self.belief = "I have just started and do not know this environment yet."
        self.rule = "unknown; I must discover how the devices and materials here behave by experimenting"
        self.last_score = 0
        self.steps_since_gain = 0

    def _c(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        score = int(obs.get("score", 0))
        if score > self.last_score:
            self.steps_since_gain = 0
        else:
            self.steps_since_gain += 1
        self.last_score = score

        experiment = self.steps_since_gain >= STAGNATION_STEPS
        contra = ""
        if experiment:
            contra = (
                "CONTRADICTION: the score has not risen recently, so your belief about how this world works is "
                "likely wrong. Form a NEW hypothesis about the mechanics (what heats, powers, mixes, or transforms "
                "things) and choose an EXPERIMENTAL action that tests it.\n"
            )

        system = (
            "You are an agent in a science simulator with hidden mechanics. Keep a situation belief and a RULE "
            "belief about how the world works (what heats, conducts, mixes, grows). When progress stalls, revise the "
            "rule belief and act to test it. Reply only with a JSON object."
        )
        prompt = (
            f"Task: {obs['task']}\n"
            f"Score so far: {score} of 100.\n"
            f"Observation: {obs['obs'][:700]}\n"
            f"Inventory: {obs['inventory'][:200]}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (how this world works): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{contra}"
            f"Action formats: {TEMPLATES}\n"
            'Reply with one JSON object: {"belief": "situation and next step", "rule": "updated theory of the '
            'mechanics", "command": "<next action>"}.'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        rule = parsed.get("rule")
        if isinstance(rule, str) and rule.strip():
            self.rule = rule.strip()[:400]
        tag = " | EXPERIMENT" if experiment else ""
        return _command_of(parsed, text), f"belief={self.belief[:50]} | rule={self.rule[:50]}{tag}"


_ROOM_RE = re.compile(r"This room is called the ([a-zA-Z ]+)\.")
_DOOR_RE = re.compile(r"door to the ([a-zA-Z ]+)")


class SWProbe52Agent:
    """probe5.2-style: rule belief + world MAP + soft-cap anti-loop + efficiency."""

    def __init__(self, client=None):
        self._client = client
        self.belief = "I have just started and do not know this environment yet."
        self.rule = "unknown; I must discover how the devices and materials here behave by experimenting"
        self.last_score = 0
        self.steps_since_gain = 0
        self.cmd_uses: dict[str, int] = {}
        self.rooms: dict[str, set[str]] = {}
        self.cur_room: str | None = None

    def _c(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _cap(self, c: str) -> int:
        low = c.lower()
        if _is_sensing(low):
            return 2  # 'look around' after moving is legitimate, so cap 2 not 1
        if low.startswith("go "):
            return 3
        return 2

    def _blocked(self, c: str) -> bool:
        return self.cmd_uses.get(c.lower(), 0) >= self._cap(c)

    def _update_map(self, obs_text: str) -> None:
        m = _ROOM_RE.search(obs_text)
        if m:
            self.cur_room = m.group(1).strip()
        room = self.cur_room or "start"
        doors = set(_DOOR_RE.findall(obs_text))
        entry = self.rooms.setdefault(room, set())
        entry |= doors

    def _render_map(self) -> str:
        parts = []
        for name, doors in list(self.rooms.items())[:8]:
            here = " (YOU ARE HERE)" if name == self.cur_room else ""
            parts.append(f"{name}{here}: doors to [{', '.join(sorted(doors)[:6]) or '?'}]")
        return " | ".join(parts)[:400]

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        score = int(obs.get("score", 0))
        self._update_map(obs["obs"])
        if score > self.last_score:
            self.steps_since_gain = 0
        else:
            self.steps_since_gain += 1
        self.last_score = score

        experiment = self.steps_since_gain >= STAGNATION_STEPS
        avoid = sorted({c for c in self.cmd_uses if self.cmd_uses[c] >= 2})[:8]
        contra = ""
        if experiment:
            contra = (
                "CONTRADICTION: no score progress recently, so your rule belief is likely wrong. Form a NEW "
                "hypothesis about the mechanics and TEST it with a world-changing action you have not tried; use the "
                "map to reach unexplored rooms. Do not repeat avoided commands and do not just look around.\n"
            )

        system = (
            "You are an agent in a science simulator with hidden mechanics and a limited step budget, so every move "
            "must count. Keep a situation belief and a RULE belief about how the world works. You have a MAP of the "
            "rooms seen; use it to navigate instead of wandering. PREFER world-changing actions; look or read only "
            "with a specific reason; never repeat an action that did nothing twice. Reply only with a JSON object."
        )
        prompt = (
            f"Task: {obs['task']}\n"
            f"Score so far: {score} of 100.\n"
            f"Observation: {obs['obs'][:700]}\n"
            f"Inventory: {obs['inventory'][:200]}\n"
            f"MAP so far: {self._render_map()}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (how this world works): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Do NOT repeat these (used enough, led nowhere): {avoid or 'none'}.\n"
            f"{contra}"
            f"Action formats: {TEMPLATES}\n"
            'Reply with one JSON object: {"belief": "situation and next step", "rule": "updated theory of the '
            'mechanics", "command": "<next action>"}.'
        )
        try:
            text = self._c().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        rule = parsed.get("rule")
        if isinstance(rule, str) and rule.strip():
            self.rule = rule.strip()[:400]
        command = _command_of(parsed, text)

        if self._blocked(command):
            command = "look around" if not _is_sensing(command) else "wait1"
            # one safe fallback that always parses; the next model call sees the avoid list

        self.cmd_uses[command.lower()] = self.cmd_uses.get(command.lower(), 0) + 1
        tag = " | EXPERIMENT" if experiment else ""
        return command, f"rule={self.rule[:45]} | rooms={len(self.rooms)}{tag}"


VARIANTS = {
    "baseline_sw": SWBaselineAgent,
    "reflexion_sw": SWReflexionAgent,
    "probe_sw": SWProbeAgent,
    "probe52_sw": SWProbe52Agent,
}


class SWProbeAAgent(SWProbe52Agent):
    """PROBE-A on ScienceWorld: probe5.2 machinery behind adaptive gates.

    The map section enters the prompt only once >= 2 rooms have been seen;
    commands are named English so the systematic probe phase never fires.
    A score-yield ledger enters once any command has produced score (partial
    credit makes this observable here, unlike TextWorld's terminal reward).
    """

    def __init__(self, client=None):
        super().__init__(client)
        self.yields: dict[str, int] = {}
        self._last_cmd: str | None = None
        self._last_score = 0

    def _render_map(self) -> str:
        if len(self.rooms) < 2:
            return ""
        return super()._render_map()

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        score = int(obs.get("score", 0))
        if self._last_cmd is not None and score > self._last_score:
            self.yields[self._last_cmd] = self.yields.get(self._last_cmd, 0) + (score - self._last_score)
        if self.yields:
            top = ", ".join(f"'{c}' earned +{v}" for c, v in sorted(self.yields.items(), key=lambda kv: -kv[1])[:5])
            obs = dict(obs)
            # PREPEND so the parent's observation truncation cannot chop the
            # ledger off the end (the first probe-u run lost it to [:700])
            obs["obs"] = f"LEDGER of what has earned score (ground truth): {top}\n" + obs["obs"][:600]
        command, note = super().act(obs, history)
        self._last_cmd, self._last_score = command, score
        return command, "A|" + note

VARIANTS["probe_a_sw"] = SWProbeAAgent
