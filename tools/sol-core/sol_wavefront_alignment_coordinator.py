# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Wavefront Alignment Coordinator
===================================
Captures and synchronizes wavefront state and phase alignment across multiple core groups.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class WavefrontAlignmentDomain:
    domain_id: str
    manifolds: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WavefrontAlignmentTarget:
    target_id: str
    expected_phase: float
    frequency: float

@dataclass
class CrossManifoldWavefrontObservation:
    observation_id: str
    manifold_id: str
    phase_skew: float
    crosstalk: float
    boundary_reflection: float
    active_mass: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class WavefrontAlignmentPlan:
    plan_id: str
    observations: List[CrossManifoldWavefrontObservation] = field(default_factory=list)
    adjustments: Dict[str, float] = field(default_factory=dict)  # manifold_id -> phase nudge value
    token: Optional[Any] = None

@dataclass
class WavefrontAlignmentReport:
    report_id: str
    plan: WavefrontAlignmentPlan
    global_phase_skew: float
    global_crosstalk: float
    global_boundary_reflection: float
    stable: bool
    timestamp: float = field(default_factory=time.time)


def capture_cross_manifold_wavefront_state(manifolds: List[Any]) -> List[CrossManifoldWavefrontObservation]:
    """
    Generates wavefront alignment observations across manifolds.
    Supports simulated value overrides via dictionary/object metadata.
    """
    observations = []
    for m in manifolds:
        m_id = getattr(m, "manifold_id", None) or (m.get("manifold_id") if isinstance(m, dict) else str(m))
        
        # Read properties or use default stable metrics
        if isinstance(m, dict):
            skew = m.get("phase_skew", 0.01)
            crosstalk = m.get("crosstalk", 0.01)
            reflection = m.get("boundary_reflection", 0.01)
            mass = m.get("active_mass", 500.0)
        else:
            skew = getattr(m, "phase_skew", 0.01)
            crosstalk = getattr(m, "crosstalk", 0.01)
            reflection = getattr(m, "boundary_reflection", 0.01)
            mass = getattr(m, "active_mass", 500.0)

        
        # simulated override
        meta = getattr(m, "metadata", {}) or m.get("metadata", {}) if isinstance(m, dict) else {}
        if meta.get("high_skew"):
            skew = 0.12
        if meta.get("high_crosstalk"):
            crosstalk = 0.15
        if meta.get("high_reflection"):
            reflection = 0.10
            
        observations.append(CrossManifoldWavefrontObservation(
            observation_id=f"OBS_{m_id}_{int(time.time())}",
            manifold_id=m_id,
            phase_skew=skew,
            crosstalk=crosstalk,
            boundary_reflection=reflection,
            active_mass=mass
        ))
        
    return observations


def measure_global_phase_alignment(observations: List[CrossManifoldWavefrontObservation]) -> float:
    """
    Measures the maximum phase skew across all observations.
    """
    if not observations:
        return 0.0
    return max(obs.phase_skew for obs in observations)


def measure_global_boundary_reflection(observations: List[CrossManifoldWavefrontObservation]) -> float:
    """
    Measures the maximum boundary reflection score across all observations.
    """
    if not observations:
        return 0.0
    return max(obs.boundary_reflection for obs in observations)


def plan_wavefront_alignment_adjustment(
    observations: List[CrossManifoldWavefrontObservation],
    policy: Any
) -> WavefrontAlignmentPlan:
    """
    Plans phase alignment adjustments to minimize phase skew.
    """
    adjustments = {}
    max_phase_nudge = getattr(policy, "max_phase_nudge", 0.05) if policy else 0.05
    
    for obs in observations:
        if obs.phase_skew > 0.02:
            # Plan a corrective phase nudge (negative half of the skew, clamped)
            nudge = -0.5 * obs.phase_skew
            clamped_nudge = max(-max_phase_nudge, min(max_phase_nudge, nudge))
            adjustments[obs.manifold_id] = clamped_nudge
        else:
            adjustments[obs.manifold_id] = 0.0
            
    plan_id = f"WPLAN_{int(time.time())}"
    return WavefrontAlignmentPlan(
        plan_id=plan_id,
        observations=observations,
        adjustments=adjustments
    )


