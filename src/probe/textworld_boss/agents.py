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


STUCK_STEPS = 5


class TWProbe3Agent:
    """Middle ground of probe1 (Round 1) and probe2 (Round 2): keep probe1's
    cheap single-belief prompt and add only the two low-cost wins, dropping
    probe2's expensive machinery entirely.

    Diagnosis that motivates it: probe2's hypothesis-set + plan + elimination
    fired its contradiction only 4% of steps yet cost tokens and turns every
    step, raising the examine share and running out the 30-turn budget (71/100
    budget-exhausted losses vs probe1's 44). So the heavy machinery was almost
    all cost, no benefit. probe3 keeps only:
      1. A better stuck detector: progress = a score gain OR a new world state
         (admissible-command-set change), so the nudge fires when GENUINELY
         stuck rather than every step under the terminal reward.
      2. Episode-wide anti-repeat: remember (state, command) pairs that changed
         nothing and skip them, so turns are not wasted redoing dead ends.
    When stuck it adds ONE line to the prompt and forces one untried action; it
    never examines more (the failure mode of the rejected surprise gate). The
    prompt stays probe1-sized, so token cost per step is unchanged.
    """

    def __init__(self, client=None):
        self._client = client
        self.belief = "I have just arrived and do not yet know the layout or the goal."
        self.rule = "unknown; I do not yet know what earns score, so I must discover it by trying different kinds of actions and watching the score"
        self.seen_states: set[str] = set()
        self.steps_since_progress = 0
        self.last_score = 0
        self.dead: dict[str, set[str]] = {}
        self.tried_here: dict[str, set[str]] = {}
        self.last_state = None
        self.last_cmd = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state = repr(sorted(commands))
        score = int(obs.get("score", 0))
        tried = self.tried_here.setdefault(state, set())

        # anti-repeat: did the PREVIOUS command change the world? if not, it is dead here
        if self.last_state is not None and self.last_cmd is not None:
            if state == self.last_state and score <= self.last_score and not self.last_cmd.startswith(
                ("examine", "look", "inventory")
            ):
                self.dead.setdefault(self.last_state, set()).add(self.last_cmd)

        # progress = score gain OR a new world state (admissible set), not text
        progress = score > self.last_score or state not in self.seen_states
        self.seen_states.add(state)
        self.steps_since_progress = 0 if progress else self.steps_since_progress + 1
        stuck = self.rule.startswith("unknown") or self.steps_since_progress >= STUCK_STEPS

        dead_here = self.dead.get(state, set()) & set(commands)
        avoid = sorted(set(c for c in tried if c in commands) | dead_here)
        stuck_line = ""
        if stuck:
            stuck_line = (
                "You seem STUCK (no new progress recently). Try a DIFFERENT kind of action you have not tried here, "
                "not another examine or look. Avoid the dead-end commands listed above.\n"
            )

        system = (
            "You play a text adventure with a hidden objective. Keep a short situation belief and a short rule belief "
            "(what raises the score). Act to make progress; when stuck, try something new rather than sensing. Reply "
            "only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what earns score, and what you ruled out): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Commands that led nowhere here, avoid them: {avoid or 'none'}.\n"
            f"{stuck_line}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next step), "rule" (updated theory of what '
            'raises the score, and what you ruled out), and "command_number" (the integer command).'
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

        # when stuck, force a genuinely untried, non-dead command; otherwise just
        # avoid repeating a dead command
        if stuck:
            fresh = [c for c in commands if c not in tried and c not in dead_here]
            if fresh:
                command = fresh[0]
        elif command in dead_here:
            alive = [c for c in commands if c not in dead_here]
            if alive:
                command = alive[0]

        tried.add(command)
        self.last_state, self.last_cmd, self.last_score = state, command, score
        tag = " | STUCK" if stuck else ""
        return command, f"belief={self.belief[:60]} | rule={self.rule[:60]}{tag}"


def _is_sensing(cmd: str) -> bool:
    return cmd.lower().startswith(("examine", "look", "inventory", "search"))


class TWProbe4Agent:
    """Efficiency-first probe: win by wasting fewer turns, not by thinking more.

    Diagnosis: every one of probe1's 44 TextWorld losses is a budget time-out
    (30 turns, task unfinished), not a wrong answer. So the way to beat probe1
    is to spend more of the 30 turns on progress. probe3 kept probe1's brain and
    added anti-repeat but STILL examined 42% (its stuck rule forced examines).
    probe4 keeps the cheap adds and fixes the waste:
      1. Discourage examining in the prompt (prefer world-changing actions).
      2. When stuck, force an untried NON-sensing action (probe3 could pick an
         examine, which was the bug).
      3. Do not treat "rule still unknown" as stuck (that fired the nudge every
         early step and drove examining); stuck is purely a lack-of-progress
         streak.
      4. Keep probe3's novelty stuck detector and episode-wide anti-repeat.
    Same lean single-belief prompt as probe1, so per-step token cost is unchanged.
    """

    def __init__(self, client=None):
        self._client = client
        self.belief = "I have just arrived and do not yet know the layout or the goal."
        self.rule = "unknown; I must discover what earns score by trying actions that change the world and watching the score"
        self.seen_states: set[str] = set()
        self.steps_since_progress = 0
        self.last_score = 0
        self.dead: dict[str, set[str]] = {}
        self.tried_here: dict[str, set[str]] = {}
        self.last_state = None
        self.last_cmd = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state = repr(sorted(commands))
        score = int(obs.get("score", 0))
        tried = self.tried_here.setdefault(state, set())

        if self.last_state is not None and self.last_cmd is not None:
            if state == self.last_state and score <= self.last_score and not _is_sensing(self.last_cmd):
                self.dead.setdefault(self.last_state, set()).add(self.last_cmd)

        progress = score > self.last_score or state not in self.seen_states
        self.seen_states.add(state)
        self.steps_since_progress = 0 if progress else self.steps_since_progress + 1
        # stuck is purely a lack-of-progress streak; an unknown rule is NOT stuck
        stuck = self.steps_since_progress >= STUCK_STEPS

        dead_here = self.dead.get(state, set()) & set(commands)
        avoid = sorted(set(c for c in tried if c in commands) | dead_here)
        stuck_line = ""
        if stuck:
            stuck_line = (
                "You seem STUCK. Take a DIFFERENT world-changing action you have not tried here (move, take, open, "
                "put, unlock); do NOT examine or look. Avoid the dead-end commands above.\n"
            )

        system = (
            "You play a text adventure with a hidden objective and a 30-move budget, so every move must count. Keep a "
            "short situation belief and a short rule belief. PREFER actions that change the world (move, take, open, "
            "put, unlock) and examine only when you have a specific reason; do not waste moves looking around. Reply "
            "only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what earns score, and what you ruled out): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Commands that led nowhere here, avoid them: {avoid or 'none'}.\n"
            f"{stuck_line}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next step), "rule" (updated theory of what '
            'raises the score), and "command_number" (the integer command).'
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

        if stuck:
            # prefer an untried, non-dead, NON-sensing action; then any untried; then keep
            nonsense = [c for c in commands if c not in tried and c not in dead_here and not _is_sensing(c)]
            fresh = [c for c in commands if c not in tried and c not in dead_here]
            if nonsense:
                command = nonsense[0]
            elif fresh:
                command = fresh[0]
        elif command in dead_here:
            alive = [c for c in commands if c not in dead_here]
            if alive:
                command = alive[0]

        tried.add(command)
        self.last_state, self.last_cmd, self.last_score = state, command, score
        tag = " | STUCK" if stuck else ""
        return command, f"belief={self.belief[:60]} | rule={self.rule[:60]}{tag}"


class TWProbe5Agent:
    """Anti-loop probe: probe4's efficiency plus a hard rule against repeating.

    Loss analysis (probe1's 44 TextWorld losses, all time-outs): lost games have
    a 39% command-repeat rate vs 14% in won games. They loop, re-examining the
    same object (examine portal x3), redoing the same manipulation (drop passkey
    x2, open portal x2), and ping-ponging between two rooms (go east <-> go
    west), until the 30-move budget runs out. probe4's anti-repeat only blocked
    moves that changed NOTHING, so state-changing loops slipped through. probe5
    adds three memories that between them kill all three loop types:
      1. Examine-once: a sensing command (examine/look/inventory/search) already
         issued this episode is blocked; sensing is idempotent, once is enough.
      2. Full no-repeat: any non-sensing command already issued that did not
         raise the score is avoided, even if it changed the room (this also
         breaks the go east/west ping-pong, since neither raised the score).
      3. Least-used fallback: if every command is blocked, take the least-used
         one, so the agent still moves rather than deadlocking.
    Everything else is probe4 (lean prompt, low examining, budget-aware, novelty
    stuck detector). Same per-step token cost.
    """

    def __init__(self, client=None):
        self._client = client
        self.belief = "I have just arrived and do not yet know the layout or the goal."
        self.rule = "unknown; I must discover what earns score by trying actions that change the world and watching the score"
        self.seen_states: set[str] = set()
        self.steps_since_progress = 0
        self.last_score = 0
        self.issued_sensing: set[str] = set()
        self.unproductive: set[str] = set()
        self.cmd_uses: dict[str, int] = {}
        self.last_cmd = None
        self.last_state = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _blocked(self, c: str) -> bool:
        if _is_sensing(c):
            return c in self.issued_sensing
        return c in self.unproductive

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state = repr(sorted(commands))
        score = int(obs.get("score", 0))

        # after the fact: did the PREVIOUS command earn score? if not, it is
        # unproductive (sensing goes to its own idempotent set)
        if self.last_cmd is not None and score <= self.last_score:
            if _is_sensing(self.last_cmd):
                self.issued_sensing.add(self.last_cmd)
            else:
                self.unproductive.add(self.last_cmd)

        progress = score > self.last_score or state not in self.seen_states
        self.seen_states.add(state)
        self.steps_since_progress = 0 if progress else self.steps_since_progress + 1
        stuck = self.steps_since_progress >= STUCK_STEPS

        avoid = sorted(c for c in commands if self._blocked(c))
        stuck_line = ""
        if stuck:
            stuck_line = (
                "You seem STUCK. Take a DIFFERENT world-changing action you have not tried (move, take, open, put, "
                "unlock); do NOT examine or look, and do NOT repeat anything in the avoid list.\n"
            )

        system = (
            "You play a text adventure with a hidden objective and a 30-move budget, so every move must count. Keep a "
            "short situation belief and a short rule belief. PREFER actions that change the world; examine only with a "
            "specific reason; NEVER repeat a move that did nothing and NEVER re-examine what you already examined. "
            "Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what earns score, and what you ruled out): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Do NOT choose any of these (already tried, led nowhere): {avoid or 'none'}.\n"
            f"{stuck_line}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next step), "rule" (updated theory of what '
            'raises the score), and "command_number" (the integer command).'
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

        # override a blocked pick: prefer an untried, non-sensing, non-blocked
        # command; then any untried non-blocked; then the least-used command
        if self._blocked(command):
            untried_action = [c for c in commands if not self._blocked(c) and c not in self.cmd_uses and not _is_sensing(c)]
            untried_any = [c for c in commands if not self._blocked(c) and c not in self.cmd_uses]
            open_cmds = [c for c in commands if not self._blocked(c)]
            if untried_action:
                command = untried_action[0]
            elif untried_any:
                command = untried_any[0]
            elif open_cmds:
                command = open_cmds[0]
            else:
                command = min(commands, key=lambda c: self.cmd_uses.get(c, 0))

        self.cmd_uses[command] = self.cmd_uses.get(command, 0) + 1
        self.last_cmd, self.last_state, self.last_score = command, state, score
        tag = " | STUCK" if stuck else ""
        return command, f"belief={self.belief[:55]} | avoid={len(avoid)}{tag}"


class TWProbe51Agent:
    """Probe 5.1: probe5's anti-loop, but with a soft cap instead of a hard block.

    probe5 blocked any non-sensing command after ONE non-scoring use, which was
    too strict: some winnable games need a command twice (cross a room, come
    back with a key), so the hard block broke them and probe5 fell to 0.44 from
    probe1's 0.56 even though its won games were very clean. probe5.1 keeps the
    anti-loop but loosens the cap:
      - sensing (examine/look/inventory/search): cap 1 (idempotent, once is enough)
      - every other command: cap 2 (allow a legitimate repeat, block the 3rd+)
    This still kills the wasteful 3x+ loops seen in the losses (examine portal
    x3, go east/west ping-pong) while letting a necessary second use through.
    Everything else is probe4/probe5 (lean prompt, low examining, budget-aware).
    """

    def __init__(self, client=None):
        self._client = client
        self.belief = "I have just arrived and do not yet know the layout or the goal."
        self.rule = "unknown; I must discover what earns score by trying actions that change the world and watching the score"
        self.seen_states: set[str] = set()
        self.steps_since_progress = 0
        self.last_score = 0
        self.cmd_uses: dict[str, int] = {}
        self.last_state = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _cap(self, c: str) -> int:
        return 1 if _is_sensing(c) else 2

    def _blocked(self, c: str) -> bool:
        return self.cmd_uses.get(c, 0) >= self._cap(c)

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state = repr(sorted(commands))
        score = int(obs.get("score", 0))

        progress = score > self.last_score or state not in self.seen_states
        self.seen_states.add(state)
        self.steps_since_progress = 0 if progress else self.steps_since_progress + 1
        stuck = self.steps_since_progress >= STUCK_STEPS

        avoid = sorted(c for c in commands if self._blocked(c))
        stuck_line = ""
        if stuck:
            stuck_line = (
                "You seem STUCK. Take a DIFFERENT world-changing action (move, take, open, put, unlock); do NOT "
                "examine or look, and do NOT pick anything in the avoid list.\n"
            )

        system = (
            "You play a text adventure with a hidden objective and a 30-move budget, so every move must count. Keep a "
            "short situation belief and a short rule belief. PREFER actions that change the world; examine each thing "
            "only once; do not repeat the same move more than twice. Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:600]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what earns score, and what you ruled out): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Do NOT choose any of these (already used enough, led nowhere): {avoid or 'none'}.\n"
            f"{stuck_line}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next step), "rule" (updated theory of what '
            'raises the score), and "command_number" (the integer command).'
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

        # override a capped pick: prefer untried non-sensing, then untried, then
        # any not-yet-capped command, then the least-used
        if self._blocked(command):
            untried_action = [c for c in commands if not self._blocked(c) and c not in self.cmd_uses and not _is_sensing(c)]
            untried_any = [c for c in commands if not self._blocked(c) and c not in self.cmd_uses]
            open_cmds = [c for c in commands if not self._blocked(c)]
            if untried_action:
                command = untried_action[0]
            elif untried_any:
                command = untried_any[0]
            elif open_cmds:
                command = open_cmds[0]
            else:
                command = min(commands, key=lambda c: self.cmd_uses.get(c, 0))

        self.cmd_uses[command] = self.cmd_uses.get(command, 0) + 1
        self.last_state, self.last_score = state, score
        tag = " | STUCK" if stuck else ""
        return command, f"belief={self.belief[:55]} | capped={len(avoid)}{tag}"


_ROOM_RE = re.compile(r"-= ([^=]+?) =-")
_OBJ_RE = re.compile(r"^(?:take|examine|open|close|unlock|lock) ([a-zA-Z' -]+?)(?: from .*| with .*)?$")
_GO_RE = re.compile(r"^go (north|south|east|west)$")


class TWProbe52Agent:
    """Probe 5.2: probe5.1's soft-cap anti-loop plus a WORLD MAP memory.

    The union analysis showed 92/100 games are winnable by at least one agent,
    so the ~0.56 plateau is not a task cap; it is wandering. Every earlier
    variant carried only NEGATIVE memory (tried/dead/capped commands) and saw
    just the current room plus 6 recent actions, so it forgot what it had seen
    (a locked chest two rooms back, an exit never taken) and wandered blind.
    probe5.2 adds the missing POSITIVE memory:
      - a map of every room visited: its exits (and where they lead once
        traversed) and the objects seen there (parsed from the admissible
        commands, which is robust to prose changes);
      - the map is shown each turn, so the model can plan a route back to a
        remembered object once it acquires something new, instead of rediscovering.
    Caps are tuned for map use: sensing 1 (idempotent), movement (go X) 3
    (backtracking legitimately reuses moves), everything else 2.
    """

    def __init__(self, client=None):
        self._client = client
        self.belief = "I have just arrived and do not yet know the layout or the goal."
        self.rule = "unknown; I must discover what earns score by trying actions that change the world and watching the score"
        self.seen_states: set[str] = set()
        self.steps_since_progress = 0
        self.last_score = 0
        self.cmd_uses: dict[str, int] = {}
        self.rooms: dict[str, dict] = {}
        self.cur_room: str | None = None
        self.last_room: str | None = None
        self.last_go: str | None = None

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def _cap(self, c: str) -> int:
        if _is_sensing(c):
            return 1
        if _GO_RE.match(c):
            return 3
        return 2

    def _blocked(self, c: str) -> bool:
        return self.cmd_uses.get(c, 0) >= self._cap(c)

    def _update_map(self, obs: dict, commands: list[str]) -> None:
        m = _ROOM_RE.search(obs.get("description", ""))
        room = m.group(1).strip() if m else (self.cur_room or "start")
        entry = self.rooms.setdefault(room, {"exits": {}, "objects": set()})
        for c in commands:
            g = _GO_RE.match(c)
            if g:
                entry["exits"].setdefault(g.group(1), "?")
            o = _OBJ_RE.match(c)
            if o:
                entry["objects"].add(o.group(1).strip()[:24])
        # record the connection the last successful move revealed
        if self.last_room and self.last_go and room != self.last_room:
            self.rooms.setdefault(self.last_room, {"exits": {}, "objects": set()})["exits"][self.last_go] = room
        self.last_room = self.cur_room
        self.cur_room = room

    def _render_map(self) -> str:
        parts = []
        for name, e in list(self.rooms.items())[:6]:
            exits = ", ".join(f"{d}->{t}" for d, t in list(e["exits"].items())[:4]) or "none seen"
            objs = ", ".join(sorted(e["objects"])[:5]) or "none seen"
            here = " (YOU ARE HERE)" if name == self.cur_room else ""
            parts.append(f"{name}{here}: exits[{exits}] things[{objs}]")
        return " | ".join(parts)[:500]

    def act(self, obs: dict, history: list[dict]) -> tuple[str, str]:
        commands = obs["admissible"]
        state = repr(sorted(commands))
        score = int(obs.get("score", 0))
        self._update_map(obs, commands)

        progress = score > self.last_score or state not in self.seen_states
        self.seen_states.add(state)
        self.steps_since_progress = 0 if progress else self.steps_since_progress + 1
        stuck = self.steps_since_progress >= STUCK_STEPS

        avoid = sorted(c for c in commands if self._blocked(c))
        stuck_line = ""
        if stuck:
            stuck_line = (
                "You seem STUCK. Use your map: go to a room or exit you have not fully explored, or apply something "
                "in your inventory to a thing you remember seeing. Do NOT examine or look; do NOT pick from the avoid list.\n"
            )

        system = (
            "You play a text adventure with a hidden objective and a 30-move budget, so every move must count. You "
            "have a MAP of everything seen so far; use it to plan routes instead of wandering, and to return to "
            "remembered things once you hold a relevant item. PREFER actions that change the world; examine each "
            "thing at most once; do not repeat a move that led nowhere. Reply only with a JSON object."
        )
        prompt = (
            f"{HIDDEN}\n"
            f"Current score: {score} of a possible {obs['max_score']}.\n"
            f"Location: {obs['description'][:500]}\n"
            f"Inventory: {obs['inventory']}\n"
            f"MAP so far: {self._render_map()}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what earns score, and what you ruled out): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"Do NOT choose any of these (used enough, led nowhere): {avoid or 'none'}.\n"
            f"{stuck_line}"
            f"Available commands:\n{_numbered(commands)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next step), "rule" (updated theory of what '
            'raises the score), and "command_number" (the integer command).'
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

        if self._blocked(command):
            untried_action = [c for c in commands if not self._blocked(c) and c not in self.cmd_uses and not _is_sensing(c)]
            untried_any = [c for c in commands if not self._blocked(c) and c not in self.cmd_uses]
            open_cmds = [c for c in commands if not self._blocked(c)]
            if untried_action:
                command = untried_action[0]
            elif untried_any:
                command = untried_any[0]
            elif open_cmds:
                command = open_cmds[0]
            else:
                command = min(commands, key=lambda c: self.cmd_uses.get(c, 0))

        self.cmd_uses[command] = self.cmd_uses.get(command, 0) + 1
        g = _GO_RE.match(command)
        self.last_go = g.group(1) if g else None
        self.last_score = score
        tag = " | STUCK" if stuck else ""
        return command, f"belief={self.belief[:45]} | rooms={len(self.rooms)}{tag}"
