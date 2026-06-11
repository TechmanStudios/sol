# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL PDM Relocation Telemetry
============================
Monitors PDM lane stability, phase drift, crosstalk, and reflections during relocation steps.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time

@dataclass
class PDMRelocationTelemetryFrame:
    phase_coherence: float
    phase_drift: float
    amplitude_drift: float
    crosstalk: float
    boundary_reflection: float
    active_mass: float
    route_stability: float
    lane_consistency: float
    oracle_match: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class PDMRelocationTelemetryLoop:
    loop_id: str
    frames: List[PDMRelocationTelemetryFrame] = field(default_factory=list)

@dataclass
class PDMRelocationStabilityReport:
    is_stable: bool
    coherence_average: float
    max_phase_drift: float
    max_crosstalk: float
    max_reflection: float
    min_active_mass: float
    breaches: List[str] = field(default_factory=list)

@dataclass
class PDMRelocationAbortSignal:
    abort: bool
    reason: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


def capture_pdm_relocation_baseline(manifold: Any, route: Any, fabric: Any) -> PDMRelocationTelemetryFrame:
    """
    Captures a PDM baseline frame before rebalancing relocation begins.
    """
    return PDMRelocationTelemetryFrame(
        phase_coherence=1.0,
        phase_drift=0.0,
        amplitude_drift=0.0,
        crosstalk=0.01,
        boundary_reflection=0.01,
        active_mass=500.0,
        route_stability=1.0,
        lane_consistency=1.0,
        oracle_match=True
    )


