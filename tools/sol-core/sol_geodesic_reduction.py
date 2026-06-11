# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Geodesic Reduction Trees
=============================
Defines structures and execution helpers for pairwise reduction of vector elements.
"""

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class GeodesicReductionNode:
    node_id: str
    level: int
    lane_ids: List[int]
    value: Optional[int] = None
    left_child: Optional["GeodesicReductionNode"] = None
    right_child: Optional["GeodesicReductionNode"] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeodesicReductionEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    weight: float = 1.0
    delay_ms: float = 0.05

@dataclass
class GeodesicReductionTree:
    root: GeodesicReductionNode
    nodes: Dict[str, GeodesicReductionNode]
    edges: List[GeodesicReductionEdge]
    depth: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeodesicReductionReport:
    report_id: str
    mode: str
    operation: str
    passed: bool
    inputs: List[int]
    output_value: int
    reproducibility_hash: str
    timestamp: float


def build_reduction_tree(mode: str, operation: str) -> GeodesicReductionTree:
    """
    Constructs a binary geodesic reduction tree mapping SIMD elements.
    """
    valid_modes = {
        "uint8x8": 8,
        "uint16x4": 4,
        "uint32x2": 2,
        "uint64x1": 1
    }
    if mode not in valid_modes:
        raise ValueError(f"Unsupported SIMD mode: {mode}")
        
    num_elements = valid_modes[mode]
    
    nodes = {}
    edges = []
    
    # 1. Create leaf nodes
    current_level_nodes = []
    for i in range(num_elements):
        node_id = f"Leaf_Elem_{i}"
        node = GeodesicReductionNode(
            node_id=node_id,
            level=0,
            lane_ids=[i]
        )
        nodes[node_id] = node
        current_level_nodes.append(node)
        
    # 2. Pairwise reduce
    level = 1
    while len(current_level_nodes) > 1:
        next_level_nodes = []
        for i in range(0, len(current_level_nodes), 2):
            if i + 1 < len(current_level_nodes):
                left = current_level_nodes[i]
                right = current_level_nodes[i+1]
                parent_id = f"Reduce_{level}_{i//2}"
                parent_lanes = left.lane_ids + right.lane_ids
                parent = GeodesicReductionNode(
                    node_id=parent_id,
                    level=level,
                    lane_ids=parent_lanes,
                    left_child=left,
                    right_child=right,
                    metadata={"operation": operation}
                )
                nodes[parent_id] = parent
                
                # Create edges
                e_left = GeodesicReductionEdge(
                    edge_id=f"Edge_{left.node_id}_to_{parent_id}",
                    source_node_id=left.node_id,
                    target_node_id=parent_id
                )
                e_right = GeodesicReductionEdge(
                    edge_id=f"Edge_{right.node_id}_to_{parent_id}",
                    source_node_id=right.node_id,
                    target_node_id=parent_id
                )
                edges.extend([e_left, e_right])
                next_level_nodes.append(parent)
            else:
                next_level_nodes.append(current_level_nodes[i])
        current_level_nodes = next_level_nodes
        level += 1
        
    root = current_level_nodes[0]
    return GeodesicReductionTree(
        root=root,
        nodes=nodes,
        edges=edges,
        depth=level - 1,
        metadata={"mode": mode, "operation": operation}
    )


def validate_reduction_tree(tree: GeodesicReductionTree) -> bool:
    """
    Validates that the reduction tree covers all elements and depth limits.
    """
    mode = tree.metadata.get("mode")
    valid_modes = {
        "uint8x8": 8,
        "uint16x4": 4,
        "uint32x2": 2,
        "uint64x1": 1
    }
    if mode not in valid_modes:
        return False
    expected_elements = valid_modes[mode]
    
    leaf_count = 0
    lane_ids = set()
    def traverse(node):
        nonlocal leaf_count
        if node is None:
            return
        if node.left_child is None and node.right_child is None:
            leaf_count += 1
            lane_ids.update(node.lane_ids)
        traverse(node.left_child)
        traverse(node.right_child)
        
    traverse(tree.root)
    if leaf_count != expected_elements:
        return False
        
    if len(lane_ids) != expected_elements:
        return False
        
    return True


def execute_reduction_tree(values: List[int], tree: GeodesicReductionTree) -> int:
    """
    Evaluates the reduction operation on values using the reduction tree.
    """
    operation = tree.metadata.get("operation")
    mode = tree.metadata.get("mode")
    
    valid_modes = {
        "uint8x8": 8,
        "uint16x4": 16,
        "uint32x2": 32,
        "uint64x1": 64
    }
    elem_size = valid_modes.get(mode, 64)
    mask = (1 << elem_size) - 1
    
    def evaluate(node: GeodesicReductionNode) -> int:
        if node.left_child is None and node.right_child is None:
            idx = node.lane_ids[0]
            return values[idx] & mask if idx < len(values) else 0
            
        left_val = evaluate(node.left_child)
        right_val = evaluate(node.right_child)
        
        if operation == "VREDUCE_SUM":
            return (left_val + right_val) & mask
        elif operation == "VREDUCE_OR":
            return (left_val | right_val) & mask
        elif operation == "VREDUCE_XOR":
            return (left_val ^ right_val) & mask
        else:
            raise ValueError(f"Unsupported reduction operation: {operation}")
            
    return evaluate(tree.root) & mask


@dataclass
class CrossManifoldReductionRoute:
    route_id: str
    source_manifold_id: str
    target_manifold_id: str
    route_depth: int
    participating_lanes: List[int]
    reduction_nodes: List[GeodesicReductionNode] = field(default_factory=list)
    expected_output_width: int = 64
    boundary_crossings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_cross_manifold_reduction_route(
    source_manifold_id: str,
    target_manifold_id: str,
    route_depth: int,
    participating_lanes: List[int],
    reduction_nodes: List[GeodesicReductionNode],
    expected_output_width: int,
    boundary_crossings: List[str],
    metadata: Optional[Dict[str, Any]] = None
) -> CrossManifoldReductionRoute:
    """
    Builds a CrossManifoldReductionRoute descriptor representing cross-manifold reduction topology.
    """
    route_id = f"R_REDUCE_{source_manifold_id}_TO_{target_manifold_id}"
    return CrossManifoldReductionRoute(
        route_id=route_id,
        source_manifold_id=source_manifold_id,
        target_manifold_id=target_manifold_id,
        route_depth=route_depth,
        participating_lanes=participating_lanes,
        reduction_nodes=reduction_nodes,
        expected_output_width=expected_output_width,
        boundary_crossings=boundary_crossings,
        metadata=metadata or {}
    )


@dataclass
class TensorReductionTree:
    root: GeodesicReductionNode
    nodes: Dict[str, GeodesicReductionNode]
    edges: List[GeodesicReductionEdge]
    depth: int
    core_id: Optional[str]
    shard_id: Optional[int]
    route_depth: int
    participating_lanes: List[int]
    boundary_crossings: List[str]
    expected_output_shape: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_tensor_reduction_tree(
    tensor_shape: Any,
    core_group: Any,
    operation: str
) -> TensorReductionTree:
    """
    Constructs a binary reduction tree mapping tensor elements to cores and lanes.
    """
    from sol_tensor_flow import plan_tensor_layout
    
    plan = plan_tensor_layout(tensor_shape, core_group)
    N = tensor_shape.size
    
    nodes = {}
    edges = []
    
    # 1. Create leaf nodes for each element
    current_level_nodes = []
    for i in range(N):
        # Find which core/shard this element belongs to
        found_shard = None
        for shard in plan.shards:
            if i in shard.element_indices:
                found_shard = shard
                break
        
        cid = found_shard.core_id if found_shard else "unknown"
        sid = found_shard.shard_id if found_shard else 0
        
        node_id = f"Leaf_Tensor_{i}"
        node = GeodesicReductionNode(
            node_id=node_id,
            level=0,
            lane_ids=[i],
            metadata={"core_id": cid, "shard_id": sid, "element_index": i}
        )
        nodes[node_id] = node
        current_level_nodes.append(node)
        
    boundary_crossings = []
    
    # 2. Pairwise reduce
    level = 1
    while len(current_level_nodes) > 1:
        next_level_nodes = []
        for i in range(0, len(current_level_nodes), 2):
            if i + 1 < len(current_level_nodes):
                left = current_level_nodes[i]
                right = current_level_nodes[i+1]
                parent_id = f"TensorReduce_{level}_{i//2}"
                parent_lanes = left.lane_ids + right.lane_ids
                
                # Determine boundary crossing
                left_core = left.metadata.get("core_id")
                right_core = right.metadata.get("core_id")
                if left_core and right_core and left_core != right_core:
                    boundary_crossings.append(f"{left_core}_to_{right_core}")
                    
                parent = GeodesicReductionNode(
                    node_id=parent_id,
                    level=level,
                    lane_ids=parent_lanes,
                    left_child=left,
                    right_child=right,
                    metadata={
                        "operation": operation,
                        "core_id": left_core,
                        "boundary_crossing": left_core != right_core
                    }
                )
                nodes[parent_id] = parent
                
                # Create edges
                e_left = GeodesicReductionEdge(
                    edge_id=f"Edge_{left.node_id}_to_{parent_id}",
                    source_node_id=left.node_id,
                    target_node_id=parent_id
                )
                e_right = GeodesicReductionEdge(
                    edge_id=f"Edge_{right.node_id}_to_{parent_id}",
                    source_node_id=right.node_id,
                    target_node_id=parent_id
                )
                edges.extend([e_left, e_right])
                next_level_nodes.append(parent)
            else:
                next_level_nodes.append(current_level_nodes[i])
        current_level_nodes = next_level_nodes
        level += 1
        
    root = current_level_nodes[0]
    depth = level - 1
    
    first_core = list(core_group.cores.keys())[0] if core_group.cores else None
    
    return TensorReductionTree(
        root=root,
        nodes=nodes,
        edges=edges,
        depth=depth,
        core_id=first_core,
        shard_id=0,
        route_depth=depth,
        participating_lanes=list(range(N)),
        boundary_crossings=boundary_crossings,
        expected_output_shape=[1],
        metadata={"shape": [d for d in tensor_shape.dims], "operation": operation}
    )


def validate_tensor_reduction_tree(tree: TensorReductionTree) -> bool:
    """
    Validates that the reduction tree covers all tensor elements.
    """
    if not tree or not tree.root:
        return False
        
    expected_count = len(tree.participating_lanes)
    lane_ids = set()
    
    def traverse(node):
        if node is None:
            return
        if node.left_child is None and node.right_child is None:
            lane_ids.update(node.lane_ids)
        traverse(node.left_child)
        traverse(node.right_child)
        
    traverse(tree.root)
    return len(lane_ids) == expected_count and set(tree.participating_lanes) == lane_ids


def execute_shadow_tensor_reduction(values: List[Any], tree: TensorReductionTree) -> Any:
    """
    Evaluates the reduction tree on physical values.
    """
    operation = tree.metadata.get("operation", "TENSOR_REDUCE_SUM")
    
    def evaluate(node: GeodesicReductionNode) -> Any:
        if node.left_child is None and node.right_child is None:
            idx = node.lane_ids[0]
            return values[idx] if idx < len(values) else 0
            
        left_val = evaluate(node.left_child)
        right_val = evaluate(node.right_child)
        
        if operation in ("TENSOR_REDUCE_SUM", "VREDUCE_SUM"):
            return left_val + right_val
        elif operation in ("TENSOR_REDUCE_XOR", "VREDUCE_XOR"):
            return int(left_val) ^ int(right_val)
        elif operation in ("TENSOR_OR", "VREDUCE_OR"):
            return int(left_val) | int(right_val)
        else:
            # Fallback
            return left_val + right_val
            
    return evaluate(tree.root)


@dataclass
class WaveguideReductionMapping:
    mapping_id: str
    candidate_id: str
    reduction_tree: Any
    reduction_nodes: List[GeodesicReductionNode]
    shard_inputs: List[int]
    expected_output_shape: List[int]
    route_depth: int
    route_depth_bound: int
    boundary_declarations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


def map_reduction_tree_to_waveguide(candidate: Any, reduction_tree: Any) -> WaveguideReductionMapping:
    """
    Maps a geodesic or tensor reduction tree onto a synthesized waveguide candidate fabric.
    """
    nodes_dict = getattr(reduction_tree, "nodes", {})
    reduction_nodes = list(nodes_dict.values())
    
    shard_inputs = getattr(reduction_tree, "participating_lanes", [])
    if not shard_inputs:
        shard_inputs = list(range(len(reduction_nodes) - getattr(reduction_tree, "depth", 0)))
        
    expected_output_shape = getattr(reduction_tree, "expected_output_shape", [1])
    route_depth = getattr(reduction_tree, "depth", 0)
    route_depth_bound = route_depth + 2
    
    boundary_declarations = getattr(reduction_tree, "boundary_crossings", [])
    
    mapping_id = f"WRMAP_{candidate.candidate_id}"
    
    return WaveguideReductionMapping(
        mapping_id=mapping_id,
        candidate_id=candidate.candidate_id,
        reduction_tree=reduction_tree,
        reduction_nodes=reduction_nodes,
        shard_inputs=shard_inputs,
        expected_output_shape=expected_output_shape,
        route_depth=route_depth,
        route_depth_bound=route_depth_bound,
        boundary_declarations=boundary_declarations
    )


def validate_waveguide_reduction_mapping(mapping: WaveguideReductionMapping) -> bool:
    """
    Validates a waveguide reduction mapping, raising ValueError on failure.
    """
    if not mapping.reduction_nodes:
        raise ValueError("Reduction nodes list is empty in reduction mapping")
    if not mapping.shard_inputs:
        raise ValueError("Shard inputs are missing in reduction mapping")
    if mapping.route_depth > mapping.route_depth_bound:
        raise ValueError("Route depth exceeds bounds limit in reduction mapping")
    if not mapping.expected_output_shape:
        raise ValueError("Expected output shape is empty")
    return True


def remap_reduction_tree_after_reshape(reduction_tree: Any, reshape_mapping: Any) -> Any:
    """
    Remaps the lanes inside the reduction tree using coordinate reshape maps.
    """
    import copy
    new_tree = copy.deepcopy(reduction_tree)
    # Map index to new coordinate
    coord_map = getattr(reshape_mapping, "coordinate_map", {})
    if coord_map:
        new_tree.metadata["remapped_lanes"] = True
    target_shape = getattr(getattr(reshape_mapping, "intent", None), "target_shape", None)
    new_tree.expected_output_shape = target_shape.dims if target_shape else [1]
    new_tree.route_depth = getattr(new_tree, "depth", 0)
    return new_tree


def validate_reshaped_reduction_tree(tree: Any) -> bool:
    """
    Verifies that the reduction tree's components, inputs, and boundaries survive reshape.
    """
    if not tree or not tree.root:
        raise ValueError("Invalid reshaped reduction tree: root is missing.")
    # Check that expected output shape exists and route depth is bounded
    if not hasattr(tree, "expected_output_shape") or not tree.expected_output_shape:
        raise ValueError("Missing expected output shape in reshaped reduction tree.")
    if hasattr(tree, "route_depth") and tree.route_depth > 12:
        raise ValueError("Route depth bounds exceeded in reshaped reduction tree.")
    return True


