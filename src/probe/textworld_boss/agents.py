from __future__ import annotations

import re

from probe.rule_shift.agents import _default_client, _extract_json


HIDDEN = (
    "You are not told the objective. Your score rises when you do the right things. "
    "You must infer from the score feedback what this world rewards, and pursue it."
)

STAGNATION_STEPS = 8


def _numbered(admissible: list[str]) -> str:
    return "\n".join(f"{index}: {command}" for index, command in enumerate(admissible))


def _select(text: str, admissible: list[str]) -> str:
    if not admissible:
        return "look"
    match = re.search(r"\d+", text or "")
    if match:
        index = int(match.group())
        if 0 <= index < len(admissible):
            return admissible[index]
    low = (text or "").lower()
    for command in admissible:
        if command.lower() in low:
            return command
    return admissible[0]


def _recent(history: list[dict], window: int = 6) -> list[str]:
    return [h["cmd"] for h in history[-window:]]


class TWBaselineAgent:
    def __init__(self, client=None):
        self._client = client
        self.tried_here: dict[str, set[str]] = {}

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state_key = obs["description"][:200]
        tried = self.tried_here.setdefault(state_key, set())
        avoid = sorted(c for c in tried if c in commands)
        system = "You play a text adventure game. Reply with only the number of the command to take."
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {obs['score']} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Recent actions: {_recent(history)}\n"
            f"From this location you have already tried, without progress: {avoid or 'nothing yet'}. "
            "If you keep returning to the same location, you are in a loop; pick a command you have not tried here.\n"
            f"Available commands:\n{_numbered(commands)}\n"
            "Reply with just the number of the best command to raise your score."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        command = _select(text, commands)
        if command in tried:
            untried = [c for c in commands if c not in tried]
            if untried:
                command = untried[0]
        tried.add(command)
        return command, ""


