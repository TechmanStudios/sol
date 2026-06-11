# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Geodesic Pipeline Balancer
==============================
Balances workload across pipeline segments in shadow/sandbox mode.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class GeodesicPipelineBalancePolicy:
    max_imbalance_threshold: float = 0.1
    allow_shadow_balance: bool = True
    court_token_required: bool = True
    rollback_required: bool = True

@dataclass
class GeodesicPipelineSegment:
    segment_id: str
    stage_name: str
    core_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeodesicPipelineLoadMetric:
    segment_id: str
    queue_depth: int = 0
    latency: float = 0.0
    stall_time: float = 0.0
    reduction_wait: float = 0.0
    consensus_wait: float = 0.0
    lock_wait: float = 0.0
    route_depth: int = 0
    waveguide_load: float = 0.0
    cadence_skew: float = 0.0
    wavefront_drift: float = 0.0
    crosstalk: float = 0.0
    reflection: float = 0.0
    rollback_complexity: int = 0

@dataclass
class GeodesicPipelineImbalance:
    segment_id: str
    imbalance_score: float

@dataclass
class GeodesicPipelineBalancePlan:
    plan_id: str
    policy: GeodesicPipelineBalancePolicy
    imbalances: List[GeodesicPipelineImbalance]
    adjustments: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeodesicPipelineBalanceResult:
    success: bool
    errors: List[str] = field(default_factory=list)
    adjusted_segments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeodesicPipelineBalanceReport:
    report_id: str
    plan: GeodesicPipelineBalancePlan
    result: GeodesicPipelineBalanceResult
    timestamp: float = field(default_factory=time.time)


