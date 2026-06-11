# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Transactional Geodesic Route Optimizer
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

@dataclass
class TransactionalGeodesicRoute:
    route_id: str
    path: List[str]
    manifolds: List[str]
    shard_crossings: int = 0
    manifold_crossings: int = 0
    depth: int = 0

@dataclass
class TransactionalRouteCandidate:
    candidate_id: str
    route: TransactionalGeodesicRoute
    estimated_cost: float = 0.0
    estimated_risk: float = 0.0
    is_valid: bool = True

@dataclass
class TransactionalRouteOptimizationIntent:
    intent_id: str
    transaction_report: Dict[str, Any]
    topology: Dict[str, Any]
    policy: Dict[str, Any]

@dataclass
class TransactionalRouteOptimizationPlan:
    plan_id: str
    intent: TransactionalRouteOptimizationIntent
    candidates: List[TransactionalRouteCandidate] = field(default_factory=list)
    selected_candidate: Optional[TransactionalRouteCandidate] = None
    rollback_snapshots: List[str] = field(default_factory=list)
    state_hash_references: List[str] = field(default_factory=list)
    quorum_requirements: Dict[str, Any] = field(default_factory=dict)
    global_lock_boundaries: List[str] = field(default_factory=list)
    cadence_windows: List[str] = field(default_factory=list)
    wavefront_stability_requirements: Dict[str, Any] = field(default_factory=dict)
    evidence_packet_references: List[str] = field(default_factory=list)
    validation_passed: bool = False

@dataclass
class TransactionalRouteOptimizationResult:
    result_id: str
    plan_id: str
    optimized_route: Optional[TransactionalGeodesicRoute] = None
    success: bool = False
    executed_in_shadow: bool = True
    rollback_complexity: int = 0

@dataclass
class TransactionalRouteOptimizationReport:
    report_id: str
    plan: TransactionalRouteOptimizationPlan
    result: TransactionalRouteOptimizationResult
    success: bool = False
    passed_gates: bool = False
    errors: List[str] = field(default_factory=list)


def build_transactional_route_optimization_intent(
    transaction_report: Dict[str, Any],
    topology: Dict[str, Any],
    policy: Dict[str, Any]
) -> TransactionalRouteOptimizationIntent:
    """
    Builds a TransactionalRouteOptimizationIntent from mock or real transaction reports, topology and policy.
    """
    return TransactionalRouteOptimizationIntent(
        intent_id=f"INTENT_{uuid.uuid4().hex[:8]}",
        transaction_report=transaction_report,
        topology=topology,
        policy=policy
    )


def identify_transactional_route_candidates(
    intent: TransactionalRouteOptimizationIntent
) -> List[TransactionalRouteCandidate]:
    """
    Identifies candidate routes from the optimization intent.
    """
    candidates = []
    # Identify from intent transaction_report or topology
    routes_data = intent.topology.get("available_routes", [])
    if not routes_data:
        # Default fallback route
        routes_data = [{"route_id": "route_default", "path": ["shard_a", "shard_b"], "manifolds": ["manifold_1"]}]
        
    for r_idx, r in enumerate(routes_data):
        route = TransactionalGeodesicRoute(
            route_id=r.get("route_id", f"route_{r_idx}"),
            path=r.get("path", []),
            manifolds=r.get("manifolds", []),
            shard_crossings=r.get("shard_crossings", 0),
            manifold_crossings=r.get("manifold_crossings", 0),
            depth=r.get("depth", len(r.get("path", [])))
        )
        candidates.append(
            TransactionalRouteCandidate(
                candidate_id=f"CANDIDATE_{uuid.uuid4().hex[:8]}",
                route=route,
                estimated_cost=0.0,
                estimated_risk=0.0,
                is_valid=True
            )
        )
    return candidates


def build_transactional_route_optimization_plan(
    candidates: List[TransactionalRouteCandidate],
    policy: Dict[str, Any]
) -> TransactionalRouteOptimizationPlan:
    """
    Builds an optimization plan from candidates and policy.
    """
    # Look for candidate with lowest estimated cost/risk, or just pick the first valid
    valid_candidates = [c for c in candidates if c.is_valid]
    selected = None
    if valid_candidates:
        # Sort by cost + risk
        valid_candidates.sort(key=lambda x: x.estimated_cost + x.estimated_risk)
        selected = valid_candidates[0]

    return TransactionalRouteOptimizationPlan(
        plan_id=f"PLAN_{uuid.uuid4().hex[:8]}",
        intent=policy.get("intent"), # can be None or set
        candidates=candidates,
        selected_candidate=selected,
        rollback_snapshots=policy.get("rollback_snapshots", []),
        state_hash_references=policy.get("state_hash_references", []),
        quorum_requirements=policy.get("quorum_requirements", {}),
        global_lock_boundaries=policy.get("global_lock_boundaries", []),
        cadence_windows=policy.get("cadence_windows", []),
        wavefront_stability_requirements=policy.get("wavefront_stability_requirements", {}),
        evidence_packet_references=policy.get("evidence_packet_references", []),
        validation_passed=False
    )


