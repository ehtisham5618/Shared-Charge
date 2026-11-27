# Implementation record

Short log of what was built and checked, in order.

## 1. Repository and data
- Teacher archive in `starter_data/` (15 files). All SHA-256 checksums match `SHA256SUMS.txt`.
- Every file audited (`docs/data_audit.md`): no missing or duplicate rows, feasible requests, low ⊂ medium ⊂ high, demand at 50% / 100% / 150% of daily capacity.
- `generate_data.py` writes into its own folder by default, so every call passes `--output`.
- Generated `data/generated/data_seed_0..4` (`--urgent-prior 0.30`). Urgent counts: 12, 11, 15, 10, 6.

## 2. Simulator
- `shared_charge/` package: `data`, `strategies`, `simulator`, `metrics`, `experiments`, command-line entry point in `__main__`.
- Event order follows the brief exactly; a hold is legal when t + O ≤ departure; a car that finishes at departure is released automatically; missing times are saved as `NA`.
- The mini case is reproduced exactly, per driver (wait 4 / energy 15 / utility 25; wait 6 / utility 23).

## 3. Experiments
- 30 main runs and 10 fixed-Hold control runs, 60 days each, saved in `results/runs/`.
- Matched comparisons in `results/comparison_by_seed.csv`, `comparison_stats.csv` and `control_*.csv`.
- A full re-run gives byte-identical outputs (129 files compared), and regenerating the seed inputs reproduces the same files.

## 4. Game theory
- `game_theory.py` and `evolutionary.py` compute every written result from the supplied CSVs. Nash equilibrium (H, H); backward induction H→H (1, 1); memory tree L, L, R (8, 4); mixed 1.5 / behavioral 4.25; δ* = 0.4; Bayesian 1.20 / 1.00 / 1.20 / 2.00 (a BNE); x₁ = 0.48125 and 0.50625.
- Report figures in `results/figures/`. The two-series chart colours were checked for colour-blind separation and contrast in light (#2A76AA / #B07A1E) and dark (#58A0D8 / #C48A22) themes.

## 5. Results screen
- FastAPI (`shared_charge/api.py`) serves only saved files, plus a re-run endpoint that checks reproducibility. React, TypeScript, Vite, Tailwind CSS and Recharts in `frontend/`; the built copy is served at http://127.0.0.1:8000.
- First version: one long light-themed page. After team feedback (too much text, too much white, no clear starting point) it was redesigned as a dark, minimal interface with five views, chosen from a floating icon sidebar on the left that expands on hover to show labels (a bottom bar on phones):
  - **Overview:** the question, one headline number, four key measures, one chart and three findings.
  - **Site:** the six-bay day plan.
  - **Drivers:** Urgent vs Flexible, driver rules, the control, and all measures.
  - **Game theory:** the evolutionary graph and the four game calculations.
  - **Data:** visit table, downloads, mini case, settings and input hashes.

  Paragraph text was cut to one-line hints, and the experiment controls are hidden on the Game theory tab, where they do not apply.
- Browser check (`scripts/ui_check.py`): no console errors and no sideways scrolling at 1440 / 1280 / 768 / 390 px; on-screen measures equal `summary.json`; "Run experiment" reproduces the saved results; the site-plan tooltip works.

## 6. Tests
- 71 pytest tests pass (`python -m pytest`).

## 7. Documents
- `docs/proposal.md`, `docs/data_audit.md`, `docs/viva_preparation.md`, `README.md`.
- `reports/final_report.md` → `.docx` (python-docx) → `.pdf` (Microsoft Word export) via `scripts/build_documents.py`, which also builds the one-page proposal (`docs/proposal.pdf`). Both follow the FAST School of Computing format (cover page, page borders, Times New Roman). The report body has the five parts the brief asks for (problem, assumptions, design, findings, limits): cover page 1, body pages 2–7, references page 8, appendix pages 9–11.
- Reading: the ACN-Data paper [3] was read in full from the authors' PDF. The MDPI evolutionary paper [4] could not be retrieved automatically (HTTP 403), so the report cites it only at the level confirmed by its abstract.
