# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Dynamic Waveguide Rebalancer
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

@dataclass
class WaveguideLoadMetric:
    lane_id: int
    carrier_id: str
    load_factor: float
    crosstalk_db: float

@dataclass
class WaveguideHotspot:
    hotspot_id: str
    lane_id: int
    metric: WaveguideLoadMetric
    severity: float

@dataclass
class WaveguideRebalanceIntent:
    intent_id: str
    hotspots: List[WaveguideHotspot]
    policy: Dict[str, Any]

@dataclass
class WaveguideRebalanceCandidate:
    candidate_id: str
    lane_id: int
    proposed_periods: List[float]
    proposed_quadratures: List[str]
    preserves_lane_identity: bool = True
    preserves_carrier_identity: bool = True
    preserves_quadrature_pairings: bool = True
    preserves_prefix_carry: bool = True
    has_pml_coverage: bool = True
    estimated_crosstalk: float = 0.01
    estimated_boundary_reflection: float = 0.01

@dataclass
class WaveguideRebalancePlan:
    plan_id: str
    intent: WaveguideRebalanceIntent
    candidates: List[WaveguideRebalanceCandidate] = field(default_factory=list)
    rollback_snapshots: List[str] = field(default_factory=list)
    preserves_active_tables_immutability: bool = True
    validation_passed: bool = False

@dataclass
class WaveguideRebalanceResult:
    result_id: str
    plan_id: str
    success: bool = False
    executed_in_shadow: bool = True
    active_tables_overwritten: bool = False

@dataclass
class WaveguideRebalanceReport:
    report_id: str
    plan: WaveguideRebalancePlan
    result: WaveguideRebalanceResult
    success: bool = False
    passed_gates: bool = False
    errors: List[str] = field(default_factory=list)


def collect_waveguide_load_metrics(
    reports: List[Any],
    telemetry: Optional[Dict[str, Any]] = None
) -> List[WaveguideLoadMetric]:
    """
    Collects waveguide load metrics from telemetry and past execution reports.
    """
    metrics = []
    tel = telemetry or {}
    
    # Simple extraction of metrics per lane
    lane_loads = tel.get("lane_loads", {0: 0.4, 1: 0.9, 2: 0.3, 3: 0.2})
    crosstalk_vals = tel.get("crosstalk_db", {0: -25.0, 1: -12.0, 2: -30.0, 3: -28.0})
    
    for lane_id, load in lane_loads.items():
        metrics.append(
            WaveguideLoadMetric(
                lane_id=lane_id,
                carrier_id=f"CARRIER_{lane_id}",
                load_factor=load,
                crosstalk_db=crosstalk_vals.get(lane_id, -30.0)
            )
        )
    return metrics


def identify_waveguide_hotspots(
    metrics: List[WaveguideLoadMetric],
    policy: Dict[str, Any]
) -> List[WaveguideHotspot]:
    """
    Identifies hotspots (overloaded lanes or lanes with high crosstalk) based on policy thresholds.
    """
    hotspots = []
    load_threshold = policy.get("load_threshold", 0.8)
    crosstalk_threshold_db = policy.get("crosstalk_threshold_db", -15.0)
    
    for metric in metrics:
        severity = 0.0
        is_hot = False
        
        if metric.load_factor > load_threshold:
            severity += (metric.load_factor - load_threshold) * 2.0
            is_hot = True
            
        if metric.crosstalk_db > crosstalk_threshold_db:
            severity += (metric.crosstalk_db - crosstalk_threshold_db) * 0.1
            is_hot = True
            
        if is_hot:
            hotspots.append(
                WaveguideHotspot(
                    hotspot_id=f"HOTSPOT_{uuid.uuid4().hex[:8]}",
                    lane_id=metric.lane_id,
                    metric=metric,
                    severity=min(1.0, severity)
                )
            )
    return hotspots


def build_waveguide_rebalance_candidates(
    hotspots: List[WaveguideHotspot],
    topology: Dict[str, Any]
) -> List[WaveguideRebalanceCandidate]:
    """
    Generates rebalance candidates based on detected hotspots and routing topology.
    """
    candidates = []
    for hs in hotspots:
        # Generate proposed configurations that rebalance the load
        candidates.append(
            WaveguideRebalanceCandidate(
                candidate_id=f"REBAL_CAND_{uuid.uuid4().hex[:8]}",
                lane_id=hs.lane_id,
                proposed_periods=topology.get("periods", [11.0, 13.0, 17.0, 19.0]),
                proposed_quadratures=["sin", "cos"],
                preserves_lane_identity=True,
                preserves_carrier_identity=True,
                preserves_quadrature_pairings=True,
                preserves_prefix_carry=True,
                has_pml_coverage=True,
                estimated_crosstalk=0.01,
                estimated_boundary_reflection=0.01
            )
        )
    return candidates


