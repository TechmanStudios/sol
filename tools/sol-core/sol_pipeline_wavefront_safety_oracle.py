# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Pipeline Wavefront Safety Oracle
====================================
Evaluates safety limits of balancing and calibration fault injection cases.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class PipelineWavefrontSafetyOracleInput:
    fault_case: Any
    target_state: Any
    policy: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineWavefrontSafetyOracleDecision:
    outcome: str  # accept_shadow, hold_pipeline_balance, hold_wavefront_calibration, reject_candidate, rollback_pipeline_balance, rollback_wavefront_calibration, quarantine_pipeline_segment, quarantine_wavefront_packet, quarantine_core
    justification: str
    confidence: float

@dataclass
class PipelineWavefrontSafetyOracleReport:
    report_id: str
    input: PipelineWavefrontSafetyOracleInput
    decision: PipelineWavefrontSafetyOracleDecision
    timestamp: float = field(default_factory=time.time)


def evaluate_pipeline_wavefront_safety(
    oracle_input: PipelineWavefrontSafetyOracleInput
) -> PipelineWavefrontSafetyOracleReport:
    """
    Evaluates safety parameters and returns the decision report.
    """
    case = oracle_input.fault_case
    expected = classify_pipeline_wavefront_expected_outcome(case)
    
    dec = PipelineWavefrontSafetyOracleDecision(
        outcome=expected,
        justification=f"Oracle evaluated safety for category: {getattr(case, 'category', 'generic')}",
        confidence=0.99
    )
    
    return PipelineWavefrontSafetyOracleReport(
        report_id=f"RPT_WF_SFT_ORC_{uuid.uuid4().hex[:8]}",
        input=oracle_input,
        decision=dec
    )


def classify_pipeline_wavefront_expected_outcome(fault_case: Any) -> str:
    """
    Classifies a fault case into the expected safety outcome.
    """
    cat = getattr(fault_case, "category", "") if fault_case else ""
    
    # Map category to expected outcome
    if cat == "missing pipeline metrics":
        return "reject_candidate"
    elif cat == "invalid balance plan":
        return "reject_candidate"
    elif cat == "false balance improvement":
        return "reject_candidate"
    elif cat == "increased route depth without justification":
        return "hold_pipeline_balance"
    elif cat == "increased core queue depth":
        return "hold_pipeline_balance"
    elif cat == "increased stage latency":
        return "hold_pipeline_balance"
    elif cat == "cross-core stall spike":
        return "hold_pipeline_balance"
    elif cat == "backpressure spike":
        return "hold_pipeline_balance"
    elif cat == "reduction wait spike":
        return "hold_pipeline_balance"
    elif cat == "consensus wait spike":
        return "hold_pipeline_balance"
    elif cat == "lock wait spike":
        return "hold_pipeline_balance"
    elif cat == "cadence skew spike":
        return "hold_pipeline_balance"
    elif cat == "wavefront timing drift":
        return "hold_wavefront_calibration"
    elif cat == "missing quantum wavefront baseline":
        return "reject_candidate"
    elif cat == "amplitude coherence collapse":
        return "rollback_wavefront_calibration"
    elif cat == "phase coherence collapse":
        return "rollback_wavefront_calibration"
    elif cat == "resonance coherence collapse":
        return "rollback_wavefront_calibration"
    elif cat == "packet dispersion breach":
        return "quarantine_wavefront_packet"
    elif cat == "unbounded uncertainty window":
        return "reject_candidate"
    elif cat == "missing PML boundary":
        return "quarantine_pipeline_segment"
    elif cat == "weakened PML absorption":
        return "quarantine_pipeline_segment"
    elif cat == "carrier binding break":
        return "reject_candidate"
    elif cat == "quadrature pairing break":
        return "reject_candidate"
    elif cat == "prefix-carry bridge break":
        return "reject_candidate"
    elif cat == "arithmetic oracle mismatch":
        return "reject_candidate"
    elif cat == "tensor oracle mismatch":
        return "reject_candidate"
    elif cat == "runtime ledger missing event":
        return "reject_candidate"
    elif cat == "rollback reference missing":
        return "reject_candidate"
    elif cat == "state checksum mismatch":
        return "reject_candidate"
    elif cat == "active phase-table overwrite attempt":
        return "quarantine_core"
    elif cat == "active cadence-profile overwrite attempt":
        return "quarantine_core"
    elif cat == "active carrier-registry overwrite attempt":
        return "quarantine_core"
    elif cat == "production/default mutation attempt":
        return "reject_candidate"

    return "accept_shadow"


def compare_pipeline_wavefront_actual_to_expected(expected: str, actual: str) -> bool:
    """
    Verifies that actual outcome matches expected safe failure behavior.
    """
    return expected == actual
