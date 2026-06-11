# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Shard Boundary Calibration
==============================
Manages shard boundary groups, drift measurement, and boundary calibration plans.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import math

@dataclass
class ShardBoundaryGroup:
    group_id: str
    shards: List[str] = field(default_factory=list)
    boundaries: List[str] = field(default_factory=list)

@dataclass
class ShardBoundaryCalibrationTarget:
    target_id: str
    group: ShardBoundaryGroup
    target_channel: Optional[Any] = None

@dataclass
class ShardBoundaryDriftReport:
    report_id: str
    group_id: str
    phase_drift: float
    global_phase_skew: float
    crosstalk: float
    boundary_reflection: float
    active_mass_preserved: bool
    lane_consistency: float
    route_stability: float
    pml_absorption_effectiveness: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class ShardBoundaryCalibrationPlan:
    plan_id: str
    target: ShardBoundaryCalibrationTarget
    drift_report: ShardBoundaryDriftReport
    policy: Any
    candidate_phase_table: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ShardBoundaryCalibrationReport:
    report_id: str
    plan: ShardBoundaryCalibrationPlan
    success: bool
    final_drift_report: ShardBoundaryDriftReport
    errors: List[str] = field(default_factory=list)


def collect_shard_boundary_groups(topology: Any) -> List[ShardBoundaryGroup]:
    """
    Groups boundary points by independent shard boundaries from shard topology.
    """
    groups = []
    shards = getattr(topology, "shards", []) or (topology.get("shards", []) if isinstance(topology, dict) else [])
    
    if not shards:
        # Create default mock groups if topology is empty/unspecified
        groups.append(ShardBoundaryGroup(
            group_id="SBG_DEFAULT_0",
            shards=["shard_0"],
            boundaries=["bnd_0"]
        ))
    else:
        # Partition shards into groups (e.g. up to 2 shards per group)
        current_shards = []
        current_bnds = []
        group_idx = 0
        
        for i, s in enumerate(shards):
            s_id = getattr(s, "shard_id", None) or (s.get("shard_id") if isinstance(s, dict) else str(s))
            current_shards.append(s_id)
            current_bnds.append(f"bnd_{s_id}")
            
            if len(current_shards) >= 2 or i == len(shards) - 1:
                groups.append(ShardBoundaryGroup(
                    group_id=f"SBG_{group_idx}",
                    shards=list(current_shards),
                    boundaries=list(current_bnds)
                ))
                current_shards.clear()
                current_bnds.clear()
                group_idx += 1
                
    return groups


