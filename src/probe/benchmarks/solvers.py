from __future__ import annotations

import random


class EliminationSolver:
    def __init__(self, seed: int = 0):
        self.confirmed: dict[str, str] = {}
        self.ruled_out: dict[str, set[str]] = {}

    def reset(self) -> None:
        self.confirmed = {}
        self.ruled_out = {}

    def act(self, obs: dict) -> str:
        cue, keys = obs["cue"], obs["keys"]
        self.ruled_out.setdefault(cue, set())
        if cue in self.confirmed:
            return self.confirmed[cue]
        for key in keys:
            if key not in self.ruled_out[cue]:
                return key
        self.ruled_out[cue] = set()
        return keys[0]

    def update(self, cue: str, key: str, reward: int) -> None:
        self.ruled_out.setdefault(cue, set())
        if reward == 1:
            self.confirmed[cue] = key
            self.ruled_out[cue] = set()
        elif self.confirmed.get(cue) == key:
            del self.confirmed[cue]
            self.ruled_out[cue] = {key}
        else:
            self.ruled_out[cue].add(key)

    def memory(self) -> int:
        return len(self.confirmed) + sum(len(v) for v in self.ruled_out.values())


class MemorylessSolver:
    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def reset(self) -> None:
        pass

    def act(self, obs: dict) -> str:
        return self.rng.choice(obs["keys"])

    def update(self, cue: str, key: str, reward: int) -> None:
        pass

    def memory(self) -> int:
        return 0


class GreedyHistorySolver:
    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.last_good: dict[str, str] = {}

    def reset(self) -> None:
        self.last_good = {}

    def act(self, obs: dict) -> str:
        cue = obs["cue"]
        if cue in self.last_good:
            return self.last_good[cue]
        return self.rng.choice(obs["keys"])

    def update(self, cue: str, key: str, reward: int) -> None:
        if reward == 1:
            self.last_good[cue] = key

    def memory(self) -> int:
        return len(self.last_good)


SOLVERS = {
    "memoryless": MemorylessSolver,
    "greedy_history": GreedyHistorySolver,
    "probe_core": EliminationSolver,
}
