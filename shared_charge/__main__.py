"""Command line entry point (no UI needed).

    python -m shared_charge generate          # create data/generated/data_seed_0..4
    python -m shared_charge minicase          # check the supplied mini case
    python -m shared_charge run --demand medium --policy P1 --seed 0 [--control]
    python -m shared_charge games             # game theory + evolutionary outputs
    python -m shared_charge all               # everything above + 40 runs + figures
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

from . import config as C
from .data import load_drivers, load_requests
from .evolutionary import both_trajectories
from .experiments import run_all, run_experiment, save_experiment, write_csv
from .game_theory import compute_all
from .simulator import simulate_run


def generate(force: bool = False) -> None:
    for seed in C.SEEDS:
        out = C.seed_dir(seed)
        if out.exists() and not force:
            print(f"  {out.relative_to(C.ROOT)} exists - kept")
            continue
        # The generator writes to its own folder by default; always pass --output
        subprocess.run([sys.executable, "-I", str(C.STARTER_DIR / "generate_data.py"),
                        "--output", str(out), "--seed", str(seed),
                        "--urgent-prior", str(C.URGENT_PRIOR)], check=True, capture_output=True)
        print(f"  generated {out.relative_to(C.ROOT)}")


MINI_FIXED_ACTIONS = {
    "all_release": {"A": 0, "B": 0, "C": 0},
    "A_holds_one_slot": {"A": 1, "B": 0, "C": 0},
}


def mini_case() -> dict:
    expected = json.loads((C.STARTER_DIR / "mini_case_expected.json").read_text(encoding="utf-8"))
    cond = expected["conditions"]
    requests = load_requests(C.STARTER_DIR / "mini_case_public.csv")
    drivers = load_drivers(C.STARTER_DIR / "mini_case_private.csv")
    report = {"conditions": cond, "cases": {}, "all_match": True}
    for case, actions in MINI_FIXED_ACTIONS.items():
        rows, _ = simulate_run(requests, drivers, cond["fee"],
                               [f"C{i:02}" for i in range(1, cond["chargers"] + 1)],
                               cond["end_boundary"], fixed_actions=actions)
        got = {r["driver_id"]: {"start": r["start"], "finish": r["finish"], "release": r["release"],
                                "wait_slots": r["waiting_slots"], "utility": r["net_utility"]} for r in rows}
        got["total_utility"] = sum(r["net_utility"] for r in rows)
        got["total_wait_slots"] = sum(r["waiting_slots"] for r in rows)
        got["delivered_kwh"] = sum(r["delivered_kwh"] for r in rows)
        match = got == expected[case]
        report["all_match"] &= match
        report["cases"][case] = {"simulated": got, "expected": expected[case], "match": match}
        print(f"  mini case {case:<17} match={match}  wait={got['total_wait_slots']} "
              f"energy={got['delivered_kwh']} utility={got['total_utility']}")
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (C.RESULTS_DIR / "mini_case_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def games() -> None:
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    gt = compute_all()
    (C.RESULTS_DIR / "game_theory.json").write_text(json.dumps(gt, indent=2, default=list), encoding="utf-8")
    evo = both_trajectories()
    write_csv(C.RESULTS_DIR / "evolutionary.csv", evo, list(evo[0]))
    (C.RESULTS_DIR / "evolutionary.json").write_text(json.dumps(evo, indent=2), encoding="utf-8")
    first = evo[1]["x_share_C"]
    print(f"  game theory saved; Nash={gt['normal_form']['pure_nash']}, "
          f"delta*={gt['infinite_repeated']['threshold']}, BNE={gt['bayesian']['is_bayesian_nash_equilibrium']}")
    print(f"  evolutionary first no-fee update x1={first}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="shared_charge", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--force", action="store_true")
    sub.add_parser("minicase")
    r = sub.add_parser("run")
    r.add_argument("--demand", choices=C.DEMANDS, required=True)
    r.add_argument("--policy", choices=C.POLICY_IDS, required=True)
    r.add_argument("--seed", type=int, choices=C.SEEDS, required=True)
    r.add_argument("--control", action="store_true", help="force every driver to the fixed Hold rule")
    sub.add_parser("games")
    sub.add_parser("all")
    sub.add_parser("figures")
    s = sub.add_parser("serve", help="start the local results screen")
    s.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)

    if a.cmd == "serve":
        import uvicorn
        print(f"Shared Charge running at http://127.0.0.1:{a.port}  (Ctrl+C to stop)")
        uvicorn.run("shared_charge.api:app", host="127.0.0.1", port=a.port)
        return 0
    if a.cmd == "figures":
        from .figures import make_all
        make_all()
        return 0

    if a.cmd == "generate":
        generate(a.force)
    elif a.cmd == "minicase":
        return 0 if mini_case()["all_match"] else 1
    elif a.cmd == "run":
        res = run_experiment(a.seed, a.demand, a.policy, a.control)
        out = save_experiment(res)
        print(json.dumps(res["summary"]["overall"], indent=2))
        print(f"saved to {out.relative_to(C.ROOT)}")
    elif a.cmd == "games":
        games()
    elif a.cmd == "all":
        print("[1/5] seed inputs"); generate()
        print("[2/5] mini case")
        if not mini_case()["all_match"]:
            print("mini case FAILED - stopping"); return 1
        print("[3/5] 30 main runs + 10 fixed-Hold control runs"); m = run_all()
        print(f"  {m['main_runs']} main runs, {m['control_runs']} control runs saved")
        print("[4/5] game theory and evolutionary"); games()
        print("[5/5] figures")
        from .figures import make_all
        make_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
