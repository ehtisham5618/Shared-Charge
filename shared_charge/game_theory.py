"""Written game-theory examples (project brief, sections 3 and 4).

These are small checking calculations, not general solvers. Every number is
computed from the supplied benchmark_game.csv, memory_tree.csv and
bayesian_types.csv so the report and tests share one source of truth.
"""
from __future__ import annotations

import csv
from fractions import Fraction
from itertools import product
from pathlib import Path

from .config import STARTER_DIR

ACTIONS = ("C", "H")


# ---------------------------------------------------------------- loading
def load_benchmark(path: Path = STARTER_DIR / "benchmark_game.csv") -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        return {(r["p1_action"], r["p2_action"]): (float(r["p1_payoff"]), float(r["p2_payoff"]))
                for r in csv.DictReader(f)}


def load_memory_tree(path: Path = STARTER_DIR / "memory_tree.csv") -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        return {(r["p1_first"], r["p2_action"], r["p1_second"]): (float(r["p1_payoff"]), float(r["p2_payoff"]))
                for r in csv.DictReader(f)}


def load_bayesian_types(path: Path = STARTER_DIR / "bayesian_types.csv") -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        return {r["private_type"]: {"prob": float(r["probability"]), "alpha": float(r["extra_hold_payoff"])}
                for r in csv.DictReader(f)}


# ---------------------------------------------------------------- 3A normal form
def best_responses(game: dict) -> dict:
    """For each opponent action, the payoff-maximising own action(s)."""
    p1 = {a2: [a1 for a1 in ACTIONS if game[(a1, a2)][0] == max(game[(b, a2)][0] for b in ACTIONS)]
          for a2 in ACTIONS}
    p2 = {a1: [a2 for a2 in ACTIONS if game[(a1, a2)][1] == max(game[(a1, b)][1] for b in ACTIONS)]
          for a1 in ACTIONS}
    return {"P1_vs_P2": p1, "P2_vs_P1": p2}


def pure_nash(game: dict) -> list[tuple]:
    br = best_responses(game)
    return [(a1, a2) for a1, a2 in product(ACTIONS, ACTIONS)
            if a1 in br["P1_vs_P2"][a2] and a2 in br["P2_vs_P1"][a1]]


def strictly_dominant(game: dict, player: int) -> str | None:
    for a in ACTIONS:
        other = [b for b in ACTIONS if b != a][0]
        if player == 0 and all(game[(a, x)][0] > game[(other, x)][0] for x in ACTIONS):
            return a
        if player == 1 and all(game[(x, a)][1] > game[(x, other)][1] for x in ACTIONS):
            return a
    return None


def best_joint_outcome(game: dict) -> tuple:
    return max(game, key=lambda k: sum(game[k]))


# ---------------------------------------------------------------- 3A extensive form
def backward_induction_sequential(game: dict) -> dict:
    """P1 moves first; P2 observes P1's move, then chooses."""
    p2_plan = {a1: max(ACTIONS, key=lambda a2: game[(a1, a2)][1]) for a1 in ACTIONS}
    p1_choice = max(ACTIONS, key=lambda a1: game[(a1, p2_plan[a1])][0])
    path = (p1_choice, p2_plan[p1_choice])
    return {"p2_strategy": p2_plan, "p1_strategy": p1_choice, "path": path, "payoffs": game[path]}


# ---------------------------------------------------------------- 3B memory tree
def solve_memory_tree_full_info(tree: dict) -> dict:
    final = {}
    for a1, a2 in product("LR", "LR"):
        choice = max("LR", key=lambda a3: tree[(a1, a2, a3)][0])
        final[a1 + a2] = {"choice": choice, "payoffs": tree[(a1, a2, choice)]}
    p2 = {}
    for a1 in "LR":
        choice = max("LR", key=lambda a2: final[a1 + a2]["payoffs"][1])
        p2[a1] = {"choice": choice, "payoffs": final[a1 + choice]["payoffs"]}
    root = max("LR", key=lambda a1: p2[a1]["payoffs"][0])
    path = (root, p2[root]["choice"], final[root + p2[root]["choice"]]["choice"])
    return {"p1_final": final, "p2": p2, "p1_root": root, "path": "".join(path), "payoffs": tree[path]}