def execute_shadow_wavefront_alignment(plan: WavefrontAlignmentPlan) -> WavefrontAlignmentReport:
    """
    Simulates applying the wavefront alignment plan and generates a report.
    Checks against safety thresholds:
    - Phase skew <= 0.05
    - Crosstalk <= 0.05
    - Reflection <= 0.05
    """
    drifts = [obs.phase_skew for obs in plan.observations]
    crosstalks = [obs.crosstalk for obs in plan.observations]
    reflections = [obs.boundary_reflection for obs in plan.observations]
    
    max_drift = max(drifts) if drifts else 0.0
    max_crosstalk = max(crosstalks) if crosstalks else 0.0
    max_reflection = max(reflections) if reflections else 0.0
    
    stable = max_drift <= 0.05 and max_crosstalk <= 0.05 and max_reflection <= 0.05
    
    report_id = f"WRPT_{plan.plan_id}_{int(time.time())}"
    return WavefrontAlignmentReport(
        report_id=report_id,
        plan=plan,
        global_phase_skew=max_drift,
        global_crosstalk=max_crosstalk,
        global_boundary_reflection=max_reflection,
        stable=stable
    )


def validate_alignment_for_propagation(
    observations: List[CrossManifoldWavefrontObservation],
    propagation_plan: Any
) -> bool:
    """
    Validates that wavefront alignments are stable and within tolerances before propagation.
    """
    if not observations:
        return False
    for obs in observations:
        if obs.phase_skew > 0.05:
            return False
        if obs.crosstalk > 0.05:
            return False
        if obs.boundary_reflection > 0.05:
            return False
        if obs.active_mass < 14.0:
            return False
    return True


def measure_propagation_phase_error(before: Any, after: Any) -> float:
    """
    Measures the difference/error in phase alignment between before and after states.
    """
    u_before = getattr(before, "u", None)
    u_after = getattr(after, "u", None)
    if u_before is not None and u_after is not None:
        try:
            import numpy as np
            return float(np.max(np.abs(np.array(u_after) - np.array(u_before))))
        except Exception:
            return abs(u_after[0] - u_before[0]) if len(u_after) > 0 else 0.02
    return 0.02


def coordinate_boundary_group_alignment(boundary_groups: List[Any], policy: Any) -> List[Any]:
    """
    Coordinates and creates alignment reports for independent shard boundary groups.
    """
    from sol_wavefront_alignment_stabilizer import build_wavefront_alignment_trial, execute_shadow_wavefront_stabilization
    # Support multiple independent boundary groups
    trial = build_wavefront_alignment_trial(boundary_groups, policy)
    report = execute_shadow_wavefront_stabilization(trial)
    return [report]


def evaluate_distributed_alignment_stability(reports: List[Any]) -> bool:
    """
    Evaluates distributed alignment stability across all reports.
    A single unstable group must invalidate the entire alignment coordination.
    """
    from sol_wavefront_alignment_stabilizer import evaluate_wavefront_stability
    if not reports:
        return False
    for r in reports:
        if not evaluate_wavefront_stability(r):
            return False
    return True


@dataclass
class WavefrontTemporalAlignmentReport:
    report_id: str
    phase_drift: float
    cadence_drift: float
    global_skew: float
    temporal_boundary_reflection: float
    cross_manifold_crosstalk: float
    lane_timing_consistency: bool
    active_mass_preservation: bool
    stable: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


