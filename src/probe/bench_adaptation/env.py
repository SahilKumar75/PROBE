from __future__ import annotations

import random


COLOR_POOL = ["red", "green", "blue", "yellow", "purple", "orange", "cyan", "pink", "brown"]
SHAPE_POOL = ["circle", "square", "triangle", "star"]
KEYS_POOL = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

LEVELS = {
    "easy": {"multifactor": False, "n_symbols": 3, "n_shifts": 1},
    "medium": {"multifactor": False, "n_symbols": 6, "n_shifts": 1},
    "hard": {"multifactor": False, "n_symbols": 9, "n_shifts": 1},
    "hardest": {"multifactor": True, "n_colors": 3, "n_shapes": 2, "n_keys": 3, "n_shifts": 3},
}


def _reducible_multi(rule: dict) -> bool:
    for index in range(2):
        groups: dict = {}
        for combo, key in rule.items():
            groups.setdefault(combo[index], set()).add(key)
        if all(len(k) == 1 for k in groups.values()):
            return True
    return False


class AdaptationEnv:
    def __init__(self, level: str = "hardest", horizon: int | None = None, seed: int = 0):
        config = LEVELS[level]
        self.level = level
        self.multifactor = config["multifactor"]
        self.n_shifts = config["n_shifts"]
        self.rng = random.Random(seed)

        if self.multifactor:
            self.colors = COLOR_POOL[: config["n_colors"]]
            self.shapes = SHAPE_POOL[: config["n_shapes"]]
            self.keys = KEYS_POOL[: config["n_keys"]]
            self.cue_objects = [(c, s) for c in range(len(self.colors)) for s in range(len(self.shapes))]
        else:
            self.n_symbols = config["n_symbols"]
            self.cue_objects = COLOR_POOL[: self.n_symbols]
            self.keys = KEYS_POOL[: self.n_symbols]

        self.n_cues = len(self.cue_objects)
        self.horizon = horizon if horizon is not None else 8 * self.n_cues
        self.shift_steps = sorted(
            {max(1, round(self.horizon * (i + 1) / (self.n_shifts + 1))) for i in range(self.n_shifts)}
        )
        self.rule: dict = {}
        self.prev_rule: dict = {}
        self.segment = 0
        self.step_count = 0
        self.cue = None

    def _cue_id(self, cue) -> str:
        return f"{cue[0]}|{cue[1]}" if self.multifactor else str(cue)

    def _cue_text(self, cue) -> str:
        if self.multifactor:
            return f"{self.colors[cue[0]]} {self.shapes[cue[1]]}"
        return str(cue)

    def _space_text(self) -> str:
        if self.multifactor:
            return f"color in ({', '.join(self.colors)}); shape in ({', '.join(self.shapes)})"
        return f"cues in ({', '.join(self.cue_objects)})"

    def _build_initial(self) -> dict:
        if self.multifactor:
            for _ in range(400):
                rule = {combo: self.rng.choice(self.keys) for combo in self.cue_objects}
                if not _reducible_multi(rule):
                    return rule
            return rule
        shuffled = self.keys[:]
        self.rng.shuffle(shuffled)
        return dict(zip(self.cue_objects, shuffled))

    def _derange(self, rule: dict) -> dict:
        ids = list(rule.keys())
        if self.multifactor:
            for _ in range(400):
                candidate = {i: self.rng.choice([k for k in self.keys if k != rule[i]]) for i in ids}
                if not _reducible_multi(candidate):
                    return candidate
            return {i: self.keys[(self.keys.index(rule[i]) + 1) % len(self.keys)] for i in ids}
        for _ in range(400):
            shuffled = self.keys[:]
            self.rng.shuffle(shuffled)
            candidate = dict(zip(ids, shuffled))
            if all(candidate[i] != rule[i] for i in ids):
                return candidate
        return {i: rule[ids[(index + 1) % len(ids)]] for index, i in enumerate(ids)}

    def reset(self) -> dict:
        self.step_count = 0
        self.segment = 0
        self.prev_rule = {}
        self.rule = self._build_initial()
        self.cue = self.rng.choice(self.cue_objects)
        return self._observation()

    def step(self, key: str):
        cue_before = self.cue
        segment_before = self.segment
        correct_key = self.rule[cue_before]
        reward = 1 if key == correct_key else 0
        old_correct_key = self.prev_rule.get(cue_before, "") if segment_before > 0 else ""

        self.step_count += 1
        shifted_now = self.step_count in self.shift_steps
        if shifted_now:
            self.prev_rule = dict(self.rule)
            self.rule = self._derange(self.rule)
            self.segment += 1

        done = self.step_count >= self.horizon
        info = {
            "cue": self._cue_id(cue_before),
            "cue_text": self._cue_text(cue_before),
            "correct_key": correct_key,
            "old_correct_key": old_correct_key,
            "chosen_key": key,
            "shifted_now": shifted_now,
            "segment": segment_before,
        }
        self.cue = self.rng.choice(self.cue_objects)
        return self._observation(), reward, done, info

    def _observation(self) -> dict:
        return {
            "cue": self._cue_id(self.cue),
            "cue_text": self._cue_text(self.cue),
            "keys": self.keys,
            "space_text": self._space_text(),
            "step": self.step_count,
            "horizon": self.horizon,
        }
