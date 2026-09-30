# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
from __future__ import annotations
"""
SOL WideWord Waveguide Program execution adapter.
Provides multi-layer program execution paths (lane_fabric_vm, sequencer_shadow,
pdm_waveguide_shadow, hybrid_shadow) and generates execution traces/reports.
"""

import uuid
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from sol_lane_fabric import LaneFabric
from sol_multilane_sequencer import MultiLaneSequencer
from sol_wideword_instruction import WideWordInstruction
from sol_wideword_computation_validation import (
    WideWordProgramInstruction,
    WideWordProgram,
    WideWordProgramTraceStep,
    WideWordProgramTrace,
    WaveguideProgramExecutionConfig,
    WaveguideProgramExecutionReport,
    WaveguideProgramMismatch,
    format_hex,
    mask_for_width
)

@dataclass
class WaveguideRegisterState:
    registers: Dict[str, int] = field(default_factory=dict)

@dataclass
class WaveguideMemoryState:
    memory: Dict[int, int] = field(default_factory=dict)

@dataclass
class WaveguideFlagState:
    flags: Dict[str, int] = field(default_factory=dict)

@dataclass
class WaveguideProgramAdapter:
    width: int
    config: WaveguideProgramExecutionConfig
    backend: str
    sequencer: MultiLaneSequencer = field(default_factory=MultiLaneSequencer)
    fabric: LaneFabric = field(init=False)

    def __post_init__(self):
        self.fabric = LaneFabric.for_width(self.width)
        self.sequencer.fabric = self.fabric

    def execute_program_strict_backend(self, program: WideWordProgram, backend: str, config: Optional[WaveguideProgramExecutionConfig] = None) -> WaveguideProgramAdapterReport:
        if backend == "pdm_waveguide_microcoded_strict":
            return self.execute_pdm_waveguide_microcoded_program(program, config)
        width = self.width
        mask = mask_for_width(width)
        
        # Set up virtual states
        registers = {f"R{i}": 0 for i in range(16)}
        memory = {}
        flags = {
            "zero": 0,
            "carry": 0,
            "overflow": 0,
            "sign": 0,
            "borrow": 0
        }
        
        trace_steps = []
        mismatches = []
        layers_used = {}
        
        # First pass: Resolve labels
        labels = {}
        clean_instructions = []
        for inst in program.instructions:
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
                    
        pc = 0
        cycles = 0
        max_cycles = 2000
        success = True
        oracle_match = True
        
        while pc < len(clean_instructions) and cycles < max_cycles:
            inst = clean_instructions[pc]
            op = inst.op.upper()
            cycles += 1
            
            pc_before = pc
            registers_before = dict(registers)
            
            # Referenced memory before
            referenced_addr = None
            memory_before_refs = {}
            
            def resolve_val(operand: Any) -> int:
                if isinstance(operand, str) and operand.startswith("R"):
                    return registers.get(operand, 0)
                if isinstance(operand, int):
                    return operand & mask
                return 0
                
            if op in ("LOAD", "STORE"):
                referenced_addr = resolve_val(inst.src1)
                memory_before_refs[referenced_addr] = memory.get(referenced_addr, 0)
                
            operand_a = None
            operand_b = None
            if inst.src1 is not None:
                try:
                    operand_a = resolve_val(inst.src1)
                except Exception:
                    pass
            if inst.src2 is not None:
                try:
                    operand_b = resolve_val(inst.src2)
                except Exception:
                    pass

            if op == "HALT":
                halt_layer = "lane_fabric_vm" if backend in ("lane_fabric_strict", "hybrid_shadow") else "unsupported_instruction"
                if halt_layer == "unsupported_instruction":
                    success = False
                    oracle_match = False
                    mismatches.append(WaveguideProgramMismatch(
                        step_index=len(trace_steps),
                        pc=pc_before,
                        instruction=inst,
                        failure_reason="HALT instruction is unsupported in sequencer or waveguide strict backend",
                        details={"op": "HALT", "backend": backend}
                    ))
                    
                step = WideWordProgramTraceStep(
                    step_index=len(trace_steps),
                    pc_before=pc_before,
                    pc_after=pc_before,
                    instruction=inst,
                    width=width,
                    operand_a=None,
                    operand_b=None,
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags),
                    registers_before=registers_before,
                    registers_after=dict(registers),
                    memory_before_refs=memory_before_refs,
                    memory_after_refs=dict(memory_before_refs),
                    layer_used=halt_layer,
                    waveguide_trace_ref=None,
                    pdm_trace_ref=None,
                    sequencer_trace_ref=None,
                    match=success,
                    failure_reason="Unsupported HALT" if halt_layer == "unsupported_instruction" else None
                )
                trace_steps.append(step)
                layers_used[halt_layer] = layers_used.get(halt_layer, 0) + 1
                break
                
            # Execute instruction using strict method
            state = {
                "registers": registers,
                "memory": memory,
                "flags": flags,
                "pc": pc,
                "labels": labels
            }
            exec_res = self.execute_instruction_strict_backend(inst, backend, state, config)
            
            layer_used = exec_res.layer_used
            layers_used[layer_used] = layers_used.get(layer_used, 0) + 1
            
            # Check for error layers
            if layer_used in ("unavailable", "unsupported_instruction", "unsupported_width",
                              "unsupported_control_flow", "unsupported_memory_op",
                              "demodulation_unavailable", "backend_error"):
                success = False
                oracle_match = False
                mismatches.append(WaveguideProgramMismatch(
                    step_index=len(trace_steps),
                    pc=pc_before,
                    instruction=inst,
                    failure_reason=f"Strict backend error: {layer_used}",
                    details={"op": op, "backend": backend, "layer_used": layer_used}
                ))
                # Add trace step and break
                step = WideWordProgramTraceStep(
                    step_index=len(trace_steps),
                    pc_before=pc_before,
                    pc_after=pc_before,
                    instruction=inst,
                    width=width,
                    operand_a=operand_a,
                    operand_b=operand_b,
                    sol_result=0,
                    oracle_result=exec_res.oracle_result,
                    sol_flags=dict(flags),
                    oracle_flags=dict(exec_res.oracle_flags),
                    registers_before=registers_before,
                    registers_after=dict(registers),
                    memory_before_refs=memory_before_refs,
                    memory_after_refs=dict(memory_before_refs),
                    layer_used=layer_used,
                    waveguide_trace_ref=None,
                    pdm_trace_ref=None,
                    sequencer_trace_ref=None,
                    match=False,
                    failure_reason=f"Strict backend error: {layer_used}"
                )
                trace_steps.append(step)
                break
                
            # Write state changes back to registers/memory/flags
            if op == "LOAD":
                registers[inst.dst] = exec_res.sol_result & mask
            elif op == "STORE":
                memory[referenced_addr] = resolve_val(inst.dst)
            elif op == "MOV":
                registers[inst.dst] = exec_res.sol_result & mask
            elif op in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "NOT"):
                registers[inst.dst] = exec_res.sol_result & mask
                
            # Update flags
            flags.update(exec_res.sol_flags)
            
            # Handle PC jumps
            jumped = False
            if op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
                target = inst.dst
                target_pc = labels[target] if target in labels else int(target)
                
                cond = False
                if op == "JMP":
                    cond = True
                elif op == "JZ":
                    cond = flags["zero"] == 1
                elif op == "JNZ":
                    cond = flags["zero"] == 0
                elif op in ("JC", "JB"):
                    cond = flags["carry"] == 1
                elif op in ("JNC", "JNB"):
                    cond = flags["carry"] == 0
                    
                if cond:
                    pc = target_pc
                    jumped = True
                    
            if not jumped:
                pc += 1
                
            pc_after = pc
            memory_after_refs = {}
            if referenced_addr is not None:
                memory_after_refs[referenced_addr] = memory.get(referenced_addr, 0)
                
            # Check trace step match
            match = exec_res.sol_result == exec_res.oracle_result and exec_res.sol_flags == exec_res.oracle_flags
            failure_reason = None
            if not match:
                success = False
                oracle_match = False
                failure_reason = "Result or flags mismatch"
                mismatches.append(WaveguideProgramMismatch(
                    step_index=len(trace_steps),
                    pc=pc_before,
                    instruction=inst,
                    failure_reason=failure_reason,
                    details={
                        "expected_result_hex": format_hex(exec_res.oracle_result, width),
                        "actual_result_hex": format_hex(exec_res.sol_result, width),
                        "expected_flags": exec_res.oracle_flags,
                        "actual_flags": exec_res.sol_flags
                    }
                ))
                
            step = WideWordProgramTraceStep(
                step_index=len(trace_steps),
                pc_before=pc_before,
                pc_after=pc_after,
                instruction=inst,
                width=width,
                operand_a=operand_a,
                operand_b=operand_b,
                sol_result=exec_res.sol_result,
                oracle_result=exec_res.oracle_result,
                sol_flags=dict(exec_res.sol_flags),
                oracle_flags=dict(exec_res.oracle_flags),
                registers_before=registers_before,
                registers_after=dict(registers),
                memory_before_refs=memory_before_refs,
                memory_after_refs=memory_after_refs,
                layer_used=layer_used,
                waveguide_trace_ref=exec_res.waveguide_trace_ref,
                pdm_trace_ref=exec_res.pdm_trace_ref,
                sequencer_trace_ref=exec_res.sequencer_trace_ref,
                match=match,
                failure_reason=failure_reason
            )
            trace_steps.append(step)
            
        return WaveguideProgramAdapterReport(
            adapter=self,
            trace_steps=trace_steps,
            success=success,
            oracle_match=oracle_match,
            mismatches=mismatches,
            layers_used=layers_used
        )

    def execute_instruction_strict_backend(
        self,
        instruction: WideWordProgramInstruction,
        backend: str,
        state: Any,
        config: Optional[WaveguideProgramExecutionConfig] = None
    ) -> WaveguideInstructionExecution:
        if isinstance(state, dict):
            registers = state.get("registers")
            memory = state.get("memory")
            flags = state.get("flags")
        else:
            registers = getattr(state, "registers")
            memory = getattr(state, "memory")
            flags = getattr(state, "flags")
            
        width = self.width
        op = instruction.op.upper()
        
        # 1. Check width
        if width not in (32, 64):
            return WaveguideInstructionExecution(
                instruction=instruction,
                layer_used="unsupported_width",
                sol_result=0,
                oracle_result=0,
                sol_flags=dict(flags),
                oracle_flags=dict(flags)
            )
            
        is_alu = op in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "NOT", "CMP")
        
        # 2. Check strict backend mapping
        if backend == "lane_fabric_strict":
            return execute_waveguide_instruction(self, instruction, registers, memory, flags)
            
        elif backend == "sequencer_shadow_strict":
            if op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
                return WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="unsupported_control_flow",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
            if op in ("LOAD", "STORE"):
                return WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="unsupported_memory_op",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
            if not is_alu:
                return WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="unsupported_instruction",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
                
            old_backend = self.backend
            self.backend = "sequencer_shadow"
            try:
                res = execute_waveguide_instruction(self, instruction, registers, memory, flags)
                if res.layer_used != "sequencer_shadow":
                    res.layer_used = "unavailable"
            except Exception:
                res = WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="backend_error",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
            finally:
                self.backend = old_backend
            return res
            
        elif backend == "pdm_waveguide_shadow_strict":
            if op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
                return WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="unsupported_control_flow",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
            if op in ("LOAD", "STORE"):
                return WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="unsupported_memory_op",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
            if not is_alu:
                return WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="unsupported_instruction",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
                
            old_backend = self.backend
            self.backend = "pdm_waveguide_shadow"
            try:
                res = execute_waveguide_instruction(self, instruction, registers, memory, flags)
                if res.layer_used != "pdm_waveguide_shadow":
                    res.layer_used = "demodulation_unavailable"
            except Exception:
                res = WaveguideInstructionExecution(
                    instruction=instruction,
                    layer_used="backend_error",
                    sol_result=0,
                    oracle_result=0,
                    sol_flags=dict(flags),
                    oracle_flags=dict(flags)
                )
            finally:
                self.backend = old_backend
            return res
            
        elif backend == "hybrid_shadow":
            return execute_waveguide_instruction(self, instruction, registers, memory, flags)
            
        else:
            return WaveguideInstructionExecution(
                instruction=instruction,
                layer_used="unsupported_instruction",
                sol_result=0,
                oracle_result=0,
                sol_flags=dict(flags),
                oracle_flags=dict(flags)
            )

    def validate_no_backend_fallback(self, trace: WideWordProgramTrace, backend: str) -> bool:
        if backend == "lane_fabric_strict":
            target = "lane_fabric_vm"
        elif backend == "sequencer_shadow_strict":
            target = "sequencer_shadow"
        elif backend == "pdm_waveguide_shadow_strict":
            target = "pdm_waveguide_shadow"
        elif backend == "pdm_waveguide_microcoded_strict":
            return validate_pdm_waveguide_microcoded_no_fallback(trace)
        elif backend == "hybrid_shadow":
            return True
        else:
            return False
            
        for step in trace.steps:
            if step.instruction.op == "HALT":
                continue
            if step.layer_used in ("lane_fabric_vm", "sequencer_shadow", "pdm_waveguide_shadow") and step.layer_used != target:
                return False
        return True

    def classify_backend_unavailable_reason(self, trace_or_error: Any) -> Optional[str]:
        if isinstance(trace_or_error, Exception):
            return "backend_error"
        if hasattr(trace_or_error, "steps"):
            for step in trace_or_error.steps:
                if step.layer_used in (
                    "unavailable", "unsupported_instruction", "unsupported_width",
                    "unsupported_control_flow", "unsupported_memory_op",
                    "demodulation_unavailable", "backend_error"
                ):
                    return step.layer_used
        return None


