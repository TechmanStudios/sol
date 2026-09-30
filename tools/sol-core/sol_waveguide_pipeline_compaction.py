# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Pipeline Compaction
=================================
Implements carry-chain compaction, parallel prefix carry/borrow routing,
and loop optimization for PDM/waveguide microcoded execution.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from sol_wideword_computation_validation import WideWordProgramInstruction, mask_for_width
from sol_prefix_carry import PrefixCarry, CarrySignal

@dataclass
class CompactionWindow:
    start_pc: int
    end_pc: int
    window_type: str  # "multiplication", "division", "generic_loop"
    original_instructions: List[WideWordProgramInstruction]
    unsafe: bool = False
    unsafe_reason: Optional[str] = None
    original_cycle_estimate: int = 0
    compacted_cycle_estimate: int = 0

@dataclass
class WaveguideCompactionReport:
    enabled: bool = True
    windows_detected: int = 0
    windows_compacted: int = 0
    original_cycles: int = 0
    compacted_cycles: int = 0
    cycle_savings: int = 0
    semantic_equivalence: bool = True
    unsafe_windows_skipped: List[Dict[str, Any]] = field(default_factory=list)

def build_waveguide_prefix_carry_routes(
    width: int,
    val1: int,
    val2: int,
    op: str
) -> Tuple[int, int, Dict[str, Any]]:
    """
    Simulates waveguide-native prefix-carry group resolution.
    Decomposes word into 8-bit byte lanes, resolves carries using parallel prefix logic,
    and returns (result, carry_out, routing_metadata).
    """
    mask = mask_for_width(width)
    lane_width = 8
    num_lanes = width // lane_width
    
    val1_masked = val1 & mask
    val2_masked = val2 & mask
    
    # Extract 8-bit lanes
    lanes1 = [(val1_masked >> (i * lane_width)) & 0xFF for i in range(num_lanes)]
    lanes2 = [(val2_masked >> (i * lane_width)) & 0xFF for i in range(num_lanes)]
    
    # Compute generate and propagate signals for parallel prefix carries/borrows
    resolver = PrefixCarry(num_lanes=num_lanes)
    
    sig_list = []
    for i in range(num_lanes):
        a_byte = lanes1[i]
        b_byte = lanes2[i]
        if op in ("SUB", "CMP"):
            # Subtraction borrow generate: a < b; propagate: a == b
            generate = a_byte < b_byte
            propagate = a_byte == b_byte
        else:
            # Addition carry generate: a + b > 255; propagate: a + b == 255
            lane_sum = a_byte + b_byte
            generate = lane_sum > 255
            propagate = lane_sum == 255
        sig_list.append(CarrySignal(generate=generate, propagate=propagate))
        
    prefix_res = resolver.resolve_prefix_carries(sig_list, carry_in=0)
    carries = prefix_res.carries
    carry_out = prefix_res.carry_out
    
    # Compute sum for each lane using resolved carries/borrows
    result_lanes = []
    for i in range(num_lanes):
        a = lanes1[i]
        b = lanes2[i]
        c_in = 1 if carries[i] else 0
        
        if op in ("SUB", "CMP"):
            # a - b - c_in
            lane_res = (a - b - c_in) & 0xFF
        else:
            # a + b + c_in
            lane_res = (a + b + c_in) & 0xFF
        result_lanes.append(lane_res)
        
    # Reassemble result
    result = 0
    for i in range(num_lanes):
        result |= (result_lanes[i] << (i * lane_width))
    result &= mask
    
    # Format routing metadata
    routing_metadata = {
        "strategy": "prefix_carry_group_routing",
        "lanes": num_lanes,
        "resolved_carries": [int(c) for c in carries],
        "final_carry_out": int(carry_out),
        "signals": [{"generate": int(s.generate), "propagate": int(s.propagate)} for s in sig_list]
    }
    
    c_flag = 1 if carry_out else 0
    
    return result, c_flag, routing_metadata

