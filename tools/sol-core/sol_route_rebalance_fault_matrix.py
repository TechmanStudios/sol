# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Route Rebalance Fault Matrix
================================
Injects deterministic faults into route optimization and waveguide rebalancing plans.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class RouteRebalanceFaultCase:
    case_id: str
    category: str
    description: str
    injected_value: Any
    expected_outcome: str

@dataclass
class RouteRebalanceFaultInjection:
    injection_id: str
    case: RouteRebalanceFaultCase
    timestamp: float = field(default_factory=time.time)

@dataclass
class RouteRebalanceFaultScenario:
    scenario_id: str
    name: str
    cases: List[RouteRebalanceFaultCase]

@dataclass
class RouteRebalanceFaultResult:
    case_id: str
    category: str
    success: bool
    actual_outcome: str
    matched_expected: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class RouteRebalanceFaultMatrix:
    matrix_id: str
    policy: Any
    scenarios: List[RouteRebalanceFaultScenario] = field(default_factory=list)

@dataclass
class RouteRebalanceFaultMatrixReport:
    report_id: str
    matrix_id: str
    results: List[RouteRebalanceFaultResult]
    passed_cases: int
    failed_cases: int
    success: bool
    timestamp: float = field(default_factory=time.time)


def build_route_rebalance_fault_matrix(policy: Any = None) -> RouteRebalanceFaultMatrix:
    """
    Builds a fault matrix containing cases for all required route rebalance categories.
    """
    categories = [
        ("transaction boundary break", "Optimization breaks transaction boundaries", True, "reject_route_candidate"),
        ("atomic commit boundary break", "Optimization breaks atomic commit boundaries", True, "reject_route_candidate"),
        ("missing rollback reference", "Rollback snapshot references are missing", True, "reject_route_candidate"),
        ("corrupted rollback reference", "Rollback snapshot is corrupted during verification", True, "reject_route_candidate"),
        ("state hash mismatch", "Before and after state hashes do not match", True, "reject_route_candidate"),
        ("route state hash mismatch", "Route state hashes do not match references", True, "reject_route_candidate"),
        ("local quorum failure", "Local quorum voting consensus is rejected", True, "reject_route_candidate"),
        ("global quorum failure", "Global coordinator transaction consensus fails", True, "reject_route_candidate"),
        ("sequencer quorum failure", "Sequencer group consensus is rejected", True, "reject_route_candidate"),
        ("lock boundary violation", "Lock boundary violation detected", True, "request_lock_boundary_review"),
        ("cross-manifold deadlock", "Deadlock detected during lock acquisition", True, "request_lock_boundary_review"),
        ("cadence window failure", "Route lies outside approved cadence window", True, "request_cadence_recalibration"),
        ("global cadence skew spike", "Global cadence skew exceeds threshold", True, "request_cadence_recalibration"),
        ("wavefront coherence collapse", "Wavefront coherence falls below threshold", True, "reject_route_candidate"),
        ("crosstalk spike", "Inter-lane crosstalk exceeds safe limit", True, "quarantine_waveguide_segment"),
        ("boundary reflection breach", "PML boundary reflection exceeds threshold", True, "quarantine_route"),
        ("missing PML boundary", "PML cells boundary is missing or invalid", True, "quarantine_waveguide_segment"),
        ("weakened PML boundary", "PML boundary reflection exceeds limit", True, "reject_route_candidate"),
        ("carrier identity break", "Rebalance candidate breaks carrier identity", True, "reject_route_candidate"),
        ("quadrature pairing break", "Rebalance candidate breaks quadrature pairings", True, "reject_route_candidate"),
        ("carrier lease failure", "Missing active lease for carrier on lane", True, "quarantine_carrier"),
        ("lane isolation breach", "Rebalance candidate breaks lane isolation rules", True, "reject_route_candidate"),
        ("prefix-carry bridge break", "Rebalance candidate breaks prefix-carry semantics", True, "quarantine_manifold"),
        ("arithmetic oracle mismatch", "Arithmetic pipeline result does not match oracle", True, "reject_route_candidate"),
        ("tensor binding break", "Tensor binding plan fails to map components", True, "reject_route_candidate"),
        ("reduction tree break", "Reduction tree plan breaks bindings", True, "reject_route_candidate"),
        ("cost model false improvement", "Route cost increases without justification", True, "request_cost_model_review"),
        ("route risk underestimation", "Route risk is underestimated against policy", True, "request_cost_model_review"),
        ("safety oracle mismatch", "Mismatch between oracle expectation and outcome", True, "reject_route_candidate"),
        ("active phase-table overwrite attempt", "Attempt to overwrite active phase table", True, "restore_candidate_tables"),
        ("active cadence-profile overwrite attempt", "Attempt to overwrite active cadence table", True, "restore_candidate_tables"),
        ("active carrier-registry overwrite attempt", "Attempt to overwrite active carrier registry", True, "restore_candidate_tables"),
        ("production/default route mutation attempt", "Attempt to mutate default production route", True, "reject_route_candidate"),
    ]

    cases = []
    for idx, (cat, desc, val, out) in enumerate(categories):
        cases.append(RouteRebalanceFaultCase(
            case_id=f"CASE_RR_{idx+1:03d}",
            category=cat,
            description=desc,
            injected_value=val,
            expected_outcome=out
        ))

    scenario = RouteRebalanceFaultScenario(
        scenario_id="SCEN_RR_ALL",
        name="All Route Rebalance Faults Scenario",
        cases=cases
    )

    matrix_id = f"MATRIX_RR_{uuid.uuid4().hex[:8]}"
    return RouteRebalanceFaultMatrix(
        matrix_id=matrix_id,
        policy=policy,
        scenarios=[scenario]
    )


