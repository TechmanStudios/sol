# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Phase Alignment & Drift Checking
====================================
Defines phase alignment tables, entries, error metrics, and tolerance checking
for PDM carrier waves on the WideWord compute fabric.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class PhaseAlignmentEntry:
    carrier_period: float
    quadrature: str  # "sin" or "cos"
    calibrated_phase: float

@dataclass
class PhaseAlignmentTable:
    lane_id: int
    entries: List[PhaseAlignmentEntry]

@dataclass
class PhaseDriftObservation:
    lane_id: int
    max_phase_error: float
    average_phase_error: float
    out_of_tolerance: bool
    evidence: Dict[str, Any]

@dataclass
class PhaseAlignmentReport:
    lane_id: int
    drift_observation: PhaseDriftObservation
    evidence: Dict[str, Any]

def build_default_phase_table(lane_id: int, periods: List[float]) -> PhaseAlignmentTable:
    """
    Initializes a default PhaseAlignmentTable for 4 carrier periods × 2 quadratures (sine/cosine).
    Default phase is set to 0.0.
    """
    entries = []
    for period in periods:
        for quad in ["sin", "cos"]:
            entries.append(PhaseAlignmentEntry(
                carrier_period=period,
                quadrature=quad,
                calibrated_phase=0.0
            ))
    return PhaseAlignmentTable(lane_id=lane_id, entries=entries)

def phase_error(expected_phase: float, observed_phase: float) -> float:
    """
    Calculates the shortest angular difference (phase error) between expected and observed phase.
    Wraps the error correctly to the range [-pi, pi].
    """
    diff = (observed_phase - expected_phase) % (2.0 * math.pi)
    if diff > math.pi:
        diff -= 2.0 * math.pi
    return diff

def observe_phase_drift(expected_table: PhaseAlignmentTable, observed_table: PhaseAlignmentTable) -> PhaseDriftObservation:
    """
    Compares the expected alignment table against the observed table to calculate phase error deltas.
    Returns a PhaseDriftObservation.
    """
    if expected_table.lane_id != observed_table.lane_id:
        raise ValueError(
            f"Mismatched lane IDs: expected {expected_table.lane_id}, observed {observed_table.lane_id}"
        )

    errors = []
    details = []
    
    # Map observed entries for easy lookup
    obs_map = {
        (entry.carrier_period, entry.quadrature): entry.calibrated_phase
        for entry in observed_table.entries
    }

    for exp_entry in expected_table.entries:
        key = (exp_entry.carrier_period, exp_entry.quadrature)
        obs_phase = obs_map.get(key, 0.0)
        
        err = phase_error(exp_entry.calibrated_phase, obs_phase)
        errors.append(abs(err))
        details.append({
            "period": exp_entry.carrier_period,
            "quadrature": exp_entry.quadrature,
            "expected_phase": exp_entry.calibrated_phase,
            "observed_phase": obs_phase,
            "error": err
        })

    max_err = max(errors) if errors else 0.0
    avg_err = sum(errors) / len(errors) if errors else 0.0
    out_of_tolerance = max_err > 0.05

    evidence = {
        "channel_errors": details,
        "raw_errors": errors
    }

    return PhaseDriftObservation(
        lane_id=expected_table.lane_id,
        max_phase_error=max_err,
        average_phase_error=avg_err,
        out_of_tolerance=out_of_tolerance,
        evidence=evidence
    )

def is_within_phase_tolerance(observation: PhaseDriftObservation, tolerance: float = 0.05) -> bool:
    """
    Evaluates whether the observation's maximum phase error is within the specified tolerance.
    """
    return abs(observation.max_phase_error) <= tolerance


def apply_candidate_phase_correction(table: PhaseAlignmentTable, correction: Any) -> PhaseAlignmentTable:
    """
    Creates and returns a new PhaseAlignmentTable with the candidate phase correction applied,
    preserving the original table immutably.
    """
    new_entries = []
    
    target_channel = getattr(correction, "target_channel", None)
    bounded_delta = getattr(correction, "bounded_delta", 0.0)
    target_lane = getattr(correction, "target_lane", None)
    
    if target_lane is not None and target_lane != table.lane_id:
        for entry in table.entries:
            new_entries.append(PhaseAlignmentEntry(
                carrier_period=entry.carrier_period,
                quadrature=entry.quadrature,
                calibrated_phase=entry.calibrated_phase
            ))
        return PhaseAlignmentTable(lane_id=table.lane_id, entries=new_entries)

    for entry in table.entries:
        phase_val = entry.calibrated_phase
        is_target = False
        if target_channel is not None:
            if isinstance(target_channel, (tuple, list)) and len(target_channel) == 2:
                if entry.carrier_period == target_channel[0] and entry.quadrature == target_channel[1]:
                    is_target = True
            elif entry.carrier_period == target_channel or entry.quadrature == target_channel:
                is_target = True
        else:
            is_target = True

        if is_target:
            phase_val += bounded_delta

        new_entries.append(PhaseAlignmentEntry(
            carrier_period=entry.carrier_period,
            quadrature=entry.quadrature,
            calibrated_phase=phase_val
        ))

    return PhaseAlignmentTable(lane_id=table.lane_id, entries=new_entries)


def diff_phase_tables(old_table: PhaseAlignmentTable, new_table: PhaseAlignmentTable) -> Dict[tuple, tuple]:
    """
    Compares two phase tables and returns a dictionary of differences.
    Key: (carrier_period, quadrature), Value: (old_phase, new_phase)
    """
    diffs = {}
    old_map = {
        (e.carrier_period, e.quadrature): e.calibrated_phase for e in old_table.entries
    }
    for entry in new_table.entries:
        key = (entry.carrier_period, entry.quadrature)
        old_val = old_map.get(key, 0.0)
        if abs(entry.calibrated_phase - old_val) > 1e-9:
            diffs[key] = (old_val, entry.calibrated_phase)
    return diffs


def validate_phase_table_bounds(table: PhaseAlignmentTable, policy: Any) -> bool:
    """
    Validates that all phase values in the table fall within bounded limits.
    """
    for entry in table.entries:
        if not math.isfinite(entry.calibrated_phase):
            return False
        if abs(entry.calibrated_phase) > 2.0 * math.pi:
            return False
    return True


def build_distributed_phase_alignment_table(boundary_groups: List[Any]) -> PhaseAlignmentTable:
    """
    Builds a candidate PhaseAlignmentTable separate from active phase tables.
    """
    entries = []
    # Use standard periods [11.0, 13.0, 17.0, 19.0]
    for period in [11.0, 13.0, 17.0, 19.0]:
        for quad in ["sin", "cos"]:
            entries.append(PhaseAlignmentEntry(
                carrier_period=period,
                quadrature=quad,
                calibrated_phase=0.0
            ))
    # Return as candidate table (indicated by target lane_id = -30)
    return PhaseAlignmentTable(lane_id=-30, entries=entries)


def compare_phase_alignment_tables(before: PhaseAlignmentTable, after: PhaseAlignmentTable) -> Dict[tuple, tuple]:
    """
    Compares before and after alignment tables returning the differences.
    """
    return diff_phase_tables(before, after)


def validate_phase_adjustment_bounds(adjustment: Any, policy: Any) -> bool:
    """
    Enforces maximum phase correction bounds on calibration adjustments.
    """
    max_corr = getattr(policy, "max_phase_correction", 0.05)
    if not max_corr and policy:
        max_corr = getattr(policy, "max_phase_nudge", 0.05)
    val = abs(getattr(adjustment, "phase_correction", 0.0) or getattr(adjustment, "nudge_value", 0.0))
    return val <= max_corr


