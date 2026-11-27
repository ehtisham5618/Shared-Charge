"""Checks on the saved experiment outputs (run `python -m shared_charge all` first)."""
import csv
import json
import pytest

from shared_charge import config as C
from shared_charge.data import sha256
from shared_charge.experiments import all_run_specs, run_experiment
from shared_charge.metrics import flatten, summarize

pytestmark = pytest.mark.skipif(not (C.RESULTS_DIR / "manifest.json").exists(),
                                reason="experiments not run yet")


def read_visits(run_id):
    with (C.RUNS_DIR / run_id / "visits.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse(row):
    out = dict(row)
    for k in ("day", "arrival", "departure", "waiting_slots", "idle_slots"):
        out[k] = int(row[k])
    for k in ("requested_kwh", "delivered_kwh", "fee", "penalty", "gross_utility", "net_utility"):
        out[k] = float(row[k])
    out["fully_served"] = row["fully_served"] == "True"
    return out


def test_starter_data_unchanged():
    lines = (C.STARTER_DIR / "SHA256SUMS.txt").read_text().split("\n")
    checked = 0
    for line in filter(None, (x.strip() for x in lines)):
        digest, name = line.split(maxsplit=1)
        assert sha256(C.STARTER_DIR / name) == digest, name
        checked += 1
    assert checked == 15


def test_all_forty_runs_exist_with_sixty_days():
    specs = list(all_run_specs())
    assert len(specs) == 40 and sum(1 for s in specs if s[3]) == 10
    manifest = json.loads((C.RESULTS_DIR / "manifest.json").read_text())
    assert manifest["main_runs"] == 30 and manifest["control_runs"] == 10
    for seed, demand, pol, control in specs:
        rid = C.run_id(demand, pol, seed, control)
        settings = json.loads((C.RUNS_DIR / rid / "settings.json").read_text())
        assert (settings["seed"], settings["demand"], settings["policy_id"]) == (seed, demand, pol)
        assert settings["control_all_hold"] == control and settings["days"] == 60
        rows = read_visits(rid)
        assert len({r["day"] for r in rows}) == 60
        assert len(rows) == {"low": 720, "medium": 1440, "high": 2160}[demand]
        assert {r["policy"] for r in rows} == {pol}


@pytest.mark.parametrize("seed", C.SEEDS)
@pytest.mark.parametrize("demand", C.DEMANDS)
def test_matched_inputs_across_policies(seed, demand):
    keys = ("request_id", "driver_id", "driver_type", "strategy", "arrival", "departure", "requested_kwh")
    p0 = [tuple(r[k] for k in keys) for r in read_visits(C.run_id(demand, "P0", seed))]
    p1 = [tuple(r[k] for k in keys) for r in read_visits(C.run_id(demand, "P1", seed))]
    assert p0 == p1


def test_saved_summaries_match_visits():
    for seed, demand, pol, control in all_run_specs():
        rid = C.run_id(demand, pol, seed, control)
        rows = [parse(r) for r in read_visits(rid)]
        saved = json.loads((C.RUNS_DIR / rid / "summary.json").read_text())
        recomputed = summarize(rows)
        for k, v in flatten(recomputed).items():
            assert flatten(saved)[k] == pytest.approx(v), (rid, k)


def test_rerun_reproduces_saved_summary():
    res = run_experiment(2, "medium", "P1")
    saved = json.loads((C.RUNS_DIR / "medium_P1_seed2" / "summary.json").read_text())
    assert json.loads(json.dumps(res["summary"])) == saved


def test_control_runs_behave_identically_under_fee():
    for seed in C.SEEDS:
        a = read_visits(C.run_id("medium", "P0", seed, True))
        b = read_visits(C.run_id("medium", "P1", seed, True))
        same = ("start", "finish", "release", "action", "idle_slots", "delivered_kwh", "waiting_slots")
        assert [tuple(r[k] for k in same) for r in a] == [tuple(r[k] for k in same) for r in b]
        assert all(r["strategy"] == "hold" for r in a)
        assert all(float(r["penalty"]) == 2 * int(r["idle_slots"]) for r in b)


def test_missing_values_explicit():
    rows = read_visits("high_P0_seed0")
    unserved = [r for r in rows if r["action"] == "unserved"]
    assert unserved and all(r["start"] == "NA" and r["finish"] == "NA" and r["release"] == "NA" for r in unserved)
    incomplete = [r for r in rows if r["action"] == "departed_incomplete"]
    assert incomplete and all(r["finish"] == "NA" and r["start"] != "NA" for r in incomplete)


def test_comparison_stats_consistent():
    with (C.RESULTS_DIR / "comparison_by_seed.csv").open() as f:
        per_seed = list(csv.DictReader(f))
    with (C.RESULTS_DIR / "comparison_stats.csv").open() as f:
        stats = list(csv.DictReader(f))
    assert len(stats) == 3 * len({r["metric"] for r in per_seed})
    for s in stats:
        diffs = [float(r["diff_P1_minus_P0"]) for r in per_seed
                 if r["demand"] == s["demand"] and r["metric"] == s["metric"]]
        assert len(diffs) == 5
        assert float(s["diff_mean"]) == pytest.approx(sum(diffs) / 5)
        assert float(s["diff_min"]) == pytest.approx(min(diffs))
