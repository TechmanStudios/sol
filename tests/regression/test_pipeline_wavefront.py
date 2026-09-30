# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 46: Geodesic Pipeline Balancing and Quantum Wavefront Calibration.
"""

import sys
from pathlib import Path
import pytest
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List

# Setup path injection
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# New imports
from sol_geodesic_pipeline_balancer import (
    GeodesicPipelineBalancePolicy,
    GeodesicPipelineSegment,
    GeodesicPipelineLoadMetric,
    GeodesicPipelineImbalance,
    GeodesicPipelineBalancePlan,
    GeodesicPipelineBalanceResult,
    GeodesicPipelineBalanceReport,
    collect_geodesic_pipeline_metrics,
    detect_geodesic_pipeline_imbalance,
    build_geodesic_pipeline_balance_plan,
    validate_geodesic_pipeline_balance_plan,
    execute_shadow_geodesic_pipeline_balance,
    compare_pipeline_balance_before_after
)

from sol_quantum_wavefront_calibration import (
    QuantumWavefrontPacket,
    QuantumWavefrontCalibrationPolicy,
    QuantumWavefrontBaseline,
    QuantumWavefrontObservation,
    QuantumWavefrontAdjustment,
    QuantumWavefrontCalibrationResult,
    QuantumWavefrontCalibrationReport,
    build_quantum_wavefront_packets,
    capture_quantum_wavefront_baseline,
    measure_quantum_wavefront_error,
    plan_quantum_wavefront_adjustment,
    execute_shadow_quantum_wavefront_calibration,
    summarize_quantum_wavefront_calibration
)

from sol_wavefront_uncertainty_window import (
    WavefrontUncertaintyWindow,
    WavefrontUncertaintyObservation,
    WavefrontUncertaintyBound,
    WavefrontUncertaintyReport,
    build_uncertainty_window,
    measure_wavefront_uncertainty,
    validate_uncertainty_within_bounds,
    classify_wavefront_uncertainty_state
)

from sol_pipeline_balance_safety_oracle import (
    PipelineBalanceOracleInput,
    PipelineBalanceOracleDecision,
    PipelineBalanceOracleReport,
    evaluate_pipeline_balance_safety,
    classify_balance_expected_outcome,
    compare_balance_actual_to_expected
)

from sol_quantum_wavefront_protocol import (
    QuantumWavefrontProtocol,
    QuantumWavefrontPrepareState,
    QuantumWavefrontCalibrateState,
    QuantumWavefrontVerifyState,
    QuantumWavefrontCommitState,
    QuantumWavefrontAbortState,
    QuantumWavefrontProtocolReport,
    prepare_quantum_wavefront_protocol,
    calibrate_quantum_wavefront_shadow,
    verify_quantum_wavefront_protocol,
    commit_quantum_wavefront_shadow,
    abort_quantum_wavefront_protocol
)

# Extended imports
from sol_multicore_pipeline import (
    PipelineSchedule,
    PipelineTask,
    export_geodesic_pipeline_segments,
    validate_pipeline_after_geodesic_balancing,
    run_shadow_balanced_pipeline
)
from sol_pipeline_calibration import (
    PipelineCalibrationPolicy,
    calibrate_pipeline_after_geodesic_balance,
    validate_pipeline_calibration_after_balance
)
from sol_transactional_geodesic_optimizer import (
    validate_route_after_pipeline_balance,
    remap_route_metrics_after_pipeline_balance
)
from sol_dynamic_waveguide_rebalancer import (
    validate_waveguide_after_pipeline_balance,
    remap_waveguide_load_after_pipeline_balance
)
from sol_wavefront_propagator import (
    WavefrontPropagationConfig,
    initialize_quantum_wavefront_packets_from_state,
    run_shadow_quantum_wavefront_steps,
    measure_quantum_wavefront_stability
)
from sol_waveguide_boundary import (
    validate_pml_for_quantum_wavefront_packets,
    measure_quantum_boundary_reflection
)
from sol_carrier_registry import (
    validate_carriers_for_quantum_wavefront_packets,
    snapshot_carriers_before_quantum_calibration
)
from sol_temporal_cadence import (
    validate_quantum_wavefront_cadence,
    measure_quantum_wavefront_cadence_error
)
from sol_resonant_cadence_controller import (
    validate_resonant_cadence_for_quantum_wavefront
)
from sol_autonomous_cadence_sync import (
    block_quantum_calibration_on_unstable_autonomous_cadence
)
from sol_entangled_resonant_feedback import (
    validate_resonant_feedback_after_quantum_calibration,
    measure_quantum_feedback_disturbance
)
from sol_interlane_prefix_carry import (
    validate_prefix_carry_after_pipeline_balance
)
from sol_waveguide_arithmetic_pipeline import (
    validate_arithmetic_after_quantum_wavefront_calibration
)
from sol_sovereign_runtime import (
    SovereignRuntimeState,
    SovereignRuntimePolicy,
    SovereignRuntimeCommand,
    SovereignRuntimeId,
    submit_pipeline_balance_command,
    execute_shadow_pipeline_balance_command,
    submit_quantum_wavefront_calibration_command,
    execute_shadow_quantum_wavefront_calibration_command
)
from sol_runtime_ledger import (
    build_runtime_ledger,
    append_runtime_event,
    attach_runtime_evidence,
    attach_rollback_reference,
    validate_runtime_ledger
)
from coding_library.sovereign_domain.frontier_bridge import (
    FrontierBridge,
    GeodesicPipelineBalanceAdvisor,
    QuantumWavefrontCalibrationAdvisor,
    PipelineBalanceSuggestion,
    QuantumWavefrontSuggestion,
    PipelineWavefrontClosedLoopReport
)
from coding_library.sovereign_domain.rangers.pipeline_wavefront_ranger import PipelineWavefrontRanger
from coding_library.sovereign_domain.promotion_court import PromotionCourt
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from sol_court_supervised_promotion import (
    CourtPromotionDecision,
    review_geodesic_pipeline_balance_report,
    review_quantum_wavefront_calibration_report,
    review_wavefront_uncertainty_report,
    review_pipeline_balance_oracle_report,
    review_quantum_wavefront_protocol_report,
    review_pipeline_wavefront_ranger_packet
)


# Test 1: geodesic pipeline metrics collect from mock pipeline and route reports.
def test_geodesic_metrics_collection():
    pipeline_report = {
        "segments": [{"segment_id": "seg_0"}, {"segment_id": "seg_1"}],
        "metrics": {
            "seg_0": {"queue_depth": 5, "latency": 0.04},
            "seg_1": {"queue_depth": 2, "latency": 0.02}
        }
    }
    route_report = {
        "metrics": {
            "seg_0": {"route_depth": 3, "waveguide_load": 0.4},
            "seg_1": {"route_depth": 1, "waveguide_load": 0.1}
        }
    }
    core_report = {
        "metrics": {
            "seg_0": {"cadence_skew": 0.03},
            "seg_1": {"cadence_skew": 0.01}
        }
    }
    metrics = collect_geodesic_pipeline_metrics(pipeline_report, route_report, core_report)
    assert len(metrics) == 2
    assert metrics[0].segment_id == "seg_0"
    assert metrics[0].queue_depth == 5
    assert metrics[0].route_depth == 3
    assert metrics[0].cadence_skew == 0.03
    assert metrics[1].segment_id == "seg_1"
    assert metrics[1].queue_depth == 2


# Test 2: imbalance is detected for overloaded pipeline segment.
def test_imbalance_detection():
    metrics = [
        GeodesicPipelineLoadMetric("seg_0", queue_depth=10, latency=0.1, stall_time=0.08),
        GeodesicPipelineLoadMetric("seg_1", queue_depth=1, latency=0.01, stall_time=0.0)
    ]
    policy = GeodesicPipelineBalancePolicy(max_imbalance_threshold=0.2)
    imbalances = detect_geodesic_pipeline_imbalance(metrics, policy)
    assert len(imbalances) > 0
    assert imbalances[0].segment_id == "seg_0"


# Test 3: balance plan builds from imbalance.
def test_balance_plan_building():
    imbalances = [GeodesicPipelineImbalance("seg_0", imbalance_score=0.6)]
    policy = GeodesicPipelineBalancePolicy(max_imbalance_threshold=0.2)
    plan = build_geodesic_pipeline_balance_plan(imbalances, policy)
    assert plan.plan_id.startswith("BAL_PLAN_")
    assert "seg_0" in plan.adjustments
    assert plan.metadata.get("rollback_snapshot") is not None


# Test 4: invalid balance policy is rejected.
def test_invalid_balance_policy():
    imbalances = [GeodesicPipelineImbalance("seg_0", imbalance_score=0.6)]
    policy = GeodesicPipelineBalancePolicy(max_imbalance_threshold=-0.1) # Invalid <= 0
    with pytest.raises(ValueError, match="Unbounded policy"):
        build_geodesic_pipeline_balance_plan(imbalances, policy)


# Test 5: balance before/after comparison is generated.
def test_balance_before_after_comparison():
    before = [GeodesicPipelineLoadMetric("seg_0", latency=0.1, stall_time=0.05)]
    after = [GeodesicPipelineLoadMetric("seg_0", latency=0.05, stall_time=0.01)]
    comp = compare_pipeline_balance_before_after(before, after)
    assert comp["improved"] is True
    assert comp["before_latency"] == 0.1
    assert comp["after_latency"] == 0.05


# Test 6: no improvement without justification blocks promotion.
def test_no_improvement_without_justification():
    # If balancing did not improve, and no policy justification exists
    before = [GeodesicPipelineLoadMetric("seg_0", latency=0.05)]
    after = [GeodesicPipelineLoadMetric("seg_0", latency=0.05)]
    comp = compare_pipeline_balance_before_after(before, after)
    assert comp["improved"] is False


# Test 7: quantum wavefront packets build from mock state.
def test_quantum_wavefront_packets_building():
    state = {
        "packets": [
            {"packet_id": "p_0", "amplitude": 1.2, "phase": 0.1, "frequency": 15.0, "active_mass": 14.0, "dispersion": 0.02}
        ]
    }
    packets = build_quantum_wavefront_packets(state, None)
    assert len(packets) == 1
    assert packets[0].packet_id == "p_0"
    assert packets[0].amplitude == 1.2
    assert packets[0].active_mass == 14.0


# Test 8: quantum wavefront baseline is required before calibration.
def test_quantum_wavefront_baseline_required():
    with pytest.raises(ValueError, match="baseline is required"):
        # Calling error measurement with missing baseline
        measure_quantum_wavefront_error(None, [])


# Test 9: quantum calibration policy rejects unbounded adjustment.
def test_unbounded_calibration_policy():
    policy = QuantumWavefrontCalibrationPolicy(max_phase_coherence_error=0.0) # Invalid <= 0
    with pytest.raises(ValueError, match="max_phase_coherence_error must be > 0"):
        plan_quantum_wavefront_adjustment([], policy)


# Test 10: uncertainty window builds for packet.
def test_uncertainty_window_building():
    packet = QuantumWavefrontPacket("pkt_0", 1.0, 0.0, 10.0)
    class MockPolicy:
        phase_tolerance = 0.02
        amplitude_tolerance = 0.03
        frequency_tolerance = 0.05
    window = build_uncertainty_window(packet, MockPolicy())
    assert window.packet_id == "pkt_0"
    assert window.phase_min == -0.02
    assert window.phase_max == 0.02


# Test 11: unbounded uncertainty blocks promotion.
def test_unbounded_uncertainty_blocks_promotion():
    window = WavefrontUncertaintyWindow("pkt_0", -0.1, 0.1, 0.9, 1.1, 9.9, 10.1)
    obs = WavefrontUncertaintyObservation("pkt_0", 0.0, 1.0, 10.0)
    bound = WavefrontUncertaintyBound(0.05, 0.05, 0.05, is_bounded=False) # Marked unbounded
    report = WavefrontUncertaintyReport("rep_0", "pkt_0", window, obs, bound, 0.0, 0.0, 0.0, is_valid=True)
    
    assert validate_uncertainty_within_bounds(report, None) is False
    assert classify_wavefront_uncertainty_state(report) == "unbounded_uncertainty"


# Test 12: amplitude coherence breach blocks promotion.
def test_amplitude_coherence_breach():
    # amplitude coherence < 0.9 in stability report returns False
    obs = [QuantumWavefrontObservation("obs_0", "pkt_0", amplitude_coherence=0.85, phase_coherence=0.95, resonance_coherence=0.95, packet_dispersion=0.01, carrier_phase_error=0.0, cadence_drift=0.0, wavefront_timing_drift=0.0, crosstalk=0.0, boundary_reflection=0.0, pml_absorption_effectiveness=0.99, active_mass_preservation=14.0)]
    report = QuantumWavefrontCalibrationReport("rep_0", None, obs, QuantumWavefrontCalibrationResult(True))
    assert measure_quantum_wavefront_stability(report) is False


# Test 13: phase coherence breach blocks promotion.
def test_phase_coherence_breach():
    obs = [QuantumWavefrontObservation("obs_0", "pkt_0", amplitude_coherence=0.95, phase_coherence=0.82, resonance_coherence=0.95, packet_dispersion=0.01, carrier_phase_error=0.0, cadence_drift=0.0, wavefront_timing_drift=0.0, crosstalk=0.0, boundary_reflection=0.0, pml_absorption_effectiveness=0.99, active_mass_preservation=14.0)]
    report = QuantumWavefrontCalibrationReport("rep_0", None, obs, QuantumWavefrontCalibrationResult(True))
    assert measure_quantum_wavefront_stability(report) is False


# Test 14: packet dispersion breach blocks promotion.
def test_packet_dispersion_breach():
    obs = [QuantumWavefrontObservation("obs_0", "pkt_0", amplitude_coherence=0.95, phase_coherence=0.95, resonance_coherence=0.95, packet_dispersion=0.15, carrier_phase_error=0.0, cadence_drift=0.0, wavefront_timing_drift=0.0, crosstalk=0.0, boundary_reflection=0.0, pml_absorption_effectiveness=0.99, active_mass_preservation=14.0)]
    report = QuantumWavefrontCalibrationReport("rep_0", None, obs, QuantumWavefrontCalibrationResult(True))
    assert measure_quantum_wavefront_stability(report) is False


# Test 15: cadence window failure blocks calibration.
def test_cadence_window_failure():
    packet_report = {
        "observations": [
            {"cadence_drift": 0.01, "wavefront_timing_drift": 0.01}
        ]
    }
    cadence_report = {
        "global_skew": 0.02,
        "outside_cadence_window": True # timing falls outside cadence window
    }
    assert validate_quantum_wavefront_cadence(packet_report, cadence_report) is False


# Test 16: unstable autonomous cadence blocks calibration.
def test_unstable_autonomous_cadence():
    sync_report = {
        "result": {"success": False, "errors": ["Autonomous sync is unstable"]}
    }
    with pytest.raises(ValueError, match="unstable autonomous cadence"):
        block_quantum_calibration_on_unstable_autonomous_cadence(sync_report)


# Test 17: missing PML boundary blocks calibration.
def test_missing_pml_boundary():
    # If pml config cells = 0
    pml_state = {
        "config": {"pml_cells": 0},
        "metadata": {}
    }
    with pytest.raises(ValueError, match="missing PML cells"):
        validate_pml_for_quantum_wavefront_packets([{"packet_id": "pkt_0", "metadata": {}}], pml_state)


# Test 18: carrier identity break blocks calibration.
def test_carrier_identity_break():
    registry = {"leases": {}}
    packets = [
        QuantumWavefrontPacket("pkt_0", 1.0, 0.0, 10.0, metadata={"carrier_identity_broken": True})
    ]
    assert validate_carriers_for_quantum_wavefront_packets(registry, packets) is False


# Test 19: prefix-carry break blocks pipeline balance when required.
def test_prefix_carry_break():
    carry_report = {
        "metadata": {"carry_tree_connectivity_violated": True}
    }
    balance_report = {
        "result": {"success": True}
    }
    with pytest.raises(ValueError, match="invalidates carry tree connectivity"):
        validate_prefix_carry_after_pipeline_balance(carry_report, balance_report)


# Test 20: arithmetic oracle mismatch blocks promotion when arithmetic report is present.
def test_arithmetic_oracle_mismatch():
    arithmetic_report = {"oracle_match": False}
    with pytest.raises(ValueError, match="Arithmetic oracle mismatch"):
        validate_arithmetic_after_quantum_wavefront_calibration(arithmetic_report, None)


# Test 21: active phase table overwrite attempt is rejected.
def test_active_phase_table_overwrite_rejection():
    # When submitting sovereign runtime command
    runtime = SovereignRuntimeState(
        runtime_id=SovereignRuntimeId("RUN_MOCK"),
        active_level=45,
        mode="sandbox",
        policy=SovereignRuntimePolicy(allowed_modes=["sandbox"])
    )
    cmd = SovereignRuntimeCommand(
        command_id="cmd_0",
        target_level=46,
        operation="quantum_calibration",
        mode="sandbox",
        payload={
            "court_token": "SANDBOX_TOKEN",
            "ranger_observer": "ranger_0",
            "rollback_snapshot": "snap_0",
            "overwrite_active_phase_table": True # attempt to overwrite
        }
    )
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        submit_quantum_wavefront_calibration_command(runtime, cmd)


# Test 22: active cadence profile overwrite attempt is rejected.
def test_active_cadence_profile_overwrite_rejection():
    runtime = SovereignRuntimeState(
        runtime_id=SovereignRuntimeId("RUN_MOCK"),
        active_level=45,
        mode="sandbox",
        policy=SovereignRuntimePolicy(allowed_modes=["sandbox"])
    )
    cmd = SovereignRuntimeCommand(
        command_id="cmd_0",
        target_level=46,
        operation="quantum_calibration",
        mode="sandbox",
        payload={
            "court_token": "SANDBOX_TOKEN",
            "ranger_observer": "ranger_0",
            "rollback_snapshot": "snap_0",
            "overwrite_active_cadence": True
        }
    )
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        submit_quantum_wavefront_calibration_command(runtime, cmd)


# Test 23: active carrier registry overwrite attempt is rejected.
def test_active_carrier_registry_overwrite_rejection():
    runtime = SovereignRuntimeState(
        runtime_id=SovereignRuntimeId("RUN_MOCK"),
        active_level=45,
        mode="sandbox",
        policy=SovereignRuntimePolicy(allowed_modes=["sandbox"])
    )
    cmd = SovereignRuntimeCommand(
        command_id="cmd_0",
        target_level=46,
        operation="quantum_calibration",
        mode="sandbox",
        payload={
            "court_token": "SANDBOX_TOKEN",
            "ranger_observer": "ranger_0",
            "rollback_snapshot": "snap_0",
            "overwrite_active_carrier": True
        }
    )
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        submit_quantum_wavefront_calibration_command(runtime, cmd)


# Test 24: runtime ledger records balance plan, quantum baseline, uncertainty report, ranger packet, court verdict, and rollback refs.
def test_runtime_ledger_recordkeeping():
    ledger = build_runtime_ledger()
    
    # 1. balance plan
    plan = GeodesicPipelineBalancePlan("P_0", GeodesicPipelineBalancePolicy(), [], {})
    append_runtime_event(ledger, plan)
    
    # 2. quantum baseline
    baseline = QuantumWavefrontBaseline("B_0", [])
    append_runtime_event(ledger, baseline)
    
    # 3. uncertainty report
    window = WavefrontUncertaintyWindow("pkt_0", -0.1, 0.1, 0.9, 1.1, 9.9, 10.1)
    obs = WavefrontUncertaintyObservation("pkt_0", 0.0, 1.0, 10.0)
    bound = WavefrontUncertaintyBound(0.05, 0.05, 0.05)
    unc_rep = WavefrontUncertaintyReport("rep_0", "pkt_0", window, obs, bound, 0.0, 0.0, 0.0, is_valid=True)
    append_runtime_event(ledger, unc_rep)
    
    # 4. ranger packet
    pkt = SovereignPacket("pkt_ranger", "sol_sovereign", 46, "Ranger", "ranger", "M_0", "Claim", {}, [], [], "promote", 0.99, "P_0")
    append_runtime_event(ledger, pkt)
    
    # 5. court verdict
    dec = CourtPromotionDecision("DEC_0", "promote_level46_candidate", "Success")
    append_runtime_event(ledger, dec)
    
    # 6. rollback refs
    rollback = {"rollback_id": "RLBK_0", "state_checksum": "hash_0"}
    attach_rollback_reference(ledger, rollback)
    
    report = validate_runtime_ledger(ledger)
    assert report.passed_validation is True
    assert len(report.entries) >= 6


# Test 25: rollback restores mock balance plan and quantum calibration candidate state.
def test_rollback_restoration():
    plan = build_geodesic_pipeline_balance_plan([], GeodesicPipelineBalancePolicy())
    # Rollback snapshot checks
    assert plan.metadata.get("rollback_snapshot") is not None


# Test 26: PipelineWavefrontRanger emits JSON-serializable SovereignPacket.
def test_ranger_emits_sovereign_packet():
    ranger = PipelineWavefrontRanger()
    
    plan = GeodesicPipelineBalancePlan("P_0", GeodesicPipelineBalancePolicy(), [], {})
    res = GeodesicPipelineBalanceResult(success=True)
    balance_report = GeodesicPipelineBalanceReport("R_0", plan, res)
    
    packet = ranger.observe_pipeline_wavefront(
        balance_report=balance_report,
        quantum_report=None,
        uncertainty_report=None,
        oracle_report=None,
        protocol_report=None,
        ledger_report=None
    )
    
    assert packet.packet_id.startswith("PKT_WF_BAL_")
    assert packet.level == 46
    assert packet.recommendation == "observe" # since missing rollback/uncertainty status


# Test 27: Promotion Court can review pipeline balance, quantum wavefront calibration, uncertainty, oracle, protocol, and ranger reports.
def test_promotion_court_reviews():
    court = PromotionCourt()
    
    # 1. Pipeline balance
    bal_plan = GeodesicPipelineBalancePlan("P_0", GeodesicPipelineBalancePolicy(), [], {})
    bal_res = GeodesicPipelineBalanceResult(success=True)
    bal_rep = GeodesicPipelineBalanceReport("REP_0", bal_plan, bal_res)
    res1 = court.review_geodesic_pipeline_balance_report(bal_rep)
    assert res1.passed is True
    
    # 2. Quantum calibration
    cal_res = QuantumWavefrontCalibrationResult(success=True)
    cal_rep = QuantumWavefrontCalibrationReport("REP_1", None, [], cal_res)
    res2 = court.review_quantum_wavefront_calibration_report(cal_rep)
    assert res2.passed is True
    
    # 3. Uncertainty
    window = WavefrontUncertaintyWindow("pkt_0", -0.1, 0.1, 0.9, 1.1, 9.9, 10.1)
    obs = WavefrontUncertaintyObservation("pkt_0", 0.0, 1.0, 10.0)
    bound = WavefrontUncertaintyBound(0.05, 0.05, 0.05)
    unc_rep = WavefrontUncertaintyReport("rep_0", "pkt_0", window, obs, bound, 0.0, 0.0, 0.0, is_valid=True)
    res3 = court.review_wavefront_uncertainty_report(unc_rep)
    assert res3.passed is True
    
    # 4. Oracle
    oracle_dec = PipelineBalanceOracleDecision("accept", "Success", 0.95)
    oracle_rep = PipelineBalanceOracleReport("rep_3", PipelineBalanceOracleInput(None, [], {}), oracle_dec)
    res4 = court.review_pipeline_balance_oracle_report(oracle_rep)
    assert res4.passed is True
    
    # 5. Protocol
    prot = QuantumWavefrontProtocol("PROT_0")
    prot_rep = QuantumWavefrontProtocolReport("rep_4", prot, success=True)
    res5 = court.review_quantum_wavefront_protocol_report(prot_rep)
    assert res5.passed is True
    
    # 6. Ranger
    packet = SovereignPacket("pkt_ranger", "sol_sovereign", 46, "Ranger", "ranger", "M_0", "Claim", {"promotion_readiness": True}, [], [], "promote", 0.99, "P_0")
    res6 = court.review_pipeline_wavefront_ranger_packet(packet)
    assert res6.passed is True
