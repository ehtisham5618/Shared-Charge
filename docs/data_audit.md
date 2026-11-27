# Data audit: teacher-provided starter archive

Audit date: 2026-11-27. Folder audited: `starter_data/` (treated as read-only; nothing in it was edited).

## 1. Integrity

All 15 files match the supplied `SHA256SUMS.txt` (checked with `sha256sum -c` before any work and re-checked by `tests/test_experiments.py::test_starter_data_unchanged` after every experiment run).

## 2. File inventory and purpose

| File | Rows | Purpose in this project |
|---|---:|---|
| `sessions_public.csv` | 4,320 | Public charging requests. Shipped example uses generator seed 20261104. |
| `drivers_private.csv` | 40 | Private type, utility weights (v, w, h) and rule label per driver. |
| `chargers.csv` | 6 | Six chargers C01–C06, 6 kW each. |
| `policies.csv` | 4 | P0–P3. Only P0 (fee 0) and P1 (fee 2) are used; P2/P3 are out of scope. |
| `config.json` | – | Base settings (60 days, 16 slots, 6 chargers, urgent prior 0.30, history settings for the larger version). |
| `data_summary.json` | – | Counts and realised urgent count (11 of 40). |
| `data_dictionary.csv` | 46 | Field meanings, units and who may see each field. |
| `benchmark_game.csv` | 4 | C/H teaching game used in Sections 3–5. |
| `memory_tree.csv` | 8 | Eight leaves of the P1 → P2 → P1 memory tree. |
| `bayesian_types.csv` | 2 | Type prior (0.3 / 0.7) and alpha (0 / 1) for the Bayesian example. |
| `mini_case_public.csv`, `mini_case_private.csv`, `mini_case_expected.json` | 3, 3, – | One-charger, three-driver check case with expected per-driver results. |
| `generate_data.py` | – | Standard-library generator. **Its default output folder is `starter_data/` itself**, so it is always called with an explicit `--output`. |
| `README.md`, `SHA256SUMS.txt` | – | Pack notes and checksums. |

## 3. Schemas

`sessions_public.csv`: `scenario` (text: low/medium/high), `request_id` (text, unique), `day` (int 1–60), `driver_id` (text D001–D040), `arrival_slot` (int 0–8), `departure_slot` (int 2–16), `requested_kwh` (int 6–18, multiple of 3).

`drivers_private.csv`: `driver_id`, `private_type` (urgent/flexible), `value_per_kwh`, `wait_cost_per_slot`, `idle_benefit_per_slot` (ints), `private_strategy` (release/hold/reciprocal/fee_aware).

## 4. Checks on `sessions_public.csv` (shipped seed 20261104)

| Check | Result |
|---|---|
| Rows per scenario | low 720, medium 1,440, high 2,160 (matches brief) |
| Days per scenario | 60 in each; exactly 12 / 24 / 36 requests every day |
| Missing values | 0 |
| Duplicate rows / duplicate `request_id` | 0 / 0 |
| A driver twice on one day in one scenario | 0 |
| Unknown `driver_id` | none; all 40 drivers appear in every scenario |
| `arrival < departure ≤ 16` | true for all rows |
| `requested_kwh ≤ 3 × (departure − arrival)` | true for all rows (every request is physically feasible) |
| Requested energy values | 6, 9, 12, 15, 18 kWh, roughly equal counts |
| Arrivals in slots 0–4 | 70.0% (generator uses a 70% draw) |
| Slack slots `(departure − arrival) − kWh/3` | 0 to 7, mean 3.35 |
| Departure at 16 | 11.2% |
| Nesting | low ⊂ medium ⊂ high: each low request reappears with a new `request_id` in medium and high |

Demand against capacity: the site can deliver at most 6 × 16 × 3 = 288 kWh per day. Mean requested energy is 145 kWh/day (low), 290 kWh/day (medium) and 433 kWh/day (high). Medium demand therefore sits at capacity and high demand exceeds it even before any idle holding.

## 5. Drivers

| | release | hold | reciprocal | fee_aware | total |
|---|---:|---:|---:|---:|---:|
| urgent | 4 | 2 | 2 | 3 | 11 |
| flexible | 6 | 8 | 8 | 7 | 29 |
| total | 10 | 10 | 10 | 10 | 40 |

Weights are exactly as in the brief: Urgent (v, w, h) = (3, 3, 1); Flexible = (2, 1, 2). No missing values.

## 6. Small-game files

`benchmark_game.csv` reproduces the brief's table: CC (4,4), CH (0,6), HC (6,0), HH (1,1). `memory_tree.csv` has all eight leaves; with P2 fixed to L the P1 payoffs are LL 1, LR 8, RL 6, RR 2, exactly as quoted in the brief. `bayesian_types.csv`: urgent 0.3 / alpha 0, flexible 0.7 / alpha 1. Mini-case files match the brief's description (A and B arrive at 0, C at 1; one charger; end boundary 6).

## 7. Generated seed inputs (`data/generated/data_seed_0` … `data_seed_4`)

Created with `python starter_data/generate_data.py --output data/generated/data_seed_<k> --seed <k> --urgent-prior 0.30` (done by `python -m shared_charge generate`). Each folder passes the generator's own assertions and the simulator's `validate_inputs` (4,320 requests, 60 days per scenario, feasible requests).

| Seed | Urgent drivers | Urgent by rule (release / hold / reciprocal / fee_aware) |
|---:|---:|---|
| 0 | 12 | 4 / 3 / 3 / 2 |
| 1 | 11 | 3 / 2 / 3 / 3 |
| 2 | 15 | 5 / 4 / 3 / 3 |
| 3 | 10 | 1 / 4 / 2 / 3 |
| 4 | 6 | 0 / 3 / 1 / 2 |

Every seed has 10 drivers on each rule. The realised urgent share varies from 15% to 37.5% around the 0.30 prior, which is expected for 40 independent draws.

## 8. Discrepancies with the brief and how they were handled

1. **Seeds.** The pack's README and the "larger version" mention seeds 0–29 and P2/P3 history scores. The four-week brief limits the project to seeds 0–4 and P0/P1, so only those are run (the brief's scope note says no data changes are needed).
2. **The shipped dataset (seed 20261104) is not one of the five experimental seeds.** It is used for this audit; the experiments use the five generated seed folders, as the brief instructs.
3. **Generator default output.** Running `generate_data.py` without `--output` would overwrite the teacher files. The project never does this.
4. **Mini-case private file has no strategy column.** Actions in the mini case are fixed by the brief (all release, or A holds one slot), so the simulator passes fixed actions there.
5. **Realised type share ≠ prior.** The shipped sample has 11 urgent drivers (27.5%), not 12; generated seeds range from 6 to 15. The Bayesian example uses the prior 0.30, not the sample share, as the brief requires.

No observations were added, removed or altered.
