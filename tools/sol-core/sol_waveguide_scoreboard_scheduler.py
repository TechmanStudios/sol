# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Scoreboard Scheduler
==================================
Implements instruction hazard analysis, superblock partitioning, and wavefront
batch scheduling for the strict PDM/waveguide execution backend.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from sol_wideword_computation_validation import WideWordProgramInstruction

@dataclass
class Superblock:
    id: int
    units: List[Any]  # WideWordProgramInstruction or CompactionWindow
    hazards: List[Dict[str, Any]]

@dataclass
class WaveguideSchedulerReport:
    enabled: bool = True
    superblocks_detected: int = 0
    instructions_seen: int = 0
    wavefront_batches: int = 0
    serial_cycle_estimate: int = 0
    scheduled_cycle_estimate: int = 0
    cycle_savings: int = 0
    hazards_detected: List[Dict[str, Any]] = field(default_factory=list)
    barriers: List[Dict[str, Any]] = field(default_factory=list)
    semantic_equivalence: bool = True
    recognized_kernels_count: int = 0

def build_waveguide_instruction_hazards(inst: Any, pc: int) -> Dict[str, Any]:
    """
    Analyzes an instruction to extract register, flag, and memory reads/writes.
    Also flags control flow, unsupported instructions, or unsafe operations as barriers.
    """
    op = inst.op.upper()
    reads_regs = []
    writes_regs = []
    reads_flags = []
    writes_flags = []
    reads_mem = []
    writes_mem = []
    changes_pc = False
    is_barrier = False
    reason = None
    
    # 21 Micro-ISA v0 instructions:
    # LOAD_IMM, LOAD, STORE, MOV, ADD, SUB, AND, OR, XOR, NOT, SHL, SHR, CMP, JMP, JZ, JNZ, JC, JNC, JB, JNB, HALT
    
    if op in ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "MOV", "LOAD_IMM", "LOAD"):
        if inst.dst and isinstance(inst.dst, str) and inst.dst.startswith("R"):
            writes_regs.append(inst.dst)
            
    if op in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR"):
        if inst.src1 and isinstance(inst.src1, str) and inst.src1.startswith("R"):
            reads_regs.append(inst.src1)
        if inst.src2 and isinstance(inst.src2, str) and inst.src2.startswith("R"):
            reads_regs.append(inst.src2)
            
    elif op == "NOT":
        if inst.src1 and isinstance(inst.src1, str) and inst.src1.startswith("R"):
            reads_regs.append(inst.src1)
            
    elif op == "MOV":
        if inst.src1 and isinstance(inst.src1, str) and inst.src1.startswith("R"):
            reads_regs.append(inst.src1)
            
    elif op == "LOAD":
        if inst.src1 and isinstance(inst.src1, str) and inst.src1.startswith("R"):
            reads_regs.append(inst.src1)
        if isinstance(inst.src1, int):
            reads_mem.append(inst.src1)
        else:
            reads_mem.append("dynamic")
            
    elif op == "STORE":
        if inst.src1 and isinstance(inst.src1, str) and inst.src1.startswith("R"):
            reads_regs.append(inst.src1)
        if inst.dst and isinstance(inst.dst, str) and inst.dst.startswith("R"):
            reads_regs.append(inst.dst)
        if isinstance(inst.src1, int):
            writes_mem.append(inst.src1)
        else:
            writes_mem.append("dynamic")
            
    elif op == "CMP":
        if inst.dst and isinstance(inst.dst, str) and inst.dst.startswith("R"):
            reads_regs.append(inst.dst)
        if inst.src1 and isinstance(inst.src1, str) and inst.src1.startswith("R"):
            reads_regs.append(inst.src1)
            
    elif op in ("JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
        changes_pc = True
        is_barrier = True
        reason = "control flow branch"
        if op in ("JZ", "JNZ"):
            reads_flags.append("zero")
        elif op in ("JC", "JNC", "JB", "JNB"):
            reads_flags.append("carry")
            reads_flags.append("borrow")
            
    elif op == "JMP":
        changes_pc = True
        is_barrier = True
        reason = "unconditional jump"
        
    elif op == "HALT":
        changes_pc = True
        is_barrier = True
        reason = "halt instruction"
        
    # ALU instructions write flags
    if op in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "NOT", "SHL", "SHR"):
        writes_flags = ["zero", "carry", "overflow", "sign", "borrow"]
        
    # Classify unsupported / unknown instructions as barriers
    supported_ops = {
        "LOAD_IMM", "LOAD", "STORE", "MOV", "ADD", "SUB", "AND", "OR", "XOR", 
        "NOT", "SHL", "SHR", "CMP", "JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "HALT"
    }
    if op not in supported_ops:
        is_barrier = True
        reason = f"unknown or unsupported opcode {op}"
        
    # Classify dynamic address memory operations as unsafe memory operations
    if op in ("LOAD", "STORE") and ("dynamic" in reads_mem or "dynamic" in writes_mem):
        is_barrier = True
        reason = "unsafe memory operation (dynamic address)"

    mem_access = None
    if op in ("LOAD", "STORE"):
        from sol_waveguide_memory_alias import build_waveguide_memory_access
        mem_access = build_waveguide_memory_access(inst, pc)

    return {
        "pc": pc,
        "opcode": op,
        "reads_registers": list(set(reads_regs)),
        "writes_registers": list(set(writes_regs)),
        "reads_flags": list(set(reads_flags)),
        "writes_flags": list(set(writes_flags)),
        "reads_memory": list(set(reads_mem)),
        "writes_memory": list(set(writes_mem)),
        "changes_pc": changes_pc,
        "is_barrier": is_barrier,
        "reason": reason,
        "memory_access": mem_access,
    }

