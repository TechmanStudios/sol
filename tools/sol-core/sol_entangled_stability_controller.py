# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Stability Controller
==================================
Formulates advisory stabilization suggestions, boundary validation, and health state classification.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class EntangledStabilityControlPolicy:
    coherence_threshold: float = 0.90
    drift_threshold: float = 0.05
    crosstalk_threshold: float = 0.05
    reflection_threshold: float = 0.05
    carrier_error_threshold: float = 0.05

@dataclass
class EntangledStabilityControlSuggestion:
    suggestion_id: str
    action: str
    justification: str
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledStabilityControlDecision:
    decision_id: str
    suggestion: EntangledStabilityControlSuggestion
    applied: bool
    token: Optional[str] = None

@dataclass
class EntangledStabilityControlReport:
    report_id: str
    state: str  # "stable" | "unstable" | "drift_detected" | "crosstalk_warning"
    suggestions: List[EntangledStabilityControlSuggestion]
    timestamp: float = field(default_factory=time.time)


def suggest_entangled_stability_control(
    calibration_report: Any,
    feedback_policy: Any
) -> EntangledStabilityControlReport:
    """
    Formulates a list of suggestions based on errors found in calibration.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(calibration_report, "result")
    success = extract(res, "success", True) if res else True
    errors = extract(res, "errors", []) if res else []
    
    suggestions = []
    
    # Check baseline parameters from report
    baseline = extract(calibration_report, "baseline")
    drift = extract(baseline, "phase_drift", 0.0) if baseline else 0.0
    crosstalk = extract(baseline, "crosstalk", 0.0) if baseline else 0.0
    reflection = extract(baseline, "boundary_reflection", 0.0) if baseline else 0.0
    coherence = extract(baseline, "phase_coherence", 1.0) if baseline else 1.0
    
    # Formulate suggestions based on observations
    if errors or not success:
        reason = "; ".join(errors)
        if "phase" in reason.lower():
            suggestions.append(EntangledStabilityControlSuggestion(
                suggestion_id="SUG_PHASE",
                action="request_phase_realign",
                justification="Phase realign needed due to calibration errors.",
                parameters={"phase_step": 0.01}
            ))
        elif "deadlock" in reason.lower():
            suggestions.append(EntangledStabilityControlSuggestion(
                suggestion_id="SUG_ABORT",
                action="quarantine_manifold",
                justification="Manifold quarantine due to deadlock.",
                parameters={"manifold_id": "M1"}
            ))
        else:
            suggestions.append(EntangledStabilityControlSuggestion(
                suggestion_id="SUG_HOLD",
                action="hold_epoch",
                justification=f"Holding epoch: {reason}"
            ))
    else:
        # Check drift, crosstalk, reflection values from baseline
        if drift > 0.05:
            suggestions.append(EntangledStabilityControlSuggestion(
                suggestion_id="SUG_REALIGN",
                action="request_phase_realign",
                justification="Phase drift above threshold.",
                parameters={"phase_step": 0.01}
            ))
        if crosstalk > 0.05:
            suggestions.append(EntangledStabilityControlSuggestion(
                suggestion_id="SUG_QUARANTINE_LINK",
                action="quarantine_entanglement_link",
                justification="High crosstalk leakage detected.",
                parameters={"link_id": "LINK_M1_M2"}
            ))
        if reflection > 0.05:
            suggestions.append(EntangledStabilityControlSuggestion(
                suggestion_id="SUG_PML",
                action="increase_boundary_absorption",
                justification="Boundary reflection breach detected.",
                parameters={"damping_step": 0.02}
            ))
            
    if not suggestions:
        suggestions.append(EntangledStabilityControlSuggestion(
            suggestion_id="SUG_OBSERVE",
            action="observe",
            justification="Wavefront is stable; continuing observation."
        ))
        
    state = "stable"
    if any(s.action == "hold_epoch" for s in suggestions):
        state = "unstable"
    elif any(s.action == "request_phase_realign" for s in suggestions):
        state = "drift_detected"
    elif any(s.action == "quarantine_entanglement_link" for s in suggestions):
        state = "crosstalk_warning"
        
    import uuid
    report_id = f"ESCR_{uuid.uuid4().hex[:8]}"
    return EntangledStabilityControlReport(
        report_id=report_id,
        state=state,
        suggestions=suggestions
    )


def validate_entangled_control_bounds(
    suggestion: EntangledStabilityControlSuggestion,
    policy: EntangledStabilityControlPolicy
) -> bool:
    """
    Enforces maximum adjustment bounds on planned actions.
    """
    action = suggestion.action
    params = suggestion.parameters
    
    if action == "request_phase_realign":
        step = params.get("phase_step", 0.0)
        if abs(step) > policy.drift_threshold:
            return False
    elif action == "increase_boundary_absorption":
        step = params.get("damping_step", 0.0)
        if abs(step) > policy.reflection_threshold:
            return False
            
    return True


def classify_entangled_stability_state(report: EntangledStabilityControlReport) -> str:
    """
    Determines if report suggestions require holding or aborting.
    """
    for sug in report.suggestions:
        if sug.action in ["hold_epoch", "quarantine_manifold", "rollback_feedback_loop"]:
            return "critical"
    return "nominal"
