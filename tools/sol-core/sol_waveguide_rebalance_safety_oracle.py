# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Rebalance Safety Oracle
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import uuid

@dataclass
class WaveguideRebalanceOracleInput:
    candidate: Any
    telemetry: Dict[str, Any]
    policy: Dict[str, Any]

@dataclass
class WaveguideRebalanceOracleDecision:
    decision_id: str
    verdict: str  # "accept_shadow", "hold_rebalance", "reject_candidate", "rollback_rebalance", "quarantine_route", "quarantine_waveguide_segment", "quarantine_manifold"
    justification: str

@dataclass
class WaveguideRebalanceOracleReport:
    report_id: str
    input_data: WaveguideRebalanceOracleInput
    decision: WaveguideRebalanceOracleDecision
    agreement: bool = True


def classify_rebalance_expected_outcome(candidate: Any) -> str:
    """
    Classifies the expected outcome based on candidate properties.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    has_pml = extract(candidate, "has_pml_coverage", True)
    preserves_carry = extract(candidate, "preserves_prefix_carry", True)
    crosstalk = extract(candidate, "estimated_crosstalk", 0.0)
    reflection = extract(candidate, "estimated_boundary_reflection", 0.0)
    preserves_lane = extract(candidate, "preserves_lane_identity", True)
    preserves_carrier = extract(candidate, "preserves_carrier_identity", True)
    preserves_quad = extract(candidate, "preserves_quadrature_pairings", True)

    # Classifications for unsafe candidates
    if not has_pml:
        return "reject_candidate"
        
    if not preserves_carry:
        return "quarantine_manifold"
        
    if crosstalk > 0.05:
        return "quarantine_waveguide_segment"
        
    if reflection > 0.05:
        return "quarantine_route"
        
    if not preserves_lane or not preserves_carrier or not preserves_quad:
        return "reject_candidate"

    # Specific classifications for telemetry flags
    telemetry = getattr(candidate, "telemetry", {}) or {}
    if telemetry.get("lock_violation", False):
        return "hold_rebalance"
    if telemetry.get("rollback_failure", False):
        return "rollback_rebalance"
        
    return "accept_shadow"


def evaluate_waveguide_rebalance_safety(
    input_data: WaveguideRebalanceOracleInput
) -> WaveguideRebalanceOracleDecision:
    """
    Evaluates waveguide rebalance safety based on input candidate and telemetry.
    """
    verdict = classify_rebalance_expected_outcome(input_data.candidate)
    justification = f"Safety oracle determined verdict: {verdict}"
    
    return WaveguideRebalanceOracleDecision(
        decision_id=f"DEC_SO_{uuid.uuid4().hex[:8]}",
        verdict=verdict,
        justification=justification
    )


def compare_rebalance_actual_to_expected(
    expected: str,
    actual: str
) -> bool:
    """
    Compares the expected outcome with the actual outcome.
    """
    return expected == actual


def compare_fault_expected_to_actual_outcome(fault_case: Any, actual: str) -> bool:
    """
    Compares expected fault outcome to actual outcome.
    """
    expected = getattr(fault_case, "expected_outcome", "")
    if not expected and isinstance(fault_case, dict):
        expected = fault_case.get("expected_outcome", "")
    return expected == actual


def validate_safety_oracle_regression(matrix_report: Any) -> bool:
    """
    Validates that the safety oracle outcomes did not regress compared to expectations.
    """
    results = getattr(matrix_report, "results", [])
    for r in results:
        if not getattr(r, "matched_expected", True):
            return False
    return getattr(matrix_report, "success", True)

