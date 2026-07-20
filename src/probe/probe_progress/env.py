from __future__ import annotations

import random


TARGETS = ["T1", "T2", "T3"]
SAFE_REWARD = 1.0
COMMIT_CORRECT = 3.0
COMMIT_WRONG = -1.0


def action_set() -> list[str]:
    return ["safe", "probe"] + [f"commit_{t}" for t in TARGETS]


class ProbeOrProgressEnv:
    def __init__(self, horizon: int = 20, seed: int = 0):
        self.horizon = horizon
        self.rng = random.Random(seed)
        self.target = "T1"
        self.revealed = False
        self.step_count = 0

    def reset(self) -> dict:
        self.step_count = 0
        self.revealed = False
        self.target = self.rng.choice(TARGETS)
        return self._observation()

    def step(self, action: str):
        reward = 0.0
        if action == "safe":
            reward = SAFE_REWARD
        elif action == "probe":
            self.revealed = True
            reward = 0.0
        elif action.startswith("commit_"):
            reward = COMMIT_CORRECT if action == f"commit_{self.target}" else COMMIT_WRONG
        self.step_count += 1
        done = self.step_count >= self.horizon
        info = {"action": action, "reward": reward, "target": self.target, "revealed": self.revealed}
        return self._observation(), reward, done, info

    def _observation(self) -> dict:
        return {
            "actions": action_set(),
            "revealed": self.revealed,
            "known_target": self.target if self.revealed else None,
            "step": self.step_count,
            "horizon": self.horizon,
        }
