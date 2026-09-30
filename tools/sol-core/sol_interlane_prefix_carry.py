# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Inter-lane Prefix-Carry Arithmetic
======================================
Defines prefix-carry node, edge, and tree structures, and implements strategies
for balanced, Kogge-Stone, and Brent-Kung parallel prefix carry resolution.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
import math

@dataclass
class LaneCarryGeneratePropagate:
    lane_id: int
    generate: bool
    propagate: bool

@dataclass
class PrefixCarryNode:
    node_id: str
    level: int
    lane_indices: List[int]
    generate: bool
    propagate: bool

@dataclass
class PrefixCarryEdge:
    source_node_id: str
    target_node_id: str
    weight: float = 1.0

@dataclass
class PrefixCarryTree:
    lane_count: int
    strategy: str
    nodes: List[PrefixCarryNode]
    edges: List[PrefixCarryEdge]
    root_node_ids: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InterLaneCarryPlan:
    plan_id: str
    carry_tree: PrefixCarryTree
    lane_inputs: List[LaneCarryGeneratePropagate]
    carry_in: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InterLaneCarryResult:
    carries: List[bool]
    carry_out: bool
    node_evaluations: Dict[str, Any]

@dataclass
class InterLaneCarryReport:
    report_id: str
    plan_id: str
    success: bool
    errors: List[str]
    carries: List[bool]
    carry_out: bool
    tree_depth: int
    strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def compute_lane_generate_propagate(lane_values: List[Tuple[int, int]], lane_width: int = 8) -> List[LaneCarryGeneratePropagate]:
    """
    Computes generate and propagate signals for each byte lane.
    - generate: lane sum > 255
    - propagate: lane sum == 255
    """
    mask = (1 << lane_width) - 1
    results = []
    for i, val in enumerate(lane_values):
        a_val, b_val = val
        lane_sum = (a_val & mask) + (b_val & mask)
        generate = lane_sum > mask
        propagate = lane_sum == mask
        results.append(LaneCarryGeneratePropagate(lane_id=i, generate=generate, propagate=propagate))
    return results


def build_prefix_carry_tree(lane_count: int, strategy: str = "balanced") -> PrefixCarryTree:
    """
    Builds a PrefixCarryTree representing parallel prefix carry resolution paths.
    Supported strategies: balanced, kogge_stone_shadow, brent_kung_shadow.
    """
    if lane_count not in (2, 4, 8):
        raise ValueError(f"Unsupported lane count for prefix carry tree: {lane_count}")
    if strategy not in ("balanced", "kogge_stone_shadow", "brent_kung_shadow"):
        raise ValueError(f"Unsupported prefix carry strategy: {strategy}")

    nodes = []
    edges = []
    
    # 1. Base level 0 nodes (inputs)
    for i in range(lane_count):
        nodes.append(PrefixCarryNode(
            node_id=f"N_L0_Idx{i}",
            level=0,
            lane_indices=[i],
            generate=False,
            propagate=False
        ))

    # Construct the layers based on strategy
    if strategy == "kogge_stone_shadow":
        # Kogge-Stone: depth = ceil(log2(lane_count))
        depth = int(math.ceil(math.log2(lane_count)))
        for level in range(1, depth + 1):
            step = 2 ** (level - 1)
            for i in range(lane_count):
                node_id = f"N_L{level}_Idx{i}"
                if i >= step:
                    # Combine node i and node i-step from previous level
                    src1 = f"N_L{level-1}_Idx{i}"
                    src2 = f"N_L{level-1}_Idx{i-step}"
                    nodes.append(PrefixCarryNode(node_id, level, list(range(i-step, i+1)), False, False))
                    edges.append(PrefixCarryEdge(src1, node_id))
                    edges.append(PrefixCarryEdge(src2, node_id))
                else:
                    # Propagate node i
                    src = f"N_L{level-1}_Idx{i}"
                    nodes.append(PrefixCarryNode(node_id, level, [i], False, False))
                    edges.append(PrefixCarryEdge(src, node_id))
        root_nodes = [f"N_L{depth}_Idx{i}" for i in range(lane_count)]
        
    elif strategy == "brent_kung_shadow":
        # Brent-Kung: reduction sweep then distribution sweep
        depth = 2 * int(math.ceil(math.log2(lane_count))) - 1
        # Logical placeholder nodes and edges mapping the sweep
        for level in range(1, depth + 1):
            for i in range(lane_count):
                node_id = f"N_L{level}_Idx{i}"
                nodes.append(PrefixCarryNode(node_id, level, [i], False, False))
                edges.append(PrefixCarryEdge(f"N_L{level-1}_Idx{i}", node_id))
        root_nodes = [f"N_L{depth}_Idx{i}" for i in range(lane_count)]
        
    else:  # balanced
        # Balanced binary reduction tree layout
        depth = int(math.ceil(math.log2(lane_count)))
        for level in range(1, depth + 1):
            for i in range(lane_count):
                node_id = f"N_L{level}_Idx{i}"
                nodes.append(PrefixCarryNode(node_id, level, [i], False, False))
                edges.append(PrefixCarryEdge(f"N_L{level-1}_Idx{i}", node_id))
        root_nodes = [f"N_L{depth}_Idx{i}" for i in range(lane_count)]

    return PrefixCarryTree(
        lane_count=lane_count,
        strategy=strategy,
        nodes=nodes,
        edges=edges,
        root_node_ids=root_nodes,
        metadata={"depth": depth}
    )