def measure_boundary_group_drift(group: ShardBoundaryGroup, telemetry: Any) -> ShardBoundaryDriftReport:
    """
    Aggregates and measures phase drift, skew, crosstalk, and boundary reflections across group.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # Read telemetry metrics or use safe defaults
    drift = extract(telemetry, "phase_drift", 0.01)
    skew = extract(telemetry, "phase_skew", 0.01)
    crosstalk = extract(telemetry, "crosstalk", 0.01)
    reflection = extract(telemetry, "boundary_reflection", 0.01)
    mass_preserved = extract(telemetry, "active_mass_preserved", True)
    lane_cons = extract(telemetry, "lane_consistency", 1.0)
    route_stab = extract(telemetry, "route_stability", 1.0)
    pml_eff = extract(telemetry, "pml_absorption_effectiveness", 0.98)

    # Simulated override via metadata
    meta = extract(telemetry, "metadata", {}) or {}
    if meta.get("high_skew") or meta.get("drift_breach"):
        drift = 0.12
        skew = 0.12
    if meta.get("high_crosstalk") or meta.get("crosstalk_breach"):
        crosstalk = 0.15
    if meta.get("high_reflection") or meta.get("reflection_breach"):
        reflection = 0.10

    report_id = f"SBDRIFT_{group.group_id}_{int(time.time())}"
    return ShardBoundaryDriftReport(
        report_id=report_id,
        group_id=group.group_id,
        phase_drift=drift,
        global_phase_skew=skew,
        crosstalk=crosstalk,
        boundary_reflection=reflection,
        active_mass_preserved=mass_preserved,
        lane_consistency=lane_cons,
        route_stability=route_stab,
        pml_absorption_effectiveness=pml_eff
    )


def plan_boundary_group_calibration(
    group: ShardBoundaryGroup,
    drift_report: ShardBoundaryDriftReport,
    policy: Any
) -> ShardBoundaryCalibrationPlan:
    """
    Generates calibration adjustment plan, including candidate phase table offsets.
    """
    from sol_phase_alignment import build_default_phase_table, apply_candidate_phase_correction, PhaseAlignmentTable
    
    target = ShardBoundaryCalibrationTarget(
        target_id=f"TGT_{group.group_id}",
        group=group,
        target_channel=(11.0, "sin")
    )

    # Initialize a candidate phase table (separate from default phase tables)
    raw_table = build_default_phase_table(lane_id=0, periods=[11.0, 13.0, 17.0, 19.0])
    
    # Calculate bounded phase correction suggestion
    max_phase_nudge = getattr(policy, "max_phase_nudge", 0.05) if policy else 0.05
    nudge = -0.5 * drift_report.phase_drift
    clamped_nudge = max(-max_phase_nudge, min(max_phase_nudge, nudge))

    @dataclass
    class MockCorrection:
        target_channel: Any
        bounded_delta: float
        target_lane: int

    corr = MockCorrection(target_channel=(11.0, "sin"), bounded_delta=clamped_nudge, target_lane=0)
    candidate_table = apply_candidate_phase_correction(raw_table, corr)

    plan_id = f"SBCALPLAN_{group.group_id}_{int(time.time())}"
    return ShardBoundaryCalibrationPlan(
        plan_id=plan_id,
        target=target,
        drift_report=drift_report,
        policy=policy,
        candidate_phase_table=candidate_table
    )


def execute_shadow_boundary_calibration(
    plan: ShardBoundaryCalibrationPlan
) -> ShardBoundaryCalibrationReport:
    """
    Simulates applying the calibration plan and generates an execution report.
    Checks stability invariants:
    - Phase drift within threshold
    - Crosstalk within threshold
    - Boundary reflection within threshold
    """
    errors = []
    success = True
    
    report = plan.drift_report
    
    # Check threshold limits
    if report.phase_drift > 0.10:
        errors.append("Unstable calibration loop: phase drift exceeded safety limits.")
        success = False
        
    if report.crosstalk > 0.05:
        errors.append("Unstable calibration loop: high crosstalk detected.")
        success = False
        
    if report.boundary_reflection > 0.05:
        errors.append("Unstable calibration loop: boundary reflection breach.")
        success = False

    # Simulate final drift report after calibration correction
    final_drift = report.phase_drift * 0.5  # drift is reduced by 50%
    final_skew = report.global_phase_skew * 0.5
    final_crosstalk = report.crosstalk
    final_reflection = report.boundary_reflection

    final_report = ShardBoundaryDriftReport(
        report_id=f"SBDRIFT_POST_{plan.target.group.group_id}_{int(time.time())}",
        group_id=plan.target.group.group_id,
        phase_drift=final_drift,
        global_phase_skew=final_skew,
        crosstalk=final_crosstalk,
        boundary_reflection=final_reflection,
        active_mass_preserved=report.active_mass_preserved,
        lane_consistency=report.lane_consistency,
        route_stability=report.route_stability,
        pml_absorption_effectiveness=report.pml_absorption_effectiveness
    )

    report_id = f"SBCALREP_{plan.plan_id}"
    return ShardBoundaryCalibrationReport(
        report_id=report_id,
        plan=plan,
        success=success and (len(errors) == 0),
        final_drift_report=final_report,
        errors=errors
    )
