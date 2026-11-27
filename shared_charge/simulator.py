"""Boundary-by-boundary charging-queue engine.

Event order at every boundary t = 0 .. end (project brief, section 1):

  1. Finish energy delivered during the previous slot [t-1, t).
  2. Remove drivers whose departure time is t (including incomplete charges and
     drivers who never started).
  3. Ask each newly completed driver who can stay for Release / Hold 1 / Hold 2.
  4. End earlier holds that expire at t.
  5. Add new arrivals to the queue.
  6. Allocate free chargers by (arrival time, driver ID).
  7. Charge during the next slot [t, t+1). There is no slot after the end boundary.

Utility = v*kWh - w*waiting_slots + h*idle_slots - F*idle_slots
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .config import KWH_PER_SLOT, MAX_HOLD_SLOTS
from .data import DriverProfile, Request
from .strategies import RULES, LastVisit, Observation, legal_holds

# Outcome labels saved in the 'action' column
RELEASE, HOLD_1, HOLD_2 = "release", "hold_1", "hold_2"
FORCED_RELEASE = "forced_release"        # completed exactly at departure: no choice
INCOMPLETE = "departed_incomplete"       # started but left before the request was met
UNSERVED = "unserved"                    # never reached a charger


@dataclass
class Visit:
    request: Request
    profile: DriverProfile
    charger: Optional[str] = None
    start: Optional[int] = None
    finish: Optional[int] = None       # boundary at which the request was fully met
    release: Optional[int] = None      # boundary at which the charger was freed
    delivered_kwh: float = 0.0
    idle_slots: int = 0
    hold_end: Optional[int] = None
    action: Optional[str] = None
    state: str = "pending"             # pending/waiting/charging/holding/done
    charged_slots: list = field(default_factory=list)  # slots t in which energy flowed

    @property
    def remaining(self) -> float:
        return self.request.requested_kwh - self.delivered_kwh

    @property
    def waiting_slots(self) -> int:
        end = self.start if self.start is not None else self.request.departure
        return end - self.request.arrival


def visit_record(v: Visit, fee: float) -> dict:
    """Flatten one finished visit into a saved row (None = missing value)."""
    p = v.profile
    wait = v.waiting_slots
    gross = p.v * v.delivered_kwh - p.w * wait + p.h * v.idle_slots
    penalty = fee * v.idle_slots
    return {
        "day": v.request.day,
        "request_id": v.request.request_id,
        "driver_id": p.driver_id,
        "driver_type": p.private_type,
        "strategy": p.strategy,
        "arrival": v.request.arrival,
        "departure": v.request.departure,
        "charger_id": v.charger,
        "start": v.start,
        "finish": v.finish,
        "release": v.release,
        "requested_kwh": v.request.requested_kwh,
        "delivered_kwh": v.delivered_kwh,
        "waiting_slots": wait,
        "action": v.action,
        "idle_slots": v.idle_slots,
        "fee": fee,
        "penalty": penalty,
        "gross_utility": gross,
        "net_utility": gross - penalty,
        "fully_served": v.delivered_kwh >= v.request.requested_kwh,
    }


class DaySimulator:
    """Simulates one day for one site. Queues are fresh every day; driver memory
    (for the Reciprocal rule) is passed in and updated by the caller."""

    def __init__(
        self,
        requests: list[Request],
        profiles: dict[str, DriverProfile],
        memory: dict[str, LastVisit],
        fee: float,
        charger_ids: list[str],
        end_boundary: int,
        kwh_per_slot: float = KWH_PER_SLOT,
        fixed_actions: Optional[dict[str, int]] = None,
    ):
        self.visits = [Visit(r, profiles[r.driver_id]) for r in requests]
        self.memory = memory
        self.fee = fee
        self.chargers: dict[str, Optional[Visit]] = {c: None for c in sorted(charger_ids)}
        self.end = end_boundary
        self.kwh = kwh_per_slot
        self.fixed_actions = fixed_actions or {}
        self.timeline: list[dict] = []   # per-slot charger occupancy (for checks/UI)

    # -- helpers -----------------------------------------------------------
    def _free(self, v: Visit, t: int) -> None:
        self.chargers[v.charger] = None
        v.release = t
        v.state = "done"

    def _decide(self, v: Visit, t: int) -> int:
        """Ask a newly completed driver for its single hold decision."""
        options = legal_holds(t, v.request.departure, MAX_HOLD_SLOTS)
        if v.profile.driver_id in self.fixed_actions:
            choice = self.fixed_actions[v.profile.driver_id]
        else:
            obs = Observation(
                boundary=t,
                fee=self.fee,
                queue_length=sum(1 for x in self.visits if x.state == "waiting"),
                legal_holds=options,
            )
            # The rule sees only its own profile and its own memory.
            rule = RULES[v.profile.strategy]
            choice = rule(v.profile, self.memory.get(v.profile.driver_id), obs)
        if choice not in options:
            raise ValueError(f"illegal hold {choice} for {v.request.request_id} at t={t}; legal={options}")
        return choice

    # -- main loop ---------------------------------------------------------
    def run(self) -> list[Visit]:
        for t in range(0, self.end + 1):
            # 1. finish energy from slot [t-1, t)
            newly_completed = []
            if t > 0:
                for v in self.chargers.values():
                    if v is not None and v.state == "charging":
                        v.delivered_kwh += min(self.kwh, v.remaining)
                        v.charged_slots.append(t - 1)
                        if v.remaining <= 1e-9:
                            v.finish = t
                            newly_completed.append(v)

            # 2. departures (everyone whose departure boundary is t leaves now)
            for v in self.visits:
                if v.request.departure != t or v.state in ("pending", "done"):
                    continue
                if v.state == "waiting":
                    v.action = UNSERVED
                    v.state = "done"
                elif v.state == "charging" and v.finish == t:
                    v.action = FORCED_RELEASE          # completed exactly at departure
                    self._free(v, t)
                elif v.state == "charging":
                    v.action = INCOMPLETE
                    self._free(v, t)
                elif v.state == "holding":             # hold always ends by departure
                    self._free(v, t)

            # 3. single hold decision from newly completed drivers who can stay
            for v in sorted(newly_completed, key=lambda x: x.profile.driver_id):
                if v.state != "charging":
                    continue                           # already left at step 2
                o = self._decide(v, t)
                v.idle_slots = o
                v.action = (RELEASE, HOLD_1, HOLD_2)[o]
                if o == 0:
                    self._free(v, t)
                else:
                    v.state = "holding"
                    v.hold_end = t + o

            # 4. end earlier holds that expire now
            for v in self.chargers.values():
                if v is not None and v.state == "holding" and v.hold_end == t:
                    self._free(v, t)

            if t == self.end:
                break                                  # no slot after the last boundary

            # 5. arrivals join the queue
            for v in self.visits:
                if v.state == "pending" and v.request.arrival == t:
                    v.state = "waiting"

            # 6. allocate free chargers by arrival time, then driver ID
            queue = sorted((v for v in self.visits if v.state == "waiting"),
                           key=lambda x: (x.request.arrival, x.profile.driver_id))
            for cid in self.chargers:
                if self.chargers[cid] is None and queue:
                    v = queue.pop(0)
                    v.charger, v.start, v.state = cid, t, "charging"
                    self.chargers[cid] = v

            # 7. record the slot [t, t+1) occupancy; energy is added at step 1 of t+1
            for cid, v in self.chargers.items():
                if v is not None:
                    self.timeline.append({"slot": t, "charger_id": cid,
                                          "driver_id": v.profile.driver_id, "state": v.state})

        # anyone still pending/waiting at the end (cannot happen with departure <= end)
        for v in self.visits:
            if v.state != "done":
                raise RuntimeError(f"visit {v.request.request_id} not closed at end of day")
        return self.visits


def update_memory(memory: dict[str, LastVisit], visits: list[Visit]) -> None:
    """Store each driver's most recent visit. Days without a visit leave memory unchanged."""
    for v in visits:
        memory[v.profile.driver_id] = LastVisit(
            fully_served=v.delivered_kwh >= v.request.requested_kwh,
            waiting_slots=v.waiting_slots,
        )


def simulate_run(
    requests_by_day: dict[int, list[Request]],
    profiles: dict[str, DriverProfile],
    fee: float,
    charger_ids: list[str],
    end_boundary: int,
    strategy_override: Optional[str] = None,
    fixed_actions: Optional[dict[str, int]] = None,
    keep_timeline: bool = False,
):
    """Run all days of one experiment from a fresh state.

    Returns (visit rows, timeline rows). ``strategy_override`` replaces every
    driver's rule (used by the fixed-Hold control) without touching the input file.
    """
    if strategy_override is not None:
        profiles = {k: DriverProfile(p.driver_id, p.private_type, p.v, p.w, p.h, strategy_override)
                    for k, p in profiles.items()}
    memory: dict[str, LastVisit] = {}          # fresh per run; kept across days
    rows, timeline = [], []
    for day, reqs in sorted(requests_by_day.items()):
        sim = DaySimulator(reqs, profiles, memory, fee, charger_ids, end_boundary,
                           fixed_actions=fixed_actions)
        visits = sim.run()
        update_memory(memory, visits)
        rows.extend(visit_record(v, fee) for v in visits)
        if keep_timeline:
            timeline.extend({"day": day, **x} for x in sim.timeline)
    return rows, timeline
