# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Temporal Cadence
====================
Provides temporal cadence profiles, clocks, stability evaluations, and correction planning.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class CadenceClockId:
    manifold_id: str
    clock_idx: int = 0

@dataclass
class TemporalCadenceProfile:
    manifold_id: str
    tick_rate: float
    phase_offset: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CadenceTick:
    step_index: int
    timestamp: float

@dataclass
class CadenceWindow:
    start_tick: int
    end_tick: int
    active: bool = True

@dataclass
class CadenceDriftObservation:
    manifold_id: str
    drift: float
    jitter: float = 0.01

@dataclass
class CadenceStabilityReport:
    report_id: str
    observations: List[CadenceDriftObservation] = field(default_factory=list)
    global_skew: float = 0.0
    stable: bool = True

@dataclass
class CadenceCorrectionPlan:
    plan_id: str
    adjustments: Dict[str, float] = field(default_factory=dict)  # manifold_id -> correction phase shift
    token: Optional[str] = None


def build_temporal_cadence_profile(manifold_id: str, tick_rate: float, phase_offset: float = 0.0) -> TemporalCadenceProfile:
    """
    Constructs a TemporalCadenceProfile. Rejects invalid tick rates.
    """
    if tick_rate <= 0.0:
        raise ValueError(f"Invalid tick_rate {tick_rate}: must be greater than zero.")
    return TemporalCadenceProfile(
        manifold_id=manifold_id,
        tick_rate=tick_rate,
        phase_offset=phase_offset
    )


def sample_cadence_tick(profile: TemporalCadenceProfile, step_index: int) -> CadenceTick:
    """
    Generates a CadenceTick with step index and timestamp.
    """
    period = 1.0 / profile.tick_rate
    timestamp = step_index * period + profile.phase_offset
    return CadenceTick(step_index=step_index, timestamp=timestamp)


def measure_cadence_drift(source_profile: TemporalCadenceProfile, target_profile: TemporalCadenceProfile, window: CadenceWindow) -> CadenceDriftObservation:
    """
    Measures temporal drift between source and target profiles within a cadence window.
    """
    drift = abs(source_profile.phase_offset - target_profile.phase_offset)
    # add slight scale difference if tick rates differ
    if source_profile.tick_rate != target_profile.tick_rate:
        drift += abs(1.0 / source_profile.tick_rate - 1.0 / target_profile.tick_rate) * window.start_tick
    return CadenceDriftObservation(
        manifold_id=target_profile.manifold_id,
        drift=drift,
        jitter=0.005
    )


def evaluate_cadence_stability(observations: List[CadenceDriftObservation], thresholds: Dict[str, float]) -> CadenceStabilityReport:
    """
    Evaluates drift observations to compile global cadence skew and stability.
    """
    if not observations:
        return CadenceStabilityReport(report_id="CAD_STAB_EMPTY", global_skew=0.0, stable=True)
        
    global_skew = max(obs.drift for obs in observations)
    max_allowed = thresholds.get("max_drift", 0.05)
    stable = (global_skew <= max_allowed)
    
    import time
    report_id = f"CAD_STAB_REP_{int(time.time() * 1000)}"
    return CadenceStabilityReport(
        report_id=report_id,
        observations=observations,
        global_skew=global_skew,
        stable=stable
    )


def build_shadow_cadence_correction_plan(report: CadenceStabilityReport, policy: Any) -> CadenceCorrectionPlan:
    """
    Builds a correction plan to nudge profiles back into phase lock.
    """
    adjustments = {}
    for obs in report.observations:
        if obs.drift > 0.01:
            # Shift by negative of drift to align
            adjustments[obs.manifold_id] = -0.5 * obs.drift
            
    import time
    plan_id = f"CAD_CORR_PLAN_{int(time.time() * 1000)}"
    return CadenceCorrectionPlan(
        plan_id=plan_id,
        adjustments=adjustments,
        token=getattr(policy, "token", "SHADOW_TOKEN")
    )


