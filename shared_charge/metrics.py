"""Summary statistics for one run. Unserved drivers are included in waiting results."""
from __future__ import annotations

from .config import SLOT_MINUTES


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def _group(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "requests": n,
        "avg_wait_slots": _mean(r["waiting_slots"] for r in rows),
        "completion_rate": _mean(1.0 if r["fully_served"] else 0.0 for r in rows),
        "energy_kwh": sum(r["delivered_kwh"] for r in rows),
        "idle_slots": sum(r["idle_slots"] for r in rows),
        "unserved": sum(r["action"] == "unserved" for r in rows),
        "incomplete": sum(r["action"] == "departed_incomplete" for r in rows),
        "holds": sum(r["idle_slots"] > 0 for r in rows),
        "total_gross_utility": sum(r["gross_utility"] for r in rows),
        "total_penalty": sum(r["penalty"] for r in rows),
        "total_net_utility": sum(r["net_utility"] for r in rows),
        "mean_gross_utility": _mean(r["gross_utility"] for r in rows),
        "mean_net_utility": _mean(r["net_utility"] for r in rows),
    }


def summarize(rows: list[dict]) -> dict:
    overall = _group(rows)
    overall["avg_wait_minutes"] = overall["avg_wait_slots"] * SLOT_MINUTES if rows else None
    overall["days"] = len({r["day"] for r in rows})
    return {
        "overall": overall,
        "by_type": {t: _group([r for r in rows if r["driver_type"] == t]) for t in ("urgent", "flexible")},
        "by_strategy": {s: _group([r for r in rows if r["strategy"] == s])
                        for s in ("release", "hold", "reciprocal", "fee_aware")},
        "actions": {a: sum(r["action"] == a for r in rows)
                    for a in ("release", "hold_1", "hold_2", "forced_release", "departed_incomplete", "unserved")},
    }


# Flat metric names used in the comparison tables (label, path into summary)
FLAT_METRICS = {
    "avg_wait_slots": ("overall", "avg_wait_slots"),
    "completion_rate": ("overall", "completion_rate"),
    "energy_kwh": ("overall", "energy_kwh"),
    "idle_slots": ("overall", "idle_slots"),
    "unserved": ("overall", "unserved"),
    "total_gross_utility": ("overall", "total_gross_utility"),
    "total_penalty": ("overall", "total_penalty"),
    "total_net_utility": ("overall", "total_net_utility"),
    "mean_gross_utility": ("overall", "mean_gross_utility"),
    "mean_net_utility": ("overall", "mean_net_utility"),
}
for _t in ("urgent", "flexible"):
    for _m in ("avg_wait_slots", "completion_rate", "energy_kwh", "idle_slots",
               "mean_gross_utility", "mean_net_utility"):
        FLAT_METRICS[f"{_t}_{_m}"] = ("by_type", _t, _m)


def flatten(summary: dict) -> dict:
    out = {}
    for name, path in FLAT_METRICS.items():
        node = summary
        for key in path:
            node = node[key]
        out[name] = node
    return out
