# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Dispersion Model
==============================
Simulates physical waveguide signal distortion, group delays, and phase shifts
due to frequency-dependent wave propagation velocities.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class DispersionProfile:
    lane_id: int
    lane_length: float
    dispersion_coeff: float
    periods: List[float]
    group_delays: Dict[float, float]
    phase_shifts: Dict[float, float]
    evidence: Dict[str, Any]

@dataclass
class DispersionObservation:
    lane_id: int
    dispersion_profile: DispersionProfile
    max_delay: float
    max_phase_shift: float
    evidence: Dict[str, Any]

def estimate_group_delay(period: float, lane_length: float, dispersion_coeff: float) -> float:
    """
    Computes deterministic placeholder group delay.
    Delay is inversely proportional to carrier period.
    """
    if period <= 0.0:
        return 0.0
    return (dispersion_coeff * lane_length) / period

def estimate_phase_shift(period: float, distance: float, dispersion_coeff: float) -> float:
    """
    Computes deterministic phase shift wrapped to [0, 2*pi).
    """
    if period <= 0.0:
        return 0.0
    # Phase shift is proportional to frequency (1/period) and distance
    shift = (dispersion_coeff * distance * (2.0 * math.pi / period)) % (2.0 * math.pi)
    return shift

def build_dispersion_profile(lane_id: int, periods: List[float], lane_length: float = 512.0) -> DispersionProfile:
    """
    Generates a DispersionProfile for a waveguide lane with the given carrier periods.
    """
    dispersion_coeff = 0.015  # Deterministic placeholder constant
    group_delays = {}
    phase_shifts = {}

    for period in periods:
        group_delays[period] = estimate_group_delay(period, lane_length, dispersion_coeff)
        phase_shifts[period] = estimate_phase_shift(period, lane_length, dispersion_coeff)

    evidence = {
        "lane_id": lane_id,
        "lane_length": lane_length,
        "dispersion_coeff": dispersion_coeff,
        "periods": periods
    }

    return DispersionProfile(
        lane_id=lane_id,
        lane_length=lane_length,
        dispersion_coeff=dispersion_coeff,
        periods=periods,
        group_delays=group_delays,
        phase_shifts=phase_shifts,
        evidence=evidence
    )
