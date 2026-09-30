from __future__ import annotations

from pathlib import Path
import sys


_RSI_DIR = Path(__file__).resolve().parents[2] / "tools" / "sol-rsi"
if str(_RSI_DIR) not in sys.path:
    sys.path.insert(0, str(_RSI_DIR))

import rsi_engine


def test_reward_mutation_ignores_failed_no_execution_outcomes(monkeypatch):
    monkeypatch.setattr(
        rsi_engine,
        "_load_outcome_history",
        lambda last_n=20: [
            {
                "templates_planned": ["parameter_sweep"],
                "experiments_executed": 0,
                "delta": {"claims": 10, "fitness": 25.0},
                "error": "pipeline failed before execution",
            }
        ],
    )
    monkeypatch.setattr(rsi_engine.random, "random", lambda: 0.0)
    monkeypatch.setattr(rsi_engine.random, "uniform", lambda _a, _b: 0.0)

    genome = {
        "mutation_rate": 1.0,
        "exploration_rate": 0.2,
        "template_preferences": {"parameter_sweep": 1.0},
        "parameter_focus": {"damping_priority_zones": []},
        "experiment_types": {"enabled": [], "scope_frontier": []},
        "history": [],
    }
    reflection = rsi_engine.ReflectionReport(cycle_id=1)

    updated = rsi_engine.mutate_genome(genome, reflection)

    mutations = updated["history"][-1]["mutations"]
    assert all(not mutation.startswith("REWARD ") for mutation in mutations)
    assert updated["template_preferences"]["parameter_sweep"] == 1.0
