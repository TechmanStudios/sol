# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA v1-to-v0 Lowering Module
======================================
Provides standard templates and safety analysis to translate experimental v1 opcodes
into validated v0 strict execution sequences.
"""

from typing import Any, Dict, List, Tuple, Optional
from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_micro_isa_v1_candidates import (
    validate_v1_candidate_instruction,
    is_immediate,
    is_register,
    is_flag_name
)

FLAG_TO_JUMP = {
    "Z": "JZ", "ZERO": "JZ",
    "NZ": "JNZ",
    "C": "JC", "CARRY": "JC",
    "NC": "JNC",
    "B": "JB", "BORROW": "JB",
    "NB": "JNB"
}

CMOV_SKIP_CONDITIONS = {
    "CMOVZ": "JNZ",
    "CMOVNZ": "JZ",
    "CMOVC": "JNC",
    "CMOVNC": "JC",
    "CMOVB": "JNB",
    "CMOVNB": "JB",
}

def get_scratch_register(exclude_regs: List[str]) -> str:
    """Finds a register in R0-R15 that is not in exclude_regs."""
    exclude_set = {r.upper() for r in exclude_regs if isinstance(r, str)}
    for i in range(16):
        reg = f"R{i}"
        if reg not in exclude_set:
            return reg
    raise ValueError(f"No available scratch registers. Excluded: {exclude_regs}")

def validate_v1_candidate_lowering_safety(inst: Any, enable_waveguide_channel_state: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether a candidate instruction can be safely lowered.
    Returns (is_safe, reject_reason).
    """
    try:
        validate_v1_candidate_instruction(inst)
    except ValueError as e:
        return False, f"malformed_schema: {str(e)}"

    op = inst.op.upper()

    if op == "PLOAD_RO":
        # Check address safety: must be static (immediates)
        addr_true, addr_false = inst.src2
        if not (is_immediate(addr_true) and is_immediate(addr_false)):
            return False, "dynamic_address_unknown_alias"

    if op in {"WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE"}:
        if not enable_waveguide_channel_state:
            return False, "unsupported_waveguide_channel_operation"

    return True, None

def lower_v1_candidate_to_v0(
    inst: Any,
    label_counter: int,
    width: int = 32,
    enable_waveguide_channel_state: bool = False
) -> Tuple[List[Any], int, Dict[str, Any]]:
    """
    Lowers a single v1 candidate instruction to a sequence of v0 instructions.
    Returns (lowered_instructions, updated_label_counter, metadata).
    """
    op = inst.op.upper()
    is_safe, reason = validate_v1_candidate_lowering_safety(inst, enable_waveguide_channel_state)

    if not is_safe:
        metadata = {
            "micro_isa_v1_candidate": True,
            "candidate_opcode": op,
            "lowered_to_v0": False,
            "lowering_safe": False,
            "skip_reason": reason
        }
        return [inst], label_counter, metadata

    if op == "SELECT":
        lowered, label_counter, strategy = lower_v1_select_to_v0(inst, label_counter)
    elif op in CMOV_SKIP_CONDITIONS:
        lowered, label_counter, strategy = lower_v1_cmov_to_v0(inst, label_counter)
    elif op == "PLOAD_RO":
        lowered, label_counter, strategy = lower_v1_pload_ro_to_v0(inst, label_counter)
    elif op in {"LANE_ADD", "LANE_SUB"}:
        lowered, label_counter, strategy = lower_v1_lane_arithmetic_to_v0(inst, label_counter)
    elif op in {"PREFIX_ADD", "PREFIX_SUB"}:
        lowered, label_counter, strategy = lower_v1_prefix_arithmetic_to_v0(inst, label_counter)
    elif op == "VEC_PACK":
        lowered, label_counter, strategy = lower_v1_vec_pack_to_v0(inst, label_counter, width)
    elif op == "VEC_UNPACK":
        lowered, label_counter, strategy = lower_v1_vec_unpack_to_v0(inst, label_counter, width)
    elif op == "VEC_BROADCAST":
        lowered, label_counter, strategy = lower_v1_vec_broadcast_to_v0(inst, label_counter, width)
    elif op == "VEC_EXTRACT":
        lowered, label_counter, strategy = lower_v1_vec_extract_to_v0(inst, label_counter, width)
    elif op == "VEC_INSERT":
        lowered, label_counter, strategy = lower_v1_vec_insert_to_v0(inst, label_counter, width)
    elif op in {"VEC_LANE_ADD", "VEC_LANE_SUB", "VEC_LANE_AND", "VEC_LANE_OR", "VEC_LANE_XOR"}:
        lowered, label_counter, strategy = lower_v1_lane_bitwise_arithmetic_to_v0(inst, label_counter, width)
    elif op == "VEC_MASK_SELECT":
        lowered, label_counter, strategy = lower_v1_vec_mask_select_to_v0(inst, label_counter, width)
    elif op == "WG_CHAN_FENCE":
        lowered, label_counter, strategy = lower_v1_wg_chan_fence_to_v0(inst, label_counter, width)
    elif op == "WG_CHAN_SEND":
        lowered, label_counter, strategy = lower_v1_wg_chan_send_to_v0(inst, label_counter, width)
    elif op == "WG_CHAN_RECV":
        lowered, label_counter, strategy = lower_v1_wg_chan_recv_to_v0(inst, label_counter, width)
    elif op == "WG_CHAN_ROUTE":
        lowered, label_counter, strategy = lower_v1_wg_chan_route_to_v0(inst, label_counter, width)
    else:
        # Fallback (should not be hit if validated)
        return [inst], label_counter, {
            "micro_isa_v1_candidate": True,
            "candidate_opcode": op,
            "lowered_to_v0": False,
            "lowering_safe": False,
            "skip_reason": "unknown_opcode"
        }

    metadata = {
        "micro_isa_v1_candidate": True,
        "candidate_opcode": op,
        "candidate_pc": None,  # Filled by Pass Manager
        "lowered_to_v0": True,
        "v0_pc_range": [],  # Filled by Pass Manager
        "lowering_strategy": strategy,
        "semantic_equivalence_required": True,
        "lowering_safe": True,
        "skip_reason": None,
        "dst": getattr(inst, "dst", None),
        "src1": getattr(inst, "src1", None),
        "src2": getattr(inst, "src2", None),
        "original_instruction_obj": inst,
        "original_instruction_str": f"{getattr(inst, 'op', '')} {getattr(inst, 'dst', '')}, {getattr(inst, 'src1', '')}, {getattr(inst, 'src2', '')}"
    }

    return lowered, label_counter, metadata