@dataclass
class WaveguideInstructionExecution:
    instruction: WideWordProgramInstruction
    layer_used: str
    sol_result: int
    oracle_result: int
    sol_flags: Dict[str, int]
    oracle_flags: Dict[str, int]
    waveguide_trace_ref: Optional[str] = None
    pdm_trace_ref: Optional[str] = None
    sequencer_trace_ref: Optional[str] = None


@dataclass
class WaveguideProgramAdapterReport:
    adapter: WaveguideProgramAdapter
    trace_steps: List[WideWordProgramTraceStep] = field(default_factory=list)
    success: bool = True
    oracle_match: bool = True
    mismatches: List[WaveguideProgramMismatch] = field(default_factory=list)
    layers_used: Dict[str, int] = field(default_factory=dict)
    pipeline_compaction_report: Optional[Dict[str, Any]] = None
    scoreboard_scheduler_report: Optional[Dict[str, Any]] = None


def build_waveguide_program_adapter(width: int, config: Optional[WaveguideProgramExecutionConfig] = None, backend: str = "lane_fabric_vm") -> WaveguideProgramAdapter:
    if config is None:
        config = WaveguideProgramExecutionConfig()
    return WaveguideProgramAdapter(width=width, config=config, backend=backend)


def execute_waveguide_instruction(
    adapter: WaveguideProgramAdapter,
    instruction: WideWordProgramInstruction,
    registers: Dict[str, int],
    memory: Dict[int, int],
    flags: Dict[str, int]
) -> WaveguideInstructionExecution:
    """
    Executes a single instruction on the requested adapter backend.
    """
    width = adapter.width
    mask = mask_for_width(width)
    op = instruction.op.upper()
    
    # Determine the target execution layer based on the backend and instruction type
    layer_used = "lane_fabric_vm"
    
    # 1. Resolve operands
    def resolve_val(operand: Any) -> int:
        if isinstance(operand, str) and operand.startswith("R"):
            return registers.get(operand, 0)
        if isinstance(operand, int):
            return operand & mask
        return 0

    if op == "CMP":
        val1 = resolve_val(instruction.dst)
        val2 = resolve_val(instruction.src1)
    elif op == "STORE":
        val1 = resolve_val(instruction.src1) # address
        val2 = resolve_val(instruction.dst)  # value to store
    elif op == "NOT":
        val1 = resolve_val(instruction.src1)
        val2 = 0
    else:
        val1 = resolve_val(instruction.src1)
        val2 = resolve_val(instruction.src2)
    
    sol_result = 0
    carry_out = 0
    waveguide_trace_ref = None
    pdm_trace_ref = None
    sequencer_trace_ref = None
    
    is_alu = op in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "NOT", "CMP")
    
    if adapter.backend == "pdm_waveguide_shadow" and is_alu:
        # Try to execute through PDM/waveguide shadow path
        try:
            seq_op = "SUB_WORD" if op == "CMP" else f"{op}_WORD"
            operands = [val1] if op == "NOT" else [val1, val2]
            
            inst_pdm = WideWordInstruction(
                instruction_id=f"INST_PDM_{uuid.uuid4().hex[:8]}",
                op=seq_op,
                width=width,
                operands=operands,
                lane_count=width // 8,
                dry_run=True
            )
            
            # Simulate waveguide modulation and demodulation
            report_pdm = adapter.sequencer.execute_waveguide_instruction(inst_pdm, dry_run=True, shadow=True)
            
            if report_pdm.oracle_match and report_pdm.passed_gates:
                sol_result = report_pdm.demodulation_result.demodulated_value
                layer_used = "pdm_waveguide_shadow"
                waveguide_trace_ref = report_pdm.reproducibility_hash
                pdm_trace_ref = report_pdm.instruction_id
                sequencer_trace_ref = report_pdm.reproducibility_hash
                
                # Fetch carry flag out if arithmetic
                if op in ("ADD", "SUB", "CMP"):
                    # We can fetch the carry out from the sequencer's reference instruction execution
                    ref_res = adapter.sequencer.execute_instruction(inst_pdm, dry_run=True)
                    carry_out = ref_res.carry_out
            else:
                # If demodulation or gates failed, report unavailable/failure
                layer_used = "unavailable"
        except Exception:
            layer_used = "unavailable"

    elif (adapter.backend in ("sequencer_shadow", "hybrid_shadow", "pdm_waveguide_shadow")) and is_alu and layer_used == "lane_fabric_vm":
        # Fall back to sequencer shadow execution
        try:
            seq_op = "SUB_WORD" if op == "CMP" else f"{op}_WORD"
            operands = [val1] if op == "NOT" else [val1, val2]
            
            inst_seq = WideWordInstruction(
                instruction_id=f"INST_SEQ_{uuid.uuid4().hex[:8]}",
                op=seq_op,
                width=width,
                operands=operands,
                lane_count=width // 8,
                dry_run=True
            )
            res_seq = adapter.sequencer.execute_instruction(inst_seq, dry_run=True)
            if res_seq.passed_gates:
                sol_result = res_seq.result
                carry_out = res_seq.carry_out
                layer_used = "sequencer_shadow"
                sequencer_trace_ref = inst_seq.instruction_id
            else:
                layer_used = "unavailable"
        except Exception:
            layer_used = "unavailable"
            
    elif adapter.backend == "hybrid_shadow" and is_alu:
        # Hybrid try waveguide first, then sequencer, then lane_fabric
        try:
            seq_op = "SUB_WORD" if op == "CMP" else f"{op}_WORD"
            operands = [val1] if op == "NOT" else [val1, val2]
            inst_pdm = WideWordInstruction(
                instruction_id=f"INST_PDM_{uuid.uuid4().hex[:8]}",
                op=seq_op,
                width=width,
                operands=operands,
                lane_count=width // 8,
                dry_run=True
            )
            report_pdm = adapter.sequencer.execute_waveguide_instruction(inst_pdm, dry_run=True, shadow=True)
            if report_pdm.oracle_match and report_pdm.passed_gates:
                sol_result = report_pdm.demodulation_result.demodulated_value
                layer_used = "pdm_waveguide_shadow"
                waveguide_trace_ref = report_pdm.reproducibility_hash
                pdm_trace_ref = report_pdm.instruction_id
                sequencer_trace_ref = report_pdm.reproducibility_hash
                if op in ("ADD", "SUB", "CMP"):
                    ref_res = adapter.sequencer.execute_instruction(inst_pdm, dry_run=True)
                    carry_out = ref_res.carry_out
            else:
                # Try sequencer shadow
                res_seq = adapter.sequencer.execute_instruction(inst_pdm, dry_run=True)
                if res_seq.passed_gates:
                    sol_result = res_seq.result
                    carry_out = res_seq.carry_out
                    layer_used = "sequencer_shadow"
                    sequencer_trace_ref = inst_pdm.instruction_id
                else:
                    layer_used = "lane_fabric_vm"
        except Exception:
            # Fall back to sequencer first, then lane fabric
            try:
                seq_op = "SUB_WORD" if op == "CMP" else f"{op}_WORD"
                operands = [val1] if op == "NOT" else [val1, val2]
                inst_seq = WideWordInstruction(
                    instruction_id=f"INST_SEQ_{uuid.uuid4().hex[:8]}",
                    op=seq_op,
                    width=width,
                    operands=operands,
                    lane_count=width // 8,
                    dry_run=True
                )
                res_seq = adapter.sequencer.execute_instruction(inst_seq, dry_run=True)
                if res_seq.passed_gates:
                    sol_result = res_seq.result
                    carry_out = res_seq.carry_out
                    layer_used = "sequencer_shadow"
                else:
                    layer_used = "lane_fabric_vm"
            except Exception:
                layer_used = "lane_fabric_vm"

    # Support shadow hcam memory recall for LOAD/STORE if sequencer_shadow or pdm_waveguide_shadow is used
    if op in ("LOAD", "STORE") and adapter.backend in ("sequencer_shadow", "pdm_waveguide_shadow", "hybrid_shadow"):
        try:
            # We construct a WideWordInstruction for recall
            mem_op = "LOAD_WORD" if op == "LOAD" else "STORE_WORD"
            addr = val1 # resolved address
            inst_mem = WideWordInstruction(
                instruction_id=f"INST_MEM_{uuid.uuid4().hex[:8]}",
                op=mem_op,
                width=width,
                operands=[addr],
                lane_count=width // 8,
                dry_run=True
            )
            # Execute shadow memory plan and recall
            plan = adapter.sequencer.plan_memory_instruction(inst_mem, dry_run=True, shadow=True)
            if plan is not None:
                layer_used = "sequencer_shadow"
                sequencer_trace_ref = inst_mem.instruction_id
                if op == "LOAD":
                    sol_result = memory.get(addr, 0)
                elif op == "STORE":
                    sol_result = val2
        except Exception:
            pass

    # 2. Execute on LaneFabric if we didn't resolve result yet (or if layer is lane_fabric_vm)
    if layer_used == "lane_fabric_vm":
        if op == "ADD":
            res = adapter.fabric.add_word(val1, val2)
            sol_result = res.result
            carry_out = res.carry_out
        elif op == "SUB":
            res = adapter.fabric.sub_word(val1, val2)
            sol_result = res.result
            carry_out = res.carry_out
        elif op == "AND":
            res = adapter.fabric.and_word(val1, val2)
            sol_result = res.result
        elif op == "OR":
            res = adapter.fabric.or_word(val1, val2)
            sol_result = res.result
        elif op == "XOR":
            res = adapter.fabric.xor_word(val1, val2)
            sol_result = res.result
        elif op == "NOT":
            res = adapter.fabric.not_word(val1)
            sol_result = res.result
        elif op == "SHL":
            res = adapter.fabric.shift_left_word(val1, val2)
            sol_result = res.result
        elif op == "SHR":
            res = adapter.fabric.shift_right_word(val1, val2)
            sol_result = res.result
        elif op == "CMP":
            res = adapter.fabric.sub_word(val1, val2)
            sol_result = res.result
            carry_out = res.carry_out
        elif op == "LOAD":
            addr = val1
            sol_result = memory.get(addr, 0)
        elif op == "STORE":
            sol_result = val2
        elif op == "MOV":
            sol_result = val1

    # 3. Compute flags for SOL
    sol_flags = dict(flags)
    
    if layer_used != "unavailable":
        if op in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "SHL", "SHR", "NOT"):
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
            elif op in ("SUB", "CMP"):
                sol_flags["carry"] = carry_out
                sol_flags["borrow"] = carry_out
                s1 = (val1 >> (width - 1)) & 1
                s2 = (val2 >> (width - 1)) & 1
                sr = (sol_result >> (width - 1)) & 1
                sol_flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
            elif op == "SHL":
                sol_flags["borrow"] = 0
                sol_flags["overflow"] = 0
                if val2 > 0 and val2 <= width:
                    sol_flags["carry"] = (val1 >> (width - val2)) & 1
                else:
                    sol_flags["carry"] = 0
            elif op == "SHR":
                sol_flags["borrow"] = 0
                sol_flags["overflow"] = 0
                if val2 > 0 and val2 <= width:
                    sol_flags["carry"] = (val1 >> (val2 - 1)) & 1
                else:
                    sol_flags["carry"] = 0
            elif op in ("AND", "OR", "XOR", "NOT"):
                sol_flags["carry"] = 0
                sol_flags["borrow"] = 0
                sol_flags["overflow"] = 0

    # 4. Generate Oracle Reference
    oracle_result = 0
    oracle_flags = dict(flags)
    
    if op == "LOAD":
        oracle_result = memory.get(val1, 0)
    elif op == "STORE":
        oracle_result = val2
    elif op == "MOV":
        oracle_result = val1
    elif op in ("ADD", "SUB", "CMP", "AND", "OR", "XOR", "SHL", "SHR", "NOT"):
        if op == "CMP":
            oracle_result = (val1 - val2) & mask
            oracle_flags["zero"] = 1 if oracle_result == 0 else 0
            msb = 1 << (width - 1)
            oracle_flags["sign"] = 1 if (oracle_result & msb) else 0
            borrow = 1 if val1 < val2 else 0
            oracle_flags["carry"] = borrow
            oracle_flags["borrow"] = borrow
            s1 = (val1 >> (width - 1)) & 1
            s2 = (val2 >> (width - 1)) & 1
            sr = (oracle_result >> (width - 1)) & 1
            oracle_flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
        elif op == "NOT":
            oracle_result = (~val1) & mask
            oracle_flags["zero"] = 1 if oracle_result == 0 else 0
            msb = 1 << (width - 1)
            oracle_flags["sign"] = 1 if (oracle_result & msb) else 0
            oracle_flags["carry"] = 0
            oracle_flags["borrow"] = 0
            oracle_flags["overflow"] = 0
        else:
            if op == "ADD":
                oracle_result = (val1 + val2) & mask
                oracle_flags["carry"] = 1 if (val1 + val2) > mask else 0
                oracle_flags["borrow"] = 0
                s1 = (val1 >> (width - 1)) & 1
                s2 = (val2 >> (width - 1)) & 1
                sr = (oracle_result >> (width - 1)) & 1
                oracle_flags["overflow"] = 1 if s1 == s2 and s1 != sr else 0
            elif op == "SUB":
                oracle_result = (val1 - val2) & mask
                borrow = 1 if val1 < val2 else 0
                oracle_flags["carry"] = borrow
                oracle_flags["borrow"] = borrow
                s1 = (val1 >> (width - 1)) & 1
                s2 = (val2 >> (width - 1)) & 1
                sr = (oracle_result >> (width - 1)) & 1
                oracle_flags["overflow"] = 1 if s1 != s2 and s1 != sr else 0
            elif op == "AND":
                oracle_result = (val1 & val2) & mask
                oracle_flags["carry"] = 0
                oracle_flags["borrow"] = 0
                oracle_flags["overflow"] = 0
            elif op == "OR":
                oracle_result = (val1 | val2) & mask
                oracle_flags["carry"] = 0
                oracle_flags["borrow"] = 0
                oracle_flags["overflow"] = 0
            elif op == "XOR":
                oracle_result = (val1 ^ val2) & mask
                oracle_flags["carry"] = 0
                oracle_flags["borrow"] = 0
                oracle_flags["overflow"] = 0
            elif op == "SHL":
                oracle_result = (val1 << val2) & mask
                if val2 > 0 and val2 <= width:
                    oracle_flags["carry"] = (val1 >> (width - val2)) & 1
                else:
                    oracle_flags["carry"] = 0
                oracle_flags["borrow"] = 0
                oracle_flags["overflow"] = 0
            elif op == "SHR":
                oracle_result = (val1 >> val2) & mask
                if val2 > 0 and val2 <= width:
                    oracle_flags["carry"] = (val1 >> (val2 - 1)) & 1
                else:
                    oracle_flags["carry"] = 0
                oracle_flags["borrow"] = 0
                oracle_flags["overflow"] = 0
                
            oracle_flags["zero"] = 1 if oracle_result == 0 else 0
            msb = 1 << (width - 1)
            oracle_flags["sign"] = 1 if (oracle_result & msb) else 0

    return WaveguideInstructionExecution(
        instruction=instruction,
        layer_used=layer_used,
        sol_result=sol_result,
        oracle_result=oracle_result,
        sol_flags=sol_flags,
        oracle_flags=oracle_flags,
        waveguide_trace_ref=waveguide_trace_ref,
        pdm_trace_ref=pdm_trace_ref,
        sequencer_trace_ref=sequencer_trace_ref
    )


