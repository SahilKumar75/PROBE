"""Internal Stage 0 environment: Boss I0."""

from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass
class BossI0Step:
    position: int
    target_here: bool
    reward: int
    done: bool
    step_count: int

    def as_dict(self) -> dict:
        return {
            "position": self.position,
            "target_here": self.target_here,
            "reward": self.reward,
            "done": self.done,
            "step_count": self.step_count,
        }


class BossI0:
    """A tiny 1D world with a single hidden target."""

    ACTIONS = ("move_left", "move_right")
    MAX_STEPS = 20

    def __init__(self, seed: int):
        self._rng = random.Random(seed)
        self.seed = seed
        self.position = 0
        self.target = 1
        self.step_count = 0

    def reset(self) -> dict:
        self.position = 0
        self.step_count = 0
        self.target = self._rng.choice((1, 2, 3, 4))
        return self._observation()

    def step(self, action: str) -> dict:
        if action not in self.ACTIONS:
            raise ValueError(f"Unsupported action: {action}")

        if action == "move_left":
            self.position = max(0, self.position - 1)
        elif action == "move_right":
            self.position = min(4, self.position + 1)

        self.step_count += 1
        success = self.position == self.target
        done = success or self.step_count >= self.MAX_STEPS
        reward = 1 if success else 0
        return BossI0Step(
            position=self.position,
            target_here=success,
            reward=reward,
            done=done,
            step_count=self.step_count,
        ).as_dict()

    def _observation(self) -> dict:
        return {
            "position": self.position,
            "target_here": self.position == self.target,
        }
