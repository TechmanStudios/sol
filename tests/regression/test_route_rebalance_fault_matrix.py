# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 42: Route Rebalance Fault Injection and Optimization Regression Matrix.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
import pytest
import json
import uuid
from typing import Dict, Any, List

# Setup path injection to guarantee local tools importing
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))


# Core dataclasses and functions from Phase 42
from sol_route_rebalance_fault_matrix import (
    RouteRebalanceFaultCase,
    RouteRebalanceFaultInjection,
    RouteRebalanceFaultScenario,
    RouteRebalanceFaultResult,
    RouteRebalanceFaultMatrix,
    RouteRebalanceFaultMatrixReport,
    build_route_rebalance_fault_matrix,
    inject_route_rebalance_fault,
    run_shadow_route_rebalance_fault_case,
    run_shadow_route_rebalance_fault_matrix,
    summarize_route_rebalance_fault_matrix
)
from sol_optimization_regression_matrix import (
    OptimizationRegressionCase,
    OptimizationRegressionBaseline,
    OptimizationRegressionResult,
    OptimizationRegressionMatrix,
    OptimizationRegressionReport,
    build_optimization_regression_matrix,
    capture_optimization_baseline,
    run_shadow_optimization_regression_case,
    run_shadow_optimization_regression_matrix,
    summarize_optimization_regressions
)
from sol_route_cost_faults import (
    RouteCostFault,
    RouteCostFaultInjection,
    RouteCostRegressionReport,
    inject_false_route_cost_improvement,
    inject_rollback_complexity_underestimate,
    inject_cadence_risk_underestimate,
    inject_crosstalk_risk_underestimate,
    validate_cost_model_rejects_faulty_improvement
)
from sol_waveguide_rebalance_faults import (
    WaveguideRebalanceFault,
    WaveguideFaultInjectionResult,
    WaveguideFaultAuditReport,
    inject_missing_pml_coverage,
    inject_carrier_identity_break,
    inject_quadrature_pair_break,
    inject_lane_isolation_breach,
    inject_prefix_carry_bridge_break,
    inject_boundary_reflection_breach
)
from sol_route_rebalance_rollback_proof import (
    RouteRebalanceRollbackSnapshot,
    RouteRebalanceRollbackCase,
    RouteRebalanceRollbackResult,
    RouteRebalanceRollbackProofReport,
    capture_route_rebalance_rollback_snapshot,
    inject_fault_then_rollback_route_rebalance,
    verify_route_rebalance_rollback,
    run_route_rebalance_rollback_proof
)
from sol_route_rebalance_protocol import (
    RouteRebalanceProtocol,
    prepare_route_rebalance,
    verify_route_rebalance,
    commit_shadow_route_rebalance,
    abort_route_rebalance
)
from sol_transactional_geodesic_optimizer import (
    TransactionalGeodesicRoute,
    TransactionalRouteCandidate,
    TransactionalRouteOptimizationIntent,
    TransactionalRouteOptimizationPlan,
    export_route_optimization_fault_targets,
    validate_route_optimization_against_fault_matrix
)
from sol_dynamic_waveguide_rebalancer import (
    WaveguideRebalanceCandidate,
    WaveguideRebalancePlan,
    WaveguideRebalanceIntent,
    export_waveguide_rebalance_fault_targets,
    validate_waveguide_rebalance_fault_response
)
from sol_geodesic_route_cost_model import (
    validate_cost_improvement_not_false_positive,
    validate_risk_not_underestimated
)
from sol_waveguide_rebalance_safety_oracle import (
    compare_fault_expected_to_actual_outcome,
    validate_safety_oracle_regression
)
from sol_global_lock_boundary import (
    inject_optimized_route_lock_boundary_violation,
    inject_rebalance_lock_boundary_violation
)
from sol_temporal_cadence import (
    inject_optimized_route_cadence_failure,
    inject_rebalance_cadence_skew
)
from sol_waveguide_boundary import (
    inject_rebalanced_waveguide_missing_pml,
    inject_rebalanced_waveguide_reflection_breach
)
from sol_carrier_registry import (
    inject_waveguide_rebalance_carrier_alias
)
from sol_pdm_carrier_relocation import (
    inject_rebalance_carrier_lease_failure,
    inject_rebalance_quadrature_pair_break
)
from sol_interlane_prefix_carry import (
    inject_prefix_carry_bridge_break,
    validate_prefix_carry_fault_blocks_rebalance
)
from sol_waveguide_arithmetic_pipeline import (
    inject_arithmetic_oracle_mismatch
)
from coding_library.sovereign_domain.frontier_bridge import (
    RouteRebalanceFaultAdvisor,
    RouteRebalanceFaultSuggestion,
    RouteRebalanceFaultResponsePolicy,
    RouteRebalanceFaultResponseReport
)
from coding_library.sovereign_domain.rangers.route_fault_ranger import RouteFaultRanger
from coding_library.sovereign_domain.promotion_court import PromotionCourt
from coding_library.sovereign_domain.evidence_packet import SovereignPacket


