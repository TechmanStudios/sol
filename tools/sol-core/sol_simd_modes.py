# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL SIMD Modes & Execution Planning
====================================
Scaffolds SIMD execution layout structures mapping vector groups onto
reusable byte-sliced lane configurations.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SIMDMode:
    name: str
    element_size_bits: int
    lane_count: int

@dataclass
class SIMDExecutionPlan:
    width: int
    mode: SIMDMode
    groups: List[Dict[str, Any]]
    evidence: Dict[str, Any]

@dataclass
class SIMDLaneGroup:
    group_index: int
    lanes: List[int]
    bit_offset: int
    width: int

@dataclass
class SIMDInstruction:
    instruction_id: str
    op: str  # VADD, VSUB, VAND, VOR, VXOR, VNOT, VSHL, VSHR, VREDUCE_SUM, VREDUCE_OR, VREDUCE_XOR, VCOMPARE_EQ
    mode: str  # uint8x8, uint16x4, uint32x2, uint64x1
    operands: List[List[int]]
    dry_run: bool = True
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SIMDInstructionResult:
    instruction: SIMDInstruction
    results: List[int]
    lane_results: List[Any]  # List[SIMDLaneGroup] or Dicts
    passed_gates: bool
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SIMDReductionPlan:
    mode: str
    operation: str
    reduction_tree: Any  # GeodesicReductionTree
    execution_steps: List[str]
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SIMDExecutionReport:
    report_id: str
    instruction_id: str
    mode: str
    op: str
    passed_gates: bool
    oracle_match: bool
    gate_report: Any  # InstructionGateReport
    instruction_result: SIMDInstructionResult
    timestamp: float
    reproducibility_hash: str
    reduction_tree: Optional[Any] = None  # GeodesicReductionTree
    metadata: Dict[str, Any] = field(default_factory=dict)


def plan_simd_mode(width: int, mode_name: str) -> SIMDExecutionPlan:
    """
    Computes a vector execution group mapping layout for the given fabric width and mode.
    """
    valid_modes = {
        "uint8x8": (8, 8),
        "uint16x4": (16, 4),
        "uint32x2": (32, 2),
        "uint64x1": (64, 1)
    }

    if mode_name not in valid_modes:
        raise ValueError(f"Unsupported SIMD mode: {mode_name}")

    elem_size, group_count = valid_modes[mode_name]
    total_bits = elem_size * group_count

    # Build the group lane index mapping
    groups = []
    bytes_per_elem = elem_size // 8

    for g_idx in range(group_count):
        start_lane = g_idx * bytes_per_elem
        end_lane = start_lane + bytes_per_elem
        groups.append({
            "group_index": g_idx,
            "mapped_lanes": list(range(start_lane, end_lane)),
            "bit_range": (start_lane * 8, end_lane * 8)
        })

    evidence = {
        "width_configured": width,
        "mode_requested": mode_name,
        "total_bits_required": total_bits,
        "group_count": group_count,
        "bytes_per_element": bytes_per_elem
    }

    return SIMDExecutionPlan(
        width=width,
        mode=SIMDMode(name=mode_name, element_size_bits=elem_size, lane_count=group_count),
        groups=groups,
        evidence=evidence
    )


def lane_groups_for_simd(mode: str) -> List[SIMDLaneGroup]:
    """
    Constructs SIMDLaneGroup mappings onto WideWord fabric byte lanes.
    """
    valid_modes = {
        "uint8x8": (8, 8),
        "uint16x4": (16, 4),
        "uint32x2": (32, 2),
        "uint64x1": (64, 1)
    }
    if mode not in valid_modes:
        raise ValueError(f"Unsupported SIMD mode: {mode}")
        
    elem_size, group_count = valid_modes[mode]
    groups = []
    bytes_per_elem = elem_size // 8
    
    for i in range(group_count):
        start_lane = i * bytes_per_elem
        groups.append(SIMDLaneGroup(
            group_index=i,
            lanes=list(range(start_lane, start_lane + bytes_per_elem)),
            bit_offset=start_lane * 8,
            width=elem_size
        ))
    return groups


def plan_tensor_simd_mode(shape: Any, mode: str, core_group: Any) -> Dict[str, Any]:
    """
    Maps tensor shards onto SIMD lanes of each core.
    """
    from sol_tensor_flow import plan_tensor_layout
    tensor_plan = plan_tensor_layout(shape, core_group)
    
    valid_modes = {
        "uint8x8": (8, 8),
        "uint16x4": (16, 4),
        "uint32x2": (32, 2),
        "uint64x1": (64, 1)
    }
    if mode not in valid_modes:
        raise ValueError(f"Unsupported SIMD mode: {mode}")
        
    elem_size, group_count = valid_modes[mode]
    
    core_mappings = {}
    for shard in tensor_plan.shards:
        num_elements = len(shard.element_indices)
        groups_needed = (num_elements + group_count - 1) // group_count
        
        lane_mappings = []
        for g in range(groups_needed):
            el_start = g * group_count
            el_end = min(el_start + group_count, num_elements)
            mapped_indices = shard.element_indices[el_start:el_end]
            
            lane_mappings.append({
                "simd_group_index": g,
                "element_indices": mapped_indices,
                "active_lanes": list(range(len(mapped_indices)))
            })
            
        core_mappings[shard.core_id] = {
            "core_id": shard.core_id,
            "shard_id": shard.shard_id,
            "element_count": num_elements,
            "groups_needed": groups_needed,
            "lane_mappings": lane_mappings
        }
        
    return {
        "shape": [d for d in shape.dims] if hasattr(shape, "dims") else list(shape),
        "mode": mode,
        "element_size_bits": elem_size,
        "lanes_per_group": group_count,
        "core_mappings": core_mappings,
        "physical_execution": False
    }