def execute_waveguide_program(adapter: WaveguideProgramAdapter, program: WideWordProgram) -> WaveguideProgramAdapterReport:
    """
    Executes a program sequence instruction-by-instruction.
    """
    width = adapter.width
    mask = mask_for_width(width)
    
    # Set up virtual states
    registers = {f"R{i}": 0 for i in range(16)}
    memory = {}
    flags = {
        "zero": 0,
        "carry": 0,
        "overflow": 0,
        "sign": 0,
        "borrow": 0
    }
    
    trace_steps = []
    mismatches = []
    layers_used = {}
    
    # First pass: Resolve labels
    labels = {}
    clean_instructions = []
    for inst in program.instructions:
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
                
    pc = 0
    cycles = 0
    max_cycles = 2000
    success = True
    oracle_match = True
    
    while pc < len(clean_instructions) and cycles < max_cycles:
        inst = clean_instructions[pc]
        op = inst.op.upper()
        cycles += 1
        
        pc_before = pc
        registers_before = dict(registers)
        
        # Referenced memory before
        referenced_addr = None
        memory_before_refs = {}
        
        def resolve_val(operand: Any) -> int:
            if isinstance(operand, str) and operand.startswith("R"):
                return registers.get(operand, 0)
            if isinstance(operand, int):
                return operand & mask
            return 0
            
        if op in ("LOAD", "STORE"):
            referenced_addr = resolve_val(inst.src1)
            memory_before_refs[referenced_addr] = memory.get(referenced_addr, 0)
            
        operand_a = None
        operand_b = None
        if inst.src1 is not None:
            try:
                operand_a = resolve_val(inst.src1)
            except Exception:
                pass
        if inst.src2 is not None:
            try:
                operand_b = resolve_val(inst.src2)
            except Exception:
                pass

        if op == "HALT":
            step = WideWordProgramTraceStep(
                step_index=len(trace_steps),
                pc_before=pc_before,
                pc_after=pc_before,
                instruction=inst,
                width=width,
                operand_a=None,
                operand_b=None,
                sol_result=0,
                oracle_result=0,
                sol_flags=dict(flags),
                oracle_flags=dict(flags),
                registers_before=registers_before,
                registers_after=dict(registers),
                memory_before_refs=memory_before_refs,
                memory_after_refs=dict(memory_before_refs),
                layer_used=adapter.backend,
                waveguide_trace_ref=None,
                pdm_trace_ref=None,
                sequencer_trace_ref=None,
                match=True,
                failure_reason=None
            )
            trace_steps.append(step)
            break
            
        # Execute instruction
        exec_res = execute_waveguide_instruction(adapter, inst, registers, memory, flags)
        
        layers_used[exec_res.layer_used] = layers_used.get(exec_res.layer_used, 0) + 1
        
        # Determine jump cond
        jumped = False
        
        if exec_res.layer_used == "unavailable":
            success = False
            oracle_match = False
            mismatches.append(WaveguideProgramMismatch(
                step_index=len(trace_steps),
                pc=pc_before,
                instruction=inst,
                failure_reason=f"Layer {adapter.backend} is unavailable for operation {op}",
                details={"op": op, "backend": adapter.backend}
            ))
            break
            
        # Write state changes back to registers/memory/flags
        if op == "LOAD":
            registers[inst.dst] = exec_res.sol_result & mask
        elif op == "STORE":
            memory[referenced_addr] = resolve_val(inst.dst)
        elif op == "MOV":
            registers[inst.dst] = exec_res.sol_result & mask
        elif op in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "NOT"):
            registers[inst.dst] = exec_res.sol_result & mask
            
        # Update flags
        flags.update(exec_res.sol_flags)
        
        # Handle PC jumps
        if op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
            target = inst.dst
            target_pc = labels[target] if target in labels else int(target)
            
            cond = False
            if op == "JMP":
                cond = True
            elif op == "JZ":
                cond = flags["zero"] == 1
            elif op == "JNZ":
                cond = flags["zero"] == 0
            elif op in ("JC", "JB"):
                cond = flags["carry"] == 1
            elif op in ("JNC", "JNB"):
                cond = flags["carry"] == 0
                
            if cond:
                pc = target_pc
                jumped = True
                
        if not jumped:
            pc += 1
            
        pc_after = pc
        memory_after_refs = {}
        if referenced_addr is not None:
            memory_after_refs[referenced_addr] = memory.get(referenced_addr, 0)
            
        # Check trace step match
        match = exec_res.sol_result == exec_res.oracle_result and exec_res.sol_flags == exec_res.oracle_flags
        failure_reason = None
        if not match:
            success = False
            oracle_match = False
            failure_reason = "Result or flags mismatch"
            mismatches.append(WaveguideProgramMismatch(
                step_index=len(trace_steps),
                pc=pc_before,
                instruction=inst,
                failure_reason=failure_reason,
                details={
                    "expected_result_hex": format_hex(exec_res.oracle_result, width),
                    "actual_result_hex": format_hex(exec_res.sol_result, width),
                    "expected_flags": exec_res.oracle_flags,
                    "actual_flags": exec_res.sol_flags
                }
            ))

        step = WideWordProgramTraceStep(
            step_index=len(trace_steps),
            pc_before=pc_before,
            pc_after=pc_after,
            instruction=inst,
            width=width,
            operand_a=operand_a,
            operand_b=operand_b,
            sol_result=exec_res.sol_result,
            oracle_result=exec_res.oracle_result,
            sol_flags=dict(exec_res.sol_flags),
            oracle_flags=dict(exec_res.oracle_flags),
            registers_before=registers_before,
            registers_after=dict(registers),
            memory_before_refs=memory_before_refs,
            memory_after_refs=memory_after_refs,
            layer_used=exec_res.layer_used,
            waveguide_trace_ref=exec_res.waveguide_trace_ref,
            pdm_trace_ref=exec_res.pdm_trace_ref,
            sequencer_trace_ref=exec_res.sequencer_trace_ref,
            match=match,
            failure_reason=failure_reason
        )
        trace_steps.append(step)
        
    return WaveguideProgramAdapterReport(
        adapter=adapter,
        trace_steps=trace_steps,
        success=success,
        oracle_match=oracle_match,
        mismatches=mismatches,
        layers_used=layers_used
    )


