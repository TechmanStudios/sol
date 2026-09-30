# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Synthesis Policy
==============================
Defines security policy, constraints, and cost estimation structures for waveguide fabric synthesis.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class WaveguideConstraint:
    name: str
    limit: Any
    description: str

@dataclass
class WaveguideSynthesisPolicy:
    shadow_only_by_default: bool = True
    preserve_phase_tables: bool = True
    preserve_hcam_banks: bool = True
    preserve_pml_boundaries: bool = True
    preserve_lane_isolation: bool = True
    max_crossings_per_lane: int = 2
    max_junction_degree: int = 4
    max_phase_error: float = 0.05
    max_crosstalk: float = 0.05
    min_boundary_absorption: float = 0.95
    rollback_required_for_live_trial: bool = True
    court_token_required_for_sandbox_execution: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideSynthesisGateResult:
    gate_name: str
    passed: bool
    description: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideSynthesisCostEstimate:
    candidate_id: str
    route_depth: int
    lane_crossings: int
    junction_count: int
    boundary_crossings: int
    estimated_crosstalk_risk: float
    phase_alignment_risk: float
    pml_absorption_coverage: float
    simd_dispatch_overhead: float
    total_cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)