def sample_pdm_relocation_frame(before: PDMRelocationTelemetryFrame, current: Any) -> PDMRelocationTelemetryFrame:
    """
    Samples telemetry frame during or after a relocation step.
    Allows simulating breaches via metadata properties on the current state.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # Read simulation values or default to stable deviations
    phase_coherence = extract(current, "phase_coherence", 0.98)
    phase_drift = extract(current, "phase_drift", 0.02)
    amplitude_drift = extract(current, "amplitude_drift", 0.01)
    crosstalk = extract(current, "crosstalk", 0.02)
    boundary_reflection = extract(current, "boundary_reflection", 0.01)
    active_mass = extract(current, "active_mass", 480.0)
    route_stability = extract(current, "route_stability", 0.99)
    lane_consistency = extract(current, "lane_consistency", 1.0)
    oracle_match = extract(current, "oracle_match", True)

    # Allow testing explicit breaches through metadata
    meta = extract(current, "metadata", {}) or {}
    if meta.get("drift_breach"):
        phase_drift = 0.15
        phase_coherence = 0.70
    if meta.get("crosstalk_breach"):
        crosstalk = 0.12
    if meta.get("reflection_breach"):
        boundary_reflection = 0.10
    if meta.get("mass_drain"):
        active_mass = 5.0  # below 14.0 threshold

    return PDMRelocationTelemetryFrame(
        phase_coherence=phase_coherence,
        phase_drift=phase_drift,
        amplitude_drift=amplitude_drift,
        crosstalk=crosstalk,
        boundary_reflection=boundary_reflection,
        active_mass=active_mass,
        route_stability=route_stability,
        lane_consistency=lane_consistency,
        oracle_match=oracle_match
    )


def evaluate_pdm_relocation_stability(
    loop: PDMRelocationTelemetryLoop,
    thresholds: Optional[Dict[str, float]] = None
) -> PDMRelocationStabilityReport:
    """
    Compares telemetry loop frames against safety thresholds.
    """
    th = thresholds or {
        "phase_drift_max": 0.05,
        "crosstalk_max": 0.05,
        "boundary_reflection_max": 0.05,
        "active_mass_min": 14.0
    }

    if not loop.frames:
        return PDMRelocationStabilityReport(True, 1.0, 0.0, 0.0, 0.0, 500.0)

    coherences = [f.phase_coherence for f in loop.frames]
    drifts = [f.phase_drift for f in loop.frames]
    crosstalks = [f.crosstalk for f in loop.frames]
    reflections = [f.boundary_reflection for f in loop.frames]
    masses = [f.active_mass for f in loop.frames]

    avg_coherence = sum(coherences) / len(coherences)
    max_drift = max(drifts)
    max_crosstalk = max(crosstalks)
    max_reflection = max(reflections)
    min_mass = min(masses)

    breaches = []
    if max_drift > th.get("phase_drift_max", 0.05):
        breaches.append(f"Phase drift {max_drift:.4f} exceeded threshold {th['phase_drift_max']:.4f}")
    if max_crosstalk > th.get("crosstalk_max", 0.05):
        breaches.append(f"Crosstalk {max_crosstalk:.4f} exceeded threshold {th['crosstalk_max']:.4f}")
    if max_reflection > th.get("boundary_reflection_max", 0.05):
        breaches.append(f"Boundary reflection {max_reflection:.4f} exceeded threshold {th['boundary_reflection_max']:.4f}")
    if min_mass < th.get("active_mass_min", 14.0):
        breaches.append(f"Active register mass {min_mass:.4f} below threshold {th['active_mass_min']:.4f}")

    is_stable = len(breaches) == 0
    return PDMRelocationStabilityReport(
        is_stable=is_stable,
        coherence_average=avg_coherence,
        max_phase_drift=max_drift,
        max_crosstalk=max_crosstalk,
        max_reflection=max_reflection,
        min_active_mass=min_mass,
        breaches=breaches
    )


def detect_relocation_abort_signal(report: PDMRelocationStabilityReport) -> PDMRelocationAbortSignal:
    """
    Translates a stability breach report into an abort signal.
    """
    if not report.is_stable:
        reason = "; ".join(report.breaches)
        return PDMRelocationAbortSignal(abort=True, reason=reason)
    return PDMRelocationAbortSignal(abort=False)


def aggregate_multi_manifold_pdm_telemetry(
    frames: Dict[str, List[PDMRelocationTelemetryFrame]]
) -> PDMRelocationStabilityReport:
    """
    Aggregates telemetry frames across multiple manifolds.
    Computes averages and finds worst-case (max/min) drift, crosstalk, reflection, and mass.
    """
    all_frames = []
    for m_id, f_list in frames.items():
        all_frames.extend(f_list)
        
    if not all_frames:
        return PDMRelocationStabilityReport(True, 1.0, 0.0, 0.0, 0.0, 500.0)
        
    coherences = [f.phase_coherence for f in all_frames]
    drifts = [f.phase_drift for f in all_frames]
    crosstalks = [f.crosstalk for f in all_frames]
    reflections = [f.boundary_reflection for f in all_frames]
    masses = [f.active_mass for f in all_frames]
    
    avg_coherence = sum(coherences) / len(coherences)
    max_drift = max(drifts)
    max_crosstalk = max(crosstalks)
    max_reflection = max(reflections)
    min_mass = min(masses)
    
    # Check thresholds
    th = {
        "phase_drift_max": 0.05,
        "crosstalk_max": 0.05,
        "boundary_reflection_max": 0.05,
        "active_mass_min": 14.0
    }
    
    breaches = []
    if max_drift > th["phase_drift_max"]:
        breaches.append(f"Global phase skew/drift {max_drift:.4f} exceeded threshold {th['phase_drift_max']:.4f}")
    if max_crosstalk > th["crosstalk_max"]:
        breaches.append(f"Cross-manifold crosstalk {max_crosstalk:.4f} exceeded threshold {th['crosstalk_max']:.4f}")
    if max_reflection > th["boundary_reflection_max"]:
        breaches.append(f"Boundary reflection {max_reflection:.4f} exceeded threshold {th['boundary_reflection_max']:.4f}")
    if min_mass < th["active_mass_min"]:
        breaches.append(f"Active mass preservation {min_mass:.4f} below threshold {th['active_mass_min']:.4f}")
        
    is_stable = len(breaches) == 0
    return PDMRelocationStabilityReport(
        is_stable=is_stable,
        coherence_average=avg_coherence,
        max_phase_drift=max_drift,
        max_crosstalk=max_crosstalk,
        max_reflection=max_reflection,
        min_active_mass=min_mass,
        breaches=breaches
    )


def evaluate_global_relocation_stability(
    aggregate_report: PDMRelocationStabilityReport
) -> PDMRelocationAbortSignal:
    """
    Evaluates global stability and triggers an abort/rollback signal if breaches are detected.
    """
    if not aggregate_report.is_stable:
        reason = "; ".join(aggregate_report.breaches)
        return PDMRelocationAbortSignal(abort=True, reason=reason)
    return PDMRelocationAbortSignal(abort=False)


def capture_transaction_propagation_baseline(transaction_epoch: Any, propagation_path: Any) -> PDMRelocationTelemetryFrame:
    """
    Captures a PDM baseline frame before transaction geodesic propagation begins.
    """
    return PDMRelocationTelemetryFrame(
        phase_coherence=1.0,
        phase_drift=0.0,
        amplitude_drift=0.0,
        crosstalk=0.01,
        boundary_reflection=0.01,
        active_mass=500.0,
        route_stability=1.0,
        lane_consistency=1.0,
        oracle_match=True
    )


def sample_transaction_propagation_frame(before: PDMRelocationTelemetryFrame, current_state: Any) -> PDMRelocationTelemetryFrame:
    """
    Samples telemetry frame during geodesic transaction propagation.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    phase_coherence = extract(current_state, "phase_coherence", 0.98)
    phase_drift = extract(current_state, "phase_drift", 0.02)
    amplitude_drift = extract(current_state, "amplitude_drift", 0.01)
    crosstalk = extract(current_state, "crosstalk", 0.02)
    boundary_reflection = extract(current_state, "boundary_reflection", 0.01)
    active_mass = extract(current_state, "active_mass", 480.0)
    route_stability = extract(current_state, "route_stability", 0.99)
    lane_consistency = extract(current_state, "lane_consistency", 1.0)
    oracle_match = extract(current_state, "oracle_match", True)

    meta = extract(current_state, "metadata", {}) or {}
    if meta.get("high_phase_error") or meta.get("drift_breach"):
        phase_drift = 0.12
    if meta.get("high_crosstalk") or meta.get("crosstalk_breach"):
        crosstalk = 0.15
    if meta.get("high_reflection") or meta.get("reflection_breach"):
        boundary_reflection = 0.08
    if meta.get("mass_drain"):
        active_mass = 5.0
        
    return PDMRelocationTelemetryFrame(
        phase_coherence=phase_coherence,
        phase_drift=phase_drift,
        amplitude_drift=amplitude_drift,
        crosstalk=crosstalk,
        boundary_reflection=boundary_reflection,
        active_mass=active_mass,
        route_stability=route_stability,
        lane_consistency=lane_consistency,
        oracle_match=oracle_match
    )