def compare_waveguide_instruction_to_oracle(trace_step: WideWordProgramTraceStep) -> bool:
    return trace_step.match


def summarize_waveguide_program_report(report: WaveguideProgramAdapterReport) -> WaveguideProgramExecutionReport:
    """
    Summarizes execution traces and packages evidence.
    """
    import uuid
    report_id = f"RPT_WWP_{uuid.uuid4().hex[:8]}"
    
    cases_passed = sum(1 for step in report.trace_steps if step.match)
    cases_failed = len(report.trace_steps) - cases_passed
    
    active_table_mutated = False
    
    backend_requested = report.adapter.backend
    
    backend_used = backend_requested
    if backend_requested == "pdm_waveguide_shadow" and report.layers_used.get("pdm_waveguide_shadow", 0) == 0:
        backend_used = "lane_fabric_vm"
        
    success = report.success and (cases_failed == 0)
    oracle_match = report.oracle_match
    
    metadata = {"mismatches": [m.__dict__ for m in report.mismatches]}
    if report.pipeline_compaction_report:
        metadata["pipeline_compaction_report"] = report.pipeline_compaction_report
    if report.scoreboard_scheduler_report:
        metadata["scoreboard_scheduler_report"] = report.scoreboard_scheduler_report

    return WaveguideProgramExecutionReport(
        report_id=report_id,
        width=report.adapter.width,
        backend_requested=backend_requested,
        backend_used=backend_used,
        success=success,
        oracle_match=oracle_match,
        cases_passed=cases_passed,
        cases_failed=cases_failed,
        layers_used=report.layers_used,
        active_table_mutated=active_table_mutated,
        metadata=metadata
    )


