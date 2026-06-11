# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Hierarchical Waveguide Fabric
=================================
Defines hierarchical 16-bit, 32-bit, and 64-bit waveguide fabric models,
spines, clusters, inter-lane bridges, and topological validation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class WaveguideHierarchyLevel:
    level_id: int
    name: str
    scale_bits: int
    description: str

@dataclass
class WaveguideFabricCluster:
    cluster_id: int
    lane_ids: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideLaneGroup:
    group_id: int
    lane_ids: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideSpine:
    spine_id: str
    connected_cluster_ids: List[int]
    capacity_bits: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InterLaneBridge:
    bridge_id: str
    source_lane_id: int
    target_lane_id: int
    crosstalk_db: float = -40.0
    reflection_coefficient: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HierarchicalWaveguideTopology:
    width: int
    lane_width: int
    levels: List[WaveguideHierarchyLevel]
    clusters: List[WaveguideFabricCluster]
    lane_groups: List[WaveguideLaneGroup]
    spines: List[WaveguideSpine]
    bridges: List[InterLaneBridge]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HierarchicalWaveguideReport:
    report_id: str
    width: int
    lane_count: int
    cluster_count: int
    bridge_count: int
    valid: bool
    errors: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_hierarchical_waveguide_topology(width: int, lane_width: int = 8) -> HierarchicalWaveguideTopology:
    """
    Constructs the HierarchicalWaveguideTopology for the given bit width.
    - 16-bit -> 2 lanes
    - 32-bit -> 4 lanes
    - 64-bit -> 8 lanes
    Preserves spatial scaling by grouping lanes without overloading single buses.
    """
    if width not in (16, 32, 64):
        raise ValueError(f"Unsupported hierarchical fabric width: {width}")
    
    num_lanes = width // lane_width
    
    # 1. Define hierarchy levels
    levels = [
        WaveguideHierarchyLevel(0, "Bit-level", 1, "Individual bit channels"),
        WaveguideHierarchyLevel(1, "Byte-lane", lane_width, f"PDM byte-slice lanes ({lane_width}-bit)"),
    ]
    if width >= 32:
        levels.append(WaveguideHierarchyLevel(2, "Cluster", 32, "Logical 32-bit word clusters"))
    if width >= 64:
        levels.append(WaveguideHierarchyLevel(3, "System-word", 64, "Hierarchical 64-bit wide words"))

    # 2. Define lane groups (same structure as WideWordFabric)
    lane_groups = []
    if width == 64:
        lane_groups.append(WaveguideLaneGroup(group_id=0, lane_ids=[0, 1, 2, 3], metadata={"description": "Low 32-bit lanes"}))
        lane_groups.append(WaveguideLaneGroup(group_id=1, lane_ids=[4, 5, 6, 7], metadata={"description": "High 32-bit lanes"}))
    else:
        lane_groups.append(WaveguideLaneGroup(group_id=0, lane_ids=list(range(num_lanes)), metadata={"description": f"Standard {width}-bit lane group"}))

    # 3. Define clusters mapping
    clusters = []
    for g in lane_groups:
        clusters.append(WaveguideFabricCluster(
            cluster_id=g.group_id,
            lane_ids=list(g.lane_ids),
            metadata={"description": f"Cluster representing lane group {g.group_id}"}
        ))

    # 4. Define spines
    spines = [
        WaveguideSpine(
            spine_id="Spine_0",
            connected_cluster_ids=[c.cluster_id for c in clusters],
            capacity_bits=width,
            metadata={"description": "Main inter-cluster communication spine"}
        )
    ]

    # 5. Define inter-lane bridges between adjacent lanes
    bridges = []
    for i in range(num_lanes - 1):
        bridges.append(InterLaneBridge(
            bridge_id=f"Bridge_{i}_{i+1}",
            source_lane_id=i,
            target_lane_id=i + 1,
            crosstalk_db=-40.0,
            reflection_coefficient=0.01,
            metadata={"type": "neighboring_bridge"}
        ))

    return HierarchicalWaveguideTopology(
        width=width,
        lane_width=lane_width,
        levels=levels,
        clusters=clusters,
        lane_groups=lane_groups,
        spines=spines,
        bridges=bridges,
        metadata={
            "crosstalk_threshold": 0.05,
            "isolation_gap": 0.05,
            "boundary_gamma": 0.15,
            "core_gamma": 0.002
        }
    )


