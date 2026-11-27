"""Fixed settings for the four-week project scope and the project folder layout."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STARTER_DIR = ROOT / "starter_data"            # teacher-provided, read-only
GENERATED_DIR = ROOT / "data" / "generated"    # data_seed_0 .. data_seed_4
RESULTS_DIR = ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
FIGURES_DIR = RESULTS_DIR / "figures"

# Site settings (project brief, section 1)
CHARGER_COUNT = 6
CHARGER_POWER_KW = 6
SLOT_MINUTES = 30
KWH_PER_SLOT = CHARGER_POWER_KW * SLOT_MINUTES / 60   # = 3 kWh per full slot
DAY_END_BOUNDARY = 16                                 # boundaries 0..16 = 08:00..16:00
DAYS_PER_RUN = 60
MAX_HOLD_SLOTS = 2

# Experiment design (project brief, section 2)
SEEDS = (0, 1, 2, 3, 4)
DEMANDS = ("low", "medium", "high")
POLICY_IDS = ("P0", "P1")       # P2/P3 (history scores) are outside this scope
URGENT_PRIOR = 0.30
CONTROL_DEMAND = "medium"
CONTROL_STRATEGY = "hold"


@dataclass(frozen=True)
class Policy:
    policy_id: str
    name: str
    fee_per_idle_slot: float
    use_history: bool


def seed_dir(seed: int) -> Path:
    return GENERATED_DIR / f"data_seed_{seed}"


def run_id(demand: str, policy_id: str, seed: int, control: bool = False) -> str:
    prefix = "control_allhold_" if control else ""
    return f"{prefix}{demand}_{policy_id}_seed{seed}"