def inject_route_rebalance_fault(case: RouteRebalanceFaultCase, baseline: Any) -> Any:
    """
    Injects the specified route rebalance fault case into a protocol or dict.
    """
    # Baseline is assumed to be a RouteRebalanceProtocol
    if not hasattr(baseline, "route_telemetry") or baseline.route_telemetry is None:
        baseline.route_telemetry = {}
    if not hasattr(baseline, "waveguide_telemetry") or baseline.waveguide_telemetry is None:
        baseline.waveguide_telemetry = {}

    cat = case.category
    if cat == "transaction boundary break":
        baseline.route_telemetry["break_transaction_boundaries"] = True
    elif cat == "atomic commit boundary break":
        baseline.route_telemetry["break_atomic_commit_boundaries"] = True
    elif cat == "missing rollback reference":
        baseline.rollback_snapshots = []
        baseline.route_telemetry["missing_rollback_snapshot"] = True
    elif cat == "corrupted rollback reference":
        baseline.route_telemetry["corrupted_rollback_snapshot"] = True
    elif cat == "state hash mismatch":
        baseline.route_telemetry["state_hash_mismatch"] = True
    elif cat == "route state hash mismatch":
        baseline.route_telemetry["route_state_hash_mismatch"] = True
    elif cat == "local quorum failure":
        baseline.route_telemetry["local_quorum_failed"] = True
    elif cat == "global quorum failure":
        baseline.route_telemetry["global_quorum_failed"] = True
    elif cat == "sequencer quorum failure":
        baseline.route_telemetry["sequencer_quorum_failed"] = True
    elif cat == "lock boundary violation":
        baseline.route_telemetry["lock_schedule"] = ["lock_violation"]
        baseline.route_telemetry["lock_boundary_violation"] = True
    elif cat == "cross-manifold deadlock":
        baseline.route_telemetry["lock_schedule"] = ["lock_violation"]
        baseline.route_telemetry["cross_manifold_deadlock"] = True
    elif cat == "cadence window failure":
        baseline.route_telemetry["outside_cadence_window"] = True
    elif cat == "global cadence skew spike":
        baseline.route_telemetry["global_skew"] = 0.09
        baseline.route_telemetry["global_cadence_skew"] = True
    elif cat == "wavefront coherence collapse":
        baseline.route_telemetry["wavefront_coherence_collapse"] = True
    elif cat == "crosstalk spike":
        baseline.waveguide_telemetry["crosstalk_spike"] = True
    elif cat == "boundary reflection breach":
        baseline.waveguide_telemetry["reflection_breach"] = True
    elif cat == "missing PML boundary":
        baseline.waveguide_telemetry["missing_pml"] = True
    elif cat == "weakened PML boundary":
        baseline.waveguide_telemetry["weakened_pml"] = True
    elif cat == "carrier identity break":
        baseline.waveguide_telemetry["break_carrier_identity"] = True
    elif cat == "quadrature pairing break":
        baseline.waveguide_telemetry["break_quadrature_pair"] = True
    elif cat == "carrier lease failure":
        baseline.waveguide_telemetry["carrier_lease_failure"] = True
    elif cat == "lane isolation breach":
        baseline.waveguide_telemetry["lane_isolation_breached"] = True
    elif cat == "prefix-carry bridge break":
        baseline.waveguide_telemetry["break_prefix_carry"] = True
    elif cat == "arithmetic oracle mismatch":
        baseline.route_telemetry["arithmetic_oracle_mismatch"] = True
    elif cat == "tensor binding break":
        baseline.route_telemetry["tensor_binding_break"] = True
    elif cat == "reduction tree break":
        baseline.route_telemetry["reduction_tree_break"] = True
    elif cat == "cost model false improvement":
        baseline.route_telemetry["no_improvement_without_justification"] = True
    elif cat == "route risk underestimation":
        baseline.route_telemetry["risk_underestimated"] = True
    elif cat == "safety oracle mismatch":
        baseline.route_telemetry["safety_oracle_mismatch"] = True
        baseline.safety_oracle_agreement = False
    elif cat == "active phase-table overwrite attempt":
        baseline.route_telemetry["active_phase_table_overwritten"] = True
        baseline.route_telemetry["active_tables_overwritten"] = True
    elif cat == "active cadence-profile overwrite attempt":
        baseline.route_telemetry["active_cadence_table_overwritten"] = True
        baseline.route_telemetry["active_tables_overwritten"] = True
    elif cat == "active carrier-registry overwrite attempt":
        baseline.route_telemetry["active_carrier_registry_overwritten"] = True
        baseline.route_telemetry["active_tables_overwritten"] = True
    elif cat == "production/default route mutation attempt":
        baseline.route_telemetry["production_route_mutation_attempt"] = True

    return baseline


