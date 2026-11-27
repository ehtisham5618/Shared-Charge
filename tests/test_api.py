"""The API must return exactly what is saved on disk."""
import csv
import json

import pytest
from fastapi.testclient import TestClient

from shared_charge import config as C
from shared_charge.api import app

pytestmark = pytest.mark.skipif(not (C.RESULTS_DIR / "manifest.json").exists(), reason="run experiments first")
client = TestClient(app)


def test_meta():
    m = client.get("/api/meta").json()
    assert m["seeds"] == [0, 1, 2, 3, 4] and m["policies"] == ["P0", "P1"]
    assert m["mini_case"]["all_match"] is True


def test_run_summary_matches_file():
    r = client.get("/api/runs/medium_P1_seed3").json()
    saved = json.loads((C.RUNS_DIR / "medium_P1_seed3" / "summary.json").read_text())
    assert r["summary"] == saved and r["settings"]["fee_per_idle_slot"] == 2


def test_visits_match_csv():
    api_rows = client.get("/api/runs/low_P0_seed1/visits").json()
    with (C.RUNS_DIR / "low_P0_seed1" / "visits.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(api_rows) == len(rows) == 720
    assert sum(r["waiting_slots"] for r in api_rows) == sum(int(r["waiting_slots"]) for r in rows)
    unserved = [r for r in api_rows if r["action"] == "unserved"]
    assert all(r["start"] is None for r in unserved)


def test_rerun_identical():
    r = client.post("/api/runs/high_P0_seed4/rerun").json()
    assert r["identical_to_saved"] is True and r["days"] == 60


def test_bad_inputs_rejected():
    assert client.get("/api/runs/medium_P2_seed0").status_code == 400
    assert client.get("/api/runs/..%2F..%2Fstarter_data").status_code in (400, 404)
    assert client.get("/api/download/../starter_data/drivers_private.csv").status_code == 404
    assert client.get("/api/comparison/extreme").status_code == 400


def test_download_and_comparison():
    assert client.get("/api/download/summary_runs.csv").status_code == 200
    c = client.get("/api/comparison/medium").json()
    assert len(c["by_seed"]) == 5 * len(c["stats"])
    assert len(client.get("/api/evolutionary").json()) == 62