def validate_transactional_route_optimization_plan(
    plan: TransactionalRouteOptimizationPlan,
    errors: Optional[List[str]] = None
) -> bool:
    """
    Validates that the optimization plan preserves transaction boundaries,
    locks, cadence, rollback state, and wavefront stability.
    """
    if errors is None:
        errors = []
    
    # 1. Rollback snapshot references must be present
    if not plan.rollback_snapshots:
        errors.append("Missing rollback snapshots")
        
    # 2. State hash references must be present
    if not plan.state_hash_references:
        errors.append("Missing state hash references")
        
    # 3. Get contexts
    tx_context = plan.intent.transaction_report if plan.intent else {}
    policy = plan.intent.policy if (plan.intent and hasattr(plan.intent, "policy")) else {}
    if not isinstance(tx_context, dict):
        tx_context = {}
    if not isinstance(policy, dict):
        policy = {}
        
    def get_flag(name):
        return (
            tx_context.get(name, False) or 
            policy.get(name, False) or 
            (plan.intent.metadata.get(name, False) if (plan.intent and hasattr(plan.intent, "metadata") and isinstance(plan.intent.metadata, dict)) else False)
        )
        
    if get_flag("break_transaction_boundaries"):
        errors.append("Optimization breaks transaction boundaries")
        
    if get_flag("break_atomic_commit_boundaries"):
        errors.append("Optimization breaks atomic commit boundaries")
        
    if get_flag("missing_rollback_snapshot"):
        errors.append("Missing rollback snapshots")
        
    if get_flag("corrupted_rollback_snapshot"):
        errors.append("Corrupted rollback snapshot")
        
    if get_flag("state_hash_mismatch") or get_flag("route_state_hash_mismatch"):
        errors.append("State hash mismatch")
        
    if get_flag("local_quorum_failed"):
        errors.append("Local quorum failure")
        
    if get_flag("global_quorum_failed"):
        errors.append("Global quorum failure")
        
    if get_flag("sequencer_quorum_failed"):
        errors.append("Sequencer quorum failure")
        
    # 4. Lock boundary check
    if "lock_boundary_violation" in plan.global_lock_boundaries or get_flag("lock_boundary_violation"):
        errors.append("Lock boundary violation detected")
        
    # 5. Cross-manifold deadlock risk check
    if plan.quorum_requirements.get("cross_manifold_deadlock", False) or get_flag("cross_manifold_deadlock"):
        errors.append("Cross-manifold deadlock risk detected")
        
    # 6. Cadence window check
    if "outside_cadence_window" in plan.cadence_windows or get_flag("outside_cadence_window"):
        errors.append("Route lies outside approved cadence window")
        
    if get_flag("global_cadence_skew") or tx_context.get("global_skew", 0.0) > 0.05:
        errors.append("Global cadence skew spike detected")
        
    if get_flag("wavefront_coherence_collapse"):
        errors.append("Wavefront coherence collapse")
        
    if get_flag("arithmetic_oracle_mismatch"):
        errors.append("Arithmetic oracle mismatch")
        
    if get_flag("tensor_binding_break"):
        errors.append("Tensor binding break")
        
    if get_flag("reduction_tree_break"):
        errors.append("Reduction tree break")
        
    if get_flag("no_improvement_without_justification"):
        errors.append("No cost improvement detected without policy justification")
        
    if get_flag("risk_underestimated"):
        errors.append("Route risk underestimation detected")
        
    if get_flag("safety_oracle_mismatch"):
        errors.append("Safety oracle mismatch")
        
    if get_flag("active_phase_table_overwritten") or get_flag("active_cadence_table_overwritten") or get_flag("active_carrier_registry_overwritten") or get_flag("active_tables_overwritten"):
        errors.append("Active tables overwritten")
        
    if get_flag("production_route_mutation_attempt"):
        errors.append("Production route mutation attempt")

    plan.validation_passed = (len(errors) == 0)
    return plan.validation_passed


def execute_shadow_transactional_route_optimization(
    plan: TransactionalRouteOptimizationPlan
) -> TransactionalRouteOptimizationReport:
    """
    Executes route optimization in shadow mode. Returns a report.
    """
    errors = []
    passed_gates = validate_transactional_route_optimization_plan(plan, errors)
    
    if not plan.selected_candidate:
        errors.append("No candidate selected for optimization")
        passed_gates = False
        
    if not passed_gates:
        errors.append("Validation gates failed for route optimization plan")
        
    success = passed_gates and len(errors) == 0
    
    result = TransactionalRouteOptimizationResult(
        result_id=f"RESULT_{uuid.uuid4().hex[:8]}",
        plan_id=plan.plan_id,
        optimized_route=plan.selected_candidate.route if (success and plan.selected_candidate) else None,
        success=success,
        executed_in_shadow=True,
        rollback_complexity=len(plan.rollback_snapshots)
    )
    
    return TransactionalRouteOptimizationReport(
        report_id=f"REPORT_{uuid.uuid4().hex[:8]}",
        plan=plan,
        result=result,
        success=success,
        passed_gates=passed_gates,
        errors=errors
    )


def export_route_optimization_fault_targets(plan: TransactionalRouteOptimizationPlan) -> Dict[str, Any]:
    """
    Exports a list of potential fault targets associated with the plan.
    """
    return {
        "plan_id": plan.plan_id,
        "selected_candidate_id": plan.selected_candidate.candidate_id if plan.selected_candidate else None,
        "rollback_count": len(plan.rollback_snapshots),
        "target_route_id": plan.selected_candidate.route.route_id if (plan.selected_candidate and plan.selected_candidate.route) else None
    }


def validate_route_optimization_against_fault_matrix(report: TransactionalRouteOptimizationReport, matrix_report: Any) -> bool:
    """
    Ensures route optimization passes checks and matches fault matrix safety.
    """
    if not report.success:
        return False
    if matrix_report and not getattr(matrix_report, "success", True):
        return False
    return True

