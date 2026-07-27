from __future__ import annotations

import itertools
import random


FEATURE_POOL = {
    "color": ["red", "green", "blue"],
    "shape": ["circle", "square", "triangle"],
    "fill": ["solid", "striped", "dotted"],
}
KEYS_POOL = ["A", "B", "C", "D", "E", "F"]

LEVELS = {
    "easy": {"factors": ["color", "shape"], "values": 2, "n_keys": 2, "relational": False},
    "medium": {"factors": ["color", "shape"], "values": 3, "n_keys": 3, "relational": False},
    "hard": {"factors": ["color", "shape", "fill"], "values": 2, "n_keys": 3, "relational": False},
    "hardest": {"factors": ["color", "shape", "fill"], "values": 3, "n_keys": 4, "relational": True},
}


def _sufficient(rule: dict, n_factors: int, index: int) -> bool:
    groups: dict = {}
    for combo, key in rule.items():
        groups.setdefault(combo[index], set()).add(key)
    return all(len(k) == 1 for k in groups.values())


def _build_rule(rng: random.Random, n_factors: int, n_values: int, keys: list[str], relational: bool) -> dict:
    combos = list(itertools.product(range(n_values), repeat=n_factors))
    match_key = keys[-1]
    for _ in range(400):
        rule = {combo: rng.choice(keys) for combo in combos}
        if relational:
            for combo in combos:
                if combo[0] == combo[1]:
                    rule[combo] = match_key
        reducible = any(_sufficient(rule, n_factors, i) for i in range(n_factors))
        if not reducible:
            return rule
    return rule


class InductionEnv:
    def __init__(self, level: str = "hardest", horizon: int | None = None, seed: int = 0):
        config = LEVELS[level]
        self.level = level
        self.factors = config["factors"]
        self.n_factors = len(self.factors)
        self.n_values = config["values"]
        self.relational = config["relational"]
        self.values = {f: FEATURE_POOL[f][: self.n_values] for f in self.factors}
        self.keys = KEYS_POOL[: config["n_keys"]]
        self.n_combos = self.n_values ** self.n_factors
        self.horizon = horizon if horizon is not None else 8 * self.n_combos
        self.rng = random.Random(seed)
        self.rule: dict = {}
        self.combo: tuple = ()
        self.step_count = 0

    def _cue_text(self, combo: tuple) -> str:
        return " ".join(self.values[self.factors[i]][combo[i]] for i in range(self.n_factors))

    def _cue_id(self, combo: tuple) -> str:
        return "|".join(str(v) for v in combo)

    def _space_text(self) -> str:
        parts = [f"{f} in ({', '.join(self.values[f])})" for f in self.factors]
        extra = "; a match on the first two features can matter" if self.relational else ""
        return "; ".join(parts) + extra

    def reset(self) -> dict:
        self.step_count = 0
        self.rule = _build_rule(self.rng, self.n_factors, self.n_values, self.keys, self.relational)
        self.combo = self.rng.choice(list(self.rule.keys()))
        return self._observation()

    def step(self, key: str):
        correct_key = self.rule[self.combo]
        reward = 1 if key == correct_key else 0
        combo_before = self.combo
        self.step_count += 1
        done = self.step_count >= self.horizon
        info = {
            "cue": self._cue_id(combo_before),
            "cue_text": self._cue_text(combo_before),
            "correct_key": correct_key,
            "chosen_key": key,
        }
        self.combo = self.rng.choice(list(self.rule.keys()))
        return self._observation(), reward, done, info

    def _observation(self) -> dict:
        return {
            "cue": self._cue_id(self.combo),
            "cue_text": self._cue_text(self.combo),
            "keys": self.keys,
            "space_text": self._space_text(),
            "step": self.step_count,
            "horizon": self.horizon,
        }
