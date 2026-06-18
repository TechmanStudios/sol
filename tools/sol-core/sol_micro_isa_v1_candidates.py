# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA v1 Candidate Opcode Definition Module
====================================================
Defines the experimental v1 extension opcodes, operand schemas, and stability contracts.
"""

from typing import Any, Dict, List, Tuple, Union

V1_CANDIDATE_OPCODES = {
    "SELECT",
    "CMOVZ",
    "CMOVNZ",
    "CMOVC",
    "CMOVNC",
    "CMOVB",
    "CMOVNB",
    "PLOAD_RO",
    "LANE_ADD",
    "LANE_SUB",
    "PREFIX_ADD",
    "PREFIX_SUB",
    "VEC_PACK",
    "VEC_UNPACK",
    "VEC_BROADCAST",
    "VEC_EXTRACT",
    "VEC_INSERT",
    "VEC_LANE_ADD",
    "VEC_LANE_SUB",
    "VEC_LANE_AND",
    "VEC_LANE_OR",
    "VEC_LANE_XOR",
    "VEC_MASK_SELECT",
    "WG_CHAN_SEND",
    "WG_CHAN_RECV",
    "WG_CHAN_ROUTE",
    "WG_CHAN_FENCE",
}

STABILITY_STATUS = {
    "SELECT": "experimental",
    "CMOVZ": "experimental",
    "CMOVNZ": "experimental",
    "CMOVC": "experimental",
    "CMOVNC": "experimental",
    "CMOVB": "experimental",
    "CMOVNB": "experimental",
    "PLOAD_RO": "experimental",
    "LANE_ADD": "experimental",
    "LANE_SUB": "experimental",
    "PREFIX_ADD": "experimental",
    "PREFIX_SUB": "experimental",
    "VEC_PACK": "experimental",
    "VEC_UNPACK": "experimental",
    "VEC_BROADCAST": "experimental",
    "VEC_EXTRACT": "experimental",
    "VEC_INSERT": "experimental",
    "VEC_LANE_ADD": "experimental",
    "VEC_LANE_SUB": "experimental",
    "VEC_LANE_AND": "experimental",
    "VEC_LANE_OR": "experimental",
    "VEC_LANE_XOR": "experimental",
    "VEC_MASK_SELECT": "experimental",
    "WG_CHAN_SEND": "experimental",
    "WG_CHAN_RECV": "experimental",
    "WG_CHAN_ROUTE": "experimental",
    "WG_CHAN_FENCE": "experimental",
}

def is_register(val: Any) -> bool:
    """Checks if a value is a valid register identifier (e.g. R0 to R15)."""
    if not isinstance(val, str):
        return False
    if not val.startswith("R"):
        return False
    try:
        num = int(val[1:])
        return 0 <= num <= 15
    except ValueError:
        return False

def is_immediate(val: Any) -> bool:
    """Checks if a value is a valid immediate integer."""
    return isinstance(val, int) and not isinstance(val, bool)

def is_flag_name(val: Any) -> bool:
    """Checks if a value is a valid CPU flag name or alias."""
    return isinstance(val, str) and val.upper() in {
        "ZERO", "CARRY", "OVERFLOW", "SIGN", "BORROW",
        "Z", "NZ", "C", "NC", "B", "NB"
    }

def validate_v1_candidate_instruction(inst: Any) -> bool:
    """
    Validates the structure and operand schemas of a v1 candidate instruction.
    Raises ValueError if the instruction is malformed or uses unsupported types.
    """
    if not hasattr(inst, "op") or not hasattr(inst, "dst") or not hasattr(inst, "src1") or not hasattr(inst, "src2"):
        raise ValueError("Instruction must have op, dst, src1, and src2 attributes.")

    op = inst.op.upper()
    if op not in V1_CANDIDATE_OPCODES:
        raise ValueError(f"Unknown v1 candidate opcode: {op}")

    # Validate SELECT
    if op == "SELECT":
        # SELECT dst, cond, (src_true, src_false)
        if not is_register(inst.dst):
            raise ValueError(f"SELECT dst must be a register, got {inst.dst}")
        # cond can be a register or a flag name
        if not (is_register(inst.src1) or is_flag_name(inst.src1)):
            raise ValueError(f"SELECT condition must be a register or a flag name, got {inst.src1}")
        if not isinstance(inst.src2, (tuple, list)) or len(inst.src2) != 2:
            raise ValueError(f"SELECT expects a tuple/list of two source values in src2, got {inst.src2}")
        src_true, src_false = inst.src2
        if not (is_register(src_true) or is_immediate(src_true)):
            raise ValueError(f"SELECT src_true must be a register or immediate, got {src_true}")
        if not (is_register(src_false) or is_immediate(src_false)):
            raise ValueError(f"SELECT src_false must be a register or immediate, got {src_false}")

    # Validate CMOV*
    elif op in {"CMOVZ", "CMOVNZ", "CMOVC", "CMOVNC", "CMOVB", "CMOVNB"}:
        # CMOV* dst, src
        if not is_register(inst.dst):
            raise ValueError(f"{op} dst must be a register, got {inst.dst}")
        if not (is_register(inst.src1) or is_immediate(inst.src1)):
            raise ValueError(f"{op} src must be a register or immediate, got {inst.src1}")
        if inst.src2 is not None:
            raise ValueError(f"{op} does not expect a src2 operand, got {inst.src2}")

    # Validate PLOAD_RO
    elif op == "PLOAD_RO":
        # PLOAD_RO dst, predicate, (addr_true, addr_false)
        if not is_register(inst.dst):
            raise ValueError(f"PLOAD_RO dst must be a register, got {inst.dst}")
        if not (is_register(inst.src1) or is_flag_name(inst.src1)):
            raise ValueError(f"PLOAD_RO predicate must be a register or flag name, got {inst.src1}")
        if not isinstance(inst.src2, (tuple, list)) or len(inst.src2) != 2:
            raise ValueError(f"PLOAD_RO expects a tuple/list of two address values in src2, got {inst.src2}")
        addr_true, addr_false = inst.src2
        if not (is_register(addr_true) or is_immediate(addr_true)):
            raise ValueError(f"PLOAD_RO addr_true must be a register or immediate, got {addr_true}")
        if not (is_register(addr_false) or is_immediate(addr_false)):
            raise ValueError(f"PLOAD_RO addr_false must be a register or immediate, got {addr_false}")

    # Validate LANE_ADD, LANE_SUB, PREFIX_ADD, PREFIX_SUB
    elif op in {"LANE_ADD", "LANE_SUB", "PREFIX_ADD", "PREFIX_SUB"}:
        # LANE_*/PREFIX_* dst, src1, src2
        if not is_register(inst.dst):
            raise ValueError(f"{op} dst must be a register, got {inst.dst}")
        if not is_register(inst.src1):
            raise ValueError(f"{op} src1 must be a register, got {inst.src1}")
        if not (is_register(inst.src2) or is_immediate(inst.src2)):
            raise ValueError(f"{op} src2 must be a register or immediate, got {inst.src2}")

    # Validate VEC_PACK
    elif op == "VEC_PACK":
        if not is_register(inst.dst):
            raise ValueError(f"VEC_PACK dst must be a register, got {inst.dst}")
        if not isinstance(inst.src2, (tuple, list)) or len(inst.src2) != 4:
            raise ValueError(f"VEC_PACK expects a 4-tuple of lane values in src2, got {inst.src2}")
        for i, lane in enumerate(inst.src2):
            if not (is_register(lane) or is_immediate(lane)):
                raise ValueError(f"VEC_PACK lane {i} must be a register or immediate, got {lane}")

    # Validate VEC_UNPACK
    elif op == "VEC_UNPACK":
        if not is_register(inst.dst):
            raise ValueError(f"VEC_UNPACK src must be a register, got {inst.dst}")
        if not isinstance(inst.src2, (tuple, list)) or len(inst.src2) != 4:
            raise ValueError(f"VEC_UNPACK expects a 4-tuple of destination registers in src2, got {inst.src2}")
        for i, r in enumerate(inst.src2):
            if not is_register(r):
                raise ValueError(f"VEC_UNPACK dst {i} must be a register, got {r}")

    # Validate VEC_BROADCAST
    elif op == "VEC_BROADCAST":
        if not is_register(inst.dst):
            raise ValueError(f"VEC_BROADCAST dst must be a register, got {inst.dst}")
        if not (is_register(inst.src1) or is_immediate(inst.src1)):
            raise ValueError(f"VEC_BROADCAST src must be a register or immediate, got {inst.src1}")
        if inst.src2 is not None:
            raise ValueError(f"VEC_BROADCAST does not expect a src2 operand, got {inst.src2}")

    # Validate VEC_EXTRACT
    elif op == "VEC_EXTRACT":
        if not is_register(inst.dst):
            raise ValueError(f"VEC_EXTRACT dst must be a register, got {inst.dst}")
        if not is_register(inst.src1):
            raise ValueError(f"VEC_EXTRACT src must be a register, got {inst.src1}")
        if not is_immediate(inst.src2) or not (0 <= inst.src2 <= 3):
            raise ValueError(f"VEC_EXTRACT lane_index must be an integer in [0, 3], got {inst.src2}")

    # Validate VEC_INSERT
    elif op == "VEC_INSERT":
        if not is_register(inst.dst):
            raise ValueError(f"VEC_INSERT dst must be a register, got {inst.dst}")
        if not is_register(inst.src1):
            raise ValueError(f"VEC_INSERT src_vec must be a register, got {inst.src1}")
        if not isinstance(inst.src2, (tuple, list)) or len(inst.src2) != 2:
            raise ValueError(f"VEC_INSERT expects a 2-tuple (lane_index, src_scalar) in src2, got {inst.src2}")
        lane_index, src_scalar = inst.src2
        if not is_immediate(lane_index) or not (0 <= lane_index <= 3):
            raise ValueError(f"VEC_INSERT lane_index must be an integer in [0, 3], got {lane_index}")
        if not (is_register(src_scalar) or is_immediate(src_scalar)):
            raise ValueError(f"VEC_INSERT src_scalar must be a register or immediate, got {src_scalar}")

    # Validate VEC_LANE_ADD, VEC_LANE_SUB, VEC_LANE_AND, VEC_LANE_OR, VEC_LANE_XOR
    elif op in {"VEC_LANE_ADD", "VEC_LANE_SUB", "VEC_LANE_AND", "VEC_LANE_OR", "VEC_LANE_XOR"}:
        if not is_register(inst.dst):
            raise ValueError(f"{op} dst must be a register, got {inst.dst}")
        if not is_register(inst.src1):
            raise ValueError(f"{op} src_a must be a register, got {inst.src1}")
        if not isinstance(inst.src2, (tuple, list)) or len(inst.src2) != 2:
            raise ValueError(f"{op} expects a 2-tuple (src_b, mask) in src2, got {inst.src2}")
        src_b, mask = inst.src2
        if not (is_register(src_b) or is_immediate(src_b)):
            raise ValueError(f"{op} src_b must be a register or immediate, got {src_b}")
        if not is_immediate(mask) or not (0 <= mask <= 0xF):
            raise ValueError(f"{op} mask must be an integer in [0, 15], got {mask}")

    # Validate VEC_MASK_SELECT
    elif op == "VEC_MASK_SELECT":
        if not is_register(inst.dst):
            raise ValueError(f"VEC_MASK_SELECT dst must be a register, got {inst.dst}")
        if not (is_register(inst.src1) or is_immediate(inst.src1)):
            raise ValueError(f"VEC_MASK_SELECT mask must be a register or immediate, got {inst.src1}")
        if isinstance(inst.src1, int) and not (0 <= inst.src1 <= 0xF):
            raise ValueError(f"VEC_MASK_SELECT mask immediate must be in [0, 15], got {inst.src1}")
        if not isinstance(inst.src2, (tuple, list)) or len(inst.src2) != 2:
            raise ValueError(f"VEC_MASK_SELECT expects a 2-tuple (src_true, src_false) in src2, got {inst.src2}")
        src_true, src_false = inst.src2
        if not (is_register(src_true) or is_immediate(src_true)):
            raise ValueError(f"VEC_MASK_SELECT src_true must be a register or immediate, got {src_true}")
        if not (is_register(src_false) or is_immediate(src_false)):
            raise ValueError(f"VEC_MASK_SELECT src_false must be a register or immediate, got {src_false}")

    # Validate WG_CHAN_SEND
    elif op == "WG_CHAN_SEND":
        if not (is_immediate(inst.dst) or is_register(inst.dst) or isinstance(inst.dst, str)):
            raise ValueError(f"WG_CHAN_SEND channel must be an integer, register, or string, got {inst.dst}")
        if not (is_register(inst.src1) or is_immediate(inst.src1)):
            raise ValueError(f"WG_CHAN_SEND src must be a register or immediate, got {inst.src1}")
        if inst.src2 is not None:
            raise ValueError(f"WG_CHAN_SEND does not expect a src2 operand, got {inst.src2}")

    # Validate WG_CHAN_RECV
    elif op == "WG_CHAN_RECV":
        if not is_register(inst.dst):
            raise ValueError(f"WG_CHAN_RECV dst must be a register, got {inst.dst}")
        if not (is_immediate(inst.src1) or is_register(inst.src1) or isinstance(inst.src1, str)):
            raise ValueError(f"WG_CHAN_RECV channel must be an integer, register, or string, got {inst.src1}")
        if inst.src2 is not None:
            raise ValueError(f"WG_CHAN_RECV does not expect a src2 operand, got {inst.src2}")

    # Validate WG_CHAN_ROUTE
    elif op == "WG_CHAN_ROUTE":
        if not (is_immediate(inst.dst) or is_register(inst.dst) or isinstance(inst.dst, str)):
            raise ValueError(f"WG_CHAN_ROUTE dst_channel must be an integer, register, or string, got {inst.dst}")
        if not (is_immediate(inst.src1) or is_register(inst.src1) or isinstance(inst.src1, str)):
            raise ValueError(f"WG_CHAN_ROUTE src_channel must be an integer, register, or string, got {inst.src1}")
        if not (is_immediate(inst.src2) or is_register(inst.src2)):
            raise ValueError(f"WG_CHAN_ROUTE route_mask must be a register or immediate, got {inst.src2}")

    # Validate WG_CHAN_FENCE
    elif op == "WG_CHAN_FENCE":
        if inst.dst is not None or inst.src1 is not None or inst.src2 is not None:
            raise ValueError(f"WG_CHAN_FENCE does not expect any operands, got dst={inst.dst}, src1={inst.src1}, src2={inst.src2}")

    return True