def lower_v1_select_to_v0(inst: Any, label_counter: int) -> Tuple[List[Any], int, str]:
    """Lowers SELECT to a branch diamond."""
    dst = inst.dst
    cond = inst.src1
    src_true, src_false = inst.src2

    l_true = f"__v1_lowered_L_true_{label_counter}"
    l_end = f"__v1_lowered_L_end_{label_counter}"
    label_counter += 1

    ops = []
    
    # Check if cond is flag name or register
    if isinstance(cond, str) and cond.upper() in FLAG_TO_JUMP:
        jump_op = FLAG_TO_JUMP[cond.upper()]
        ops.append(WideWordProgramInstruction(op=jump_op, dst=l_true))
    else:
        # Register condition
        ops.append(WideWordProgramInstruction(op="CMP", dst=cond, src1=0))
        ops.append(WideWordProgramInstruction(op="JNZ", dst=l_true))

    # False path
    mov_false_op = "LOAD_IMM" if isinstance(src_false, int) else "MOV"
    ops.append(WideWordProgramInstruction(op=mov_false_op, dst=dst, src1=src_false))
    ops.append(WideWordProgramInstruction(op="JMP", dst=l_end))

    # True path
    ops.append(f"{l_true}:")
    mov_true_op = "LOAD_IMM" if isinstance(src_true, int) else "MOV"
    ops.append(WideWordProgramInstruction(op=mov_true_op, dst=dst, src1=src_true))

    # End label
    ops.append(f"{l_end}:")

    return ops, label_counter, "branchless_select_via_predication"

def lower_v1_cmov_to_v0(inst: Any, label_counter: int) -> Tuple[List[Any], int, str]:
    """Lowers CMOV* to a single conditional skip branch diamond."""
    op = inst.op.upper()
    dst = inst.dst
    src = inst.src1

    l_skip = f"__v1_lowered_L_skip_{label_counter}"
    label_counter += 1

    skip_op = CMOV_SKIP_CONDITIONS[op]
    mov_op = "LOAD_IMM" if isinstance(src, int) else "MOV"

    ops = [
        WideWordProgramInstruction(op=skip_op, dst=l_skip),
        WideWordProgramInstruction(op=mov_op, dst=dst, src1=src),
        f"{l_skip}:"
    ]

    return ops, label_counter, "conditional_select_via_skip_branch"