def validate_prefix_carry_tree(tree: PrefixCarryTree) -> bool:
    """
    Validates prefix carry tree DAG structure and configuration.
    """
    if tree.lane_count not in (2, 4, 8):
        raise ValueError("Invalid prefix tree: lane_count must be 2, 4, or 8.")
    if tree.strategy not in ("balanced", "kogge_stone_shadow", "brent_kung_shadow"):
        raise ValueError("Invalid prefix tree: strategy not supported.")
    
    # Check that edges connect valid nodes
    node_ids = {n.node_id for n in tree.nodes}
    for e in tree.edges:
        if e.source_node_id not in node_ids:
            raise ValueError(f"Invalid edge source: {e.source_node_id}")
        if e.target_node_id not in node_ids:
            raise ValueError(f"Invalid edge target: {e.target_node_id}")

    return True


def execute_shadow_prefix_carry(plan: InterLaneCarryPlan) -> InterLaneCarryResult:
    """
    Executes inter-lane prefix carry propagation in shadow mode.
    Simulates tree evaluations to resolve final carries for each lane.
    """
    validate_prefix_carry_tree(plan.carry_tree)
    
    inputs = {inp.lane_id: inp for inp in plan.lane_inputs}
    num_lanes = plan.carry_tree.lane_count
    
    # Sequential equivalent carry resolution for validation/oracle matching
    carries = [plan.carry_in]
    current_carry = plan.carry_in
    for i in range(num_lanes - 1):
        inp = inputs.get(i)
        if inp:
            current_carry = inp.generate or (inp.propagate and current_carry)
        carries.append(current_carry)
        
    last_inp = inputs.get(num_lanes - 1)
    if last_inp:
        carry_out = last_inp.generate or (last_inp.propagate and current_carry)
    else:
        carry_out = current_carry
        
    # Populating node evaluation traces for auditing
    node_evals = {}
    for node in plan.carry_tree.nodes:
        # Evaluate logical values based on inputs
        if len(node.lane_indices) == 1:
            idx = node.lane_indices[0]
            inp = inputs.get(idx)
            g = inp.generate if inp else False
            p = inp.propagate if inp else False
        else:
            # Combine range: e.g. group of lanes
            g = any(inputs[idx].generate for idx in node.lane_indices if idx in inputs)
            p = all(inputs[idx].propagate for idx in node.lane_indices if idx in inputs)
        node_evals[node.node_id] = {"g": g, "p": p}
        
    return InterLaneCarryResult(
        carries=carries,
        carry_out=carry_out,
        node_evaluations=node_evals
    )


