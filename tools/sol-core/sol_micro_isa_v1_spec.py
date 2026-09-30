# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA v1 Extension Specification Layer
==============================================
Defines the formal v1 candidate opcode records, maturity levels,
operand schemas, semantics, and compliance constraints.

Note: Channelized kernels are optimization-recognition artifacts, not new opcodes.
"""

from typing import Any, Dict, List, Optional

# Maturity levels
PROPOSED = "PROPOSED"
SCHEMA_VALIDATED = "SCHEMA_VALIDATED"
LOWERING_VALIDATED = "LOWERING_VALIDATED"
TRACE_VALIDATED = "TRACE_VALIDATED"
BENCHMARK_VALIDATED = "BENCHMARK_VALIDATED"
EXTENSION_COMPLIANT = "EXTENSION_COMPLIANT"
UNSUPPORTED = "UNSUPPORTED"
REJECTED = "REJECTED"

V1_CANDIDATE_SPEC_RECORDS = {
    "SELECT": {
        "opcode": "SELECT",
        "category": "conditional_select",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "cond", "src_true", "src_false"],
        "semantics": "Commit src_true to dst if cond evaluates truthy, otherwise commit src_false.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "branchless_select_via_predication",
        "requires": ["branch_predication", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "valid_condition"],
        "benchmark_cases": ["v1_select_true", "v1_select_false"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "CMOVZ": {
        "opcode": "CMOVZ",
        "category": "conditional_select",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src"],
        "semantics": "Move src to dst if Zero flag is set, otherwise preserve dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "conditional_select_via_skip_branch",
        "requires": ["branch_predication", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "valid_condition"],
        "benchmark_cases": ["v1_cmovz_taken", "v1_cmovz_not_taken"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "CMOVNZ": {
        "opcode": "CMOVNZ",
        "category": "conditional_select",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src"],
        "semantics": "Move src to dst if Zero flag is clear, otherwise preserve dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "conditional_select_via_skip_branch",
        "requires": ["branch_predication", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "valid_condition"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "CMOVC": {
        "opcode": "CMOVC",
        "category": "conditional_select",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src"],
        "semantics": "Move src to dst if Carry flag is set, otherwise preserve dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "conditional_select_via_skip_branch",
        "requires": ["branch_predication", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "valid_condition"],
        "benchmark_cases": ["v1_cmovc_taken"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "CMOVNC": {
        "opcode": "CMOVNC",
        "category": "conditional_select",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src"],
        "semantics": "Move src to dst if Carry flag is clear, otherwise preserve dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "conditional_select_via_skip_branch",
        "requires": ["branch_predication", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "valid_condition"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "CMOVB": {
        "opcode": "CMOVB",
        "category": "conditional_select",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src"],
        "semantics": "Move src to dst if Borrow flag is set, otherwise preserve dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "conditional_select_via_skip_branch",
        "requires": ["branch_predication", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "valid_condition"],
        "benchmark_cases": ["v1_cmovb_taken"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "CMOVNB": {
        "opcode": "CMOVNB",
        "category": "conditional_select",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src"],
        "semantics": "Move src to dst if Borrow flag is clear, otherwise preserve dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "conditional_select_via_skip_branch",
        "requires": ["branch_predication", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "valid_condition"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "PLOAD_RO": {
        "opcode": "PLOAD_RO",
        "category": "memory",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "predicate", "addr_true", "addr_false"],
        "semantics": "Read-only predicated load. Loads from addr_true if predicate is true, else from addr_false.",
        "flags_behavior": "preserve",
        "memory_behavior": "read",
        "lowering_strategy": "conditional_load_via_predication",
        "requires": ["branch_predication", "memory_shard", "trace_mapping"],
        "safety_constraints": ["no_memory_write", "static_addresses_only"],
        "benchmark_cases": ["v1_pload_ro_static", "v1_pload_ro_dynamic_rejected"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "LANE_ADD": {
        "opcode": "LANE_ADD",
        "category": "alu",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src1", "src2"],
        "semantics": "Per-lane addition operation.",
        "flags_behavior": "update_arithmetic",
        "memory_behavior": "none",
        "lowering_strategy": "direct_v0_alu_mapping",
        "requires": [],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "LANE_SUB": {
        "opcode": "LANE_SUB",
        "category": "alu",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src1", "src2"],
        "semantics": "Per-lane subtraction operation.",
        "flags_behavior": "update_arithmetic",
        "memory_behavior": "none",
        "lowering_strategy": "direct_v0_alu_mapping",
        "requires": [],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "PREFIX_ADD": {
        "opcode": "PREFIX_ADD",
        "category": "alu",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src1", "src2"],
        "semantics": "Prefix carry-aware wide-word addition operation.",
        "flags_behavior": "update_arithmetic",
        "memory_behavior": "none",
        "lowering_strategy": "direct_v0_alu_mapping",
        "requires": ["prefix_carry_routing"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_prefix_add"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "PREFIX_SUB": {
        "opcode": "PREFIX_SUB",
        "category": "alu",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src1", "src2"],
        "semantics": "Prefix borrow-aware wide-word subtraction operation.",
        "flags_behavior": "update_arithmetic",
        "memory_behavior": "none",
        "lowering_strategy": "direct_v0_alu_mapping",
        "requires": ["prefix_carry_routing"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_prefix_sub"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_PACK": {
        "opcode": "VEC_PACK",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "lane0", "lane1", "lane2", "lane3"],
        "semantics": "Pack scalar lane values into a wide-word register.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "vec_pack_via_shifts_and_ors",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_pack_u32"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_UNPACK": {
        "opcode": "VEC_UNPACK",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["src", "dst0", "dst1", "dst2", "dst3"],
        "semantics": "Unpack byte/word lanes from a wide-word register into scalar registers.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "vec_unpack_via_shifts_and_masks",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_unpack_u32"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_BROADCAST": {
        "opcode": "VEC_BROADCAST",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src"],
        "semantics": "Broadcast scalar src into all lanes of dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "vec_broadcast_via_duplication_shifts",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_broadcast_u32"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_EXTRACT": {
        "opcode": "VEC_EXTRACT",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src", "lane_index"],
        "semantics": "Extract lane_index from src into dst.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "vec_extract_via_shift_and_mask",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_extract_lane0", "v1_vec_extract_lane3"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_INSERT": {
        "opcode": "VEC_INSERT",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src_vec", "lane_index", "src_scalar"],
        "semantics": "Copy src_vec to dst, replacing one lane with src_scalar.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "vec_insert_via_clear_mask_and_or",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_insert_lane2"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_LANE_ADD": {
        "opcode": "VEC_LANE_ADD",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src_a", "src_b", "mask"],
        "semantics": "Add lanes independently under mask.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "lane_add_via_lane_extraction",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_lane_add_mask_all", "v1_vec_lane_add_mask_partial"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_LANE_SUB": {
        "opcode": "VEC_LANE_SUB",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src_a", "src_b", "mask"],
        "semantics": "Subtract lanes independently under mask.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "lane_sub_via_lane_extraction",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_lane_sub_mask_all"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_LANE_AND": {
        "opcode": "VEC_LANE_AND",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src_a", "src_b", "mask"],
        "semantics": "AND lanes independently under mask.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "lane_and_via_lane_extraction",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_LANE_OR": {
        "opcode": "VEC_LANE_OR",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src_a", "src_b", "mask"],
        "semantics": "OR lanes independently under mask.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "lane_or_via_lane_extraction",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_LANE_XOR": {
        "opcode": "VEC_LANE_XOR",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "src_a", "src_b", "mask"],
        "semantics": "XOR lanes independently under mask.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "lane_xor_via_lane_extraction",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": [],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "VEC_MASK_SELECT": {
        "opcode": "VEC_MASK_SELECT",
        "category": "vector_lane",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": ["dst", "mask", "src_true", "src_false"],
        "semantics": "Per-lane conditional select.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "vec_mask_select_via_lane_selection",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_vec_mask_select"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "WG_CHAN_FENCE": {
        "opcode": "WG_CHAN_FENCE",
        "category": "ordering_barrier",
        "status": EXTENSION_COMPLIANT,
        "enabled_by_default": False,
        "operand_schema": [],
        "semantics": "Candidate ordering barrier for channel operations. Acts as a global ordering barrier preventing wavefront batching across the fence.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": "waveguide_channel_fence_barrier",
        "requires": ["trace_mapping"],
        "safety_constraints": ["no_memory_write"],
        "benchmark_cases": ["v1_wg_chan_fence_barrier"],
        "trace_metadata": ["micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"]
    },
    "WG_CHAN_SEND": {
        "opcode": "WG_CHAN_SEND",
        "category": "waveguide_channel",
        "status": UNSUPPORTED,
        "enabled_by_default": False,
        "operand_schema": ["channel", "src"],
        "semantics": "Candidate channel send operation. Writes specified channel. Evaluated for static independence and batched when conflict-free.",
        "flags_behavior": "preserve",
        "memory_behavior": "write",
        "lowering_strategy": None,
        "requires": [],
        "safety_constraints": ["memory_write_rejected", "unsupported_channel_write"],
        "benchmark_cases": [],
        "trace_metadata": []
    },
    "WG_CHAN_RECV": {
        "opcode": "WG_CHAN_RECV",
        "category": "waveguide_channel",
        "status": UNSUPPORTED,
        "enabled_by_default": False,
        "operand_schema": ["dst", "channel"],
        "semantics": "Candidate channel receive operation. Reads specified channel. Evaluated for static independence and register safety.",
        "flags_behavior": "preserve",
        "memory_behavior": "read",
        "lowering_strategy": None,
        "requires": [],
        "safety_constraints": ["no_memory_write", "unsupported_channel_read"],
        "benchmark_cases": [],
        "trace_metadata": []
    },
    "WG_CHAN_ROUTE": {
        "opcode": "WG_CHAN_ROUTE",
        "category": "waveguide_channel",
        "status": UNSUPPORTED,
        "enabled_by_default": False,
        "operand_schema": ["dst_channel", "src_channel", "route_mask"],
        "semantics": "Candidate channel routing metadata operation. Reads source channel and writes destination channel.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": None,
        "requires": [],
        "safety_constraints": ["no_memory_write", "unsupported_channel_route"],
        "benchmark_cases": [],
        "trace_metadata": []
    },
    # Placeholders marked as unsupported or proposed
    "PSTORE_WO": {
        "opcode": "PSTORE_WO",
        "category": "memory",
        "status": UNSUPPORTED,
        "enabled_by_default": False,
        "operand_schema": ["predicate", "addr", "src"],
        "semantics": "Write-only predicated store. Writes src to addr if predicate is true.",
        "flags_behavior": "preserve",
        "memory_behavior": "write",
        "lowering_strategy": None,
        "requires": [],
        "safety_constraints": ["memory_write_rejected"],
        "benchmark_cases": [],
        "trace_metadata": []
    },
    "DUMMY_V1_OP": {
        "opcode": "DUMMY_V1_OP",
        "category": "control",
        "status": PROPOSED,
        "enabled_by_default": False,
        "operand_schema": ["dst"],
        "semantics": "Proposed placeholder op for testing matrix validation.",
        "flags_behavior": "preserve",
        "memory_behavior": "none",
        "lowering_strategy": None,
        "requires": [],
        "safety_constraints": [],
        "benchmark_cases": [],
        "trace_metadata": []
    }
}

_waveguide_channel_state_enabled = False

def set_waveguide_channel_state_enabled(enabled: bool) -> None:
    global _waveguide_channel_state_enabled
    _waveguide_channel_state_enabled = enabled
    for op in ("WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE"):
        if enabled:
            V1_CANDIDATE_SPEC_RECORDS[op]["status"] = TRACE_VALIDATED
            V1_CANDIDATE_SPEC_RECORDS[op]["lowering_strategy"] = f"waveguide_channel_{op.lower().split('_')[-1]}_barrier"
            V1_CANDIDATE_SPEC_RECORDS[op]["trace_metadata"] = [
                "micro_isa_v1_candidate", "candidate_opcode", "v0_pc_range"
            ]
        else:
            V1_CANDIDATE_SPEC_RECORDS[op]["status"] = UNSUPPORTED
            V1_CANDIDATE_SPEC_RECORDS[op]["lowering_strategy"] = None
            V1_CANDIDATE_SPEC_RECORDS[op]["trace_metadata"] = []

def build_micro_isa_v1_opcode_spec() -> Dict[str, Dict[str, Any]]:
    """
    Returns the dictionary of formal v1 candidate opcode spec records.
    """
    return V1_CANDIDATE_SPEC_RECORDS

def build_micro_isa_v1_spec_table() -> List[Dict[str, Any]]:
    """
    Returns the v1 candidate opcode specification as a table list.
    """
    return list(V1_CANDIDATE_SPEC_RECORDS.values())

def get_micro_isa_v1_opcode_record(opcode: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the specification record for a given candidate opcode.
    """
    return V1_CANDIDATE_SPEC_RECORDS.get(opcode.upper())

