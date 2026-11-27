"""Shared Charge: a small EV charging-queue simulator for the
"Fair Access to Shared EV Chargers" game theory project.

Modules
-------
config        fixed site settings, policies and folder paths
data          loading and validating the supplied CSV/JSON inputs
strategies    the four supplied driver rules (Release, Hold, Reciprocal, Fee aware)
simulator     the boundary-by-boundary queue engine
metrics       summary statistics for one run
experiments   the 30 main runs, 10 fixed-Hold control runs and matched comparisons
game_theory   the written game-theory examples (normal/extensive form, recall,
              mixed vs behavioral, repeated, Bayesian)
evolutionary  the replicator-style update and its 30-step trajectories
"""

__version__ = "1.0.0"
