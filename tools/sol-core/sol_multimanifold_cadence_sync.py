# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Multi-Manifold Cadence Synchronization
==========================================
Coordinates cadence profiles across multiple manifolds to establish coherence.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_temporal_cadence import (
    TemporalCadenceProfile,
    validate_cadence_after_entangled_feedback,
    measure_feedback_induced_cadence_drift
)

@dataclass
class CadenceSyncParticipant:
    manifold_id: str
    profile_id: str
    status: str = "synchronized"

@dataclass
class CadenceSyncGroup:
    sync_group_id: str
    participants: List[CadenceSyncParticipant] = field(default_factory=list)
    profiles: Dict[str, TemporalCadenceProfile] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CadenceSyncIntent:
    intent_id: str
    manifolds: List[str] = field(default_factory=list)
    target_skew: float = 0.05
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CadenceSyncPlan:
    plan_id: str
    intent: CadenceSyncIntent
    group: CadenceSyncGroup
    steps: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class CadenceSyncResult:
    success: bool
    final_skew: float
    errors: List[str] = field(default_factory=list)

@dataclass
class CadenceSyncReport:
    report_id: str
    sync_group: CadenceSyncGroup
    result: CadenceSyncResult
    passed_gates: bool
    global_skew: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_cadence_sync_group(manifolds: List[Any], profiles: Dict[str, TemporalCadenceProfile]) -> CadenceSyncGroup:
    """
    Builds a synchronization group for 2 or 3+ manifolds.
    """
    participants = []
    sync_profiles = {}
    
    def extract_id(m):
        if isinstance(m, dict):
            return m.get("manifold_id") or m.get("id") or str(m)
        return getattr(m, "manifold_id", None) or getattr(m, "id", None) or str(m)
        
    for m in manifolds:
        m_id = extract_id(m)
        profile = profiles.get(m_id)
        if not profile:
            raise ValueError(f"Missing cadence profile for manifold {m_id}")
        participants.append(CadenceSyncParticipant(
            manifold_id=m_id,
            profile_id=f"PROF_{m_id}"
        ))
        sync_profiles[m_id] = profile
        
    import time
    group_id = f"SYNC_GP_{int(time.time() * 1000)}"
    return CadenceSyncGroup(
        sync_group_id=group_id,
        participants=participants,
        profiles=sync_profiles
    )


def validate_cadence_sync_group(group: CadenceSyncGroup) -> bool:
    """
    Validates synchronization group completeness.
    """
    if not group.participants:
        raise ValueError("Cadence sync group must have at least one participant.")
    for p in group.participants:
        if p.manifold_id not in group.profiles:
            raise ValueError(f"Participant {p.manifold_id} is missing an associated cadence profile.")
        if not p.status:
            raise ValueError(f"Participant {p.manifold_id} has invalid status.")
    return True


def plan_multimanifold_cadence_sync(intent: CadenceSyncIntent, group: CadenceSyncGroup) -> CadenceSyncPlan:
    """
    Formulates coordination adjustments to bring skew within target boundaries.
    """
    validate_cadence_sync_group(group)
    steps = []
    
    # Calculate target phase (average phase_offset)
    offsets = [p.phase_offset for p in group.profiles.values()]
    avg_offset = sum(offsets) / len(offsets) if offsets else 0.0
    
    for m_id, profile in group.profiles.items():
        diff = avg_offset - profile.phase_offset
        if abs(diff) > 0.001:
            steps.append({
                "action": "adjust_cadence_phase",
                "manifold_id": m_id,
                "adjustment": diff
            })
            
    import time
    plan_id = f"SYNC_PLAN_{int(time.time() * 1000)}"
    return CadenceSyncPlan(
        plan_id=plan_id,
        intent=intent,
        group=group,
        steps=steps
    )


def execute_shadow_cadence_sync(plan: CadenceSyncPlan) -> CadenceSyncReport:
    """
    Runs shadow execution to assess resulting skew.
    """
    errors = []
    
    # Calculate global skew (max diff between phase offsets)
    offsets = [p.phase_offset for p in plan.group.profiles.values()]
    skew = max(offsets) - min(offsets) if offsets else 0.0
    
    # Simulate potential failures from intent metadata
    if plan.intent.metadata.get("simulate_sync_failure"):
        skew = plan.intent.target_skew + 0.05
        errors.append("Simulated synchronization failure.")
        
    if skew > plan.intent.target_skew:
        errors.append(f"Global cadence skew {skew:.4f} exceeds target {plan.intent.target_skew:.4f}")
        
    success = len(errors) == 0
    result = CadenceSyncResult(
        success=success,
        final_skew=skew,
        errors=errors
    )
    
    import time
    report_id = f"SYNC_REP_{plan.plan_id}_{int(time.time())}"
    return CadenceSyncReport(
        report_id=report_id,
        sync_group=plan.group,
        result=result,
        passed_gates=success,
        global_skew=skew,
        metadata=dict(plan.intent.metadata)
    )


def summarize_cadence_sync(result: CadenceSyncResult) -> Dict[str, Any]:
    """
    Summarizes outcomes of synchronization.
    """
    return {
        "sync_success": result.success,
        "final_skew": result.final_skew,
        "error_count": len(result.errors),
        "errors": list(result.errors)
    }


def run_shadow_autonomous_multimanifold_cadence_sync(
    sync_intent: Any
) -> Any:
    """
    Simulates autonomous multi-manifold cadence sync in shadow mode.
    Supports 2-manifold, 3+ manifolds, independent shard boundary groups,
    entangled wavefront participants, and split-brain detection.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    group = extract(sync_intent, "cadence_group")
    policy = extract(sync_intent, "policy")
    metadata = extract(sync_intent, "metadata", {}) or {}

    participants = extract(group, "participants", [])
    num_participants = len(participants)
    
    errors = []
    
    # Split brain detection
    if metadata.get("split_brain") or metadata.get("split_brain_detected"):
        errors.append("Cadence split-brain detected across manifolds.")
        
    # Boundary group check
    if metadata.get("shard_boundary_conflict"):
        errors.append("Independent shard boundary group synchronization conflict.")
        
    # Wavefront check
    if metadata.get("wavefront_instability"):
        errors.append("Entangled wavefront participant calibration unstable.")

    skew = metadata.get("telemetry", {}).get("global_skew", 0.0) if isinstance(metadata, dict) else 0.0
    # check policy limit
    max_skew = getattr(policy, "max_skew", 0.05) if policy else 0.05
    if skew > max_skew:
        errors.append(f"Global cadence skew {skew} exceeds limit {max_skew}.")

    import uuid
    success = len(errors) == 0
    return {
        "report_id": f"AUTO_SYN_REP_{uuid.uuid4().hex[:8]}",
        "sync_intent": sync_intent,
        "manifold_count": num_participants,
        "success": success,
        "global_skew": skew,
        "errors": errors
    }


def validate_autonomous_sync_result(
    sync_report: Any
) -> bool:
    """
    Verifies that the autonomous sync report did not encounter any errors or split-brain.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(sync_report, "success", False)
    errors = extract(sync_report, "errors", [])
    if not success or errors:
        return False
    return True

