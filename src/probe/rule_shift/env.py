from __future__ import annotations

import random


CUES_POOL = ["red", "green", "blue", "yellow", "purple", "orange", "cyan", "pink", "brown"]
KEYS_POOL = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]


def _random_mapping(rng: random.Random, cues: list[str], keys: list[str]) -> dict[str, str]:
    shuffled = keys[:]
    rng.shuffle(shuffled)
    return dict(zip(cues, shuffled))


def _shifted_mapping(rng: random.Random, current: dict[str, str], cues: list[str], keys: list[str]) -> dict[str, str]:
    for _ in range(200):
        candidate = _random_mapping(rng, cues, keys)
        if all(candidate[cue] != current[cue] for cue in cues):
            return candidate
    return {cue: current[cues[(index + 1) % len(cues)]] for index, cue in enumerate(cues)}


class RuleShiftEnv:
    def __init__(self, n_symbols: int = 3, horizon: int | None = None, shift_step: int | None = None, seed: int = 0):
        self.cues = CUES_POOL[:n_symbols]
        self.keys = KEYS_POOL[:n_symbols]
        self.n_symbols = n_symbols
        self.horizon = horizon if horizon is not None else 8 * n_symbols
        self.shift_step = shift_step if shift_step is not None else self.horizon // 2
        self.rng = random.Random(seed)
        self.rule: dict[str, str] = {}
        self.cue = ""
        self.step_count = 0
        self.has_shifted = False

    def reset(self) -> dict:
        self.step_count = 0
        self.has_shifted = False
        self.rule = _random_mapping(self.rng, self.cues, self.keys)
        self.cue = self.rng.choice(self.cues)
        return self._observation()

    def step(self, key: str):
        correct_key = self.rule[self.cue]
        reward = 1 if key == correct_key else 0
        cue_before = self.cue
        rule_before = dict(self.rule)

        self.step_count += 1
        shifted_now = self.step_count == self.shift_step
        if shifted_now:
            self.rule = _shifted_mapping(self.rng, self.rule, self.cues, self.keys)
            self.has_shifted = True

        done = self.step_count >= self.horizon
        info = {
            "cue": cue_before,
            "correct_key": correct_key,
            "chosen_key": key,
            "shifted_now": shifted_now,
            "has_shifted": self.has_shifted,
            "rule_before_step": rule_before,
            "rule_after_step": dict(self.rule),
        }
        self.cue = self.rng.choice(self.cues)
        return self._observation(), reward, done, info

    def _observation(self) -> dict:
        return {
            "cue": self.cue,
            "step": self.step_count,
            "horizon": self.horizon,
            "cues": self.cues,
            "keys": self.keys,
        }