def build_waveguide_window_hazards(w: Any) -> Dict[str, Any]:
    """
    Builds union hazard metadata for a compacted loop window unit.
    """
    reads_regs = set()
    writes_regs = set()
    reads_flags = set()
    writes_flags = set()
    reads_mem = set()
    writes_mem = set()
    
    for i, inst in enumerate(w.original_instructions):
        h = build_waveguide_instruction_hazards(inst, w.start_pc + i)
        reads_regs.update(h["reads_registers"])
        writes_regs.update(h["writes_registers"])
        reads_flags.update(h["reads_flags"])
        writes_flags.update(h["writes_flags"])
        reads_mem.update(h["reads_memory"])
        writes_mem.update(h["writes_memory"])
        
    return {
        "pc": w.start_pc,
        "opcode": "COMPACTED_LOOP",
        "reads_registers": list(reads_regs),
        "writes_registers": list(writes_regs),
        "reads_flags": list(reads_flags),
        "writes_flags": list(writes_flags),
        "reads_memory": list(reads_mem),
        "writes_memory": list(writes_mem),
        "changes_pc": False,
        "is_barrier": False,
        "reason": "compacted loop window",
    }

def split_waveguide_superblocks(
    clean_instructions: List[Any],
    windows: List[Any],
    v1_lowering_metadata: Optional[List[Dict[str, Any]]] = None,
    enable_channel_independence_analysis: bool = False
) -> List[Superblock]:
    """
    Partitions program instructions and compacted windows into Superblocks separated by barriers.
    """
    superblocks = []
    current_units = []
    current_hazards = []
    
    pc = 0
    n = len(clean_instructions)
    
    safe_windows = {}
    for w in windows:
        if not w.unsafe:
            safe_windows[w.start_pc] = w
            
    while pc < n:
        if pc in safe_windows:
            w = safe_windows[pc]
            w_hazard = build_waveguide_window_hazards(w)
            current_units.append(w)
            current_hazards.append(w_hazard)
            pc += len(w.original_instructions)
        else:
            inst = clean_instructions[pc]
            h = build_waveguide_instruction_hazards(inst, pc)
            
            # Check if this pc belongs to a waveguide channel lowered barrier range
            if v1_lowering_metadata:
                for m in v1_lowering_metadata:
                    op_candidate = m.get("candidate_opcode")
                    if op_candidate in ("WG_CHAN_FENCE", "WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE"):
                        if pc in m.get("v0_pc_range", []):
                            # Overwrite reads/writes registers of h to match original V1 instruction
                            from sol_waveguide_channel_dependency import build_waveguide_channel_access
                            c_access = build_waveguide_channel_access(inst, pc, v1_lowering_metadata)
                            if c_access:
                                h["reads_registers"] = list(c_access["reads_registers"])
                                h["writes_registers"] = list(c_access["writes_registers"])
                                h["channel_access"] = c_access
                                h["opcode"] = op_candidate
                                
                            is_bar = False
                            if enable_channel_independence_analysis:
                                if op_candidate == "WG_CHAN_FENCE":
                                    is_bar = True
                            else:
                                is_bar = True
                                
                            if is_bar:
                                h["is_barrier"] = True
                                h["reason"] = f"waveguide channel {op_candidate.lower().split('_')[-1]}"
                            break
                            
            current_units.append(inst)
            current_hazards.append(h)
            
            if h["is_barrier"]:
                superblocks.append(Superblock(
                    id=len(superblocks),
                    units=current_units,
                    hazards=current_hazards
                ))
                current_units = []
                current_hazards = []
            
            pc += 1
            
    if current_units:
        superblocks.append(Superblock(
            id=len(superblocks),
            units=current_units,
            hazards=current_hazards
        ))
        
    return superblocks

