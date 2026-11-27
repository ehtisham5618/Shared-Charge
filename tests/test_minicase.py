"""The supplied one-charger, three-driver mini case must match exactly."""
import json

from shared_charge import config as C
from shared_charge.__main__ import mini_case


def test_mini_case_matches_expected_json():
    report = mini_case()
    assert report["all_match"]
    expected = json.loads((C.STARTER_DIR / "mini_case_expected.json").read_text())
    for case in ("all_release", "A_holds_one_slot"):
        assert report["cases"][case]["simulated"] == expected[case]


def test_mini_case_headline_numbers():
    r = mini_case()["cases"]
    rel, hold = r["all_release"]["simulated"], r["A_holds_one_slot"]["simulated"]
    assert [rel[d]["start"] for d in "ABC"] == [0, 2, 3]
    assert (rel["total_wait_slots"], rel["delivered_kwh"], rel["total_utility"]) == (4, 15, 25)
    assert [hold[d]["start"] for d in "ABC"] == [0, 3, 4]
    assert (hold["total_wait_slots"], hold["total_utility"]) == (6, 23)
