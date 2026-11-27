# Fair Access to Shared EV Chargers

This is the starter data for the game theory semester project. Every supplied row is synthetic. It is not a real campus record and has not been fitted to ACN-Data. No real people, fees or preferences are represented.

## Start here

1. Read the Word project brief.
2. Load the mini_case files and reproduce mini_case_expected.json with your own simulator.
3. Select ONE scenario from sessions_public.csv: low, medium or high.
4. Use chargers.csv, policies.csv and config.json for the main runs.
5. Keep drivers_private.csv out of the public queue policy and other agents' observations.

## Main files

- sessions_public.csv: 4,320 requests. Low has 720, medium 1,440 and high 2,160. Each scenario has 60 days. The same request can appear in multiple demand scenarios, with a different request_id. Do not run those copies together.
- drivers_private.csv: 40 fake drivers, their private type, utility weights and rule labels. Give each driver only its own row. The evaluator can use all rows after decisions have been made.
- chargers.csv: six 6 kW chargers. Each supplies 3 kWh in a 30-minute slot, limited by remaining demand.
- policies.csv: P0 first come first served; P1 penalty only; P2 history only; P3 history and penalty.
- config.json: the exact base settings. A score affects future queue priority, not immediate utility points.
- data_summary.json: counts and the realized private-type sample. The model prior is 0.30; the supplied sample has 11 urgent drivers, not exactly 30% of 40.
- data_dictionary.csv: fields, meanings, units and observation rules.

## Small game inputs

- benchmark_game.csv: the no-penalty two-player cycle game. C means release on time. H means hold one slot. For penalty F, subtract F from each H player's own payoff.
- bayesian_types.csv: independent private types. An Urgent player has alpha=0 and a Flexible player alpha=1. In the Bayesian benchmark only, add alpha to the player's own H payoff after subtracting F. This alpha is NOT the main simulator's full utility formula.
- memory_tree.csv: all eight leaves of the P1 -> P2 -> P1 booking tree. The action menu is L/R at all moves. The payoff values are teaching points, not observations.

For the memory tree, use these information sets:

- Full information: every decision node is separate.
- Forget own first action: P1 root is separate; later nodes (L,L) and (R,L) are joined; later nodes (L,R) and (R,R) are joined. P1 still knows it is the later move and sees P2's action.
- Forget visit number: P1 root and all four later P1 nodes are joined. P1 cannot read time, history, the P2 action or an internal stage field. P2 observes P1's first move in all three variants.

In the last variant, fix P2 to L after either first move. A behavioral P1 using L with probability 1/2 on each visit gets (1+8+6+2)/4=4.25. A 50-50 lottery over always L and always R gets (1+2)/2=1.5. The behavioral draws are independent; a chosen pure plan uses its selected action at both visits.

## Time and event rules

Boundaries 0..16 cover 08:00..16:00. Charging slot t is [t,t+1). A departure at 4 allows charging in slot 3, but not slot 4.

At boundary t: finish energy from the preceding slot; enforce departures; take one hold/release decision from each newly completed driver who can remain; release expired holds; add arrivals; allocate free chargers; then deliver energy in [t,t+1). At t=16, stop after departures and final accounting. Holdings cannot be extended repeatedly. Do not expose future input rows to agents.

Once assigned, a driver remains until it finishes or departs. Charge completion and release are different events. No energy is added while idle. Hold 1 or Hold 2 is legal only if it fits before departure. A forced departure is not a voluntary bad release choice.

## Main utility and policy rules

utility = v * delivered_kwh - w * waiting_slots + h * idle_slots - F * idle_slots

If the driver is never assigned, waiting_slots = departure_slot - arrival_slot. Otherwise it is start_slot - arrival_slot. For an incomplete charge there is no idle choice, idle_slots=0, and the score is unchanged. No-shows are not part of this version.

A fully served visit with a choice updates the score after the visit: +1 for Release, -1 for any Hold, capped to [-3,3]. A car completing exactly at departure has no choice: leave its score unchanged. P0/P1 ignore scores. P2/P3 first serve drivers who have waited at least four slots, ordered by arrival and ID. Order other drivers by descending score, then arrival, then ID. Retain state over days, reset it between runs.

Driver rules:

- release: always Release.
- hold: largest legal hold up to 2 slots.
- reciprocal: Release on first visit; later Release if the previous visit was fully served with at most 2 waiting slots, otherwise Hold 1 if legal. Ignore days without a visit.
- fee_aware: maximize (h-F)*O over legal O values. Resolve payoff ties by Release.

The fee-aware rule is a short-term best response to direct idle payoff only. It is not claimed to be a best response to the whole dynamic queue game.

## Mini case

Use ONE charger, six slots, P0 and no penalty. Drivers A and B arrive at 0; C arrives at 1. Break the initial tie by ID. The mini private rows use the same utility formula as the main data.

all_release: A starts 0, B starts 2, C starts 3. Total wait 4 slots, delivered energy 15 kWh, total utility 25.
A_holds_one_slot: A starts 0 and releases at 3, B starts 3, C starts 4. Total wait 6 slots, delivered energy 15 kWh, total utility 23. B and C release on time.

The expected JSON gives all per-driver results. These values check arithmetic, not policy effectiveness.

## Recreate the data

The generator uses only the Python standard library. It writes the files in the selected output folder. Use a new folder to retain an earlier dataset.

    python generate_data.py --output data_seed_0 --seed 0 --urgent-prior 0.30

    python generate_data.py --output data_seed_0_prior_075 --seed 0 --urgent-prior 0.75

The Word brief's main comparisons use seeds 0..29. The shipped example uses seed 20261104. Type draws, strategy assignment and sessions use independent random streams, so changing the type prior preserves the public request file for a fixed seed. Type is fixed for a driver throughout a run.

For each day, 36 distinct drivers are drawn. The first 12 form low demand, the first 24 medium, and all 36 high. Arrivals use a 70% draw from slots 0..4 and a 30% draw from slots 5..8. Energy uses an equal choice from 6,9,12,15,18 kWh. Departure is arrival + required service slots + a random integer from 0..7, capped at 16. These choices are modelling assumptions, not fitted real-world distributions.

## Real data and sources

ACN-Data can be used as an optional observed-session extension: https://ev.caltech.edu/dataset.html . API use requires registration. This pack includes no ACN records. Do not treat energy delivered as ground-truth energy needed, connection time as queue arrival, or a late unplug event as proof of selfishness.

The benchmark tables, generated records and mini-case calculations in this pack may be used and changed for the course project. Cite real external data and research papers separately. Keep a record of every change to the supplied assumptions.