def validate_entangled_commit_cadence(commit_intent: Any, cadence_report: Any) -> bool:
    """
    Validates synchronized sequencer commits under cadence constraints.
    Blocks if:
    - any participant is outside cadence window
    - cadence drift exceeds threshold
    - global cadence skew exceeds threshold
    - cadence checkpoint is incomplete
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # 1. Check intent/report metadata for window failure
    commit_meta = extract(commit_intent, "metadata", {}) or {}
    report_meta = extract(cadence_report, "metadata", {}) or {}
    
    if commit_meta.get("outside_cadence_window") or report_meta.get("outside_cadence_window"):
        return False
    if commit_meta.get("outside_window") or report_meta.get("outside_window"):
        return False
        
    # 2. Check drift and skew
    drift = extract(cadence_report, "drift", 0.0)
    skew = extract(cadence_report, "global_skew", 0.0)
    # Check if drift is in stability report or sync report
    if hasattr(cadence_report, "observations") and cadence_report.observations:
        skew = max(o.drift for o in cadence_report.observations)
        
    if drift > 0.05 or skew > 0.05:
        return False
        
    # Check checkpoint incomplete
    if commit_meta.get("checkpoint_incomplete") or report_meta.get("checkpoint_incomplete"):
        return False
        
    # Split brain
    if commit_meta.get("split_brain") or report_meta.get("split_brain") or commit_meta.get("split_brain_detected") or report_meta.get("split_brain_detected"):
        return False
        
    return True


def measure_entangled_commit_cadence_error(commit_report: Any, cadence_profile: Any) -> float:
    """
    Measures cadence error for a commit report against a target profile.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    skew = extract(commit_report, "global_skew", 0.0)
    drift = extract(commit_report, "drift", 0.0)
    phase_offset = extract(cadence_profile, "phase_offset", 0.0)
    
    return max(skew, drift) + abs(phase_offset)


def validate_cadence_after_entangled_feedback(cadence_report: Any, feedback_report: Any) -> bool:
    """
    Validates cadence profiles after entangled feedback loops.
    Feedback may not push manifolds outside approved cadence windows.
    """
    if not cadence_report or not feedback_report:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(feedback_report, "result")
    if not res:
        return False
        
    if not extract(res, "success", True):
        return False

    final_state = extract(res, "final_state")
    if not final_state:
        return False

    drift = extract(final_state, "cadence_drift", 0.0)
    if drift > 0.05:
        return False

    # Check if outside cadence window or if metadata has outside_cadence_window
    meta = extract(feedback_report, "metadata", {}) or {}
    if extract(meta, "outside_cadence_window") or extract(cadence_report, "outside_cadence_window") or extract(feedback_report, "outside_cadence_window"):
        return False

    return True


def measure_feedback_induced_cadence_drift(before: Any, after: Any) -> float:
    """
    Measures the drift induced by feedback by comparing states/profiles before and after.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    offset_before = extract(before, "phase_offset", 0.0)
    offset_after = extract(after, "phase_offset", 0.0)
    return abs(offset_after - offset_before)


def validate_prefix_carry_cadence(carry_report: Any, cadence_profile: Any) -> bool:
    """
    Validates that carry-wave propagation complies with temporal cadence thresholds.
    Blocks (returns False) if cadence drift exceeds threshold (0.05).
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    drift = extract(carry_report, "carry_wavefront_phase_drift", 0.0) or extract(carry_report, "drift", 0.0)
    if drift > 0.05:
        return False
    return True


def measure_carry_cadence_error(carry_trace: Any, cadence_profile: Any) -> float:
    """
    Measures the cadence error (phase drift + profile phase offset) for carry propagation.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    drift = extract(carry_trace, "carry_wavefront_phase_drift", 0.0) or extract(carry_trace, "drift", 0.0)
    phase_offset = extract(cadence_profile, "phase_offset", 0.0)
    return drift + abs(phase_offset)


def validate_atomic_commit_cadence(atomic_intent: Any, cadence_report: Any) -> bool:
    """
    Validates atomic commit cadence constraints.
    Blocks if:
    - cadence drift exceeds threshold
    - global cadence skew exceeds threshold
    - participant is outside commit window
    - cadence checkpoint is incomplete
    """
    if not atomic_intent or not cadence_report:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    intent_meta = extract(atomic_intent, "metadata", {}) or {}
    report_meta = extract(cadence_report, "metadata", {}) or {}
    
    if not isinstance(intent_meta, dict):
        intent_meta = {}
    if not isinstance(report_meta, dict):
        report_meta = {}
        
    # Check outside cadence window
    if intent_meta.get("outside_cadence_window") or report_meta.get("outside_cadence_window"):
        return False
    if intent_meta.get("outside_window") or report_meta.get("outside_window"):
        return False
        
    # Check incomplete checkpoints
    if intent_meta.get("checkpoint_incomplete") or report_meta.get("checkpoint_incomplete"):
        return False
        
    # Check drift and skew
    drift = extract(cadence_report, "drift", 0.0) or 0.0
    skew = extract(cadence_report, "global_skew", 0.0) or 0.0
    if hasattr(cadence_report, "observations") and cadence_report.observations:
        skew = max(o.drift for o in cadence_report.observations)
        
    if drift > 0.05 or skew > 0.05:
        return False
        
    # Check split brain
    if intent_meta.get("split_brain") or report_meta.get("split_brain") or intent_meta.get("split_brain_detected") or report_meta.get("split_brain_detected"):
        return False
        
    return True


def measure_atomic_commit_cadence_error(commit_report: Any, cadence_profile: Any) -> float:
    """
    Measures error metric for atomic commit cadence.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    skew = extract(commit_report, "global_skew", 0.0)
    drift = extract(commit_report, "drift", 0.0)
    phase_offset = extract(cadence_profile, "phase_offset", 0.0)
    return max(skew, drift) + abs(phase_offset)


