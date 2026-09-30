# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Optimization Regression Matrix
==================================
Identifies and tracks regressions in route optimization and waveguide rebalancing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class OptimizationRegressionCase:
    case_id: str
    category: str
    description: str
    expected_outcome: str

@dataclass
class OptimizationRegressionBaseline:
    baseline_id: str
    route_plan_id: str
    rebalance_plan_id: str
    estimated_cost: float
    estimated_risk: float
    has_pml: bool
    preserves_identity: bool
    preserves_prefix_carry: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class OptimizationRegressionResult:
    case_id: str
    category: str
    success: bool
    regression_detected: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class OptimizationRegressionMatrix:
    matrix_id: str
    policy: Any
    cases: List[OptimizationRegressionCase] = field(default_factory=list)

@dataclass
class OptimizationRegressionReport:
    report_id: str
    matrix_id: str
    results: List[OptimizationRegressionResult]
    passed_cases: int
    failed_cases: int
    success: bool
    timestamp: float = field(default_factory=time.time)


def build_optimization_regression_matrix(policy: Any = None) -> OptimizationRegressionMatrix:
    """
    Builds the optimization regression matrix with all required cases.
    """
    cases = [
        OptimizationRegressionCase(
            case_id="REG_CASE_001",
            category="risk increase",
            description="optimized route does not increase risk without justification",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_002",
            category="transaction boundaries",
            description="optimized route does not break transaction boundaries",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_003",
            category="rollback references",
            description="optimized route does not break rollback references",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_004",
            category="PML coverage",
            description="waveguide rebalance does not remove PML coverage",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_005",
            category="carrier identity",
            description="waveguide rebalance does not break carrier identity",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_006",
            category="prefix-carry paths",
            description="waveguide rebalance does not break prefix-carry paths",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_007",
            category="false speedups",
            description="cost model does not accept false speedups",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_008",
            category="safety oracle outcomes",
            description="safety oracle expected outcome matches actual outcome",
            expected_outcome="block_promotion"
        ),
        OptimizationRegressionCase(
            case_id="REG_CASE_009",
            category="table overwrites",
            description="no active/default tables are overwritten",
            expected_outcome="block_promotion"
        ),
    ]
    return OptimizationRegressionMatrix(
        matrix_id=f"REG_MATRIX_{uuid.uuid4().hex[:8]}",
        policy=policy,
        cases=cases
    )


def capture_optimization_baseline(route_plan: Any, rebalance_plan: Any) -> OptimizationRegressionBaseline:
    """
    Captures an optimization baseline from plans.
    """
    cost = 0.0
    risk = 0.0
    if route_plan and route_plan.selected_candidate:
        cost = route_plan.selected_candidate.estimated_cost
        risk = route_plan.selected_candidate.estimated_risk

    has_pml = True
    preserves_identity = True
    preserves_prefix_carry = True
    if rebalance_plan and rebalance_plan.candidates:
        c = rebalance_plan.candidates[0]
        has_pml = c.has_pml_coverage
        preserves_identity = c.preserves_lane_identity and c.preserves_carrier_identity
        preserves_prefix_carry = c.preserves_prefix_carry

    return OptimizationRegressionBaseline(
        baseline_id=f"BASE_{uuid.uuid4().hex[:8]}",
        route_plan_id=getattr(route_plan, "plan_id", "none"),
        rebalance_plan_id=getattr(rebalance_plan, "plan_id", "none"),
        estimated_cost=cost,
        estimated_risk=risk,
        has_pml=has_pml,
        preserves_identity=preserves_identity,
        preserves_prefix_carry=preserves_prefix_carry
    )


def run_shadow_optimization_regression_case(case: OptimizationRegressionCase) -> OptimizationRegressionResult:
    """
    Runs a shadow optimization regression case.
    """
    from sol_route_rebalance_protocol import RouteRebalanceProtocol, prepare_route_rebalance, verify_route_rebalance

    # Construct protocol and set flags corresponding to the regression case category
    protocol = RouteRebalanceProtocol(
        protocol_id=f"PROTO_REG_{uuid.uuid4().hex[:8]}",
        rollback_snapshots=["snap1", "snap2"],
        state_hash_references=["hash1", "hash2"],
        safety_oracle_agreement=True,
        court_token="COURT_TOKEN_VALID"
    )

    cat = case.category
    if cat == "risk increase":
        protocol.route_telemetry = {"risk_underestimated": True, "depth": 3}
    elif cat == "transaction boundaries":
        protocol.route_telemetry = {"break_transaction_boundaries": True}
    elif cat == "rollback references":
        protocol.rollback_snapshots = []
    elif cat == "PML coverage":
        protocol.waveguide_telemetry = {"missing_pml": True}
    elif cat == "carrier identity":
        protocol.waveguide_telemetry = {"break_carrier_identity": True}
    elif cat == "prefix-carry paths":
        protocol.waveguide_telemetry = {"break_prefix_carry": True}
    elif cat == "false speedups":
        protocol.route_telemetry = {"no_improvement_without_justification": True}
    elif cat == "safety oracle outcomes":
        protocol.safety_oracle_agreement = False
    elif cat == "table overwrites":
        protocol.route_telemetry = {"active_phase_table_overwritten": True}

    prep_state = prepare_route_rebalance(protocol)
    
    errors = []
    if prep_state.prepared:
        verify_state = verify_route_rebalance(protocol)
        success = verify_state.verified
        errors = verify_state.errors
    else:
        success = False
        errors = prep_state.errors

    # If the protocol validation failed (success is False), it means the regression was correctly caught and blocked.
    # Therefore, the regression case succeeded.
    regression_detected = not success
    case_success = regression_detected

    return OptimizationRegressionResult(
        case_id=case.case_id,
        category=case.category,
        success=case_success,
        regression_detected=regression_detected,
        errors=errors
    )


def run_shadow_optimization_regression_matrix(matrix: OptimizationRegressionMatrix) -> OptimizationRegressionReport:
    """
    Runs all cases in the optimization regression matrix.
    """
    results = []
    for case in matrix.cases:
        results.append(run_shadow_optimization_regression_case(case))

    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    success = failed == 0

    return OptimizationRegressionReport(
        report_id=f"REP_REG_MATRIX_{uuid.uuid4().hex[:8]}",
        matrix_id=matrix.matrix_id,
        results=results,
        passed_cases=passed,
        failed_cases=failed,
        success=success
    )


def summarize_optimization_regressions(results: List[OptimizationRegressionResult]) -> Dict[str, Any]:
    """
    Summarizes optimization regression results.
    """
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "success": all(r.success for r in results)
    }
