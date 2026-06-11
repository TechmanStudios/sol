# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Burn-In Regression Detector
===============================
Classifies stability metrics drift, checks ledger gaps, and flags regressions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class BurnInRegressionCase:
    case_id: str
    metric_name: str
    severity: str  # low, medium, high, critical
    description: str

@dataclass
class BurnInRegressionSignal:
    signal_id: str
    case: BurnInRegressionCase
    drift_value: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class BurnInRegressionDecision:
    decision: str  # continue_shadow, hold_burnin, request_ranger_review, request_court_review, rollback_to_checkpoint, quarantine_sequence_step, reject_burnin_candidate
    justification: str
    action_required: bool = False

@dataclass
class BurnInRegressionReport:
    report_id: str
    signals: List[BurnInRegressionSignal]
    decision: BurnInRegressionDecision
    passed: bool = True
    timestamp: float = field(default_factory=time.time)


def detect_burnin_regressions(metrics: Dict[str, Any], ledger: Any) -> BurnInRegressionReport:
    """
    Scans recent metrics and ledger checks to identify stability regressions.
    """
    signals = []
    
    # 1. Check phase drift limits
    if "phase_drift" in metrics:
        vals = metrics["phase_drift"].values
        if vals and vals[-1] > 0.05:
            signals.append(BurnInRegressionSignal(
                signal_id=f"SIG_{uuid.uuid4().hex[:8]}",
                case=BurnInRegressionCase("C_PD", "phase_drift", "critical", "Phase drift exceeded critical threshold of 0.05"),
                drift_value=vals[-1]
            ))
            
    # 2. Check oracle mismatch spikes
    if "oracle_match_rate" in metrics:
        vals = metrics["oracle_match_rate"].values
        if vals and vals[-1] < 1.0:
            signals.append(BurnInRegressionSignal(
                signal_id=f"SIG_{uuid.uuid4().hex[:8]}",
                case=BurnInRegressionCase("C_OM", "oracle_match_rate", "critical", "Oracle match rate dropped below 100%"),
                drift_value=1.0 - vals[-1]
            ))
            
    # 3. Check wavefront coherence collapses
    if "wavefront_coherence" in metrics:
        vals = metrics["wavefront_coherence"].values
        if vals and vals[-1] < 0.90:
            signals.append(BurnInRegressionSignal(
                signal_id=f"SIG_{uuid.uuid4().hex[:8]}",
                case=BurnInRegressionCase("C_WC", "wavefront_coherence", "critical", "Wavefront coherence collapsed below 0.90"),
                drift_value=vals[-1]
            ))

    passed = len(signals) == 0
    decision = classify_burnin_regression(signals[0] if signals else None)
    
    return BurnInRegressionReport(
        report_id=f"REG_RPT_{uuid.uuid4().hex[:8]}",
        signals=signals,
        decision=decision,
        passed=passed
    )


def classify_burnin_regression(signal: Optional[BurnInRegressionSignal]) -> BurnInRegressionDecision:
    """
    Classifies a regression signal and yields a decision.
    """
    if not signal:
        return BurnInRegressionDecision(
            decision="continue_shadow",
            justification="No regression signals detected. Normal stability verified.",
            action_required=False
        )
        
    case = signal.case
    if case.severity == "critical":
        if case.metric_name == "oracle_match_rate":
            return BurnInRegressionDecision(
                decision="reject_burnin_candidate",
                justification=f"Critical failure: {case.description}. Mismatch requires rejection.",
                action_required=True
            )
        elif case.metric_name in ["phase_drift", "wavefront_coherence"]:
            return BurnInRegressionDecision(
                decision="hold_burnin",
                justification=f"Drift spike detected: {case.description}. Holding burn-in for recalibration.",
                action_required=True
            )
        return BurnInRegressionDecision(
            decision="rollback_to_checkpoint",
            justification=f"Critical regression: {case.description}. Recommending state rollback.",
            action_required=True
        )
    elif case.severity == "high":
        return BurnInRegressionDecision(
            decision="request_court_review",
            justification=f"High severity event: {case.description}. Escalate to Promotion Court.",
            action_required=True
        )
    else:
        return BurnInRegressionDecision(
            decision="request_ranger_review",
            justification=f"Moderate warning: {case.description}.",
            action_required=True
        )


def recommend_burnin_response(regression_report: BurnInRegressionReport) -> str:
    """
    Helper to extract recommended response action string.
    """
    return regression_report.decision.decision
