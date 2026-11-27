---
team: "M. Nade Ali (23i-0116); Abdul Mateen (23i-2511); Ehtisham Abid (23i-0091); Talha Akram (23i-0139)"
degree: "Bachelors of Artificial Intelligence"
date: "28 Nov 2026"
lecturer: "Ms. Mahnoor Tariq"
cover_title: "MAS Project"
cover_subtitle: "Fair Access to Shared EV Chargers: Project Proposal"
title_lines: "Fair Access to Shared EV Chargers"
title_note: "MAS Project: One-Page Proposal"
---

# 1. Problem and Research Question

A driver whose car has finished charging may leave it in the bay rather than move it, so the charger sits idle while another driver waits. Charging networks use idle fees to discourage this; Electrify America states that "idle fees may be imposed for parking time after your charging session has ended". Drivers differ in how urgently they need energy and how much they value leaving the car, so a fee that helps the average driver may still harm some drivers. **Research question:** does an idle penalty reduce waiting, and how does it affect drivers with different needs?

# 2. Objectives

- Build a deterministic queue simulator for one site with six 6 kW chargers, 16 half-hour slots and 40 drivers, following the brief's event order exactly.
- Compare **P0** (first come, first served, no fee) with **P1** (same order, 2 points per idle slot) at low, medium and high demand over five seeded input sets: 30 runs of 60 simulated days, plus 10 fixed-Hold control runs.
- Report waiting (including unserved drivers), full service, energy, idle slots and utility before and after the penalty, for Urgent and Flexible drivers, comparing matching seeds first.
- Explain the choice with normal and extensive form games, information and recall, mixed and behavioral strategies, repeated games, a Bayesian game and an evolutionary model.

# 3. Game-Theory Framing

Each completed driver chooses between release and hold, a choice that is privately good and socially costly: a prisoner's dilemma (the C/H table). Repetition and memory can support release (trigger strategies, the Reciprocal rule), private types make it a Bayesian game, and the evolutionary model shows which behaviour spreads under each fee.

# 4. Data, Method and Deliverables

We use only the supplied synthetic archive and generate seeds 0–4 with `generate_data.py --urgent-prior 0.30` into separate folders, never editing the originals. Requests, types and rules stay identical across P0 and P1 within a seed, and the simulator must first reproduce the supplied mini case (wait 4 / utility 25, and 6 / 23 when A holds). Deliverables: the Python simulator and experiment script, saved CSV/JSON results, a local results screen with the evolutionary graph, a 6–8 page report with a calculation appendix, and automated tests.

# 5. Scope Limits

No hardware, payments, mobile app or real data; history scores and P2/P3 are excluded. Utility values are teaching points, not prices; five synthetic seeds cannot show exact behaviour at a real campus, and programmed rules are not claimed to be Nash equilibria.
