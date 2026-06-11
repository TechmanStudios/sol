# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Runtime Governor
====================
Enforces the 16 sovereign runtime security gates and issues governance decisions for sequence progression.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class RuntimeGovernancePolicy:
    require_ranger_signature: bool = True
    require_court_signature: bool = True
    strict_sandbox_validation: bool = True

@dataclass
class RuntimeGateSnapshot:
    snapshot_id: str
    gates_status: Dict[str, bool] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class RuntimeGovernanceDecision:
    decision_id: str
    decision: str  # continue_shadow, hold_for_evidence, request_ranger_review, request_court_review, authorize_sandbox_step, rollback_step, quarantine_step, reject_sequence
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class RuntimeGovernanceReport:
    report_id: str
    gate_snapshot: RuntimeGateSnapshot
    decision: RuntimeGovernanceDecision
    policy_satisfied: bool


def evaluate_runtime_gates(runtime: Any, sequence: Any) -> RuntimeGateSnapshot:
    """
    Evaluates the 16 required runtime security gates.
    """
    gates = {
        "runtime_policy_valid": True,
        "runtime_mode_allowed": True,
        "levelup_sequence_valid": True,
        "dependencies_satisfied": True,
        "no_cycle_in_levelup_sequence": True,
        "token_valid_if_sandbox": True,
        "court_authorization_present_if_sandbox": True,
        "ranger_observer_present": True,
        "rollback_reference_present": True,
        "runtime_ledger_complete": True,
        "gate_snapshots_complete": True,
        "evidence_complete": True,
        "unresolved_quarantine_absent": True,
        "critical_tests_passed_or_noncritical": True,
        "no_automatic_promotion": True,
        "no_production_runtime_execution": True
    }
    
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # 1. runtime_policy_valid
    policy = extract(runtime, "policy")
    if not policy or extract(policy, "allow_production_execution", False):
        gates["runtime_policy_valid"] = False
        
    # 2. runtime_mode_allowed
    mode = extract(runtime, "mode")
    if mode not in ["shadow", "sandbox", "hold", "quarantine"]:
        gates["runtime_mode_allowed"] = False
        
    # 3. levelup_sequence_valid
    if not sequence:
        gates["levelup_sequence_valid"] = False
    else:
        steps = extract(sequence, "steps", [])
        if not steps:
            gates["levelup_sequence_valid"] = False
            
    # 4. dependencies_satisfied & 5. no_cycle_in_levelup_sequence
    if sequence:
        from sol_levelup_sequence import validate_levelup_sequence
        try:
            validate_levelup_sequence(sequence)
        except Exception:
            gates["dependencies_satisfied"] = False
            gates["no_cycle_in_levelup_sequence"] = False
            
    # Sandbox-specific gates (6, 7, 8, 9)
    if mode == "sandbox":
        token = extract(runtime, "active_token")
        if not token:
            gates["token_valid_if_sandbox"] = False
            gates["court_authorization_present_if_sandbox"] = False
        else:
            # Check validation
            is_valid = extract(token, "active", False) and extract(token, "expires_at", 0.0) > time.time()
            if not is_valid:
                gates["token_valid_if_sandbox"] = False
            if not extract(token, "court_authorization_id"):
                gates["court_authorization_present_if_sandbox"] = False
            if not extract(token, "ranger_observer_id"):
                gates["ranger_observer_present"] = False
            if not extract(token, "rollback_required", False) and not extract(token, "rollback_reference"):
                gates["rollback_reference_present"] = False
                
        # Additional checks for observers/references on runtime structure
        if not extract(runtime, "ranger_observer_id") and not (token and extract(token, "ranger_observer_id")):
            gates["ranger_observer_present"] = False
        if not extract(runtime, "rollback_reference") and not (token and extract(token, "rollback_reference")):
            gates["rollback_reference_present"] = False
            
    # 10. runtime_ledger_complete & 11. gate_snapshots_complete
    ledger = extract(runtime, "ledger")
    if not ledger:
        gates["runtime_ledger_complete"] = False
        gates["gate_snapshots_complete"] = False
    else:
        entries = extract(ledger, "entries", [])
        if not entries:
            gates["runtime_ledger_complete"] = False
            gates["gate_snapshots_complete"] = False
            
    # 12. evidence_complete
    evidence = extract(runtime, "evidence", {}) or {}
    if not evidence and not (ledger and extract(ledger, "evidence_references")):
        gates["evidence_complete"] = False
        
    # 13. unresolved_quarantine_absent
    if extract(runtime, "quarantine_flags") or mode == "quarantine":
        gates["unresolved_quarantine_absent"] = False
        
    # 14. critical_tests_passed_or_noncritical
    test_summary = extract(runtime, "test_summary") or extract(evidence, "test_summary")
    if test_summary:
        status = extract(test_summary, "status", "failed")
        if status not in ["passed", "all_passed"]:
            gates["critical_tests_passed_or_noncritical"] = False
    else:
        # If missing test summary, block if policy strictly requires it
        gates["critical_tests_passed_or_noncritical"] = False
        
    # 15. no_automatic_promotion
    if extract(runtime, "auto_promote", False):
        gates["no_automatic_promotion"] = False
        
    # 16. no_production_runtime_execution
    if mode == "production" or extract(policy, "allow_production_execution", False):
        gates["no_production_runtime_execution"] = False

    import uuid
    snap_id = f"SNAP_{uuid.uuid4().hex[:8]}"
    return RuntimeGateSnapshot(
        snapshot_id=snap_id,
        gates_status=gates
    )


def validate_runtime_evidence(runtime: Any, sequence: Any) -> bool:
    """
    Checks that all required telemetry and docket evidence is present.
    """
    snap = evaluate_runtime_gates(runtime, sequence)
    return all(snap.gates_status.values())


def decide_runtime_continuation(report: RuntimeGovernanceReport) -> RuntimeGovernanceDecision:
    """
    Translates gate check statuses into progression decisions.
    """
    return report.decision


def block_uncontrolled_execution(reason: str) -> None:
    """
    Clamps the runtime environment and raises an execution veto.
    """
    raise PermissionError(f"Autonomous production execution vetoed by Sovereign Governor: {reason}")
