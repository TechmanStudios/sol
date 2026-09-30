# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Pipeline Balance Safety Oracle
==================================
Evaluates pipeline balancing candidates to prevent unsafe runtime configurations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class PipelineBalanceOracleInput:
    candidate_plan: Any
    load_metrics: List[Any]
    coherence_metrics: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineBalanceOracleDecision:
    decision: str  # e.g., "accept", "hold_balance", "reject_balance_candidate", "rollback_balance", "quarantine_pipeline_segment", "quarantine_wavefront_packet", "quarantine_core"
    justification: str
    safety_score: float

@dataclass
class PipelineBalanceOracleReport:
    report_id: str
    input_data: PipelineBalanceOracleInput
    decision: PipelineBalanceOracleDecision
    timestamp: float = field(default_factory=time.time)


def evaluate_pipeline_balance_safety(
    oracle_input: PipelineBalanceOracleInput
) -> PipelineBalanceOracleDecision:
    """
    Evaluates balancing safety parameters and yields an advisory decision.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # 1. Check for explicit quarantine or invalid indicators in input data
    meta = oracle_input.metadata or {}
    if meta.get("force_reject"):
        return PipelineBalanceOracleDecision(
            decision="reject_balance_candidate",
            justification="Forced rejection requested by simulation controller.",
            safety_score=0.0
        )

    # 2. Check metrics breaches (e.g. latency, backpressure, stalls, dispersion)
    max_latency = 0.0
    max_backpressure = 0.0
    max_stalls = 0.0
    for m in oracle_input.load_metrics:
        lat = extract(m, "latency", 0.0)
        bp = extract(m, "backpressure", 0.0)
        stalls = extract(m, "stall_time", 0.0)
        
        max_latency = max(max_latency, lat)
        max_backpressure = max(max_backpressure, bp)
        max_stalls = max(max_stalls, stalls)

    # Coherence metrics checks
    amplitude_coh = oracle_input.coherence_metrics.get("amplitude_coherence", 1.0)
    phase_coh = oracle_input.coherence_metrics.get("phase_coherence", 1.0)
    packet_disp = oracle_input.coherence_metrics.get("packet_dispersion", 0.0)

    # 3. Deciding severity classifications
    if max_latency > 0.5:
        return PipelineBalanceOracleDecision(
            decision="quarantine_pipeline_segment",
            justification=f"Latency critical breach: {max_latency}s. Quarantining segment.",
            safety_score=0.1
        )
        
    if max_backpressure > 0.5:
        return PipelineBalanceOracleDecision(
            decision="hold_balance",
            justification=f"Backpressure critical breach: {max_backpressure}. Holding balance.",
            safety_score=0.2
        )

    if max_stalls > 0.5:
        return PipelineBalanceOracleDecision(
            decision="quarantine_core",
            justification=f"Cross-core stalls critical breach: {max_stalls}s. Quarantining core.",
            safety_score=0.15
        )

    if amplitude_coh < 0.8 or phase_coh < 0.8:
        return PipelineBalanceOracleDecision(
            decision="rollback_balance",
            justification="Wavefront coherence loss exceeds safety bounds. Rollback required.",
            safety_score=0.3
        )

    if packet_disp > 0.4:
        return PipelineBalanceOracleDecision(
            decision="quarantine_wavefront_packet",
            justification=f"Wavefront dispersion breach: {packet_disp}. Quarantining wave packet.",
            safety_score=0.25
        )

    # Policy boundary or general reject checks
    plan = oracle_input.candidate_plan
    policy = extract(plan, "policy") if plan else None
    max_imbalance = extract(policy, "max_imbalance_threshold", 0.1) if policy else 0.1
    if max_imbalance <= 0.0:
        return PipelineBalanceOracleDecision(
            decision="reject_balance_candidate",
            justification="Unbounded balance plan policy threshold <= 0.",
            safety_score=0.0
        )

    return PipelineBalanceOracleDecision(
        decision="accept",
        justification="All pipeline safety parameters are within acceptable thresholds.",
        safety_score=0.95
    )


def classify_balance_expected_outcome(
    candidate: Any
) -> str:
    """
    Predicts balancing effectiveness based on plan adjustments.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    adj = extract(candidate, "adjustments", {})
    if not adj:
        return "noop"
    
    # Calculate predicted load shifts
    total_shift = 0.0
    for sid, details in adj.items():
        total_shift += abs(extract(details, "shift_factor", 0.0))

    if total_shift > 0.3:
        return "high_impact_balancing"
    elif total_shift > 0.0:
        return "stable_balancing"
    else:
        return "negligible_impact"


def compare_balance_actual_to_expected(
    expected: str,
    actual: str
) -> bool:
    """
    Compares oracle's prediction with actual observed behavior.
    """
    # Simple semantic matching
    if expected == actual:
        return True
    if expected == "stable_balancing" and actual == "high_impact_balancing":
        return True
    if expected == "high_impact_balancing" and actual == "stable_balancing":
        return True
    return False


def compare_fault_expected_to_actual_outcome(fault_case: Any, actual: str) -> bool:
    """
    Compares the expected safety outcome for a fault case with the actual outcome.
    """
    if not fault_case:
        return actual in ["reject_candidate", "reject_level47_candidate"]
    
    expected = getattr(fault_case, "expected_outcome", "reject_candidate")
    return expected == actual or (expected == "reject_candidate" and actual == "reject_level47_candidate")


def validate_pipeline_balance_oracle_regression(matrix_report: Any) -> bool:
    """
    Verifies that all actual safety outcomes in the matrix match the expected safety outcomes.
    Mismatches fail regression checks.
    """
    if not matrix_report or not hasattr(matrix_report, "results"):
        return False
    
    for res in matrix_report.results:
        if not res.outcome_matched:
            return False
            
    return True
