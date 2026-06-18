# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Channelized Pattern Recognizer Module
===================================================
Scans lowered instruction streams using V1 lowering metadata to detect
safe channel/dataflow motifs, validate safety, and emit kernel descriptors.
"""

from typing import List, Dict, Any, Tuple, Optional
from sol_waveguide_channel_kernel_library import build_waveguide_channel_kernel_descriptor

def is_static_channel(operand: Any) -> bool:
    """
    Checks if a channel operand is a static integer in [0, 7].
    """
    if isinstance(operand, int):
        return 0 <= operand < 8
    if isinstance(operand, str):
        if operand.startswith("R"):
            return False
        try:
            val = int(operand)
            return 0 <= val < 8
        except ValueError:
            return False
    return False

def get_static_channel(operand: Any) -> Optional[int]:
    """
    Converts operand to static integer channel if valid, else returns None.
    """
    if isinstance(operand, int) and 0 <= operand < 8:
        return operand
    if isinstance(operand, str) and not operand.startswith("R"):
        try:
            val = int(operand)
            if 0 <= val < 8:
                return val
        except ValueError:
            pass
    return None

def match_waveguide_channel_parallel_load_kernel(metadata_slice: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Matches N sends on distinct static channels followed by N receives on matching distinct channels.
    """
    n = len(metadata_slice)
    if n < 2 or n % 2 != 0:
        return None
    n_half = n // 2
    
    sends = metadata_slice[:n_half]
    recvs = metadata_slice[n_half:]
    
    if any(m.get("candidate_opcode") != "WG_CHAN_SEND" for m in sends):
        return None
    if any(m.get("candidate_opcode") != "WG_CHAN_RECV" for m in recvs):
        return None
        
    send_channels = []
    send_regs = []
    for s in sends:
        inst = s.get("original_instruction_obj")
        if not inst:
            return None
        ch = get_static_channel(inst.dst)
        if ch is None:
            return None
        send_channels.append(ch)
        if isinstance(inst.src1, str) and inst.src1.startswith("R"):
            send_regs.append(inst.src1)
        else:
            return None
            
    recv_channels = []
    recv_regs = []
    for r in recvs:
        inst = r.get("original_instruction_obj")
        if not inst:
            return None
        ch = get_static_channel(inst.src1)
        if ch is None:
            return None
        recv_channels.append(ch)
        if isinstance(inst.dst, str) and inst.dst.startswith("R"):
            recv_regs.append(inst.dst)
        else:
            return None
            
    if len(set(send_channels)) != n_half or len(set(recv_channels)) != n_half:
        return None
    if len(set(recv_regs)) != n_half:
        return None
    if set(send_channels) != set(recv_channels):
        return None
        
    # Check contiguity
    v0_pcs = []
    for m in metadata_slice:
        v0_pcs.extend(m.get("v0_pc_range", []))
    if not v0_pcs:
        return None
    start_pc = min(v0_pcs)
    end_pc = max(v0_pcs)
    if len(set(v0_pcs)) != end_pc - start_pc + 1:
        return None
        
    return build_waveguide_channel_kernel_descriptor(
        kernel_id="channel_parallel_load",
        pc_range=[start_pc, end_pc],
        input_channels=sorted(list(set(send_channels))),
        output_channels=sorted(list(set(recv_channels))),
        input_registers=sorted(list(set(send_regs))),
        output_registers=sorted(list(set(recv_regs))),
        contains_fence=False
    )

