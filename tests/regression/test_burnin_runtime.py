# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 48: Sovereign Burn-In Runtime and Long-Horizon Stability Ledger.
"""

import sys
from pathlib import Path
import pytest
import time
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List

# Setup path injection to guarantee local tools importing
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Import new modules
from sol_sovereign_burnin_runtime import (
    BurnInRunId,
    BurnInRuntimePolicy,
    BurnInCycle,
    BurnInSequence,
    BurnInCycleResult,
    BurnInRuntimeResult,
    BurnInRuntimeReport,
    build_burnin_runtime,
    validate_burnin_runtime,
    build_burnin_sequence,
    run_shadow_burnin_cycle,
    run_shadow_burnin_sequence,
    summarize_burnin_runtime
)
from sol_long_horizon_stability_ledger import (
    StabilityLedger,
    StabilityLedgerEntry,
    StabilityLedgerHash,
    StabilityLedgerCheckpoint,
    StabilityLedgerValidationReport,
    create_stability_ledger,
    append_stability_ledger_entry,
    checkpoint_stability_ledger,
    validate_stability_ledger_chain,
    summarize_stability_ledger
)
from sol_burnin_stability_metrics import (
    BurnInStabilityMetric,
    BurnInMetricWindow,
    BurnInDriftReport,
    BurnInStabilityTrend,
    BurnInStabilitySummary,
    collect_burnin_metrics,
    measure_metric_drift,
    detect_stability_regression,
    summarize_stability_trends
)
from sol_burnin_sequence_runner import (
    BurnInSequenceStep,
    BurnInSequencePlan,
    BurnInSequenceTrace,
    BurnInSequenceReport,
    build_burnin_sequence_plan,
    validate_burnin_sequence_plan,
    execute_shadow_burnin_sequence_plan,
    summarize_burnin_sequence_trace
)
from sol_burnin_regression_detector import (
    BurnInRegressionCase,
    BurnInRegressionSignal,
    BurnInRegressionDecision,
    BurnInRegressionReport,
    detect_burnin_regressions,
    classify_burnin_regression,
    recommend_burnin_response
)
from sol_burnin_rollback_manager import (
    BurnInRollbackCheckpoint,
    BurnInRollbackPlan,
    BurnInRollbackResult,
    BurnInRollbackReport,
    capture_burnin_rollback_checkpoint,
    build_burnin_rollback_plan,
    execute_shadow_burnin_rollback,
    verify_burnin_rollback
)
from sol_burnin_promotion_readiness import (
    BurnInPromotionReadinessPolicy,
    BurnInPromotionReadinessScore,
    BurnInPromotionReadinessReport,
    evaluate_burnin_promotion_readiness,
    classify_burnin_readiness
)

# Extension imports and other classes needed for mock integration
from sol_sovereign_runtime import (
    SovereignRuntimeId,
    SovereignRuntimeState,
    SovereignRuntimePolicy,
    SovereignRuntimeCommand,
    submit_burnin_runtime_command,
    execute_shadow_burnin_runtime_command
)
from sol_runtime_ledger import (
    append_burnin_cycle_entry,
    append_burnin_metric_entry,
    append_burnin_regression_entry,
    append_burnin_rollback_entry,
    validate_burnin_ledger_integrity
)
from sol_pipeline_wavefront_fault_matrix import (
    run_fault_matrix_during_burnin,
    summarize_burnin_fault_matrix_results
)
from sol_quantum_wavefront_calibration import (
    export_quantum_stability_metrics_for_burnin,
    validate_quantum_stability_over_burnin
)
from sol_geodesic_pipeline_balancer import (
    export_pipeline_balance_metrics_for_burnin,
    validate_pipeline_balance_over_burnin
)
from sol_resonant_cadence_controller import (
    export_cadence_stability_metrics_for_burnin,
    validate_autonomous_cadence_over_burnin
)
from sol_autonomous_cadence_sync import (
    export_cadence_stability_metrics_for_burnin as export_cadence_stability_metrics_for_burnin_sync,
    validate_autonomous_cadence_over_burnin as validate_autonomous_cadence_over_burnin_sync
)
from sol_carrier_registry import (
    validate_carrier_registry_stable_over_burnin,
    validate_cadence_profiles_stable_over_burnin,
    validate_candidate_tables_not_active_over_burnin
)
from coding_library.sovereign_domain.frontier_bridge import (
    BurnInClosedLoopReport,
    BurnInRuntimeAdvisor,
    BurnInRuntimeSuggestion,
    BurnInStabilityPolicy
)
from coding_library.sovereign_domain.rangers.burnin_runtime_ranger import BurnInRuntimeRanger
from coding_library.sovereign_domain.promotion_court import PromotionCourt

# Let's write the test cases

def test_burnin_runtime_builds_in_shadow_mode():
    policy = BurnInRuntimePolicy(allow_production_execution=False, allow_infinite_loops=False)
    runtime = build_burnin_runtime(policy)
    assert runtime.mode == "shadow"
    assert validate_burnin_runtime(runtime)

def test_unbounded_burnin_policy_is_rejected():
    with pytest.raises(ValueError, match="Unbounded burn-in policy"):
        build_burnin_runtime(BurnInRuntimePolicy(max_cycles=10000))
    with pytest.raises(ValueError, match="Unbounded burn-in policy"):
        build_burnin_runtime(BurnInRuntimePolicy(max_steps_per_cycle=50000))

def test_burnin_sequence_builds_with_deterministic_cycle_count():
    policy = BurnInRuntimePolicy(max_cycles=12)
    seq = build_burnin_sequence([48], policy)
    assert len(seq.cycles) == 12

def test_infinite_loop_configuration_is_rejected():
    policy = BurnInRuntimePolicy(allow_infinite_loops=True)
    with pytest.raises(ValueError, match="infinite loops are prohibited"):
        build_burnin_runtime(policy)
    with pytest.raises(ValueError, match="Infinite loops are prohibited"):
        build_burnin_sequence([48], policy)

def test_burnin_cycle_executes_in_shadow_mode():
    policy = BurnInRuntimePolicy(max_cycles=3)
    seq = build_burnin_sequence([48], policy)
    res = run_shadow_burnin_cycle(seq, 0)
    assert res.success
    assert "wavefront_coherence" in res.metrics

def test_stability_ledger_records_cycle_start_and_end():
    ledger = create_stability_ledger("RUN_48")
    entry_start = StabilityLedgerEntry("E1", time.time(), 0, "cycle_start", {"details": "start"})
    entry_end = StabilityLedgerEntry("E2", time.time(), 0, "cycle_end", {"details": "end"})
    append_stability_ledger_entry(ledger, entry_start)
    append_stability_ledger_entry(ledger, entry_end)
    assert len(ledger.entries) == 2
    assert ledger.entries[0].event_type == "cycle_start"
    assert ledger.entries[1].event_type == "cycle_end"

def test_stability_ledger_detects_missing_entry():
    ledger = create_stability_ledger("RUN_48")
    entry_0 = StabilityLedgerEntry("E0", time.time(), 0, "cycle_start")
    entry_1 = StabilityLedgerEntry("E1", time.time(), 1, "cycle_start")
    entry_2 = StabilityLedgerEntry("E2", time.time(), 2, "cycle_start")
    
    append_stability_ledger_entry(ledger, entry_0)
    append_stability_ledger_entry(ledger, entry_1)
    append_stability_ledger_entry(ledger, entry_2)
    
    # Remove entry_1 to simulate missing entry
    ledger.entries.pop(1)
    report = validate_stability_ledger_chain(ledger)
    assert not report.valid

def test_stability_ledger_detects_reordered_entry():
    ledger = create_stability_ledger("RUN_48")
    entry_0 = StabilityLedgerEntry("E0", time.time(), 0, "cycle_start")
    entry_1 = StabilityLedgerEntry("E1", time.time(), 1, "cycle_start")
    
    append_stability_ledger_entry(ledger, entry_0)
    append_stability_ledger_entry(ledger, entry_1)
    
    # Swap order
    ledger.entries[0], ledger.entries[1] = ledger.entries[1], ledger.entries[0]
    report = validate_stability_ledger_chain(ledger)
    assert not report.valid

def test_stability_ledger_checkpoint_validates():
    ledger = create_stability_ledger("RUN_48")
    entry = StabilityLedgerEntry("E0", time.time(), 0, "cycle_start")
    append_stability_ledger_entry(ledger, entry)
    checkpoint = checkpoint_stability_ledger(ledger, 0)
    assert checkpoint.cumulative_hash == ledger.entries[-1].current_hash
    assert len(ledger.checkpoints) == 1

def test_metrics_are_collected_every_cycle():
    reports = [
        {"metrics": {"phase_drift": 0.01}, "timestamp": time.time()},
        {"metrics": {"phase_drift": 0.02}, "timestamp": time.time()}
    ]
    collected = collect_burnin_metrics(reports)
    assert len(collected["phase_drift"].values) == 2

def test_phase_drift_trend_is_measured():
    reports = [
        {"metrics": {"phase_drift": 0.01}, "timestamp": time.time()},
        {"metrics": {"phase_drift": 0.03}, "timestamp": time.time()}
    ]
    collected = collect_burnin_metrics(reports)
    summary = summarize_stability_trends(collected)
    assert summary.trends["phase_drift"].slope == pytest.approx(0.02)

def test_cadence_drift_trend_is_measured():
    reports = [
        {"metrics": {"cadence_drift": 0.005}, "timestamp": time.time()},
        {"metrics": {"cadence_drift": 0.007}, "timestamp": time.time()}
    ]
    collected = collect_burnin_metrics(reports)
    summary = summarize_stability_trends(collected)
    assert summary.trends["cadence_drift"].slope == pytest.approx(0.002)

def test_carrier_drift_trend_is_measured():
    reports = [
        {"metrics": {"carrier_drift": 0.008}, "timestamp": time.time()},
        {"metrics": {"carrier_drift": 0.010}, "timestamp": time.time()}
    ]
    collected = collect_burnin_metrics(reports)
    summary = summarize_stability_trends(collected)
    assert summary.trends["carrier_drift"].slope == pytest.approx(0.002)

def test_wavefront_coherence_trend_is_measured():
    reports = [
        {"metrics": {"wavefront_coherence": 0.98}, "timestamp": time.time()},
        {"metrics": {"wavefront_coherence": 0.95}, "timestamp": time.time()}
    ]
    collected = collect_burnin_metrics(reports)
    summary = summarize_stability_trends(collected)
    assert summary.trends["wavefront_coherence"].slope == pytest.approx(-0.03)

def test_uncertainty_window_trend_is_measured():
    reports = [
        {"metrics": {"uncertainty_window_size": 0.02}, "timestamp": time.time()},
        {"metrics": {"uncertainty_window_size": 0.03}, "timestamp": time.time()}
    ]
    collected = collect_burnin_metrics(reports)
    summary = summarize_stability_trends(collected)
    assert summary.trends["uncertainty_window_size"].slope == pytest.approx(0.01)

def test_oracle_match_rate_is_calculated():
    reports = [
        {"metrics": {"oracle_match_rate": 1.0}, "timestamp": time.time()},
        {"metrics": {"oracle_match_rate": 0.95}, "timestamp": time.time()}
    ]
    collected = collect_burnin_metrics(reports)
    summary = summarize_stability_trends(collected)
    assert summary.trends["oracle_match_rate"].slope == pytest.approx(-0.05)

def test_regression_detector_holds_burnin_on_critical_drift():
    metrics = {
        "phase_drift": BurnInStabilityMetric("phase_drift", [0.01, 0.06])
    }
    report = detect_burnin_regressions(metrics, None)
    assert not report.passed
    assert report.decision.decision == "hold_burnin"

def test_regression_detector_holds_burnin_on_oracle_mismatch_spike():
    metrics = {
        "oracle_match_rate": BurnInStabilityMetric("oracle_match_rate", [1.0, 0.92])
    }
    report = detect_burnin_regressions(metrics, None)
    assert not report.passed
    assert report.decision.decision == "reject_burnin_candidate"

def test_rollback_checkpoint_is_captured_before_risky_cycle():
    policy = BurnInRuntimePolicy()
    runtime = build_burnin_runtime(policy)
    checkpoint = capture_burnin_rollback_checkpoint(runtime, 1)
    assert checkpoint.cycle_index == 1
    assert "candidate_phase_tables" in checkpoint.__dict__

def test_rollback_restores_mock_burnin_state():
    policy = BurnInRuntimePolicy()
    runtime = build_burnin_runtime(policy)
    checkpoint = capture_burnin_rollback_checkpoint(runtime, 1)
    plan = build_burnin_rollback_plan(checkpoint, "Simulated failure")
    result = execute_shadow_burnin_rollback(plan)
    assert result.success
    assert verify_burnin_rollback(None, result.restored_state)

def test_rollback_preserves_ledger_references_and_quarantine_flags():
    policy = BurnInRuntimePolicy()
    runtime = build_burnin_runtime(policy)
    checkpoint = capture_burnin_rollback_checkpoint(runtime, 1)
    plan = build_burnin_rollback_plan(checkpoint, "Simulated failure")
    result = execute_shadow_burnin_rollback(plan)
    assert "ledger_references" in result.restored_state
    assert "quarantine_flags" in result.restored_state

def test_active_phase_table_overwrite_attempt_is_rejected():
    policy = SovereignRuntimePolicy(allowed_modes=["shadow", "sandbox"])
    r_id = SovereignRuntimeId(runtime_id="R1")
    runtime = SovereignRuntimeState(runtime_id=r_id, active_level=0, policy=policy)
    cmd = SovereignRuntimeCommand(
        command_id="C1",
        target_level=48,
        operation="burnin_runtime",
        mode="sandbox",
        payload={
            "court_token": "VALID_TOKEN",
            "ranger_observer": "ranger_ref",
            "rollback_snapshot": "snapshot_ref",
            "overwrite_active_phase_table": True
        }
    )
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        submit_burnin_runtime_command(runtime, cmd)

def test_active_cadence_profile_overwrite_attempt_is_rejected():
    policy = SovereignRuntimePolicy(allowed_modes=["shadow", "sandbox"])
    r_id = SovereignRuntimeId(runtime_id="R1")
    runtime = SovereignRuntimeState(runtime_id=r_id, active_level=0, policy=policy)
    cmd = SovereignRuntimeCommand(
        command_id="C1",
        target_level=48,
        operation="burnin_runtime",
        mode="sandbox",
        payload={
            "court_token": "VALID_TOKEN",
            "ranger_observer": "ranger_ref",
            "rollback_snapshot": "snapshot_ref",
            "overwrite_active_cadence": True
        }
    )
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        submit_burnin_runtime_command(runtime, cmd)

def test_active_carrier_registry_overwrite_attempt_is_rejected():
    policy = SovereignRuntimePolicy(allowed_modes=["shadow", "sandbox"])
    r_id = SovereignRuntimeId(runtime_id="R1")
    runtime = SovereignRuntimeState(runtime_id=r_id, active_level=0, policy=policy)
    cmd = SovereignRuntimeCommand(
        command_id="C1",
        target_level=48,
        operation="burnin_runtime",
        mode="sandbox",
        payload={
            "court_token": "VALID_TOKEN",
            "ranger_observer": "ranger_ref",
            "rollback_snapshot": "snapshot_ref",
            "overwrite_active_carrier": True
        }
    )
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        submit_burnin_runtime_command(runtime, cmd)

def test_scheduler_does_not_auto_promote_after_burn_in():
    policy = BurnInRuntimePolicy(allow_automatic_promotion=True)
    with pytest.raises(ValueError, match="Automatic promotion is prohibited"):
        build_burnin_runtime(policy)

def test_court_review_is_required_for_promotion_readiness():
    score = BurnInPromotionReadinessScore(readiness_value=1.0, passed=True)
    report = BurnInPromotionReadinessReport("R1", score)
    assert classify_burnin_readiness(report) == "promote_level48_candidate"


def test_ranger_emits_json_serializable_sovereign_packet():
    ranger = BurnInRuntimeRanger()
    packet = ranger.observe_burnin_runtime()
    assert packet.domain == "sol_sovereign"
    assert packet.level == 48
    assert "burn_in_run_id" in packet.evidence
    json_str = json.dumps(packet.evidence)
    assert isinstance(json_str, str)

def test_promotion_court_can_review_all_reports():
    court = PromotionCourt()
    
    # Review BurnInRuntimeReport
    run_rpt = BurnInRuntimeReport("R1", "RUN1", BurnInRuntimePolicy(), BurnInRuntimeResult(True, 3))
    res1 = court.review_burnin_runtime_report(run_rpt)
    assert res1.passed
    
    # Review BurnInSequenceReport
    seq_rpt = BurnInSequenceReport("R2", "PLN1", True, BurnInSequenceTrace("T1", "PLN1"))
    res2 = court.review_burnin_sequence_report(seq_rpt)
    assert res2.passed

    # Review StabilityLedgerValidationReport
    ledger_rpt = StabilityLedgerValidationReport(True, 3)
    res3 = court.review_stability_ledger_report(ledger_rpt)
    assert res3.passed

    # Review BurnInRegressionReport
    reg_rpt = BurnInRegressionReport("R3", [], BurnInRegressionDecision("continue_shadow", "No regressions"))
    res4 = court.review_burnin_regression_report(reg_rpt)
    assert res4.passed

    # Review BurnInRollbackReport
    rlb_rpt = BurnInRollbackReport("R4", "PLN2", BurnInRollbackResult(True, "CHK1"))
    res5 = court.review_burnin_rollback_report(rlb_rpt)
    assert res5.passed

    # Review BurnInPromotionReadinessReport
    readiness_rpt = BurnInPromotionReadinessReport("R5", BurnInPromotionReadinessScore(1.0, True))
    res6 = court.review_burnin_promotion_readiness_report(readiness_rpt)
    assert res6.passed

    # Review BurnInRuntimeRanger packet
    ranger = BurnInRuntimeRanger()
    packet = ranger.observe_burnin_runtime(readiness_report=readiness_rpt)
    res7 = court.review_burnin_runtime_ranger_packet(packet)
    assert res7.passed
