"""Phase 2.1 tests for stage-specific trust decay/recovery dynamics."""
from __future__ import annotations

import sys
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent.parent
_ORCH_DIR = _SOL_ROOT / "tools" / "sol-orchestrator"

if str(_ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(_ORCH_DIR))

from delegation_v1 import TrustLedger


def _dynamics_config() -> dict:
    return {
        "default": {
            "alpha": 0.25,
            "success_gain": 1.0,
            "failure_penalty": 1.0,
            "min_score": 0.0,
            "max_score": 1.0,
            "history_window": 20,
            "dynamic_weight": 0.65,
            "lifetime_weight": 0.35,
            "confidence_k": 5.0,
            "confidence_ema_alpha": 0.3,
            "neutral_score": 0.5,
            "trigger_type_weights": {
                "sanity_fail": 1.0,
                "anomaly": 0.7,
            },
        },
        "stages": {
            "cortex": {
                "alpha": 0.35,
                "failure_penalty": 1.2,
                "history_window": 3,
                "trigger_type_weights": {
                    "sanity_fail": 1.0,
                    "anomaly": 0.9,
                },
            },
            "hippocampus": {
                "alpha": 0.2,
                "failure_penalty": 1.0,
                "success_gain": 1.1,
                "history_window": 5,
                "trigger_type_weights": {
                    "sanity_fail": 1.0,
                    "anomaly": 0.4,
                },
            },
        },
    }


def test_stage_specific_failure_decay(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    # One failure each: cortex should decay more strongly than hippocampus.
    ledger.record("cortex", "failed", 1.0, [], "R1")
    ledger.record("hippocampus", "failed", 1.0, [], "R2")

    snap = ledger.snapshot()["agents"]
    cortex_dyn = snap["stage:cortex"]["dynamic_trust_score"]
    hippo_dyn = snap["stage:hippocampus"]["dynamic_trust_score"]
    assert cortex_dyn < hippo_dyn


def test_success_recovery_increases_dynamic_score(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    ledger.record("cortex", "failed", 1.0, [], "R1")
    after_fail = ledger.snapshot()["agents"]["stage:cortex"]["dynamic_trust_score"]
    ledger.record("cortex", "passed", 1.0, [], "R2")
    after_pass = ledger.snapshot()["agents"]["stage:cortex"]["dynamic_trust_score"]

    assert after_pass > after_fail


def test_skipped_preserves_dynamic_score(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    ledger.record("evolve", "passed", 1.0, [], "R1")
    before_skip = ledger.snapshot()["agents"]["stage:evolve"]["dynamic_trust_score"]
    ledger.record("evolve", "skipped", 1.0, [], "R2")
    after_skip = ledger.snapshot()["agents"]["stage:evolve"]["dynamic_trust_score"]

    assert before_skip == after_skip


def test_blended_score_fields_present(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())
    ledger.record("cortex", "passed", 1.0, [], "R1")

    stats = ledger.snapshot()["agents"]["stage:cortex"]
    assert "lifetime_trust_score" in stats
    assert "dynamic_trust_score" in stats
    assert "trust_score" in stats
    assert 0.0 <= stats["trust_score"] <= 1.0


def test_stage_context_exposes_recent_trigger_rate(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    ledger.record("cortex", "passed", 1.0, ["anomaly"], "R1")
    ledger.record("cortex", "passed", 1.0, [], "R2")
    ledger.record("cortex", "passed", 1.0, ["sanity_fail"], "R3")

    ctx = ledger.get_stage_context("cortex")
    assert "recent_trigger_rate" in ctx
    assert "recent_trigger_load" in ctx
    # history is [1, 0, 1] => 0.667
    assert abs(ctx["recent_trigger_rate"] - 0.667) < 1e-6
    # load history is [0.9, 0.0, 1.0] => 0.633
    assert abs(ctx["recent_trigger_load"] - 0.633) < 1e-6


def test_stage_specific_history_window_changes_recent_rate(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    # Trigger pattern over 5 records: [1, 0, 1, 0, 1]
    pattern = [["anomaly"], [], ["sanity_fail"], [], ["anomaly"]]
    for index, trigger_types in enumerate(pattern, start=1):
        ledger.record("cortex", "passed", 1.0, trigger_types, f"C{index}")
        ledger.record("hippocampus", "passed", 1.0, trigger_types, f"H{index}")

    cortex_ctx = ledger.get_stage_context("cortex")
    hippo_ctx = ledger.get_stage_context("hippocampus")

    # Cortex window=3 => tail [1,0,1] => 0.667
    assert abs(cortex_ctx["recent_trigger_rate"] - 0.667) < 1e-6
    # Hippocampus window=5 => full [1,0,1,0,1] => 0.6
    assert abs(hippo_ctx["recent_trigger_rate"] - 0.6) < 1e-6


def test_stage_specific_trigger_load_weights_change_context(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    # Same trigger pattern, but stage-specific anomaly weights differ.
    pattern = [["anomaly"], [], ["anomaly"], [], ["anomaly"]]
    for index, trigger_types in enumerate(pattern, start=1):
        ledger.record("cortex", "passed", 1.0, trigger_types, f"C{index}")
        ledger.record("hippocampus", "passed", 1.0, trigger_types, f"H{index}")

    cortex_ctx = ledger.get_stage_context("cortex")
    hippo_ctx = ledger.get_stage_context("hippocampus")
    assert cortex_ctx["recent_trigger_load"] > hippo_ctx["recent_trigger_load"]


def test_confidence_weight_keeps_sparse_evidence_near_neutral(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    ledger.record("cortex", "passed", 1.0, [], "R1")
    stats = ledger.snapshot()["agents"]["stage:cortex"]

    assert stats["trust_confidence"] < 0.2
    assert 0.5 <= stats["trust_score"] < 0.6


def test_confidence_weight_increases_with_more_evidence(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    ledger.record("cortex", "passed", 1.0, [], "R1")
    early = ledger.snapshot()["agents"]["stage:cortex"]
    early_confidence = early["trust_confidence"]
    early_score = early["trust_score"]

    for index in range(2, 11):
        ledger.record("cortex", "passed", 1.0, [], f"R{index}")
    late = ledger.snapshot()["agents"]["stage:cortex"]

    assert late["trust_confidence"] > early_confidence
    assert late["trust_score"] > early_score


def test_stage_context_exposes_trust_confidence(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = TrustLedger(ledger_path, dynamics=_dynamics_config())

    ledger.record("cortex", "passed", 1.0, [], "R1")
    ctx = ledger.get_stage_context("cortex")

    assert "trust_confidence" in ctx
    assert "trust_confidence_ema" in ctx
    assert 0.0 <= ctx["trust_confidence"] <= 1.0
    assert 0.0 <= ctx["trust_confidence_ema"] <= 1.0