def test_fault_matrix_builds():
    """Verify that route rebalance fault matrix builds with all 33 required categories."""
    matrix = build_route_rebalance_fault_matrix()
    assert isinstance(matrix, RouteRebalanceFaultMatrix)
    assert len(matrix.scenarios) == 1
    
    cases = matrix.scenarios[0].cases
    assert len(cases) == 33
    
    categories = [c.category for c in cases]
    required_categories = [
        "transaction boundary break",
        "atomic commit boundary break",
        "missing rollback reference",
        "corrupted rollback reference",
        "state hash mismatch",
        "route state hash mismatch",
        "local quorum failure",
        "global quorum failure",
        "sequencer quorum failure",
        "lock boundary violation",
        "cross-manifold deadlock",
        "cadence window failure",
        "global cadence skew spike",
        "wavefront coherence collapse",
        "crosstalk spike",
        "boundary reflection breach",
        "missing PML boundary",
        "weakened PML boundary",
        "carrier identity break",
        "quadrature pairing break",
        "carrier lease failure",
        "lane isolation breach",
        "prefix-carry bridge break",
        "arithmetic oracle mismatch",
        "tensor binding break",
        "reduction tree break",
        "cost model false improvement",
        "route risk underestimation",
        "safety oracle mismatch",
        "active phase-table overwrite attempt",
        "active cadence-profile overwrite attempt",
        "active carrier-registry overwrite attempt",
        "production/default route mutation attempt"
    ]
    for req in required_categories:
        assert req in categories, f"Missing required fault category: {req}"


def test_optimization_regression_matrix_builds():
    """Verify that optimization regression matrix builds with all required cases."""
    matrix = build_optimization_regression_matrix()
    assert isinstance(matrix, OptimizationRegressionMatrix)
    assert len(matrix.cases) == 9
    
    categories = [c.category for c in matrix.cases]
    required = [
        "risk increase",
        "transaction boundaries",
        "rollback references",
        "PML coverage",
        "carrier identity",
        "prefix-carry paths",
        "false speedups",
        "safety oracle outcomes",
        "table overwrites"
    ]
    for r in required:
        assert r in categories


def test_rollback_proof_matrix_builds():
    """Verify that rollback proof matrix builds with required cases."""
    cases = [
        RouteRebalanceRollbackCase("C1", "route plan", "Verify route plan restored"),
        RouteRebalanceRollbackCase("C2", "waveguide plan", "Verify waveguide plan restored")
    ]
    report = run_route_rebalance_rollback_proof(cases)
    assert isinstance(report, RouteRebalanceRollbackProofReport)
    assert report.success is True
    assert len(report.results) == 2


