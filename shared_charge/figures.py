"""Report figures (PNG) built only from the saved result files."""
from __future__ import annotations

import csv
import json
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import config as C  # noqa: E402

# Validated two-series palette (light surface): colour always encodes the fee regime
P0_COLOR, P1_COLOR = "#2A76AA", "#B07A1E"
INK, MUTED, GRID, SURFACE = "#28343A", "#68757A", "#D8DCD4", "#FFFFFF"
DEMAND_LABEL = {"low": "Low", "medium": "Medium", "high": "High"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titleweight": "bold", "axes.titlesize": 10,
    "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.dpi": 200,
    "legend.frameon": False,
})


def _read_csv(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _runs():
    rows = _read_csv(C.RESULTS_DIR / "summary_runs.csv")
    return [r for r in rows if r["control_all_hold"] == "False"]


def _save(fig, name):
    C.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(C.FIGURES_DIR / name, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ evolutionary
def fig_evolutionary():
    rows = json.loads((C.RESULTS_DIR / "evolutionary.json").read_text())
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for fee, color, label in ((0.0, P0_COLOR, "F = 0 (no fee)"), (2.0, P1_COLOR, "F = 2 (idle fee)")):
        pts = [r for r in rows if r["fee"] == fee]
        xs = [r["update"] for r in pts]
        ys = [r["x_share_C"] for r in pts]
        ax.plot(xs, ys, color=color, lw=2, marker="o", ms=3)
        ax.annotate(f"{label}: {ys[-1]:.3f}", (xs[-1], ys[-1]), xytext=(-4, 8 if fee else -14),
                    textcoords="offset points", ha="right", color=INK, fontsize=8.5)
    ax.scatter([0], [0.5], s=40, color=INK, zorder=5)
    ax.annotate("start x = 0.5", (0, 0.5), xytext=(6, 6), textcoords="offset points", fontsize=8, color=INK)
    ax.set_xlim(-0.5, 30.5); ax.set_ylim(0, 1)
    ax.set_xlabel("Update"); ax.set_ylabel("Share choosing C (release), x")
    ax.set_title("Evolutionary C/H share over 30 updates")
    _save(fig, "evolutionary.png")


# ------------------------------------------------------------------ policy overview
def _by(runs, metric):
    out = defaultdict(list)
    for r in runs:
        out[(r["demand"], r["policy"])].append(float(r[metric]))
    return out


def _paired_bars(ax, runs, metric, title, ylabel, scale=1.0, fmt="{:.2f}"):
    data = _by(runs, metric)
    w = 0.36
    for i, d in enumerate(C.DEMANDS):
        for j, (pol, color) in enumerate((("P0", P0_COLOR), ("P1", P1_COLOR))):
            vals = [v * scale for v in data[(d, pol)]]
            m = sum(vals) / len(vals)
            x = i + (j - 0.5) * (w + 0.04)
            ax.bar(x, m, width=w, color=color, edgecolor=SURFACE, linewidth=1)
            ax.errorbar(x, m, yerr=[[m - min(vals)], [max(vals) - m]], color=INK, lw=0.9, capsize=2.5)
            ax.annotate(fmt.format(m), (x, max(vals)), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=7, color=INK)
    ax.set_xticks(range(3), [DEMAND_LABEL[d] for d in C.DEMANDS])
    ax.set_title(title); ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    ax.margins(y=0.14)


def fig_policy_overview():
    runs = _runs()
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))
    _paired_bars(axes[0, 0], runs, "avg_wait_slots", "Average waiting", "slots per request")
    _paired_bars(axes[0, 1], runs, "completion_rate", "Requests fully served", "% of requests", 100, "{:.1f}")
    _paired_bars(axes[1, 0], runs, "idle_slots", "Idle (held) charger slots", "slots per 60-day run", 1, "{:.0f}")
    _paired_bars(axes[1, 1], runs, "mean_net_utility", "Net utility after penalty", "points per request")
    handles = [plt.Rectangle((0, 0), 1, 1, color=P0_COLOR), plt.Rectangle((0, 0), 1, 1, color=P1_COLOR)]
    fig.legend(handles, ["P0  FCFS, no fee", "P1  FCFS, fee 2 / idle slot"], loc="upper center", ncol=2,
               bbox_to_anchor=(0.5, 1.03))
    fig.text(0.5, -0.01, "Bars: mean of 5 seeds. Whiskers: min-max across seeds.", ha="center",
             color=MUTED, fontsize=8)
    fig.tight_layout()
    _save(fig, "policy_overview.png")


