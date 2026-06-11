# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Resonant Cadence Controller
===============================
Formulates advisory suggestions and control decisions to stabilize resonant timing loops.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class ResonantCadenceControlPolicy:
    max_gain_limit: float = 0.5
    max_adjustment_limit: float = 0.2
    max_absorption_adjustment: float = 0.1
    court_token_required_for_sandbox: bool = True

@dataclass
class ResonantCadenceControlSuggestion:
    suggestion_id: str
    action: str  # "observe", "hold_epoch", "reduce_feedback_gain", "reduce_sync_step_size", etc.
    value: float = 0.0
    justification: str = ""

@dataclass
class ResonantCadenceControlDecision:
    decision_id: str
    verdict: str  # "authorized", "hold", "rollback", "quarantine"
    applied_suggestions: List[ResonantCadenceControlSuggestion] = field(default_factory=list)

@dataclass
class ResonantCadenceControlReport:
    report_id: str
    suggestions: List[ResonantCadenceControlSuggestion]
    decision: ResonantCadenceControlDecision
    state_classification: str


def suggest_resonant_cadence_control(
    feedback_report: Any,
    cadence_report: Any,
    policy: ResonantCadenceControlPolicy
) -> List[ResonantCadenceControlSuggestion]:
    """
    Generates advisory suggestions based on timing drift, skew, or phase error.
    """
    suggestions = []
    
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # Extract metrics from reports
    result = extract(feedback_report, "result", {})
    obs = extract(result, "final_observation", {})
    
    drift = extract(obs, "cadence_drift", 0.0) or extract(feedback_report, "drift", 0.0) or 0.0
    skew = extract(obs, "global_cadence_skew", 0.0) or extract(cadence_report, "global_skew", 0.0) or 0.0
    crosstalk = extract(obs, "crosstalk", 0.0) or 0.0
    reflection = extract(obs, "boundary_reflection", 0.0) or 0.0
    carrier_err = extract(obs, "carrier_phase_error", 0.0) or 0.0
    coh = extract(obs, "wavefront_coherence", 1.0) or 1.0

    # Build recommendations based on severity:
    if skew > 0.05:
        suggestions.append(ResonantCadenceControlSuggestion(
            suggestion_id=f"SUGG_RCS_{uuid.uuid4().hex[:4]}",
            action="reduce_sync_step_size",
            value=-0.1,
            justification=f"High global cadence skew {skew} detected."
        ))
    if drift > 0.03:
        suggestions.append(ResonantCadenceControlSuggestion(
            suggestion_id=f"SUGG_RCS_{uuid.uuid4().hex[:4]}",
            action="apply_candidate_cadence_offset",
            value=-drift,
            justification=f"Timing drift of {drift} exceeds normal levels."
        ))
    if reflection > 0.02:
        suggestions.append(ResonantCadenceControlSuggestion(
            suggestion_id=f"SUGG_RCS_{uuid.uuid4().hex[:4]}",
            action="increase_boundary_absorption",
            value=0.05,
            justification=f"Boundary reflection {reflection} is elevated."
        ))
    if crosstalk > 0.08:
        suggestions.append(ResonantCadenceControlSuggestion(
            suggestion_id=f"SUGG_RCS_{uuid.uuid4().hex[:4]}",
            action="quarantine_resonant_link",
            value=0.0,
            justification="Crosstalk spike detected; quarantining resonant link."
        ))
    if coh < 0.8:
        suggestions.append(ResonantCadenceControlSuggestion(
            suggestion_id=f"SUGG_RCS_{uuid.uuid4().hex[:4]}",
            action="quarantine_manifold_clock",
            value=0.0,
            justification="Wavefront coherence collapse detected."
        ))
    if not suggestions:
        suggestions.append(ResonantCadenceControlSuggestion(
            suggestion_id=f"SUGG_RCS_{uuid.uuid4().hex[:4]}",
            action="observe",
            value=0.0,
            justification="All resonant cadence control parameters are normal."
        ))
        
    return suggestions


def validate_resonant_control_bounds(
    suggestion: ResonantCadenceControlSuggestion,
    policy: ResonantCadenceControlPolicy
) -> bool:
    """
    Validates control suggestions against policy safety bounds.
    """
    act = suggestion.action
    val = abs(suggestion.value)
    
    if act == "reduce_feedback_gain" and val > policy.max_gain_limit:
        raise ValueError("Gain adjustment exceeds policy limit.")
    if act == "apply_candidate_cadence_offset" and val > policy.max_adjustment_limit:
        raise ValueError("Cadence offset adjustment exceeds policy limit.")
    if act == "apply_candidate_phase_offset" and val > policy.max_adjustment_limit:
        raise ValueError("Phase offset adjustment exceeds policy limit.")
    if act == "increase_boundary_absorption" and val > policy.max_absorption_adjustment:
        raise ValueError("Boundary absorption offset exceeds policy limit.")
        
    return True


def classify_resonant_cadence_state(report: Any) -> str:
    """
    Classifies timing loops into states: nominal, drift, skew_warning, quarantine_required.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    result = extract(report, "result", {})
    obs = extract(result, "final_observation", {})
    
    drift = extract(obs, "cadence_drift", 0.0)
    skew = extract(obs, "global_cadence_skew", 0.0)
    coh = extract(obs, "wavefront_coherence", 1.0)
    
    if coh < 0.8:
        return "quarantine_required"
    if skew > 0.04:
        return "skew_warning"
    if drift > 0.02:
        return "drift"
    return "nominal"


def validate_resonant_cadence_after_core_assembly(
    cadence_report: Any,
    assembly_report: Any
) -> bool:
    """
    Validates resonant cadence controller status after core assembly.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(assembly_report, "result")
    success = extract(res, "success", True) if res is not None else extract(assembly_report, "success", True)
    if not success:
        raise ValueError("Core assembly failed; holding resonant cadence validation.")

    meta = extract(cadence_report, "metadata", {}) or {}
    if meta.get("cadence_skew_breach") or meta.get("high_skew"):
        raise ValueError("Cadence skew breach blocks promotion.")
        
    return True


def validate_resonant_cadence_for_quantum_wavefront(
    report: Any,
    packet_report: Any
) -> bool:
    """
    Validates resonant cadence controller status against quantum wavefront calibration reports.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not packet_report:
        return True

    obs_list = extract(packet_report, "observations", [])
    for obs in obs_list:
        drift = extract(obs, "cadence_drift", 0.0)
        if drift > 0.05:
            raise ValueError("Cadence drift exceeds threshold during quantum wavefront calibration.")

    meta = extract(report, "metadata", {}) or {}
    if meta.get("cadence_skew_breach") or meta.get("high_skew"):
        raise ValueError("Cadence skew breach blocks quantum wavefront calibration.")

    return True


def export_cadence_stability_metrics_for_burnin(report: Any) -> Dict[str, Any]:
    """
    Exports cadence stability metrics for burn-in monitoring.
    """
    if not report:
        return {"cadence_drift": 0.005}
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    meta = extract(report, "metadata", {}) or {}
    return {
        "cadence_drift": float(meta.get("cadence_drift", 0.005))
    }


def validate_autonomous_cadence_over_burnin(metric_window: Any) -> bool:
    """
    Validates autonomous cadence sync stability. Unbounded loop immediately fails.
    """
    metrics = getattr(metric_window, "metrics", {}) or {}
    drift = metrics.get("cadence_drift")
    if drift and hasattr(drift, "values"):
        if any(v > 0.02 for v in drift.values):
            return False
        if any(v > 999.0 for v in drift.values):
            return False
    return True