def validate_hierarchical_waveguide_topology(topology: HierarchicalWaveguideTopology) -> bool:
    """
    Validates that a HierarchicalWaveguideTopology is structurally sound.
    """
    if topology.width not in (16, 32, 64):
        return False
    
    expected_lanes = topology.width // topology.lane_width
    
    # Check all expected lanes are covered by clusters exactly once
    cluster_lanes = []
    for c in topology.clusters:
        cluster_lanes.extend(c.lane_ids)
    if len(cluster_lanes) != expected_lanes or set(cluster_lanes) != set(range(expected_lanes)):
        return False

    # Check lane groups cover all lanes
    group_lanes = []
    for g in topology.lane_groups:
        group_lanes.extend(g.lane_ids)
    if len(group_lanes) != expected_lanes or set(group_lanes) != set(range(expected_lanes)):
        return False

    # Check bridges connect valid adjacent lanes
    for b in topology.bridges:
        if b.source_lane_id < 0 or b.source_lane_id >= expected_lanes:
            return False
        if b.target_lane_id < 0 or b.target_lane_id >= expected_lanes:
            return False
        if abs(b.source_lane_id - b.target_lane_id) != 1:
            return False

    # Check spines
    for s in topology.spines:
        if not s.connected_cluster_ids:
            return False
        for cid in s.connected_cluster_ids:
            if cid not in [c.cluster_id for c in topology.clusters]:
                return False

    return True


def map_lanes_to_waveguide_clusters(topology: HierarchicalWaveguideTopology) -> Dict[int, int]:
    """
    Returns a mapping of lane_id -> cluster_id.
    """
    mapping = {}
    for c in topology.clusters:
        for lid in c.lane_ids:
            mapping[lid] = c.cluster_id
    return mapping


def build_interlane_bridges(topology: HierarchicalWaveguideTopology) -> List[InterLaneBridge]:
    """
    Returns the list of interlane bridges configured in the topology.
    """
    return list(topology.bridges)


def summarize_hierarchical_waveguide(topology: HierarchicalWaveguideTopology) -> HierarchicalWaveguideReport:
    """
    Performs validation and summarizes the waveguide configuration.
    """
    errors = []
    valid = True
    try:
        if not validate_hierarchical_waveguide_topology(topology):
            valid = False
            errors.append("Topology validation failed: lane, cluster, or bridge mismatch.")
    except Exception as e:
        valid = False
        errors.append(f"Validation error: {str(e)}")

    num_lanes = topology.width // topology.lane_width
    report_id = f"HWREP_{topology.width}_{int(time.time())}"
    
    return HierarchicalWaveguideReport(
        report_id=report_id,
        width=topology.width,
        lane_count=num_lanes,
        cluster_count=len(topology.clusters),
        bridge_count=len(topology.bridges),
        valid=valid,
        errors=errors,
        metadata={"timestamp": time.time()}
    )


def validate_waveguide_topology_after_core_assembly(
    topology: Any,
    assembly_report: Any
) -> bool:
    """
    Validates hierarchical waveguide topology against core assembly mapping report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(assembly_report, "result")
    success = extract(res, "success", True) if res is not None else extract(assembly_report, "success", True)
    if not success:
        raise ValueError("Core assembly failed; holding waveguide topology validation.")

    # Check validation
    valid = getattr(topology, "valid", True) if hasattr(topology, "valid") else True
    if not valid:
        raise ValueError("Hierarchical waveguide topology validation failed.")
        
    meta = extract(topology, "metadata", {}) or {}
    if meta.get("pml_coverage_violated") or meta.get("missing_pml_boundary"):
        raise ValueError("Waveguide topology fails: missing or violated PML boundary coverage.")
        
    return True

