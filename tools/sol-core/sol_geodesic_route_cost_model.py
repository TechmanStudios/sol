# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Geodesic Route Cost Model
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from sol_transactional_geodesic_optimizer import TransactionalGeodesicRoute, TransactionalRouteCandidate

@dataclass
class GeodesicRouteCostPolicy:
    policy_id: str
    depth_weight: float = 1.0
    shard_crossing_weight: float = 2.0
    manifold_crossing_weight: float = 5.0
    lock_crossing_weight: float = 3.0
    crosstalk_weight: float = 10.0
    reflection_weight: float = 10.0
    risk_threshold: float = 0.8

@dataclass
class GeodesicRouteCostEstimate:
    route_id: str
    depth: int = 0
    shard_crossings: int = 0
    manifold_crossings: int = 0
    lock_crossings: int = 0
    cadence_risk: float = 0.0
    wavefront_coherence_risk: float = 0.0
    crosstalk_risk: float = 0.0
    boundary_reflection_risk: float = 0.0
    pml_coverage: float = 1.0  # 1.0 is full, 0.0 is none
    rollback_complexity: int = 0
    quorum_overhead: float = 0.0
    expected_latency: float = 0.0
    total_cost: float = 0.0

@dataclass
class GeodesicRouteComparison:
    route_id_before: str
    route_id_after: str
    cost_before: float
    cost_after: float
    cost_improved: bool
    risk_before: float
    risk_after: float
    risk_improved: bool
    justification: str

@dataclass
class RouteOptimizationScore:
    candidate_id: str
    score: float
    passed_policy_bounds: bool


def estimate_geodesic_route_cost(
    route: TransactionalGeodesicRoute,
    telemetry: Optional[Dict[str, Any]] = None
) -> GeodesicRouteCostEstimate:
    """
    Estimates the physical and computational cost of a geodesic route.
    """
    tel = telemetry or {}
    
    # Extract telemetry metrics if present, otherwise default
    lock_crossings = tel.get("lock_crossings", 1 if "lock" in getattr(route, "path", []) else 0)
    cadence_risk = tel.get("cadence_risk", 0.1)
    wavefront_coherence_risk = tel.get("wavefront_coherence_risk", 0.05)
    crosstalk_risk = tel.get("crosstalk_risk", 0.1)
    
    # Boundary reflection risk is higher if PML coverage is low
    pml_coverage = tel.get("pml_coverage", 1.0)
    boundary_reflection_risk = tel.get("boundary_reflection_risk", max(0.0, 1.0 - pml_coverage))
    
    rollback_complexity = tel.get("rollback_complexity", 1)
    quorum_overhead = tel.get("quorum_overhead", 0.2)
    
    # Simple expected latency model (latency steps)
    expected_latency = (
        route.depth * 2.0 +
        route.shard_crossings * 3.5 +
        route.manifold_crossings * 6.0 +
        lock_crossings * 4.0
    )
    
    # Total cost formula
    total_cost = (
        route.depth * 1.0 +
        route.shard_crossings * 2.5 +
        route.manifold_crossings * 5.0 +
        lock_crossings * 3.0 +
        crosstalk_risk * 10.0 +
        boundary_reflection_risk * 10.0 +
        expected_latency * 0.5
    )
    
    return GeodesicRouteCostEstimate(
        route_id=route.route_id,
        depth=route.depth,
        shard_crossings=route.shard_crossings,
        manifold_crossings=route.manifold_crossings,
        lock_crossings=lock_crossings,
        cadence_risk=cadence_risk,
        wavefront_coherence_risk=wavefront_coherence_risk,
        crosstalk_risk=crosstalk_risk,
        boundary_reflection_risk=boundary_reflection_risk,
        pml_coverage=pml_coverage,
        rollback_complexity=rollback_complexity,
        quorum_overhead=quorum_overhead,
        expected_latency=expected_latency,
        total_cost=total_cost
    )


def estimate_transactional_route_risk(
    route: TransactionalGeodesicRoute,
    transaction_context: Dict[str, Any]
) -> float:
    """
    Estimates routing risk based on transaction settings, crosstalk, cadence, reflection, and rollback complexity.
    """
    cadence_risk = transaction_context.get("cadence_risk", 0.2)
    crosstalk = transaction_context.get("crosstalk", 0.1)
    rollback_complexity = transaction_context.get("rollback_complexity", 2)
    
    # Scale rollback complexity factor (complexity 0 to 10 mapped to 0.0 to 1.0)
    rollback_factor = min(1.0, rollback_complexity / 10.0)
    
    # Risk calculation
    risk = (cadence_risk + crosstalk + rollback_factor) / 3.0
    return risk


def compare_geodesic_routes(
    before: GeodesicRouteCostEstimate,
    after: GeodesicRouteCostEstimate
) -> GeodesicRouteComparison:
    """
    Compares two route cost estimates and determines if improvement exists.
    """
    cost_improved = after.total_cost < before.total_cost
    risk_improved = (after.crosstalk_risk + after.cadence_risk + after.boundary_reflection_risk) < (
        before.crosstalk_risk + before.cadence_risk + before.boundary_reflection_risk
    )
    
    improvement_delta = before.total_cost - after.total_cost
    if cost_improved:
        justification = f"Cost improved by {improvement_delta:.4f} units."
    else:
        justification = "Cost did not improve. Candidate rejected unless justified by policy."
        
    return GeodesicRouteComparison(
        route_id_before=before.route_id,
        route_id_after=after.route_id,
        cost_before=before.total_cost,
        cost_after=after.total_cost,
        cost_improved=cost_improved,
        risk_before=before.cadence_risk + before.crosstalk_risk + before.boundary_reflection_risk,
        risk_after=after.cadence_risk + after.crosstalk_risk + after.boundary_reflection_risk,
        risk_improved=risk_improved,
        justification=justification
    )


def score_route_candidate(
    candidate: TransactionalRouteCandidate,
    policy: GeodesicRouteCostPolicy
) -> RouteOptimizationScore:
    """
    Scores a candidate route based on the cost policy.
    """
    # Low score is better (lower cost)
    score = candidate.estimated_cost + candidate.estimated_risk
    passed = candidate.is_valid and candidate.estimated_risk <= policy.risk_threshold
    
    # Propagate risk underestimated flag if present
    ret_score = RouteOptimizationScore(
        candidate_id=candidate.candidate_id,
        score=score,
        passed_policy_bounds=passed
    )
    if getattr(candidate, "risk_underestimated", False):
        setattr(ret_score, "risk_underestimated", True)
    return ret_score


def validate_cost_improvement_not_false_positive(comparison: GeodesicRouteComparison, policy: Any = None) -> bool:
    """
    Ensures that cost improvement is not a false positive that increases critical safety risk without justification.
    """
    if comparison.cost_improved and not comparison.risk_improved:
        justified = False
        if policy:
            justified = getattr(policy, "justified_non_promotion", False) or (isinstance(policy, dict) and policy.get("justified_non_promotion", False))
        if not justified and "justified" not in comparison.justification.lower():
            return False
    return True


def validate_risk_not_underestimated(score: Any, policy: Any = None) -> bool:
    """
    Validates that the route risk is not underestimated.
    """
    if getattr(score, "risk_underestimated", False):
        return False
    if not getattr(score, "passed_policy_bounds", True):
        return False
    return True

