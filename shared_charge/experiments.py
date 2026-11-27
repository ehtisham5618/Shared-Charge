"""Run the required experiments and save every result to disk.

Main design : 2 policies (P0, P1) x 3 demand levels x 5 seeds = 30 runs.
Control     : medium demand, every driver forced to the fixed Hold rule,
              P0 and P1, seeds 0-4 = 10 runs.
Each run covers 60 simulated days and starts from a fresh state.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from . import config as C
from .data import (load_chargers, load_config, load_drivers, load_policies, load_requests,
                   sha256, validate_inputs)
from .metrics import FLAT_METRICS, flatten, summarize
from .simulator import simulate_run

VISIT_FIELDS = ["seed", "demand", "policy", "day", "request_id", "driver_id", "driver_type", "strategy",
                "arrival", "departure", "charger_id", "start", "finish", "release", "requested_kwh",
                "delivered_kwh", "waiting_slots", "action", "idle_slots", "fee", "penalty",
                "gross_utility", "net_utility", "fully_served"]
MISSING = "NA"   # explicit missing value for service that never started or finished

INPUT_FILES = ("sessions_public.csv", "drivers_private.csv", "chargers.csv", "policies.csv", "config.json")


def _fmt(value):
    if value is None:
        return MISSING
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: _fmt(r.get(k)) for k in fields})


def run_experiment(seed: int, demand: str, policy_id: str, control: bool = False,
                   data_dir: Path | None = None) -> dict:
    """Run one experiment in memory and return settings, visit rows and summary."""
    data_dir = data_dir or C.seed_dir(seed)
    if not data_dir.exists():
        raise FileNotFoundError(f"{data_dir} missing - run scripts/generate_seeds.py first")
    policies = load_policies(data_dir / "policies.csv")
    if policy_id not in C.POLICY_IDS:
        raise ValueError(f"policy {policy_id} is outside the project scope {C.POLICY_IDS}")
    policy = policies[policy_id]
    requests = load_requests(data_dir / "sessions_public.csv", scenario=demand)
    drivers = load_drivers(data_dir / "drivers_private.csv")
    chargers = load_chargers(data_dir / "chargers.csv")
    cfg = load_config(data_dir / "config.json")
    problems = validate_inputs(requests, drivers)
    if problems:
        raise ValueError("input check failed: " + "; ".join(problems[:5]))
    if len(requests) != C.DAYS_PER_RUN:
        raise ValueError(f"expected {C.DAYS_PER_RUN} days, found {len(requests)}")

    override = C.CONTROL_STRATEGY if control else None
    rows, _ = simulate_run(requests, drivers, policy.fee_per_idle_slot,
                           [c["charger_id"] for c in chargers], C.DAY_END_BOUNDARY,
                           strategy_override=override)
    for r in rows:
        r.update(seed=seed, demand=demand, policy=policy_id)

    rid = C.run_id(demand, policy_id, seed, control)
    settings = {
        "run_id": rid,
        "seed": seed,
        "demand": demand,
        "policy_id": policy_id,
        "policy_name": policy.name,
        "fee_per_idle_slot": policy.fee_per_idle_slot,
        "use_history": False,
        "control_all_hold": control,
        "strategy_override": override,
        "days": len(requests),
        "requests": len(rows),
        "chargers": len(chargers),
        "charger_power_kw": chargers[0]["power_kw"],
        "kwh_per_slot": C.KWH_PER_SLOT,
        "day_end_boundary": C.DAY_END_BOUNDARY,
        "slot_minutes": C.SLOT_MINUTES,
        "urgent_prior": cfg["urgent_prior"],
        "generator_seed": cfg["seed"],
        "input_dir": data_dir.relative_to(C.ROOT).as_posix(),
        "input_files": {f: sha256(data_dir / f) for f in INPUT_FILES},
        "utility": "v*delivered_kwh - w*waiting_slots + h*idle_slots - F*idle_slots",
        "event_order": ["finish energy", "departures", "hold decisions", "expire holds",
                        "arrivals", "allocate by (arrival, driver_id)", "charge next slot"],
    }
    return {"settings": settings, "visits": rows, "summary": summarize(rows)}


def save_experiment(result: dict) -> Path:
    out = C.RUNS_DIR / result["settings"]["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "visits.csv", result["visits"], VISIT_FIELDS)
    (out / "settings.json").write_text(json.dumps(result["settings"], indent=2), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(result["summary"], indent=2), encoding="utf-8")
    return out


def all_run_specs():
    for seed in C.SEEDS:
        for demand in C.DEMANDS:
            for pol in C.POLICY_IDS:
                yield seed, demand, pol, False
    for seed in C.SEEDS:
        for pol in C.POLICY_IDS:
            yield seed, C.CONTROL_DEMAND, pol, True


def _matched(summaries: dict, control: bool, demands) -> tuple[list[dict], list[dict]]:
    """P1 - P0 per matching seed, then mean / min / max across the five seeds."""
    per_seed, stats = [], []
    for demand in demands:
        for metric in FLAT_METRICS:
            diffs = []
            for seed in C.SEEDS:
                p0 = summaries[(seed, demand, "P0", control)][metric]
                p1 = summaries[(seed, demand, "P1", control)][metric]
                d = None if p0 is None or p1 is None else p1 - p0
                diffs.append(d)
                per_seed.append({"demand": demand, "metric": metric, "seed": seed,
                                 "P0": p0, "P1": p1, "diff_P1_minus_P0": d})
            vals = [d for d in diffs if d is not None]
            p0s = [summaries[(s, demand, "P0", control)][metric] for s in C.SEEDS]
            p1s = [summaries[(s, demand, "P1", control)][metric] for s in C.SEEDS]
            stats.append({
                "demand": demand, "metric": metric,
                "P0_mean": sum(p0s) / len(p0s), "P1_mean": sum(p1s) / len(p1s),
                "diff_mean": sum(vals) / len(vals), "diff_min": min(vals), "diff_max": max(vals),
                "seeds_P1_lower": sum(d < -1e-12 for d in vals),
                "seeds_P1_higher": sum(d > 1e-12 for d in vals),
            })
    return per_seed, stats


def run_all(verbose: bool = True) -> dict:
    C.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    flat: dict = {}
    run_rows = []
    for seed, demand, pol, control in all_run_specs():
        res = run_experiment(seed, demand, pol, control)
        save_experiment(res)
        f = flatten(res["summary"])
        flat[(seed, demand, pol, control)] = f
        run_rows.append({"run_id": res["settings"]["run_id"], "seed": seed, "demand": demand,
                         "policy": pol, "control_all_hold": control,
                         "days": res["settings"]["days"], "requests": res["settings"]["requests"], **f})
        if verbose:
            print(f"  {res['settings']['run_id']:<34} wait={f['avg_wait_slots']:.3f} "
                  f"served={f['completion_rate']:.3f} idle={f['idle_slots']}")

    fields = ["run_id", "seed", "demand", "policy", "control_all_hold", "days", "requests", *FLAT_METRICS]
    write_csv(C.RESULTS_DIR / "summary_runs.csv", run_rows, fields)
    per_seed, stats = _matched(flat, False, C.DEMANDS)
    write_csv(C.RESULTS_DIR / "comparison_by_seed.csv", per_seed,
              ["demand", "metric", "seed", "P0", "P1", "diff_P1_minus_P0"])
    sfields = ["demand", "metric", "P0_mean", "P1_mean", "diff_mean", "diff_min", "diff_max",
               "seeds_P1_lower", "seeds_P1_higher"]
    write_csv(C.RESULTS_DIR / "comparison_stats.csv", stats, sfields)
    c_per_seed, c_stats = _matched(flat, True, (C.CONTROL_DEMAND,))
    write_csv(C.RESULTS_DIR / "control_by_seed.csv", c_per_seed,
              ["demand", "metric", "seed", "P0", "P1", "diff_P1_minus_P0"])
    write_csv(C.RESULTS_DIR / "control_stats.csv", c_stats, sfields)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "main_runs": sum(1 for r in run_rows if not r["control_all_hold"]),
        "control_runs": sum(1 for r in run_rows if r["control_all_hold"]),
        "seeds": list(C.SEEDS), "demands": list(C.DEMANDS), "policies": list(C.POLICY_IDS),
        "days_per_run": C.DAYS_PER_RUN,
        "runs": [r["run_id"] for r in run_rows],
        "seed_inputs": {s: {f: sha256(C.seed_dir(s) / f) for f in INPUT_FILES} for s in C.SEEDS},
    }
    (C.RESULTS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
