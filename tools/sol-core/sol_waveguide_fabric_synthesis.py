# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Fabric Synthesis
==============================
Synthesizes candidate waveguide fabrics, layout structures, and segments under court supervision.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class WaveguideFabricSpec:
    width: int
    lane_groups: List[Any]
    simd_plan: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideSegment:
    segment_id: str
    source_junction_id: str
    target_junction_id: str
    length: float = 1.0

@dataclass
class WaveguideJunction:
    junction_id: str
    position: tuple  # (x, y)
    degree: int = 2

@dataclass
class WaveguideLaneBinding:
    lane_id: int
    shard_id: Optional[str]
    core_id: Optional[str]
    logic_slice_idx: int

@dataclass
class WaveguideBoundaryBinding:
    lane_id: int
    boundary_id: str
    pml_profile_ref: Optional[Any]

@dataclass
class WaveguideFabricCandidate:
    candidate_id: str
    spec: WaveguideFabricSpec
    segments: List[WaveguideSegment]
    junctions: List[WaveguideJunction]
    lane_bindings: List[WaveguideLaneBinding]
    boundary_bindings: List[WaveguideBoundaryBinding]
    phase_alignment_refs: Dict[int, Any]
    pdm_carrier_refs: Dict[int, Any]
    tensor_shard_bindings: List[Any] = field(default_factory=list)
    rollback_snapshot_refs: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideSynthesisPlan:
    plan_id: str
    candidate: WaveguideFabricCandidate
    steps: List[str]
    timestamp: float = field(default_factory=time.time)

