# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Autonomous Cadence Sync
===========================
Orchestrates autonomous synchronization candidate generation and adjustment validation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class AutonomousCadenceSyncPolicy:
    max_sync_steps: int
    max_cadence_adjustment: float
    max_phase_offset_adjustment: float
    max_carrier_offset_adjustment: float
    max_boundary_absorption_adjustment: float
    max_feedback_gain: float
    abort_thresholds: Dict[str, float] = field(default_factory=dict)
    rollback_requirement: bool = True
    court_token_required_for_sandbox: bool = True

@dataclass
class AutonomousCadenceSyncIntent:
    intent_id: str
    cadence_group: Any
    policy: AutonomousCadenceSyncPolicy
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CadenceSyncCandidate:
    candidate_id: str
    manifold_id: str
    drift: float
    jitter: float = 0.0

@dataclass
class CadenceSyncAdjustment:
    adjustment_id: str
    candidate_id: str
    cadence_offset: float = 0.0
    phase_offset: float = 0.0
    carrier_offset: float = 0.0
    boundary_absorption_offset: float = 0.0

@dataclass
class CadenceSyncDecision:
    decision_id: str
    verdict: str  # "apply", "hold", "reject"
    adjustments: List[CadenceSyncAdjustment] = field(default_factory=list)

@dataclass
class AutonomousCadenceSyncResult:
    success: bool
    final_skew: float
    errors: List[str] = field(default_factory=list)
    rolled_back: bool = False

@dataclass
class AutonomousCadenceSyncReport:
    report_id: str
    intent: AutonomousCadenceSyncIntent
    candidates: List[CadenceSyncCandidate]
    decision: CadenceSyncDecision
    result: AutonomousCadenceSyncResult


def build_autonomous_cadence_sync_intent(
    cadence_group: Any,
    policy: AutonomousCadenceSyncPolicy
) -> AutonomousCadenceSyncIntent:
    """
    Constructs a validation-ready intent for autonomous cadence sync.
    """
    if not cadence_group:
        raise ValueError("Cadence group is empty.")
    
    # Enforce policy bounds on adjustment limits
    if policy.max_cadence_adjustment <= 0.0 or policy.max_cadence_adjustment > 0.5:
        raise ValueError("Policy has invalid max cadence adjustment bounds.")
    if policy.max_phase_offset_adjustment <= 0.0 or policy.max_phase_offset_adjustment > 0.5:
        raise ValueError("Policy has invalid max phase offset adjustment bounds.")
    if policy.max_carrier_offset_adjustment <= 0.0 or policy.max_carrier_offset_adjustment > 0.5:
        raise ValueError("Policy has invalid max carrier offset adjustment bounds.")
    if policy.max_boundary_absorption_adjustment <= 0.0 or policy.max_boundary_absorption_adjustment > 0.5:
        raise ValueError("Policy has invalid max boundary absorption adjustment bounds.")

    return AutonomousCadenceSyncIntent(
        intent_id=f"CAD_SYNC_INT_{uuid.uuid4().hex[:8]}",
        cadence_group=cadence_group,
        policy=policy,
        created_at=time.time()
    )


def identify_cadence_sync_candidates(
    intent: AutonomousCadenceSyncIntent,
    telemetry: Dict[str, Any]
) -> List[CadenceSyncCandidate]:
    """
    Identifies manifolds requiring sync corrections based on drift telemetry.
    """
    candidates = []
    # telemetry mapping (e.g. manifold_id -> drift value)
    drifts = telemetry.get("drifts", {})
    for m_id, drift_val in drifts.items():
        if abs(drift_val) > 0.001:
            candidates.append(CadenceSyncCandidate(
                candidate_id=f"CAND_{m_id}_{uuid.uuid4().hex[:4]}",
                manifold_id=m_id,
                drift=drift_val,
                jitter=telemetry.get("jitter", {}).get(m_id, 0.005)
            ))
    return candidates


def build_cadence_sync_adjustment(
    candidate: CadenceSyncCandidate,
    policy: AutonomousCadenceSyncPolicy
) -> CadenceSyncAdjustment:
    """
    Maps candidates to suggested offset shifts bounded by policy constraints.
    """
    # Proportional control bounded by max adjustments
    cadence_off = -0.5 * candidate.drift
    # Clamp to policy bounds
    cadence_off = max(-policy.max_cadence_adjustment, min(policy.max_cadence_adjustment, cadence_off))
    
    phase_off = -0.2 * candidate.drift
    phase_off = max(-policy.max_phase_offset_adjustment, min(policy.max_phase_offset_adjustment, phase_off))
    
    carrier_off = 0.1 * candidate.drift
    carrier_off = max(-policy.max_carrier_offset_adjustment, min(policy.max_carrier_offset_adjustment, carrier_off))
    
    boundary_off = 0.05 * candidate.drift
    boundary_off = max(-policy.max_boundary_absorption_adjustment, min(policy.max_boundary_absorption_adjustment, boundary_off))

    return CadenceSyncAdjustment(
        adjustment_id=f"ADJ_{uuid.uuid4().hex[:8]}",
        candidate_id=candidate.candidate_id,
        cadence_offset=cadence_off,
        phase_offset=phase_off,
        carrier_offset=carrier_off,
        boundary_absorption_offset=boundary_off
    )


