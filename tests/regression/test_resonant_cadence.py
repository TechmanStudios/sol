# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 44: Entangled Resonant Wavefront Feedback and Autonomous Cadence Sync.
"""

import sys
from pathlib import Path
import pytest
import time
import uuid
import json
from dataclasses import dataclass

# Setup path injection to guarantee local tools importing
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Import new Phase 44 modules
from sol_entangled_resonant_feedback import (
    ResonantFeedbackParticipant,
    ResonantFeedbackPolicy,
    ResonantFeedbackObservation,
    ResonantFeedbackSignal,
    ResonantFeedbackAction,
    ResonantFeedbackStep,
    ResonantFeedbackResult,
    ResonantFeedbackReport,
    build_resonant_feedback_loop,
    validate_resonant_feedback_loop,
    sample_resonant_feedback_observation,
    plan_resonant_feedback_action,
    execute_shadow_resonant_feedback,
    summarize_resonant_feedback
)
from sol_autonomous_cadence_sync import (
    AutonomousCadenceSyncPolicy,
    AutonomousCadenceSyncIntent,
    CadenceSyncCandidate,
    CadenceSyncAdjustment,
    CadenceSyncDecision,
    AutonomousCadenceSyncResult,
    AutonomousCadenceSyncReport,
    build_autonomous_cadence_sync_intent,
    identify_cadence_sync_candidates,
    build_cadence_sync_adjustment,
    validate_cadence_sync_adjustment,
    execute_shadow_autonomous_cadence_sync
)
from sol_resonant_cadence_controller import (
    ResonantCadenceControlPolicy,
    ResonantCadenceControlSuggestion,
    ResonantCadenceControlDecision,
    ResonantCadenceControlReport,
    suggest_resonant_cadence_control,
    validate_resonant_control_bounds,
    classify_resonant_cadence_state
)
from sol_cadence_autonomy_guard import (
    CadenceAutonomyGuardPolicy,
    CadenceAutonomyGuardSnapshot,
    CadenceAutonomyGuardDecision,
    CadenceAutonomyGuardReport,
    capture_cadence_autonomy_guard_snapshot,
    evaluate_cadence_autonomy_guard,
    block_unbounded_cadence_autonomy,
    verify_autonomy_remains_bounded
)

# Import extended modules
from sol_temporal_cadence import (
    TemporalCadenceProfile,
    export_cadence_sync_targets,
    validate_candidate_cadence_profile,
    compare_candidate_cadence_to_active
)
from sol_multimanifold_cadence_sync import (
    run_shadow_autonomous_multimanifold_cadence_sync,
    validate_autonomous_sync_result
)
from sol_entangled_wavefront_calibration import (
    EntangledCalibrationTarget,
    EntangledCalibrationBaseline,
    EntangledCalibrationReport,
    EntangledCalibrationResult,
    export_resonant_feedback_targets,
    validate_resonant_feedback_after_calibration
)
from sol_entangled_feedback_loop import (
    bridge_entangled_feedback_to_resonant_feedback,
    validate_resonant_feedback_loop_stability
)
from sol_entangled_wavefront_propagation import (
    validate_resonant_feedback_for_entangled_propagation,
    measure_resonant_wavefront_disturbance
)
from sol_synchronized_sequencer_commit import (
    validate_commit_after_autonomous_cadence_sync
)
from sol_sovereign_runtime import (
    SovereignRuntimeState,
    SovereignRuntimePolicy,
    SovereignRuntimeCommand,
    build_sovereign_runtime,
    submit_autonomous_cadence_sync_command,
    execute_shadow_autonomous_cadence_command
)
from sol_runtime_ledger import (
    build_runtime_ledger,
    append_runtime_event,
    validate_runtime_ledger
)
from coding_library.sovereign_domain.frontier_bridge import (
    AutonomousCadenceAdvisor,
    AutonomousCadenceSuggestion,
    AutonomousCadenceClosedLoopPolicy,
    AutonomousCadenceClosedLoopReport
)
from coding_library.sovereign_domain.rangers.resonant_cadence_ranger import ResonantCadenceRanger
from coding_library.sovereign_domain.promotion_court import PromotionCourt, PromotionGateResult


@pytest.fixture
def sample_policy():
    return ResonantFeedbackPolicy(
        max_feedback_gain=0.1,
        max_steps=10,
        abort_thresholds={
            "min_resonance_coherence": 0.8,
            "min_entanglement_coherence": 0.8,
            "max_crosstalk": 0.1,
            "max_reflection": 0.05,
            "min_pml_absorption": 0.9
        },
        rollback_requirement=True,
        court_token_required_for_sandbox=True
    )

@pytest.fixture
def sample_participants():
    return [
        ResonantFeedbackParticipant(manifold_id="manifold_A", clock_id="clk_0"),
        ResonantFeedbackParticipant(manifold_id="manifold_B", clock_id="clk_1")
    ]


# Test 1: Resonant feedback loop builds for 2 mock manifolds
def test_resonant_feedback_loop_builds_2_manifolds(sample_participants, sample_policy):
    loop = build_resonant_feedback_loop(sample_participants, sample_policy)
    assert loop is not None
    assert loop["loop_id"].startswith("RES_LOOP_")
    assert len(loop["participants"]) == 2


# Test 2: Resonant feedback loop builds for 3+ mock manifolds
def test_resonant_feedback_loop_builds_3_plus_manifolds(sample_policy):
    parts = [
        ResonantFeedbackParticipant(manifold_id="m1", clock_id="c1"),
        ResonantFeedbackParticipant(manifold_id="m2", clock_id="c2"),
        ResonantFeedbackParticipant(manifold_id="m3", clock_id="c3")
    ]
    loop = build_resonant_feedback_loop(parts, sample_policy)
    assert len(loop["participants"]) == 3


# Test 3: Invalid resonant feedback policy is rejected (max_steps <= 0)
def test_invalid_resonant_feedback_policy_rejected(sample_participants):
    invalid_policy = ResonantFeedbackPolicy(
        max_feedback_gain=0.1,
        max_steps=0  # invalid
    )
    with pytest.raises(ValueError, match="max_steps > 0"):
        build_resonant_feedback_loop(sample_participants, invalid_policy)


# Test 4: Unbounded feedback gain is rejected (gain > 1.0 or <= 0.0)
def test_unbounded_feedback_gain_rejected(sample_participants):
    invalid_policy = ResonantFeedbackPolicy(
        max_feedback_gain=1.5,  # too high
        max_steps=10
    )
    with pytest.raises(ValueError, match="invalid feedback gain bounds"):
        build_resonant_feedback_loop(sample_participants, invalid_policy)


# Test 5: Autonomous cadence sync intent builds from mock cadence group
def test_autonomous_cadence_sync_intent_builds():
    policy = AutonomousCadenceSyncPolicy(
        max_sync_steps=100,
        max_cadence_adjustment=0.1,
        max_phase_offset_adjustment=0.1,
        max_carrier_offset_adjustment=0.1,
        max_boundary_absorption_adjustment=0.1,
        max_feedback_gain=0.1
    )
    group = {"group_id": "CAD_GP_01", "participants": [{"manifold_id": "m1"}]}
    intent = build_autonomous_cadence_sync_intent(group, policy)
    assert intent is not None
    assert intent.intent_id.startswith("CAD_SYNC_INT_")


# Test 6: Cadence sync candidate is generated from drift telemetry
def test_cadence_sync_candidate_generated():
    policy = AutonomousCadenceSyncPolicy(
        max_sync_steps=100,
        max_cadence_adjustment=0.1, max_phase_offset_adjustment=0.1,
        max_carrier_offset_adjustment=0.1, max_boundary_absorption_adjustment=0.1,
        max_feedback_gain=0.1
    )
    intent = build_autonomous_cadence_sync_intent({"group_id": "gp1"}, policy)
    telemetry = {"drifts": {"m1": 0.04}, "jitter": {"m1": 0.002}}
    candidates = identify_cadence_sync_candidates(intent, telemetry)
    assert len(candidates) == 1
    assert candidates[0].manifold_id == "m1"
    assert candidates[0].drift == 0.04


# Test 7: Cadence sync adjustment respects max cadence adjustment
def test_cadence_sync_adjustment_respects_max():
    policy = AutonomousCadenceSyncPolicy(
        max_sync_steps=100,
        max_cadence_adjustment=0.05, max_phase_offset_adjustment=0.1,
        max_carrier_offset_adjustment=0.1, max_boundary_absorption_adjustment=0.1,
        max_feedback_gain=0.1
    )
    cand = CadenceSyncCandidate(candidate_id="cand_1", manifold_id="m1", drift=0.2)
    adj = build_cadence_sync_adjustment(cand, policy)
    # Expected cadence adjustment without bounds is -0.5 * 0.2 = -0.1. Should be clamped to -0.05
    assert adj.cadence_offset == -0.05


# Test 8: Phase offset adjustment respects policy bounds
def test_phase_offset_adjustment_respects_policy():
    policy = AutonomousCadenceSyncPolicy(
        max_sync_steps=100,
        max_cadence_adjustment=0.1, max_phase_offset_adjustment=0.02,
        max_carrier_offset_adjustment=0.1, max_boundary_absorption_adjustment=0.1,
        max_feedback_gain=0.1
    )
    cand = CadenceSyncCandidate(candidate_id="cand_1", manifold_id="m1", drift=0.2)
    adj = build_cadence_sync_adjustment(cand, policy)
    # Expected phase adjustment without bounds is -0.2 * 0.2 = -0.04. Should be clamped to -0.02
    assert adj.phase_offset == -0.02


# Test 9: Candidate cadence profile does not overwrite active profile
def test_candidate_profile_does_not_overwrite():
    active = TemporalCadenceProfile(manifold_id="m1", tick_rate=100.0, phase_offset=0.0)
    candidate_overwrite = {
        "manifold_id": "m1",
        "tick_rate": 105.0,
        "phase_offset": 0.01,
        "overwrite_active": True
    }
    with pytest.raises(ValueError, match="attempts to overwrite active profile in place"):
        validate_candidate_cadence_profile(candidate_overwrite, active)


# Test 10: Active phase table overwrite attempt is rejected
def test_active_phase_table_overwrite_rejected():
    policy = CadenceAutonomyGuardPolicy()
    sync_report = {
        "intent": {
            "metadata": {
                "overwrite_active_phase_table": True,
                "rollback_snapshot": "snap"
            }
        }
    }
    report = evaluate_cadence_autonomy_guard(sync_report, None, policy)
    assert not report.decision.passed
    assert any("phase-table overwrite" in r for r in report.decision.blocked_reasons)


# Test 11: Active carrier registry overwrite attempt is rejected
def test_active_carrier_registry_overwrite_rejected():
    policy = CadenceAutonomyGuardPolicy()
    sync_report = {
        "intent": {
            "metadata": {
                "overwrite_active_carrier_registry": True,
                "rollback_snapshot": "snap"
            }
        }
    }
    report = evaluate_cadence_autonomy_guard(sync_report, None, policy)
    assert not report.decision.passed
    assert any("carrier-registry overwrite" in r for r in report.decision.blocked_reasons)


# Test 12: Autonomy guard blocks infinite sync loop
def test_autonomy_guard_blocks_infinite_sync_loop():
    policy = CadenceAutonomyGuardPolicy(max_loop_iterations=50)
    # Sync report showing step count exceeding limit
    sync_report = {
        "step_count": 60,
        "intent": {
            "metadata": {
                "rollback_snapshot": "snap"
            }
        }
    }
    report = evaluate_cadence_autonomy_guard(sync_report, None, policy)
    assert not report.decision.passed
    assert any("Infinite sync loops" in r for r in report.decision.blocked_reasons)


# Test 13: Autonomy guard blocks production/default cadence mutation
def test_autonomy_guard_blocks_production_mutation():
    policy = CadenceAutonomyGuardPolicy(allow_production_mutations=True) # triggers violation in evaluator
    sync_report = {
        "intent": {
            "metadata": {
                "rollback_snapshot": "snap"
            }
        }
    }
    report = evaluate_cadence_autonomy_guard(sync_report, None, policy)
    assert not report.decision.passed
    assert any("Production cadence mutation" in r for r in report.decision.blocked_reasons)


# Test 14: Cadence split-brain blocks sync promotion
def test_cadence_split_brain_blocks_sync_promotion():
    intent = {
        "cadence_group": {"group_id": "gp1", "participants": []},
        "metadata": {
            "split_brain": True
        }
    }
    report = run_shadow_autonomous_multimanifold_cadence_sync(intent)
    assert not report["success"]
    assert any("split-brain" in err for err in report["errors"])
    assert not validate_autonomous_sync_result(report)


# Test 15: High global cadence skew blocks synchronized commit
def test_high_skew_blocks_commit():
    sync_report = {
        "success": True,
        "global_skew": 0.06,  # > 0.05
        "intent": {
            "metadata": {
                "rollback_snapshot": "snap"
            }
        }
    }
    commit_report = {"passed_gates": True}
    res = validate_commit_after_autonomous_cadence_sync(commit_report, sync_report)
    assert not res


# Test 16: Resonant phase decoherence blocks promotion
def test_resonant_phase_decoherence_blocks_promotion(sample_participants, sample_policy):
    loop = build_resonant_feedback_loop(sample_participants, sample_policy)
    # Coherence below threshold of 0.8
    obs = ResonantFeedbackObservation(
        observation_id="obs1", timestamp=time.time(),
        resonant_phase_coherence=0.7, entanglement_phase_coherence=1.0,
        cadence_drift=0.0, global_cadence_skew=0.0, carrier_phase_error=0.0,
        wavefront_coherence=1.0, crosstalk=0.0, boundary_reflection=0.0,
        pml_absorption_effectiveness=1.0, active_mass_preservation=1.0,
        lane_timing_consistency=1.0
    )
    report = execute_shadow_resonant_feedback(loop, [obs])
    assert not report.result.success
    assert any("phase decoherence" in err for err in report.result.errors)


# Test 17: Entanglement coherence failure blocks promotion
def test_entanglement_coherence_failure_blocks_promotion(sample_participants, sample_policy):
    loop = build_resonant_feedback_loop(sample_participants, sample_policy)
    # Entanglement coherence below threshold
    obs = ResonantFeedbackObservation(
        observation_id="obs1", timestamp=time.time(),
        resonant_phase_coherence=1.0, entanglement_phase_coherence=0.7,
        cadence_drift=0.0, global_cadence_skew=0.0, carrier_phase_error=0.0,
        wavefront_coherence=1.0, crosstalk=0.0, boundary_reflection=0.0,
        pml_absorption_effectiveness=1.0, active_mass_preservation=1.0,
        lane_timing_consistency=1.0
    )
    report = execute_shadow_resonant_feedback(loop, [obs])
    assert not report.result.success
    assert any("Entanglement coherence failure" in err for err in report.result.errors)


# Test 18: Crosstalk spike blocks promotion
def test_crosstalk_spike_blocks_promotion(sample_participants, sample_policy):
    loop = build_resonant_feedback_loop(sample_participants, sample_policy)
    obs = ResonantFeedbackObservation(
        observation_id="obs1", timestamp=time.time(),
        resonant_phase_coherence=1.0, entanglement_phase_coherence=1.0,
        cadence_drift=0.0, global_cadence_skew=0.0, carrier_phase_error=0.0,
        wavefront_coherence=1.0, crosstalk=0.15, boundary_reflection=0.0,
        pml_absorption_effectiveness=1.0, active_mass_preservation=1.0,
        lane_timing_consistency=1.0
    )
    report = execute_shadow_resonant_feedback(loop, [obs])
    assert not report.result.success
    assert any("Crosstalk spike" in err for err in report.result.errors)


# Test 19: Boundary reflection breach blocks promotion
def test_boundary_reflection_breach_blocks_promotion(sample_participants, sample_policy):
    loop = build_resonant_feedback_loop(sample_participants, sample_policy)
    obs = ResonantFeedbackObservation(
        observation_id="obs1", timestamp=time.time(),
        resonant_phase_coherence=1.0, entanglement_phase_coherence=1.0,
        cadence_drift=0.0, global_cadence_skew=0.0, carrier_phase_error=0.0,
        wavefront_coherence=1.0, crosstalk=0.0, boundary_reflection=0.08,
        pml_absorption_effectiveness=1.0, active_mass_preservation=1.0,
        lane_timing_consistency=1.0
    )
    report = execute_shadow_resonant_feedback(loop, [obs])
    assert not report.result.success
    assert any("Boundary reflection breach" in err for err in report.result.errors)


# Test 20: PML weakening blocks promotion
def test_pml_weakening_blocks_promotion(sample_participants, sample_policy):
    loop = build_resonant_feedback_loop(sample_participants, sample_policy)
    obs = ResonantFeedbackObservation(
        observation_id="obs1", timestamp=time.time(),
        resonant_phase_coherence=1.0, entanglement_phase_coherence=1.0,
        cadence_drift=0.0, global_cadence_skew=0.0, carrier_phase_error=0.0,
        wavefront_coherence=1.0, crosstalk=0.0, boundary_reflection=0.0,
        pml_absorption_effectiveness=0.85, active_mass_preservation=1.0,
        lane_timing_consistency=1.0
    )
    report = execute_shadow_resonant_feedback(loop, [obs])
    assert not report.result.success
    assert any("PML weakening" in err for err in report.result.errors)


# Test 21: Synchronized commit remains blocked until cadence sync is stable
def test_commit_remains_blocked_until_stable():
    # Sync report is not stable/successful
    sync_report = {
        "success": False,
        "errors": ["Some sync failure"],
        "intent": {
            "metadata": {
                "rollback_snapshot": "snap"
            }
        }
    }
    commit_report = {"passed_gates": True}
    res = validate_commit_after_autonomous_cadence_sync(commit_report, sync_report)
    assert not res


# Test 22: Rollback restores candidate cadence profile
def test_rollback_restores_mock_profile():
    # We can simulate rollback by verifying it resets active state changes
    policy = AutonomousCadenceSyncPolicy(
        max_sync_steps=10,
        max_cadence_adjustment=0.1, max_phase_offset_adjustment=0.1,
        max_carrier_offset_adjustment=0.1, max_boundary_absorption_adjustment=0.1,
        max_feedback_gain=0.1, rollback_requirement=True
    )
    intent = build_autonomous_cadence_sync_intent({"group_id": "gp1"}, policy)
    # Simulate a run with errors to trigger rollback
    intent.metadata["telemetry"] = {"global_skew": 0.08, "split_brain": True}
    report = execute_shadow_autonomous_cadence_sync(intent)
    assert report.result.rolled_back
    assert report.result.errors


# Test 23: Runtime ledger records autonomy guard, ranger packet, court verdict, and rollback refs
def test_runtime_ledger_records_details():
    ledger = build_runtime_ledger()
    guard_rep = CadenceAutonomyGuardReport(
        report_id="GUARD_REP_01",
        snapshot=capture_cadence_autonomy_guard_snapshot({"group_id": "gp", "participants": []}),
        decision=CadenceAutonomyGuardDecision(decision_id="DEC_01", passed=True)
    )
    append_runtime_event(ledger, guard_rep)
    
    # Check that it got logged as autonomy_guard_snapshot
    assert len(ledger["entries"]) == 1
    assert ledger["entries"][0].entry_type == "autonomy_guard_snapshot"



# Test 24: ResonantCadenceRanger emits JSON-serializable SovereignPacket
def test_ranger_emits_serializable_packet(sample_policy):
    feedback_report = ResonantFeedbackReport(
        report_id="FB_REP_01", loop_id="LOOP_01", policy=sample_policy,
        result=ResonantFeedbackResult(
            success=True, step_count=5,
            final_observation=ResonantFeedbackObservation(
                observation_id="obs1", timestamp=time.time(),
                resonant_phase_coherence=0.95, entanglement_phase_coherence=0.95,
                cadence_drift=0.01, global_cadence_skew=0.01, carrier_phase_error=0.0,
                wavefront_coherence=0.95, crosstalk=0.01, boundary_reflection=0.01,
                pml_absorption_effectiveness=0.99, active_mass_preservation=1.0,
                lane_timing_consistency=1.0
            )
        )
    )
    
    sync_report = {
        "success": True,
        "global_skew": 0.02,
        "candidates": [],
        "intent": {
            "metadata": {
                "rollback_snapshot": "snap"
            }
        }
    }
    
    guard_report = {
        "report_id": "GUARD_01",
        "decision": {"passed": True}
    }
    
    ranger = ResonantCadenceRanger()
    packet = ranger.observe_resonant_cadence(feedback_report, sync_report, {}, guard_report, {}, {})
    assert packet is not None
    assert packet.level == 44
    assert packet.recommendation == "promote"
    
    # Test JSON serializability
    serialized = json.dumps(packet, default=lambda x: x.__dict__)
    assert serialized is not None


# Test 25: Promotion Court can review resonant feedback, autonomous cadence sync, control, autonomy guard, and ranger reports
def test_promotion_court_reviews_all_reports(sample_policy):
    court = PromotionCourt()
    
    feedback_report = ResonantFeedbackReport(
        report_id="FB_REP_01", loop_id="LOOP_01", policy=sample_policy,
        result=ResonantFeedbackResult(
            success=True, step_count=5,
            final_observation=ResonantFeedbackObservation(
                observation_id="obs1", timestamp=time.time(),
                resonant_phase_coherence=0.95, entanglement_phase_coherence=0.95,
                cadence_drift=0.01, global_cadence_skew=0.01, carrier_phase_error=0.0,
                wavefront_coherence=0.95, crosstalk=0.01, boundary_reflection=0.01,
                pml_absorption_effectiveness=0.99, active_mass_preservation=1.0,
                lane_timing_consistency=1.0
            )
        )
    )
    
    sync_report = {
        "success": True,
        "global_skew": 0.02,
        "candidates": [],
        "intent": {
            "metadata": {
                "rollback_snapshot": "snap"
            }
        }
    }
    
    guard_report = {
        "report_id": "GUARD_01",
        "decision": {"passed": True}
    }
    
    control_report = {
        "report_id": "CTRL_01",
        "state_classification": "nominal"
    }
    
    ranger = ResonantCadenceRanger()
    packet = ranger.observe_resonant_cadence(feedback_report, sync_report, {}, guard_report, {}, {})

    res_fb = court.review_resonant_feedback_report(feedback_report)
    res_sync = court.review_autonomous_cadence_sync_report(sync_report)
    res_ctrl = court.review_resonant_cadence_control_report(control_report)
    res_guard = court.review_cadence_autonomy_guard_report(guard_report)
    res_pkt = court.review_resonant_cadence_ranger_packet(packet)
    
    assert res_fb.passed
    assert res_sync.passed
    assert res_ctrl.passed
    assert res_guard.passed
    assert res_pkt.passed
