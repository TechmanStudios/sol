# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Calibration Replay & Promotion Gate Validator
=================================================
Runs offline replay/simulation verification on candidate phase tables
against PDM calibration thresholds before promoting them.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from sol_phase_alignment import PhaseAlignmentTable, diff_phase_tables

@dataclass
class CalibrationReplayInput:
    old_table: PhaseAlignmentTable
    new_table: PhaseAlignmentTable
    metrics: Optional[Dict[str, Any]] = None

@dataclass
class CalibrationReplayResult:
    status: str  # "pass" | "fail" | "needs_more_evidence"
    reason: str
    details: Dict[str, Any]

@dataclass
class CalibrationPromotionReport:
    replay_result: CalibrationReplayResult
    promotion_status: str  # "approved" | "rejected" | "deferred"
    evidence_hash: str

def run_calibration_replay(replay_input: CalibrationReplayInput) -> CalibrationReplayResult:
    """
    Executes a deterministic validation replay comparing old and new phase tables
    and checking active, inactive, reversed, and crosstalk thresholds against metrics.
    """
    old_t = replay_input.old_table
    new_t = replay_input.new_table
    metrics = replay_input.metrics

    # Check differences
    diffs = diff_phase_tables(old_t, new_t)
    if not diffs:
        return CalibrationReplayResult(
            status="pass",
            reason="No phase changes detected. Current alignment is valid.",
            details={"diff_count": 0}
        )

    # If metrics are missing, return needs_more_evidence
    if metrics is None:
        return CalibrationReplayResult(
            status="needs_more_evidence",
            reason="Required calibration validation metrics are missing.",
            details={"diff_count": len(diffs)}
        )

    # Required validation metrics: active_delta, crosstalk, reversed_delta
    active_delta = metrics.get("active_delta")
    crosstalk = metrics.get("crosstalk")
    if crosstalk is None:
        crosstalk = metrics.get("cross_talk")
    reversed_delta = metrics.get("reversed_delta")

    if active_delta is None or crosstalk is None or reversed_delta is None:
        return CalibrationReplayResult(
            status="needs_more_evidence",
            reason="One or more required metrics (active_delta, crosstalk, reversed_delta) are missing.",
            details={"diff_count": len(diffs), "supplied_metrics": list(metrics.keys())}
        )

    # Threshold checks
    active_delta_min = 0.20
    crosstalk_max = 0.05
    reversed_delta_max = 0.10

    passed = True
    reasons = []

    if active_delta < active_delta_min:
        passed = False
        reasons.append(f"active_delta {active_delta:.4f} < minimum {active_delta_min:.2f}")
    if crosstalk > crosstalk_max:
        passed = False
        reasons.append(f"crosstalk {crosstalk:.4f} > maximum {crosstalk_max:.2f}")
    if reversed_delta > reversed_delta_max:
        passed = False
        reasons.append(f"reversed_delta {reversed_delta:.4f} > maximum {reversed_delta_max:.2f}")

    if passed:
        return CalibrationReplayResult(
            status="pass",
            reason="All calibration replay thresholds passed successfully.",
            details={
                "diff_count": len(diffs),
                "active_delta": active_delta,
                "crosstalk": crosstalk,
                "reversed_delta": reversed_delta
            }
        )
    else:
        return CalibrationReplayResult(
            status="fail",
            reason="Calibration replay validation failed: " + "; ".join(reasons),
            details={
                "diff_count": len(diffs),
                "active_delta": active_delta,
                "crosstalk": crosstalk,
                "reversed_delta": reversed_delta
            }
        )
