"""Load and validate the supplied input files.

Public request rows and private driver rows are kept in separate types so the
simulator can pass each driver only its own private row.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .config import DAY_END_BOUNDARY, KWH_PER_SLOT, Policy

VALID_TYPES = {"urgent", "flexible"}
VALID_STRATEGIES = {"release", "hold", "reciprocal", "fee_aware"}


@dataclass(frozen=True)
class Request:
    """One public charging request (visible to the queue at its arrival boundary)."""
    request_id: str
    day: int
    driver_id: str
    arrival: int
    departure: int
    requested_kwh: float


@dataclass(frozen=True)
class DriverProfile:
    """One private driver row. Only its own driver and the evaluator may read it."""
    driver_id: str
    private_type: str
    v: float   # value per kWh
    w: float   # cost per waiting slot
    h: float   # benefit per idle (held) slot
    strategy: str


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_requests(path: Path, scenario: str | None = None) -> dict[int, list[Request]]:
    """Return requests grouped by day. ``scenario`` filters sessions_public.csv;
    the mini-case file has no scenario/day columns and is loaded as day 1."""
    by_day: dict[int, list[Request]] = defaultdict(list)
    for row in _read_csv(path):
        if scenario is not None and row.get("scenario") != scenario:
            continue
        req = Request(
            request_id=row["request_id"],
            day=int(row.get("day", 1)),
            driver_id=row["driver_id"],
            arrival=int(row["arrival_slot"]),
            departure=int(row["departure_slot"]),
            requested_kwh=float(row["requested_kwh"]),
        )
        by_day[req.day].append(req)
    return dict(sorted(by_day.items()))


def load_drivers(path: Path, default_strategy: str = "release") -> dict[str, DriverProfile]:
    """The mini-case private file has no strategy column; actions there are fixed
    by the caller, so a placeholder strategy is used."""
    drivers = {}
    for row in _read_csv(path):
        drivers[row["driver_id"]] = DriverProfile(
            driver_id=row["driver_id"],
            private_type=row["private_type"],
            v=float(row["value_per_kwh"]),
            w=float(row["wait_cost_per_slot"]),
            h=float(row["idle_benefit_per_slot"]),
            strategy=row.get("private_strategy", default_strategy),
        )
    return drivers


def load_policies(path: Path) -> dict[str, Policy]:
    return {
        r["policy_id"]: Policy(r["policy_id"], r["name"], float(r["fee_per_idle_slot"]), r["use_history"] == "1")
        for r in _read_csv(path)
    }


def load_chargers(path: Path) -> list[dict]:
    return [{"charger_id": r["charger_id"], "power_kw": float(r["power_kw"])} for r in _read_csv(path)]


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_inputs(requests: dict[int, list[Request]], drivers: dict[str, DriverProfile]) -> list[str]:
    """Return a list of problems (empty list = inputs pass the checks)."""
    problems = []
    for day, reqs in requests.items():
        ids = [r.driver_id for r in reqs]
        if len(ids) != len(set(ids)):
            problems.append(f"day {day}: a driver has more than one request")
        for r in reqs:
            if r.driver_id not in drivers:
                problems.append(f"{r.request_id}: unknown driver {r.driver_id}")
            if not 0 <= r.arrival < r.departure <= DAY_END_BOUNDARY:
                problems.append(f"{r.request_id}: bad arrival/departure {r.arrival}/{r.departure}")
            if r.requested_kwh <= 0:
                problems.append(f"{r.request_id}: non-positive request")
            if r.requested_kwh > KWH_PER_SLOT * (r.departure - r.arrival):
                problems.append(f"{r.request_id}: request cannot fit before departure")
    for d in drivers.values():
        if d.private_type not in VALID_TYPES:
            problems.append(f"{d.driver_id}: unknown type {d.private_type}")
        if d.strategy not in VALID_STRATEGIES:
            problems.append(f"{d.driver_id}: unknown strategy {d.strategy}")
    return problems