def collect_geodesic_pipeline_metrics(
    pipeline_report: Optional[Any] = None,
    route_report: Optional[Any] = None,
    core_assembly_report: Optional[Any] = None
) -> List[GeodesicPipelineLoadMetric]:
    """
    Collects load metrics for geodesic pipeline segments.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # Use defaults if reports are not provided (useful for mock setups in tests)
    segment_ids = ["seg_0", "seg_1", "seg_2"]
    if pipeline_report:
        # Extract segments if available
        segs = extract(pipeline_report, "segments", [])
        if segs:
            segment_ids = [extract(s, "segment_id", f"seg_{i}") for i, s in enumerate(segs)]

    metrics = []
    for sid in segment_ids:
        # Defaults
        queue_depth = 1
        latency = 0.02
        stall_time = 0.01
        reduction_wait = 0.01
        consensus_wait = 0.01
        lock_wait = 0.01
        route_depth = 2
        waveguide_load = 0.1
        cadence_skew = 0.02
        wavefront_drift = 0.01
        crosstalk = 0.01
        reflection = 0.01
        rollback_complexity = 1

        # Populate from reports if available
        if pipeline_report:
            p_data = extract(pipeline_report, "metrics", {}).get(sid, {})
            if p_data:
                queue_depth = extract(p_data, "queue_depth", queue_depth)
                latency = extract(p_data, "latency", latency)
                stall_time = extract(p_data, "stall_time", stall_time)
                reduction_wait = extract(p_data, "reduction_wait", reduction_wait)
                consensus_wait = extract(p_data, "consensus_wait", consensus_wait)
                lock_wait = extract(p_data, "lock_wait", lock_wait)

        if route_report:
            r_data = extract(route_report, "metrics", {}).get(sid, {})
            if r_data:
                route_depth = extract(r_data, "route_depth", route_depth)
                waveguide_load = extract(r_data, "waveguide_load", waveguide_load)
                crosstalk = extract(r_data, "crosstalk", crosstalk)
                reflection = extract(r_data, "reflection", reflection)

        if core_assembly_report:
            c_data = extract(core_assembly_report, "metrics", {}).get(sid, {})
            if c_data:
                cadence_skew = extract(c_data, "cadence_skew", cadence_skew)
                wavefront_drift = extract(c_data, "wavefront_drift", wavefront_drift)

        metrics.append(GeodesicPipelineLoadMetric(
            segment_id=sid,
            queue_depth=queue_depth,
            latency=latency,
            stall_time=stall_time,
            reduction_wait=reduction_wait,
            consensus_wait=consensus_wait,
            lock_wait=lock_wait,
            route_depth=route_depth,
            waveguide_load=waveguide_load,
            cadence_skew=cadence_skew,
            wavefront_drift=wavefront_drift,
            crosstalk=crosstalk,
            reflection=reflection,
            rollback_complexity=rollback_complexity
        ))

    return metrics


def detect_geodesic_pipeline_imbalance(
    metrics: List[GeodesicPipelineLoadMetric],
    policy: GeodesicPipelineBalancePolicy
) -> List[GeodesicPipelineImbalance]:
    """
    Detects imbalances across pipeline segments based on metrics and policy threshold.
    """
    if not metrics:
        return []

    # Calculate average queue depth and latency
    avg_queue = sum(m.queue_depth for m in metrics) / len(metrics)
    avg_latency = sum(m.latency for m in metrics) / len(metrics)

    imbalances = []
    for m in metrics:
        # imbalance score = sum of relative deviations
        qd_dev = abs(m.queue_depth - avg_queue) / (avg_queue if avg_queue > 0 else 1.0)
        lat_dev = abs(m.latency - avg_latency) / (avg_latency if avg_latency > 0 else 1.0)
        
        # add extra weights for stalls or drift
        extra_score = m.stall_time + m.cadence_skew + m.wavefront_drift
        score = qd_dev + lat_dev + extra_score
        
        if score > policy.max_imbalance_threshold:
            imbalances.append(GeodesicPipelineImbalance(
                segment_id=m.segment_id,
                imbalance_score=score
            ))

    return imbalances


def build_geodesic_pipeline_balance_plan(
    imbalances: List[GeodesicPipelineImbalance],
    policy: GeodesicPipelineBalancePolicy
) -> GeodesicPipelineBalancePlan:
    """
    Creates a plan to balance pipeline load. Rejects unbounded/invalid policies.
    """
    if policy.max_imbalance_threshold <= 0:
        raise ValueError("Unbounded policy max_imbalance_threshold: must be greater than 0.")

    adjustments = {}
    for imb in imbalances:
        # Adjust load by reducing queue depth or shifting segments
        adjustments[imb.segment_id] = {
            "shift_factor": -0.1 if imb.imbalance_score > 0.5 else -0.05,
            "target_core": "core_backup",
            "rollback_ref": f"snap_{uuid.uuid4().hex[:6]}"
        }

    return GeodesicPipelineBalancePlan(
        plan_id=f"BAL_PLAN_{uuid.uuid4().hex[:8]}",
        policy=policy,
        imbalances=imbalances,
        adjustments=adjustments,
        metadata={"rollback_snapshot": f"rollback_{uuid.uuid4().hex[:6]}"}
    )


def validate_geodesic_pipeline_balance_plan(plan: GeodesicPipelineBalancePlan) -> bool:
    """
    Validates balance plan validity and rollback references.
    """
    if not plan.policy:
        raise ValueError("Invalid balance plan: policy is missing.")
    if plan.policy.max_imbalance_threshold <= 0:
        raise ValueError("Invalid balance plan: policy max_imbalance_threshold is invalid.")
    if not plan.metadata.get("rollback_snapshot"):
        raise ValueError("Invalid balance plan: missing rollback snapshot.")
    return True


def execute_shadow_geodesic_pipeline_balance(
    plan: GeodesicPipelineBalancePlan
) -> GeodesicPipelineBalanceReport:
    """
    Executes a dry-run balance in shadow mode.
    """
    errors = []
    adjusted_segments = []

    try:
        validate_geodesic_pipeline_balance_plan(plan)
        # execute
        for sid in plan.adjustments:
            adjusted_segments.append(sid)
    except ValueError as e:
        errors.append(str(e))

    success = len(errors) == 0

    # check if any specific segment has invalid config or quarantine flags
    if plan.metadata.get("quarantine_segment"):
        errors.append(f"Segment {plan.metadata['quarantine_segment']} is quarantined.")
        success = False

    result = GeodesicPipelineBalanceResult(
        success=success,
        errors=errors,
        adjusted_segments=adjusted_segments,
        metadata={"timestamp": time.time()}
    )

    return GeodesicPipelineBalanceReport(
        report_id=f"BAL_REP_{uuid.uuid4().hex[:8]}",
        plan=plan,
        result=result
    )


def compare_pipeline_balance_before_after(
    before: List[GeodesicPipelineLoadMetric],
    after: List[GeodesicPipelineLoadMetric]
) -> Dict[str, Any]:
    """
    Compares load metrics before and after balancing to check for improvement.
    """
    before_tot_lat = sum(m.latency for m in before)
    after_tot_lat = sum(m.latency for m in after)
    
    before_tot_stalls = sum(m.stall_time for m in before)
    after_tot_stalls = sum(m.stall_time for m in after)

    improved = (after_tot_lat < before_tot_lat) or (after_tot_stalls < before_tot_stalls)

    return {
        "improved": improved,
        "before_latency": before_tot_lat,
        "after_latency": after_tot_lat,
        "before_stalls": before_tot_stalls,
        "after_stalls": after_tot_stalls
    }


def export_pipeline_balance_fault_targets(balance_plan: GeodesicPipelineBalancePlan) -> List[str]:
    """
    Exports target pipeline segment IDs that can be targeted for fault injection.
    """
    if not balance_plan:
        return []
    return [imb.segment_id for imb in balance_plan.imbalances] or ["seg_default"]


def validate_pipeline_balance_against_fault_matrix(
    balance_report: GeodesicPipelineBalanceReport,
    matrix_report: Any
) -> bool:
    """
    Validates that the pipeline balance handles/blocks when there are failures in the fault matrix.
    """
    # If fault matrix failed to audit successfully, balance report cannot be accepted for promotion
    passed = getattr(matrix_report, "passed_audit", True)
    if not passed:
        return False
    return True


def export_pipeline_balance_metrics_for_burnin(report: GeodesicPipelineBalanceReport) -> Dict[str, Any]:
    """
    Exports pipeline balancing stability metrics for burn-in monitoring.
    """
    if not report or not report.result:
        return {"stage_latency": 0.05, "backpressure": 0.01, "cross_core_stalls": 0.0}
        
    meta = report.result.metadata or {}
    return {
        "stage_latency": float(meta.get("stage_latency", 0.05)),
        "backpressure": float(meta.get("backpressure", 0.01)),
        "cross_core_stalls": float(meta.get("cross_core_stalls", 0.0))
    }


def validate_pipeline_balance_over_burnin(metric_window: Any) -> bool:
    """
    Validates that pipeline balance metrics do not show critical regression without justification.
    """
    metrics = getattr(metric_window, "metrics", {}) or {}
    
    # Check if stage latency increases by more than 50% from start to end of window
    latency = metrics.get("stage_latency")
    if latency and hasattr(latency, "values") and len(latency.values) >= 2:
        start_val = latency.values[0]
        end_val = latency.values[-1]
        if start_val > 0 and (end_val - start_val) / start_val > 0.5:
            return False
            
    return True