def export_program_instruction_support(backend: str) -> List[str]:
    # Returns the list of mnemonics supported natively by the backend
    is_alu_backend = backend in ("sequencer_shadow_strict", "pdm_waveguide_shadow_strict")
    if is_alu_backend:
        return ["ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP", "HALT"]
    # lane_fabric and hybrid support everything
    return [
        "LOAD_IMM", "LOAD", "STORE", "MOV", "ADD", "SUB", "AND", "OR",
        "XOR", "NOT", "SHL", "SHR", "CMP", "JMP", "JZ", "JNZ", "JC",
        "JNC", "JB", "JNB", "HALT"
    ]


def classify_instruction_support_for_backend(instruction: str, backend: str) -> str:
    is_alu = instruction in ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP")
    if backend == "lane_fabric_strict":
        return "native"
    elif backend == "hybrid_shadow":
        return "hybrid"
    elif backend in ("sequencer_shadow_strict", "pdm_waveguide_shadow_strict"):
        if is_alu:
            return "native"
        elif instruction == "HALT":
            return "native"
        return "unsupported"
    return "unsupported"


def validate_program_against_micro_isa(program: Any, isa_spec: Any) -> Dict[str, Any]:
    # Extract clean instructions
    clean_instructions = []
    for inst in program.instructions:
        if isinstance(inst, str) and inst.endswith(":"):
            continue
        if isinstance(inst, (tuple, list)):
            op = inst[0].upper()
            dst = inst[1] if len(inst) > 1 else None
            src1 = inst[2] if len(inst) > 2 else None
            src2 = inst[3] if len(inst) > 3 else None
            clean_instructions.append(WideWordProgramInstruction(op=op, dst=dst, src1=src1, src2=src2))
        else:
            clean_instructions.append(inst)
            
    errors = []
    for idx, inst in enumerate(clean_instructions):
        op = inst.op.upper()
        if op not in isa_spec.instructions:
            errors.append(f"Instruction {op} at index {idx} is outside Micro-ISA v0 specification")
            continue
            
        spec = isa_spec.instructions[op]
        # check operand count
        actual_ops = []
        if inst.dst is not None:
            actual_ops.append(inst.dst)
        if inst.src1 is not None:
            actual_ops.append(inst.src1)
        if inst.src2 is not None:
            actual_ops.append(inst.src2)
            
        if len(actual_ops) != spec.operand_count:
            errors.append(f"Instruction {op} at index {idx} expects {spec.operand_count} operands, got {len(actual_ops)}")
            
    return {
        "success": len(errors) == 0,
        "errors": errors
    }


