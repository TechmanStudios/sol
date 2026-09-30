# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Resonant Feedback
===============================
Tracks and simulates closed-loop resonant feedback for timing and phase synchronization in shadow/sandbox mode.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class ResonantFeedbackId:
    loop_id: str
    epoch_id: str

@dataclass
class ResonantFeedbackParticipant:
    manifold_id: str
    clock_id: str
    active: bool = True

@dataclass
class ResonantFeedbackPolicy:
    max_feedback_gain: float
    max_steps: int
    abort_thresholds: Dict[str, float] = field(default_factory=dict)
    rollback_requirement: bool = True
    court_token_required_for_sandbox: bool = True

@dataclass
class ResonantFeedbackObservation:
    observation_id: str
    timestamp: float
    resonant_phase_coherence: float
    entanglement_phase_coherence: float
    cadence_drift: float
    global_cadence_skew: float
    carrier_phase_error: float
    wavefront_coherence: float
    crosstalk: float
    boundary_reflection: float
    pml_absorption_effectiveness: float
    active_mass_preservation: float
    lane_timing_consistency: float

@dataclass
class ResonantFeedbackSignal:
    signal_id: str
    error_vector: Dict[str, float]

@dataclass
class ResonantFeedbackAction:
    action_id: str
    suggested_adjustments: Dict[str, float]

@dataclass
class ResonantFeedbackStep:
    step_idx: int
    observation: ResonantFeedbackObservation
    signal: ResonantFeedbackSignal
    action: ResonantFeedbackAction

@dataclass
class ResonantFeedbackResult:
    success: bool
    step_count: int
    final_observation: ResonantFeedbackObservation
    errors: List[str] = field(default_factory=list)
    rolled_back: bool = False

@dataclass
class ResonantFeedbackReport:
    report_id: str
    loop_id: str
    policy: ResonantFeedbackPolicy
    result: ResonantFeedbackResult
    history: List[ResonantFeedbackStep] = field(default_factory=list)


def build_resonant_feedback_loop(
    participants: List[ResonantFeedbackParticipant],
    policy: ResonantFeedbackPolicy
) -> Dict[str, Any]:
    """
    Constructs a resonant feedback loop structure.
    """
    if not participants:
        raise ValueError("Cannot build feedback loop: participants list is empty.")
    
    # Enforce positive step limit
    if policy.max_steps <= 0:
        raise ValueError("Feedback policy must specify max_steps > 0.")
    # Enforce policy bounds on gain
    if policy.max_feedback_gain <= 0.0 or policy.max_feedback_gain > 1.0:
        raise ValueError("Feedback policy has invalid feedback gain bounds.")

    loop_id = f"RES_LOOP_{uuid.uuid4().hex[:8]}"
    return {
        "loop_id": loop_id,
        "participants": participants,
        "policy": policy,
        "active": True
    }


def validate_resonant_feedback_loop(loop: Dict[str, Any]) -> bool:
    """
    Validates resonant feedback loop structure and policy constraints.
    """
    if not loop.get("loop_id"):
        raise ValueError("Resonant feedback loop is missing loop_id.")
    if not loop.get("participants"):
        raise ValueError("Resonant feedback loop has no participants.")
    policy = loop.get("policy")
    if not policy:
        raise ValueError("Resonant feedback loop has no policy.")
    if getattr(policy, "max_feedback_gain", 0.0) <= 0.0:
        raise ValueError("Feedback gain must be positive.")
    return True


def sample_resonant_feedback_observation(
    loop: Dict[str, Any],
    telemetry: Dict[str, Any]
) -> ResonantFeedbackObservation:
    """
    Extracts telemetry values and builds a ResonantFeedbackObservation.
    """
    def extract(name, default):
        return telemetry.get(name, default)

    return ResonantFeedbackObservation(
        observation_id=f"OBS_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        resonant_phase_coherence=extract("resonant_phase_coherence", 1.0),
        entanglement_phase_coherence=extract("entanglement_phase_coherence", 1.0),
        cadence_drift=extract("cadence_drift", 0.0),
        global_cadence_skew=extract("global_cadence_skew", 0.0),
        carrier_phase_error=extract("carrier_phase_error", 0.0),
        wavefront_coherence=extract("wavefront_coherence", 1.0),
        crosstalk=extract("crosstalk", 0.0),
        boundary_reflection=extract("boundary_reflection", 0.0),
        pml_absorption_effectiveness=extract("pml_absorption_effectiveness", 1.0),
        active_mass_preservation=extract("active_mass_preservation", 1.0),
        lane_timing_consistency=extract("lane_timing_consistency", 1.0)
    )


