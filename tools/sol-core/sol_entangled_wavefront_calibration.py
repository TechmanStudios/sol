# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Wavefront Calibration
===================================
Manages phase coherence calibration and drift metrics tracking across multiple manifolds.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class EntangledCalibrationTarget:
    target_id: str
    source_manifold_id: str
    target_manifold_id: str
    link_id: str

@dataclass
class EntangledCalibrationPolicy:
    max_steps: int
    max_phase_adj: float
    max_cadence_adj: float
    max_carrier_adj: float
    max_damping_adj: float
    max_pml_adj: float
    max_route_damping: float
    abort_thresholds: Dict[str, float] = field(default_factory=dict)

@dataclass
class EntangledCalibrationBaseline:
    baseline_id: str
    phase_coherence: float = 1.0
    phase_drift: float = 0.0
    global_phase_skew: float = 0.0
    cadence_drift: float = 0.0
    carrier_phase_error: float = 0.0
    crosstalk: float = 0.0
    boundary_reflection: float = 0.0
    active_mass_preservation: bool = True
    lane_timing_consistency: bool = True
    pml_absorption_effectiveness: float = 1.0

@dataclass
class EntangledCalibrationObservation:
    manifold_id: str
    phase_coherence: float
    phase_drift: float
    global_phase_skew: float
    cadence_drift: float
    carrier_phase_error: float
    crosstalk: float
    boundary_reflection: float
    active_mass: float
    lane_timing: float
    pml_effectiveness: float

@dataclass
class EntangledCalibrationAdjustment:
    manifold_id: str
    phase_adjustment: float = 0.0
    cadence_adjustment: float = 0.0
    carrier_adjustment: float = 0.0
    damping_adjustment: float = 0.0
    pml_adjustment: float = 0.0
    route_damping_adjustment: float = 0.0

@dataclass
class EntangledCalibrationStep:
    step_idx: int
    adjustments: List[EntangledCalibrationAdjustment] = field(default_factory=list)

@dataclass
class EntangledCalibrationResult:
    success: bool
    final_error: float
    errors: List[str] = field(default_factory=field(default_factory=list))

@dataclass
class EntangledCalibrationReport:
    report_id: str
    targets: List[EntangledCalibrationTarget]
    baseline: EntangledCalibrationBaseline
    steps: List[EntangledCalibrationStep]
    result: EntangledCalibrationResult
    passed_gates: bool
    timestamp: float = field(default_factory=time.time)


def build_entangled_calibration_targets(
    propagation_paths: List[Any],
    entanglement_links: List[Any]
) -> List[EntangledCalibrationTarget]:
    """
    Builds calibration targets mapping source/target manifolds.
    """
    targets = []
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    for i, path in enumerate(propagation_paths):
        src = extract(path, "source_manifold_id")
        tgt = extract(path, "target_manifold_id")
        link_id = extract(path, "link_id")
        if not src or not tgt or not link_id:
            raise ValueError("Invalid propagation path in build_entangled_calibration_targets.")
        targets.append(EntangledCalibrationTarget(
            target_id=f"CAL_TGT_{src}_{tgt}_{i}",
            source_manifold_id=src,
            target_manifold_id=tgt,
            link_id=link_id
        ))
    return targets


def capture_entangled_calibration_baseline(
    targets: List[EntangledCalibrationTarget]
) -> EntangledCalibrationBaseline:
    """
    Captures the initial calibration baseline.
    """
    if not targets:
        raise ValueError("Cannot capture baseline: targets list is empty.")
    import uuid
    baseline_id = f"CAL_BASE_{uuid.uuid4().hex[:8]}"
    return EntangledCalibrationBaseline(baseline_id=baseline_id)