INFORMATION_SETS = {
    "full_information": {
        "P1": [["root"], ["LL"], ["LR"], ["RL"], ["RR"]],
        "P2": [["L"], ["R"]],
        "perfect_recall": True,
    },
    "forget_own_first_action": {
        # P1 sees P2's action and knows it is the later move, but not its own first move
        "P1": [["root"], ["LL", "RL"], ["LR", "RR"]],
        "P2": [["L"], ["R"]],
        "perfect_recall": False,
    },
    "forget_stage": {
        # P1 cannot tell the root from any later node
        "P1": [["root", "LL", "LR", "RL", "RR"]],
        "P2": [["L"], ["R"]],
        "perfect_recall": False,
    },
}


# ---------------------------------------------------------------- 3C mixed vs behavioral
def mixed_vs_behavioral(tree: dict, p2_fixed: str = "L") -> dict:
    pay = {a + b: tree[(a, p2_fixed, b)][0] for a, b in product("LR", "LR")}
    half = Fraction(1, 2)
    mixed = {"LL": half, "LR": Fraction(0), "RL": Fraction(0), "RR": half}
    behavioral = {k: half * half for k in pay}
    recall_behavioral = {"LL": half * 1, "LR": half * 0, "RL": half * 0, "RR": half * 1}

    def ev(dist):
        return float(sum(dist[k] * Fraction(pay[k]).limit_denominator() for k in pay))

    # Under forgotten stage a behavioral strategy is one probability p of L used at
    # every visit: E(p) = p^2*LL + p(1-p)*(LR+RL) + (1-p)^2*RR.  Maximise over p.
    a = pay["LL"] - pay["LR"] - pay["RL"] + pay["RR"]
    b = pay["LR"] + pay["RL"] - 2 * pay["RR"]
    c = pay["RR"]
    p_star = -b / (2 * a) if a < 0 else None
    best_p = min(max(p_star, 0.0), 1.0) if p_star is not None else 0.0
    return {
        "p1_payoffs_given_p2_L": pay,
        "mixed_probabilities": {k: float(v) for k, v in mixed.items()},
        "behavioral_probabilities": {k: float(v) for k, v in behavioral.items()},
        "recall_behavioral_probabilities": {k: float(v) for k, v in recall_behavioral.items()},
        "mixed_expected": ev(mixed),
        "behavioral_expected": ev(behavioral),
        "recall_behavioral_expected": ev(recall_behavioral),
        "probability_totals": {
            "mixed": float(sum(mixed.values())),
            "behavioral": float(sum(behavioral.values())),
            "recall_behavioral": float(sum(recall_behavioral.values())),
        },
        "forgotten_stage_behavioral_curve": {"a": a, "b": b, "c": c},
        "forgotten_stage_best_p": best_p,
        "forgotten_stage_best_value": a * best_p ** 2 + b * best_p + c,
    }


# ---------------------------------------------------------------- 4A repeated games
def finite_repeated(game: dict, rounds: int = 3) -> dict:
    ne = pure_nash(game)
    assert len(ne) == 1, "unique stage equilibrium expected"
    stage = ne[0]
    plan = [{"round": r, "actions": stage, "payoffs": game[stage]} for r in range(1, rounds + 1)]
    return {"rounds": plan, "total_payoffs": tuple(game[stage][i] * rounds for i in (0, 1)),
            "cooperative_total": tuple(game[("C", "C")][i] * rounds for i in (0, 1))}


def discounted_constant(r: float, delta: float, T: int | None = None) -> float:
    if T is None:
        if not 0 <= delta < 1:
            raise ValueError("infinite stream needs 0 <= delta < 1")
        return r / (1 - delta)
    return T * r if delta == 1 else r * (1 - delta ** T) / (1 - delta)


def cooperate_forever(game: dict, delta: float) -> float:
    return discounted_constant(game[("C", "C")][0], delta)


def deviate_now(game: dict, delta: float) -> float:
    return game[("H", "C")][0] + delta * discounted_constant(game[("H", "H")][0], delta)


def cooperate_twice_then_deviate(game: dict, delta: float) -> float:
    cc, hc, hh = game[("C", "C")][0], game[("H", "C")][0], game[("H", "H")][0]
    return cc + cc * delta + hc * delta ** 2 + hh * delta ** 3 / (1 - delta)


