# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Boundary
======================
Scaffolds Perfectly Matched Layer (PML) damping and soliton/Hermite-Gaussian envelopes.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Callable

@dataclass
class PMLProfile:
    lane_id: int
    grid_size: int
    pml_cells: int
    boundary_gamma: float
    core_gamma: float
    profile: List[float]
    evidence: Dict[str, Any]

class WaveguideBoundary:
    """
    Manages PML parameters (absorbing layers, boundary cell grids) and Hermite-Gaussian envelopes
    to eliminate standing waves and crosstalk at waveguide termination boundaries.
    """
    def __init__(self, num_pml_cells: int = 32, boundary_damping: float = 0.15):
        self.num_pml_cells = num_pml_cells
        self.boundary_damping = boundary_damping

    def build_pml_profile(
        self,
        lane_id: int = 0,
        grid_size: int = 512,
        pml_cells: int = 32,
        core_gamma: float = 0.002,
        boundary_gamma: float = 0.15
    ) -> PMLProfile:
        """
        Builds a deterministic PML profile that smoothly increases damping
        near grid boundaries while maintaining core_gamma in the interior.
        """
        profile = []
        for x in range(grid_size):
            if x < pml_cells:
                # Left boundary region
                depth = (pml_cells - x) / pml_cells
                damping = core_gamma + (boundary_gamma - core_gamma) * (depth ** 2)
            elif x >= grid_size - pml_cells:
                # Right boundary region
                depth = (x - (grid_size - pml_cells - 1)) / pml_cells
                damping = core_gamma + (boundary_gamma - core_gamma) * (depth ** 2)
            else:
                # Interior active region
                damping = core_gamma
            profile.append(damping)

        evidence = {
            "pml_cells_left": pml_cells,
            "pml_cells_right": pml_cells,
            "min_damping": min(profile),
            "max_damping": max(profile)
        }

        return PMLProfile(
            lane_id=lane_id,
            grid_size=grid_size,
            pml_cells=pml_cells,
            boundary_gamma=boundary_gamma,
            core_gamma=core_gamma,
            profile=profile,
            evidence=evidence
        )

    def calculate_pml_damping_profile(self, grid_size: int) -> List[float]:
        """
        Generates a parabolic damping profile for boundary cells.
        Damping is 0 in the core region and increases towards the grid edges.
        (Retained for backward compatibility).
        """
        profile = []
        for x in range(grid_size):
            if x < self.num_pml_cells:
                # Left PML region
                depth = (self.num_pml_cells - x) / self.num_pml_cells
                damping = self.boundary_damping * (depth ** 2)
            elif x >= grid_size - self.num_pml_cells:
                # Right PML region
                depth = (x - (grid_size - self.num_pml_cells - 1)) / self.num_pml_cells
                damping = self.boundary_damping * (depth ** 2)
            else:
                # Core active region
                damping = 0.0
            profile.append(damping)
        return profile

    def apply_gaussian_envelope(self, x: float, t: float, amplitude: float, center: float, width: float) -> float:
        """
        Applies a localized gaussian spatial/temporal envelope to a carrier wave amplitude
        to prevent standing-wave collapse during long-range routing.
        """
        spatial_envelope = math.exp(-((x - center) ** 2) / (2 * (width ** 2)))
        return amplitude * spatial_envelope

    def get_temporal_gaussian_envelope(self, t0: float = 0.0, width: float = 1.0) -> Callable[[float], float]:
        """
        Returns a temporal Gaussian envelope function: f(t) = exp(-((t - t0) ** 2) / (2 * width ** 2))
        """
        return lambda t: math.exp(-((t - t0) ** 2) / (2 * (width ** 2)))


@dataclass
class PMLBoundaryConfig:
    grid_size: int
    pml_cells: int
    core_gamma: float
    boundary_gamma: float
    lane_id: int = 0

@dataclass
class PMLBoundaryState:
    config: PMLBoundaryConfig
    absorption_mask: Any  # np.ndarray or List[float]
    absorbed_energy: float = 0.0