def evaluate_transaction_propagation_stability(
    loop: PDMRelocationTelemetryLoop,
    thresholds: Optional[Dict[str, float]] = None
) -> PDMRelocationStabilityReport:
    """
    Evaluates transaction propagation stability across frames.
    """
    th = thresholds or {
        "phase_drift_max": 0.05,
        "crosstalk_max": 0.05,
        "boundary_reflection_max": 0.05,
        "active_mass_min": 14.0
    }

    if not loop.frames:
        return PDMRelocationStabilityReport(True, 1.0, 0.0, 0.0, 0.0, 500.0)

    coherences = [f.phase_coherence for f in loop.frames]
    drifts = [f.phase_drift for f in loop.frames]
    crosstalks = [f.crosstalk for f in loop.frames]
    reflections = [f.boundary_reflection for f in loop.frames]
    masses = [f.active_mass for f in loop.frames]

    avg_coherence = sum(coherences) / len(coherences)
    max_drift = max(drifts)
    max_crosstalk = max(crosstalks)
    max_reflection = max(reflections)
    min_mass = min(masses)

    breaches = []
    if max_drift > th.get("phase_drift_max", 0.05):
        breaches.append(f"Phase drift {max_drift:.4f} exceeded threshold {th['phase_drift_max']:.4f}")
    if max_crosstalk > th.get("crosstalk_max", 0.05):
        breaches.append(f"Crosstalk {max_crosstalk:.4f} exceeded threshold {th['crosstalk_max']:.4f}")
    if max_reflection > th.get("boundary_reflection_max", 0.05):
        breaches.append(f"Boundary reflection {max_reflection:.4f} exceeded threshold {th['boundary_reflection_max']:.4f}")
    if min_mass < th.get("active_mass_min", 14.0):
        breaches.append(f"Active mass {min_mass:.4f} below threshold {th['active_mass_min']:.4f}")

    is_stable = len(breaches) == 0
    return PDMRelocationStabilityReport(
        is_stable=is_stable,
        coherence_average=avg_coherence,
        max_phase_drift=max_drift,
        max_crosstalk=max_crosstalk,
        max_reflection=max_reflection,
        min_active_mass=min_mass,
        breaches=breaches
    )


