# Viva preparation

A study aid for each team member. Every answer below refers to the code in `shared_charge/`, the saved results in `results/`, or the report. Be ready to open the file or the results screen to show where an answer comes from. Means are over seeds 0–4 unless stated.

---

## A. The problem and the design

**Why does this project use game theory at all?**
Each driver's choice affects others: a hold gives the holder a private benefit (h per slot) and makes queuing drivers wait. Outcomes depend on everyone's choices, and drivers have private information (type, weights), so it is a strategic multi-agent problem. The C/H table shows the core tension: holding is dominant (Nash equilibrium (H, H) = (1, 1)) but mutual release (C, C) = (4, 4) is better for both.

**Why study idle penalties?**
Real networks use them (Electrify America: "idle fees may be imposed for parking time after your charging session has ended"). A fee changes the payoff of holding (h − F per slot) and could move drivers from H to C. The question is whether that shortens the queue and who pays.

**What exactly are P0 and P1?**
Both use first come, first served (arrival time, then driver ID). P0 has fee 0; P1 charges F = 2 points per idle slot. Read from `policies.csv`; P2/P3 (history scores) are outside the four-week scope.

**What is the utility formula?**
`U = v·kWh − w·waiting_slots + h·idle_slots − F·idle_slots` (`simulator.py`, `visit_record`). Urgent (v, w, h) = (3, 3, 1); Flexible = (2, 1, 2). We save gross utility (before the penalty), the penalty, and net utility separately. Example from the brief: Flexible, 6 kWh, waits 1, holds 1, P1 gives 12 − 1 + 2 − 2 = 11 (a test reproduces it).

## B. How the simulator works

**Walk me through one boundary.** (`DaySimulator.run`)
1. Add the energy from slot [t−1, t): each charging car gets min(3 kWh, remaining). Cars that reach their request are "newly completed".
2. Departures at t: waiting cars become `unserved`; charging cars that finished exactly now get `forced_release`; incomplete cars become `departed_incomplete`; holders leave.
3. Newly completed cars that can stay make one decision: 0, 1 or 2 idle slots.
4. Holds that end at t release the charger.
5. Arrivals at t join the queue.
6. Free chargers (C01…C06 in order) go to waiting cars sorted by (arrival, driver_id).
7. The slot [t, t+1) runs. At t = 16 the loop stops after step 4.

**How is charger allocation done?** Step 6: `sorted(waiting, key=(arrival, driver_id))`, and each free charger takes the next driver. A driver keeps the charger until it finishes, departs or its hold ends. There is no pre-emption.

**When is a hold legal?** `legal_holds(t, departure)` returns every O in {0, 1, 2} with t + O ≤ departure. A car finishing exactly at departure has only {0}, a forced release. One decision only; holds are never extended. An illegal choice raises `ValueError` (tested).

**How do you make sure no charger serves two drivers, and that no energy is delivered during a hold?**
The simulator stores at most one visit per charger. The tests rebuild a per-slot timeline for a full high-demand run and check one driver per charger per slot, one charger per driver per slot, every slot inside [arrival, departure) and before 16, energy = 3 × charging slots, and idle slots = holding slots (`tests/test_simulator.py`).

**Why do unserved drivers have a waiting cost?** The brief defines waiting as arrival to departure for a driver who is never served. Leaving them out would make congested policies look better than they are. An unserved Urgent driver who waits 3 slots scores −9 (tested).

**What information does a driver's rule see?** (`strategies.py`) Only its own `DriverProfile`, its own `LastVisit`, and an `Observation` with boundary, fee, queue length and legal holds. A test checks that a rule is called only with its own profile and that `Observation` has exactly those four fields. Rules never see other drivers' types, rules or future arrivals.

**Is the simulator random?** No. There is no randomness in the queue; all randomness is in the generated inputs. Same inputs and settings give identical results (test re-runs and compares; the "Run experiment" button does the same live).

## C. The four driver rules

* **Release:** always 0.
* **Hold:** `max(legal_holds)`, so 2 if possible, else 1, else 0.
* **Reciprocal:** first visit in the run → 0. Later → 0 if the last visit was fully served with ≤ 2 waiting slots, otherwise 1 if legal. Memory (`LastVisit`) is kept across days within a run and reset between runs. A day without a visit leaves it unchanged (tested across a skipped day).
* **Fee aware:** maximise (h − F)·O, ties → release. P0: h > 0 → hold maximum. P1: Urgent h − F = −1 → release; Flexible h − F = 0 → tie → release. So under P1 no Fee aware driver holds.

**Are these rules Nash equilibria?** No. They are programmed behaviour supplied by the brief. Fee aware is a short-term best response to the direct idle payoff only.

## D. Experiments

**Why matched seeds?** Within a seed, P0 and P1 read identical files (same requests, types, rules), so any difference is caused by the fee alone. This is a paired comparison and removes noise from different random demand. A test checks that the request/type/rule columns are identical row by row.

**Why five seeds?** The brief's four-week scope. Five seeds show whether the direction of an effect is stable and give a range. They are not enough for strong statistical claims, and they are synthetic, so they say nothing exact about a real campus.

**How many runs?** 2 policies × 3 demands × 5 seeds = 30 main runs of 60 days, plus 10 control runs (medium, all drivers forced to Hold, both policies, five seeds). The control uses `strategy_override="hold"` and does not edit the CSV.