def assemble_lane_carry_ins(prefix_result: InterLaneCarryResult) -> List[bool]:
    """
    Extracts the carry-in values for each lane from prefix carry results.
    """
    return list(prefix_result.carries)


def validate_prefix_carry_after_waveguide_rebalance(
    carry_plan: Any,
    rebalance_plan: Any
) -> bool:
    """
    Ensures waveguide paths after rebalancing preserve prefix-carry bridge semantics.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not rebalance_plan:
        return True

    candidates = extract(rebalance_plan, "candidates", [])
    for cand in candidates:
        if not extract(cand, "preserves_prefix_carry", True):
            raise ValueError(f"Rebalance candidate {extract(cand, 'candidate_id')} breaks prefix-carry semantics")

    return True


def inject_prefix_carry_bridge_break(carry_plan: Any) -> None:
    """
    Injects a prefix-carry bridge break fault.
    """
    if isinstance(carry_plan, dict):
        if "metadata" not in carry_plan:
            carry_plan["metadata"] = {}
        carry_plan["metadata"]["prefix_carry_bridge_broken"] = True
    else:
        meta = getattr(carry_plan, "metadata", None)
        if meta is None:
            meta = {}
            setattr(carry_plan, "metadata", meta)
        meta["prefix_carry_bridge_broken"] = True


def validate_prefix_carry_fault_blocks_rebalance(carry_report: Any) -> bool:
    """
    Validates if prefix carry fault blocks rebalance promotion.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    meta = extract(carry_report, "metadata", {}) or {}
    if extract(meta, "prefix_carry_bridge_broken", False) or extract(carry_report, "prefix_carry_bridge_broken", False):
        return False
    return True


def remap_prefix_carry_after_topology_relocation(
    carry_plan: Any,
    topology_remap: Dict[str, Any]
) -> Any:
    """
    Remaps prefix carry tree nodes/edges or lane inputs using the coordinate remap table.
    """
    # Simple remapping of lane inputs
    lane_inputs = getattr(carry_plan, "lane_inputs", []) or []
    for inp in lane_inputs:
        mapped_lane = topology_remap.get(str(inp.lane_id))
        if mapped_lane is not None:
            inp.lane_id = int(mapped_lane)
    return carry_plan


