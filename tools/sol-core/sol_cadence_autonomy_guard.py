# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Cadence Autonomy Guard
==========================
Guards temporal clock synchronization against infinite loops and unauthorized live overwrites.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class CadenceAutonomyGuardPolicy:
    max_allowable_gain: float = 0.5
    max_loop_iterations: int = 100
    allow_live_overwrites: bool = False
    allow_production_mutations: bool = False
    require_rollback_refs: bool = True
    require_ranger_evidence: bool = True

@dataclass
class CadenceAutonomyGuardSnapshot:
    snapshot_id: str
    timestamp: float
    group_id: str
    active_profile_count: int
    active_profile_hashes: Dict[str, str]

@dataclass
class CadenceAutonomyGuardDecision:
    decision_id: str
    passed: bool
    blocked_reasons: List[str] = field(default_factory=list)

@dataclass
class CadenceAutonomyGuardReport:
    report_id: str
    snapshot: CadenceAutonomyGuardSnapshot
    decision: CadenceAutonomyGuardDecision
    timestamp: float = field(default_factory=time.time)


def capture_cadence_autonomy_guard_snapshot(
    cadence_group: Any
) -> CadenceAutonomyGuardSnapshot:
    """
    Captures active profiles and active clocks configurations to guard against live overwrites.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    group_id = extract(cadence_group, "group_id", "GROUP_DEFAULT")
    participants = extract(cadence_group, "participants", [])
    
    # Store mock hashes of active profiles
    profile_hashes = {}
    for p in participants:
        m_id = extract(p, "manifold_id", "unknown")
        profile_hashes[m_id] = f"HASH_{m_id}_ACTIVE"

    return CadenceAutonomyGuardSnapshot(
        snapshot_id=f"GUARD_SNAP_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        group_id=group_id,
        active_profile_count=len(participants),
        active_profile_hashes=profile_hashes
    )


def evaluate_cadence_autonomy_guard(
    sync_report: Any,
    feedback_report: Any,
    policy: CadenceAutonomyGuardPolicy
) -> CadenceAutonomyGuardReport:
    """
    Evaluates sync adjustments and feedback signals to ensure safety constraints.
    Blocks overwrite attempts and infinite loops.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    blocked_reasons = []

    # 1. Block production/default cadence mutation
    if policy.allow_production_mutations:
        # We must protect production profiles at all costs
        blocked_reasons.append("Production cadence mutation is explicitly prohibited.")

    # 2. Block active cadence-profile/phase-table/carrier-registry overwrite
    # Check reports for any overwrite flags
    if sync_report:
        intent = extract(sync_report, "intent", {})
        metadata = extract(intent, "metadata", {}) or {}
        if metadata.get("mutate_production_cadence") or metadata.get("overwrite_active_cadence"):
            blocked_reasons.append("Active cadence-profile overwrite attempt is rejected.")
        if metadata.get("overwrite_active_phase_table"):
            blocked_reasons.append("Active phase-table overwrite attempt is rejected.")
        if metadata.get("overwrite_active_carrier_registry"):
            blocked_reasons.append("Active carrier-registry overwrite attempt is rejected.")
            
        # Check loop iteration bounds
        step_count = extract(sync_report, "step_count", 0) or extract(extract(sync_report, "result", {}), "step_count", 0) or 0
        if step_count > policy.max_loop_iterations:
            blocked_reasons.append("Infinite sync loops detected and blocked.")

    if feedback_report:
        res = extract(feedback_report, "result", {})
        history = extract(feedback_report, "history", [])
        if len(history) > policy.max_loop_iterations or extract(res, "step_count", 0) > policy.max_loop_iterations:
            blocked_reasons.append("Infinite feedback loop detected and blocked.")
            
        pol = extract(feedback_report, "policy", None)
        if pol:
            gain = getattr(pol, "max_feedback_gain", 0.0)
            if gain > policy.max_allowable_gain:
                blocked_reasons.append("Unbounded feedback gain is rejected.")

    # 3. Require rollback references
    if policy.require_rollback_refs:
        # check if rollback reference exists
        has_rollback = False
        if sync_report:
            intent = extract(sync_report, "intent", {})
            metadata = extract(intent, "metadata", {}) or {}
            if metadata.get("rollback_snapshot") or metadata.get("rollback_snapshot_ref"):
                has_rollback = True
        if feedback_report:
            # check policy/metadata
            pol = extract(feedback_report, "policy", None)
            if pol and getattr(pol, "rollback_requirement", False):
                has_rollback = True
                
        if not has_rollback:
            blocked_reasons.append("Cadence changes without rollback references are blocked.")

    # 4. Require ranger evidence
    if policy.require_ranger_evidence:
        # Check if ranger packet or evidence is present
        has_ranger = False
        if sync_report:
            intent = extract(sync_report, "intent", {})
            metadata = extract(intent, "metadata", {}) or {}
            if metadata.get("ranger_evidence") or metadata.get("ranger_evidence_complete"):
                has_ranger = True
        if not has_ranger:
            blocked_reasons.append("Sync progression without ranger evidence is blocked.")

    # Capture snapshot
    snap = capture_cadence_autonomy_guard_snapshot({"group_id": "MOCK_GROUP", "participants": []})
    
    passed = len(blocked_reasons) == 0
    decision = CadenceAutonomyGuardDecision(
        decision_id=f"DEC_GUARD_{uuid.uuid4().hex[:8]}",
        passed=passed,
        blocked_reasons=blocked_reasons
    )
    
    return CadenceAutonomyGuardReport(
        report_id=f"GUARD_REP_{uuid.uuid4().hex[:8]}",
        snapshot=snap,
        decision=decision
    )


def block_unbounded_cadence_autonomy(reason: str) -> None:
    """
    Explicitly raises an exception to block execution if unbounded autonomy is detected.
    """
    raise ValueError(f"Unbounded cadence autonomy blocked: {reason}")


def verify_autonomy_remains_bounded(report: CadenceAutonomyGuardReport) -> bool:
    """
    Asserts that guard evaluation checks passed.
    """
    if not report.decision.passed:
        block_unbounded_cadence_autonomy("; ".join(report.decision.blocked_reasons))
    return True
