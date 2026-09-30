# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 47: Pipeline Wavefront Fault Injection and Quantum Calibration Stability Audit.
"""

import sys
import json
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

from sol_pipeline_wavefront_fault_matrix import (
    PipelineWavefrontFaultCase,
    PipelineWavefrontFaultInjection,
    PipelineWavefrontFaultScenario,
    PipelineWavefrontFaultResult,
    PipelineWavefrontFaultMatrix,
    PipelineWavefrontFaultMatrixReport,
    build_pipeline_wavefront_fault_matrix,
    inject_pipeline_wavefront_fault,
    run_shadow_pipeline_wavefront_fault_case,
    run_shadow_pipeline_wavefront_fault_matrix,
    summarize_pipeline_wavefront_fault_matrix
)

from sol_quantum_calibration_faults import (
    QuantumCalibrationFault,
    QuantumCalibrationFaultInjection,
    QuantumCalibrationFaultResult,
    QuantumCalibrationFaultAudit,
    QuantumCalibrationFaultReport,
    build_quantum_calibration_faults,
    inject_quantum_calibration_fault,
    run_shadow_quantum_calibration_fault,
    summarize_quantum_calibration_faults
)

from sol_pipeline_balance_faults import (
    PipelineBalanceFault,
    PipelineBalanceFaultInjection,
    PipelineBalanceFaultReport,
    inject_false_pipeline_balance_improvement,
    inject_core_queue_depth_spike,
    inject_stage_latency_spike,
    inject_cross_core_stall_spike,
    inject_backpressure_breach,
    validate_balance_fault_blocks_promotion
)

from sol_uncertainty_fault_audit import (
    UncertaintyFaultCase,
    UncertaintyFaultResult,
    UncertaintyFaultAuditReport,
    inject_unbounded_uncertainty_window,
    inject_dispersion_breach,
    inject_invalid_uncertainty_bound,
    validate_uncertainty_fault_response
)

from sol_pipeline_wavefront_rollback_proof import (
    PipelineWavefrontRollbackSnapshot,
    PipelineWavefrontRollbackCase,
    PipelineWavefrontRollbackResult,
    PipelineWavefrontRollbackProofReport,
    capture_pipeline_wavefront_rollback_snapshot,
    inject_fault_then_rollback_pipeline_wavefront,
    verify_pipeline_wavefront_rollback,
    run_pipeline_wavefront_rollback_proof
)

from sol_pipeline_wavefront_safety_oracle import (
    PipelineWavefrontSafetyOracleInput,
    PipelineWavefrontSafetyOracleDecision,
    PipelineWavefrontSafetyOracleReport,
    evaluate_pipeline_wavefront_safety,
    classify_pipeline_wavefront_expected_outcome,
    compare_pipeline_wavefront_actual_to_expected
)

from sol_geodesic_pipeline_balancer import (
    GeodesicPipelineBalanceReport,
    GeodesicPipelineBalanceResult,
    GeodesicPipelineBalancePlan,
    export_pipeline_balance_fault_targets,
    validate_pipeline_balance_against_fault_matrix
)
from sol_quantum_wavefront_calibration import (
    QuantumWavefrontCalibrationReport,
    QuantumWavefrontCalibrationResult,
    export_quantum_wavefront_fault_targets,
    validate_quantum_fault_response,
    measure_quantum_wavefront_error
)
from sol_wavefront_uncertainty_window import (
    WavefrontUncertaintyReport,
    WavefrontUncertaintyBound,
    export_uncertainty_fault_targets,
    validate_uncertainty_audit_response
)
from sol_pipeline_balance_safety_oracle import (
    compare_fault_expected_to_actual_outcome,
    validate_pipeline_balance_oracle_regression
)
from sol_waveguide_boundary import (
    inject_quantum_wavefront_missing_pml,
    inject_quantum_wavefront_pml_weakening,
    inject_quantum_boundary_reflection_breach
)
from sol_carrier_registry import (
    inject_quantum_carrier_binding_break,
    inject_quantum_quadrature_pair_break,
    inject_quantum_carrier_lease_failure
)
from sol_temporal_cadence import (
    inject_quantum_cadence_window_failure,
    inject_quantum_global_cadence_skew
)
from sol_interlane_prefix_carry import (
    inject_quantum_prefix_carry_bridge_break,
    validate_quantum_prefix_fault_blocks_promotion
)
from sol_waveguide_arithmetic_pipeline import (
    inject_quantum_arithmetic_oracle_mismatch
)
from sol_runtime_ledger import (
    inject_missing_balance_plan_ledger_entry,
    inject_missing_quantum_baseline_ledger_entry,
    inject_missing_ranger_packet_ledger_entry,
    inject_missing_court_verdict_ledger_entry,
    validate_ledger_fault_blocks_promotion,
    build_runtime_ledger
)
from coding_library.sovereign_domain.frontier_bridge import (
    PipelineWavefrontFaultAdvisor,
    PipelineWavefrontFaultSuggestion,
    PipelineWavefrontFaultResponsePolicy,
    PipelineWavefrontFaultResponseReport
)
from coding_library.sovereign_domain.rangers.pipeline_wavefront_fault_ranger import (
    PipelineWavefrontFaultRanger
)
from coding_library.sovereign_domain.promotion_court import (
    PromotionCourt,
    PromotionGateResult
)
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from sol_court_supervised_promotion import (
    CourtPromotionDecision,
    review_pipeline_wavefront_fault_matrix_report,
    review_quantum_calibration_fault_report,
    review_pipeline_balance_fault_report,
    review_uncertainty_fault_audit_report,
    review_pipeline_wavefront_rollback_proof_report,
    review_pipeline_wavefront_safety_oracle_report,
    review_pipeline_wavefront_fault_ranger_packet
)


def test_pipeline_wavefront_fault_matrix_builds():
    matrix = build_pipeline_wavefront_fault_matrix()
    assert matrix is not None
    assert len(matrix.cases) == 33
    
    categories = [case.category for case in matrix.cases]
    required = [
        "missing pipeline metrics", "invalid balance plan", "false balance improvement",
        "increased route depth without justification", "increased core queue depth",
        "increased stage latency", "cross-core stall spike", "backpressure spike",
        "reduction wait spike", "consensus wait spike", "lock wait spike",
        "cadence skew spike", "wavefront timing drift", "missing quantum wavefront baseline",
        "amplitude coherence collapse", "phase coherence collapse", "resonance coherence collapse",
        "packet dispersion breach", "unbounded uncertainty window", "missing PML boundary",
        "weakened PML absorption", "carrier binding break", "quadrature pairing break",
        "prefix-carry bridge break", "arithmetic oracle mismatch", "tensor oracle mismatch",
        "runtime ledger missing event", "rollback reference missing", "state checksum mismatch",
        "active phase-table overwrite attempt", "active cadence-profile overwrite attempt",
        "active carrier-registry overwrite attempt", "production/default mutation attempt"
    ]
    for r in required:
        assert r in categories


def test_quantum_calibration_faults_builds():
    faults = build_quantum_calibration_faults()
    assert len(faults) == 12
    categories = [f.category for f in faults]
    required = [
        "amplitude spike", "phase drift spike", "resonance coherence loss",
        "packet dispersion overflow", "uncertainty bound failure", "carrier phase error spike",
        "cadence drift spike", "PML weakening", "crosstalk spike",
        "boundary reflection breach", "oracle mismatch", "rollback after calibration failure"
    ]
    for r in required:
        assert r in categories


def test_pipeline_balance_fault_cases_build():
    fault = PipelineBalanceFault("f_0", "latency_spike", magnitude=5.0)
    injection = PipelineBalanceFaultInjection("inj_0", fault)
    report = PipelineBalanceFaultReport("rpt_0", fault, success=False, blocks_promotion=True)
    
    assert fault.magnitude == 5.0
    assert injection.fault.category == "latency_spike"
    assert validate_balance_fault_blocks_promotion(report) is True


def test_uncertainty_fault_audit_builds():
    case = UncertaintyFaultCase("c_0", "dispersion_breach", "Dispersion breach description", injected_value=0.5)
    result = UncertaintyFaultResult("res_0", "c_0", blocks_promotion=True)
    report = UncertaintyFaultAuditReport("rpt_0", [result], passed_audit=False)
    
    assert case.injected_value == 0.5
    assert validate_uncertainty_fault_response(report) is True


def test_missing_pipeline_metrics_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "missing pipeline metrics"][0]
    
    # Run the shadow case validation
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_invalid_balance_plan_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "invalid balance plan"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_false_balance_improvement_rejected():
    # Mock balance report
    @dataclass
    class MockResult:
        success: bool = True
        metadata: Dict[str, Any] = field(default_factory=dict)
        
    @dataclass
    class MockReport:
        report_id: str = "RPT_BAL_0"
        result: MockResult = field(default_factory=MockResult)

    report = MockReport()
    mutated = inject_false_pipeline_balance_improvement(report)
    assert mutated.result.metadata.get("false_improvement") is True
    
    # Evaluate with safety oracle expected outcome
    outcome = classify_pipeline_wavefront_expected_outcome(
        PipelineWavefrontFaultCase("c_false", "false balance improvement", "")
    )
    assert outcome == "reject_candidate"


def test_increased_route_depth_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "increased route depth without justification"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "hold_pipeline_balance"


def test_stage_latency_spike_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "increased stage latency"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "hold_pipeline_balance"


def test_cross_core_stall_spike_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "cross-core stall spike"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "hold_pipeline_balance"


def test_backpressure_spike_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "backpressure spike"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "hold_pipeline_balance"


def test_missing_quantum_wavefront_baseline_blocks_calibration():
    # If baseline is missing, error measurement should raise ValueError
    with pytest.raises(ValueError, match="baseline is required"):
        measure_quantum_wavefront_error(None, [])


def test_amplitude_coherence_collapse_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "amplitude coherence collapse"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "rollback_wavefront_calibration"


def test_phase_coherence_collapse_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "phase coherence collapse"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "rollback_wavefront_calibration"


def test_resonance_coherence_collapse_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "resonance coherence collapse"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "rollback_wavefront_calibration"


def test_packet_dispersion_breach_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "packet dispersion breach"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "quarantine_wavefront_packet"


def test_unbounded_uncertainty_window_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "unbounded uncertainty window"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_missing_pml_boundary_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "missing PML boundary"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "quarantine_pipeline_segment"


def test_weakened_pml_absorption_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "weakened PML absorption"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "quarantine_pipeline_segment"


def test_carrier_binding_break_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "carrier binding break"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_quadrature_pairing_break_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "quadrature pairing break"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_cadence_skew_spike_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "cadence skew spike"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "hold_pipeline_balance"


def test_prefix_carry_bridge_break_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "prefix-carry bridge break"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_arithmetic_oracle_mismatch_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "arithmetic oracle mismatch"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_tensor_oracle_mismatch_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "tensor oracle mismatch"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_missing_runtime_ledger_event_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "runtime ledger missing event"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_missing_rollback_reference_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "rollback reference missing"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_state_checksum_mismatch_blocks_promotion():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "state checksum mismatch"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "reject_candidate"


def test_active_phase_table_overwrite_rejected():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "active phase-table overwrite attempt"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "quarantine_core"


def test_active_cadence_profile_overwrite_rejected():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "active cadence-profile overwrite attempt"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "quarantine_core"


def test_active_carrier_registry_overwrite_rejected():
    matrix = build_pipeline_wavefront_fault_matrix()
    case = [c for c in matrix.cases if c.category == "active carrier-registry overwrite attempt"][0]
    res = run_shadow_pipeline_wavefront_fault_case(case)
    assert res.success is True
    assert res.actual_outcome == "quarantine_core"


def test_rollback_restores_mock_state():
    balance_plan = {"plan_id": "BAL_PLAN_TEST", "adjustments": {}}
    baseline = [{"packet_id": "pkt_0", "amplitude": 1.0}]
    
    snapshot = capture_pipeline_wavefront_rollback_snapshot(
        balance_plan=balance_plan,
        wavefront_packets=baseline,
        cadence_profile={"profile_id": "CAD_TEST"},
        carrier_registry={"registry_id": "REG_TEST"},
        pml_state={"pml_id": "PML_TEST"},
        prefix_carry_bindings={"binding_id": "BIND_TEST"}
    )
    
    assert snapshot.balance_plan == balance_plan
    assert snapshot.wavefront_packets == baseline
    
    case = PipelineWavefrontRollbackCase(
        case_id="RLBK_0",
        description="Rollback test case",
        fault_case=None,
        snapshot=snapshot
    )
    
    restored = inject_fault_then_rollback_pipeline_wavefront(case, snapshot)
    assert verify_pipeline_wavefront_rollback(snapshot, restored) is True
    
    proof_report = run_pipeline_wavefront_rollback_proof([case])
    assert proof_report.passed_proof is True


def test_safety_oracle_expected_matches_actual():
    case = PipelineWavefrontFaultCase("c_test", "amplitude coherence collapse", "", injected_value=0.0)
    oracle_input = PipelineWavefrontSafetyOracleInput(case, None)
    
    report = evaluate_pipeline_wavefront_safety(oracle_input)
    assert report.decision.outcome == "rollback_wavefront_calibration"
    assert compare_pipeline_wavefront_actual_to_expected("rollback_wavefront_calibration", report.decision.outcome) is True


def test_fault_ranger_packet_serializable():
    ranger = PipelineWavefrontFaultRanger()
    
    # Mock reports
    matrix_report = PipelineWavefrontFaultMatrixReport("RPT_0", "MTX_0", [], passed_audit=True)
    quantum_report = QuantumCalibrationFaultReport("RPT_1", "AUD_1", [], passed_audit=True)
    balance_report = PipelineBalanceFaultReport("RPT_2", PipelineBalanceFault("f_0", "latency"), success=True)
    uncertainty_report = UncertaintyFaultAuditReport("RPT_3", [], passed_audit=True)
    rollback_report = PipelineWavefrontRollbackProofReport("RPT_4", [], passed_proof=True)
    oracle_report = PipelineWavefrontSafetyOracleReport(
        "RPT_5",
        PipelineWavefrontSafetyOracleInput(None, None),
        PipelineWavefrontSafetyOracleDecision("accept_shadow", "Acceptable", 1.0)
    )
    
    packet = ranger.observe_faults(
        fault_matrix_report=matrix_report,
        quantum_fault_report=quantum_report,
        balance_fault_report=balance_report,
        uncertainty_audit_report=uncertainty_report,
        rollback_proof_report=rollback_report,
        oracle_report=oracle_report
    )
    
    assert isinstance(packet, SovereignPacket)
    assert packet.recommendation == "promote"
    
    # Verify serializability
    serialized = json.dumps({
        "packet_id": packet.packet_id,
        "domain": packet.domain,
        "level": packet.level,
        "actor": packet.actor,
        "evidence": packet.evidence,
        "recommendation": packet.recommendation
    })
    assert serialized is not None


def test_court_reviews():
    court = PromotionCourt()
    
    # Mock report objects
    matrix_report = PipelineWavefrontFaultMatrixReport("RPT_0", "MTX_0", [], passed_audit=True)
    quantum_report = QuantumCalibrationFaultReport("RPT_1", "AUD_1", [], passed_audit=True)
    balance_report = PipelineBalanceFaultReport("RPT_2", PipelineBalanceFault("f_0", "latency"), success=True, blocks_promotion=False)
    uncertainty_report = UncertaintyFaultAuditReport("RPT_3", [], passed_audit=True)
    rollback_report = PipelineWavefrontRollbackProofReport("RPT_4", [], passed_proof=True)
    oracle_report = PipelineWavefrontSafetyOracleReport(
        "RPT_5",
        PipelineWavefrontSafetyOracleInput(None, None),
        PipelineWavefrontSafetyOracleDecision("accept_shadow", "Acceptable", 1.0)
    )
    ranger_packet = PipelineWavefrontFaultRanger().observe_faults(
        fault_matrix_report=matrix_report,
        quantum_fault_report=quantum_report,
        balance_fault_report=balance_report,
        uncertainty_audit_report=uncertainty_report,
        rollback_proof_report=rollback_report,
        oracle_report=oracle_report
    )
    
    res0 = court.review_pipeline_wavefront_fault_matrix_report(matrix_report)
    assert res0.passed is True
    assert res0.decision == "accept_shadow_pipeline_wavefront_fault_matrix"
    
    res1 = court.review_quantum_calibration_fault_report(quantum_report)
    assert res1.passed is True
    assert res1.decision == "accept_shadow_pipeline_wavefront_fault_matrix"
    
    res2 = court.review_pipeline_balance_fault_report(balance_report)
    assert res2.passed is True
    assert res2.decision == "accept_shadow_pipeline_wavefront_fault_matrix"
    
    res3 = court.review_uncertainty_fault_audit_report(uncertainty_report)
    assert res3.passed is True
    assert res3.decision == "accept_shadow_pipeline_wavefront_fault_matrix"
    
    res4 = court.review_pipeline_wavefront_rollback_proof_report(rollback_report)
    assert res4.passed is True
    assert res4.decision == "accept_shadow_pipeline_wavefront_fault_matrix"
    
    res5 = court.review_pipeline_wavefront_safety_oracle_report(oracle_report)
    assert res5.passed is True
    assert res5.decision == "accept_shadow_pipeline_wavefront_fault_matrix"
    
    res6 = court.review_pipeline_wavefront_fault_ranger_packet(ranger_packet)
    assert res6.passed is True
    assert res6.decision == "promote_level47_candidate"