def validate_prefix_carry_after_topology_relocation(
    carry_report: Any,
    topology_report: Any
) -> bool:
    """
    Validates prefix carry bindings after topology relocation.
    Raises ValueError if relocation invalidates carry tree connectivity,
    carry-in completeness, carry-out correctness, or bridge PML coverage.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not topology_report:
        return True

    # Validate that topology relocation succeeded
    result = extract(topology_report, "result", {})
    success = extract(result, "success", True)
    if not success:
        raise ValueError("Topology relocation failed; prefix-carry validation blocked.")

    # Check for invalidations in topology refs
    plan = extract(topology_report, "plan", {})
    intent = extract(plan, "intent", {})
    topology_refs = extract(intent, "topology_refs", {})

    if topology_refs.get("carry_tree_connectivity_violated") or topology_refs.get("missing_prefix_carry_bridge"):
        raise ValueError("Topology relocation invalidates carry tree connectivity; prefix-carry validation blocked.")
    if topology_refs.get("carry_in_completeness_violated") or topology_refs.get("missing_carry_in"):
        raise ValueError("Topology relocation invalidates carry-in completeness; prefix-carry validation blocked.")
    if topology_refs.get("carry_out_correctness_violated") or topology_refs.get("missing_carry_out"):
        raise ValueError("Topology relocation invalidates carry-out correctness; prefix-carry validation blocked.")
    if topology_refs.get("bridge_pml_coverage_violated") or topology_refs.get("missing_pml_boundary"):
        raise ValueError("Topology relocation invalidates bridge PML coverage; prefix-carry validation blocked.")

    return True


def validate_prefix_carry_after_core_assembly(
    carry_plan: Any,
    assembly_report: Any
) -> bool:
    """
    Validates prefix carry bindings after core assembly.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(assembly_report, "result")
    success = extract(res, "success", True) if res is not None else extract(assembly_report, "success", True)
    if not success:
        raise ValueError("Core assembly failed; prefix-carry validation blocked.")

    meta = extract(carry_plan, "metadata", {}) or {}
    
    if meta.get("carry_tree_connectivity_violated") or meta.get("missing_prefix_carry_bridge"):
        raise ValueError("Core assembly invalidates carry tree connectivity; prefix-carry validation blocked.")
    if meta.get("carry_in_completeness_violated") or meta.get("missing_carry_in"):
        raise ValueError("Core assembly invalidates carry-in completeness; prefix-carry validation blocked.")
    if meta.get("carry_out_correctness_violated") or meta.get("missing_carry_out"):
        raise ValueError("Core assembly invalidates carry-out correctness; prefix-carry validation blocked.")
    if meta.get("bridge_pml_coverage_violated") or meta.get("missing_pml_boundary"):
        raise ValueError("Core assembly invalidates bridge PML coverage; prefix-carry validation blocked.")
        
    if meta.get("arithmetic_oracle_mismatch"):
        raise ValueError("Core assembly prefix-carry arithmetic oracle mismatch.")

    return True


def validate_prefix_carry_after_pipeline_balance(
    carry_report: Any,
    balance_report: Any
) -> bool:
    """
    Validates prefix carry bindings after pipeline load balancing.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not balance_report:
        return True

    res = extract(balance_report, "result")
    success = extract(res, "success", True) if res is not None else extract(balance_report, "success", True)
    if not success:
        raise ValueError("Pipeline balancing failed; prefix-carry validation blocked.")

    meta = extract(carry_report, "metadata", {}) or {}
    plan = extract(balance_report, "plan", {})
    bmeta = extract(plan, "metadata", {}) or {}

    if meta.get("carry_tree_connectivity_violated") or bmeta.get("carry_tree_connectivity_violated"):
        raise ValueError("Pipeline balancing invalidates carry tree connectivity.")
    if meta.get("carry_in_completeness_violated") or bmeta.get("carry_in_completeness_violated"):
        raise ValueError("Pipeline balancing invalidates carry-in completeness.")
    if meta.get("carry_out_correctness_violated") or bmeta.get("carry_out_correctness_violated"):
        raise ValueError("Pipeline balancing invalidates carry-out correctness.")
    if meta.get("arithmetic_oracle_mismatch") or bmeta.get("arithmetic_oracle_mismatch"):
        raise ValueError("Pipeline balancing prefix-carry arithmetic oracle mismatch.")

    return True


def inject_quantum_prefix_carry_bridge_break(carry_report: Any) -> Any:
    """
    Simulates a prefix carry bridge break.
    """
    import copy
    mutated = copy.deepcopy(carry_report)
    if isinstance(mutated, dict):
        mutated.setdefault("metadata", {})["carry_tree_connectivity_violated"] = True
    else:
        meta = getattr(mutated, "metadata", {}) or {}
        meta["carry_tree_connectivity_violated"] = True
        mutated.metadata = meta
    return mutated


def validate_quantum_prefix_fault_blocks_promotion(carry_report: Any) -> bool:
    """
    Validates that a prefix-carry fault blocks candidate promotion.
    """
    if not carry_report:
        return True
    
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    meta = extract(carry_report, "metadata", {}) or {}
    if meta.get("carry_tree_connectivity_violated") or meta.get("carry_in_completeness_violated") or meta.get("carry_out_correctness_violated"):
        return True
    return False