def lower_v1_pload_ro_to_v0(inst: Any, label_counter: int) -> Tuple[List[Any], int, str]:
    """Lowers PLOAD_RO to a conditional load diamond using the destination as a temp register."""
    dst = inst.dst
    cond = inst.src1
    addr_true, addr_false = inst.src2

    l_true = f"__v1_lowered_L_true_{label_counter}"
    l_end = f"__v1_lowered_L_end_{label_counter}"
    label_counter += 1

    ops = []
    
    # Check if cond is flag name or register
    if isinstance(cond, str) and cond.upper() in FLAG_TO_JUMP:
        jump_op = FLAG_TO_JUMP[cond.upper()]
        ops.append(WideWordProgramInstruction(op=jump_op, dst=l_true))
    else:
        ops.append(WideWordProgramInstruction(op="CMP", dst=cond, src1=0))
        ops.append(WideWordProgramInstruction(op="JNZ", dst=l_true))

    # False path
    ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=dst, src1=addr_false))
    ops.append(WideWordProgramInstruction(op="LOAD", dst=dst, src1=dst))
    ops.append(WideWordProgramInstruction(op="JMP", dst=l_end))

    # True path
    ops.append(f"{l_true}:")
    ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=dst, src1=addr_true))
    ops.append(WideWordProgramInstruction(op="LOAD", dst=dst, src1=dst))

    # End label
    ops.append(f"{l_end}:")

    return ops, label_counter, "conditional_load_via_predication"

def lower_v1_lane_arithmetic_to_v0(inst: Any, label_counter: int) -> Tuple[List[Any], int, str]:
    """Lowers LANE_ADD/SUB to standard v0 ALU ADD/SUB."""
    op = inst.op.upper()
    v0_op = "ADD" if "ADD" in op else "SUB"
    ops = [
        WideWordProgramInstruction(op=v0_op, dst=inst.dst, src1=inst.src1, src2=inst.src2)
    ]
    return ops, label_counter, "direct_v0_alu_mapping"

def lower_v1_prefix_arithmetic_to_v0(inst: Any, label_counter: int) -> Tuple[List[Any], int, str]:
    """Lowers PREFIX_ADD/SUB to standard v0 ALU ADD/SUB."""
    op = inst.op.upper()
    v0_op = "ADD" if "ADD" in op else "SUB"
    ops = [
        WideWordProgramInstruction(op=v0_op, dst=inst.dst, src1=inst.src1, src2=inst.src2)
    ]
    return ops, label_counter, "direct_v0_alu_mapping"

def lower_v1_vec_pack_to_v0(inst: Any, label_counter: int, width: int = 32) -> Tuple[List[Any], int, str]:
    dst = inst.dst
    lanes = inst.src2  # 4-tuple of registers/immediates
    lane_size = width // 4
    mask_val = (1 << lane_size) - 1
    
    # Collect all operand registers to exclude
    exclude = [dst]
    for l in lanes:
        if isinstance(l, str):
            exclude.append(l)
            
    acc = get_scratch_register(exclude)
    ops = []
    
    for i, val in enumerate(lanes):
        shift_amt = i * lane_size
        if isinstance(val, int):
            masked_shifted = (val & mask_val) << shift_amt
            if i == 0:
                ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=acc, src1=masked_shifted))
            else:
                t = get_scratch_register(exclude + [acc])
                ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=t, src1=masked_shifted))
                ops.append(WideWordProgramInstruction(op="OR", dst=acc, src1=acc, src2=t))
        else:
            t = get_scratch_register(exclude + [acc])
            ops.append(WideWordProgramInstruction(op="MOV", dst=t, src1=val))
            ops.append(WideWordProgramInstruction(op="AND", dst=t, src1=t, src2=mask_val))
            if shift_amt > 0:
                ops.append(WideWordProgramInstruction(op="SHL", dst=t, src1=t, src2=shift_amt))
            if i == 0:
                ops.append(WideWordProgramInstruction(op="MOV", dst=acc, src1=t))
            else:
                ops.append(WideWordProgramInstruction(op="OR", dst=acc, src1=acc, src2=t))
                
    ops.append(WideWordProgramInstruction(op="MOV", dst=dst, src1=acc))
    return ops, label_counter, "vec_pack_via_shifts_and_ors"

