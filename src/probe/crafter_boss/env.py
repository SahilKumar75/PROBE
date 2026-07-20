from __future__ import annotations

import crafter


ACTIONS = list(crafter.constants.actions)
INTEREST = ["tree", "stone", "coal", "iron", "diamond", "water", "lava", "cow", "zombie", "skeleton", "table", "furnace", "plant"]


def make_env(seed: int):
    return crafter.Env(seed=seed)


def id_to_name(env) -> dict[int, str]:
    view = env._sem_view
    mapping = {value: name for name, value in view._mat_ids.items()}
    for cls, index in view._obj_ids.items():
        mapping[index] = cls.__name__.lower()
    return mapping


def _direction(dx: int, dy: int) -> str:
    parts = []
    if dy < 0:
        parts.append(f"{-dy} up")
    elif dy > 0:
        parts.append(f"{dy} down")
    if dx < 0:
        parts.append(f"{-dx} left")
    elif dx > 0:
        parts.append(f"{dx} right")
    return " and ".join(parts) if parts else "on your tile"


def describe(info: dict, idmap: dict[int, str], radius: int = 5) -> dict:
    inv = info["inventory"]
    vitals = f"health {inv['health']}, food {inv['food']}, drink {inv['drink']}, energy {inv['energy']}"
    resources = {k: v for k, v in inv.items() if k not in ("health", "food", "drink", "energy") and v > 0}
    achievements = [k for k, v in info["achievements"].items() if v > 0]

    sem = info["semantic"]
    px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
    height, width = sem.shape
    nearest: dict[str, tuple[int, int, int]] = {}
    for x in range(max(0, px - radius), min(height, px + radius + 1)):
        for y in range(max(0, py - radius), min(width, py + radius + 1)):
            name = idmap.get(int(sem[x, y]))
            if name in INTEREST:
                distance = abs(x - px) + abs(y - py)
                if name not in nearest or distance < nearest[name][0]:
                    nearest[name] = (distance, x - px, y - py)
    nearby = "; ".join(
        f"{name} ({_direction(dx, dy)})"
        for name, (dist, dx, dy) in sorted(nearest.items(), key=lambda kv: kv[1][0])
    )

    return {
        "vitals": vitals,
        "resources": resources or "none",
        "achievements": achievements or "none yet",
        "nearby": nearby or "nothing notable within view",
    }