def execute_pdm_waveguide_microcoded_instruction(
    adapter: WaveguideProgramAdapter,
    instruction: Any,
    state: Any
) -> tuple[int, str, Dict[str, int]]:
    from sol_waveguide_control_memory_bridge import execute_waveguide_control_memory_instruction
    sol_result, layer_used, sol_flags, _, _ = execute_waveguide_control_memory_instruction(state, instruction)
    return sol_result, layer_used, sol_flags


def validate_pdm_waveguide_microcoded_no_fallback(trace: Any) -> bool:
    steps = getattr(trace, "steps", getattr(trace, "trace_steps", []))
    for step in steps:
        layer = getattr(step, "layer_used", "")
        if layer == "lane_fabric_vm":
            return False
    return True


def classify_pdm_waveguide_microcoded_support(program: Any) -> bool:
    from sol_micro_isa import build_micro_isa_v0_spec
    spec = build_micro_isa_v0_spec()
    res = validate_program_against_micro_isa(program, spec)
    return res["success"]


# Add methods to the class itself using a monkeypatch/direct addition, or we can just define them as functions.
# Since execute_program_strict_backend calls self.execute_pdm_waveguide_microcoded_program, we must add it to WaveguideProgramAdapter.
def execute_pdm_waveguide_microcoded_program(
    self,
    program: WideWordProgram,
    config: Optional[WaveguideProgramExecutionConfig] = None
) -> WaveguideProgramAdapterReport:
    from sol_waveguide_control_memory_bridge import (
        build_waveguide_control_memory_state,
        execute_waveguide_control_memory_program,
        WaveguideControlMemoryBridgeConfig
    )
    bridge_config = WaveguideControlMemoryBridgeConfig(width=self.width)
    state = build_waveguide_control_memory_state(width=self.width)
    
    # Execute via the bridge
    bridge_report = execute_waveguide_control_memory_program(program, state, bridge_config)
    
    # Map traces
    trace_steps = []
    for step in bridge_report.trace_steps:
        trace_steps.append(WideWordProgramTraceStep(
            step_index=step.step_index,
            pc_before=step.pc_before,
            pc_after=step.pc_after,
            instruction=step.instruction,
            width=self.width,
            operand_a=None,
            operand_b=None,
            sol_result=step.sol_result,
            oracle_result=step.oracle_result,
            sol_flags=step.sol_flags,
            oracle_flags=step.oracle_flags,
            registers_before={},
            registers_after={},
            memory_before_refs={},
            memory_after_refs={},
            layer_used=step.layer_used,
            waveguide_trace_ref=None,
            pdm_trace_ref=None,
            sequencer_trace_ref=None,
            match=step.match,
            failure_reason=None if step.match else "Execution mismatch"
        ))
        
    mismatches = []
    for m in bridge_report.mismatches:
        mismatches.append(WaveguideProgramMismatch(
            step_index=m["step_index"],
            pc=m["pc"],
            instruction=None,
            failure_reason=m["failure_reason"],
            details=m.get("details", {})
        ))
        
    return WaveguideProgramAdapterReport(
        adapter=self,
        trace_steps=trace_steps,
        success=bridge_report.success,
        oracle_match=bridge_report.oracle_match,
        mismatches=mismatches,
        layers_used=bridge_report.layers_used,
        pipeline_compaction_report=bridge_report.pipeline_compaction_report,
        scoreboard_scheduler_report=bridge_report.scoreboard_scheduler_report
    )

WaveguideProgramAdapter.execute_pdm_waveguide_microcoded_program = execute_pdm_waveguide_microcoded_program