# ------------------------------------------------------------------ type changes
def fig_type_change():
    stats = {(r["demand"], r["metric"]): r for r in _read_csv(C.RESULTS_DIR / "comparison_stats.csv")}
    panels = (("avg_wait_slots", "Change in waiting (slots)"),
              ("completion_rate", "Change in fully served (pp)"),
              ("mean_net_utility", "Change in net utility (points)"))
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7), sharey=True)
    types = (("urgent", "Urgent", "o"), ("flexible", "Flexible", "s"))
    for ax, (metric, title) in zip(axes, panels):
        scale = 100 if metric == "completion_rate" else 1
        for i, d in enumerate(C.DEMANDS):
            for j, (t, label, marker) in enumerate(types):
                s = stats[(d, f"{t}_{metric}")]
                y = i + (j - 0.5) * 0.3
                m, lo, hi = (float(s[k]) * scale for k in ("diff_mean", "diff_min", "diff_max"))
                ax.plot([lo, hi], [y, y], color=MUTED, lw=1.4)
                ax.plot(m, y, marker=marker, color=INK, ms=6, mfc=SURFACE if t == "flexible" else INK)
        ax.axvline(0, color=INK, lw=0.8)
        ax.set_title(title, fontsize=9)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(3), [DEMAND_LABEL[d] for d in C.DEMANDS])
    axes[0].invert_yaxis()
    from matplotlib.lines import Line2D
    fig.legend([Line2D([], [], marker="o", color=INK, ls=""), Line2D([], [], marker="s", color=INK, mfc=SURFACE, ls="")],
               ["Urgent", "Flexible"], loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.06))
    fig.text(0.5, -0.04, "P1 minus P0 on matching seeds. Marker: mean of 5 seeds; line: min-max.",
             ha="center", color=MUTED, fontsize=8)
    fig.tight_layout()
    _save(fig, "type_change.png")


# ------------------------------------------------------------------ strategy breakdown
def fig_strategy():
    names = {"release": "Release", "hold": "Hold", "reciprocal": "Reciprocal", "fee_aware": "Fee aware"}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    for ax, metric, title in ((axes[0], "idle_slots", "Idle slots per 60 days (medium)"),
                              (axes[1], "mean_net_utility", "Net utility per visit (medium)")):
        w = 0.36
        for i, s in enumerate(names):
            for j, (pol, color) in enumerate((("P0", P0_COLOR), ("P1", P1_COLOR))):
                vals = [json.loads((C.RUNS_DIR / C.run_id("medium", pol, seed) / "summary.json").read_text())
                        ["by_strategy"][s][metric] for seed in C.SEEDS]
                m = sum(vals) / len(vals)
                x = i + (j - 0.5) * (w + 0.04)
                ax.bar(x, m, width=w, color=color)
                ax.annotate(f"{m:.0f}" if metric == "idle_slots" else f"{m:.1f}", (x, m), xytext=(0, 2),
                            textcoords="offset points", ha="center", fontsize=6.8, color=INK)
        ax.set_xticks(range(4), list(names.values()))
        ax.set_title(title); ax.grid(axis="x", visible=False); ax.margins(y=0.15)
    handles = [plt.Rectangle((0, 0), 1, 1, color=P0_COLOR), plt.Rectangle((0, 0), 1, 1, color=P1_COLOR)]
    fig.legend(handles, ["P0", "P1"], loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.07))
    fig.tight_layout()
    _save(fig, "strategy_medium.png")


# ------------------------------------------------------------------ game trees
def _node(ax, x, y, label, color=INK, filled=True):
    ax.plot(x, y, "o", ms=13, color=color, mfc=color if filled else SURFACE, zorder=3)
    ax.text(x, y, label, ha="center", va="center", fontsize=7, color=SURFACE if filled else INK,
            zorder=4, fontweight="bold")


def _edge(ax, a, b, label, bold=False):
    ax.plot([a[0], b[0]], [a[1], b[1]], color=INK if bold else MUTED, lw=2.2 if bold else 1, zorder=1)
    ax.text((a[0] + b[0]) / 2 + (-0.12 if b[0] < a[0] else 0.12), (a[1] + b[1]) / 2, label,
            ha="center", va="center", fontsize=8, color=INK,
            bbox=dict(boxstyle="round,pad=0.1", fc=SURFACE, ec="none"))


def _info_set(ax, pts, label=""):
    xs = [p[0] for p in pts]
    y = pts[0][1]
    ax.plot([min(xs), max(xs)], [y, y], ls=(0, (4, 3)), color=P1_COLOR, lw=1.6, zorder=2)
    if label:
        ax.text(max(xs) + 0.25, y, label, fontsize=7, color=P1_COLOR, va="center")