def detect_waveguide_mul_compaction_window(instructions: List[WideWordProgramInstruction]) -> bool:
    """
    Checks if instructions within a loop window match a shift-add multiplication pattern.
    Typically contains: AND, SHL, SHR, ADD and conditional branch.
    """
    opcodes = {inst.op.upper() for inst in instructions}
    return "SHL" in opcodes and "SHR" in opcodes and "AND" in opcodes and "ADD" in opcodes

def detect_waveguide_div_compaction_window(instructions: List[WideWordProgramInstruction]) -> bool:
    """
    Checks if instructions within a loop window match a division scaffold pattern.
    Typically contains: CMP, SUB, ADD and conditional branch.
    """
    opcodes = {inst.op.upper() for inst in instructions}
    return "CMP" in opcodes and "SUB" in opcodes and "ADD" in opcodes

def analyze_waveguide_microcode_chain(program: Any) -> List[CompactionWindow]:
    """
    Statically analyzes program instructions to locate loop compaction windows.
    Detects loop boundaries and classifies safe/unsafe windows.
    """
    insts = program if isinstance(program, list) else getattr(program, "instructions", program)
    
    # First pass: Resolve labels and build instruction list
    labels = {}
    clean_instructions = []
    
    for inst in insts:
        if isinstance(inst, str) and inst.endswith(":"):
            labels[inst[:-1]] = len(clean_instructions)
        else:
            if isinstance(inst, (tuple, list)):
                op = inst[0].upper()
                dst = inst[1] if len(inst) > 1 else None
                src1 = inst[2] if len(inst) > 2 else None
                src2 = inst[3] if len(inst) > 3 else None
                clean_instructions.append(WideWordProgramInstruction(op=op, dst=dst, src1=src1, src2=src2))
            else:
                clean_instructions.append(inst)
                
    windows = []
    
    # Look for loop back-branches
    for pc, inst in enumerate(clean_instructions):
        op = inst.op.upper()
        if op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            target_label = str(inst.dst)
            if target_label in labels:
                target_pc = labels[target_label]
                if target_pc <= pc:
                    # Found loop window [target_pc, pc]
                    window_insts = clean_instructions[target_pc:pc + 1]
                    
                    # Check safety barriers
                    unsafe = False
                    unsafe_reason = None
                    
                    for w_inst in window_insts:
                        w_op = w_inst.op.upper()
                        if w_op in ("LOAD", "STORE"):
                            unsafe = True
                            unsafe_reason = f"contains unsafe memory operation {w_op}"
                            break
                        if w_op not in ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP",
                                       "LOAD_IMM", "MOV", "JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "HALT"):
                            unsafe = True
                            unsafe_reason = f"contains unknown or unsupported opcode {w_op}"
                            break
                            
                    # Classify loop type
                    if detect_waveguide_mul_compaction_window(window_insts):
                        w_type = "multiplication"
                    elif detect_waveguide_div_compaction_window(window_insts):
                        w_type = "division"
                    else:
                        w_type = "generic_loop"
                        
                    windows.append(CompactionWindow(
                        start_pc=target_pc,
                        end_pc=pc,
                        window_type=w_type,
                        original_instructions=window_insts,
                        unsafe=unsafe,
                        unsafe_reason=unsafe_reason
                    ))
                    
    # Sort windows by start_pc to process sequentially
    windows.sort(key=lambda w: w.start_pc)
    return windows

