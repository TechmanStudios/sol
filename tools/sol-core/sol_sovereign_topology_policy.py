# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Sovereign Topology Policy
=============================
Defines standard constraints, risks, and properties required to plan safe relocation actions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class TopologyRelocationConstraint:
    name: str
    limit: float
    hard: bool = True

@dataclass
class TopologyRelocationGateResult:
    gate_name: str
    passed: bool
    message: str

@dataclass
class TopologyRelocationRiskEstimate:
    risk_level: str  # "low", "medium", "high"
    crosstalk_risk: float
    boundary_reflection_risk: float
    coherence_risk: float

@dataclass
class SovereignTopologyPolicy:
    shadow_only_by_default: bool = True
    preserve_active_phase_tables: bool = True
    preserve_active_carrier_registry: bool = True
    preserve_active_cadence_profiles: bool = True
    preserve_hcam_banks: bool = True
    preserve_pml_boundaries: bool = True
    preserve_prefix_carry_bridges: bool = True
    preserve_transaction_boundaries: bool = True
    preserve_atomic_commit_boundaries: bool = True
    preserve_state_hash_refs: bool = True
    max_shape_distortion: float = 1.0
    max_route_depth_increase: float = 2.0
    max_boundary_crossing_increase: float = 0.0
    max_crosstalk: float = 0.05
    max_boundary_reflection: float = 0.02
    rollback_required_for_live_trial: bool = True
    court_token_required_for_sandbox_execution: bool = True
    constraints: List[TopologyRelocationConstraint] = field(default_factory=list)
