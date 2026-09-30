# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Uncertainty Fault Audit
===========================
Audits wavefront uncertainty window faults and dispersion breaches.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class UncertaintyFaultCase:
    case_id: str
    category: str  # unbounded_window, dispersion_breach, invalid_bound
    description: str
    injected_value: Any = None

@dataclass
class UncertaintyFaultResult:
    result_id: str
    case_id: str
    blocks_promotion: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UncertaintyFaultAuditReport:
    report_id: str
    results: List[UncertaintyFaultResult]
    passed_audit: bool = False
    timestamp: float = field(default_factory=time.time)


def inject_unbounded_uncertainty_window(window: Any) -> Any:
    """
    Sets bounds/flags to make the uncertainty window unbounded.
    """
    import copy
    mutated = copy.deepcopy(window)
    if hasattr(mutated, "bound") and mutated.bound:
        mutated.bound.is_bounded = False
    elif isinstance(mutated, dict):
        mutated.setdefault("bound", {})["is_bounded"] = False
    return mutated


def inject_dispersion_breach(window: Any, magnitude: float) -> Any:
    """
    Injects a packet dispersion breach into the uncertainty window report.
    """
    import copy
    mutated = copy.deepcopy(window)
    if hasattr(mutated, "dispersion"):
        mutated.dispersion = magnitude
    elif isinstance(mutated, dict):
        mutated["dispersion"] = magnitude
    return mutated


def inject_invalid_uncertainty_bound(window: Any) -> Any:
    """
    Sets bound limits to invalid (e.g. negative or infinite).
    """
    import copy
    mutated = copy.deepcopy(window)
    if hasattr(mutated, "bound") and mutated.bound:
        mutated.bound.min_amplitude = -1.0
        mutated.bound.max_amplitude = -1.0
    elif isinstance(mutated, dict):
        mutated.setdefault("bound", {})["min_amplitude"] = -1.0
        mutated.setdefault("bound", {})["max_amplitude"] = -1.0
    return mutated


def validate_uncertainty_fault_response(report: UncertaintyFaultAuditReport) -> bool:
    """
    Checks that any unbounded uncertainty or dispersion breach blocks promotion.
    """
    # If any case is present, passed_audit must be False, blocking promotion
    return len(report.results) == 0 or not report.passed_audit
