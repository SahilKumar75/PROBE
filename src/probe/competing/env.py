from __future__ import annotations

import random


COLORS = ["red", "blue"]
SHAPES = ["circle", "square"]
KEYS = ["A", "B"]
CONFOUND = {"red": "circle", "blue": "square"}


class CompetingHypothesesEnv:
    def __init__(self, horizon: int = 30, shift_step: int = 10, seed: int = 0):
        self.horizon = horizon
        self.shift_step = shift_step
        self.rng = random.Random(seed)
        self.true_feature = "color"
        self.true_map: dict[str, str] = {}
        self.color = ""
        self.shape = ""
        self.step_count = 0

    def reset(self) -> dict:
        self.step_count = 0
        self.true_feature = self.rng.choice(["color", "shape"])
        keys = KEYS[:]
        self.rng.shuffle(keys)
        values = COLORS if self.true_feature == "color" else SHAPES
        self.true_map = dict(zip(values, keys))
        self._new_cue()
        return self._observation()

    def _new_cue(self) -> None:
        if self.step_count < self.shift_step:
            color = self.rng.choice(COLORS)
            self.color, self.shape = color, CONFOUND[color]
        else:
            self.color = self.rng.choice(COLORS)
            self.shape = self.rng.choice(SHAPES)

    def step(self, key: str):
        value = self.color if self.true_feature == "color" else self.shape
        correct_key = self.true_map[value]
        reward = 1 if key == correct_key else 0
        color_before, shape_before = self.color, self.shape
        graded_step = self.step_count
        self.step_count += 1
        done = self.step_count >= self.horizon
        info = {
            "color": color_before,
            "shape": shape_before,
            "correct_key": correct_key,
            "chosen_key": key,
            "phase": "ambiguous" if graded_step < self.shift_step else "disambiguating",
            "true_feature": self.true_feature,
        }
        self._new_cue()
        return self._observation(), reward, done, info

    def _observation(self) -> dict:
        return {
            "color": self.color,
            "shape": self.shape,
            "step": self.step_count,
            "horizon": self.horizon,
            "colors": COLORS,
            "shapes": SHAPES,
            "keys": KEYS,
        }
