# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Rebalance Faults
==============================
Injects physical faults into waveguide rebalance plans.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import time
import uuid

@dataclass
class WaveguideRebalanceFault:
    fault_id: str
    category: str
    description: str

@dataclass
class WaveguideFaultInjectionResult:
    injection_id: str
    fault: WaveguideRebalanceFault
    success: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class WaveguideFaultAuditReport:
    report_id: str
    success: bool
    quarantine_recommended: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def inject_missing_pml_coverage(rebalance_plan: Any) -> Any:
    """
    Removes PML coverage from all candidates in the plan.
    """
    for cand in getattr(rebalance_plan, "candidates", []):
        cand.has_pml_coverage = False
    return rebalance_plan


def inject_carrier_identity_break(rebalance_plan: Any) -> Any:
    """
    Breaks carrier identity preservation for all candidates in the plan.
    """
    for cand in getattr(rebalance_plan, "candidates", []):
        cand.preserves_carrier_identity = False
    return rebalance_plan


def inject_quadrature_pair_break(rebalance_plan: Any) -> Any:
    """
    Breaks quadrature pairings preservation for all candidates in the plan.
    """
    for cand in getattr(rebalance_plan, "candidates", []):
        cand.preserves_quadrature_pairings = False
    return rebalance_plan


def inject_lane_isolation_breach(rebalance_plan: Any) -> Any:
    """
    Breaks lane identity preservation (isolation) for all candidates in the plan.
    """
    for cand in getattr(rebalance_plan, "candidates", []):
        cand.preserves_lane_identity = False
    return rebalance_plan


def inject_prefix_carry_bridge_break(rebalance_plan: Any) -> Any:
    """
    Breaks prefix carry preservation for all candidates in the plan.
    """
    for cand in getattr(rebalance_plan, "candidates", []):
        cand.preserves_prefix_carry = False
    return rebalance_plan


def inject_boundary_reflection_breach(rebalance_plan: Any, magnitude: float) -> Any:
    """
    Sets estimated boundary reflection beyond the safe threshold.
    """
    for cand in getattr(rebalance_plan, "candidates", []):
        cand.estimated_boundary_reflection = magnitude
    return rebalance_plan