**Why does fixed Hold not respond to the fee?** Its decision function ignores F, so P0 and P1 produce identical schedules (difference exactly 0 in all five seeds). The fee is then a pure transfer: on average 2,093 points per run, −1.45 net utility per visit.

## E. Findings (be ready to quote)

* Waiting fell and full service rose in **all 15** matched comparisons. Waiting: low 0.52 → 0.38, medium 2.88 → 2.64, high 4.26 → 4.10 slots. Full service: +1.8, +3.5, +2.4 percentage points.
* Idle slots fell by 49% (low), 39% (medium) and 36% (high), not to zero, because Hold and Reciprocal drivers still hold. Fee aware idle use drops from about 280–290 slots per run to 0.
* Net utility per visit: low −0.99 (worse in all 5 seeds), medium +0.30, high +0.34.
* Urgent: medium +0.94, high +0.75, low −0.66. Flexible: medium +0.03 (range −0.07 to +0.15, better in 3 of 5), high +0.17, low −1.13.
* By rule at medium: Release +1.38, Reciprocal +0.45, Fee aware −0.13, Hold −0.52 per visit.
* **When the fee does not help:** at low demand the queue is short, so the time saved (about 4 minutes) is worth less than the holding benefit given up and the penalties paid.

**Most important finding in one sentence:** the fee shortens the queue whenever some drivers respond to it, but it only raises drivers' net utility when chargers are scarce, and the gain goes mainly to Urgent drivers.

## F. Game theory

**Nash equilibrium versus social optimum.** Equilibrium: no player gains by deviating alone, which here is (H, H) = (1, 1) because H is strictly dominant (6 > 4, 1 > 0). Social optimum: the highest total, (C, C) = 8. They differ because each player ignores the cost its hold imposes on the other (a negative externality). With F = 2, H payoffs drop by 2, C becomes weakly dominant, and (C, C) is an equilibrium.

**Perfect versus imperfect information.** Perfect: every information set is a single node; P2 sees P1's move. Backward induction gives P2 = (H after C, H after H), P1 = H, path (H, H). Imperfect: P2's two nodes are joined, so P2 must choose the same action at both. That is equivalent to the simultaneous normal form.

**Perfect versus imperfect recall.** Perfect recall means a player never forgets its own earlier moves or what it knew. The hidden-move C/H game keeps perfect recall (P2 has nothing earlier to forget). The memory tree breaks it: "forget own first action" joins (L,L) with (R,L) and (L,R) with (R,R); "forget the stage" joins the root with all four later P1 nodes. Full-information solution: L, L, R with (8, 4).

**Mixed versus behavioral.** Mixed: randomise over complete plans before play; 50–50 over always-L and always-R gives LL or RR, with expected 0.5×1 + 0.5×2 = 1.5. Behavioral: randomise independently at each information set; fresh 50–50 draws give all four pairs with 0.25, expected (1+8+6+2)/4 = 4.25. With perfect recall, "draw once, then repeat" reproduces the mixed lottery (Kuhn's theorem). Under forgotten stage, P1 cannot remember its draw, so it cannot reproduce it. Its best single probability is p = 5/11, giving 4.27.

**Finite versus infinite repetition.** Three known rounds: the last round is a one-shot game → (H, H); then round 2, then round 1 → (H, H) in all rounds, 3 points each. Infinite with grim trigger: 4/(1−δ) ≥ 6 + δ/(1−δ) ⟺ δ ≥ 0.4. At δ = 0.2: 5.00 < 6.25 (deviate). At δ = 0.5: 8.00 > 7.00 (cooperate). In punishment H earns 1 and C earns 0, so H stays a best response. δ is the weight on a payoff one round later.

**Bayesian Nash equilibrium.** A strategy assigns an action to each type; it is an equilibrium if no type of any player can raise its expected payoff by changing its action alone. With π = 0.3 and fee 1.5: Urgent E[C] = 1.20 > E[H] = 1.00; Flexible E[H] = 2.00 > E[C] = 1.20. The plan (Urgent C, Flexible H) is a BNE, for both players by symmetry.

**Evolutionary dynamics.** Strategies that earn more than average spread: x′ = x + 0.05·x(1−x)(fC − fH). F = 0: fC − fH = −x − 1 < 0, so C shrinks (x₁ = 0.48125, x₃₀ = 0.124). F = 2: fC − fH = 1 − x > 0, so C grows (x₁ = 0.50625, x₃₀ = 0.653). All values stay in [0, 1]. This is a 30-step model path, not an ESS proof or a forecast.

## G. Limits and honesty

* Synthetic data and teaching weights; points are not money.
* Five seeds only; programmed rules; demand does not respond to the fee.
* The C/H, Bayesian and evolutionary models use a fixed teaching table, not the simulator's energy formula.
* The penalty is counted as a loss to drivers; it is not returned to them.
* ACN-Data [3] has real sessions but does not reveal urgency, private utility or why a car stayed connected.

## H. Likely "show me" requests during the demo

| Request | Where |
|---|---|
| Mini case | Results screen → Checks; `python -m shared_charge minicase`; `results/mini_case_check.json` |
| Both policies | Policy control: P0, P1, or Compare P0 and P1 |
| A finding | Headline sentence and Drivers section, medium vs low demand |
| A game calculation | Games section (normal form, δ threshold, Bayesian table) |
| Evolutionary graph | Evolution section; `results/figures/evolutionary.png` |
| Reproducibility | "Run experiment" re-runs 60 days and compares with the saved files |
| Event order | `shared_charge/simulator.py`, top docstring and `DaySimulator.run` |
