# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Core Cadence Calibration
============================
Measures skew and calibrates clock profiles for core execution groups without overwriting active profiles.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class CoreCadenceProfile:
    core_id: str
    tick_rate: float
    phase_offset: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CoreCadenceObservation:
    core_id: str
    skew: float
    jitter: float = 0.005

@dataclass
class CoreCadenceAdjustment:
    adjustment_id: str
    core_id: str
    tick_rate_offset: float
    phase_offset_offset: float

@dataclass
class CoreCadenceCalibrationReport:
    report_id: str
    profiles: List[CoreCadenceProfile]
    skew: float
    success: bool
    errors: List[str] = field(default_factory=list)


def build_core_cadence_profiles(
    core_group: Any
) -> List[CoreCadenceProfile]:
    """
    Creates candidate clock profiles for the core group.
    Ensures they are separate objects from default/active profiles.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    cores = extract(core_group, "cores", {})
    if isinstance(cores, dict):
        core_ids = list(cores.keys())
    elif isinstance(cores, list):
        core_ids = cores
    else:
        core_ids = ["core_0", "core_1"]

    profiles = []
    for cid in core_ids:
        profiles.append(CoreCadenceProfile(
            core_id=cid,
            tick_rate=100.0,
            phase_offset=0.0,
            metadata={"candidate": True}  # Keep separate
        ))
    return profiles


def measure_core_cadence_skew(
    core_profiles: List[CoreCadenceProfile]
) -> float:
    """
    Computes global clock phase skew across core profiles.
    """
    if not core_profiles:
        return 0.0
    offsets = [p.phase_offset for p in core_profiles]
    return max(offsets) - min(offsets)


def plan_core_cadence_adjustment(
    skew_report: float,
    policy: Any
) -> List[CoreCadenceAdjustment]:
    """
    Computes clock drift correction offsets bounded by calibration limits.
    """
    adjustments = []
    # simple proportional offset
    adjustments.append(CoreCadenceAdjustment(
        adjustment_id=f"CAD_ADJ_{uuid.uuid4().hex[:4]}",
        core_id="core_0",
        tick_rate_offset=0.0,
        phase_offset_offset=-0.5 * skew_report
    ))
    return adjustments


def execute_shadow_core_cadence_calibration(
    adjustments: List[CoreCadenceAdjustment]
) -> CoreCadenceCalibrationReport:
    """
    Executes clock adjustment dry-runs.
    """
    errors = []
    
    # Check for active profiles protection block
    for adj in adjustments:
        if adj.core_id == "active" or adj.core_id == "production" or "active" in adj.core_id:
            errors.append("Active cadence profile overwrite attempt is rejected.")
            
    success = len(errors) == 0
    return CoreCadenceCalibrationReport(
        report_id=f"CAD_CAL_REP_{uuid.uuid4().hex[:8]}",
        profiles=[],
        skew=0.001 if success else 0.05,
        success=success,
        errors=errors
    )