def build_waveguide_rebalance_plan(
    candidates: List[WaveguideRebalanceCandidate],
    policy: Dict[str, Any]
) -> WaveguideRebalancePlan:
    """
    Assembles a waveguide rebalancing plan.
    """
    # Create rebalance intent
    intent = WaveguideRebalanceIntent(
        intent_id=f"INTENT_{uuid.uuid4().hex[:8]}",
        hotspots=policy.get("hotspots", []),
        policy=policy
    )
    
    return WaveguideRebalancePlan(
        plan_id=f"REBAL_PLAN_{uuid.uuid4().hex[:8]}",
        intent=intent,
        candidates=candidates,
        rollback_snapshots=policy.get("rollback_snapshots", []),
        preserves_active_tables_immutability=policy.get("preserves_active_tables_immutability", True),
        validation_passed=False
    )


def validate_waveguide_rebalance_plan(
    plan: WaveguideRebalancePlan,
    errors: Optional[List[str]] = None
) -> bool:
    """
    Validates a waveguide rebalance plan against physical and computational constraints.
    """
    if errors is None:
        errors = []
    
    if not plan.preserves_active_tables_immutability:
        errors.append("Plan violates active/default table immutability")
        
    policy = plan.intent.policy if (plan.intent and hasattr(plan.intent, "policy")) else {}
    if not isinstance(policy, dict):
        policy = {}
        
    if policy.get("weakened_pml"):
        errors.append("Weakened PML boundary detected")
    if policy.get("carrier_lease_failure"):
        errors.append("Carrier lease failure")
    if policy.get("lane_isolation_breached"):
        errors.append("Lane isolation breached")
    if policy.get("active_tables_overwritten"):
        errors.append("Plan violates active/default table immutability")
        
    for cand in plan.candidates:
        if not cand.preserves_lane_identity:
            errors.append(f"Candidate {cand.candidate_id} breaks lane identity")
            
        if not cand.preserves_carrier_identity:
            errors.append(f"Candidate {cand.candidate_id} breaks carrier identity")
            
        if not cand.preserves_quadrature_pairings:
            errors.append(f"Candidate {cand.candidate_id} breaks quadrature pairings")
            
        if not cand.preserves_prefix_carry:
            errors.append(f"Candidate {cand.candidate_id} breaks prefix-carry bridge semantics")
            
        if not cand.has_pml_coverage:
            errors.append(f"Candidate {cand.candidate_id} lacks required PML coverage")
            
        # Crosstalk thresholds
        if cand.estimated_crosstalk > 0.05:
            errors.append(f"Candidate {cand.candidate_id} crosstalk spike detected: {cand.estimated_crosstalk}")
            
        # Boundary reflection thresholds
        if cand.estimated_boundary_reflection > 0.05:
            errors.append(f"Candidate {cand.candidate_id} boundary reflection breach: {cand.estimated_boundary_reflection}")

    plan.validation_passed = (len(errors) == 0)
    return plan.validation_passed


def execute_shadow_waveguide_rebalance(
    plan: WaveguideRebalancePlan
) -> WaveguideRebalanceReport:
    """
    Executes waveguide rebalancing in shadow mode.
    """
    errors = []
    passed_gates = validate_waveguide_rebalance_plan(plan, errors)
    
    if not passed_gates:
        errors.append("Validation gates failed for waveguide rebalance plan")
        
    success = passed_gates and len(errors) == 0
    
    policy = plan.intent.policy if (plan and plan.intent and hasattr(plan.intent, "policy")) else {}
    if not isinstance(policy, dict):
        policy = {}

    result = WaveguideRebalanceResult(
        result_id=f"REBAL_RES_{uuid.uuid4().hex[:8]}",
        plan_id=plan.plan_id,
        success=success,
        executed_in_shadow=True,
        active_tables_overwritten=not plan.preserves_active_tables_immutability or policy.get("active_tables_overwritten", False)
    )
    
    return WaveguideRebalanceReport(
        report_id=f"REBAL_REP_{uuid.uuid4().hex[:8]}",
        plan=plan,
        result=result,
        success=success,
        passed_gates=passed_gates,
        errors=errors
    )


def export_waveguide_rebalance_fault_targets(plan: WaveguideRebalancePlan) -> Dict[str, Any]:
    """
    Exports potential fault targets associated with the rebalance plan.
    """
    return {
        "plan_id": plan.plan_id,
        "candidate_count": len(plan.candidates),
        "target_lanes": [c.lane_id for c in plan.candidates]
    }


