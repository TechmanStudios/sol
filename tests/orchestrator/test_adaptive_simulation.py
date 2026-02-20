"""Phase 1.4 deterministic adaptive simulation tests."""
from __future__ import annotations

import sys
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_ORCH_DIR = _SOL_ROOT / "tools" / "sol-orchestrator"

if str(_ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(_ORCH_DIR))

from simulate_adaptive_triggers import run_scenarios


def test_sim_cortex_sanity_fail():
    results = run_scenarios(["cortex_sanity_fail"])
    assert results[0]["passed"] is True
    assert results[0]["adaptive"]["triggered_by"] == "sanity_fail"


def test_sim_cortex_velocity_drop():
    results = run_scenarios(["cortex_velocity_drop"])
    assert results[0]["passed"] is True
    assert results[0]["adaptive"]["triggered_by"] == "velocity_drop"


def test_sim_consolidate_recovery():
    results = run_scenarios(["consolidate_recovery"])
    assert results[0]["passed"] is True
    assert results[0]["adaptive"]["triggered_by"] == "anomaly"


def test_sim_hippocampus_recovery():
    results = run_scenarios(["hippocampus_recovery"])
    assert results[0]["passed"] is True
    assert results[0]["adaptive"]["triggered_by"] == "anomaly"


def test_sim_evolve_recovery():
    results = run_scenarios(["evolve_recovery"])
    assert results[0]["passed"] is True
    assert results[0]["adaptive"]["triggered_by"] == "anomaly"
