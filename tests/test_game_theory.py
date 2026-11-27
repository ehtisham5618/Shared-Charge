"""Checks for every written game-theory calculation in the brief."""
import pytest

from shared_charge import evolutionary as E
from shared_charge import game_theory as G


@pytest.fixture(scope="module")
def game():
    return G.load_benchmark()


def test_normal_form(game):
    br = G.best_responses(game)
    assert br["P1_vs_P2"] == {"C": ["H"], "H": ["H"]}
    assert br["P2_vs_P1"] == {"C": ["H"], "H": ["H"]}
    assert G.strictly_dominant(game, 0) == "H" and G.strictly_dominant(game, 1) == "H"
    assert G.pure_nash(game) == [("H", "H")] and game[("H", "H")] == (1, 1)
    assert G.best_joint_outcome(game) == ("C", "C") and game[("C", "C")] == (4, 4)
    assert G.is_symmetric(game)


def test_sequential_backward_induction(game):
    s = G.backward_induction_sequential(game)
    assert s["p2_strategy"] == {"C": "H", "H": "H"}
    assert s["p1_strategy"] == "H" and s["path"] == ("H", "H") and s["payoffs"] == (1, 1)


def test_memory_tree_full_information():
    tree = G.load_memory_tree()
    assert len(tree) == 8
    sol = G.solve_memory_tree_full_info(tree)
    assert {k: v["choice"] for k, v in sol["p1_final"].items()} == {"LL": "R", "LR": "L", "RL": "L", "RR": "L"}
    assert sol["p2"]["L"]["choice"] == "L" and sol["p2"]["R"]["choice"] == "L"
    assert sol["path"] == "LLR" and sol["payoffs"] == (8, 4)


def test_information_sets_partition_p1_nodes():
    nodes = {"root", "LL", "LR", "RL", "RR"}
    for name, spec in G.INFORMATION_SETS.items():
        flat = [n for s in spec["P1"] for n in s]
        assert sorted(flat) == sorted(nodes), name
    assert G.INFORMATION_SETS["full_information"]["perfect_recall"]
    assert ["LL", "RL"] in G.INFORMATION_SETS["forget_own_first_action"]["P1"]
    assert len(G.INFORMATION_SETS["forget_stage"]["P1"]) == 1


def test_mixed_vs_behavioral():
    m = G.mixed_vs_behavioral(G.load_memory_tree())
    assert m["p1_payoffs_given_p2_L"] == {"LL": 1, "LR": 8, "RL": 6, "RR": 2}
    assert m["mixed_expected"] == pytest.approx(1.5)
    assert m["behavioral_expected"] == pytest.approx(4.25)
    assert m["recall_behavioral_expected"] == pytest.approx(1.5)
    assert m["recall_behavioral_probabilities"] == m["mixed_probabilities"]
    for total in m["probability_totals"].values():
        assert total == pytest.approx(1.0)
    assert m["forgotten_stage_best_p"] == pytest.approx(5 / 11)


def test_finite_repeated(game):
    f = G.finite_repeated(game, 3)
    assert all(r["actions"] == ("H", "H") for r in f["rounds"])
    assert f["total_payoffs"] == (3, 3) and f["cooperative_total"] == (12, 12)


def test_infinite_repeated(game):
    assert G.trigger_threshold(game) == pytest.approx(0.4)
    assert G.cooperate_forever(game, 0.2) == pytest.approx(5.0)
    assert G.deviate_now(game, 0.2) == pytest.approx(6.25)
    assert G.cooperate_forever(game, 0.5) == pytest.approx(8.0)
    assert G.deviate_now(game, 0.5) == pytest.approx(7.0)
    assert G.cooperate_forever(game, 0.4) == pytest.approx(G.deviate_now(game, 0.4))
    inf = G.infinite_repeated(game)
    assert inf["H_best_response_in_punishment"]
    d = 0.5
    assert G.cooperate_twice_then_deviate(game, d) == pytest.approx(4 + 4 * d + 6 * d**2 + d**3 / (1 - d))


def test_discount_formulas():
    assert G.discounted_constant(4, 0.5, T=3) == pytest.approx(4 + 2 + 1)
    assert G.discounted_constant(4, 1, T=3) == 12
    assert G.discounted_constant(4, 0.5) == pytest.approx(8)


def test_bayesian(game):
    b = G.bayesian_check(game, G.load_bayesian_types(), fee=1.5)
    rows = {r["type"]: r for r in b["checks"]}
    assert rows["urgent"]["EV_C"] == pytest.approx(1.20)
    assert rows["urgent"]["EV_H"] == pytest.approx(1.00)
    assert rows["flexible"]["EV_C"] == pytest.approx(1.20)
    assert rows["flexible"]["EV_H"] == pytest.approx(2.00)
    assert b["is_bayesian_nash_equilibrium"]


def test_evolutionary_first_steps():
    assert E.fitness(0.5, 0) == (2.0, 3.5)
    assert E.update(0.5, 0) == pytest.approx(0.48125)
    assert E.update(0.5, 2) == pytest.approx(0.50625)
    for fee in (0, 2):
        tr = E.trajectory(fee)
        assert len(tr) == 31 and tr[0]["x_share_C"] == 0.5
        assert all(0 <= r["x_share_C"] <= 1 for r in tr)
    assert E.trajectory(0)[-1]["x_share_C"] < 0.5 < E.trajectory(2)[-1]["x_share_C"]


def test_utility_example():
    assert G.utility(2, 1, 2, 6, 1, 1, 2) == 11