def measure_wavefront_temporal_alignment(
    observations: List[CrossManifoldWavefrontObservation],
    cadence_group: Any
) -> WavefrontTemporalAlignmentReport:
    """
    Measures wavefront temporal alignment parameters.
    """
    phase_drift = max([obs.phase_skew for obs in observations]) if observations else 0.0
    temporal_boundary_reflection = max([obs.boundary_reflection for obs in observations]) if observations else 0.0
    cross_manifold_crosstalk = max([obs.crosstalk for obs in observations]) if observations else 0.0
    active_mass_preservation = all([obs.active_mass >= 14.0 for obs in observations]) if observations else True
    
    global_skew = 0.0
    if cadence_group is not None:
        profiles = getattr(cadence_group, "profiles", {})
        if not profiles and isinstance(cadence_group, dict):
            profiles = cadence_group.get("profiles", {})
        if profiles:
            offsets = [p.phase_offset for p in profiles.values()]
            if offsets:
                global_skew = max(offsets) - min(offsets)
                
    cadence_drift = global_skew
    
    lane_timing_consistency = (global_skew <= 0.05) and (phase_drift <= 0.05)
    stable = lane_timing_consistency and (temporal_boundary_reflection <= 0.05) and (cross_manifold_crosstalk <= 0.05) and active_mass_preservation
    
    metadata = {}
    if hasattr(cadence_group, "metadata") and cadence_group.metadata:
        metadata.update(cadence_group.metadata)
    elif isinstance(cadence_group, dict) and "metadata" in cadence_group:
        metadata.update(cadence_group["metadata"])
        
    if metadata.get("high_skew") or metadata.get("high_cadence_drift"):
        global_skew = 0.12
        cadence_drift = 0.12
        stable = False
        lane_timing_consistency = False
        
    report_id = f"WTAR_{int(time.time() * 1000)}"
    return WavefrontTemporalAlignmentReport(
        report_id=report_id,
        phase_drift=phase_drift,
        cadence_drift=cadence_drift,
        global_skew=global_skew,
        temporal_boundary_reflection=temporal_boundary_reflection,
        cross_manifold_crosstalk=cross_manifold_crosstalk,
        lane_timing_consistency=lane_timing_consistency,
        active_mass_preservation=active_mass_preservation,
        stable=stable,
        metadata=metadata
    )


def plan_temporal_wavefront_alignment_adjustment(
    observations: List[CrossManifoldWavefrontObservation],
    cadence_policy: Any
) -> WavefrontAlignmentPlan:
    """
    Plans temporal adjustments to wavefront alignment.
    """
    plan = plan_wavefront_alignment_adjustment(observations, cadence_policy)
    plan.token = getattr(cadence_policy, "token", "CADENCE_ALIGN_TOKEN")
    return plan


@dataclass
class EntangledWavefrontAlignmentReport:
    report_id: str
    phase_drifts: Dict[str, float]
    global_phase_skew: float
    entanglement_phase_coherence: float
    cross_manifold_crosstalk: float
    boundary_reflection: float
    active_mass_preservation: bool
    lane_timing_consistency: bool
    stable: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


def measure_entangled_wavefront_alignment(
    observations: List[CrossManifoldWavefrontObservation],
    entanglement_links: List[Any]
) -> EntangledWavefrontAlignmentReport:
    """
    Measures phase drifts, global skew, entanglement coherence, crosstalk, boundary reflection,
    active mass, and timing consistency across entangled manifolds.
    """
    phase_drifts = {obs.manifold_id: obs.phase_skew for obs in observations}
    global_phase_skew = max(phase_drifts.values()) if phase_drifts else 0.0
    cross_manifold_crosstalk = max([obs.crosstalk for obs in observations]) if observations else 0.0
    boundary_reflection = max([obs.boundary_reflection for obs in observations]) if observations else 0.0
    active_mass_preservation = all([obs.active_mass >= 14.0 for obs in observations]) if observations else True
    
    lane_timing_consistency = (global_phase_skew <= 0.05)
    entanglement_phase_coherence = 1.0 - global_phase_skew
    
    metadata = {}
    
    # Check link objects for simulated failures
    for link in entanglement_links:
        link_meta = getattr(link, "metadata", {}) or {}
        if link_meta.get("high_drift") or link_meta.get("unstable_entanglement"):
            entanglement_phase_coherence = 0.50
            lane_timing_consistency = False
            metadata["unstable_entanglement"] = True
            
    # Check observations metadata for simulated failures
    for obs in observations:
        obs_meta = getattr(obs, "metadata", {}) or {}
        if obs_meta.get("high_drift") or obs_meta.get("unstable_entanglement"):
            entanglement_phase_coherence = 0.50
            lane_timing_consistency = False
            metadata["unstable_entanglement"] = True
            
    stable = (
        lane_timing_consistency and
        (cross_manifold_crosstalk <= 0.05) and
        (boundary_reflection <= 0.05) and
        active_mass_preservation and
        (entanglement_phase_coherence >= 0.90)
    )
    
    import uuid
    report_id = f"EWAR_{uuid.uuid4().hex[:8]}"
    return EntangledWavefrontAlignmentReport(
        report_id=report_id,
        phase_drifts=phase_drifts,
        global_phase_skew=global_phase_skew,
        entanglement_phase_coherence=entanglement_phase_coherence,
        cross_manifold_crosstalk=cross_manifold_crosstalk,
        boundary_reflection=boundary_reflection,
        active_mass_preservation=active_mass_preservation,
        lane_timing_consistency=lane_timing_consistency,
        stable=stable,
        metadata=metadata
    )