@dataclass
class PMLAbsorptionReport:
    report_id: str
    pml_cells: int
    absorbed_energy: float
    reflection_score: float
    passed_gates: bool

def build_pml_absorption_mask(
    grid_size: int,
    pml_cells: int,
    core_gamma: float,
    boundary_gamma: float
) -> Any:
    """
    Builds a PML absorption mask that smoothly increases damping toward boundaries.
    """
    mask = []
    for x in range(grid_size):
        if x < pml_cells:
            depth = (pml_cells - x) / pml_cells
            damping = core_gamma + (boundary_gamma - core_gamma) * (depth ** 2)
        elif x >= grid_size - pml_cells:
            depth = (x - (grid_size - pml_cells - 1)) / pml_cells
            damping = core_gamma + (boundary_gamma - core_gamma) * (depth ** 2)
        else:
            damping = core_gamma
        mask.append(damping)
        
    try:
        import numpy as np
        return np.array(mask, dtype=np.float64)
    except ImportError:
        return mask

def apply_pml_absorption(wavefront_state: Any, pml_state: PMLBoundaryState) -> Any:
    """
    Applies PML absorption mask to wavefront velocities, updating state and recording absorbed energy.
    """
    u = wavefront_state.u
    v = wavefront_state.v
    mask = pml_state.absorption_mask
    mass = wavefront_state.metadata.get("semantic_mass")
    
    if mass is None:
        mass = [1.0] * len(v)
        
    try:
        import numpy as np
        if isinstance(v, np.ndarray):
            v_damped = v * (1.0 - mask)
            e_absorbed = 0.5 * np.sum(mass * (v ** 2 - v_damped ** 2))
            wavefront_state.v = v_damped
            pml_state.absorbed_energy += float(e_absorbed)
            return wavefront_state
    except ImportError:
        pass
        
    v_damped = []
    e_absorbed = 0.0
    for i in range(len(v)):
        vd = v[i] * (1.0 - mask[i])
        e_absorbed += 0.5 * mass[i] * (v[i] ** 2 - vd ** 2)
        v_damped.append(vd)
    wavefront_state.v = v_damped
    pml_state.absorbed_energy += float(e_absorbed)
    return wavefront_state

def measure_boundary_reflection(before_state: Any, after_state: Any, pml_state: PMLBoundaryState) -> float:
    """
    Measures ratio of wave displacement in boundary region vs total displacement.
    """
    pml_cells = pml_state.config.pml_cells
    grid_size = pml_state.config.grid_size
    
    u_after = after_state.u
    try:
        import numpy as np
        if isinstance(u_after, np.ndarray):
            boundary_u = np.sum(np.abs(u_after[:pml_cells])) + np.sum(np.abs(u_after[-pml_cells:]))
            total_u = np.sum(np.abs(u_after))
            if total_u > 1e-9:
                return float(min(1.0, max(0.0, boundary_u / total_u)))
            return 0.0
    except ImportError:
        pass
        
    boundary_u = sum(abs(u_after[i]) for i in range(pml_cells)) + sum(abs(u_after[i]) for i in range(grid_size - pml_cells, grid_size))
    total_u = sum(abs(x) for x in u_after)
    if total_u > 1e-9:
        return min(1.0, max(0.0, boundary_u / total_u))
    return 0.0


def validate_pml_for_synthesized_fabric(candidate: Any) -> bool:
    """
    Validates PML boundary absorption coverage for a synthesized candidate fabric.
    """
    lane_count = len(candidate.lane_bindings)
    if len(candidate.boundary_bindings) != lane_count:
        raise ValueError(f"PML validation detects missing boundary coverage: expected {lane_count}, found {len(candidate.boundary_bindings)}")
        
    for bnd in candidate.boundary_bindings:
        if not bnd.pml_profile_ref:
            raise ValueError(f"Missing PML boundary coverage for lane {bnd.lane_id}")
            
    return True


