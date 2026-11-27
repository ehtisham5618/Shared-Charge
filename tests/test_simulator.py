"""Unit tests for queue rules, holds, strategies and utility."""
import inspect
from collections import Counter

import pytest

from conftest import driver, req
from shared_charge import config as C
from shared_charge.data import load_drivers, load_requests
from shared_charge.simulator import DaySimulator, simulate_run
from shared_charge.strategies import (LastVisit, Observation, RULES, fee_aware_rule, hold_rule,
                                      legal_holds, reciprocal_rule)


def run_day(requests, drivers, fee=0, chargers=1, end=16, fixed=None):
    rows, timeline = simulate_run({1: requests}, {d.driver_id: d for d in drivers}, fee,
                                  [f"C{i:02}" for i in range(1, chargers + 1)], end,
                                  fixed_actions=fixed, keep_timeline=True)
    return {r["driver_id"]: r for r in rows}, timeline


# ------------------------------------------------------------- queue order
def test_allocation_by_arrival_then_driver_id():
    drivers = [driver("B"), driver("A"), driver("C")]
    rows, _ = run_day([req("B", 0, 10, 3), req("A", 0, 10, 3), req("C", 0, 10, 3)], drivers)
    assert (rows["A"]["start"], rows["B"]["start"], rows["C"]["start"]) == (0, 1, 2)


def test_earlier_arrival_beats_lower_id():
    rows, _ = run_day([req("A", 1, 10, 3), req("Z", 0, 10, 3)], [driver("A"), driver("Z")])
    assert rows["Z"]["start"] == 0 and rows["A"]["start"] == 1


def test_arrival_not_served_before_arrival_boundary():
    rows, _ = run_day([req("A", 5, 10, 3)], [driver("A")], chargers=6)
    assert rows["A"]["start"] == 5 and rows["A"]["waiting_slots"] == 0


def test_multiple_chargers_fill_in_charger_order():
    ds = [driver(x) for x in "ABC"]
    rows, _ = run_day([req(x, 0, 10, 3) for x in "ABC"], ds, chargers=2)
    assert {rows["A"]["charger_id"], rows["B"]["charger_id"]} == {"C01", "C02"}
    assert rows["C"]["start"] == 1


# ------------------------------------------------------------- energy and departure
def test_energy_never_exceeds_request_and_finish_time():
    rows, _ = run_day([req("A", 0, 10, 9)], [driver("A")])
    assert rows["A"]["delivered_kwh"] == 9 and rows["A"]["finish"] == 3


def test_completion_exactly_at_departure_is_forced_release():
    rows, _ = run_day([req("A", 0, 3, 9)], [driver("A", strategy="hold")])
    a = rows["A"]
    assert (a["finish"], a["release"], a["delivered_kwh"], a["action"]) == (3, 3, 9, "forced_release")


def test_departed_incomplete_has_missing_finish():
    # A (lower ID) charges 0-1; B starts at 1 and must leave at 3 with 6 of 9 kWh
    rows, _ = run_day([req("A", 0, 5, 3), req("B", 0, 3, 9)], [driver("A"), driver("B")])
    b = rows["B"]
    assert (b["start"], b["finish"], b["release"], b["delivered_kwh"]) == (1, None, 3, 6)
    assert b["action"] == "departed_incomplete" and b["waiting_slots"] == 1


def test_unserved_driver_waits_arrival_to_departure_and_pays_cost():
    rows, _ = run_day([req("A", 0, 10, 18), req("B", 1, 4, 3)], [driver("A"), driver("B", "urgent")])
    b = rows["B"]
    assert b["action"] == "unserved" and b["start"] is None and b["release"] is None
    assert b["waiting_slots"] == 3 and b["net_utility"] == -9


def test_no_charging_after_last_boundary():
    rows, tl = run_day([req("A", 8, 16, 18), req("B", 8, 16, 18)], [driver("A"), driver("B")])
    assert max(t["slot"] for t in tl) == 15
    assert rows["B"]["action"] == "unserved" or rows["B"]["start"] <= 15


# ------------------------------------------------------------- holds
def test_legal_holds():
    assert legal_holds(5, 8) == (0, 1, 2)
    assert legal_holds(5, 6) == (0, 1)
    assert legal_holds(5, 5) == (0,)        # completion at departure forces release


def test_hold_two_expires_on_time_and_blocks_charger():
    rows, tl = run_day([req("A", 0, 10, 3), req("B", 0, 10, 3)],
                       [driver("A", strategy="hold"), driver("B")])
    a = rows["A"]
    assert a["finish"] == 1 and a["release"] == 3 and a["idle_slots"] == 2 and a["action"] == "hold_2"
    assert rows["B"]["start"] == 3
    states = [(t["slot"], t["state"]) for t in tl if t["driver_id"] == "A"]
    assert states == [(0, "charging"), (1, "holding"), (2, "holding")]


def test_hold_limited_by_departure():
    rows, _ = run_day([req("A", 0, 2, 3)], [driver("A", strategy="hold")])
    assert rows["A"]["idle_slots"] == 1 and rows["A"]["release"] == 2


def test_forced_release_when_completed_at_departure():
    rows, _ = run_day([req("A", 0, 1, 3)], [driver("A", strategy="hold")])
    assert rows["A"]["action"] == "forced_release" and rows["A"]["idle_slots"] == 0


def test_illegal_fixed_hold_rejected():
    with pytest.raises(ValueError):
        run_day([req("A", 0, 2, 3)], [driver("A")], fixed={"A": 2})


def test_no_energy_during_hold():
    rows, tl = run_day([req("A", 0, 10, 6)], [driver("A", strategy="hold")])
    charging = sum(1 for t in tl if t["state"] == "charging")
    assert charging * 3 == rows["A"]["delivered_kwh"] == 6