def validate_micro_isa_v1_spec_consistency() -> bool:
    """
    Validates that the v1 specification has internal consistency.
    Raises ValueError if any constraints are violated.
    """
    required_keys = {
        "opcode", "category", "status", "enabled_by_default", "operand_schema",
        "semantics", "flags_behavior", "memory_behavior", "lowering_strategy",
        "requires", "safety_constraints", "benchmark_cases", "trace_metadata"
    }
    
    for op, record in V1_CANDIDATE_SPEC_RECORDS.items():
        missing = required_keys - set(record.keys())
        if missing:
            raise ValueError(f"Candidate {op} record is missing required keys: {missing}")
            
        if record["enabled_by_default"] is not False:
            raise ValueError(f"Candidate {op} must not be enabled by default.")
            
        status = record["status"]
        if status not in (PROPOSED, SCHEMA_VALIDATED, LOWERING_VALIDATED, TRACE_VALIDATED, BENCHMARK_VALIDATED, EXTENSION_COMPLIANT, UNSUPPORTED, REJECTED):
            raise ValueError(f"Candidate {op} has invalid status maturity level: {status}")
            
        # Supported candidates must have lowering, requirements, and metadata
        if status == EXTENSION_COMPLIANT:
            if not record["lowering_strategy"]:
                raise ValueError(f"Extension compliant candidate {op} must define a lowering strategy.")
            if not isinstance(record["requires"], list):
                raise ValueError(f"Extension compliant candidate {op} must specify required features list.")
            if not record["trace_metadata"]:
                raise ValueError(f"Extension compliant candidate {op} must specify expected trace metadata keys.")
                
        # Memory touching constraints
        if record["memory_behavior"] in ("read", "write"):
            if "no_memory_write" not in record["safety_constraints"] and "memory_write_rejected" not in record["safety_constraints"]:
                raise ValueError(f"Memory-touching candidate {op} must declare memory safety constraints.")
                
    return True

def summarize_micro_isa_v1_spec() -> Dict[str, Any]:
    """
    Aggregates specifications for a high-level summary report.
    """
    validate_micro_isa_v1_spec_consistency()
    
    by_status = {}
    for record in V1_CANDIDATE_SPEC_RECORDS.values():
        status = record["status"]
        by_status[status] = by_status.get(status, 0) + 1
        
    return {
        "total_candidates": len(V1_CANDIDATE_SPEC_RECORDS),
        "status_distribution": by_status
    }