def test_transaction_boundary_break_blocks_promotion():
    """Verify that transaction boundary break blocks route optimization."""
    case = RouteRebalanceFaultCase("C_TBB", "transaction boundary break", "break transaction", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"
    assert result.matched_expected is True


def test_atomic_commit_boundary_break_blocks_promotion():
    """Verify that atomic commit boundary break blocks route optimization."""
    case = RouteRebalanceFaultCase("C_ABB", "atomic commit boundary break", "break atomic commit", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_missing_rollback_reference_blocks_promotion():
    """Verify that missing rollback reference blocks promotion."""
    case = RouteRebalanceFaultCase("C_MRR", "missing rollback reference", "missing snap", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_corrupted_rollback_reference_blocks_promotion():
    """Verify that corrupted rollback reference blocks promotion."""
    case = RouteRebalanceFaultCase("C_CRR", "corrupted rollback reference", "corrupt snap", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_state_hash_mismatch_blocks_promotion():
    """Verify that state hash mismatch blocks route optimization."""
    case = RouteRebalanceFaultCase("C_SHM", "state hash mismatch", "mismatch hash", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_local_quorum_failure_blocks_promotion():
    """Verify that local quorum failure blocks route optimization."""
    case = RouteRebalanceFaultCase("C_LQF", "local quorum failure", "local quorum", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_global_quorum_failure_blocks_promotion():
    """Verify that global quorum failure blocks route optimization."""
    case = RouteRebalanceFaultCase("C_GQF", "global quorum failure", "global quorum", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_sequencer_quorum_failure_blocks_promotion():
    """Verify that sequencer quorum failure blocks route optimization when required."""
    case = RouteRebalanceFaultCase("C_SQF", "sequencer quorum failure", "sequencer quorum", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_lock_boundary_violation_blocks_promotion():
    """Verify that lock boundary violation blocks route optimization."""
    case = RouteRebalanceFaultCase("C_LBV", "lock boundary violation", "lock breach", True, "request_lock_boundary_review")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "request_lock_boundary_review"


def test_cross_manifold_deadlock_blocks_promotion():
    """Verify that cross-manifold deadlock blocks route optimization."""
    case = RouteRebalanceFaultCase("C_CMD", "cross-manifold deadlock", "deadlock risk", True, "request_lock_boundary_review")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "request_lock_boundary_review"


def test_cadence_window_failure_blocks_promotion():
    """Verify that cadence window failure blocks route optimization."""
    case = RouteRebalanceFaultCase("C_CWF", "cadence window failure", "outside window", True, "request_cadence_recalibration")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "request_cadence_recalibration"


def test_global_cadence_skew_blocks_promotion():
    """Verify that global cadence skew blocks route optimization."""
    case = RouteRebalanceFaultCase("C_GCS", "global cadence skew spike", "skew spike", True, "request_cadence_recalibration")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "request_cadence_recalibration"


def test_wavefront_coherence_collapse_blocks_promotion():
    """Verify that wavefront coherence collapse blocks rebalance."""
    case = RouteRebalanceFaultCase("C_WCC", "wavefront coherence collapse", "coherence collapse", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_crosstalk_spike_blocks_promotion():
    """Verify that crosstalk spike blocks rebalance."""
    case = RouteRebalanceFaultCase("C_CTS", "crosstalk spike", "crosstalk", True, "quarantine_waveguide_segment")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "quarantine_waveguide_segment"


def test_boundary_reflection_breach_blocks_promotion():
    """Verify that boundary reflection breach blocks rebalance."""
    case = RouteRebalanceFaultCase("C_BRB", "boundary reflection breach", "reflection breach", True, "quarantine_route")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "quarantine_route"


def test_missing_pml_boundary_blocks_promotion():
    """Verify that missing PML boundary blocks rebalance."""
    case = RouteRebalanceFaultCase("C_MPB", "missing PML boundary", "missing pml", True, "quarantine_waveguide_segment")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "quarantine_waveguide_segment"


def test_weakened_pml_boundary_blocks_promotion():
    """Verify that weakened PML boundary blocks rebalance."""
    case = RouteRebalanceFaultCase("C_WPB", "weakened PML boundary", "weakened pml", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_carrier_identity_break_blocks_promotion():
    """Verify that carrier identity break blocks rebalance."""
    case = RouteRebalanceFaultCase("C_CIB", "carrier identity break", "break identity", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_quadrature_pair_break_blocks_promotion():
    """Verify that quadrature pair break blocks rebalance."""
    case = RouteRebalanceFaultCase("C_QPB", "quadrature pairing break", "break pairings", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_carrier_lease_failure_blocks_promotion():
    """Verify that carrier lease failure blocks rebalance."""
    case = RouteRebalanceFaultCase("C_CLF", "carrier lease failure", "lease failure", True, "quarantine_carrier")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "quarantine_carrier"


def test_lane_isolation_breach_blocks_promotion():
    """Verify that lane isolation breach blocks rebalance."""
    case = RouteRebalanceFaultCase("C_LIB", "lane isolation breach", "isolation breach", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_prefix_carry_bridge_break_blocks_promotion():
    """Verify that prefix-carry bridge break blocks rebalance."""
    case = RouteRebalanceFaultCase("C_PCB", "prefix-carry bridge break", "carry break", True, "quarantine_manifold")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "quarantine_manifold"


def test_arithmetic_oracle_mismatch_blocks_promotion():
    """Verify that arithmetic oracle mismatch blocks rebalance."""
    case = RouteRebalanceFaultCase("C_AOM", "arithmetic oracle mismatch", "oracle mismatch", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_tensor_binding_break_blocks_promotion():
    """Verify that tensor binding break blocks rebalance when tensor plan is present."""
    case = RouteRebalanceFaultCase("C_TBB2", "tensor binding break", "tensor break", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_reduction_tree_break_blocks_promotion():
    """Verify that reduction tree break blocks rebalance when reduction tree is present."""
    case = RouteRebalanceFaultCase("C_RTB", "reduction tree break", "reduction break", True, "reject_route_candidate")
    result = run_shadow_route_rebalance_fault_case(case)
    assert result.success is True
    assert result.actual_outcome == "reject_route_candidate"


def test_false_cost_improvement_rejected():
    """Verify that false cost improvement is rejected."""
    @dataclass
    class MockCost:
        total_cost: float = 100.0
        
    est = MockCost()
    inject_false_route_cost_improvement(est)
    assert getattr(est, "false_improvement") is True
    assert validate_cost_model_rejects_faulty_improvement(None, est) is True


def test_risk_underestimation_rejected():
    """Verify that risk underestimation is rejected."""
    @dataclass
    class MockScore:
        passed_policy_bounds: bool = True
        risk_underestimated: bool = True
        
    score = MockScore()
    assert validate_risk_not_underestimated(score) is False


def test_safety_oracle_expectations():
    """Verify that safety oracle expected outcomes match actual outcomes."""
    case = RouteRebalanceFaultCase("C1", "test", "test", None, "reject_route_candidate")
    assert compare_fault_expected_to_actual_outcome(case, "reject_route_candidate") is True
    assert compare_fault_expected_to_actual_outcome(case, "observe") is False


def test_rollback_restores_all_structures():
    """Verify that rollback restores all required structures."""
    snapshot = capture_route_rebalance_rollback_snapshot(None, None)
    case = RouteRebalanceRollbackCase("RC1", "all", "test restore")
    before, after = inject_fault_then_rollback_route_rebalance(case, snapshot)
    
    assert before.active_tables_overwritten is True
    assert before.candidate_phase_tables["table_1"] == "corrupted"
    
    assert verify_route_rebalance_rollback(before, after) is True
    assert after.active_tables_overwritten is False
    assert after.candidate_phase_tables["table_1"] == "calibrated"


def test_active_overwrites_rejected():
    """Verify that active phase table, cadence profile, and carrier registry overwrites are rejected."""
    case1 = RouteRebalanceFaultCase("C_AP", "active phase-table overwrite attempt", "overwrite phase", True, "restore_candidate_tables")
    result1 = run_shadow_route_rebalance_fault_case(case1)
    assert result1.success is True
    assert result1.actual_outcome == "restore_candidate_tables"

    case2 = RouteRebalanceFaultCase("C_AC", "active cadence-profile overwrite attempt", "overwrite cadence", True, "restore_candidate_tables")
    result2 = run_shadow_route_rebalance_fault_case(case2)
    assert result2.success is True
    assert result2.actual_outcome == "restore_candidate_tables"

    case3 = RouteRebalanceFaultCase("C_CR", "active carrier-registry overwrite attempt", "overwrite registry", True, "restore_candidate_tables")
    result3 = run_shadow_route_rebalance_fault_case(case3)
    assert result3.success is True
    assert result3.actual_outcome == "restore_candidate_tables"


def test_ranger_and_court_reviews():
    """Verify RouteFaultRanger emits JSON-serializable SovereignPacket and Promotion Court reviews."""
    matrix = build_route_rebalance_fault_matrix()
    report = run_shadow_route_rebalance_fault_matrix(matrix)
    assert report.success is True
    
    reg_matrix = build_optimization_regression_matrix()
    reg_report = run_shadow_optimization_regression_matrix(reg_matrix)
    assert reg_report.success is True
    
    # Cost model regression mock report
    cost_report = RouteCostRegressionReport("REP_COST", True, True)
    
    # Waveguide audit report
    wg_report = WaveguideFaultAuditReport("REP_WG", True, False)
    
    # Rollback proof report
    proof_cases = [RouteRebalanceRollbackCase("C1", "test", "test rollback")]
    proof_report = run_route_rebalance_rollback_proof(proof_cases)
    
    # Oracle report
    oracle_case = RouteRebalanceFaultCase("C_SO", "safety oracle mismatch", "mismatch", True, "reject_route_candidate")
    oracle_result = run_shadow_route_rebalance_fault_case(oracle_case)
    
    ranger = RouteFaultRanger()
    packet = ranger.observe_reports(
        fault_report=report,
        regression_report=reg_report,
        cost_report=cost_report,
        waveguide_report=wg_report,
        rollback_report=proof_report,
        oracle_report=oracle_result,
        mission_id="MISSION_42_TEST"
    )
    
    assert isinstance(packet, SovereignPacket)
    print("DEBUG PACKET EVIDENCE:", packet.evidence)
    assert packet.level == 42
    assert packet.recommendation == "promote"
    
    # JSON serialization check
    packet_dict = packet.to_dict()
    assert json.dumps(packet_dict) is not None
    
    # Promotion Court reviews
    court = PromotionCourt()
    
    dec_fm = court.review_route_rebalance_fault_matrix_report(report)
    assert dec_fm.passed is True
    assert dec_fm.decision == "accept_shadow_route_fault_matrix"
    
    dec_reg = court.review_optimization_regression_report(reg_report)
    assert dec_reg.passed is True
    assert dec_reg.decision == "accept_shadow_route_fault_matrix"
    
    dec_cost = court.review_route_cost_regression_report(cost_report)
    assert dec_cost.passed is True
    assert dec_cost.decision == "accept_shadow_route_fault_matrix"
    
    dec_wg = court.review_waveguide_fault_audit_report(wg_report)
    assert dec_wg.passed is True
    assert dec_wg.decision == "accept_shadow_route_fault_matrix"
    
    dec_rb = court.review_route_rebalance_rollback_proof_report(proof_report)
    assert dec_rb.passed is True
    assert dec_rb.decision == "accept_shadow_route_fault_matrix"
    
    dec_rng = court.review_route_fault_ranger_packet(packet)
    assert dec_rng.passed is True
    assert dec_rng.decision == "promote_level42_candidate"