def measure_entangled_calibration_error(
    baseline: EntangledCalibrationBaseline,
    current: Any
) -> float:
    """
    Computes cumulative calibration error across tracked metrics.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    phase_drift = extract(current, "phase_drift", 0.0)
    cadence_drift = extract(current, "cadence_drift", 0.0)
    crosstalk = extract(current, "crosstalk", 0.0)
    boundary_reflection = extract(current, "boundary_reflection", 0.0)
    carrier_phase_error = extract(current, "carrier_phase_error", 0.0)
    coherence = extract(current, "phase_coherence", 1.0)

    # Accumulate metric deltas
    error = (
        phase_drift +
        cadence_drift +
        crosstalk +
        boundary_reflection +
        carrier_phase_error +
        (1.0 - coherence)
    )
    return float(error)


def plan_entangled_calibration_adjustments(
    error_report: Any,
    policy: EntangledCalibrationPolicy
) -> List[EntangledCalibrationAdjustment]:
    """
    Plans phase, cadence, damping, and PML absorption adjustments based on errors and policy.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    phase_drift = extract(error_report, "phase_drift", 0.0)
    cadence_drift = extract(error_report, "cadence_drift", 0.0)
    carrier_phase_error = extract(error_report, "carrier_phase_error", 0.0)
    crosstalk = extract(error_report, "crosstalk", 0.0)
    boundary_reflection = extract(error_report, "boundary_reflection", 0.0)
    
    # Check max bounds
    if phase_drift > policy.max_phase_adj:
        phase_drift = policy.max_phase_adj
    if cadence_drift > policy.max_cadence_adj:
        cadence_drift = policy.max_cadence_adj
    if carrier_phase_error > policy.max_carrier_adj:
        carrier_phase_error = policy.max_carrier_adj
        
    adjustments = []
    # Mock planning adjustments for target manifolds
    adjustments.append(EntangledCalibrationAdjustment(
        manifold_id="M1",
        phase_adjustment=-0.5 * phase_drift,
        cadence_adjustment=-0.5 * cadence_drift,
        carrier_adjustment=-0.5 * carrier_phase_error,
        damping_adjustment=0.1 * crosstalk,
        pml_adjustment=0.1 * boundary_reflection,
        route_damping_adjustment=0.0
    ))
    return adjustments


def execute_shadow_entangled_calibration(
    adjustments: List[EntangledCalibrationAdjustment]
) -> EntangledCalibrationResult:
    """
    Simulates applying adjustments in shadow mode.
    """
    errors = []
    # Adjustments bounds check
    for adj in adjustments:
        if abs(adj.phase_adjustment) > 0.05:
            errors.append(f"Phase adjustment exceeds safety bounds on manifold {adj.manifold_id}")
            
    success = len(errors) == 0
    return EntangledCalibrationResult(
        success=success,
        final_error=0.01 if success else 0.15,
        errors=errors
    )


def summarize_entangled_calibration(result: EntangledCalibrationResult) -> Dict[str, Any]:
    """
    Creates a summary dictionary of the calibration outcome.
    """
    return {
        "success": result.success,
        "final_error": result.final_error,
        "errors": list(result.errors)
    }


def export_resonant_feedback_targets(
    calibration_report: Any
) -> List[Dict[str, Any]]:
    """
    Exports resonant feedback targets based on calibration report targets.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    targets = extract(calibration_report, "targets", [])
    feedback_targets = []
    for t in targets:
        feedback_targets.append({
            "manifold_id": extract(t, "target_manifold_id", "unknown"),
            "link_id": extract(t, "link_id", "unknown")
        })
    return feedback_targets


def validate_resonant_feedback_after_calibration(
    feedback_report: Any,
    calibration_report: Any
) -> bool:
    """
    Validates resonant feedback loop stability after calibration.
    Feedback cannot be promoted if calibration baseline is missing or unstable.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not calibration_report:
        return False

    baseline = extract(calibration_report, "baseline")
    if not baseline:
        # missing baseline
        return False
        
    coh = extract(baseline, "phase_coherence", 1.0)
    if coh < 0.8:
        # unstable baseline
        return False

    res = extract(feedback_report, "result", {})
    if not extract(res, "success", False) or extract(res, "errors", []):
        return False

    return True