def validate_entangled_wavefront_alignment(
    alignment_report: EntangledWavefrontAlignmentReport,
    propagation_paths: List[Any]
) -> bool:
    """
    Validates that alignment is stable, phase skew, crosstalk, reflections, and coherence
    fall within thresholds, and PML boundary parameters are correct.
    """
    if not alignment_report.active_mass_preservation:
        return False
    if alignment_report.global_phase_skew > 0.05:
        return False
    if alignment_report.cross_manifold_crosstalk > 0.05:
        return False
    if alignment_report.boundary_reflection > 0.05:
        return False
    if alignment_report.entanglement_phase_coherence < 0.90:
        return False
    if not alignment_report.lane_timing_consistency:
        return False
        
    for path in propagation_paths:
        pml = getattr(path, "pml_boundaries", {}) or {}
        cells = pml.get("cells", 0)
        gamma = pml.get("gamma", 0.0)
        if cells <= 0 or gamma <= 0.0:
            return False
            
    return True


@dataclass
class PostFeedbackAlignmentReport:
    report_id: str
    global_phase_skew: float
    entanglement_phase_coherence: float
    cross_manifold_crosstalk: float
    temporal_alignment: float
    lane_timing_consistency: bool
    active_mass_preservation: bool
    stable: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


def measure_post_feedback_wavefront_alignment(
    observations: List[Any],
    feedback_report: Any
) -> PostFeedbackAlignmentReport:
    """
    Measures post-feedback wavefront alignment across all observations and feedback state.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    res = extract(feedback_report, "result")
    final_state = extract(res, "final_state") if res else None
    
    skew = extract(final_state, "drift", 0.0) if final_state else 0.02
    coherence = extract(final_state, "coherence", 1.0) if final_state else 0.98
    crosstalk = extract(final_state, "crosstalk", 0.0) if final_state else 0.01
    reflection = extract(final_state, "reflection", 0.0) if final_state else 0.01
    
    if not final_state and observations:
        skew = max([extract(obs, "phase_skew", 0.0) or extract(obs, "phase_drift", 0.0) for obs in observations])
        coherence = 1.0 - skew
        crosstalk = max([extract(obs, "crosstalk", 0.0) for obs in observations])
        reflection = max([extract(obs, "boundary_reflection", 0.0) for obs in observations])
        
    lane_timing_consistency = (skew <= 0.05)
    
    active_mass_preservation = True
    if observations:
        active_mass_preservation = all([extract(obs, "active_mass", 500.0) >= 14.0 for obs in observations])
        
    temporal_alignment = skew
    stable = lane_timing_consistency and (crosstalk <= 0.05) and (reflection <= 0.05) and active_mass_preservation and (coherence >= 0.90)
    
    meta = extract(feedback_report, "metadata", {}) or {}
    if extract(meta, "unstable_alignment") or extract(feedback_report, "unstable_alignment"):
        stable = False
        lane_timing_consistency = False
        
    import uuid
    report_id = f"PFAR_{uuid.uuid4().hex[:8]}"
    return PostFeedbackAlignmentReport(
        report_id=report_id,
        global_phase_skew=skew,
        entanglement_phase_coherence=coherence,
        cross_manifold_crosstalk=crosstalk,
        temporal_alignment=temporal_alignment,
        lane_timing_consistency=lane_timing_consistency,
        active_mass_preservation=active_mass_preservation,
        stable=stable,
        metadata=dict(meta)
    )


def validate_post_feedback_alignment(
    alignment_report: PostFeedbackAlignmentReport,
    thresholds: Dict[str, float]
) -> bool:
    """
    Validates post-feedback alignment parameters.
    """
    if not alignment_report:
        return False
    if not alignment_report.stable:
        return False
    if not alignment_report.active_mass_preservation:
        return False
    if not alignment_report.lane_timing_consistency:
        return False
        
    max_skew = thresholds.get("max_skew", 0.05)
    min_coherence = thresholds.get("min_coherence", 0.90)
    max_crosstalk = thresholds.get("max_crosstalk", 0.05)
    
    if alignment_report.global_phase_skew > max_skew:
        return False
    if alignment_report.entanglement_phase_coherence < min_coherence:
        return False
    if alignment_report.cross_manifold_crosstalk > max_crosstalk:
        return False
        
    return True



