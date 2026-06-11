# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL WideWord Fabric
===================
Defines hierarchical 32-bit and 64-bit waveguide fabric models, topologies, and report structures.
Now incorporates H-CAM associative memory banking integration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from sol_pdm_byte_slice import PDMByteSlice
from sol_waveguide_boundary import PMLProfile, WaveguideBoundary
from sol_phase_alignment import PhaseAlignmentTable, build_default_phase_table

@dataclass
class WaveguideLane:
    lane_id: int
    bit_offset: int
    pdm_byte_slice: PDMByteSlice
    local_bus_metadata: Dict[str, Any]
    local_value_basin_mapping: Dict[str, Any]
    local_pml_profile: PMLProfile
    local_phase_alignment_table: PhaseAlignmentTable
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WaveguideLaneGroup:
    group_id: int
    lanes: List[WaveguideLane]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WideWordFabricTopology:
    width: int
    lane_groups: List[WaveguideLaneGroup]
    hcam_topology: Optional[Any] = None
    geodesic_reduction_metadata: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WideWordFabricExecutionPlan:
    topology: WideWordFabricTopology
    instruction: Any  # WideWordInstruction
    pdm_plan: Any  # PDMExecutionPlan
    t_values: List[float]
    envelope_func: Optional[Callable[[float], float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WideWordFabricReport:
    report_id: str
    instruction_id: str
    width: int
    lane_count: int
    passed_gates: bool
    oracle_match: bool
    gate_report: Any  # InstructionGateReport
    pdm_report: Any  # PDMExecutionReport
    crosstalk_levels: Dict[str, float]
    reproducibility_hash: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def lane_groups_for_width(width: int) -> List[WaveguideLaneGroup]:
    """
    Constructs the spatial lane groups containing lanes for the given bit width.
    """
    if width not in (16, 32, 64):
        raise ValueError(f"Unsupported WideWord width: {width}")
        
    num_lanes = width // 8
    boundary = WaveguideBoundary()
    
    lanes = []
    for i in range(num_lanes):
        bit_offset = i * 8
        pdm_slice = PDMByteSlice(lane_id=i, bit_offset=bit_offset)
        
        # Build local PML profile
        pml_profile = boundary.build_pml_profile(
            lane_id=i,
            grid_size=512,
            pml_cells=32,
            core_gamma=0.002,
            boundary_gamma=0.15
        )
        
        # Build local phase alignment table
        phase_table = build_default_phase_table(i, pdm_slice.periods)
        
        # Local metadata mapping
        local_bus_metadata = {
            "bus_id": f"P_Bus{i}",
            "capacity_bits": 8,
            "damping_factor": 0.002
        }
        
        local_basin_mapping = {
            f"bit_{bit_offset + j}": f"Basin_{i}_{j}"
            for j in range(8)
        }
        
        lane = WaveguideLane(
            lane_id=i,
            bit_offset=bit_offset,
            pdm_byte_slice=pdm_slice,
            local_bus_metadata=local_bus_metadata,
            local_value_basin_mapping=local_basin_mapping,
            local_pml_profile=pml_profile,
            local_phase_alignment_table=phase_table,
            metadata={
                "isolation_gap": 0.05,
                "crosstalk_threshold": 0.05,
                "boundary_gamma": 0.15,
                "core_gamma": 0.002
            }
        )
        lanes.append(lane)
        
    if width == 64:
        # Split 8 lanes into 2 groups of 4 lanes
        group0 = WaveguideLaneGroup(group_id=0, lanes=lanes[:4], metadata={"description": "Low 32-bit word lane group"})
        group1 = WaveguideLaneGroup(group_id=1, lanes=lanes[4:], metadata={"description": "High 32-bit word lane group"})
        return [group0, group1]
    else:
        group = WaveguideLaneGroup(group_id=0, lanes=lanes, metadata={"description": f"Word lane group for {width}-bit"})
        return [group]


def build_wideword_fabric(width: int) -> WideWordFabricTopology:
    """
    Builds the WideWordFabricTopology hierarchy configured for the given width, attaching H-CAM banking.
    """
    groups = lane_groups_for_width(width)
    from sol_hcam_banking import build_hcam_topology
    hcam_topo = build_hcam_topology(width)
    
    geodesic_metadata = {
        "supported_reductions": ["VREDUCE_SUM", "VREDUCE_OR", "VREDUCE_XOR"],
        "max_depth": 3,
        "pairwise_routing_delay_ms": 0.05
    }
    
    return WideWordFabricTopology(
        width=width,
        lane_groups=groups,
        hcam_topology=hcam_topo,
        geodesic_reduction_metadata=geodesic_metadata,
        metadata={
            "crosstalk_threshold": 0.05,
            "isolation_gap": 0.05,
            "boundary_gamma": 0.15,
            "core_gamma": 0.002
        }
    )


def validate_fabric_topology(topology: WideWordFabricTopology) -> bool:
    """
    Validates that the fabric topology conforms to the design specifications, including H-CAM gates.
    """
    if topology.width not in (16, 32, 64):
        return False
        
    expected_lanes = topology.width // 8
    total_lanes = 0
    
    # 1. H-CAM topology validation gates
    hcam_topo = topology.hcam_topology
    if hcam_topo is None:
        return False
        
    if getattr(hcam_topo, "width", 0) != topology.width:
        return False
        
    banks = getattr(hcam_topo, "banks", [])
    if len(banks) != expected_lanes:
        return False
        
    lane_ids = set()
    bank_lane_ids = set()
    
    for group in topology.lane_groups:
        total_lanes += len(group.lanes)
        for lane in group.lanes:
            if not isinstance(lane.pdm_byte_slice, PDMByteSlice):
                return False
            if not isinstance(lane.local_pml_profile, PMLProfile):
                return False
            if not isinstance(lane.local_phase_alignment_table, PhaseAlignmentTable):
                return False
            lane_ids.add(lane.lane_id)
            
    for bank in banks:
        bank_lane_id = getattr(bank, "lane_id", None)
        if bank_lane_id is None:
            return False
        bank_lane_ids.add(bank_lane_id)
        
        # Verify H-CAM basins and gates exist
        if not getattr(bank, "address_basin", ""):
            return False
        if not getattr(bank, "value_basin", ""):
            return False
        if not getattr(bank, "recall_gate", ""):
            return False
        if not getattr(bank, "commit_register", ""):
            return False
            
    # every lane has a bank, and every bank has a lane
    if lane_ids != bank_lane_ids:
        return False
        
    # Verify reduction tree covers all banks
    from sol_hcam_banking import build_response_routes, build_reduction_tree, HCAMBankedRecallPlan, HCAMQuery
    query = HCAMQuery(address=0x0, width=topology.width, metadata={})
    plan = HCAMBankedRecallPlan(query=query, topology=hcam_topo, query_routes=[], response_routes=[], metadata={})
    resp_routes = build_response_routes(plan, hcam_topo)
    tree = build_reduction_tree(resp_routes, topology.width)
    
    tree_bank_ids = set()
    def traverse(node):
        if node is None:
            return
        if getattr(node, "bank_id", None) is not None:
            tree_bank_ids.add(node.bank_id)
        traverse(node.left_child)
        traverse(node.right_child)
        
    traverse(tree.root)
    if tree_bank_ids != set(range(expected_lanes)):
        return False
        
    return total_lanes == expected_lanes


def geodesic_reduction_plan(mode: str, operation: str) -> Any:
    """
    Generates a SIMDReductionPlan for Level 14 Vector SIMD reduction operations.
    """
    from sol_geodesic_reduction import build_reduction_tree
    from sol_simd_modes import SIMDReductionPlan
    
    tree = build_reduction_tree(mode, operation)
    
    valid_modes = {
        "uint8x8": 8,
        "uint16x4": 16,
        "uint32x2": 32,
        "uint64x1": 64
    }
    elem_size = valid_modes[mode]
    
    steps = [
        f"Initialize leaf nodes for {mode} SIMD lanes",
        f"Perform pairwise reduction using operation {operation}",
        f"Final root node commit to output register"
    ]
    
    evidence = {
        "mode": mode,
        "operation": operation,
        "depth": tree.depth,
        "leaf_count": len(tree.nodes) - tree.depth,
        "output_width": elem_size
    }
    
    return SIMDReductionPlan(
        mode=mode,
        operation=operation,
        reduction_tree=tree,
        execution_steps=steps,
        evidence=evidence
    )


def export_waveguide_synthesis_spec(topology: Any, lane_fabric: Any, simd_plan: Optional[Any] = None) -> Any:
    """
    Exports a WaveguideFabricSpec candidate from a given topology and lane fabric.
    """
    from sol_waveguide_fabric_synthesis import build_waveguide_fabric_spec
    return build_waveguide_fabric_spec(topology, lane_fabric, simd_plan)


def validate_fabric_against_synthesized_waveguide(candidate: Any) -> bool:
    """
    Validates the logic fabric bindings against the synthesized candidate fabric.
    """
    from sol_waveguide_fabric_synthesis import validate_waveguide_fabric_candidate
    return validate_waveguide_fabric_candidate(candidate)


def build_hierarchical_waveguide_plan(width: int) -> Any:
    """
    Constructs a hierarchical waveguide plan for the given width.
    """
    from sol_hierarchical_waveguide_fabric import build_hierarchical_waveguide_topology
    from sol_wideword_instruction import WideWordInstruction
    from sol_pdm_executor import PDMExecutionPlan
    
    topology = build_hierarchical_waveguide_topology(width)
    inst = WideWordInstruction(op="ADD", width=width, operands=[0, 0])
    pdm_plan = PDMExecutionPlan(instruction=inst, lane_plans=[])
    t_values = [0.1 * i for i in range(100)]
    
    return WideWordFabricExecutionPlan(
        topology=topology,
        instruction=inst,
        pdm_plan=pdm_plan,
        t_values=t_values,
        metadata={"hierarchical_waveguide": True}
    )


def attach_interlane_prefix_carry(plan: Any) -> Any:
    """
    Attaches inter-lane prefix carry metadata to a WideWordFabricExecutionPlan.
    """
    from sol_interlane_prefix_carry import build_prefix_carry_tree
    import copy
    
    new_plan = copy.deepcopy(plan)
    width = getattr(plan.topology, "width", 32)
    carry_tree = build_prefix_carry_tree(width // 8, strategy="balanced")
    
    if not isinstance(new_plan.metadata, dict):
        new_plan.metadata = {}
    new_plan.metadata["carry_tree"] = carry_tree
    new_plan.metadata["interlane_prefix_carry"] = True
    
    return new_plan


def validate_wideword_arithmetic_fabric(plan: Any) -> bool:
    """
    Validates that the WideWordFabricExecutionPlan has valid hierarchical topology
    and interlane prefix carry tree bindings.
    """
    from sol_hierarchical_waveguide_fabric import validate_hierarchical_waveguide_topology
    from sol_interlane_prefix_carry import validate_prefix_carry_tree
    
    topo = getattr(plan, "topology", None)
    if topo is None:
        return False
        
    if not validate_hierarchical_waveguide_topology(topo):
        return False
        
    carry_tree = plan.metadata.get("carry_tree")
    if carry_tree is not None:
        if not validate_prefix_carry_tree(carry_tree):
            return False
            
    return True


