from __future__ import annotations

import random


COLORS = ["red", "green", "blue", "yellow"]
SHAPES = ["circle", "square", "triangle", "star"]
KEYS = ["A", "B", "C", "D"]


def _build_rule(rng: random.Random, colors: list[str], shapes: list[str], keys: list[str]) -> dict[tuple[str, str], str]:
    for _ in range(200):
        rule = {(c, s): rng.choice(keys) for c in colors for s in shapes}
        color_reducible = all(len({rule[(c, s)] for s in shapes}) == 1 for c in colors)
        shape_reducible = all(len({rule[(c, s)] for c in colors}) == 1 for s in shapes)
        if not color_reducible and not shape_reducible:
            return rule
    return rule


class MultiFactorEnv:
    def __init__(self, n_colors: int = 3, n_shapes: int = 2, n_keys: int = 3, horizon: int | None = None, seed: int = 0):
        self.colors = COLORS[:n_colors]
        self.shapes = SHAPES[:n_shapes]
        self.keys = KEYS[:n_keys]
        self.n_combos = n_colors * n_shapes
        self.horizon = horizon if horizon is not None else 8 * self.n_combos
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
        self.step_count += 1
        done = self.step_count >= self.horizon
        info = {
            "color": color_before,
            "shape": shape_before,
            "correct_key": correct_key,
            "chosen_key": key,
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