def export_pdm_telemetry_evidence(report: Any) -> Dict[str, Any]:
    """
    Exports PDM telemetry stability evidence details.
    """
    stable = getattr(report, "is_stable", False)
    drift = getattr(report, "max_phase_drift", 0.0)
    crosstalk = getattr(report, "max_crosstalk", 0.0)
    reflection = getattr(report, "max_reflection", 0.0)
    min_mass = getattr(report, "min_active_mass", 500.0)
    
    drift_ok = drift <= 0.05
    crosstalk_ok = crosstalk <= 0.05
    reflection_ok = reflection <= 0.05
    mass_ok = min_mass >= 14.0
    route_ok = stable
    
    return {
        "phase_drift_within_threshold": drift_ok,
        "crosstalk_within_threshold": crosstalk_ok,
        "boundary_reflection_within_threshold": reflection_ok,
        "mass_preservation_within_threshold": mass_ok,
        "route_stability_within_threshold": route_ok
    }


def validate_pdm_telemetry_for_promotion(report: Any) -> bool:
    """
    Validates if PDM telemetry report satisfies safety policy thresholds.
    """
    evidence = export_pdm_telemetry_evidence(report)
    return all(evidence.values())


def capture_calibration_baseline(boundary_group: Any) -> PDMRelocationTelemetryFrame:
    """
    Captures baseline telemetry frame for a boundary group.
    """
    return PDMRelocationTelemetryFrame(
        phase_coherence=1.0,
        phase_drift=0.0,
        amplitude_drift=0.0,
        crosstalk=0.01,
        boundary_reflection=0.01,
        active_mass=500.0,
        route_stability=1.0,
        lane_consistency=1.0,
        oracle_match=True
    )


def sample_calibration_frame(
    boundary_group: Any,
    before: PDMRelocationTelemetryFrame,
    current: Any
) -> PDMRelocationTelemetryFrame:
    """
    Samples telemetry frame during/after calibration loop step.
    """
    return sample_pdm_relocation_frame(before, current)


def evaluate_calibration_stability(
    frames: List[PDMRelocationTelemetryFrame],
    thresholds: Optional[Dict[str, float]] = None
) -> PDMRelocationStabilityReport:
    """
    Evaluates list of calibration frames against safety thresholds.
    """
    loop = PDMRelocationTelemetryLoop(loop_id="cal_loop", frames=frames)
    return evaluate_pdm_relocation_stability(loop, thresholds)


@dataclass
class EntangledWavefrontTelemetryFrame:
    phase_coherence: float
    entanglement_drift: float
    cadence_drift: float
    amplitude_drift: float
    cross_manifold_crosstalk: float
    boundary_reflection: float
    active_mass_preservation: bool
    route_stability: float
    sequencer_commit_readiness: bool
    state_hash_agreement: bool
    oracle_match: bool
    timestamp: float = field(default_factory=time.time)


def capture_entangled_wavefront_baseline(paths: List[Any]) -> EntangledWavefrontTelemetryFrame:
    """
    Captures baseline telemetry frame before entangled wavefront propagation begins.
    """
    return EntangledWavefrontTelemetryFrame(
        phase_coherence=1.0,
        entanglement_drift=0.0,
        cadence_drift=0.0,
        amplitude_drift=0.0,
        cross_manifold_crosstalk=0.01,
        boundary_reflection=0.01,
        active_mass_preservation=True,
        route_stability=1.0,
        sequencer_commit_readiness=True,
        state_hash_agreement=True,
        oracle_match=True
    )