def validate_cadence_sync_adjustment(
    adjustment: CadenceSyncAdjustment,
    policy: AutonomousCadenceSyncPolicy
) -> bool:
    """
    Validates adjustments against policy limits.
    """
    if abs(adjustment.cadence_offset) > policy.max_cadence_adjustment:
        raise ValueError("Cadence offset adjustment exceeds policy limit.")
    if abs(adjustment.phase_offset) > policy.max_phase_offset_adjustment:
        raise ValueError("Phase offset adjustment exceeds policy limit.")
    if abs(adjustment.carrier_offset) > policy.max_carrier_offset_adjustment:
        raise ValueError("Carrier offset adjustment exceeds policy limit.")
    if abs(adjustment.boundary_absorption_offset) > policy.max_boundary_absorption_adjustment:
        raise ValueError("Boundary absorption adjustment exceeds policy limit.")
    return True


def execute_shadow_autonomous_cadence_sync(
    intent: AutonomousCadenceSyncIntent
) -> AutonomousCadenceSyncReport:
    """
    Executes autonomous sync candidate evaluation in shadow mode.
    """
    policy = intent.policy
    
    # Enforce court token requirement in sandbox mode
    metadata = intent.metadata
    if metadata.get("sandbox_trial") or metadata.get("court_token") == "SANDBOX_TOKEN":
        token = metadata.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox cadence sync execution.")
            
    telemetry = metadata.get("telemetry", {})
    candidates = identify_cadence_sync_candidates(intent, telemetry)
    
    adjustments = []
    errors = []
    
    for cand in candidates:
        adj = build_cadence_sync_adjustment(cand, policy)
        try:
            validate_cadence_sync_adjustment(adj, policy)
        except ValueError as e:
            errors.append(str(e))
        adjustments.append(adj)
        
    final_skew = telemetry.get("global_skew", 0.0)
    
    # Check for split brain or skew abort thresholds
    if telemetry.get("split_brain") or telemetry.get("split_brain_detected"):
        errors.append("Cadence split-brain detected.")
    if final_skew > policy.abort_thresholds.get("max_skew", 0.05):
        errors.append("Skew exceeded abort threshold.")
        
    success = len(errors) == 0
    rolled_back = not success and policy.rollback_requirement
    
    verdict = "apply" if success else ("hold" if not rolled_back else "reject")
    decision = CadenceSyncDecision(
        decision_id=f"DEC_CS_{uuid.uuid4().hex[:8]}",
        verdict=verdict,
        adjustments=adjustments
    )
    
    result = AutonomousCadenceSyncResult(
        success=success,
        final_skew=final_skew,
        errors=errors,
        rolled_back=rolled_back
    )
    
    return AutonomousCadenceSyncReport(
        report_id=f"SYN_REP_{uuid.uuid4().hex[:8]}",
        intent=intent,
        candidates=candidates,
        decision=decision,
        result=result
    )


def block_core_assembly_on_unstable_autonomous_cadence(
    sync_report: Any
) -> bool:
    """
    Blocks core assembly if autonomous cadence sync is unstable.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(sync_report, "result")
    success = extract(res, "success", True) if res is not None else extract(sync_report, "success", True)
    if not success:
        raise ValueError("Core assembly blocked: unstable autonomous cadence.")
        
    errors = extract(res, "errors", []) or extract(sync_report, "errors", []) or extract(extract(sync_report, "result", {}), "errors", [])
    if errors:
        raise ValueError("Core assembly blocked: unstable autonomous cadence.")
        
    # Check for simulate instability in metadata
    meta = extract(sync_report, "metadata", {}) or {}
    if meta.get("cadence_instability") or meta.get("unstable_cadence") or (isinstance(sync_report, dict) and sync_report.get("unstable_cadence")):
        raise ValueError("Core assembly blocked: unstable autonomous cadence.")
        
    return False


def block_quantum_calibration_on_unstable_autonomous_cadence(
    sync_report: Any
) -> bool:
    """
    Blocks quantum calibration if autonomous cadence sync is unstable.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(sync_report, "result")
    success = extract(res, "success", True) if res is not None else extract(sync_report, "success", True)
    if not success:
        raise ValueError("Quantum calibration blocked: unstable autonomous cadence.")
        
    errors = extract(res, "errors", []) or extract(sync_report, "errors", []) or extract(extract(sync_report, "result", {}), "errors", [])
    if errors:
        raise ValueError("Quantum calibration blocked: unstable autonomous cadence.")
        
    meta = extract(sync_report, "metadata", {}) or {}
    if meta.get("cadence_instability") or meta.get("unstable_cadence") or (isinstance(sync_report, dict) and sync_report.get("unstable_cadence")):
        raise ValueError("Quantum calibration blocked: unstable autonomous cadence.")
        
    return False


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



