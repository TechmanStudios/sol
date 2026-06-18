# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Channel Dependency Analysis Module
===============================================
Implements deterministic, static channel hazard detection and access parsing
for v1 channel operations in the scoreboard scheduler.
"""

from typing import List, Dict, Any, Tuple, Optional

def build_waveguide_channel_access(
    inst: Any,
    pc: int,
    v1_lowering_metadata: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Parses channel read/write sets and register reads/writes for a lowered channel instruction.
    """
    if not v1_lowering_metadata:
        return None

    # Find the corresponding lowered candidate metadata for this V0 instruction PC
    meta = None
    for m in v1_lowering_metadata:
        if pc in m.get("v0_pc_range", []):
            meta = m
            break

    if not meta:
        return None

    op = meta.get("candidate_opcode")
    if op not in ("WG_CHAN_FENCE", "WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE"):
        return None

    v1_inst = meta.get("original_instruction_obj")
    if not v1_inst:
        return None

    reads_channels = []
    writes_channels = []
    reads_regs = []
    writes_regs = []
    is_global_barrier = False
    barrier_reason = None

    def resolve_static_channel(operand: Any) -> Any:
        if isinstance(operand, int):
            return operand
        if isinstance(operand, str):
            if operand.startswith("R"):
                return operand  # Unresolved register
            try:
                return int(operand)
            except ValueError:
                return operand
        return operand

    if op == "WG_CHAN_FENCE":
        is_global_barrier = True
        barrier_reason = "channel_fence"

    elif op == "WG_CHAN_SEND":
        ch = resolve_static_channel(v1_inst.dst)
        writes_channels.append(ch)
        if isinstance(ch, str) and ch.startswith("R"):
            reads_regs.append(ch)

        src = v1_inst.src1
        if isinstance(src, str) and src.startswith("R"):
            reads_regs.append(src)

    elif op == "WG_CHAN_RECV":
        dst = v1_inst.dst
        if isinstance(dst, str) and dst.startswith("R"):
            writes_regs.append(dst)

        ch = resolve_static_channel(v1_inst.src1)
        reads_channels.append(ch)
        if isinstance(ch, str) and ch.startswith("R"):
            reads_regs.append(ch)

    elif op == "WG_CHAN_ROUTE":
        dst_ch = resolve_static_channel(v1_inst.dst)
        writes_channels.append(dst_ch)
        if isinstance(dst_ch, str) and dst_ch.startswith("R"):
            reads_regs.append(dst_ch)

        src_ch = resolve_static_channel(v1_inst.src1)
        reads_channels.append(src_ch)
        if isinstance(src_ch, str) and src_ch.startswith("R"):
            reads_regs.append(src_ch)

        mask_val = v1_inst.src2
        if isinstance(mask_val, str) and mask_val.startswith("R"):
            reads_regs.append(mask_val)

    return {
        "pc": pc,
        "opcode": op,
        "reads_channels": reads_channels,
        "writes_channels": writes_channels,
        "reads_registers": list(set(reads_regs)),
        "writes_registers": list(set(writes_regs)),
        "is_channel_barrier": False,
        "is_global_barrier": is_global_barrier,
        "barrier_reason": barrier_reason
    }

def build_waveguide_channel_dependency_record(access_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Wraps access list into a dependency record.
    """
    return {
        "access_list": access_list,
        "has_global_barrier": any(a.get("is_global_barrier", False) for a in access_list)
    }

def classify_waveguide_channel_hazard(h1: Dict[str, Any], h2: Dict[str, Any]) -> str:
    """
    Classifies hazard between two channel operations.
    """
    if h1.get("is_global_barrier") or h2.get("is_global_barrier"):
        return "CHANNEL_GLOBAL_FENCE"

    h1_channels = h1.get("reads_channels", []) + h1.get("writes_channels", [])
    h2_channels = h2.get("reads_channels", []) + h2.get("writes_channels", [])

    # Check unresolved/dynamic channel IDs (registers)
    for ch in h1_channels + h2_channels:
        if isinstance(ch, str) and ch.startswith("R"):
            return "CHANNEL_UNKNOWN"
        if not isinstance(ch, int) or not (0 <= ch < 8):
            return "CHANNEL_UNKNOWN"

    # Check register conflicts (destination or read conflicts from receives/sends)
    h1_writes = set(h1.get("writes_registers", []))
    h2_writes = set(h2.get("writes_registers", []))
    h1_reads = set(h1.get("reads_registers", []))
    h2_reads = set(h2.get("reads_registers", []))

    if h1_writes.intersection(h2_writes):
        return "CHANNEL_UNKNOWN"
    if h1_writes.intersection(h2_reads) or h1_reads.intersection(h2_writes):
        return "CHANNEL_UNKNOWN"

    # Check channel overlap
    h1_reads_ch = set(h1.get("reads_channels", []))
    h1_writes_ch = set(h1.get("writes_channels", []))
    h2_reads_ch = set(h2.get("reads_channels", []))
    h2_writes_ch = set(h2.get("writes_channels", []))

    # RAW
    if h1_writes_ch.intersection(h2_reads_ch):
        return "CHANNEL_RAW"
    # WAR
    if h1_reads_ch.intersection(h2_writes_ch):
        return "CHANNEL_WAR"
    # WAW
    if h1_writes_ch.intersection(h2_writes_ch):
        return "CHANNEL_WAW"
    # Read/Read conflict (forbidden for channel operations batching to avoid non-determinism)
    if h1_reads_ch.intersection(h2_reads_ch):
        return "CHANNEL_ROUTE_CONFLICT"

    return "NO_CHANNEL_HAZARD"

def analyze_waveguide_channel_dependencies(h1: Dict[str, Any], h2: Dict[str, Any]) -> str:
    """
    Analyzes dependency between two instruction access records.
    """
    return classify_waveguide_channel_hazard(h1, h2)

def validate_waveguide_channel_batch_safety(access_list: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Validates that a list of channel accesses scheduled in the same wavefront is safe.
    """
    for i in range(len(access_list)):
        for j in range(i + 1, len(access_list)):
            hazard = classify_waveguide_channel_hazard(access_list[i], access_list[j])
            if hazard != "NO_CHANNEL_HAZARD":
                return False, f"Hazard {hazard} between PC {access_list[i]['pc']} and PC {access_list[j]['pc']}"
    return True, ""

def summarize_waveguide_channel_dependency_report(access_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarizes channel dependency characteristics for a program block.
    """
    global_barrier_count = sum(1 for a in access_list if a.get("is_global_barrier", False))
    send_count = sum(1 for a in access_list if a.get("opcode") == "WG_CHAN_SEND")
    recv_count = sum(1 for a in access_list if a.get("opcode") == "WG_CHAN_RECV")
    route_count = sum(1 for a in access_list if a.get("opcode") == "WG_CHAN_ROUTE")
    
    return {
        "channel_ops_analyzed": len(access_list),
        "global_barriers": global_barrier_count,
        "sends": send_count,
        "recvs": recv_count,
        "routes": route_count
    }
