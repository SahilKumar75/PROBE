"""Observation interpreter for the ARC-AGI-3 boss.

Turns a raw 64x64x16-colour ARC frame into compact, NEUTRAL text for an LLM
agent. Neutral is the whole point: the agent must INFER what the colours and
the actions mean, so the interpreter never names a colour "player", "goal", or
"wall". It only reports symbols, positions, and what changed after the last
action. Discovering the semantics is the hidden rule PROBE is meant to solve.

An ARC frame is upscaled from a small logical grid (e.g. 8x8 -> 64x64 by an
integer factor plus a thin letterbox). We downsample back to the logical grid
so the text is small and faithful, then render it as a character map.
"""

from __future__ import annotations

import numpy as np

# 16 colours -> 16 distinct glyphs. 0 is background, rendered as '.' for
# readability; the rest are hex digits so the map stays one char per cell.
_GLYPHS = {0: "."}
for _i in range(1, 16):
    _GLYPHS[_i] = "0123456789abcdef"[_i]

_DIVISORS = (32, 16, 8, 4, 2, 1)


def _to_grid(frame) -> np.ndarray:
    """Take the last 2D grid out of an ARC frame (a list of 64x64 grids)."""
    arr = np.array(frame)
    if arr.ndim == 3:  # list of frames -> use the final one (current state)
        arr = arr[-1]
    return arr.astype(int)


def _detect_block(grid: np.ndarray) -> int:
    """Largest k (a divisor of the side) for which every kxk block is uniform.

    ARC upscales a small logical grid by an integer factor, so the real content
    lives at 1/k resolution. Recovering k lets us shrink 64x64 to the logical
    grid with no information loss.
    """
    h, w = grid.shape
    for k in _DIVISORS:
        if h % k or w % k:
            continue
        blocks = grid.reshape(h // k, k, w // k, k)
        # every block uniform iff its min == max
        if np.all(blocks.min(axis=(1, 3)) == blocks.max(axis=(1, 3))):
            return k
    return 1


def downsample(grid: np.ndarray) -> np.ndarray:
    """Shrink an upscaled ARC grid back to its logical resolution."""
    k = _detect_block(grid)
    return grid[::k, ::k]


def _render(small: np.ndarray) -> str:
    return "\n".join("".join(_GLYPHS.get(int(c), "?") for c in row) for row in small)


def _colour_counts(small: np.ndarray) -> dict[int, int]:
    vals, counts = np.unique(small, return_counts=True)
    return {int(v): int(c) for v, c in zip(vals, counts)}


def _changes(small: np.ndarray, prev: np.ndarray | None) -> str:
    """Describe what changed vs the previous logical grid (the action's effect)."""
    if prev is None or prev.shape != small.shape:
        return "no previous frame to compare"
    diff = np.argwhere(small != prev)
    if diff.size == 0:
        return "NOTHING changed on the grid after this action"
    parts = []
    for r, c in diff[:12]:  # cap so the text stays bounded
        parts.append(f"({r},{c}): {_GLYPHS.get(int(prev[r, c]),'?')}->{_GLYPHS.get(int(small[r, c]),'?')}")
    more = "" if len(diff) <= 12 else f" (+{len(diff) - 12} more cells)"
    return f"{len(diff)} cell(s) changed: " + ", ".join(parts) + more


def describe(frame, available_actions, state, score, prev_small: np.ndarray | None):
    """Build the text observation and return (text, current_small_grid).

    The caller keeps current_small_grid to pass back as prev_small next step, so
    the "what changed" line is always relative to the immediately prior frame.
    """
    grid = _to_grid(frame)
    small = downsample(grid)
    counts = _colour_counts(small)
    legend = ", ".join(f"'{_GLYPHS.get(c,'?')}'={n}" for c, n in sorted(counts.items()))
    acts = ", ".join(f"ACTION{a}" if a != 0 else "RESET" for a in available_actions)
    text = (
        f"Grid ({small.shape[0]}x{small.shape[1]}), each char is one cell, '.' is empty:\n"
        f"{_render(small)}\n"
        f"Symbol counts: {legend}\n"
        f"Game state: {state}. Score (levels cleared): {score}.\n"
        f"Available actions: {acts}.\n"
        f"Effect of your last action: {_changes(small, prev_small)}"
    )
    return text, small


def classify_effect(prev_small, cur_small) -> str:
    """Classify what an action did, as a compact fact for the action ledger.

    Returns "NOTHING changed" (exact string relied on by the agents), a
    movement fact like "moved '8' right", or "changed N cells".
    """
    if prev_small is None or cur_small is None or prev_small.shape != cur_small.shape:
        return "changed ? cells"
    diff = np.argwhere(prev_small != cur_small)
    if diff.size == 0:
        return "NOTHING changed"
    if len(diff) == 2:
        (r1, c1), (r2, c2) = diff
        a_old, a_new = int(prev_small[r1, c1]), int(cur_small[r1, c1])
        b_old, b_new = int(prev_small[r2, c2]), int(cur_small[r2, c2])
        # one glyph left cell A and appeared at cell B: a pure move
        if a_new == b_old and b_new == a_old:
            mover = a_old if b_new == a_old and a_old != 0 else b_new
            src, dst = ((r1, c1), (r2, c2)) if cur_small[r2, c2] == a_old else ((r2, c2), (r1, c1))
            if int(cur_small[dst[0], dst[1]]) != 0:
                mover = int(cur_small[dst[0], dst[1]])
                dr, dc = dst[0] - src[0], dst[1] - src[1]
                direction = (
                    "up" if dr < 0 and dc == 0 else "down" if dr > 0 and dc == 0
                    else "left" if dc < 0 and dr == 0 else "right" if dc > 0 and dr == 0
                    else f"({dr:+d},{dc:+d})"
                )
                return f"moved '{_GLYPHS.get(mover, '?')}' {direction}"
    return f"changed {len(diff)} cells"
