# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Governance Freeze
=====================
Locks and validates core runtime governance invariants for Release Candidates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class GovernanceInvariant:
    name: str
    expected_value: Any
    description: str

@dataclass
class GovernanceFreezePolicy:
    required_invariants: List[GovernanceInvariant] = field(default_factory=lambda: [
        GovernanceInvariant("no_automatic_promotion", False, "Automatic promotion is prohibited"),
        GovernanceInvariant("no_production_mutation", False, "Production mutation is blocked"),
        GovernanceInvariant("court_review_required", True, "Promotion requires court approval"),
        GovernanceInvariant("ranger_evidence_required", True, "Promotion requires ranger evidence"),
        GovernanceInvariant("rollback_reference_required", True, "Sandbox commands require rollback references"),
        GovernanceInvariant("active_phase_tables_protected", True, "Active phase tables cannot be overwritten"),
        GovernanceInvariant("active_cadence_profiles_protected", True, "Active cadence profiles cannot be overwritten"),
        GovernanceInvariant("active_carrier_registry_protected", True, "Active carrier registry cannot be overwritten"),
        GovernanceInvariant("ledger_required", True, "Sovereign Runtime ledger required"),
        GovernanceInvariant("quarantine_flags_enforced", True, "Quarantine flags cannot be ignored")
    ])

@dataclass
class GovernanceFreezeSnapshot:
    snapshot_id: str
    invariant_values: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class GovernanceFreezeViolation:
    invariant_name: str
    expected: Any
    actual: Any
    description: str

@dataclass
class GovernanceFreezeReport:
    report_id: str
    snapshot: GovernanceFreezeSnapshot
    violations: List[GovernanceFreezeViolation] = field(default_factory=list)
    frozen: bool = True
    timestamp: float = field(default_factory=time.time)


def build_governance_freeze(policy: GovernanceFreezePolicy) -> GovernanceFreezeReport:
    """
    Builds a baseline freeze report from policy definitions.
    """
    snapshot_id = f"FRZ_{uuid.uuid4().hex[:8]}"
    invariant_values = {inv.name: inv.expected_value for inv in policy.required_invariants}
    snapshot = GovernanceFreezeSnapshot(snapshot_id=snapshot_id, invariant_values=invariant_values)
    return GovernanceFreezeReport(report_id=f"GVR_{uuid.uuid4().hex[:8]}", snapshot=snapshot, frozen=True)


def capture_governance_freeze_snapshot(runtime: Any, registries: Any) -> GovernanceFreezeSnapshot:
    """
    Captures current runtime and registry configuration states.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    snapshot_id = f"SNAP_{uuid.uuid4().hex[:8]}"
    
    # Extract states from runtime and registries
    allow_auto_promote = extract(runtime, "allow_automatic_promotion", False)
    allow_prod = extract(runtime, "allow_production_execution", False) or extract(runtime, "production_execution_attempted", False)
    court_req = not extract(runtime, "bypass_court", False)
    ranger_req = not extract(runtime, "bypass_ranger", False)
    rollback_req = not extract(runtime, "bypass_rollback", False)
    
    phase_prot = not extract(registries, "active_phase_tables_overwritten", False)
    cadence_prot = not extract(registries, "active_cadence_profiles_overwritten", False)
    carrier_prot = not extract(registries, "active_carrier_registry_overwritten", False)
    
    ledger_req = not extract(runtime, "bypass_ledger", False)
    quarantine_enforced = not extract(runtime, "ignore_quarantine", False)

    invariant_values = {
        "no_automatic_promotion": allow_auto_promote,
        "no_production_mutation": allow_prod,
        "court_review_required": court_req,
        "ranger_evidence_required": ranger_req,
        "rollback_reference_required": rollback_req,
        "active_phase_tables_protected": phase_prot,
        "active_cadence_profiles_protected": cadence_prot,
        "active_carrier_registry_protected": carrier_prot,
        "ledger_required": ledger_req,
        "quarantine_flags_enforced": quarantine_enforced
    }
    
    return GovernanceFreezeSnapshot(snapshot_id=snapshot_id, invariant_values=invariant_values)


def validate_governance_invariants(snapshot: GovernanceFreezeSnapshot, policy: GovernanceFreezePolicy) -> GovernanceFreezeReport:
    """
    Validates snapshot settings against policies and returns a report with violations.
    """
    violations = []
    for inv in policy.required_invariants:
        actual = snapshot.invariant_values.get(inv.name)
        if actual != inv.expected_value:
            violations.append(GovernanceFreezeViolation(
                invariant_name=inv.name,
                expected=inv.expected_value,
                actual=actual,
                description=inv.description
            ))
            
    frozen = len(violations) == 0
    return GovernanceFreezeReport(
        report_id=f"GVR_VAL_{uuid.uuid4().hex[:8]}",
        snapshot=snapshot,
        violations=violations,
        frozen=frozen
    )


def detect_governance_freeze_violation(before: GovernanceFreezeSnapshot, after: GovernanceFreezeSnapshot) -> List[GovernanceFreezeViolation]:
    """
    Detects changes/violations between two captured snapshots.
    """
    violations = []
    for k, v in before.invariant_values.items():
        actual = after.invariant_values.get(k)
        if actual != v:
            violations.append(GovernanceFreezeViolation(
                invariant_name=k,
                expected=v,
                actual=actual,
                description=f"Configuration drift detected: {k} changed from {v} to {actual}."
            ))
    return violations


def summarize_governance_freeze(report: GovernanceFreezeReport) -> Dict[str, Any]:
    """
    Returns summary stats for the governance freeze.
    """
    return {
        "report_id": report.report_id,
        "frozen": report.frozen,
        "violations_count": len(report.violations),
        "violations": [v.invariant_name for v in report.violations]
    }


def export_governance_freeze_for_finalization(report: GovernanceFreezeReport) -> Dict[str, Any]:
    """
    Exports governance freeze parameters for system finalization.
    """
    return {
        "report_id": report.report_id,
        "frozen": report.frozen,
        "violations_count": len(report.violations)
    }


def validate_governance_freeze_for_final_gateway(report: GovernanceFreezeReport) -> bool:
    """
    Validates that there are no governance freeze violations.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    return extract(report, "frozen", True) and len(extract(report, "violations", []) or []) == 0

