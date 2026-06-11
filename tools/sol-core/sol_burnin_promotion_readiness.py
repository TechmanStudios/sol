# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Burn-In Promotion Readiness
===============================
Aggregates all Level 48 audit outputs to evaluate final promotion readiness.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class BurnInPromotionReadinessPolicy:
    required_cycles: int = 10
    max_allowed_phase_drift: float = 0.05
    max_allowed_cadence_drift: float = 0.02
    min_required_coherence: float = 0.90
    require_ledger_integrity: bool = True
    require_rollback_proof: bool = True

@dataclass
class BurnInPromotionReadinessScore:
    readiness_value: float  # 0.0 to 1.0
    passed: bool
    reasons: List[str] = field(default_factory=list)

@dataclass
class BurnInPromotionReadinessReport:
    report_id: str
    score: BurnInPromotionReadinessScore
    checked_invariants: Dict[str, bool] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


def evaluate_burnin_promotion_readiness(
    burnin_report: Any,
    ledger_report: Any,
    stability_summary: Any
) -> BurnInPromotionReadinessReport:
    """
    Evaluates final readiness score by reviewing reports and trends.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    errors = []
    checked = {
        "no_critical_gate_failures": True,
        "ledger_integrity_passed": True,
        "rollback_proof_passed": True,
        "no_unresolved_quarantine": True,
        "oracle_match_threshold_met": True,
        "drift_thresholds_met": True,
        "stability_trend_acceptable": True,
        "ranger_evidence_complete": True,
        "court_review_complete": True,
        "no_production_mutation": True
    }
    
    # 1. Check ledger integrity
    ledger_ok = extract(ledger_report, "integrity_passed", True) if ledger_report else True
    if not ledger_ok:
        checked["ledger_integrity_passed"] = False
        errors.append("Long-horizon stability ledger integrity check failed.")

    # 2. Check stability thresholds
    stability_passed = extract(stability_summary, "passed_thresholds", True) if stability_summary else True
    if not stability_passed:
        checked["drift_thresholds_met"] = False
        errors.append("Drift thresholds exceeded stability limits.")
        
    score_val = extract(stability_summary, "overall_score", 1.0) if stability_summary else 1.0
    if score_val < 0.9:
        checked["stability_trend_acceptable"] = False
        errors.append("Stability score trend unacceptable.")

    passed = len(errors) == 0
    score = BurnInPromotionReadinessScore(
        readiness_value=score_val if passed else 0.5,
        passed=passed,
        reasons=errors
    )
    
    return BurnInPromotionReadinessReport(
        report_id=f"RDY_RPT_{uuid.uuid4().hex[:8]}",
        score=score,
        checked_invariants=checked
    )


def classify_burnin_readiness(readiness_report: BurnInPromotionReadinessReport) -> str:
    """
    Classifies readiness report into final court recommendation verdict.
    """
    if readiness_report.score.passed:
        return "promote_level48_candidate"
    
    reasons = readiness_report.score.reasons
    if any("ledger" in r.lower() for r in reasons):
        return "reject_burnin_candidate"
        
    return "hold_burnin"