class TWReflexionAgent:
    def __init__(self, client=None):
        self._client = client
        self.reflection = "none yet"
        self.tried_here: dict[str, set[str]] = {}

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state_key = obs["description"][:200]
        tried = self.tried_here.setdefault(state_key, set())
        avoid = sorted(c for c in tried if c in commands)
        system = (
            "You play a text adventure game. Reason briefly, keep a short running self reflection of what you have "
            "learned about what this world rewards, then choose a command. Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {obs['score']} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Your running self reflection: {self.reflection}\n"
            f"Recent actions: {_recent(history)}\n"
            f"From this location you have already tried, without progress: {avoid or 'nothing yet'}.\n"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "thought" (brief reasoning), "reflection" (your updated lesson about '
            'what raises the score here), and "command_number" (the integer of the command to take).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        reflection = parsed.get("reflection")
        if isinstance(reflection, str) and reflection.strip():
            self.reflection = reflection.strip()[:400]
        number = parsed.get("command_number")
        if isinstance(number, int) and 0 <= number < len(commands):
            command = commands[number]
        else:
            command = _select(text, commands)
        if command in tried:
            untried = [c for c in commands if c not in tried]
            if untried:
                command = untried[0]
        tried.add(command)
        return command, f"reflection={self.reflection[:150]}"


class TWProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet"
        self.rule = "unknown; I do not yet know what earns score, so I must discover it by trying different kinds of actions and watching the score"
        self.tried_here: dict[str, set[str]] = {}
        self.last_score = 0
        self.steps_since_gain = 0

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state_key = obs["description"][:200]
        tried = self.tried_here.setdefault(state_key, set())
        avoid = sorted(c for c in tried if c in commands)

        score = int(obs.get("score", 0))
        if score > self.last_score:
            self.steps_since_gain = 0
        else:
            self.steps_since_gain += 1
        self.last_score = score

        experiment = self.steps_since_gain >= STAGNATION_STEPS or self.rule.startswith("unknown")
        contradiction = ""
        if experiment:
            contradiction = (
                "CONTRADICTION: the score has not risen recently, so your belief about what this world rewards is "
                "falsified. Form a NEW rule hypothesis about what earns score (for example a specific object must be "
                "taken, combined, or delivered somewhere). Then choose an EXPERIMENTAL command that tests that rule, "
                "a kind of action you have not tried here, even if it does not obviously help.\n"
            )

        system = (
            "You play a text adventure game. Keep two explicit beliefs: a situation belief (where you are and your "
            "plan) and a rule belief (what this world rewards and how the score rises). When the score stalls, treat "
            "it as evidence your rule belief is wrong, revise it, and act to test the rule. Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what earns score, and what you have ruled out): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"From this location you have already tried, without progress: {avoid or 'nothing yet'}.\n"
            f"{contradiction}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next step), "rule" (your updated theory of '
            'what raises the score here, and what you have ruled out), and "command_number" (the integer command).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        rule = parsed.get("rule")
        if isinstance(rule, str) and rule.strip():
            self.rule = rule.strip()[:400]
        number = parsed.get("command_number")
        if isinstance(number, int) and 0 <= number < len(commands):
            command = commands[number]
        else:
            command = _select(text, commands)

        if not experiment and command in tried:
            untried = [c for c in commands if c not in tried]
            if untried:
                command = untried[0]
        tried.add(command)
        tag = " | EXPERIMENT" if experiment else ""
        return command, f"belief={self.belief[:70]} | rule={self.rule[:70]}{tag}"


def _objects(obs: dict) -> set[str]:
    """Crude object set from the admissible commands, for novelty tracking."""
    objs = set()
    for c in obs.get("admissible", []):
        m = re.match(r"(?:take|examine|open|close|put|insert|unlock|lock|drop|eat|drink)\s+(.+)", c)
        if m:
            objs.add(m.group(1)[:30])
    return objs


class TWProbe2Agent:
    """Round 1.5 + Round 2 probe: fixes the thrash-under-terminal-reward failure.

    Diagnosis (tw_paper1, n=100): Round 1's stagnation-as-contradiction fires on
    "no score gain", but TextWorld's reward is terminal (score stays 0 until the
    task is finished), so it fired every step and the agent thrashed, swapping
    its single rule hypothesis each step and never committing to a plan. Four
    fixes:
      1. Novelty progress signal: progress = score rose OR a new room/object was
         seen. Stagnation only counts steps with NO novelty, so exploring no
         longer looks like failure.
      2. Plan-commit gate: while progress keeps coming, follow the committed plan
         for a few steps before allowing another falsification.
      3. Competing hypotheses + elimination (Round 2 mechanic 4): keep a small
         SET of candidate rules and rule them out with evidence, instead of
         re-inventing one hypothesis per step.
      4. Episode-wide anti-repeat (Round 2 mechanic 5): remember (state, command)
         pairs that changed nothing and avoid them, so dead ends are not redone.
    """

    def __init__(self, client=None):
        self._client = client
        self.hypotheses: list[str] = []
        self.ruled_out: list[str] = []
        self.plan = ""
        self.plan_steps_left = 0
        self.seen_states: set[str] = set()
        self.seen_objects: set[str] = set()
        self.steps_since_progress = 0
        self.last_score = 0
        self.dead: dict[str, set[str]] = {}
        self.last_state = None
        self.last_cmd = None
        self.last_desc = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        # State signature is the admissible-command SET, not the description text.
        # Examining/looking changes the description but not the set, so it does
        # not read as progress; moving rooms, opening doors, or taking objects
        # DOES change the set. This is the strict progress proxy that stops both
        # the Round 1 thrash (score-only) and the placid-drift failure (text
        # novelty is too cheap).
        state = repr(sorted(commands))
        score = int(obs.get("score", 0))

        # anti-repeat bookkeeping: did the PREVIOUS command change the world?
        if self.last_desc is not None and self.last_cmd is not None:
            changed = state != self.last_desc or score > self.last_score
            if not changed and not self.last_cmd.startswith(("examine", "look", "inventory")):
                self.dead.setdefault(self.last_state, set()).add(self.last_cmd)

        # progress = a score gain or a world-state change (new admissible set)
        new_state = state not in self.seen_states
        progress = score > self.last_score or new_state
        self.seen_states.add(state)
        self.steps_since_progress = 0 if progress else self.steps_since_progress + 1

        # plan-commit gate: burn down the commit only while progress continues
        if self.plan_steps_left > 0 and progress:
            self.plan_steps_left -= 1

        # contradiction fires when (a) there is no hypothesis yet, (b) no world
        # change for STAGNATION_STEPS, or (c) score-drought: many distinct
        # world-states explored but the score is STILL zero, which under a
        # terminal reward is the real signal that the theory of what scores is
        # wrong. The plan-commit gate suppresses (b)/(c) mid-plan.
        contradiction = (not self.hypotheses) or (
            self.plan_steps_left <= 0
            and (
                self.steps_since_progress >= STAGNATION_STEPS
                or (score == 0 and len(self.seen_states) >= 12)
            )
        )

        avoid = sorted(self.dead.get(state, set()) & set(commands))
        contra_txt = ""
        if contradiction:
            contra_txt = (
                "CONTRADICTION: you have not reached any new state or object recently, so your leading hypothesis is "
                "wrong. RULE IT OUT, promote a different candidate rule, and pick a command that TESTS the new leading "
                "candidate. Do not merely restate a hypothesis; commit to a plan and follow it.\n"
            )

        system = (
            "You play a text adventure with a hidden objective. Maintain a SET of competing hypotheses about what "
            "earns score, rule them out with evidence rather than replacing them wholesale, and commit to a plan for "
            "several steps before abandoning it. Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Open hypotheses (candidate rules for what earns score): {self.hypotheses or ['none yet']}\n"
            f"Already ruled out: {self.ruled_out or 'none'}\n"
            f"Current plan: {self.plan or 'none'}\n"
            f"Progress: {'new ground just now' if self.steps_since_progress == 0 else f'no new state/object for {self.steps_since_progress} steps'}.\n"
            f"Recent actions: {_recent(history)}\n"
            f"Commands that changed nothing here, avoid them: {avoid or 'none'}.\n"
            f"{contra_txt}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "hypotheses" (list of up to 3 current candidate rules, most likely '
            'first), "ruled_out" (list of rules you are eliminating this step), "plan" (a short concrete plan), '
            '"commit" (integer steps to follow the plan before re-checking), and "command_number" (the integer command).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        hyps = parsed.get("hypotheses")
        if isinstance(hyps, list) and hyps:
            self.hypotheses = [str(h)[:120] for h in hyps[:3]]
        newly_out = parsed.get("ruled_out")
        if isinstance(newly_out, list):
            for r in newly_out:
                r = str(r)[:120]
                if r and r not in self.ruled_out:
                    self.ruled_out.append(r)
                self.hypotheses = [h for h in self.hypotheses if h != r]
        plan = parsed.get("plan")
        if isinstance(plan, str) and plan.strip():
            self.plan = plan.strip()[:200]
        commit = parsed.get("commit")
        if isinstance(commit, int) and commit > 0:
            self.plan_steps_left = min(commit, STAGNATION_STEPS)

        number = parsed.get("command_number")
        if isinstance(number, int) and 0 <= number < len(commands):
            command = commands[number]
        else:
            command = _select(text, commands)

        # anti-repeat: outside a forced contradiction, do not repeat a dead command
        if not contradiction and command in self.dead.get(state, set()):
            fresh = [c for c in commands if c not in self.dead.get(state, set())]
            if fresh:
                command = fresh[0]

        self.last_state, self.last_cmd, self.last_desc, self.last_score = state, command, state, score
        tag = " | CONTRADICTION" if contradiction else ""
        return command, f"hyps={self.hypotheses[:2]} | plan={self.plan[:50]}{tag}"