def lower_v1_vec_unpack_to_v0(inst: Any, label_counter: int, width: int = 32) -> Tuple[List[Any], int, str]:
    src = inst.dst
    dests = inst.src2  # 4-tuple of registers
    lane_size = width // 4
    mask_val = (1 << lane_size) - 1
    
    ops = []
    for i, dst_i in enumerate(dests):
        shift_amt = i * lane_size
        if shift_amt == 0:
            ops.append(WideWordProgramInstruction(op="AND", dst=dst_i, src1=src, src2=mask_val))
        else:
            ops.append(WideWordProgramInstruction(op="SHR", dst=dst_i, src1=src, src2=shift_amt))
            ops.append(WideWordProgramInstruction(op="AND", dst=dst_i, src1=dst_i, src2=mask_val))
            
    return ops, label_counter, "vec_unpack_via_shifts_and_masks"

def lower_v1_vec_broadcast_to_v0(inst: Any, label_counter: int, width: int = 32) -> Tuple[List[Any], int, str]:
    dst = inst.dst
    src = inst.src1
    lane_size = width // 4
    mask_val = (1 << lane_size) - 1
    
    ops = []
    if isinstance(src, int):
        masked_val = src & mask_val
        broadcast_val = 0
        for i in range(4):
            broadcast_val |= (masked_val << (i * lane_size))
        ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=dst, src1=broadcast_val))
    else:
        exclude = [dst, src]
        t = get_scratch_register(exclude)
        t2 = get_scratch_register(exclude + [t])
        
        ops.append(WideWordProgramInstruction(op="AND", dst=t, src1=src, src2=mask_val))
        ops.append(WideWordProgramInstruction(op="SHL", dst=t2, src1=t, src2=lane_size))
        ops.append(WideWordProgramInstruction(op="OR", dst=t, src1=t, src2=t2))
        ops.append(WideWordProgramInstruction(op="SHL", dst=t2, src1=t, src2=2 * lane_size))
        ops.append(WideWordProgramInstruction(op="OR", dst=t, src1=t, src2=t2))
        ops.append(WideWordProgramInstruction(op="MOV", dst=dst, src1=t))
        
    return ops, label_counter, "vec_broadcast_via_duplication_shifts"

def lower_v1_vec_extract_to_v0(inst: Any, label_counter: int, width: int = 32) -> Tuple[List[Any], int, str]:
    dst = inst.dst
    src = inst.src1
    lane_index = inst.src2
    lane_size = width // 4
    mask_val = (1 << lane_size) - 1
    
    ops = []
    shift_amt = lane_index * lane_size
    if shift_amt == 0:
        ops.append(WideWordProgramInstruction(op="AND", dst=dst, src1=src, src2=mask_val))
    else:
        ops.append(WideWordProgramInstruction(op="SHR", dst=dst, src1=src, src2=shift_amt))
        ops.append(WideWordProgramInstruction(op="AND", dst=dst, src1=dst, src2=mask_val))
        
    return ops, label_counter, "vec_extract_via_shift_and_mask"

def lower_v1_vec_insert_to_v0(inst: Any, label_counter: int, width: int = 32) -> Tuple[List[Any], int, str]:
    dst = inst.dst
    src_vec = inst.src1
    lane_index, src_scalar = inst.src2
    lane_size = width // 4
    mask_val = (1 << lane_size) - 1
    
    exclude = [dst, src_vec]
    if isinstance(src_scalar, str):
        exclude.append(src_scalar)
        
    t = get_scratch_register(exclude)
    t_vec = get_scratch_register(exclude + [t])
    
    ops = []
    
    # 1. Clear target lane in src_vec
    shift_amt = lane_index * lane_size
    clear_mask = (~(mask_val << shift_amt)) & ((1 << width) - 1)
    ops.append(WideWordProgramInstruction(op="AND", dst=t_vec, src1=src_vec, src2=clear_mask))
    
    # 2. Prepare shifted scalar in t
    if isinstance(src_scalar, int):
        shifted_val = (src_scalar & mask_val) << shift_amt
        ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=t, src1=shifted_val))
    else:
        ops.append(WideWordProgramInstruction(op="MOV", dst=t, src1=src_scalar))
        ops.append(WideWordProgramInstruction(op="AND", dst=t, src1=t, src2=mask_val))
        if shift_amt > 0:
            ops.append(WideWordProgramInstruction(op="SHL", dst=t, src1=t, src2=shift_amt))
            
    # 3. Combine into dst
    ops.append(WideWordProgramInstruction(op="OR", dst=dst, src1=t_vec, src2=t))
    
    return ops, label_counter, "vec_insert_via_clear_mask_and_or"