def trigger_threshold(game: dict) -> float:
    """cc/(1-d) >= hc + d*hh/(1-d)  <=>  d >= (hc - cc)/(hc - hh)."""
    cc, hc, hh = game[("C", "C")][0], game[("H", "C")][0], game[("H", "H")][0]
    return (hc - cc) / (hc - hh)


def infinite_repeated(game: dict, deltas=(0.2, 0.4, 0.5, 0.8)) -> dict:
    rows = []
    for d in deltas:
        coop, dev = cooperate_forever(game, d), deviate_now(game, d)
        rows.append({"delta": d, "cooperate_forever": coop, "deviate_now": dev,
                     "cooperate_twice_then_deviate": cooperate_twice_then_deviate(game, d),
                     "cooperation_sustained": coop >= dev - 1e-12})
    punish = {"H_vs_H": game[("H", "H")][0], "C_vs_H": game[("C", "H")][0]}
    return {"threshold": trigger_threshold(game), "table": rows,
            "punishment_stage_payoffs": punish,
            "H_best_response_in_punishment": punish["H_vs_H"] > punish["C_vs_H"]}


# ---------------------------------------------------------------- 4B Bayesian game
def bayesian_check(game: dict, types: dict, fee: float = 1.5,
                   plan: dict | None = None) -> dict:
    plan = plan or {"urgent": "C", "flexible": "H"}

    def own_payoff(own_type, a_own, a_opp):
        base = game[(a_own, a_opp)][0]            # game is symmetric; use P1 column
        if a_own == "H":
            base = base - fee + types[own_type]["alpha"]
        return base

    rows = []
    for own_type in types:
        evs = {}
        for a in ACTIONS:
            terms = [(types[t]["prob"], own_payoff(own_type, a, plan[t])) for t in types]
            evs[a] = {"terms": terms, "expected": sum(p * u for p, u in terms)}
        best = max(ACTIONS, key=lambda a: evs[a]["expected"])
        rows.append({"type": own_type, "planned": plan[own_type], "EV_C": evs["C"]["expected"],
                     "EV_H": evs["H"]["expected"], "terms_C": evs["C"]["terms"],
                     "terms_H": evs["H"]["terms"], "best": best,
                     "no_profitable_deviation": evs[plan[own_type]]["expected"] >= max(
                         e["expected"] for e in evs.values()) - 1e-12})
    # symmetric game and symmetric plan: the same check applies to both players
    return {"fee": fee, "plan": plan, "checks": rows, "players_checked": ["P1", "P2"],
            "is_bayesian_nash_equilibrium": all(r["no_profitable_deviation"] for r in rows)}


def is_symmetric(game: dict) -> bool:
    return all(game[(a, b)][0] == game[(b, a)][1] for a, b in product(ACTIONS, ACTIONS))


# ---------------------------------------------------------------- utility example
def utility(v, w, h, kwh, wait, idle, fee) -> float:
    return v * kwh - w * wait + h * idle - fee * idle


def compute_all() -> dict:
    game = load_benchmark()
    tree = load_memory_tree()
    types = load_bayesian_types()
    return {
        "utility_example_flexible_P1": utility(2, 1, 2, 6, 1, 1, 2),
        "normal_form": {
            "payoffs": {f"{a}{b}": game[(a, b)] for a, b in game},
            "best_responses": best_responses(game),
            "pure_nash": pure_nash(game),
            "dominant_P1": strictly_dominant(game, 0),
            "dominant_P2": strictly_dominant(game, 1),
            "best_joint_outcome": best_joint_outcome(game),
            "symmetric": is_symmetric(game),
        },
        "sequential_perfect_information": backward_induction_sequential(game),
        "simultaneous_imperfect_information": {"pure_nash": pure_nash(game)},
        "memory_tree": {
            "leaves": {"".join(k): v for k, v in tree.items()},
            "full_information": solve_memory_tree_full_info(tree),
            "information_sets": INFORMATION_SETS,
        },
        "mixed_vs_behavioral": mixed_vs_behavioral(tree),
        "finite_repeated": finite_repeated(game, 3),
        "infinite_repeated": infinite_repeated(game),
        "bayesian": bayesian_check(game, types, fee=1.5),
    }