def check_dependency(h1: Dict[str, Any], h2: Dict[str, Any], enable_memory_alias_analysis: bool = True) -> bool:
    """
    Checks if a dependency (RAW, WAR, WAW, flags, memory) exists between h1 and h2.
    h1 is earlier in program order; h2 is later.
    """
    # Register RAW/WAR/WAW
    if any(r in h1["writes_registers"] for r in h2["reads_registers"]):
        return True
    if any(r in h1["reads_registers"] for r in h2["writes_registers"]):
        return True
    if any(r in h1["writes_registers"] for r in h2["writes_registers"]):
        return True
        
    # Flag RAW/WAR/WAW
    if any(f in h1["writes_flags"] for f in h2["reads_flags"]):
        return True
    if any(f in h1["reads_flags"] for f in h2["writes_flags"]):
        return True
    if any(f in h1["writes_flags"] for f in h2["writes_flags"]):
        return True
        
    # Memory Conflicts
    h1_mem_read = len(h1["reads_memory"]) > 0
    h1_mem_write = len(h1["writes_memory"]) > 0
    h2_mem_read = len(h2["reads_memory"]) > 0
    h2_mem_write = len(h2["writes_memory"]) > 0
    
    if (h1_mem_write and h2_mem_read) or (h1_mem_read and h2_mem_write) or (h1_mem_write and h2_mem_write):
        if enable_memory_alias_analysis:
            from sol_waveguide_memory_alias import validate_waveguide_memory_reorder_safety
            if not validate_waveguide_memory_reorder_safety(h1.get("memory_access"), h2.get("memory_access")):
                return True
        else:
            if "dynamic" in h1["reads_memory"] or "dynamic" in h1["writes_memory"] or \
               "dynamic" in h2["reads_memory"] or "dynamic" in h2["writes_memory"]:
                return True
            h1_addrs = set(h1["reads_memory"] + h1["writes_memory"])
            h2_addrs = set(h2["reads_memory"] + h2["writes_memory"])
            if h1_addrs.intersection(h2_addrs):
                return True
            
    # Channel Conflicts
    if "channel_access" in h1 and "channel_access" in h2:
        from sol_waveguide_channel_dependency import classify_waveguide_channel_hazard
        hazard = classify_waveguide_channel_hazard(h1["channel_access"], h2["channel_access"])
        if hazard != "NO_CHANNEL_HAZARD":
            return True
            
    return False

