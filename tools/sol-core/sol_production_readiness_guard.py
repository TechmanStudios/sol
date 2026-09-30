# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Production Readiness Guard
==============================
Readiness checks protecting the system against production activation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import time

@dataclass
class ProductionReadinessGuardPolicy:
    block_production: bool = True

@dataclass
class ProductionReadinessSignal:
    name: str
    value: Any
    passed: bool

@dataclass
class ProductionReadinessDecision:
    decision: str  # not_ready, needs_more_evidence, shadow_finalized, sandbox_gateway_ready, production_blocked
    justification: str

@dataclass
class ProductionReadinessReport:
    report_id: str
    decision: ProductionReadinessDecision
    signals: List[ProductionReadinessSignal] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def collect_production_readiness_signals(final_manifest: Any) -> List[ProductionReadinessSignal]:
    """
    Collects signals from the final system manifest.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    signals = []
    
    # 1. Unresolved quarantine
    quarantine = extract(final_manifest, "quarantine_status", "none")
    signals.append(ProductionReadinessSignal(
        name="unresolved_quarantine",
        value=quarantine,
        passed=(quarantine == "none")
    ))
    
    # 2. Missing court verdict
    court_verdicts = extract(final_manifest, "court_verdicts", []) or []
    has_court = len(court_verdicts) > 0 or extract(final_manifest, "court_verdict") is not None
    signals.append(ProductionReadinessSignal(
        name="court_verdict_present",
        value=has_court,
        passed=has_court
    ))
    
    # Extract evidence payload
    evidence_items = extract(final_manifest, "evidence", []) or []
    evidence_types = {extract(item, "evidence_type") for item in evidence_items}
    evidence_map = {extract(item, "evidence_type"): extract(item, "payload", {}) for item in evidence_items}
    
    # 3. Missing ranger packet
    has_ranger = "ranger_packet" in evidence_types or extract(final_manifest, "ranger_packet") is not None
    signals.append(ProductionReadinessSignal(
        name="ranger_packet_present",
        value=has_ranger,
        passed=has_ranger
    ))
    
    # 4. Missing rollback proof
    has_rollback = "rollback_proof" in evidence_types or extract(final_manifest, "rollback_proof") is not None
    rollback_success = False
    if has_rollback:
        rollback_success = True
        payload = evidence_map.get("rollback_proof", {}) or {}
        if payload and not payload.get("success", True):
            rollback_success = False
            
    signals.append(ProductionReadinessSignal(
        name="rollback_proof_valid",
        value=rollback_success,
        passed=rollback_success
    ))
    
    # 5. Missing ledger entry
    has_ledger = "runtime_ledger" in evidence_types or "stability_ledger" in evidence_types or extract(final_manifest, "stability_ledger") is not None
    signals.append(ProductionReadinessSignal(
        name="ledger_entry_present",
        value=has_ledger,
        passed=has_ledger
    ))
    
    # 6. Failed burn-in
    burnin_passed = False
    if "burnin_report" in evidence_types or extract(final_manifest, "burnin_report") is not None:
        payload = evidence_map.get("burnin_report", {}) or {}
        burnin_passed = payload.get("passed_audit", True) and payload.get("success", True)
    signals.append(ProductionReadinessSignal(
        name="burnin_passed",
        value=burnin_passed,
        passed=burnin_passed
    ))
    
    # 7. API breakage
    api_compatible = True
    if "api_contract" in evidence_types or extract(final_manifest, "api_stability_contract") is not None:
        payload = evidence_map.get("api_contract", {}) or {}
        api_compatible = payload.get("compatible", True) and not payload.get("broken", False)
    signals.append(ProductionReadinessSignal(
        name="api_compatible",
        value=api_compatible,
        passed=api_compatible
    ))
    
    # 8. Governance freeze violation
    gov_frozen = True
    if "governance_freeze" in evidence_types or extract(final_manifest, "governance_freeze_report") is not None:
        payload = evidence_map.get("governance_freeze", {}) or {}
        gov_frozen = payload.get("frozen", True)
    signals.append(ProductionReadinessSignal(
        name="governance_frozen",
        value=gov_frozen,
        passed=gov_frozen
    ))
    
    # 9. Active table overwrite attempt & 10. Production mutation request
    # Extracted from final gateway policy or request if present
    overwrite_attempt = False
    prod_req = False
    
    policy_obj = extract(final_manifest, "final_gateway_policy")
    if policy_obj:
        if extract(policy_obj, "allow_production_mutation", False):
            prod_req = True
        if extract(policy_obj, "overwrite_active", False):
            overwrite_attempt = True
            
    signals.append(ProductionReadinessSignal(
        name="no_overwrite_attempt",
        value=not overwrite_attempt,
        passed=not overwrite_attempt
    ))
    
    signals.append(ProductionReadinessSignal(
        name="no_production_mutation_request",
        value=not prod_req,
        passed=not prod_req
    ))
    
    return signals


def evaluate_production_readiness_guard(
    signals: List[ProductionReadinessSignal],
    policy: ProductionReadinessGuardPolicy
) -> ProductionReadinessReport:
    """
    Evaluates signals against the policy. Always blocks production execution.
    """
    signal_map = {s.name: s for s in signals}
    
    # Identify failures
    failures = [s.name for s in signals if not s.passed]
    
    # Production is explicitly blocked by policy
    if policy.block_production or "no_production_mutation_request" in failures:
        dec_val = "production_blocked"
        justification = f"Production launch is strictly blocked. Failures detected: {failures}."
    elif len(failures) > 0:
        if "unresolved_quarantine" in failures:
            dec_val = "needs_more_evidence"
            justification = "System quarantined. Needs more evidence."
        elif "court_verdict_present" in failures or "ranger_packet_present" in failures:
            dec_val = "needs_more_evidence"
            justification = "Missing court review or ranger packets."
        else:
            dec_val = "not_ready"
            justification = f"Gate validation failures: {failures}."
    else:
        # Check if sandbox token is simulated/checked
        dec_val = "shadow_finalized"
        justification = "All shadow validations passed successfully."
        
    decision = ProductionReadinessDecision(decision=dec_val, justification=justification)
    
    return ProductionReadinessReport(
        report_id=f"RDY_GRD_{uuid.uuid4().hex[:8]}",
        decision=decision,
        signals=signals
    )


def classify_production_readiness(report: ProductionReadinessReport) -> str:
    """
    Returns final readiness classification.
    """
    return report.decision.decision
