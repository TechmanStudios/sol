# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL H-CAM Banking Scaffolding
==============================
Defines structures for holographic memory recall plans, byte-lane mapping, 
and hierarchical banking topology.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class HCAMBank:
    bank_id: int
    lane_id: int
    address_basin: str
    value_basin: str
    recall_gate: str
    commit_register: str
    boundary_metadata: Dict[str, Any] = field(default_factory=dict)
    phase_table_reference: Optional[Any] = None

    @classmethod
    def for_width(cls, width: int) -> List["HCAMBank"]:
        """
        Generates byte lane HCAM bank configurations depending on the wide word bit width:
        - 16-bit -> 2 byte banks
        - 32-bit -> 4 byte banks
        - 64-bit -> 8 byte banks
        """
        if width not in (16, 32, 64):
            raise ValueError(f"Unsupported bit width for HCAM banking: {width}")
        num_banks = width // 8

        banks = []
        for i in range(num_banks):
            banks.append(cls(
                bank_id=i,
                lane_id=i,
                address_basin=f"Basin_Addr_L{i}",
                value_basin=f"Basin_Val_L{i}",
                recall_gate=f"Gate_Recall_L{i}",
                commit_register=f"Reg_Commit_L{i}",
                boundary_metadata={
                    "isolation_gap": 0.05,
                    "crosstalk_threshold": 0.05,
                    "boundary_gamma": 0.15,
                    "core_gamma": 0.002
                },
                phase_table_reference=None
            ))
        return banks

@dataclass
class HCAMAddressMap:
    width: int
    lane_count: int
    banks: List[HCAMBank]

@dataclass
class HCAMRecallPlan:
    address: int
    address_map: HCAMAddressMap
    execution_steps: List[str]
    evidence: Dict[str, Any]

@dataclass
class HierarchicalHCAMTopology:
    width: int
    banks: List[HCAMBank]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HCAMQuery:
    address: int
    width: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HCAMBankRoute:
    bank_id: int
    address_basin: str
    recall_gate: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HCAMResponseRoute:
    bank_id: int
    value_basin: str
    commit_register: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HCAMBankedRecallPlan:
    query: HCAMQuery
    topology: HierarchicalHCAMTopology
    query_routes: List[HCAMBankRoute]
    response_routes: List[HCAMResponseRoute]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HCAMReductionNode:
    node_id: str
    left_child: Optional["HCAMReductionNode"] = None
    right_child: Optional["HCAMReductionNode"] = None
    bank_id: Optional[int] = None
    operation: str = "identity"  # "identity" or "merge_bytes"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HCAMReductionTree:
    root: HCAMReductionNode
    depth: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HCAMRecallReport:
    report_id: str
    instruction_id: str
    address: int
    width: int
    passed_gates: bool
    assembled_word: int
    oracle_match: bool
    gate_report: Any  # InstructionGateReport
    recall_plan: HCAMBankedRecallPlan
    reduction_tree: HCAMReductionTree
    timestamp: float
    reproducibility_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_hcam_topology(width: int) -> HierarchicalHCAMTopology:
    """
    Builds the Hierarchical HCAM Topology configuration for the given width.
    """
    if width not in (16, 32, 64):
        raise ValueError(f"Unsupported width for H-CAM topology: {width}")
        
    banks = HCAMBank.for_width(width)
    from sol_phase_alignment import build_default_phase_table
    for bank in banks:
        bank.phase_table_reference = build_default_phase_table(bank.lane_id, [11.0, 13.0, 17.0, 19.0])
        
    return HierarchicalHCAMTopology(
        width=width,
        banks=banks,
        metadata={
            "crosstalk_threshold": 0.05,
            "isolation_gap": 0.05,
            "boundary_gamma": 0.15,
            "core_gamma": 0.002
        }
    )


def build_query_plan(address: int, width: int) -> HCAMQuery:
    """
    Constructs an HCAMQuery object targeting the given address.
    """
    return HCAMQuery(
        address=address,
        width=width,
        metadata={"created_at": time.time()}
    )


def route_query_to_banks(query: HCAMQuery, topology: HierarchicalHCAMTopology) -> List[HCAMBankRoute]:
    """
    Maps address query paths to all target banks.
    """
    routes = []
    for bank in topology.banks:
        routes.append(HCAMBankRoute(
            bank_id=bank.bank_id,
            address_basin=bank.address_basin,
            recall_gate=bank.recall_gate,
            metadata={"status": "routed"}
        ))
    return routes


def build_response_routes(query_plan: HCAMBankedRecallPlan, topology: HierarchicalHCAMTopology) -> List[HCAMResponseRoute]:
    """
    Maps response routes returning values from byte banks.
    """
    routes = []
    for bank in topology.banks:
        routes.append(HCAMResponseRoute(
            bank_id=bank.bank_id,
            value_basin=bank.value_basin,
            commit_register=bank.commit_register,
            metadata={"status": "pending_demodulation"}
        ))
    return routes


def build_reduction_tree(response_routes: List[HCAMResponseRoute], width: int) -> HCAMReductionTree:
    """
    Builds a binary reduction tree for merging bank bytes into a wide word.
    """
    if not response_routes:
        raise ValueError("No response routes provided for reduction tree.")
        
    nodes = []
    for r in response_routes:
        nodes.append(HCAMReductionNode(
            node_id=f"Leaf_Bank_{r.bank_id}",
            bank_id=r.bank_id,
            operation="identity"
        ))
        
    step = 0
    while len(nodes) > 1:
        next_level = []
        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                left = nodes[i]
                right = nodes[i + 1]
                parent = HCAMReductionNode(
                    node_id=f"Internal_Merge_{step}_{i // 2}",
                    left_child=left,
                    right_child=right,
                    operation="merge_bytes",
                    metadata={"merged_lanes": [getattr(left, "bank_id", None), getattr(right, "bank_id", None)]}
                )
                next_level.append(parent)
            else:
                next_level.append(nodes[i])
        nodes = next_level
        step += 1
        
    root = nodes[0]
    
    def get_depth(node: Optional[HCAMReductionNode]) -> int:
        if node is None:
            return 0
        if node.left_child is None and node.right_child is None:
            return 1
        return 1 + max(get_depth(node.left_child), get_depth(node.right_child))
        
    depth = get_depth(root)
    
    return HCAMReductionTree(
        root=root,
        depth=depth,
        metadata={"width": width}
    )


def assemble_word_from_bank_values(bank_values: Any, width: int) -> int:
    """
    Assembles a wide integer word from bank values in little-endian order.
    """
    word = 0
    num_banks = width // 8
    
    if isinstance(bank_values, dict):
        for bank_id in range(num_banks):
            val = bank_values.get(bank_id, 0) & 0xFF
            word |= (val << (bank_id * 8))
    else:
        for bank_id in range(min(num_banks, len(bank_values))):
            val = bank_values[bank_id] & 0xFF
            word |= (val << (bank_id * 8))
            
    mask = (1 << width) - 1
    return word & mask
