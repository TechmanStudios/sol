# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Dimensional Topology
========================
Models boundaries, coordinate projections, and topology reports across multi-dimensional manifolds.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from sol_manifold_reshape import ManifoldShape

@dataclass
class DimensionalBoundary:
    axis_index: int
    lower_bound: int
    upper_bound: int
    boundary_nodes: List[Tuple[int, ...]] = field(default_factory=list)

@dataclass
class DimensionalTopology:
    shape: ManifoldShape
    boundaries: List[DimensionalBoundary] = field(default_factory=list)

@dataclass
class DimensionalProjection:
    projection_id: str
    source_shape: ManifoldShape
    target_shape: ManifoldShape
    mapping_dict: Dict[Tuple[int, ...], Tuple[int, ...]] = field(default_factory=dict)

@dataclass
class CoordinateRemap:
    remap_id: str
    projection: DimensionalProjection
    reversible: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TopologyReshapeReport:
    report_id: str
    before: DimensionalTopology
    after: DimensionalTopology
    reversible: bool
    elements_preserved: bool


def build_dimensional_topology(shape: ManifoldShape) -> DimensionalTopology:
    """
    Computes boundaries and node ranges for the topology representation.
    """
    boundaries = []
    for i, dim in enumerate(shape.dims):
        boundaries.append(DimensionalBoundary(
            axis_index=i,
            lower_bound=0,
            upper_bound=dim - 1
        ))
    return DimensionalTopology(shape=shape, boundaries=boundaries)


def project_coordinates(source_shape: ManifoldShape, target_shape: ManifoldShape) -> CoordinateRemap:
    """
    Deterministically maps coordinates between N-D shapes.
    Uses linear index mapping to ensure reversibility for lossless shapes.
    """
    src_total = source_shape.total_elements()
    tgt_total = target_shape.total_elements()
    reversible = (src_total == tgt_total)
    
    # Linear projection
    mapping_dict = {}
    limit = min(src_total, tgt_total)
    
    def idx_to_coord(idx: int, dims: List[int]) -> Tuple[int, ...]:
        coord = []
        rem = idx
        for d in reversed(dims):
            coord.append(rem % d)
            rem //= d
        return tuple(reversed(coord))

    for i in range(limit):
        src_c = idx_to_coord(i, source_shape.dims)
        tgt_c = idx_to_coord(i, target_shape.dims)
        mapping_dict[src_c] = tgt_c
        
    proj = DimensionalProjection(
        projection_id=f"PROJ_{id(source_shape)}",
        source_shape=source_shape,
        target_shape=target_shape,
        mapping_dict=mapping_dict
    )
    return CoordinateRemap(
        remap_id=f"REMAP_{proj.projection_id}",
        projection=proj,
        reversible=reversible
    )


def validate_coordinate_remap(remap: CoordinateRemap) -> bool:
    """
    Ensures that coordinate mapping is 1-to-1 and has no collision for lossless remap.
    """
    proj = remap.projection
    if remap.reversible:
        src_total = proj.source_shape.total_elements()
        tgt_total = proj.target_shape.total_elements()
        
        if len(proj.mapping_dict) != src_total:
            raise ValueError("Coordinate mapping is incomplete.")
            
        unique_targets = set(proj.mapping_dict.values())
        if len(unique_targets) != tgt_total:
            raise ValueError("Coordinate mapping is not reversible due to collision.")
            
    return True


def identify_dimensional_boundaries(topology: DimensionalTopology) -> List[DimensionalBoundary]:
    """
    Identifies grid coordinate nodes that sit on boundary outer bounds.
    """
    # Mocks boundary coordinate nodes
    shape = topology.shape
    boundaries = list(topology.boundaries)
    
    # Generate mock coordinates on the outer bounds
    for b in boundaries:
        # e.g., boundary coordinates where axis value is 0 or size - 1
        coord1 = [0] * len(shape.dims)
        coord1[b.axis_index] = 0
        coord2 = [0] * len(shape.dims)
        coord2[b.axis_index] = b.upper_bound
        b.boundary_nodes = [tuple(coord1), tuple(coord2)]
        
    return boundaries


def compare_dimensional_topologies(before: DimensionalTopology, after: DimensionalTopology) -> TopologyReshapeReport:
    """
    Builds a comparison report between two topologies.
    """
    src_total = before.shape.total_elements()
    tgt_total = after.shape.total_elements()
    
    reversible = (src_total == tgt_total)
    elements_preserved = (src_total == tgt_total)
    
    return TopologyReshapeReport(
        report_id=f"TOP_REP_{id(before)}_{id(after)}",
        before=before,
        after=after,
        reversible=reversible,
        elements_preserved=elements_preserved
    )


def build_multimanifold_dimensional_remap(manifolds: List[Any], target_shapes: List[ManifoldShape]) -> Dict[str, CoordinateRemap]:
    """
    Generates coordinate remaps for multiple manifolds.
    """
    remaps = {}
    for m, target in zip(manifolds, target_shapes):
        m_id = getattr(m, "manifold_id", None) or m.get("manifold_id")
        src_shape = getattr(m, "shape", None) or m.get("shape")
        if isinstance(src_shape, list):
            src_shape = ManifoldShape(dims=src_shape)
        remap = project_coordinates(src_shape, target)
        remaps[m_id] = remap
    return remaps


def validate_multimanifold_coordinate_consistency(remaps: Dict[str, CoordinateRemap]) -> bool:
    """
    Validates that each coordinate remap in the group is consistent and reversible if lossless.
    """
    for m_id, r in remaps.items():
        validate_coordinate_remap(r)
    return True