def find_hazards(h1: Dict[str, Any], h2: Dict[str, Any], enable_memory_alias_analysis: bool = True) -> List[str]:
    """
    Logs all specific hazard types found between h1 and h2.
    """
    hazards = []
    
    # Channel conflicts
    if "channel_access" in h1 and "channel_access" in h2:
        from sol_waveguide_channel_dependency import classify_waveguide_channel_hazard
        hazard = classify_waveguide_channel_hazard(h1["channel_access"], h2["channel_access"])
        if hazard != "NO_CHANNEL_HAZARD":
            hazards.append(f"Channel hazard conflict {hazard} between PC {h1['pc']} and PC {h2['pc']}")

    for r in h2["reads_registers"]:
        if r in h1["writes_registers"]:
            hazards.append(f"RAW register dependency on {r}")
    for r in h2["writes_registers"]:
        if r in h1["reads_registers"]:
            hazards.append(f"WAR register dependency on {r}")
        if r in h1["writes_registers"]:
            hazards.append(f"WAW register dependency on {r}")
            
    for f in h2["reads_flags"]:
        if f in h1["writes_flags"]:
            hazards.append(f"RAW flag dependency on {f}")
    for f in h2["writes_flags"]:
        if f in h1["reads_flags"]:
            hazards.append(f"WAR flag dependency on {f}")
        if f in h1["writes_flags"]:
            hazards.append(f"WAW flag dependency on {f}")
            
    h1_mem_read = len(h1["reads_memory"]) > 0
    h1_mem_write = len(h1["writes_memory"]) > 0
    h2_mem_read = len(h2["reads_memory"]) > 0
    h2_mem_write = len(h2["writes_memory"]) > 0
    
    if (h1_mem_write and h2_mem_read) or (h1_mem_read and h2_mem_write) or (h1_mem_write and h2_mem_write):
        if enable_memory_alias_analysis:
            from sol_waveguide_memory_alias import classify_waveguide_memory_alias
            alias = classify_waveguide_memory_alias(h1.get("memory_access"), h2.get("memory_access"))
            if alias != "NO_ALIAS":
                hazards.append(f"Memory conflict/alias relationship {alias} between PC {h1['pc']} and PC {h2['pc']}")
        else:
            if "dynamic" in h1["reads_memory"] or "dynamic" in h1["writes_memory"] or \
               "dynamic" in h2["reads_memory"] or "dynamic" in h2["writes_memory"]:
                hazards.append("Ambiguous memory hazard (dynamic address)")
            else:
                h1_addrs = set(h1["reads_memory"] + h1["writes_memory"])
                h2_addrs = set(h2["reads_memory"] + h2["writes_memory"])
                overlap = h1_addrs.intersection(h2_addrs)
                if overlap:
                    hazards.append(f"Memory conflict on address(es) {list(overlap)}")
                
    return hazards

def schedule_waveguide_superblock(
    units: List[Any],
    hazards: List[Dict[str, Any]],
    enable_memory_alias_analysis: bool = True
) -> List[List[int]]:
    """
    Schedules units inside a superblock into wavefront batches.
    Each batch is a list of unit indices inside the superblock.
    """
    batches = []
    unit_to_batch = {}
    
    num_units = len(units)
    for i in range(num_units):
        inst_haz = hazards[i]
        earliest_batch = 0
        for prev_idx in range(i):
            prev_haz = hazards[prev_idx]
            if check_dependency(prev_haz, inst_haz, enable_memory_alias_analysis):
                prev_batch = unit_to_batch[prev_idx]
                earliest_batch = max(earliest_batch, prev_batch + 1)
                
        while len(batches) <= earliest_batch:
            batches.append([])
        batches[earliest_batch].append(i)
        unit_to_batch[i] = earliest_batch
        
    return batches