@dataclass
class WaveguideSynthesisReport:
    report_id: str
    plan: WaveguideSynthesisPlan
    success: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def build_waveguide_fabric_spec(topology: Any, lane_fabric: Any, simd_plan: Optional[Any] = None) -> WaveguideFabricSpec:
    """
    Constructs a waveguide fabric specification.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    width = extract(topology, "width") or extract(lane_fabric, "num_lanes", 4) * 8
    lane_groups = extract(topology, "lane_groups", [])
    
    return WaveguideFabricSpec(
        width=width,
        lane_groups=lane_groups,
        simd_plan=simd_plan
    )


def synthesize_waveguide_fabric_candidate(spec: WaveguideFabricSpec, policy: Any) -> WaveguideFabricCandidate:
    """
    Synthesizes a waveguide fabric candidate based on the spec and policy limits.
    """
    # Check policy constraints
    max_junction_degree = getattr(policy, "max_junction_degree", 4)
    max_crossings = getattr(policy, "max_crossings_per_lane", 2)
    
    # Check for unbounded or invalid policy options
    if max_junction_degree <= 0 or max_junction_degree > 32:
        raise ValueError("Invalid synthesis policy: max_junction_degree is unbounded or invalid.")
    if max_crossings < 0 or max_crossings > 100:
        raise ValueError("Invalid synthesis policy: excessive or negative crossings constraint.")

    num_lanes = spec.width // 8
    
    # Synthesize junctions
    junctions = []
    segments = []
    lane_bindings = []
    boundary_bindings = []
    phase_alignment_refs = {}
    pdm_carrier_refs = {}

    for i in range(num_lanes):
        # junctions for each lane path
        j_start = WaveguideJunction(f"J_START_{i}", (0.0, float(i)), degree=2)
        j_end = WaveguideJunction(f"J_END_{i}", (10.0, float(i)), degree=2)
        junctions.extend([j_start, j_end])
        
        segments.append(WaveguideSegment(
            segment_id=f"SEG_{i}",
            source_junction_id=j_start.junction_id,
            target_junction_id=j_end.junction_id,
            length=10.0
        ))
        
        lane_bindings.append(WaveguideLaneBinding(
            lane_id=i,
            shard_id=f"shard_{i}",
            core_id=f"core_{i // 4}",
            logic_slice_idx=i
        ))
        
        boundary_bindings.append(WaveguideBoundaryBinding(
            lane_id=i,
            boundary_id=f"bnd_{i}",
            pml_profile_ref=f"PML_PROF_{i}"
        ))
        
        phase_alignment_refs[i] = f"PHASE_TABLE_{i}"
        pdm_carrier_refs[i] = [11.0, 13.0, 17.0, 19.0]

    candidate_id = f"WFCAND_{int(time.time())}"
    candidate = WaveguideFabricCandidate(
        candidate_id=candidate_id,
        spec=spec,
        segments=segments,
        junctions=junctions,
        lane_bindings=lane_bindings,
        boundary_bindings=boundary_bindings,
        phase_alignment_refs=phase_alignment_refs,
        pdm_carrier_refs=pdm_carrier_refs,
        rollback_snapshot_refs=["MOCK_SNAPSHOT_REF"]
    )
    
    # Run a validation check
    validate_waveguide_fabric_candidate(candidate)
    
    return candidate


def validate_waveguide_fabric_candidate(candidate: WaveguideFabricCandidate) -> bool:
    """
    Validates a synthesized candidate fabric. Raises ValueError on failure.
    """
    spec = candidate.spec
    expected_lanes = spec.width // 8
    
    # 1. Complete lane bindings check
    if len(candidate.lane_bindings) != expected_lanes:
        raise ValueError(f"Synthesis candidate rejects missing lane binding: expected {expected_lanes}, found {len(candidate.lane_bindings)}")
        
    lane_ids = {b.lane_id for b in candidate.lane_bindings}
    if len(lane_ids) != expected_lanes:
        raise ValueError("Missing or duplicate lane IDs in lane bindings")
        
    # 2. PML boundary validity check
    if len(candidate.boundary_bindings) != expected_lanes:
        raise ValueError("Missing boundary bindings")
    for bnd in candidate.boundary_bindings:
        if not bnd.pml_profile_ref:
            raise ValueError(f"Synthesis candidate rejects invalid PML boundary for lane {bnd.lane_id}")

    # 3. Junction degree check
    for junc in candidate.junctions:
        if junc.degree <= 0:
            raise ValueError("Junction degree must be positive")

    return True


def build_waveguide_synthesis_plan(candidate: WaveguideFabricCandidate) -> WaveguideSynthesisPlan:
    """
    Generates a synthesis plan from the candidate.
    """
    steps = [
        "Initialize waveguide synthesis layout space",
        f"Map {len(candidate.lane_bindings)} PDM byte slice lanes",
        "Configure Perfectly Matched Layer boundary profiles",
        "Set up spatial routing segments and junctions",
        "Bind phase alignment tables and carrier frequencies"
    ]
    plan_id = f"WFSYNPLAN_{candidate.candidate_id}"
    return WaveguideSynthesisPlan(plan_id=plan_id, candidate=candidate, steps=steps)


def execute_shadow_waveguide_synthesis(plan: WaveguideSynthesisPlan) -> WaveguideSynthesisReport:
    """
    Shadow-executes waveguide synthesis, returning a report.
    """
    errors = []
    success = True
    
    try:
        validate_waveguide_fabric_candidate(plan.candidate)
    except ValueError as e:
        errors.append(str(e))
        success = False
        
    report_id = f"WFSYNREP_{plan.plan_id}"
    return WaveguideSynthesisReport(
        report_id=report_id,
        plan=plan,
        success=success,
        errors=errors
    )


def export_reshape_candidate_from_fabric(candidate: WaveguideFabricCandidate) -> WaveguideFabricCandidate:
    """
    Returns a new separate copy of the candidate fabric for reshape planning.
    """
    import copy
    return copy.deepcopy(candidate)


def validate_synthesized_fabric_after_reshape(candidate: WaveguideFabricCandidate, reshape_plan: Any) -> bool:
    """
    Ensures the candidate fabric meets validation constraints after applying a reshape plan.
    """
    validate_waveguide_fabric_candidate(candidate)
    
    # Verify that target dimensions matches expected count of lane bindings
    target_shape = getattr(reshape_plan.intent, "target_shape", None)
    if target_shape:
        expected_lanes = target_shape.total_elements()
        # If lossless, expected lanes should match current lane bindings length
        if getattr(reshape_plan.intent, "lossless", True) and len(candidate.lane_bindings) != expected_lanes:
            raise ValueError(f"Reshape mapping mismatch: expected {expected_lanes} lanes, found {len(candidate.lane_bindings)}")
            
    return True


def rebind_waveguide_segments_after_reshape(candidate: WaveguideFabricCandidate, reshape_mapping: Any) -> WaveguideFabricCandidate:
    """
    Rebinds the waveguide segment mappings and lane IDs to match the reshaped coordinates.
    """
    import copy
    new_candidate = copy.deepcopy(candidate)
    
    # Process remapping of lane IDs or labels if mapping contains coordinate changes
    # For simulation purposes, we update metadata with coordinate mapping info
    new_candidate.metadata["reshape_mapping"] = getattr(reshape_mapping, "coordinate_map", {})
    return new_candidate


def synthesize_hierarchical_waveguide_from_topology(topology: Any) -> WaveguideFabricCandidate:
    """
    Synthesizes a WaveguideFabricCandidate based on the HierarchicalWaveguideTopology.
    """
    from sol_hierarchical_waveguide_fabric import map_lanes_to_waveguide_clusters
    
    spec = build_waveguide_fabric_spec(topology, None)
    num_lanes = topology.width // 8
    
    junctions = []
    segments = []
    lane_bindings = []
    boundary_bindings = []
    phase_alignment_refs = {}
    pdm_carrier_refs = {}
    
    cluster_map = map_lanes_to_waveguide_clusters(topology)
    
    for i in range(num_lanes):
        j_start = WaveguideJunction(f"J_START_{i}", (0.0, float(i)), degree=2)
        j_end = WaveguideJunction(f"J_END_{i}", (10.0, float(i)), degree=2)
        junctions.extend([j_start, j_end])
        
        segments.append(WaveguideSegment(
            segment_id=f"SEG_{i}",
            source_junction_id=j_start.junction_id,
            target_junction_id=j_end.junction_id,
            length=10.0
        ))
        
        cluster_id = cluster_map.get(i, 0)
        lane_bindings.append(WaveguideLaneBinding(
            lane_id=i,
            shard_id=f"shard_{i}",
            core_id=f"core_{cluster_id}",
            logic_slice_idx=i
        ))
        
        boundary_bindings.append(WaveguideBoundaryBinding(
            lane_id=i,
            boundary_id=f"bnd_{i}",
            pml_profile_ref=f"PML_PROF_{i}"
        ))
        
        phase_alignment_refs[i] = f"PHASE_TABLE_{i}"
        pdm_carrier_refs[i] = [11.0, 13.0, 17.0, 19.0]
        
    candidate = WaveguideFabricCandidate(
        candidate_id=f"HWFCAND_{topology.width}_{int(time.time())}",
        spec=spec,
        segments=segments,
        junctions=junctions,
        lane_bindings=lane_bindings,
        boundary_bindings=boundary_bindings,
        phase_alignment_refs=phase_alignment_refs,
        pdm_carrier_refs=pdm_carrier_refs,
        rollback_snapshot_refs=["SNAPSHOT_REF_INITIAL"],
        metadata={
            "byte_lanes": list(range(num_lanes)),
            "cluster_ids": list(set(cluster_map.values())),
            "inter_lane_bridges": [b.bridge_id for b in topology.bridges]
        }
    )
    return candidate


def bind_prefix_carry_tree_to_waveguide(candidate: WaveguideFabricCandidate, carry_tree: Any) -> WaveguideFabricCandidate:
    """
    Binds a prefix carry tree's nodes and edges to the waveguide candidate.
    """
    import copy
    new_cand = copy.deepcopy(candidate)
    new_cand.metadata["prefix_carry_tree"] = carry_tree
    new_cand.metadata["prefix_carry_nodes"] = [n.node_id for n in carry_tree.nodes]
    new_cand.metadata["prefix_carry_edges"] = [f"{e.source_node_id}->{e.target_node_id}" for e in carry_tree.edges]
    new_cand.metadata["rollback_references"] = list(candidate.rollback_snapshot_refs)
    return new_cand


def validate_prefix_carry_bindings(candidate: WaveguideFabricCandidate) -> bool:
    """
    Ensures that the prefix carry bindings, PML boundary declarations, phase alignment
    references, and rollback references are all complete and valid on the candidate.
    """
    validate_waveguide_fabric_candidate(candidate)
    
    metadata = candidate.metadata
    if "prefix_carry_tree" not in metadata:
        return False
    if "prefix_carry_nodes" not in metadata or not metadata["prefix_carry_nodes"]:
        return False
    if "prefix_carry_edges" not in metadata or not metadata["prefix_carry_edges"]:
        return False
        
    if not candidate.boundary_bindings:
        return False
    for bnd in candidate.boundary_bindings:
        if not bnd.pml_profile_ref:
            return False
            
    if not candidate.phase_alignment_refs:
        return False
        
    if not candidate.rollback_snapshot_refs:
        return False
        
    return True