def match_waveguide_channel_fanout_kernel(metadata_slice: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Matches 1 SEND, K ROUTEs from source channel, and K RECVs from destination channels.
    """
    n = len(metadata_slice)
    if n < 3 or n % 2 == 0:
        return None
    k = (n - 1) // 2
    
    send_m = metadata_slice[0]
    routes_m = metadata_slice[1 : k + 1]
    recvs_m = metadata_slice[k + 1 :]
    
    if send_m.get("candidate_opcode") != "WG_CHAN_SEND":
        return None
    if any(m.get("candidate_opcode") != "WG_CHAN_ROUTE" for m in routes_m):
        return None
    if any(m.get("candidate_opcode") != "WG_CHAN_RECV" for m in recvs_m):
        return None
        
    send = send_m.get("original_instruction_obj")
    if not send:
        return None
    src_ch = get_static_channel(send.dst)
    if src_ch is None:
        return None
    if not isinstance(send.src1, str) or not send.src1.startswith("R"):
        return None
    src_reg = send.src1
    
    dst_channels = []
    for rm in routes_m:
        r = rm.get("original_instruction_obj")
        if not r:
            return None
        r_src = get_static_channel(r.src1)
        if r_src != src_ch:
            return None
        r_dst = get_static_channel(r.dst)
        if r_dst is None or r_dst == src_ch:
            return None
        dst_channels.append(r_dst)
        
    if len(set(dst_channels)) != k:
        return None
        
    recv_channels = []
    recv_regs = []
    for rcm in recvs_m:
        rc = rcm.get("original_instruction_obj")
        if not rc:
            return None
        ch = get_static_channel(rc.src1)
        if ch is None or ch == src_ch:
            return None
        recv_channels.append(ch)
        if not isinstance(rc.dst, str) or not rc.dst.startswith("R"):
            return None
        recv_regs.append(rc.dst)
        
    if set(recv_channels) != set(dst_channels):
        return None
    if len(set(recv_regs)) != k:
        return None
        
    # Check contiguity
    v0_pcs = []
    for m in metadata_slice:
        v0_pcs.extend(m.get("v0_pc_range", []))
    if not v0_pcs:
        return None
    start_pc = min(v0_pcs)
    end_pc = max(v0_pcs)
    if len(set(v0_pcs)) != end_pc - start_pc + 1:
        return None
        
    return build_waveguide_channel_kernel_descriptor(
        kernel_id="channel_fanout",
        pc_range=[start_pc, end_pc],
        input_channels=[src_ch],
        output_channels=sorted(list(set(dst_channels))),
        input_registers=[src_reg],
        output_registers=sorted(list(set(recv_regs))),
        contains_fence=False
    )

def match_waveguide_channel_fence_order_kernel(metadata_slice: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Matches 1 SEND, 1 FENCE, and 1 RECV on same channel.
    """
    if len(metadata_slice) != 3:
        return None
    if metadata_slice[0].get("candidate_opcode") != "WG_CHAN_SEND":
        return None
    if metadata_slice[1].get("candidate_opcode") != "WG_CHAN_FENCE":
        return None
    if metadata_slice[2].get("candidate_opcode") != "WG_CHAN_RECV":
        return None
        
    send = metadata_slice[0].get("original_instruction_obj")
    recv = metadata_slice[2].get("original_instruction_obj")
    if not send or not recv:
        return None
        
    ch_send = get_static_channel(send.dst)
    ch_recv = get_static_channel(recv.src1)
    if ch_send is None or ch_recv is None or ch_send != ch_recv:
        return None
        
    if not isinstance(send.src1, str) or not send.src1.startswith("R"):
        return None
    if not isinstance(recv.dst, str) or not recv.dst.startswith("R"):
        return None
        
    # Check contiguity
    v0_pcs = []
    for m in metadata_slice:
        v0_pcs.extend(m.get("v0_pc_range", []))
    if not v0_pcs:
        return None
    start_pc = min(v0_pcs)
    end_pc = max(v0_pcs)
    if len(set(v0_pcs)) != end_pc - start_pc + 1:
        return None
        
    return build_waveguide_channel_kernel_descriptor(
        kernel_id="channel_fence_order",
        pc_range=[start_pc, end_pc],
        input_channels=[ch_send],
        output_channels=[ch_recv],
        input_registers=[send.src1],
        output_registers=[recv.dst],
        contains_fence=True
    )

def match_waveguide_channel_gather_kernel(metadata_slice: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Matches parallel load followed by VEC_PACK or VEC_INSERT sequence.
    """
    n = len(metadata_slice)
    if n < 3:
        return None
        
    for pl_len in range(2, n):
        pl_meta = metadata_slice[:pl_len]
        pl_res = match_waveguide_channel_parallel_load_kernel(pl_meta)
        if not pl_res:
            continue
            
        rem_meta = metadata_slice[pl_len:]
        if not rem_meta:
            continue
            
        is_gather = False
        vec_ops = []
        output_regs = pl_res["output_registers"]
        
        # VEC_PACK check
        if len(rem_meta) == 1 and rem_meta[0].get("candidate_opcode") == "VEC_PACK":
            vp = rem_meta[0].get("original_instruction_obj")
            if vp and isinstance(vp.src2, (tuple, list)):
                if any(r in vp.src2 for r in output_regs):
                    is_gather = True
                    vec_ops.append(rem_meta[0])
                    
        # VEC_INSERT sequence check
        if not is_gather:
            all_inserts = True
            used_inputs = []
            for m in rem_meta:
                if m.get("candidate_opcode") != "VEC_INSERT":
                    all_inserts = False
                    break
                vi = m.get("original_instruction_obj")
                if vi and isinstance(vi.src2, (tuple, list)) and len(vi.src2) == 2:
                    lane_idx, src_scalar = vi.src2
                    if src_scalar in output_regs:
                        used_inputs.append(src_scalar)
                        vec_ops.append(m)
            if all_inserts and len(used_inputs) > 0:
                is_gather = True
                
        if is_gather:
            # Check contiguity
            v0_pcs = []
            for m in metadata_slice[:pl_len + len(vec_ops)]:
                v0_pcs.extend(m.get("v0_pc_range", []))
            if not v0_pcs:
                continue
            start_pc = min(v0_pcs)
            end_pc = max(v0_pcs)
            if len(set(v0_pcs)) != end_pc - start_pc + 1:
                continue
                
            last_inst = vec_ops[-1].get("original_instruction_obj")
            out_regs = [last_inst.dst] if last_inst else pl_res["output_registers"]
            
            return build_waveguide_channel_kernel_descriptor(
                kernel_id="channel_gather",
                pc_range=[start_pc, end_pc],
                input_channels=pl_res["input_channels"],
                output_channels=pl_res["output_channels"],
                input_registers=pl_res["input_registers"],
                output_registers=out_regs,
                contains_fence=False
            )
            
    return None

def match_waveguide_channel_route_chain_kernel(metadata_slice: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Matches 1 SEND, C ROUTEs in chain (ch0 -> ch1 -> ch2), and 1 RECV.
    """
    n = len(metadata_slice)
    if n < 3:
        return None
        
    if metadata_slice[0].get("candidate_opcode") != "WG_CHAN_SEND":
        return None
    for m in metadata_slice[1 : n - 1]:
        if m.get("candidate_opcode") != "WG_CHAN_ROUTE":
            return None
    if metadata_slice[-1].get("candidate_opcode") != "WG_CHAN_RECV":
        return None
        
    send = metadata_slice[0].get("original_instruction_obj")
    routes = [m.get("original_instruction_obj") for m in metadata_slice[1 : n - 1]]
    recv = metadata_slice[-1].get("original_instruction_obj")
    if not send or any(not r for r in routes) or not recv:
        return None
        
    src_ch = get_static_channel(send.dst)
    if src_ch is None:
        return None
        
    current_ch = src_ch
    for r in routes:
        r_src = get_static_channel(r.src1)
        if r_src != current_ch:
            return None
        r_dst = get_static_channel(r.dst)
        if r_dst is None:
            return None
        current_ch = r_dst
        
    recv_ch = get_static_channel(recv.src1)
    if recv_ch is None or recv_ch != current_ch:
        return None
        
    if not isinstance(send.src1, str) or not send.src1.startswith("R"):
        return None
    if not isinstance(recv.dst, str) or not recv.dst.startswith("R"):
        return None
        
    # Check contiguity
    v0_pcs = []
    for m in metadata_slice:
        v0_pcs.extend(m.get("v0_pc_range", []))
    if not v0_pcs:
        return None
    start_pc = min(v0_pcs)
    end_pc = max(v0_pcs)
    if len(set(v0_pcs)) != end_pc - start_pc + 1:
        return None
        
    return build_waveguide_channel_kernel_descriptor(
        kernel_id="channel_route_chain",
        pc_range=[start_pc, end_pc],
        input_channels=[src_ch],
        output_channels=[recv_ch],
        input_registers=[send.src1],
        output_registers=[recv.dst],
        contains_fence=False
    )

def validate_waveguide_channel_kernel_match(kernel_id: str, metadata_slice: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    Evaluates skipped candidate reasons for a slice matching an opcode signature.
    """
    # Check for dynamic channel IDs
    for m in metadata_slice:
        inst = m.get("original_instruction_obj")
        if not inst:
            continue
        op = m.get("candidate_opcode")
        
        # Check if channel operands are dynamic registers
        if op == "WG_CHAN_SEND":
            if isinstance(inst.dst, str) and inst.dst.startswith("R"):
                return False, "dynamic_channel_id_unsupported"
        elif op == "WG_CHAN_RECV":
            if isinstance(inst.src1, str) and inst.src1.startswith("R"):
                return False, "dynamic_channel_id_unsupported"
        elif op == "WG_CHAN_ROUTE":
            if (isinstance(inst.dst, str) and inst.dst.startswith("R")) or \
               (isinstance(inst.src1, str) and inst.src1.startswith("R")):
                return False, "dynamic_channel_id_unsupported"
                
    # Check contiguity
    v0_pcs = []
    for m in metadata_slice:
        v0_pcs.extend(m.get("v0_pc_range", []))
    if v0_pcs:
        start_pc = min(v0_pcs)
        end_pc = max(v0_pcs)
        if len(set(v0_pcs)) != end_pc - start_pc + 1:
            return False, "non_contiguous_instructions"
            
    # Kernel specific semantic validations
    if kernel_id == "channel_parallel_load":
        # Check mismatched channels/registers
        sends = [m for m in metadata_slice if m.get("candidate_opcode") == "WG_CHAN_SEND"]
        recvs = [m for m in metadata_slice if m.get("candidate_opcode") == "WG_CHAN_RECV"]
        if len(sends) != len(recvs):
            return False, "mismatched_send_recv_channels"
            
        send_chs = [get_static_channel(s["original_instruction_obj"].dst) for s in sends]
        recv_chs = [get_static_channel(r["original_instruction_obj"].src1) for r in recvs]
        if any(c is None for c in send_chs + recv_chs):
            return False, "dynamic_channel_id_unsupported"
            
        if set(send_chs) != set(recv_chs):
            return False, "mismatched_send_recv_channels"
            
        recv_regs = [r["original_instruction_obj"].dst for r in recvs]
        if len(set(recv_regs)) != len(recv_regs):
            return False, "register_write_conflict"
            
    elif kernel_id == "channel_fanout":
        routes = [m for m in metadata_slice if m.get("candidate_opcode") == "WG_CHAN_ROUTE"]
        recvs = [m for m in metadata_slice if m.get("candidate_opcode") == "WG_CHAN_RECV"]
        if len(routes) != len(recvs):
            return False, "mismatched_send_recv_channels"
            
        route_dsts = [get_static_channel(r["original_instruction_obj"].dst) for r in routes]
        recv_chs = [get_static_channel(rc["original_instruction_obj"].src1) for rc in recvs]
        if set(route_dsts) != set(recv_chs):
            return False, "mismatched_send_recv_channels"
            
        recv_regs = [rc["original_instruction_obj"].dst for rc in recvs]
        if len(set(recv_regs)) != len(recv_regs):
            return False, "register_write_conflict"
            
    elif kernel_id == "channel_fence_order":
        send = metadata_slice[0]["original_instruction_obj"]
        recv = metadata_slice[2]["original_instruction_obj"]
        ch_send = get_static_channel(send.dst)
        ch_recv = get_static_channel(recv.src1)
        if ch_send != ch_recv:
            return False, "mismatched_send_recv_channels"
            
    return False, "unknown_matching_failure"

def detect_waveguide_channel_kernels(
    v1_metadata_list: List[Dict[str, Any]],
    enabled: bool = True
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Greedily scans the V1 lowering metadata list to identify contiguous channel kernel matches.
    If disabled, returns empty recognized list but records candidate matches as skipped.
    """
    recognized = []
    skipped = []
    
    n = len(v1_metadata_list)
    start_idx = 0
    
    # Priority ordered matchers
    matchers = [
        ("channel_gather", match_waveguide_channel_gather_kernel),
        ("channel_fanout", match_waveguide_channel_fanout_kernel),
        ("channel_route_chain", match_waveguide_channel_route_chain_kernel),
        ("channel_parallel_load", match_waveguide_channel_parallel_load_kernel),
        ("channel_fence_order", match_waveguide_channel_fence_order_kernel),
    ]
    
    # Opcode signatures to check for skipped candidates
    # parallel load: N sends followed by N receives
    # fanout: 1 send, K routes, K receives
    # fence order: 1 send, 1 fence, 1 receive
    # route chain: 1 send, C routes, 1 receive
    def check_signature(sub_slice: List[Dict[str, Any]]) -> Optional[str]:
        sz = len(sub_slice)
        opcodes = [m.get("candidate_opcode") for m in sub_slice]
        
        # 1. Check fence order
        if sz == 3 and opcodes == ["WG_CHAN_SEND", "WG_CHAN_FENCE", "WG_CHAN_RECV"]:
            return "channel_fence_order"
            
        # 2. Check route chain
        if sz >= 3 and opcodes[0] == "WG_CHAN_SEND" and opcodes[-1] == "WG_CHAN_RECV" and all(op == "WG_CHAN_ROUTE" for op in opcodes[1:-1]):
            return "channel_route_chain"
            
        # 3. Check parallel load
        if sz >= 2 and sz % 2 == 0:
            half = sz // 2
            if all(op == "WG_CHAN_SEND" for op in opcodes[:half]) and all(op == "WG_CHAN_RECV" for op in opcodes[half:]):
                return "channel_parallel_load"
                
        # 4. Check fanout
        if sz >= 3 and sz % 2 == 1:
            k = (sz - 1) // 2
            if opcodes[0] == "WG_CHAN_SEND" and all(op == "WG_CHAN_ROUTE" for op in opcodes[1 : k + 1]) and all(op == "WG_CHAN_RECV" for op in opcodes[k + 1 :]):
                return "channel_fanout"
                
        return None
        
    while start_idx < n:
        match_found = False
        
        # Try finding the longest match at start_idx
        for length in range(n - start_idx, 1, -1):
            sub_slice = v1_metadata_list[start_idx : start_idx + length]
            
            for k_id, matcher_fn in matchers:
                descriptor = matcher_fn(sub_slice)
                if descriptor is not None:
                    if enabled:
                        recognized.append(descriptor)
                    else:
                        skipped.append({
                            "channel_kernel_candidate": k_id,
                            "recognized": False,
                            "skip_reason": "disabled_in_config",
                            "pc_range": descriptor["pc_range"]
                        })
                    start_idx += length
                    match_found = True
                    break
            if match_found:
                break
                
        if match_found:
            continue
            
        # If no match found, check if a signature matches but was skipped due to validation failure
        # Check longest signature at start_idx
        sig_matched = False
        for length in range(n - start_idx, 1, -1):
            sub_slice = v1_metadata_list[start_idx : start_idx + length]
            sig_k_id = check_signature(sub_slice)
            if sig_k_id:
                # Signature matches! It was skipped. Let's find why.
                _, reason = validate_waveguide_channel_kernel_match(sig_k_id, sub_slice)
                v0_pcs = []
                for m in sub_slice:
                    v0_pcs.extend(m.get("v0_pc_range", []))
                st_pc = min(v0_pcs) if v0_pcs else 0
                ed_pc = max(v0_pcs) if v0_pcs else 0
                skipped.append({
                    "channel_kernel_candidate": sig_k_id,
                    "recognized": False,
                    "skip_reason": reason,
                    "pc_range": [st_pc, ed_pc]
                })
                start_idx += length
                sig_matched = True
                break
                
        if sig_matched:
            continue
            
        start_idx += 1
        
    return recognized, skipped

def summarize_waveguide_channel_kernel_recognition_report(
    recognized: List[Dict[str, Any]],
    skipped: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Summarizes results of the pattern recognition pass.
    """
    counts = {}
    for r in recognized:
        counts[r["kernel_id"]] = counts.get(r["kernel_id"], 0) + 1
        
    skipped_reasons = {}
    for s in skipped:
        cand = s["channel_kernel_candidate"]
        reason = s["skip_reason"]
        key = f"{cand}:{reason}"
        skipped_reasons[key] = skipped_reasons.get(key, 0) + 1
        
    return {
        "recognition_enabled": len(recognized) > 0 or any(s.get("skip_reason") != "disabled_in_config" for s in skipped),
        "recognized_count": len(recognized),
        "recognized_distribution": counts,
        "skipped_count": len(skipped),
        "skipped_reasons": skipped_reasons
    }
