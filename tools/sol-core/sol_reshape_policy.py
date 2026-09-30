# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Reshape & Carrier Relocation Policy
=======================================
Defines policy limits and gate results for multi-dimensional reshapes and dynamic relocations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ManifoldReshapePolicy:
    shadow_only_by_default: bool = True
    preserve_active_phase_tables: bool = True
    preserve_active_carrier_registry: bool = True
    preserve_hcam_banks: bool = True
    preserve_pml_boundaries: bool = True
    preserve_lane_isolation: bool = True
    preserve_tensor_shape_or_record_projection: bool = True
    max_coordinate_distortion: float = 10.0
    max_phase_error: float = 0.05
    max_crosstalk: float = 0.05
    max_boundary_reflection: float = 0.05
    rollback_required_for_live_trial: bool = True
    court_token_required_for_sandbox_execution: bool = True

@dataclass
class CarrierRelocationPolicy:
    shadow_only_by_default: bool = True
    preserve_active_phase_tables: bool = True
    preserve_active_carrier_registry: bool = True
    preserve_hcam_banks: bool = True
    preserve_pml_boundaries: bool = True
    preserve_lane_isolation: bool = True
    max_phase_error: float = 0.05
    max_crosstalk: float = 0.05
    max_boundary_reflection: float = 0.05
    max_carrier_moves_per_plan: int = 10
    rollback_required_for_live_trial: bool = True
    court_token_required_for_sandbox_execution: bool = True

@dataclass
class ReshapeCarrierGateResult:
    passed: bool
    gates_checked: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
