# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Wavefront Uncertainty Window
================================
Tracks and bounds deterministic uncertainty windows for wavefront propagation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class WavefrontUncertaintyWindow:
    packet_id: str
    phase_min: float
    phase_max: float
    amplitude_min: float
    amplitude_max: float
    frequency_min: float
    frequency_max: float

@dataclass
class WavefrontUncertaintyObservation:
    packet_id: str
    phase_observed: float
    amplitude_observed: float
    frequency_observed: float

@dataclass
class WavefrontUncertaintyBound:
    max_phase_uncertainty: float
    max_amplitude_uncertainty: float
    max_frequency_uncertainty: float
    is_bounded: bool = True

@dataclass
class WavefrontUncertaintyReport:
    report_id: str
    packet_id: str
    window: WavefrontUncertaintyWindow
    observation: WavefrontUncertaintyObservation
    bound: WavefrontUncertaintyBound
    phase_error: float
    amplitude_error: float
    frequency_error: float
    is_valid: bool
    timestamp: float = field(default_factory=time.time)


def build_uncertainty_window(
    packet: Any,
    policy: Any
) -> WavefrontUncertaintyWindow:
    """
    Builds the deterministic uncertainty range for a given packet.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    pid = extract(packet, "packet_id", "pkt_unknown")
    phase = extract(packet, "phase", 0.0)
    amp = extract(packet, "amplitude", 1.0)
    freq = extract(packet, "frequency", 10.0)

    # Policy details
    phase_tolerance = extract(policy, "phase_tolerance", 0.05)
    amp_tolerance = extract(policy, "amplitude_tolerance", 0.05)
    freq_tolerance = extract(policy, "frequency_tolerance", 0.1)

    return WavefrontUncertaintyWindow(
        packet_id=pid,
        phase_min=phase - phase_tolerance,
        phase_max=phase + phase_tolerance,
        amplitude_min=amp - amp_tolerance,
        amplitude_max=amp + amp_tolerance,
        frequency_min=freq - freq_tolerance,
        frequency_max=freq + freq_tolerance
    )


def measure_wavefront_uncertainty(
    packet: Any,
    baseline: Any
) -> WavefrontUncertaintyObservation:
    """
    Constructs an observation from the current packet parameters.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    pid = extract(packet, "packet_id", "pkt_unknown")
    phase = extract(packet, "phase", 0.0)
    amp = extract(packet, "amplitude", 1.0)
    freq = extract(packet, "frequency", 10.0)

    return WavefrontUncertaintyObservation(
        packet_id=pid,
        phase_observed=phase,
        amplitude_observed=amp,
        frequency_observed=freq
    )


def validate_uncertainty_within_bounds(
    report: WavefrontUncertaintyReport,
    policy: Any
) -> bool:
    """
    Validates whether measured uncertainty fits within the maximum bounds.
    If the bounds themselves are marked unbounded, it returns False.
    """
    if not report.bound.is_bounded:
        return False

    # Check phase error vs bound
    if report.phase_error > report.bound.max_phase_uncertainty:
        return False
    # Check amplitude error vs bound
    if report.amplitude_error > report.bound.max_amplitude_uncertainty:
        return False
    # Check frequency error vs bound
    if report.frequency_error > report.bound.max_frequency_uncertainty:
        return False

    return report.is_valid


def classify_wavefront_uncertainty_state(
    report: WavefrontUncertaintyReport
) -> str:
    """
    Classifies the stability state based on uncertainty deviations.
    """
    if not report.bound.is_bounded:
        return "unbounded_uncertainty"
    if not report.is_valid:
        return "out_of_bounds"
    
    total_deviation = report.phase_error + report.amplitude_error + report.frequency_error
    if total_deviation < 0.01:
        return "coherent"
    elif total_deviation < 0.05:
        return "stable"
    else:
        return "dispersed"


def export_uncertainty_fault_targets(report: WavefrontUncertaintyReport) -> List[str]:
    """
    Exports targets for uncertainty fault injection.
    """
    if not report:
        return ["pkt_default"]
    return [report.packet_id]


def validate_uncertainty_audit_response(
    report: WavefrontUncertaintyReport,
    expected_response: str
) -> bool:
    """
    Validates that uncertainty bounds and deterministic checks correctly block promotion on faults.
    """
    if not report:
        return True
    if not report.is_valid or not report.bound.is_bounded:
        # If invalid or unbounded, expected response should be a blocking/rejection action
        return expected_response in ["reject_candidate", "reject_level47_candidate", "hold_wavefront_calibration"]
    return True