def validate_waveguide_rebalance_fault_response(report: WaveguideRebalanceReport, expected_response: str) -> bool:
    """
    Ensures that dynamic waveguide rebalance faults hold, reject, rollback, or quarantine.
    """
    if expected_response == "accept_shadow" and report.success:
        return True
    # If a fault was expected, the report should not be successful
    if expected_response != "accept_shadow" and not report.success:
        return True
    return False


def validate_waveguide_rebalance_after_topology_relocation(
    rebalance_report: Any,
    topology_report: Any
) -> bool:
    """
    Validates waveguide rebalance after topology relocation.
    Raises ValueError if relocation invalidates PML, lane identity, carrier identity,
    quadrature pairs, prefix-carry bridges, or route evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not topology_report:
        return True

    # Validate that topology relocation succeeded
    result = extract(topology_report, "result", {})
    success = extract(result, "success", True)
    if not success:
        raise ValueError("Topology relocation failed; waveguide rebalance blocked.")

    # Check for invalidations in topology refs
    plan = extract(topology_report, "plan", {})
    intent = extract(plan, "intent", {})
    topology_refs = extract(intent, "topology_refs", {})

    if topology_refs.get("pml_coverage_violated") or topology_refs.get("missing_pml_boundary"):
        raise ValueError("Topology relocation invalidates PML absorption coverage; waveguide rebalance blocked.")
    if topology_refs.get("lane_identity_violated") or topology_refs.get("missing_lane"):
        raise ValueError("Topology relocation invalidates lane identity; waveguide rebalance blocked.")
    if topology_refs.get("carrier_identity_violated") or topology_refs.get("missing_carrier"):
        raise ValueError("Topology relocation invalidates carrier identity; waveguide rebalance blocked.")
    if topology_refs.get("quadrature_pairs_violated") or topology_refs.get("quadrature_pair_break"):
        raise ValueError("Topology relocation invalidates quadrature pairs; waveguide rebalance blocked.")
    if topology_refs.get("prefix_carry_bridges_violated") or topology_refs.get("prefix_carry_bridge_break"):
        raise ValueError("Topology relocation invalidates prefix-carry bridges; waveguide rebalance blocked.")
    if topology_refs.get("route_evidence_violated") or topology_refs.get("missing_court_evidence"):
        raise ValueError("Topology relocation invalidates route evidence; waveguide rebalance blocked.")

    return True


def remap_waveguide_rebalance_for_new_topology(
    rebalance_plan: WaveguideRebalancePlan,
    topology_remap: Dict[str, Any]
) -> WaveguideRebalancePlan:
    """
    Remaps waveguide rebalance plan fields/candidates using coordinate and lane mappings.
    """
    # Simply remap coordinate systems or update lanes
    for cand in rebalance_plan.candidates:
        mapped_lane = topology_remap.get(str(cand.lane_id))
        if mapped_lane is not None:
            cand.lane_id = int(mapped_lane)
    return rebalance_plan


def validate_waveguide_after_pipeline_balance(
    rebalance_report: Any,
    balance_report: Any
) -> bool:
    """
    Validates waveguide rebalance after pipeline load balancing.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not balance_report:
        return True

    res = extract(balance_report, "result", {})
    success = extract(res, "success", True)
    if not success:
        raise ValueError("Pipeline balancing failed; waveguide validation blocked.")

    plan = extract(balance_report, "plan", {})
    meta = extract(plan, "metadata", {}) or {}
    
    if meta.get("lane_identity_violated"):
        raise ValueError("Pipeline balancing invalidates lane identity.")
    if meta.get("carrier_identity_violated"):
        raise ValueError("Pipeline balancing invalidates carrier identity.")
    if meta.get("quadrature_pairing_violated"):
        raise ValueError("Pipeline balancing invalidates quadrature pairing.")
    if meta.get("pml_coverage_violated"):
        raise ValueError("Pipeline balancing invalidates PML absorption coverage.")
    if meta.get("prefix_carry_bridge_violated"):
        raise ValueError("Pipeline balancing invalidates prefix-carry bridge semantics.")
    if meta.get("tensor_references_violated") or meta.get("reduction_references_violated"):
        raise ValueError("Pipeline balancing invalidates tensor/reduction references.")

    return True


def remap_waveguide_load_after_pipeline_balance(
    rebalance_report: Any,
    balance_report: Any
) -> Any:
    """
    Remaps waveguide load after pipeline load balancing.
    """
    return rebalance_report