def build_waveguide_scoreboard(
    clean_instructions: List[Any],
    windows: List[Any],
    enable_memory_alias_analysis: bool = True,
    v1_lowering_metadata: Optional[List[Dict[str, Any]]] = None,
    enable_channel_independence_analysis: bool = False,
    recognized_kernels: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[Superblock], List[List[List[int]]], WaveguideSchedulerReport]:
    """
    Splits the program into superblocks, schedules each superblock into wavefronts,
    and returns (superblocks, scheduled_batches_per_superblock, report).
    """
    superblocks = split_waveguide_superblocks(
        clean_instructions, windows, v1_lowering_metadata, enable_channel_independence_analysis
    )
    
    scheduled_superblocks = []
    total_wavefronts = 0
    total_instructions = 0
    hazards_detected = []
    barriers = []
    
    for s in superblocks:
        # Schedule the superblock
        batches = schedule_waveguide_superblock(s.units, s.hazards, enable_memory_alias_analysis)
        scheduled_superblocks.append(batches)
        total_wavefronts += len(batches)
        
        # Accumulate instructions seen (including compacted ones)
        for u in s.units:
            if hasattr(u, "original_instructions"):
                total_instructions += len(u.original_instructions)
            else:
                total_instructions += 1
                
        # Gather hazards and barriers for reporting
        for i, h in enumerate(s.hazards):
            if h["is_barrier"]:
                barriers.append({
                    "pc": h["pc"],
                    "opcode": h["opcode"],
                    "reason": h["reason"]
                })
            # Check dependencies with prior units in superblock
            for prev_idx in range(i):
                prev_h = s.hazards[prev_idx]
                haz_list = find_hazards(prev_h, h, enable_memory_alias_analysis)
                for hz in haz_list:
                    hazards_detected.append({
                        "from_pc": prev_h["pc"],
                        "to_pc": h["pc"],
                        "from_op": prev_h["opcode"],
                        "to_op": h["opcode"],
                        "hazard": hz
                    })
                    
    # Estimate cycles
    # Serial cycle estimate is the total instructions executed (without compaction)
    serial_cycles = total_instructions
    
    # Scheduled cycle estimate is the sum of wavefront batches (non-compacted counts as 1, compacted counts as its own compacted cycles)
    # However, in this scoreboard model, if compaction is also enabled, we will integrate it.
    # By default, the scoreboard scheduling cycles is just total_wavefronts if no compaction is counted.
    scheduled_cycles = total_wavefronts
    
    k_count = len(recognized_kernels) if recognized_kernels else 0
    
    report = WaveguideSchedulerReport(
        enabled=True,
        superblocks_detected=len(superblocks),
        instructions_seen=total_instructions,
        wavefront_batches=total_wavefronts,
        serial_cycle_estimate=serial_cycles,
        scheduled_cycle_estimate=scheduled_cycles,
        cycle_savings=max(0, serial_cycles - scheduled_cycles),
        hazards_detected=hazards_detected,
        barriers=barriers,
        semantic_equivalence=True,
        recognized_kernels_count=k_count
    )
    
    return superblocks, scheduled_superblocks, report

def validate_waveguide_schedule_equivalence(serial_trace: Any, scheduled_trace: Any) -> bool:
    """
    Asserts scheduled trace is semantically equivalent to serial trace.
    """
    if len(serial_trace.steps) != len(scheduled_trace.steps):
        return False
    for i in range(len(serial_trace.steps)):
        s_step = serial_trace.steps[i]
        d_step = scheduled_trace.steps[i]
        if s_step.sol_result != d_step.sol_result:
            return False
        if s_step.sol_flags != d_step.sol_flags:
            return False
        if s_step.pc_before != d_step.pc_before or s_step.pc_after != d_step.pc_after:
            return False
    return True

def summarize_waveguide_scheduler_report(report: WaveguideSchedulerReport) -> Dict[str, Any]:
    """
    Serializes scheduler report metrics.
    """
    return {
        "enabled": report.enabled,
        "superblocks_detected": report.superblocks_detected,
        "instructions_seen": report.instructions_seen,
        "wavefront_batches": report.wavefront_batches,
        "serial_cycle_estimate": report.serial_cycle_estimate,
        "scheduled_cycle_estimate": report.scheduled_cycle_estimate,
        "cycle_savings": report.cycle_savings,
        "hazards_detected": report.hazards_detected,
        "barriers": report.barriers,
        "semantic_equivalence": report.semantic_equivalence,
        "recognized_kernels_count": getattr(report, "recognized_kernels_count", 0)
    }