# ------------------------------------------------------------- strategies
def obs(fee=0.0, legal=(0, 1, 2)):
    return Observation(boundary=4, fee=fee, queue_length=0, legal_holds=legal)


def test_hold_rule_takes_largest_legal():
    assert hold_rule(driver("A"), None, obs()) == 2
    assert hold_rule(driver("A"), None, obs(legal=(0, 1))) == 1


@pytest.mark.parametrize("kind,fee,expected", [
    ("flexible", 0, 2), ("urgent", 0, 2),      # h > 0 -> hold as long as legal
    ("flexible", 2, 0),                         # h - F = 0 -> tie -> release
    ("urgent", 2, 0),                           # h - F < 0 -> release
    ("flexible", 1, 2), ("urgent", 1, 0),       # tie for urgent at F=1
])
def test_fee_aware(kind, fee, expected):
    assert fee_aware_rule(driver("A", kind), None, obs(fee)) == expected


def test_reciprocal_rule():
    d = driver("A")
    assert reciprocal_rule(d, None, obs()) == 0
    assert reciprocal_rule(d, LastVisit(True, 2), obs()) == 0
    assert reciprocal_rule(d, LastVisit(True, 3), obs()) == 1
    assert reciprocal_rule(d, LastVisit(False, 0), obs()) == 1
    assert reciprocal_rule(d, LastVisit(False, 0), obs(legal=(0,))) == 0


def test_reciprocal_memory_kept_across_days_and_skipped_days():
    a, b = driver("A", strategy="reciprocal"), driver("B")
    days = {
        1: [req("B", 0, 10, 18, day=1), req("A", 1, 5, 3, day=1)],   # B blocks; A unserved
        2: [req("B", 0, 10, 3, day=2)],                               # A absent on day 2
        3: [req("A", 0, 10, 3, day=3)],                               # A remembers day 1
    }
    rows, _ = simulate_run(days, {"A": a, "B": b}, 0, ["C01"], 16)
    day3 = [r for r in rows if r["day"] == 3][0]
    assert day3["action"] == "hold_1"
    rows, _ = simulate_run({3: days[3]}, {"A": a, "B": b}, 0, ["C01"], 16)
    assert rows[0]["action"] == "release"     # fresh run: first visit releases


def test_rules_receive_only_own_profile():
    seen = []

    def spy(own, memory, observation):
        seen.append((own.driver_id, type(observation).__name__))
        return 0
    RULES["spy"] = spy
    try:
        ds = [driver("A", strategy="spy"), driver("B", strategy="spy")]
        rows, _ = run_day([req("A", 0, 10, 3), req("B", 0, 10, 3)], ds)
        assert sorted(seen) == [("A", "Observation"), ("B", "Observation")]
        fields = set(inspect.signature(Observation).parameters)
        assert fields == {"boundary", "fee", "queue_length", "legal_holds"}
    finally:
        del RULES["spy"]


# ------------------------------------------------------------- utility
def test_brief_utility_example():
    # Flexible B receives 6 kWh, waits 1 slot (behind A) and holds 1 slot under P1:
    # 2*6 - 1 + 2 - 2 = 11
    rows, _ = run_day([req("A", 0, 10, 3), req("B", 0, 10, 6)], [driver("A"), driver("B")],
                      fee=2, fixed={"A": 0, "B": 1})
    b = rows["B"]
    assert (b["delivered_kwh"], b["waiting_slots"], b["idle_slots"]) == (6, 1, 1)
    assert b["gross_utility"] == 13 and b["penalty"] == 2 and b["net_utility"] == 11


# ------------------------------------------------------------- full-run invariants
@pytest.fixture(scope="module")
def full_run():
    d = C.seed_dir(0)
    reqs = load_requests(d / "sessions_public.csv", "high")
    drivers = load_drivers(d / "drivers_private.csv")
    rows, tl = simulate_run(reqs, drivers, 0, [f"C{i:02}" for i in range(1, 7)], 16, keep_timeline=True)
    return reqs, rows, tl


def test_no_charger_serves_two_drivers(full_run):
    _, _, tl = full_run
    keys = Counter((t["day"], t["slot"], t["charger_id"]) for t in tl)
    assert max(keys.values()) == 1
    drivers = Counter((t["day"], t["slot"], t["driver_id"]) for t in tl)
    assert max(drivers.values()) == 1


def test_energy_only_inside_visit_window(full_run):
    _, rows, tl = full_run
    by_visit = {(r["day"], r["driver_id"]): r for r in rows}
    charged = Counter()
    held = Counter()
    for t in tl:
        r = by_visit[(t["day"], t["driver_id"])]
        assert r["arrival"] <= t["slot"] < r["departure"] and t["slot"] < 16
        (charged if t["state"] == "charging" else held)[(t["day"], t["driver_id"])] += 1
    for k, r in by_visit.items():
        assert r["delivered_kwh"] <= r["requested_kwh"]
        assert r["delivered_kwh"] == 3 * charged[k]
        assert r["idle_slots"] == held[k]


def test_every_request_has_one_visit(full_run):
    reqs, rows, _ = full_run
    assert len(rows) == sum(len(v) for v in reqs.values()) == 2160


def test_deterministic(full_run):
    d = C.seed_dir(0)
    reqs = load_requests(d / "sessions_public.csv", "high")
    drivers = load_drivers(d / "drivers_private.csv")
    rows, _ = simulate_run(reqs, drivers, 0, [f"C{i:02}" for i in range(1, 7)], 16)
    assert rows == full_run[1]