def fig_ch_trees():
    gt = json.loads((C.RESULTS_DIR / "game_theory.json").read_text())
    pay = gt["normal_form"]["payoffs"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for ax, imperfect in zip(axes, (False, True)):
        root, p2 = (2, 2), {"C": (1, 1), "H": (3, 1)}
        leaves = {"CC": (0.5, 0), "CH": (1.5, 0), "HC": (2.5, 0), "HH": (3.5, 0)}
        for a1 in "CH":
            _edge(ax, root, p2[a1], a1, bold=(a1 == "H" and not imperfect))
            for a2 in "CH":
                _edge(ax, p2[a1], leaves[a1 + a2], a2, bold=(a2 == "H" and not imperfect))
                u = pay[a1 + a2]
                ax.text(*leaves[a1 + a2], f"({u[0]:g}, {u[1]:g})", ha="center", va="top", fontsize=8,
                        color=INK, fontweight="bold" if a1 + a2 == "HH" else "normal")
        _node(ax, *root, "P1")
        for a1 in "CH":
            _node(ax, *p2[a1], "P2", color=P0_COLOR)
        if imperfect:
            _info_set(ax, [p2["C"], p2["H"]])
            ax.set_title("(b) P1's move hidden: one P2 information set", fontsize=9)
        else:
            ax.set_title("(a) Perfect information: backward induction", fontsize=9)
        ax.set_xlim(0, 4); ax.set_ylim(-0.45, 2.3); ax.axis("off")
    fig.tight_layout()
    _save(fig, "tree_ch_game.png")


def fig_memory_trees():
    gt = json.loads((C.RESULTS_DIR / "game_theory.json").read_text())
    leaves = gt["memory_tree"]["leaves"]
    sol = gt["memory_tree"]["full_information"]
    titles = ("(a) Full information", "(b) Forget own first action", "(c) Forget the stage")
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.1))
    for k, ax in enumerate(axes):
        root = (3.5, 3)
        p2 = {"L": (1.75, 2), "R": (5.25, 2)}
        p1b = {"LL": (0.75, 1), "LR": (2.75, 1), "RL": (4.25, 1), "RR": (6.25, 1)}
        path = sol["path"] if k == 0 else ""
        for a1 in "LR":
            _edge(ax, root, p2[a1], a1, bold=path[:1] == a1)
            for a2 in "LR":
                n = p1b[a1 + a2]
                _edge(ax, p2[a1], n, a2, bold=path[:2] == a1 + a2)
                for a3, dx in (("L", -0.45), ("R", 0.45)):
                    leaf = (n[0] + dx, 0)
                    ax.plot([n[0], leaf[0]], [n[1], leaf[1]],
                            color=INK if path == a1 + a2 + a3 else MUTED,
                            lw=2.2 if path == a1 + a2 + a3 else 0.9, zorder=1)
                    u = leaves[a1 + a2 + a3]
                    ax.text(leaf[0], -0.12, f"{u[0]:g}\n{u[1]:g}", ha="center", va="top", fontsize=6.3, color=INK)
        _node(ax, *root, "P1")
        for n in p2.values():
            _node(ax, *n, "P2", color=P0_COLOR)
        for n in p1b.values():
            _node(ax, *n, "P1")
        if k == 1:
            # join (L,L)-(R,L) and (L,R)-(R,R): drawn as dashed arcs
            for a, b, off in (("LL", "RL", 0.32), ("LR", "RR", 0.55)):
                (x1, y1), (x2, y2) = p1b[a], p1b[b]
                ax.annotate("", (x2, y2 + 0.12), (x1, y1 + 0.12),
                            arrowprops=dict(arrowstyle="-", ls=(0, (4, 3)), color=P1_COLOR, lw=1.5,
                                            connectionstyle=f"arc3,rad=-{off}"))
        if k == 2:
            for n in p1b.values():
                ax.annotate("", n, root, arrowprops=dict(arrowstyle="-", ls=(0, (2, 2)), color=P1_COLOR,
                                                         lw=1.2, connectionstyle="arc3,rad=0.25"))
        ax.set_title(titles[k], fontsize=9)
        ax.set_xlim(0, 7); ax.set_ylim(-0.8, 3.4); ax.axis("off")
    fig.text(0.5, -0.03, "Dashed ochre links join nodes in one P1 information set. Leaf labels: P1 payoff over P2 payoff. "
             "Bold path in (a): backward-induction outcome.", ha="center", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    _save(fig, "tree_memory.png")


def make_all():
    fig_evolutionary()
    fig_policy_overview()
    fig_type_change()
    fig_strategy()
    fig_ch_trees()
    fig_memory_trees()
    print(f"  figures written to {C.FIGURES_DIR.relative_to(C.ROOT)}")