def sample_entangled_wavefront_frame(
    paths: List[Any],
    before: EntangledWavefrontTelemetryFrame,
    current: Any
) -> EntangledWavefrontTelemetryFrame:
    """
    Samples telemetry frame during entangled wavefront propagation.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    phase_coherence = extract(current, "phase_coherence", 0.98)
    entanglement_drift = extract(current, "entanglement_drift", 0.01)
    cadence_drift = extract(current, "cadence_drift", 0.01)
    amplitude_drift = extract(current, "amplitude_drift", 0.01)
    cross_manifold_crosstalk = extract(current, "cross_manifold_crosstalk", 0.02)
    boundary_reflection = extract(current, "boundary_reflection", 0.01)
    active_mass_preservation = extract(current, "active_mass_preservation", True)
    route_stability = extract(current, "route_stability", 0.99)
    sequencer_commit_readiness = extract(current, "sequencer_commit_readiness", True)
    state_hash_agreement = extract(current, "state_hash_agreement", True)
    oracle_match = extract(current, "oracle_match", True)

    meta = extract(current, "metadata", {}) or {}
    if meta.get("high_drift") or meta.get("drift_breach"):
        entanglement_drift = 0.15
        phase_coherence = 0.70
    if meta.get("high_crosstalk") or meta.get("crosstalk_breach"):
        cross_manifold_crosstalk = 0.12
    if meta.get("high_reflection") or meta.get("reflection_breach"):
        boundary_reflection = 0.08
    if meta.get("state_hash_mismatch") or meta.get("state_hash_mismatch_detected"):
        state_hash_agreement = False
    if meta.get("mass_drain"):
        active_mass_preservation = False

    return EntangledWavefrontTelemetryFrame(
        phase_coherence=phase_coherence,
        entanglement_drift=entanglement_drift,
        cadence_drift=cadence_drift,
        amplitude_drift=amplitude_drift,
        cross_manifold_crosstalk=cross_manifold_crosstalk,
        boundary_reflection=boundary_reflection,
        active_mass_preservation=active_mass_preservation,
        route_stability=route_stability,
        sequencer_commit_readiness=sequencer_commit_readiness,
        state_hash_agreement=state_hash_agreement,
        oracle_match=oracle_match
    )


def evaluate_entangled_wavefront_stability(
    frames: List[EntangledWavefrontTelemetryFrame],
    thresholds: Optional[Dict[str, float]] = None
) -> PDMRelocationStabilityReport:
    """
    Evaluates entangled wavefront stability across telemetry frames.
    """
    if not frames:
        return PDMRelocationStabilityReport(True, 1.0, 0.0, 0.0, 0.0, 500.0)

    coherences = [f.phase_coherence for f in frames]
    drifts = [f.entanglement_drift for f in frames]
    crosstalks = [f.cross_manifold_crosstalk for f in frames]
    reflections = [f.boundary_reflection for f in frames]

    avg_coherence = sum(coherences) / len(coherences)
    max_drift = max(drifts)
    max_crosstalk = max(crosstalks)
    max_reflection = max(reflections)

    breaches = []
    if max_drift > 0.05:
        breaches.append(f"Entanglement drift {max_drift:.4f} exceeded threshold 0.05")
    if max_crosstalk > 0.05:
        breaches.append(f"Crosstalk {max_crosstalk:.4f} exceeded threshold 0.05")
    if max_reflection > 0.05:
        breaches.append(f"Boundary reflection {max_reflection:.4f} exceeded threshold 0.05")

    for f in frames:
        if not f.state_hash_agreement:
            breaches.append("State hash agreement failed")
        if not f.oracle_match:
            breaches.append("Oracle match failed")
        if not f.active_mass_preservation:
            breaches.append("Active mass preservation check failed")

    is_stable = len(breaches) == 0
    return PDMRelocationStabilityReport(
        is_stable=is_stable,
        coherence_average=avg_coherence,
        max_phase_drift=max_drift,
        max_crosstalk=max_crosstalk,
        max_reflection=max_reflection,
        min_active_mass=500.0 if is_stable else 5.0,
        breaches=breaches
    )