def plan_resonant_feedback_action(
    observation: ResonantFeedbackObservation,
    policy: ResonantFeedbackPolicy
) -> ResonantFeedbackAction:
    """
    Formulates advisory correction offsets based on drift and policy gain limits.
    """
    gain = policy.max_feedback_gain
    adjustments = {
        "phase_offset": -1.0 * observation.cadence_drift * gain,
        "damping": 0.01 * observation.crosstalk * gain
    }
    return ResonantFeedbackAction(
        action_id=f"ACT_{uuid.uuid4().hex[:8]}",
        suggested_adjustments=adjustments
    )


def execute_shadow_resonant_feedback(
    loop: Dict[str, Any],
    observations: List[ResonantFeedbackObservation]
) -> ResonantFeedbackReport:
    """
    Simulates step-by-step resonant feedback loop corrections.
    """
    validate_resonant_feedback_loop(loop)
    policy = loop["policy"]
    history = []
    
    current_obs = observations[0] if observations else ResonantFeedbackObservation(
        observation_id="OBS_EMPTY", timestamp=time.time(),
        resonant_phase_coherence=1.0, entanglement_phase_coherence=1.0,
        cadence_drift=0.0, global_cadence_skew=0.0, carrier_phase_error=0.0,
        wavefront_coherence=1.0, crosstalk=0.0, boundary_reflection=0.0,
        pml_absorption_effectiveness=1.0, active_mass_preservation=1.0,
        lane_timing_consistency=1.0
    )

    errors = []
    
    # Check for abort/failure conditions based on policy thresholds
    abort_thresh = policy.abort_thresholds
    
    if current_obs.resonant_phase_coherence < abort_thresh.get("min_resonance_coherence", 0.8):
        errors.append("Resonant phase decoherence blocks promotion.")
    if current_obs.entanglement_phase_coherence < abort_thresh.get("min_entanglement_coherence", 0.8):
        errors.append("Entanglement coherence failure blocks promotion.")
    if current_obs.crosstalk > abort_thresh.get("max_crosstalk", 0.1):
        errors.append("Crosstalk spike blocks promotion.")
    if current_obs.boundary_reflection > abort_thresh.get("max_reflection", 0.05):
        errors.append("Boundary reflection breach blocks promotion.")
    if current_obs.pml_absorption_effectiveness < abort_thresh.get("min_pml_absorption", 0.9):
        errors.append("PML weakening blocks promotion.")
        
    step_idx = 0
    for obs in observations:
        sig = ResonantFeedbackSignal(
            signal_id=f"SIG_{uuid.uuid4().hex[:8]}",
            error_vector={"cadence_drift": obs.cadence_drift}
        )
        act = plan_resonant_feedback_action(obs, policy)
        history.append(ResonantFeedbackStep(
            step_idx=step_idx,
            observation=obs,
            signal=sig,
            action=act
        ))
        step_idx += 1
        if step_idx >= policy.max_steps:
            break
            
    success = len(errors) == 0
    rolled_back = not success and policy.rollback_requirement
    
    result = ResonantFeedbackResult(
        success=success,
        step_count=step_idx,
        final_observation=current_obs,
        errors=errors,
        rolled_back=rolled_back
    )
    
    return ResonantFeedbackReport(
        report_id=f"RES_REP_{uuid.uuid4().hex[:8]}",
        loop_id=loop["loop_id"],
        policy=policy,
        result=result,
        history=history
    )


def summarize_resonant_feedback(result: ResonantFeedbackResult) -> Dict[str, Any]:
    """
    Returns summary statistics for the execution.
    """
    return {
        "success": result.success,
        "step_count": result.step_count,
        "rolled_back": result.rolled_back,
        "final_drift": result.final_observation.cadence_drift
    }


def validate_resonant_feedback_after_quantum_calibration(
    feedback_report: Any,
    quantum_report: Any
) -> bool:
    """
    Validates resonant feedback loop status after quantum wavefront calibration.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not feedback_report:
        return True

    res = extract(feedback_report, "result")
    success = extract(res, "success", True) if res is not None else extract(feedback_report, "success", True)
    if not success:
        return False

    meta = extract(feedback_report, "metadata", {}) or {}
    if meta.get("production_overwrite") or meta.get("live_mutation"):
        return False

    return True


def measure_quantum_feedback_disturbance(
    before: Any,
    after: Any
) -> float:
    """
    Measures quantum feedback loop disturbance.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    obs_b = extract(extract(before, "result", {}), "final_observation") or before
    obs_a = extract(extract(after, "result", {}), "final_observation") or after
    
    drift_b = extract(obs_b, "cadence_drift", 0.0)
    drift_a = extract(obs_a, "cadence_drift", 0.0)
    
    return abs(drift_a - drift_b)

