# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Manifold Reshape
====================
Manages planning, mapping, and verification of multi-dimensional manifold reshapes in shadow mode.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import math

@dataclass
class ManifoldDimensionAxis:
    name: str
    size: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ManifoldShape:
    dims: List[int]
    axes: List[ManifoldDimensionAxis] = field(default_factory=list)

    def total_elements(self) -> int:
        if not self.dims:
            return 0
        total = 1
        for d in self.dims:
            total *= d
        return total

@dataclass
class ManifoldReshapeIntent:
    source_shape: ManifoldShape
    target_shape: ManifoldShape
    policy: Any
    lossless: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ManifoldReshapeMapping:
    intent: ManifoldReshapeIntent
    coordinate_map: Dict[Tuple[int, ...], Tuple[int, ...]]  # Maps source coordinate to target coordinate
    preserved_node_refs: Dict[str, Any] = field(default_factory=dict)
    preserved_lane_bindings: List[Any] = field(default_factory=list)
    preserved_tensor_shards: List[Any] = field(default_factory=list)
    preserved_hcam_banks: List[Any] = field(default_factory=list)
    preserved_rollback_refs: List[Any] = field(default_factory=list)
    preserved_evidence_packets: List[Any] = field(default_factory=list)
    preserved_phase_tables: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ManifoldReshapePlan:
    plan_id: str
    intent: ManifoldReshapeIntent
    mapping: ManifoldReshapeMapping
    steps: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ManifoldReshapeResult:
    success: bool
    final_shape: ManifoldShape
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ManifoldReshapeReport:
    report_id: str
    plan: ManifoldReshapePlan
    result: ManifoldReshapeResult
    lossless: bool
    source_element_count: int
    target_element_count: int
    validation_passed: bool
    errors: List[str] = field(default_factory=list)


def build_manifold_reshape_intent(source_shape: ManifoldShape, target_shape: ManifoldShape, policy: Any) -> ManifoldReshapeIntent:
    """
    Constructs a reshape intent and checks if it's lossless by element count comparison.
    """
    source_count = source_shape.total_elements()
    target_count = target_shape.total_elements()
    lossless = (source_count == target_count)
    
    # Validation against policy
    max_distortion = getattr(policy, "max_coordinate_distortion", 10.0)
    # Check dimensions dimensions change count
    if abs(len(source_shape.dims) - len(target_shape.dims)) > max_distortion:
        raise ValueError("Dimensionality change exceeds max_coordinate_distortion policy threshold.")
        
    return ManifoldReshapeIntent(
        source_shape=source_shape,
        target_shape=target_shape,
        policy=policy,
        lossless=lossless
    )


def build_reshape_mapping(intent: ManifoldReshapeIntent) -> ManifoldReshapeMapping:
    """
    Creates a deterministic index-based coordinate projection mapping.
    Maps N-D coordinates by flattening to a 1D index and expanding to target N-D shape.
    """
    src_dims = intent.source_shape.dims
    tgt_dims = intent.target_shape.dims
    
    src_total = intent.source_shape.total_elements()
    tgt_total = intent.target_shape.total_elements()
    
    # For a lossless mapping, mapping is 1-to-1.
    # If lossy, map as many elements as fit, or pad.
    map_limit = min(src_total, tgt_total)
    
    coordinate_map = {}
    
    # Helper to convert linear index to coordinate tuple
    def idx_to_coord(idx: int, dims: List[int]) -> Tuple[int, ...]:
        coord = []
        rem = idx
        for d in reversed(dims):
            coord.append(rem % d)
            rem //= d
        return tuple(reversed(coord))

    # Helper to convert coordinate tuple to linear index
    def coord_to_idx(coord: Tuple[int, ...], dims: List[int]) -> int:
        idx = 0
        mult = 1
        for c, d in zip(reversed(coord), reversed(dims)):
            idx += c * mult
            mult *= d
        return idx

    for i in range(map_limit):
        src_c = idx_to_coord(i, src_dims)
        tgt_c = idx_to_coord(i, tgt_dims)
        coordinate_map[src_c] = tgt_c
        
    return ManifoldReshapeMapping(
        intent=intent,
        coordinate_map=coordinate_map
    )


def validate_reshape_mapping(mapping: ManifoldReshapeMapping) -> bool:
    """
    Validates completeness and reversibility of the mapping if lossless.
    """
    intent = mapping.intent
    lossless = intent.lossless
    
    if lossless:
        src_total = intent.source_shape.total_elements()
        tgt_total = intent.target_shape.total_elements()
        if len(mapping.coordinate_map) != src_total:
            raise ValueError("Lossless mapping coordinate map length mismatch: incomplete coverage.")
            
        # Check reversibility (uniqueness of target coordinates)
        seen_targets = set(mapping.coordinate_map.values())
        if len(seen_targets) != tgt_total:
            raise ValueError("Lossless mapping is not reversible (duplicate target coordinates found).")
            
    return True


def build_reshape_plan(intent: ManifoldReshapeIntent, mapping: ManifoldReshapeMapping) -> ManifoldReshapePlan:
    """
    Formulates a sequence of steps to transform coordinates.
    """
    steps = []
    for src_c, tgt_c in list(mapping.coordinate_map.items())[:100]: # limit steps representation
        steps.append({
            "action": "project_coordinate",
            "source": src_c,
            "target": tgt_c
        })
    return ManifoldReshapePlan(
        plan_id=f"PLAN_RESHAPE_{id(intent)}",
        intent=intent,
        mapping=mapping,
        steps=steps
    )


def execute_shadow_manifold_reshape(plan: ManifoldReshapePlan) -> ManifoldReshapeReport:
    """
    Executes a shadow reshape run, outputting a report.
    """
    intent = plan.intent
    mapping = plan.mapping
    
    errors = []
    try:
        validate_reshape_mapping(mapping)
    except ValueError as e:
        errors.append(str(e))
        
    success = len(errors) == 0
    
    result = ManifoldReshapeResult(
        success=success,
        final_shape=intent.target_shape,
        errors=errors
    )
    
    return ManifoldReshapeReport(
        report_id=f"REP_RESHAPE_{plan.plan_id}",
        plan=plan,
        result=result,
        lossless=intent.lossless,
        source_element_count=intent.source_shape.total_elements(),
        target_element_count=intent.target_shape.total_elements(),
        validation_passed=success,
        errors=errors
    )


def compare_manifold_shape_before_after(before: ManifoldShape, after: ManifoldShape) -> Dict[str, Any]:
    """
    Returns diagnostic differences between before and after shapes.
    """
    return {
        "dimensions_before": before.dims,
        "dimensions_after": after.dims,
        "elements_before": before.total_elements(),
        "elements_after": after.total_elements(),
        "dimension_rank_shift": len(after.dims) - len(before.dims),
        "element_gain_loss": after.total_elements() - before.total_elements()
    }
