# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Memory Alias + Shard Range Analysis Bridge
========================================================
Implements static/dynamic memory access range parsing, alias classification,
and instruction reorder safety validation for PDM/waveguide optimization passes.
"""

from typing import List, Dict, Any, Tuple, Optional

def build_waveguide_memory_access(inst: Any, pc: int, width_default: int = 32) -> Optional[Dict[str, Any]]:
    """
    Parses a single instruction's memory operand and returns its memory access metadata,
    or None if the instruction is not a memory operation.
    """
    op = inst.op.upper()
    if op not in ("LOAD", "STORE"):
        return None
        
    access_kind = "read" if op == "LOAD" else "write"
    shard_id = getattr(inst, "shard_id", getattr(inst, "shard", "default"))
    if shard_id is None:
        shard_id = "default"
        
    width_bits = getattr(inst, "width_bits", getattr(inst, "width", width_default))
    if not isinstance(width_bits, int) or width_bits <= 0:
        width_bits = width_default
        
    address = None
    address_kind = "dynamic"
    is_dynamic = True
    is_barrier = True
    barrier_reason = "dynamic_address_unknown_alias"
    range_start = None
    range_end = None
    
    # Check if address operand is present
    if hasattr(inst, "src1") and inst.src1 is not None:
        addr_op = inst.src1
        if isinstance(addr_op, int):
            # Static address
            address = addr_op
            is_dynamic = False
            if address >= 0:
                address_kind = "static"
                is_barrier = False
                barrier_reason = None
                bytes_count = max(1, width_bits // 8)
                range_start = address
                range_end = address + bytes_count - 1
            else:
                address_kind = "invalid"
                barrier_reason = "negative_address_out_of_bounds"
        elif isinstance(addr_op, str) and addr_op.startswith("R"):
            # Dynamic address register
            address_kind = "dynamic"
            barrier_reason = "dynamic_address_unknown_alias"
            
    return {
        "pc": pc,
        "opcode": op,
        "access_kind": access_kind,
        "shard_id": shard_id,
        "address": address,
        "address_kind": address_kind,
        "width_bits": width_bits,
        "range_start": range_start,
        "range_end": range_end,
        "is_dynamic": is_dynamic,
        "is_barrier": is_barrier,
        "barrier_reason": barrier_reason,
    }

def build_waveguide_memory_range(address: int, width_bits: int) -> Tuple[Optional[int], Optional[int]]:
    """
    Calculates range_start and range_end bounds for a static address.
    """
    if not isinstance(address, int) or address < 0:
        return None, None
    bytes_count = max(1, width_bits // 8)
    return address, address + bytes_count - 1

def classify_waveguide_memory_alias(access1: Optional[Dict[str, Any]], access2: Optional[Dict[str, Any]]) -> str:
    """
    Classifies the alias relationship between two memory accesses.
    Returns: "NO_ALIAS", "MAY_ALIAS", "MUST_ALIAS", or "UNKNOWN_ALIAS".
    """
    if access1 is None or access2 is None:
        return "NO_ALIAS"
        
    # Check for barriers/dynamic addresses
    if access1.get("is_barrier") or access2.get("is_barrier"):
        return "UNKNOWN_ALIAS"
        
    shard1 = access1.get("shard_id")
    shard2 = access2.get("shard_id")
    
    if shard1 is None or shard2 is None:
        return "UNKNOWN_ALIAS"
        
    # Shard boundary isolation
    if shard1 != shard2:
        return "NO_ALIAS"
        
    # Same shard: compare range bounds
    s1, e1 = access1.get("range_start"), access1.get("range_end")
    s2, e2 = access2.get("range_start"), access2.get("range_end")
    
    if s1 is None or e1 is None or s2 is None or e2 is None:
        return "UNKNOWN_ALIAS"
        
    # Overlap check
    overlap = max(s1, s2) <= min(e1, e2)
    if not overlap:
        return "NO_ALIAS"
        
    # Overlapping same-shard range
    addr1 = access1.get("address")
    addr2 = access2.get("address")
    w1 = access1.get("width_bits")
    w2 = access2.get("width_bits")
    
    if addr1 == addr2 and w1 == w2:
        return "MUST_ALIAS"
    else:
        return "MAY_ALIAS"

def validate_waveguide_memory_reorder_safety(access1: Optional[Dict[str, Any]], access2: Optional[Dict[str, Any]]) -> bool:
    """
    Returns True if access1 and access2 do not have conflicting memory hazards (RAW, WAR, WAW)
    and can be safely reordered or executed in parallel wavefronts.
    """
    if access1 is None or access2 is None:
        return True
        
    # Read-After-Read (RAR) is safe to reorder
    if access1.get("access_kind") == "read" and access2.get("access_kind") == "read":
        return True
        
    # If at least one is a write, we must prove NO_ALIAS
    alias = classify_waveguide_memory_alias(access1, access2)
    return alias == "NO_ALIAS"

def summarize_waveguide_memory_alias_report(accesses: List[Dict[str, Any]], checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Serializes memory range and alias analysis metadata into a summary dict.
    """
    no_alias = sum(1 for c in checks if c.get("alias") == "NO_ALIAS")
    must_alias = sum(1 for c in checks if c.get("alias") == "MUST_ALIAS")
    may_alias = sum(1 for c in checks if c.get("alias") == "MAY_ALIAS")
    unknown_alias = sum(1 for c in checks if c.get("alias") == "UNKNOWN_ALIAS")
    
    return {
        "total_memory_accesses": len(accesses),
        "checks_performed": len(checks),
        "no_alias_count": no_alias,
        "must_alias_count": must_alias,
        "may_alias_count": may_alias,
        "unknown_alias_count": unknown_alias,
        "reorder_safe_count": sum(1 for c in checks if c.get("reorder_safe", False))
    }

def get_instruction_memory_alias_metadata(inst: Any, pc: int, clean_instructions: List[Any], enable_memory_alias_analysis: bool, width: int) -> Optional[Dict[str, Any]]:
    """
    Constructs memory alias metadata for a trace step.
    """
    if not enable_memory_alias_analysis:
        return {
            "memory_alias_analysis_enabled": False,
            "memory_reorder_safe": False,
        }
        
    access = build_waveguide_memory_access(inst, pc, width_default=width)
    if access is None:
        return None
        
    if access.get("is_barrier"):
        return {
            "memory_alias_analysis_enabled": True,
            "memory_reorder_safe": False,
            "skip_reason": access.get("barrier_reason")
        }
        
    # Compare with other instructions in the program
    all_other_accesses = []
    for other_pc, other_inst in enumerate(clean_instructions):
        if other_pc != pc:
            other_access = build_waveguide_memory_access(other_inst, other_pc, width_default=width)
            if other_access is not None:
                all_other_accesses.append(other_access)
                
    reorder_safe = True
    alias_classification = "NO_ALIAS"
    
    for other in all_other_accesses:
        # RAR is safe
        if access["access_kind"] == "read" and other["access_kind"] == "read":
            continue
        alias = classify_waveguide_memory_alias(access, other)
        if alias != "NO_ALIAS":
            reorder_safe = False
            alias_classification = alias
            break
            
    return {
        "memory_alias_analysis_enabled": True,
        "memory_accesses": [access],
        "alias_classification": alias_classification,
        "memory_reorder_safe": reorder_safe,
        "shard_id": access["shard_id"],
        "range_start": access["range_start"],
        "range_end": access["range_end"],
    }
