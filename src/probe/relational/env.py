from __future__ import annotations

import random


COLORS = ["red", "blue", "green"]
KEYS = ["A", "B"]


class RelationalEnv:
    def __init__(self, horizon: int = 24, seed: int = 0):
        self.horizon = horizon
        self.rng = random.Random(seed)
        self.rule: dict[str, str] = {}
        self.item_a = ""
        self.item_b = ""
        self.step_count = 0

    def reset(self) -> dict:
        self.step_count = 0
        keys = KEYS[:]
        self.rng.shuffle(keys)
        self.rule = {"same": keys[0], "different": keys[1]}
        self._new_cue()
        return self._observation()

    def _new_cue(self) -> None:
        self.item_a = self.rng.choice(COLORS)
        self.item_b = self.rng.choice(COLORS)

    def step(self, key: str):
        relation = "same" if self.item_a == self.item_b else "different"
        correct_key = self.rule[relation]
        reward = 1 if key == correct_key else 0
        a_before, b_before = self.item_a, self.item_b
        self.step_count += 1
        done = self.step_count >= self.horizon
        info = {
            "item_a": a_before,
            "item_b": b_before,
            "relation": relation,
            "correct_key": correct_key,
            "chosen_key": key,
        }
        self._new_cue()
        return self._observation(), reward, done, info

    def _observation(self) -> dict:
        return {
            "item_a": self.item_a,
            "item_b": self.item_b,
            "step": self.step_count,
            "horizon": self.horizon,
            "colors": COLORS,
            "keys": KEYS,
        }
