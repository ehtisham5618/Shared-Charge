"""Evolutionary C/H task (project brief, section 5A).

x is the share choosing C (release); 1 - x choose H (hold one slot).
Everyone shares the same baseline payoffs; the private-type bonus is excluded.

    fC = 4x
    fH = (6 - F)x + (1 - F)(1 - x)
    x_next = x + 0.05 * x(1 - x)(fC - fH)
"""
from __future__ import annotations

STEP = 0.05
START = 0.5
UPDATES = 30


def fitness(x: float, fee: float) -> tuple[float, float]:
    f_c = 4 * x
    f_h = (6 - fee) * x + (1 - fee) * (1 - x)
    return f_c, f_h


def update(x: float, fee: float, step: float = STEP) -> float:
    f_c, f_h = fitness(x, fee)
    return x + step * x * (1 - x) * (f_c - f_h)


def trajectory(fee: float, start: float = START, updates: int = UPDATES) -> list[dict]:
    """Returns updates + 1 points including the starting share."""
    rows, x = [], start
    for k in range(updates + 1):
        f_c, f_h = fitness(x, fee)
        rows.append({"fee": fee, "update": k, "x_share_C": x, "share_H": 1 - x,
                     "fC": f_c, "fH": f_h, "fC_minus_fH": f_c - f_h})
        if k < updates:
            x = update(x, fee)
    return rows


def both_trajectories(fees=(0.0, 2.0)) -> list[dict]:
    return [row for fee in fees for row in trajectory(fee)]