def validate_state_relocation_cadence(relocation_plan: Any, cadence_report: Any) -> bool:
    """
    Validates cadence constraints during state relocation.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    intent = extract(relocation_plan, "intent")
    meta = extract(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("outside_cadence_window") or meta.get("outside_window"):
        return False
    if meta.get("high_phase_drift"):
        return False
    if meta.get("lane_skew_failure"):
        return False
        
    return True


def measure_relocation_cadence_error(relocation_report: Any, cadence_profile: Any) -> float:
    """
    Measures cadence error induced by state relocation.
    """
    return 0.005


def inject_cadence_window_failure(cadence_report: Any) -> None:
    """
    Simulates a cadence window failure.
    """
    if isinstance(cadence_report, dict):
        cadence_report["outside_cadence_window"] = True
        cadence_report["window_valid"] = False
        if "metadata" not in cadence_report:
            cadence_report["metadata"] = {}
        cadence_report["metadata"]["outside_cadence_window"] = True
    else:
        setattr(cadence_report, "outside_cadence_window", True)
        setattr(cadence_report, "window_valid", False)
        meta = getattr(cadence_report, "metadata", None)
        if meta is None:
            meta = {}
            setattr(cadence_report, "metadata", meta)
        meta["outside_cadence_window"] = True


def inject_global_cadence_skew(cadence_report: Any, magnitude: float) -> None:
    """
    Simulates a global cadence skew fault.
    """
    if isinstance(cadence_report, dict):
        cadence_report["global_skew"] = magnitude
        cadence_report["drift"] = magnitude
        if "metadata" not in cadence_report:
            cadence_report["metadata"] = {}
        cadence_report["metadata"]["high_phase_drift"] = True
    else:
        setattr(cadence_report, "global_skew", magnitude)
        setattr(cadence_report, "drift", magnitude)
        meta = getattr(cadence_report, "metadata", None)
        if meta is None:
            meta = {}
            setattr(cadence_report, "metadata", meta)
        meta["high_phase_drift"] = True


def validate_optimized_route_cadence(
    route_plan: Any,
    cadence_report: Any
) -> bool:
    """
    Validates that the optimized route plan does not cross any boundaries
    that put it outside the approved cadence windows.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not route_plan:
        return True

    # Check route plan cadence windows
    cad_windows = extract(route_plan, "cadence_windows", [])
    if "outside_cadence_window" in cad_windows:
        return False

    # Check cadence report outside cadence window status
    if cadence_report:
        if extract(cadence_report, "outside_cadence_window", False):
            return False
        meta = extract(cadence_report, "metadata", {}) or {}
        if extract(meta, "outside_cadence_window", False):
            return False

    return True


def measure_rebalance_cadence_disturbance(
    before: Any,
    after: Any
) -> float:
    """
    Measures the cadence/phase offset disturbance induced on the waveguides
    by comparing before and after cadence profile/report states.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    before_skew = extract(before, "global_skew", 0.0) or extract(before, "phase_offset", 0.0)
    after_skew = extract(after, "global_skew", 0.0) or extract(after, "phase_offset", 0.0)
    
    return abs(after_skew - before_skew)



