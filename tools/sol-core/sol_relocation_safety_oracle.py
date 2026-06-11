# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Relocation Safety Oracle
============================
Evaluates state relocation inputs and classifies them into safe rejections/quarantines vs approvals.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class RelocationSafetyOracleInput:
    has_fault: bool
    fault_category: str
    success: bool
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelocationSafetyOracleDecision:
    decision_id: str
    outcome: str  # accept_shadow | hold_relocation | abort_relocation | rollback_relocation | quarantine_state_ref | quarantine_manifold | reject_candidate
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class RelocationSafetyOracleReport:
    report_id: str
    decision: RelocationSafetyOracleDecision
    input_snapshot: RelocationSafetyOracleInput
    agreement: bool
    timestamp: float = field(default_factory=time.time)


def classify_expected_outcome(fault_case: str) -> str:
    """
    Classifies a fault category name into an expected safety oracle outcome.
    """
    cat = fault_case.lower().strip()
    
    # Mapping table for relocation and calibration fault categories
    if cat in [
        "state hash mismatch",
        "unstable wavefront coherence",
        "unstable feedback loop",
        "phase drift spike",
        "cadence drift spike",
        "carrier phase error spike",
        "wavefront coherence collapse",
        "runaway feedback gain",
        "feedback loop fails to converge",
        "rollback after feedback fails",
    ]:
        return "rollback_relocation"
        
    elif cat in [
        "missing source state",
        "missing target state",
        "missing rollback snapshot",
        "local quorum failure",
        "global quorum failure",
        "sequencer quorum failure",
        "cadence window failure",
        "lock boundary failure",
        "cross-manifold deadlock",
        "unbounded real-time calibration adjustment",
        "missing calibration baseline",
        "missing candidate phase table",
        "adjustment exceeds policy bounds",
        "carrier lease failure",
        "quadrature pair break",
    ]:
        return "abort_relocation"
        
    elif cat in [
        "crosstalk spike",
        "boundary reflection breach",
        "invalid pml boundary",
        "pml weakening",
        "excessive route damping",
        "feedback rollback failure",
    ]:
        return "quarantine_manifold"
        
    elif cat in [
        "partial relocation risk",
    ]:
        return "hold_relocation"
        
    elif cat in [
        "active phase-table overwrite attempt",
        "active cadence-table overwrite attempt",
        "active carrier-registry overwrite attempt",
        "candidate table accidentally points to active table",
        "oracle mismatch after calibration",
        "corrupted rollback snapshot",
    ]:
        return "reject_candidate"
        
    return "accept_shadow"


def evaluate_relocation_safety(input_data: RelocationSafetyOracleInput) -> RelocationSafetyOracleDecision:
    """
    Evaluates whether the relocation attempt is safe and recommends an outcome.
    """
    decision_id = f"DEC_ORACLE_{uuid.uuid4().hex[:8]}"
    
    if not input_data.has_fault:
        if input_data.success:
            return RelocationSafetyOracleDecision(
                decision_id=decision_id,
                outcome="accept_shadow",
                justification="No faults detected and core relocation logic succeeded."
            )
        else:
            return RelocationSafetyOracleDecision(
                decision_id=decision_id,
                outcome="abort_relocation",
                justification=f"Relocation failed with errors: {', '.join(input_data.errors)}"
            )
            
    # If there is an active fault, look up expected outcome
    expected = classify_expected_outcome(input_data.fault_category)
    justification = f"Fault '{input_data.fault_category}' was injected; safety oracle recommends: {expected}"
    
    return RelocationSafetyOracleDecision(
        decision_id=decision_id,
        outcome=expected,
        justification=justification
    )


def compare_actual_to_expected_outcome(expected: str, actual: str) -> bool:
    """
    Validates that actual outcome matches expected outcome.
    Safe fallbacks (any outcome that is not accept_shadow when expected is an error) are acceptable.
    """
    if expected == "accept_shadow":
        return actual == "accept_shadow"
        
    # Any outcome that correctly holds, aborts, rolls back, quarantines, or rejects is considered safe.
    safe_outcomes = [
        "hold_relocation",
        "abort_relocation",
        "rollback_relocation",
        "quarantine_state_ref",
        "quarantine_manifold",
        "reject_candidate"
    ]
    return (actual == expected) or (actual in safe_outcomes)
