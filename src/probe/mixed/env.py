from __future__ import annotations

import random

from probe.multifactor.env import COLORS, KEYS, SHAPES, _build_rule


def _shifted_rule(rng, combos, colors, shapes, keys, current):
    for _ in range(200):
        candidate = _build_rule(rng, colors, shapes, keys)
        if all(candidate[c] != current[c] for c in combos):
            return candidate
    return {c: keys[(keys.index(current[c]) + 1) % len(keys)] for c in combos}


class MixedEnv:
    def __init__(self, n_colors: int = 3, n_shapes: int = 2, n_keys: int = 3, horizon: int | None = None, shift_step: int | None = None, seed: int = 0):
        self.colors = COLORS[:n_colors]
        self.shapes = SHAPES[:n_shapes]
        self.keys = KEYS[:n_keys]
        self.combos = [(c, s) for c in self.colors for s in self.shapes]
        self.horizon = horizon if horizon is not None else 12 * len(self.combos)
        self.shift_step = shift_step if shift_step is not None else self.horizon // 2
        self.rng = random.Random(seed)
        self.rule: dict[tuple[str, str], str] = {}
        self.color = ""
        self.shape = ""
        self.step_count = 0

    def reset(self) -> dict:
        self.step_count = 0
        self.rule = _build_rule(self.rng, self.colors, self.shapes, self.keys)
        self.color = self.rng.choice(self.colors)
        self.shape = self.rng.choice(self.shapes)
        return self._observation()

    def step(self, key: str):
        correct_key = self.rule[(self.color, self.shape)]
        reward = 1 if key == correct_key else 0
        color_before, shape_before = self.color, self.shape
        graded_step = self.step_count
        self.step_count += 1
        if self.step_count == self.shift_step:
            self.rule = _shifted_rule(self.rng, self.combos, self.colors, self.shapes, self.keys, self.rule)
        done = self.step_count >= self.horizon
        info = {
            "color": color_before,
            "shape": shape_before,
            "correct_key": correct_key,
            "chosen_key": key,
            "phase": "pre" if graded_step < self.shift_step else "post",
        }
        self.color = self.rng.choice(self.colors)
        self.shape = self.rng.choice(self.shapes)
        return self._observation(), reward, done, info

    def _observation(self) -> dict:
        return {
            "color": self.color,
            "shape": self.shape,
            "step": self.step_count,
            "horizon": self.horizon,
            "colors": self.colors,
            "shapes": self.shapes,
            "keys": self.keys,
        }