def validate_pml_feedback_adjustment(pml_state: Any, feedback_action: Any) -> bool:
    """
    Validates PML adjustments from feedback.
    Feedback must not reduce boundary absorption below policy minimum.
    """
    if pml_state is None or feedback_action is None:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    config = extract(pml_state, "config")
    if not config:
        return False
        
    boundary_gamma = extract(config, "boundary_gamma", 0.0)
    
    # Extract policy or meta minimum
    policy = extract(feedback_action, "policy")
    min_pml = 0.05
    if policy:
        min_pml = extract(policy, "min_pml_absorption", 0.05)
        
    # Check adjustments list
    adjustments = extract(feedback_action, "adjustments", []) or []
    pml_adj = 0.0
    
    if isinstance(adjustments, list):
        for adj in adjustments:
            pml_adj += extract(adj, "pml_adjustment", 0.0)
    else:
        pml_adj = extract(adjustments, "pml_adjustment", 0.0)
        
    new_gamma = boundary_gamma + pml_adj
    if new_gamma < min_pml:
        return False
        
    return True


def measure_pml_feedback_effectiveness(before: Any, after: Any) -> float:
    """
    Measures the difference in boundary reflection before and after PML feedback is applied.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    ref_before = extract(before, "reflection_score", 0.0) or extract(before, "reflection", 0.0)
    ref_after = extract(after, "reflection_score", 0.0) or extract(after, "reflection", 0.0)
    return float(ref_before - ref_after)


def validate_pml_for_interlane_bridges(topology: Any, pml_state: Any) -> bool:
    """
    Ensures that all inter-lane bridges are covered by valid PML boundary profiles.
    Prefix-carry bridge paths must not bypass PML coverage.
    """
    if pml_state is None:
        raise ValueError("PML boundary validation failed: pml_state is missing.")
        
    # Check if topology indicates a PML bypass
    if getattr(topology, "metadata", None) and topology.metadata.get("bypass_pml"):
        raise ValueError("PML validation detects missing bridge boundary coverage: bridge path bypasses PML.")
        
    return True


def measure_bridge_boundary_reflection(before: Any, after: Any) -> float:
    """
    Measures boundary reflection for inter-lane bridges before and after PML adjustments.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    ref_before = extract(before, "boundary_reflection", 0.0) or extract(before, "reflection", 0.0)
    ref_after = extract(after, "boundary_reflection", 0.0) or extract(after, "reflection", 0.0)
    return float(ref_before - ref_after)


def inject_missing_pml_boundary(pml_state: PMLBoundaryState) -> None:
    """
    Simulates a missing PML boundary by clearing configuration cell count and absorption mask.
    """
    pml_state.config.pml_cells = 0
    pml_state.absorption_mask = [0.0] * len(pml_state.absorption_mask)
    if not hasattr(pml_state, "metadata") or pml_state.metadata is None:
        pml_state.metadata = {}
    pml_state.metadata["pml_boundaries_invalid"] = True


def inject_boundary_reflection_breach(pml_state: PMLBoundaryState, magnitude: float) -> None:
    """
    Simulates a boundary reflection breach by injecting a high reflection score in metadata.
    """
    if not hasattr(pml_state, "metadata") or pml_state.metadata is None:
        pml_state.metadata = {}
    pml_state.metadata["reflection_breach"] = True
    pml_state.metadata["reflection_score"] = magnitude
    pml_state.metadata["high_reflection"] = True


def validate_pml_for_rebalanced_waveguide(
    rebalance_plan: Any
) -> bool:
    """
    Ensures that dynamic waveguide rebalancing does not remove or weaken required PML coverage.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not rebalance_plan:
        return True

    candidates = extract(rebalance_plan, "candidates", [])
    for cand in candidates:
        if not extract(cand, "has_pml_coverage", True):
            raise ValueError(f"Rebalance candidate {extract(cand, 'candidate_id')} lacks required PML coverage")

    return True


def measure_rebalance_boundary_reflection(
    before: Any,
    after: Any
) -> float:
    """
    Measures the boundary reflection score difference before and after rebalancing.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    ref_before = extract(before, "boundary_reflection", 0.0) or extract(before, "reflection", 0.0)
    ref_after = extract(after, "boundary_reflection", 0.0) or extract(after, "reflection", 0.0)
    
    return float(ref_before - ref_after)





