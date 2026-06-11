# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Release Readiness Score
===========================
Evaluates release readiness metrics and outputs promotion readiness classifications.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import time

@dataclass
class ReleaseReadinessPolicy:
    required_test_pass_rate: float = 1.0
    require_ledger_integrity: bool = True
    require_rollback_proof: bool = True
    max_quarantine_count: int = 0
    require_api_freeze: bool = True
    require_governance_freeze: bool = True
    require_active_table_protection: bool = True

@dataclass
class ReleaseReadinessMetric:
    name: str
    value: Any
    passed: bool

@dataclass
class ReleaseReadinessScore:
    readiness_value: float  # 0.0 to 1.0
    metrics: Dict[str, ReleaseReadinessMetric] = field(default_factory=dict)
    passed: bool = True

@dataclass
class ReleaseReadinessReport:
    report_id: str
    score: ReleaseReadinessScore
    classification: str  # not_ready, needs_more_evidence, shadow_rc_ready, sandbox_rc_ready, reject_release_candidate
    timestamp: float = field(default_factory=time.time)


def collect_release_readiness_metrics(manifest: Any) -> Dict[str, ReleaseReadinessMetric]:
    """
    Extracts metrics from the manifest.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    metrics = {}
    
    # 1. Test Pass Status
    test_sum = extract(manifest, "test_summary")
    test_passed = False
    test_val = 0.0
    if test_sum:
        total = extract(test_sum, "total_tests", 0)
        passed = extract(test_sum, "passed_tests", 0)
        failed = extract(test_sum, "failed_tests", 0)
        test_val = passed / total if total > 0 else 0.0
        test_passed = (failed == 0 and total > 0)
    metrics["test_pass_status"] = ReleaseReadinessMetric("test_pass_status", test_val, test_passed)

    # Extract items from evidence list
    evidence_items = extract(manifest, "evidence", []) or []
    
    burnin_stable = False
    ledger_integrity = False
    rollback_proof = False
    api_freeze = False
    gov_freeze = False
    active_table_protected = True
    known_limitations_count = len(extract(manifest, "known_non_production_limitations", []) or [])
    unresolved_quarantine = (extract(manifest, "quarantine_status", "none") == "quarantined")
    ranger_evidence_complete = False
    court_review_complete = False

    for item in evidence_items:
        item_type = extract(item, "evidence_type")
        payload = extract(item, "payload", {}) or {}
        
        if item_type == "burnin_report":
            burnin_stable = payload.get("passed_audit", False)
        elif item_type == "stability_ledger":
            ledger_integrity = payload.get("integrity_passed", False)
        elif item_type == "rollback_proof":
            rollback_proof = payload.get("success", False)
        elif item_type == "api_contract":
            api_freeze = payload.get("compatible", False)
        elif item_type == "governance_freeze":
            gov_freeze = payload.get("frozen", False)
        elif item_type == "active_table_protection":
            active_table_protected = payload.get("protected", True)
        elif item_type == "ranger_packet":
            ranger_evidence_complete = payload.get("complete", False)
        elif item_type == "court_verdict":
            court_review_complete = payload.get("complete", False)

    # Defaults or overridden by evidence contents
    metrics["burnin_stability"] = ReleaseReadinessMetric("burnin_stability", burnin_stable, burnin_stable)
    metrics["ledger_integrity"] = ReleaseReadinessMetric("ledger_integrity", ledger_integrity, ledger_integrity)
    metrics["rollback_proof_status"] = ReleaseReadinessMetric("rollback_proof_status", rollback_proof, rollback_proof)
    metrics["unresolved_quarantine_count"] = ReleaseReadinessMetric("unresolved_quarantine_count", 1 if unresolved_quarantine else 0, not unresolved_quarantine)
    metrics["ranger_evidence_completeness"] = ReleaseReadinessMetric("ranger_evidence_completeness", ranger_evidence_complete, ranger_evidence_complete)
    metrics["court_review_completeness"] = ReleaseReadinessMetric("court_review_completeness", court_review_complete, court_review_complete)
    metrics["api_freeze_status"] = ReleaseReadinessMetric("api_freeze_status", api_freeze, api_freeze)
    metrics["governance_freeze_status"] = ReleaseReadinessMetric("governance_freeze_status", gov_freeze, gov_freeze)
    metrics["active_table_protection_status"] = ReleaseReadinessMetric("active_table_protection_status", active_table_protected, active_table_protected)
    metrics["known_limitation_count"] = ReleaseReadinessMetric("known_limitation_count", known_limitations_count, True)

    return metrics


def evaluate_release_readiness(manifest: Any, policy: ReleaseReadinessPolicy) -> ReleaseReadinessReport:
    """
    Evaluates final release readiness scores and constructs the report.
    """
    metrics = collect_release_readiness_metrics(manifest)
    
    total_metrics = len(metrics)
    passed_count = sum(1 for m in metrics.values() if m.passed)
    
    score_val = passed_count / total_metrics if total_metrics > 0 else 0.0
    
    # Critical gates validation
    passed = True
    if not metrics["test_pass_status"].passed:
        passed = False
    if not metrics["burnin_stability"].passed:
        passed = False
    if policy.require_ledger_integrity and not metrics["ledger_integrity"].passed:
        passed = False
    if policy.require_rollback_proof and not metrics["rollback_proof_status"].passed:
        passed = False
    if not metrics["unresolved_quarantine_count"].passed:
        passed = False
    if policy.require_api_freeze and not metrics["api_freeze_status"].passed:
        passed = False
    if policy.require_governance_freeze and not metrics["governance_freeze_status"].passed:
        passed = False
    if policy.require_active_table_protection and not metrics["active_table_protection_status"].passed:
        passed = False

    score = ReleaseReadinessScore(
        readiness_value=score_val if passed else min(score_val, 0.4),
        metrics=metrics,
        passed=passed
    )
    
    classification = classify_release_readiness(ReleaseReadinessReport("", score, ""))
    
    return ReleaseReadinessReport(
        report_id=f"RDY_{uuid.uuid4().hex[:8]}",
        score=score,
        classification=classification
    )


def classify_release_readiness(report: ReleaseReadinessReport) -> str:
    """
    Returns final readiness classification.
    """
    score = report.score
    if not score.passed:
        # Check if failed due to unresolved quarantine
        quarantine_metric = score.metrics.get("unresolved_quarantine_count")
        if quarantine_metric and not quarantine_metric.passed:
            return "needs_more_evidence"
            
        # Check if failed due to failed burn-in
        burnin_metric = score.metrics.get("burnin_stability")
        if burnin_metric and not burnin_metric.passed:
            return "reject_release_candidate"
            
        # Check if failed due to governance violations
        gov_metric = score.metrics.get("governance_freeze_status")
        if gov_metric and not gov_metric.passed:
            return "reject_release_candidate"
            
        return "not_ready"
        
    # Check if sandbox token is present or mock signature matches sandbox state
    court_metric = score.metrics.get("court_review_completeness")
    if court_metric and court_metric.passed:
        return "sandbox_rc_ready"
        
    return "shadow_rc_ready"
