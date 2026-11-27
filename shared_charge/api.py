"""Local results API for the Shared Charge screen.

Every number the screen shows is read from the saved files in results/.
The only computation is POST /api/runs/{id}/rerun, which repeats one
experiment in memory and reports whether it reproduces the saved summary.

Start:  python -m shared_charge serve      (then open http://127.0.0.1:8000)
"""
from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config as C
from .experiments import run_experiment

app = FastAPI(title="Shared Charge results API", version="1.0.0")
DIST = C.ROOT / "frontend" / "dist"
RUN_RE = re.compile(r"^(control_allhold_)?(low|medium|high)_(P0|P1)_seed([0-4])$")

INT_FIELDS = {"seed", "day", "arrival", "departure", "start", "finish", "release",
              "waiting_slots", "idle_slots"}
FLOAT_FIELDS = {"requested_kwh", "delivered_kwh", "fee", "penalty", "gross_utility", "net_utility"}


def _json(path: Path):
    if not path.exists():
        raise HTTPException(404, f"{path.relative_to(C.ROOT).as_posix()} not found - run `python -m shared_charge all`")
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict]:
    if not path.exists():
        raise HTTPException(404, f"{path.relative_to(C.ROOT).as_posix()} not found")
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(v: str):
    if v == "NA" or v == "":
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except ValueError:
        return {"True": True, "False": False}.get(v, v)


def _run_dir(run_id: str) -> Path:
    if not RUN_RE.match(run_id):
        raise HTTPException(400, "unknown run id")
    return C.RUNS_DIR / run_id


@app.get("/api/meta")
def meta():
    manifest = _json(C.RESULTS_DIR / "manifest.json")
    mini = _json(C.RESULTS_DIR / "mini_case_check.json")
    return {"seeds": list(C.SEEDS), "demands": list(C.DEMANDS), "policies": list(C.POLICY_IDS),
            "manifest": manifest, "mini_case": mini,
            "site": {"chargers": C.CHARGER_COUNT, "power_kw": C.CHARGER_POWER_KW,
                     "kwh_per_slot": C.KWH_PER_SLOT, "slot_minutes": C.SLOT_MINUTES,
                     "day_end_boundary": C.DAY_END_BOUNDARY, "days": C.DAYS_PER_RUN}}


@app.get("/api/runs/{run_id}")
def run(run_id: str):
    d = _run_dir(run_id)
    return {"run_id": run_id, "settings": _json(d / "settings.json"), "summary": _json(d / "summary.json"),
            "files": {k: f"runs/{run_id}/{k}" for k in ("visits.csv", "summary.json", "settings.json")}}


@app.get("/api/runs/{run_id}/visits")
def visits(run_id: str):
    rows = _csv(_run_dir(run_id) / "visits.csv")
    return [{k: (_num(v) if k in INT_FIELDS | FLOAT_FIELDS | {"fully_served"} else (None if v == "NA" else v))
             for k, v in r.items()} for r in rows]


@app.post("/api/runs/{run_id}/rerun")
def rerun(run_id: str):
    m = RUN_RE.match(run_id)
    if not m:
        raise HTTPException(400, "unknown run id")
    control, demand, pol, seed = bool(m.group(1)), m.group(2), m.group(3), int(m.group(4))
    t0 = time.perf_counter()
    res = run_experiment(seed, demand, pol, control)
    elapsed = (time.perf_counter() - t0) * 1000
    saved = _json(_run_dir(run_id) / "summary.json")
    fresh = json.loads(json.dumps(res["summary"]))
    return {"run_id": run_id, "identical_to_saved": fresh == saved, "elapsed_ms": round(elapsed, 1),
            "visits": len(res["visits"]), "days": res["settings"]["days"]}


@app.get("/api/comparison/{demand}")
def comparison(demand: str):
    if demand not in C.DEMANDS:
        raise HTTPException(400, "unknown demand")
    per_seed = [{k: _num(v) if k not in ("demand", "metric") else v for k, v in r.items()}
                for r in _csv(C.RESULTS_DIR / "comparison_by_seed.csv") if r["demand"] == demand]
    stats = [{k: _num(v) if k not in ("demand", "metric") else v for k, v in r.items()}
             for r in _csv(C.RESULTS_DIR / "comparison_stats.csv") if r["demand"] == demand]
    return {"demand": demand, "by_seed": per_seed, "stats": stats}


@app.get("/api/control")
def control():
    conv = lambda rows: [{k: _num(v) if k not in ("demand", "metric") else v for k, v in r.items()} for r in rows]  # noqa: E731
    return {"by_seed": conv(_csv(C.RESULTS_DIR / "control_by_seed.csv")),
            "stats": conv(_csv(C.RESULTS_DIR / "control_stats.csv"))}


@app.get("/api/summary-runs")
def summary_runs():
    return [{k: (_num(v) if k not in ("run_id", "demand", "policy") else v) for k, v in r.items()}
            for r in _csv(C.RESULTS_DIR / "summary_runs.csv")]


@app.get("/api/evolutionary")
def evolutionary():
    return _json(C.RESULTS_DIR / "evolutionary.json")


@app.get("/api/game-theory")
def game_theory():
    return _json(C.RESULTS_DIR / "game_theory.json")


@app.get("/api/download/{path:path}")
def download(path: str):
    target = (C.RESULTS_DIR / path).resolve()
    if C.RESULTS_DIR.resolve() not in target.parents or not target.is_file():
        raise HTTPException(404, "file not found")
    if target.suffix not in (".csv", ".json", ".png"):
        raise HTTPException(403, "file type not shared")
    return FileResponse(target, filename=target.name)


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