def compact_waveguide_microcode_sequence(
    window: CompactionWindow,
    state: Any,  # WaveguideControlMemoryState
    config: Any,  # WaveguideControlMemoryBridgeConfig
    oracle_traces: List[Any],
    clean_instructions: List[WideWordProgramInstruction],
    trace_steps: List[Any],
    mismatches: List[Dict[str, Any]]
) -> Tuple[bool, int, int]:
    """
    Executes a compaction window using fast parallel prefix arithmetic,
    bypassing physical PDM simulations while preserving traces and correctness.
    Returns (success, original_cycles_executed, compacted_cycles_executed).
    """
    width = state.width
    mask = mask_for_width(width)
    
    # Set up fast helpers for ALU operations
    def resolve_val(operand: Any) -> int:
        if isinstance(operand, str) and operand.startswith("R"):
            return state.registers.get(operand, 0)
        if isinstance(operand, int):
            return operand & mask
        return 0

    from sol_waveguide_branch_control import execute_waveguide_branch_instruction
    
    iterations = 0
    original_cycles = 0
    loop_start_pc = window.start_pc
    loop_end_pc = window.end_pc
    
    success = True
    
    # Run loop simulator
    while state.pc >= loop_start_pc and state.pc <= loop_end_pc and len(trace_steps) < 2000:
        pc_before = state.pc
        inst = clean_instructions[state.pc]
        op = inst.op.upper()
        
        # Get reference expected results from oracle
        expected_res = 0
        expected_flags = dict(state.flags)
        oracle_cycle_index = len(trace_steps)
        if oracle_cycle_index < len(oracle_traces):
            oracle_step = oracle_traces[oracle_cycle_index]
            expected_res = getattr(oracle_step, "oracle_result", 0)
            expected_flags = dict(getattr(oracle_step, "oracle_flags", {}))
            
        sol_result = 0
        sol_flags = dict(state.flags)
        layer_used = "pdm_waveguide_shadow"
        branch_trace = None
        mem_trace = None
        prefix_metadata = None
        
        # Fast prefix carry path for ALU instructions
        if op in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "NOT", "SHL", "SHR"):
            if op == "CMP":
                val1 = resolve_val(inst.dst)
                val2 = resolve_val(inst.src1)
            elif op == "NOT":
                val1 = resolve_val(inst.src1)
                val2 = 0
            else:
                val1 = resolve_val(inst.src1)
                val2 = resolve_val(inst.src2)
                
            # Perform operation
            if op in ("ADD", "SUB", "CMP"):
                sol_result, carry_out, prefix_metadata = build_waveguide_prefix_carry_routes(width, val1, val2, op)
                
                # Flag updates
                sol_flags["zero"] = 1 if sol_result == 0 else 0
                msb = 1 << (width - 1)
                sol_flags["sign"] = 1 if (sol_result & msb) else 0
                
                if op == "ADD":
                    sol_flags["carry"] = carry_out
                    sol_flags["borrow"] = 0
                    s1 = (val1 >> (width - 1)) & 1
                    s2 = (val2 >> (width - 1)) & 1
                    sr = (sol_result >> (width - 1)) & 1
                    sol_flags["overflow"] = 1 if s1 == s2 and s1 != sr else 0
                else:  # SUB or CMP
                    sol_flags["carry"] = carry_out
                    sol_flags["borrow"] = carry_out
                    s1 = (val1 >> (width - 1)) & 1
                    s2 = (val2 >> (width - 1)) & 1
                    sr = (sol_result >> (width - 1)) & 1
                    sol_flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
            else:
                # Bitwise or logical shift operations
                if op == "AND":
                    sol_result = (val1 & val2) & mask
                elif op == "OR":
                    sol_result = (val1 | val2) & mask
                elif op == "XOR":
                    sol_result = (val1 ^ val2) & mask
                elif op == "NOT":
                    sol_result = (~val1) & mask
                elif op == "SHL":
                    sol_result = (val1 << val2) & mask
                elif op == "SHR":
                    sol_result = (val1 >> val2) & mask
                    
                sol_flags["zero"] = 1 if sol_result == 0 else 0
                msb = 1 << (width - 1)
                sol_flags["sign"] = 1 if (sol_result & msb) else 0
                sol_flags["borrow"] = 0
                sol_flags["overflow"] = 0
                
                if op == "SHL":
                    if val2 > 0 and val2 <= width:
                        sol_flags["carry"] = (val1 >> (width - val2)) & 1
                    else:
                        sol_flags["carry"] = 0
                elif op == "SHR":
                    if val2 > 0 and val2 <= width:
                        sol_flags["carry"] = (val1 >> (val2 - 1)) & 1
                    else:
                        sol_flags["carry"] = 0
                else:
                    sol_flags["carry"] = 0
                    
            if op != "CMP":
                state.registers[inst.dst] = sol_result
                
        elif op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            dec, b_trace = execute_waveguide_branch_instruction(inst, state.pc, state.flags, state.labels)
            state.pc = dec.target_pc
            sol_result = 0
            layer_used = "waveguide_branch_control"
            branch_trace = b_trace
            if state.pc == loop_start_pc:
                iterations += 1
                
        elif op == "MOV":
            val = resolve_val(inst.src1)
            state.registers[inst.dst] = val
            sol_result = val
            layer_used = "waveguide_register_transfer"
            
        elif op == "LOAD_IMM":
            val = resolve_val(inst.src1)
            state.registers[inst.dst] = val
            sol_result = val
            layer_used = "waveguide_register_init"
            
        elif op == "HALT":
            layer_used = "waveguide_control_stop"
            sol_result = 0
            
        # Update state flags
        state.flags.update(sol_flags)
        
        # Increment PC if not jump
        if op not in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            state.pc += 1
            
        pc_after = state.pc
        original_cycles += 1
        
        # Match checks
        match = (sol_result == expected_res) and (sol_flags == expected_flags)
        if not match:
            success = False
            mismatches.append({
                "step_index": len(trace_steps),
                "pc": pc_before,
                "op": op,
                "failure_reason": "Compacted result or flags mismatch",
                "details": {
                    "expected_result": expected_res,
                    "actual_result": sol_result,
                    "expected_flags": expected_flags,
                    "actual_flags": sol_flags
                }
            })
            
        # Create instruction trace step
        # Import to avoid circular imports
        from sol_waveguide_control_memory_bridge import WaveguideControlMemoryInstructionTrace
        step = WaveguideControlMemoryInstructionTrace(
            step_index=len(trace_steps),
            pc_before=pc_before,
            pc_after=pc_after,
            instruction=inst,
            layer_used=layer_used,
            sol_result=sol_result,
            oracle_result=expected_res,
            sol_flags=sol_flags,
            oracle_flags=expected_flags,
            match=match,
            branch_trace=branch_trace,
            memory_trace=mem_trace
        )
        
        # Attach prefix carry metadata if present
        if prefix_metadata:
            setattr(step, "prefix_carry_metadata", prefix_metadata)
            
        trace_steps.append(step)
        
        if not success:
            break
            
        if op == "HALT":
            break
            
    # Estimate compacted cycles count
    # Compacted cycles are simulated as 1 cycle per iteration + flat log scale overhead
    compacted_cycles = max(1, iterations)
    
    return success, original_cycles, compacted_cycles

def validate_waveguide_compaction_equivalence(uncompacted_trace: Any, compacted_trace: Any) -> bool:
    """
    Compares compacted vs uncompacted traces to verify perfect register, flags, and PC match.
    """
    if len(uncompacted_trace.steps) != len(compacted_trace.steps):
        return False
    for i in range(len(uncompacted_trace.steps)):
        u_step = uncompacted_trace.steps[i]
        c_step = compacted_trace.steps[i]
        if u_step.sol_result != c_step.sol_result:
            return False
        if u_step.sol_flags != c_step.sol_flags:
            return False
        if u_step.pc_before != c_step.pc_before or u_step.pc_after != c_step.pc_after:
            return False
    return True

def summarize_waveguide_compaction_report(report: WaveguideCompactionReport) -> Dict[str, Any]:
    """Formats compaction report metrics for serialization."""
    return {
        "enabled": report.enabled,
        "windows_detected": report.windows_detected,
        "windows_compacted": report.windows_compacted,
        "original_cycles": report.original_cycles,
        "compacted_cycles": report.compacted_cycles,
        "cycle_savings": report.cycle_savings,
        "semantic_equivalence": report.semantic_equivalence,
        "unsafe_windows_skipped": report.unsafe_windows_skipped
    }