def lower_v1_lane_bitwise_arithmetic_to_v0(
    inst: Any,
    label_counter: int,
    width: int = 32
) -> Tuple[List[Any], int, str]:
    op = inst.op.upper()
    dst = inst.dst
    src_a = inst.src1
    src_b, mask = inst.src2
    lane_size = width // 4
    mask_val = (1 << lane_size) - 1
    
    op_type = "ADD" if "ADD" in op else "SUB" if "SUB" in op else "AND" if "AND" in op else "OR" if "OR" in op else "XOR"
    
    exclude = [dst, src_a]
    if isinstance(src_b, str):
        exclude.append(src_b)
        
    acc = get_scratch_register(exclude)
    ops = []
    
    for i in range(4):
        a_lane = get_scratch_register(exclude + [acc])
        # Extract lane i of src_a
        ext_inst = WideWordProgramInstruction(op="VEC_EXTRACT", dst=a_lane, src1=src_a, src2=i)
        ext_ops, label_counter, _ = lower_v1_vec_extract_to_v0(ext_inst, label_counter, width)
        ops.extend(ext_ops)
        
        target_lane = a_lane
        if (mask & (1 << i)) != 0:
            b_lane = get_scratch_register(exclude + [acc, a_lane])
            if isinstance(src_b, int):
                b_val = (src_b >> (i * lane_size)) & mask_val
                ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=b_lane, src1=b_val))
            else:
                ext_b_inst = WideWordProgramInstruction(op="VEC_EXTRACT", dst=b_lane, src1=src_b, src2=i)
                ext_b_ops, label_counter, _ = lower_v1_vec_extract_to_v0(ext_b_inst, label_counter, width)
                ops.extend(ext_b_ops)
                
            res_lane = get_scratch_register(exclude + [acc, a_lane, b_lane])
            ops.append(WideWordProgramInstruction(op=op_type, dst=res_lane, src1=a_lane, src2=b_lane))
            ops.append(WideWordProgramInstruction(op="AND", dst=res_lane, src1=res_lane, src2=mask_val))
            target_lane = res_lane
            
        # Insert target_lane into acc
        shift_amt = i * lane_size
        if shift_amt > 0:
            t_shift = get_scratch_register(exclude + [acc, target_lane])
            ops.append(WideWordProgramInstruction(op="SHL", dst=t_shift, src1=target_lane, src2=shift_amt))
            ops.append(WideWordProgramInstruction(op="OR", dst=acc, src1=acc, src2=t_shift))
        else:
            ops.append(WideWordProgramInstruction(op="MOV", dst=acc, src1=target_lane))
            
    ops.append(WideWordProgramInstruction(op="MOV", dst=dst, src1=acc))
    return ops, label_counter, f"lane_{op_type.lower()}_via_lane_extraction"

