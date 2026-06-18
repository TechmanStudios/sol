# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Branch-Diamond Predication Module
===============================================
Detects conditional branch-diamonds, performs safety checks, and lowers safe
diamonds into deterministic predicated conditional-select plans.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

@dataclass
class PredicatedDiamond:
    id: int
    diamond_type: str  # "skip" or "if_else"
    cond_pc: int
    cond_instruction: Any
    target_pc: int
    then_pc_start: int
    then_pc_end: int  # inclusive
    target_end_pc: int
    else_pc_start: Optional[int] = None
    else_pc_end: Optional[int] = None
    registers_written: List[str] = field(default_factory=list)

def are_flags_externally_visible(target_end: int, clean_instructions: List[Any]) -> bool:
    """
    Checks if CPU status flags written inside the diamond are read before being overwritten.
    """
    for pc in range(target_end, len(clean_instructions)):
        inst = clean_instructions[pc]
        op = inst.op.upper()
        if op in ("JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            return True
        if op in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "NOT", "SHL", "SHR"):
            return False
    return False

def analyze_waveguide_predication_safety(
    clean_instructions: List[Any],
    start_pc: int,
    end_pc: int,
    target_end: int,
    enable_memory_alias_analysis: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates safety of an arm inside a candidate diamond.
    Returns (is_safe, reason_if_unsafe).
    """
    if end_pc < start_pc:
        return True, None
        
    supported_alu_ops = {"MOV", "LOAD_IMM", "ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP"}
    
    for pc in range(start_pc, end_pc + 1):
        inst = clean_instructions[pc]
        if isinstance(inst, str) or not hasattr(inst, "op"):
            continue
        op = inst.op.upper()
        
        if op == "LOAD":
            if not enable_memory_alias_analysis:
                return False, "contains memory operation"
            from sol_waveguide_memory_alias import build_waveguide_memory_access
            mem_access = build_waveguide_memory_access(inst, pc)
            if mem_access is None or mem_access.get("is_barrier"):
                reason = mem_access.get("barrier_reason") if mem_access else "unknown"
                return False, f"contains unsafe memory operation ({reason})"
        elif op == "STORE":
            return False, "contains memory operation (STORE not allowed)"
        elif op == "HALT":
            return False, "contains HALT instruction"
        elif op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            return False, "contains nested branch instruction"
        elif op not in supported_alu_ops and op != "LOAD":
            return False, f"contains unsupported or unknown opcode {op}"
            
        # Check flag visibility
        if op in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "NOT", "SHL", "SHR"):
            if are_flags_externally_visible(target_end, clean_instructions):
                return False, "arm-local flag effects would be externally visible"
                
    return True, None

def detect_waveguide_branch_diamonds(
    clean_instructions: List[Any],
    labels: Dict[str, int],
    enable_memory_alias_analysis: bool = False
) -> Tuple[List[PredicatedDiamond], List[Dict[str, Any]]]:
    """
    Scans clean instructions to identify safe conditional branch diamonds.
    Returns (diamonds, skipped_candidates).
    """
    diamonds = []
    skipped_candidates = []
    pc = 0
    n = len(clean_instructions)
    
    while pc < n:
        inst = clean_instructions[pc]
        op = inst.op.upper()
        
        if op in ("JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            cond_pc = pc
            target_label = str(inst.dst)
            target_pc = labels.get(target_label)
            
            if target_pc is None:
                skipped_candidates.append({"cond_pc": cond_pc, "reason": "unresolved target label"})
                pc += 1
                continue
                
            if target_pc <= cond_pc:
                skipped_candidates.append({"cond_pc": cond_pc, "reason": "backwards loop jump"})
                pc += 1
                continue
                
            if target_pc >= n:
                skipped_candidates.append({"cond_pc": cond_pc, "reason": "out of bounds target"})
                pc += 1
                continue
                
            # 1. Check if Pattern B: if/else diamond
            prev_inst = clean_instructions[target_pc - 1]
            if prev_inst.op.upper() == "JMP":
                jmp_pc = target_pc - 1
                jmp_target_label = str(prev_inst.dst)
                target_end = labels.get(jmp_target_label)
                
                if target_end is not None and target_end > target_pc and target_end <= n:
                    then_start = cond_pc + 1
                    then_end = jmp_pc - 1
                    else_start = target_pc
                    else_end = target_end - 1
                    
                    then_ok, then_err = analyze_waveguide_predication_safety(clean_instructions, then_start, then_end, target_end, enable_memory_alias_analysis)
                    else_ok, else_err = analyze_waveguide_predication_safety(clean_instructions, else_start, else_end, target_end, enable_memory_alias_analysis)
                    
                    if then_ok and else_ok:
                        regs = set()
                        for idx in range(then_start, then_end + 1):
                            d_inst = clean_instructions[idx]
                            if d_inst.dst and isinstance(d_inst.dst, str) and d_inst.dst.startswith("R"):
                                regs.add(d_inst.dst)
                        for idx in range(else_start, else_end + 1):
                            d_inst = clean_instructions[idx]
                            if d_inst.dst and isinstance(d_inst.dst, str) and d_inst.dst.startswith("R"):
                                regs.add(d_inst.dst)
                                
                        diamonds.append(PredicatedDiamond(
                            id=len(diamonds),
                            diamond_type="if_else",
                            cond_pc=cond_pc,
                            cond_instruction=inst,
                            target_pc=target_pc,
                            then_pc_start=then_start,
                            then_pc_end=then_end,
                            else_pc_start=else_start,
                            else_pc_end=else_end,
                            target_end_pc=target_end,
                            registers_written=sorted(list(regs))
                        ))
                        pc = target_end
                        continue
                    else:
                        err_reason = then_err if not then_ok else else_err
                        skipped_candidates.append({"cond_pc": cond_pc, "reason": f"unsafe arms: {err_reason}"})
                        # Do not skip scanning the rest, just advance pc
                        
            # 2. Check if Pattern A: conditional skip
            then_start = cond_pc + 1
            then_end = target_pc - 1
            then_ok, then_err = analyze_waveguide_predication_safety(clean_instructions, then_start, then_end, target_pc, enable_memory_alias_analysis)
            
            if then_ok:
                regs = set()
                for idx in range(then_start, then_end + 1):
                    d_inst = clean_instructions[idx]
                    if d_inst.dst and isinstance(d_inst.dst, str) and d_inst.dst.startswith("R"):
                        regs.add(d_inst.dst)
                        
                diamonds.append(PredicatedDiamond(
                    id=len(diamonds),
                    diamond_type="skip",
                    cond_pc=cond_pc,
                    cond_instruction=inst,
                    target_pc=target_pc,
                    then_pc_start=then_start,
                    then_pc_end=then_end,
                    target_end_pc=target_pc,
                    registers_written=sorted(list(regs))
                ))
                pc = target_pc
                continue
            else:
                skipped_candidates.append({"cond_pc": cond_pc, "reason": f"unsafe arm: {then_err}"})
                
        pc += 1
        
    return diamonds, skipped_candidates

def execute_waveguide_predicated_diamond(
    diamond: PredicatedDiamond,
    state: Any,  # WaveguideControlMemoryState
    config: Any,  # WaveguideControlMemoryBridgeConfig
    oracle_traces: List[Any],
    clean_instructions: List[Any],
    trace_steps: List[Any],
    mismatches: List[Dict[str, Any]]
) -> Tuple[bool, int, int]:
    """
    Executes the predicated diamond and commits state transitions.
    Returns (success, original_cycles, predicated_cycles).
    """
    from sol_waveguide_branch_control import execute_waveguide_branch_instruction
    from sol_waveguide_control_memory_bridge import execute_waveguide_control_memory_instruction
    
    pc_before_diamond = state.pc
    
    # 1. Execute conditional branch condition
    decision, branch_trace = execute_waveguide_branch_instruction(
        diamond.cond_instruction, state.pc, state.flags, state.labels
    )
    taken = decision.taken
    
    # Trace step for conditional branch itself
    expected_res = 0
    expected_flags = dict(state.flags)
    oracle_cycle_index = len(trace_steps)
    if oracle_cycle_index < len(oracle_traces):
        oracle_step = oracle_traces[oracle_cycle_index]
        expected_res = getattr(oracle_step, "oracle_result", 0)
        expected_flags = dict(getattr(oracle_step, "oracle_flags", {}))
        
    # PC flows logically based on condition taken
    pc_after_branch = decision.target_pc
    
    # Select which path commits
    select_then = not taken
    
    # Determine PC ranges for logging in metadata
    then_range = list(range(diamond.then_pc_start, diamond.then_pc_end + 1))
    else_range = list(range(diamond.else_pc_start, diamond.else_pc_end + 1)) if diamond.else_pc_start is not None else []
    
    pred_meta = {
        "predication_enabled": True,
        "diamond_id": f"DIA_{diamond.id}",
        "condition_opcode": diamond.cond_instruction.op.upper(),
        "predicate_value": taken,
        "original_condition_pc": diamond.cond_pc,
        "then_pc_range": then_range,
        "else_pc_range": else_range,
        "merge_pc": diamond.target_end_pc,
        "lowering_strategy": "conditional_select",
        "registers_merged": diamond.registers_written,
        "flags_merged": False,  # Updated below if flags are written
        "memory_effects": False
    }
    
    # Trace step for branch
    from sol_waveguide_control_memory_bridge import WaveguideControlMemoryInstructionTrace
    branch_step = WaveguideControlMemoryInstructionTrace(
        step_index=len(trace_steps),
        pc_before=diamond.cond_pc,
        pc_after=pc_after_branch,
        instruction=diamond.cond_instruction,
        layer_used="waveguide_branch_control",
        sol_result=0,
        oracle_result=expected_res,
        sol_flags=dict(state.flags),
        oracle_flags=expected_flags,
        match=(0 == expected_res) and (state.flags == expected_flags),
        branch_trace=branch_trace,
        memory_trace=None,
        scheduler_metadata=None
    )
    setattr(branch_step, "predication_metadata", pred_meta)
    trace_steps.append(branch_step)
    
    original_cycles = 1
    
    # Run the chosen path (or fall through)
    state.pc = cond_pc_next = diamond.cond_pc + 1
    
    if select_then:
        # Run then-arm instructions
        for idx in range(diamond.then_pc_start, diamond.then_pc_end + 1):
            inst = clean_instructions[idx]
            expected_res = 0
            expected_flags = dict(state.flags)
            oracle_cycle_index = len(trace_steps)
            if oracle_cycle_index < len(oracle_traces):
                oracle_step = oracle_traces[oracle_cycle_index]
                expected_res = getattr(oracle_step, "oracle_result", 0)
                expected_flags = dict(getattr(oracle_step, "oracle_flags", {}))
                
            pc_before_inst = state.pc
            sol_result, layer_used, sol_flags, br_trace, mem_trace = execute_waveguide_control_memory_instruction(state, inst)
            state.flags.update(sol_flags)
            
            # Since ALU/register moves don't redirect PC, state.pc increments
            state.pc += 1
            original_cycles += 1
            
            # Check for flag writes
            if inst.op.upper() in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "NOT", "SHL", "SHR"):
                pred_meta["flags_merged"] = True
                
            match = (sol_result == expected_res) and (state.flags == expected_flags)
            step = WaveguideControlMemoryInstructionTrace(
                step_index=len(trace_steps),
                pc_before=pc_before_inst,
                pc_after=state.pc,
                instruction=inst,
                layer_used=layer_used,
                sol_result=sol_result,
                oracle_result=expected_res,
                sol_flags=dict(state.flags),
                oracle_flags=expected_flags,
                match=match,
                branch_trace=br_trace,
                memory_trace=mem_trace,
                scheduler_metadata=None
            )
            if inst.op.upper() in ("LOAD", "STORE"):
                from sol_waveguide_memory_alias import get_instruction_memory_alias_metadata
                enable_mem = getattr(config, "enable_memory_alias_analysis", True)
                setattr(step, "memory_alias_metadata", get_instruction_memory_alias_metadata(inst, pc_before_inst, clean_instructions, enable_mem, state.width))
            setattr(step, "predication_metadata", pred_meta)
            trace_steps.append(step)
            
        # Run final unconditional JMP if Pattern B
        if diamond.diamond_type == "if_else":
            jmp_inst = clean_instructions[diamond.target_pc - 1]
            expected_res = 0
            expected_flags = dict(state.flags)
            oracle_cycle_index = len(trace_steps)
            if oracle_cycle_index < len(oracle_traces):
                oracle_step = oracle_traces[oracle_cycle_index]
                expected_res = getattr(oracle_step, "oracle_result", 0)
                expected_flags = dict(getattr(oracle_step, "oracle_flags", {}))
                
            pc_before_inst = state.pc
            # Run unconditional JMP
            dec, br_trace = execute_waveguide_branch_instruction(jmp_inst, state.pc, state.flags, state.labels)
            state.pc = dec.target_pc
            original_cycles += 1
            
            step = WaveguideControlMemoryInstructionTrace(
                step_index=len(trace_steps),
                pc_before=pc_before_inst,
                pc_after=state.pc,
                instruction=jmp_inst,
                layer_used="waveguide_branch_control",
                sol_result=0,
                oracle_result=expected_res,
                sol_flags=dict(state.flags),
                oracle_flags=expected_flags,
                match=(0 == expected_res) and (state.flags == expected_flags),
                branch_trace=br_trace,
                memory_trace=None,
                scheduler_metadata=None
            )
            setattr(step, "predication_metadata", pred_meta)
            trace_steps.append(step)
            
    else:
        # select_then is False (taken path)
        if diamond.diamond_type == "skip":
            # Just jump PC to target_pc (skip then-arm)
            state.pc = diamond.target_pc
            # No instructions inside arms executed, JZ was taken
        else:
            # Pattern B: run else-arm instructions
            state.pc = diamond.else_pc_start
            for idx in range(diamond.else_pc_start, diamond.else_pc_end + 1):
                inst = clean_instructions[idx]
                expected_res = 0
                expected_flags = dict(state.flags)
                oracle_cycle_index = len(trace_steps)
                if oracle_cycle_index < len(oracle_traces):
                    oracle_step = oracle_traces[oracle_cycle_index]
                    expected_res = getattr(oracle_step, "oracle_result", 0)
                    expected_flags = dict(getattr(oracle_step, "oracle_flags", {}))
                    
                pc_before_inst = state.pc
                sol_result, layer_used, sol_flags, br_trace, mem_trace = execute_waveguide_control_memory_instruction(state, inst)
                state.flags.update(sol_flags)
                state.pc += 1
                original_cycles += 1
                
                # Check flag writes
                if inst.op.upper() in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "NOT", "SHL", "SHR"):
                    pred_meta["flags_merged"] = True
                    
                match = (sol_result == expected_res) and (state.flags == expected_flags)
                step = WaveguideControlMemoryInstructionTrace(
                    step_index=len(trace_steps),
                    pc_before=pc_before_inst,
                    pc_after=state.pc,
                    instruction=inst,
                    layer_used=layer_used,
                    sol_result=sol_result,
                    oracle_result=expected_res,
                    sol_flags=dict(state.flags),
                    oracle_flags=expected_flags,
                    match=match,
                    branch_trace=br_trace,
                    memory_trace=mem_trace,
                    scheduler_metadata=None
                )
                if inst.op.upper() in ("LOAD", "STORE"):
                    from sol_waveguide_memory_alias import get_instruction_memory_alias_metadata
                    enable_mem = getattr(config, "enable_memory_alias_analysis", True)
                    setattr(step, "memory_alias_metadata", get_instruction_memory_alias_metadata(inst, pc_before_inst, clean_instructions, enable_mem, state.width))
                setattr(step, "predication_metadata", pred_meta)
                trace_steps.append(step)
                
            state.pc = diamond.target_end_pc
            
    # Conditional MUX select cycle count ignores branch controls overhead
    # Cycles equal just the executed instructions count inside the arms (ignoring JZ and JMP overhead)
    # If no instructions are executed (i.e. Pattern A skip taken), cycles = 1 (evaluation overhead).
    predicated_cycles = max(1, original_cycles - (2 if diamond.diamond_type == "if_else" and select_then else 1))
    
    return True, original_cycles, predicated_cycles
