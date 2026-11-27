"""The four supplied driver rules.

Each rule is a function ``rule(own, memory, obs) -> idle_slots`` where

* ``own``    is the deciding driver's OWN private profile (type, v, w, h),
* ``memory`` is the driver's OWN last visit in this run (or None on a first visit),
* ``obs``    is the public information at the decision boundary.

No rule receives another driver's private row, strategy label or future arrivals.
The rules are programmed behaviour, not computed Nash equilibria.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .data import DriverProfile


@dataclass(frozen=True)
class LastVisit:
    """What a driver remembers about its own most recent visit."""
    fully_served: bool
    waiting_slots: int


@dataclass(frozen=True)
class Observation:
    """Public information available when a newly completed driver decides."""
    boundary: int                 # current boundary t
    fee: float                    # F, the posted idle fee per slot
    queue_length: int             # drivers currently waiting (public count only)
    legal_holds: tuple[int, ...]  # legal idle-slot choices, always includes 0


def legal_holds(boundary: int, departure: int, max_hold: int = 2) -> tuple[int, ...]:
    """Release (0), Hold 1 or Hold 2, as long as the hold ends no later than
    departure. Completion exactly at departure leaves only (0,), i.e. forced release."""
    return tuple(o for o in range(max_hold + 1) if boundary + o <= departure)


def release_rule(own: DriverProfile, memory: Optional[LastVisit], obs: Observation) -> int:
    return 0


def hold_rule(own: DriverProfile, memory: Optional[LastVisit], obs: Observation) -> int:
    return max(obs.legal_holds)   # largest legal hold, up to two slots


def reciprocal_rule(own: DriverProfile, memory: Optional[LastVisit], obs: Observation) -> int:
    if memory is None:                                   # first visit in this run
        return 0
    if memory.fully_served and memory.waiting_slots <= 2:
        return 0
    return 1 if 1 in obs.legal_holds else 0              # Hold 1 if legal, else Release


def fee_aware_rule(own: DriverProfile, memory: Optional[LastVisit], obs: Observation) -> int:
    """Maximise (h - F) * O over legal O; ties resolve to Release (smallest O)."""
    best_o, best_value = 0, 0.0
    for o in sorted(obs.legal_holds):
        value = (own.h - obs.fee) * o
        if value > best_value:            # strict: a tie keeps the smaller O
            best_o, best_value = o, value
    return best_o


Rule = Callable[[DriverProfile, Optional[LastVisit], Observation], int]

RULES: dict[str, Rule] = {
    "release": release_rule,
    "hold": hold_rule,
    "reciprocal": reciprocal_rule,
    "fee_aware": fee_aware_rule,
}