def lower_v1_vec_mask_select_to_v0(
    inst: Any,
    label_counter: int,
    width: int = 32
) -> Tuple[List[Any], int, str]:
    dst = inst.dst
    mask = inst.src1
    src_true, src_false = inst.src2
    lane_size = width // 4
    mask_val = (1 << lane_size) - 1
    
    exclude = [dst]
    if isinstance(mask, str):
        exclude.append(mask)
    if isinstance(src_true, str):
        exclude.append(src_true)
    if isinstance(src_false, str):
        exclude.append(src_false)
        
    acc = get_scratch_register(exclude)
    ops = []
    
    for i in range(4):
        # Extract lane i from src_true
        true_lane = get_scratch_register(exclude + [acc])
        if isinstance(src_true, int):
            t_val = (src_true >> (i * lane_size)) & mask_val
            ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=true_lane, src1=t_val))
        else:
            ext_t_inst = WideWordProgramInstruction(op="VEC_EXTRACT", dst=true_lane, src1=src_true, src2=i)
            ext_t_ops, label_counter, _ = lower_v1_vec_extract_to_v0(ext_t_inst, label_counter, width)
            ops.extend(ext_t_ops)
            
        # Extract lane i from src_false
        false_lane = get_scratch_register(exclude + [acc, true_lane])
        if isinstance(src_false, int):
            f_val = (src_false >> (i * lane_size)) & mask_val
            ops.append(WideWordProgramInstruction(op="LOAD_IMM", dst=false_lane, src1=f_val))
        else:
            ext_f_inst = WideWordProgramInstruction(op="VEC_EXTRACT", dst=false_lane, src1=src_false, src2=i)
            ext_f_ops, label_counter, _ = lower_v1_vec_extract_to_v0(ext_f_inst, label_counter, width)
            ops.extend(ext_f_ops)
            
        target_lane = get_scratch_register(exclude + [acc, true_lane, false_lane])
        
        # Decide which lane to use
        if isinstance(mask, int):
            if (mask & (1 << i)) != 0:
                ops.append(WideWordProgramInstruction(op="MOV", dst=target_lane, src1=true_lane))
            else:
                ops.append(WideWordProgramInstruction(op="MOV", dst=target_lane, src1=false_lane))
        else:
            # Mask is a register
            bit_reg = get_scratch_register(exclude + [acc, true_lane, false_lane, target_lane])
            ops.append(WideWordProgramInstruction(op="SHR", dst=bit_reg, src1=mask, src2=i))
            ops.append(WideWordProgramInstruction(op="AND", dst=bit_reg, src1=bit_reg, src2=1))
            
            l_true = f"__v1_lowered_select_L_true_{label_counter}_{i}"
            l_end = f"__v1_lowered_select_L_end_{label_counter}_{i}"
            label_counter += 1
            
            ops.append(WideWordProgramInstruction(op="CMP", dst=bit_reg, src1=0))
            ops.append(WideWordProgramInstruction(op="JNZ", dst=l_true))
            
            # False path
            ops.append(WideWordProgramInstruction(op="MOV", dst=target_lane, src1=false_lane))
            ops.append(WideWordProgramInstruction(op="JMP", dst=l_end))
            
            # True path
            ops.append(f"{l_true}:")
            ops.append(WideWordProgramInstruction(op="MOV", dst=target_lane, src1=true_lane))
            
            ops.append(f"{l_end}:")
            
        # Insert target_lane into acc
        shift_amt = i * lane_size
        if shift_amt > 0:
            t_shift = get_scratch_register(exclude + [acc, target_lane])
            ops.append(WideWordProgramInstruction(op="SHL", dst=t_shift, src1=target_lane, src2=shift_amt))
            ops.append(WideWordProgramInstruction(op="OR", dst=acc, src1=acc, src2=t_shift))
        else:
            ops.append(WideWordProgramInstruction(op="MOV", dst=acc, src1=target_lane))
            
    ops.append(WideWordProgramInstruction(op="MOV", dst=dst, src1=acc))
    return ops, label_counter, "vec_mask_select_via_lane_selection"

def lower_v1_wg_chan_fence_to_v0(
    inst: Any,
    label_counter: int,
    width: int = 32
) -> Tuple[List[Any], int, str]:
    ops = [
        WideWordProgramInstruction(op="MOV", dst="R0", src1="R0")
    ]
    return ops, label_counter, "waveguide_channel_fence_barrier"

def lower_v1_wg_chan_send_to_v0(
    inst: Any,
    label_counter: int,
    width: int = 32
) -> Tuple[List[Any], int, str]:
    ops = [
        WideWordProgramInstruction(op="MOV", dst="R0", src1="R0")
    ]
    return ops, label_counter, "waveguide_channel_send_barrier"

def lower_v1_wg_chan_recv_to_v0(
    inst: Any,
    label_counter: int,
    width: int = 32
) -> Tuple[List[Any], int, str]:
    ops = [
        WideWordProgramInstruction(op="MOV", dst=inst.dst, src1=inst.dst)
    ]
    return ops, label_counter, "waveguide_channel_recv_barrier"

def lower_v1_wg_chan_route_to_v0(
    inst: Any,
    label_counter: int,
    width: int = 32
) -> Tuple[List[Any], int, str]:
    ops = [
        WideWordProgramInstruction(op="MOV", dst="R0", src1="R0")
    ]
    return ops, label_counter, "waveguide_channel_route_barrier"


def validate_v1_lowering_equivalence(
    lowered_state: Any,
    v0_state: Any
) -> bool:
    """Verifies register, flag, and memory state equivalence."""
    return (
        lowered_state.registers == v0_state.registers and
        lowered_state.flags == v0_state.flags and
        lowered_state.memory.cells == v0_state.memory.cells
    )

def summarize_v1_lowering_report(lowering_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarizes v1 lowering statistics."""
    total = len(lowering_metadata)
    lowered = sum(1 for m in lowering_metadata if m.get("lowered_to_v0", False))
    rejected = total - lowered
    
    return {
        "total_v1_candidates": total,
        "successfully_lowered": lowered,
        "rejected": rejected
    }
