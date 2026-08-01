from __future__ import annotations

import re

from probe.crafter_boss.env import ACTIONS
from probe.rule_shift.agents import _default_client, _extract_json


TIPS = (
    "Use 'do' to collect or attack whatever is directly in front of you, so move toward a resource first. "
    "Progression: collect wood, place_table, make_wood_pickaxe, collect stone, make_stone_pickaxe, place_furnace, "
    "collect coal and iron, make iron tools. Drink water and eat cows to keep vitals up."
)


def _numbered(actions: list[str]) -> str:
    return "\n".join(f"{i}: {a}" for i, a in enumerate(actions))


def _select(text: str, actions: list[str]) -> int:
    match = re.search(r"\d+", text)
    if match:
        index = int(match.group())
        if 0 <= index < len(actions):
            return index
    low = text.lower()
    for i, a in enumerate(actions):
        if a in low:
            return i
    return 0


def _recent(history: list[dict], window: int = 8) -> list[str]:
    return [h["action"] for h in history[-window:]]


class CrafterBaselineAgent:
    def __init__(self, client=None):
        self._client = client

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        system = "You play Crafter, a survival game. Unlock as many achievements as possible. Reply with only the number of the action."
        prompt = (
            f"Vitals: {obs['vitals']}\n"
            f"Inventory: {obs['resources']}\n"
            f"Achievements unlocked: {obs['achievements']}\n"
            f"Nearby: {obs['nearby']}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(ACTIONS)}\n"
            "Reply with the number of the best action."
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""
        return _select(text, ACTIONS), ""


class CrafterProbeAgent:
    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet"

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        system = (
            "You play Crafter while keeping an explicit running belief about your situation and a plan through the "
            "achievement tech tree. Reply only with a JSON object."
        )
        prompt = (
            f"Vitals: {obs['vitals']}\n"
            f"Inventory: {obs['resources']}\n"
            f"Achievements unlocked: {obs['achievements']}\n"
            f"Nearby: {obs['nearby']}\n"
            f"Your current belief and plan: {self.belief}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(ACTIONS)}\n"
            'Reply with one JSON object with keys: "belief" (a short updated statement of your situation and your '
            'current next sub goal in the tech tree), "action_number" (the integer of the action to take).'
        )
        try:
            text = self._client_or_default().generate_text(system_instruction=system, user_prompt=prompt)
        except Exception:
            text = ""

        parsed = _extract_json(text)
        self.belief = str(parsed.get("belief", self.belief))[:400]
        number = parsed.get("action_number")
        if isinstance(number, int) and 0 <= number < len(ACTIONS):
            index = number
        else:
            index = _select(text, ACTIONS)
        return index, f"belief={self.belief[:150]}"


class CrafterReflexionAgent:
    def __init__(self, client=None):
        self._client = client
        self.reflection = "none yet"

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        system = (
            "You play Crafter. Reason briefly, keep a short running self reflection of what you have learned about the "
            "game, then choose an action. Reply only with a JSON object."
        )
        prompt = (
            f"Vitals: {obs['vitals']}\n"
            f"Inventory: {obs['resources']}\n"
            f"Achievements unlocked: {obs['achievements']}\n"
            f"Nearby: {obs['nearby']}\n"
            f"Your running self reflection: {self.reflection}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(ACTIONS)}\n"
            'Reply with one JSON object with keys: "thought" (brief reasoning), "reflection" (your updated lesson), '
            '"action_number" (the integer of the action to take).'
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
        if isinstance(number, int) and 0 <= number < len(ACTIONS):
            index = number
        else:
            index = _select(text, ACTIONS)
        return index, f"reflection={self.reflection[:150]}"


class CrafterProbeUAgent:
    """PROBE-U, the unified agent: Round 1 core + novelty stagnation + anti-spam
    + positive memory (world seen + action ledger), mapped to Crafter.

    Components and their Crafter mapping:
      - Rule belief (R1): what unlocks what in the tech tree, kept explicit.
      - Novelty progress (5.1): progress = a NEW achievement, a resource gain,
        or a never-before-seen nearby entity; stagnation is counted on that,
        not on raw state change (Crafter always changes pixels).
      - Stagnation-as-contradiction + experimentation (R1): after 10 steps
        with no novelty the plan is declared falsified and an EXPERIMENT is
        forced toward an action category not tried recently.
      - Anti-spam (5.2's cooldown, not a ban): the same action 4x in a row
        with no novelty forces a different action.
      - World memory (5.2's map): the set of entity types seen so far.
      - Action ledger (5.3): per-action tally of what it produced (resource
        gains, achievements), shown each step as ground-truth facts.
    """

    def __init__(self, client=None):
        self._client = client
        self.belief = "no plan yet"
        self.rule = "unknown; I must discover what each action yields and what unlocks what by trying and watching inventory and achievements"
        self.seen_entities: set[str] = set()
        self.last_resources: dict | None = None
        self.last_achievements: set[str] = set()
        self.steps_since_novelty = 0
        self.ledger: dict[str, dict] = {}
        self.last_action: str | None = None
        self.same_streak = 0

    def _client_or_default(self):
        if self._client is None:
            self._client = _default_client()
        return self._client

    @staticmethod
    def _parse_kv(raw) -> dict:
        if isinstance(raw, dict):
            return {str(k): v for k, v in raw.items()}
        out = {}
        for m in re.finditer(r"(\w+)\s*[:=]\s*(\d+)", str(raw)):
            out[m.group(1)] = int(m.group(2))
        return out

    def act(self, obs: dict, history: list[dict]) -> tuple[int, str]:
        resources = self._parse_kv(obs.get("resources", ""))
        achievements = set(re.findall(r"[a-z_]+", str(obs.get("achievements", ""))))
        nearby = set(re.findall(r"[a-z_]+", str(obs.get("nearby", ""))))

        # ---- ledger + novelty from the delta of the LAST action ----
        novelty = False
        if self.last_action is not None:
            gains = []
            if self.last_resources is not None:
                for k, v in resources.items():
                    if v > self.last_resources.get(k, 0):
                        gains.append(f"+{k}")
            new_ach = achievements - self.last_achievements
            for a in new_ach:
                gains.append(f"ACHIEVEMENT {a}")
            entry = self.ledger.setdefault(self.last_action, {"uses": 0, "gains": {}})
            entry["uses"] += 1
            for g in gains:
                entry["gains"][g] = entry["gains"].get(g, 0) + 1
            # world-state change counts as progress (the spec's novelty rule):
            # walking changes what is nearby; only a frozen view is stagnation
            view_changed = nearby != getattr(self, "_last_nearby", set())
            novelty = bool(gains) or bool(nearby - self.seen_entities) or view_changed
        self._last_nearby = set(nearby)
        self.seen_entities |= nearby
        self.last_resources = resources
        self.last_achievements = achievements
        self.steps_since_novelty = 0 if novelty else self.steps_since_novelty + 1

        # RULES-GIVEN gate (PROBE-A trigger): Crafter's prompt includes TIPS
        # that state the tech tree, so the rules are not hidden. Per the
        # adaptive-effort principle (Insight 041/048), suppress the experiment
        # machinery in known-rule mode and keep the instruments passive; the
        # ledger/seen lines still render but no contradiction pressure fires.
        rules_given = bool(TIPS)
        experiment = (not rules_given) and self.steps_since_novelty >= 10
        ledger_lines = []
        for a, e in sorted(self.ledger.items(), key=lambda kv: -kv[1]["uses"])[:8]:
            top = ", ".join(f"{g} x{n}" for g, n in sorted(e["gains"].items(), key=lambda kv: -kv[1])[:3]) or "nothing yet"
            ledger_lines.append(f"{a}({e['uses']}x): {top}")
        ledger = " | ".join(ledger_lines) or "no data yet"

        contra = ""
        if experiment:
            contra = (
                "CONTRADICTION: nothing new for a while, so your plan is falsified. Using the LEDGER, pick the "
                "action most likely to produce a NEW resource or achievement, or try a promising action you have "
                "not used recently. Do not keep repeating what yields nothing.\n"
            )

        system = (
            "You play Crafter, keeping an explicit situation belief and a RULE belief about what unlocks what. You "
            "have a LEDGER of what each action has actually produced: treat it as ground truth. Plan through the "
            "tech tree; when progress stalls, revise the rule belief and test it. Reply only with a JSON object."
        )
        prompt = (
            f"Vitals: {obs['vitals']}\n"
            f"Inventory: {obs['resources']}\n"
            f"Achievements unlocked: {obs['achievements']}\n"
            f"Nearby: {obs['nearby']}\n"
            f"Entity types seen so far: {sorted(self.seen_entities) or 'none'}\n"
            f"ACTION LEDGER (observed yields): {ledger}\n"
            f"Situation belief and plan: {self.belief}\n"
            f"Rule belief (what unlocks what): {self.rule}\n"
            f"Recent actions: {_recent(history)}\n"
            f"{contra}"
            f"{TIPS}\n"
            f"Actions:\n{_numbered(ACTIONS)}\n"
            'Reply with one JSON object with keys: "belief" (situation and next sub goal), "rule" (updated theory of '
            'what unlocks what), "action_number" (the integer action).'
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
        number = parsed.get("action_number")
        if isinstance(number, int) and 0 <= number < len(ACTIONS):
            index = number
        else:
            index = _select(text, ACTIONS)

        # anti-spam cooldown: same action 4x with no novelty -> force different
        action_name = ACTIONS[index]
        if action_name == self.last_action:
            self.same_streak += 1
        else:
            self.same_streak = 0
        if self.same_streak >= 3 and self.steps_since_novelty >= 3 and not action_name.startswith("move"):
            alt = [i for i, a in enumerate(ACTIONS) if a != action_name]
            if alt:
                index = alt[0] if not experiment else alt[-1]
                self.same_streak = 0
        self.last_action = ACTIONS[index]
        tag = " | EXPERIMENT" if experiment else ""
        return index, f"belief={self.belief[:60]} | rule={self.rule[:50]}{tag}"
