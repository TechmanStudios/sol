# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Layout Optimizer
==============================
Estimates physical routing costs, lane crossings, junction overhead, and optimizes lane spacing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_waveguide_synthesis_policy import WaveguideSynthesisCostEstimate
import time

@dataclass
class WaveguideLayoutOptimizationCandidate:
    candidate_id: str
    fabric_candidate: Any = None  # WaveguideFabricCandidate
    positions: Dict[str, tuple] = field(default_factory=dict)
    crossings: List[tuple] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    candidate: Any = None
    spatial_positions: Dict[str, tuple] = field(default_factory=dict)

    def __post_init__(self):
        if self.candidate is not None and self.fabric_candidate is None:
            self.fabric_candidate = self.candidate
        if self.fabric_candidate is not None and self.candidate is None:
            self.candidate = self.fabric_candidate
        if self.spatial_positions and not self.positions:
            self.positions = self.spatial_positions
        if self.positions and not self.spatial_positions:
            self.spatial_positions = self.positions

@dataclass
class WaveguideLayoutOptimizationPlan:
    plan_id: str
    candidate: Any = None
    strategy: str = "balanced"
    optimization_steps: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.steps and not self.optimization_steps:
            self.optimization_steps = self.steps
        if self.optimization_steps and not self.steps:
            self.steps = self.optimization_steps

@dataclass
class WaveguideLayoutOptimizationReport:
    report_id: str
    plan: Any = None
    before_cost: Any = None
    after_cost: Any = None
    improvement_ratio: float = 0.0
    timestamp: float = field(default_factory=time.time)
    before: Any = None
    after: Any = None
    synthesis_policy: Any = None
    success: bool = True
    errors: List[str] = field(default_factory=list)
    lane_crossings: int = 0
    junction_degree: int = 0
    estimated_crosstalk: float = 0.0
    estimated_boundary_reflection: float = 0.0

    def __post_init__(self):
        if self.before is not None and self.before_cost is None:
            self.before_cost = self.before
        if self.before_cost is not None and self.before is None:
            self.before = self.before_cost
        if self.after is not None and self.after_cost is None:
            self.after_cost = self.after
        if self.after_cost is not None and self.after is None:
            self.after = self.after_cost


def estimate_waveguide_layout_cost(candidate: Any) -> WaveguideSynthesisCostEstimate:
    """
    Computes an estimate of physical routing costs, crosstalk risk, and PML coverage.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    candidate_id = extract(candidate, "candidate_id", "unknown")
    fabric = extract(candidate, "fabric_candidate", candidate)
    
    # Extract structural counts
    segments = extract(fabric, "segments", [])
    junctions = extract(fabric, "junctions", [])
    lane_bindings = extract(fabric, "lane_bindings", [])
    
    # Calculate costs
    route_depth = len(segments)
    junction_count = len(junctions)
    
    # Crossings calculation (mock/actual based on candidate crossings list)
    crossings_list = extract(candidate, "crossings", [])
    lane_crossings = len(crossings_list)
    
    # Junction degree cost
    max_deg = max([extract(j, "degree", 2) for j in junctions]) if junctions else 2
    
    boundary_crossings = len(lane_bindings)
    
    # Risk estimations
    estimated_crosstalk_risk = 0.01 * lane_crossings + 0.005 * max_deg
    phase_alignment_risk = 0.005 * route_depth
    pml_absorption_coverage = 0.98 - 0.01 * boundary_crossings
    simd_dispatch_overhead = 0.02 * len(lane_bindings)
    
    # Total cost
    total_cost = (
        route_depth * 1.5 +
        lane_crossings * 5.0 +
        junction_count * 2.0 +
        boundary_crossings * 1.0 +
        estimated_crosstalk_risk * 100.0 +
        phase_alignment_risk * 50.0 +
        (1.0 - pml_absorption_coverage) * 200.0
    )
    
    return WaveguideSynthesisCostEstimate(
        candidate_id=candidate_id,
        route_depth=route_depth,
        lane_crossings=lane_crossings,
        junction_count=junction_count,
        boundary_crossings=boundary_crossings,
        estimated_crosstalk_risk=estimated_crosstalk_risk,
        phase_alignment_risk=phase_alignment_risk,
        pml_absorption_coverage=pml_absorption_coverage,
        simd_dispatch_overhead=simd_dispatch_overhead,
        total_cost=total_cost
    )


def identify_layout_bottlenecks(candidate: Any) -> List[str]:
    """
    Identifies high junction degree, excessive crossings, or PML coverage leaks.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    bottlenecks = []
    fabric = extract(candidate, "fabric_candidate", candidate)
    
    junctions = extract(fabric, "junctions", [])
    for j in junctions:
        if extract(j, "degree", 0) > 4:
            bottlenecks.append(f"High junction degree at {extract(j, 'junction_id')}: {extract(j, 'degree')}")
            
    crossings = extract(candidate, "crossings", [])
    if len(crossings) > 2:
        bottlenecks.append(f"Excessive waveguide lane crossings: {len(crossings)}")
        
    return bottlenecks


def optimize_waveguide_layout_shadow(candidate: Any, strategy: str = "balanced") -> WaveguideLayoutOptimizationCandidate:
    """
    Runs a shadow layout optimization routine to reduce crossing and crosstalk costs.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    candidate_id = extract(candidate, "candidate_id", "unknown")
    fabric = extract(candidate, "fabric_candidate", candidate)
    positions = dict(extract(candidate, "positions", {}))
    
    # Adjust spacing or crossings list based on optimization strategy
    optimized_crossings = []
    if strategy == "crosstalk_minimization":
        # Simulate resolving all crossings
        optimized_crossings = []
    else:
        # Balanced strategy retains up to 1 crossing if existing
        existing_crossings = extract(candidate, "crossings", [])
        optimized_crossings = existing_crossings[:1]

    # Shift positions slightly
    opt_positions = {}
    for k, v in positions.items():
        if isinstance(v, tuple) and len(v) >= 2:
            opt_positions[k] = (v[0] + 0.1, v[1])
        else:
            opt_positions[k] = v

    return WaveguideLayoutOptimizationCandidate(
        candidate_id=f"OPT_{candidate_id}",
        fabric_candidate=fabric,
        positions=opt_positions,
        crossings=optimized_crossings,
        metadata={"optimized_strategy": strategy}
    )


def compare_waveguide_layouts(before: Any, after: Any) -> Dict[str, Any]:
    """
    Calculates cost reduction and efficiency gains between two candidates.
    """
    cost_before = estimate_waveguide_layout_cost(before)
    cost_after = estimate_waveguide_layout_cost(after)
    
    diff = cost_before.total_cost - cost_after.total_cost
    ratio = diff / cost_before.total_cost if cost_before.total_cost > 0 else 0.0
    
    return {
        "cost_before": cost_before.total_cost,
        "cost_after": cost_after.total_cost,
        "cost_reduction": diff,
        "improvement_ratio": ratio,
        "crosstalk_risk_reduction": cost_before.estimated_crosstalk_risk - cost_after.estimated_crosstalk_risk
    }