def run_shadow_route_rebalance_fault_case(case: RouteRebalanceFaultCase) -> RouteRebalanceFaultResult:
    """
    Runs shadow execution of a route rebalance fault case.
    """
    from sol_route_rebalance_protocol import RouteRebalanceProtocol, prepare_route_rebalance, verify_route_rebalance
    from coding_library.sovereign_domain.frontier_bridge import RouteRebalanceFaultAdvisor

    # Instantiate protocol with rollback snapshots and safety oracle agreement
    protocol = RouteRebalanceProtocol(
        protocol_id=f"PROTO_{uuid.uuid4().hex[:8]}",
        rollback_snapshots=["snap1", "snap2"],
        state_hash_references=["hash1", "hash2"],
        safety_oracle_agreement=True,
        court_token="COURT_TOKEN_VALID"
    )

    # Inject the fault
    protocol = inject_route_rebalance_fault(case, protocol)

    # Run prepare
    prep_state = prepare_route_rebalance(protocol)

    errors = []
    if prep_state.prepared:
        verify_state = verify_route_rebalance(protocol)
        success = verify_state.verified
        errors = verify_state.errors
    else:
        success = False
        errors = prep_state.errors

    # Consult RouteRebalanceFaultAdvisor for actual outcome
    advisor = RouteRebalanceFaultAdvisor()
    advisor_report = advisor.suggest_response(protocol.route_report, protocol.rebalance_report, protocol)
    actual_outcome = advisor_report.suggestion.value

    matched = (actual_outcome == case.expected_outcome)
    # The promotion is blocked if success is False
    case_success = (not success) and matched

    return RouteRebalanceFaultResult(
        case_id=case.case_id,
        category=case.category,
        success=case_success,
        actual_outcome=actual_outcome,
        matched_expected=matched,
        errors=errors
    )


def run_shadow_route_rebalance_fault_matrix(matrix: RouteRebalanceFaultMatrix) -> RouteRebalanceFaultMatrixReport:
    """
    Runs all cases in the route rebalance fault matrix.
    """
    results = []
    for scen in matrix.scenarios:
        for case in scen.cases:
            results.append(run_shadow_route_rebalance_fault_case(case))

    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    success = failed == 0

    report_id = f"REP_RR_MATRIX_{uuid.uuid4().hex[:8]}"
    return RouteRebalanceFaultMatrixReport(
        report_id=report_id,
        matrix_id=matrix.matrix_id,
        results=results,
        passed_cases=passed,
        failed_cases=failed,
        success=success
    )


def summarize_route_rebalance_fault_matrix(results: List[RouteRebalanceFaultResult]) -> Dict[str, Any]:
    """
    Summarizes the results of route rebalance fault execution.
    """
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "success": all(r.success for r in results)
    }
