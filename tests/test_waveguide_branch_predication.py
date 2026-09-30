# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Branch-Diamond Predication + Conditional Select Lowering Bridge
"""

import pytest
from typing import List, Dict, Any

from sol_wideword_computation_validation import (
    WideWordProgramInstruction,
    WideWordProgram,
    WideWordVirtualVM,
    mask_for_width
)
from sol_waveguide_branch_control import evaluate_waveguide_branch_condition
from sol_waveguide_predication import (
    detect_waveguide_branch_diamonds,
    analyze_waveguide_predication_safety,
    execute_waveguide_predicated_diamond
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_waveguide_trace_replay import (
    replay_waveguide_execution_trace,
    validate_waveguide_trace_metadata
)
from sol_strict_backend_execution_proof import (
    StrictBackendProofConfig,
    StrictBackendProgramCase,
    run_strict_backend_program_case,
    build_strict_backend_support_matrix
)

# Helper to normalize label formats
def clean_program(instructions: List[Any]) -> List[Any]:
    clean = []
    for inst in instructions:
        if isinstance(inst, str) and inst.endswith(":"):
            clean.append(inst)
        elif isinstance(inst, tuple):
            op = inst[0].upper()
            dst = inst[1] if len(inst) > 1 else None
            src1 = inst[2] if len(inst) > 2 else None
            src2 = inst[3] if len(inst) > 3 else None
            clean.append(WideWordProgramInstruction(op=op, dst=dst, src1=src1, src2=src2))
        else:
            clean.append(inst)
    return clean

def test_waveguide_diamond_detection_skip():
    # Pattern A: conditional skip
    prog = [
        ("MOV", "R1", 1),
        ("CMP", "R1", 0),
        ("JZ", "target"),
        ("ADD", "R2", "R2", 10),
        "target:",
        ("HALT",)
    ]
    clean_insts = clean_program(prog)
    
    # Manually compute labels mapping
    labels = {}
    cleaned_instrs_list = []
    for inst in clean_insts:
        if isinstance(inst, str) and inst.endswith(":"):
            labels[inst[:-1]] = len(cleaned_instrs_list)
        else:
            cleaned_instrs_list.append(inst)
            
    diamonds, skipped = detect_waveguide_branch_diamonds(cleaned_instrs_list, labels)
    
    assert len(diamonds) == 1
    d = diamonds[0]
    assert d.diamond_type == "skip"
    assert d.cond_instruction.op == "JZ"
    assert d.then_pc_start == 3
    assert d.then_pc_end == 3
    assert d.target_end_pc == 4  # target label points to HALT at pc 4

def test_waveguide_diamond_detection_ifelse():
    # Pattern B: if/else diamond
    prog = [
        ("MOV", "R1", 1),
        ("CMP", "R1", 0),
        ("JZ", "else_label"),
        ("ADD", "R2", "R2", 10),
        ("JMP", "end_label"),
        "else_label:",
        ("ADD", "R2", "R2", 20),
        "end_label:",
        ("HALT",)
    ]
    clean_insts = clean_program(prog)
    
    labels = {}
    cleaned_instrs_list = []
    for inst in clean_insts:
        if isinstance(inst, str) and inst.endswith(":"):
            labels[inst[:-1]] = len(cleaned_instrs_list)
        else:
            cleaned_instrs_list.append(inst)
            
    diamonds, skipped = detect_waveguide_branch_diamonds(cleaned_instrs_list, labels)
    
    assert len(diamonds) == 1
    d = diamonds[0]
    assert d.diamond_type == "if_else"
    assert d.cond_instruction.op == "JZ"
    assert d.then_pc_start == 3
    assert d.then_pc_end == 3
    assert d.else_pc_start == 5
    assert d.else_pc_end == 5
    assert d.target_end_pc == 6  # end_label points to HALT

def test_waveguide_diamond_detection_loop_skip():
    # Verify backward loop jumps are skipped
    prog = [
        "loop:",
        ("SUB", "R1", "R1", 1),
        ("CMP", "R1", 0),
        ("JNZ", "loop"),
        ("HALT",)
    ]
    clean_insts = clean_program(prog)
    
    labels = {}
    cleaned_instrs_list = []
    for inst in clean_insts:
        if isinstance(inst, str) and inst.endswith(":"):
            labels[inst[:-1]] = len(cleaned_instrs_list)
        else:
            cleaned_instrs_list.append(inst)
            
    diamonds, skipped = detect_waveguide_branch_diamonds(cleaned_instrs_list, labels)
    assert len(diamonds) == 0
    assert any("backwards" in s["reason"] for s in skipped)

def test_waveguide_predication_safety_barriers():
    # Helper to check safety of an instruction block
    def is_block_safe(prog_slice: List[Any], target_end_pc: int = 100) -> bool:
        clean_slice = clean_program(prog_slice)
        ok, err = analyze_waveguide_predication_safety(clean_slice, 0, len(clean_slice) - 1, target_end_pc)
        return ok

    # Safe block
    assert is_block_safe([("ADD", "R2", "R3", "R4"), ("MOV", "R4", 5)]) is True
    
    # Unsafe: LOAD
    assert is_block_safe([("LOAD", "R2", 100)]) is False
    
    # Unsafe: STORE
    assert is_block_safe([("STORE", "R2", 100)]) is False
    
    # Unsafe: HALT
    assert is_block_safe([("HALT",)]) is False
    
    # Unsafe: nested branch
    assert is_block_safe([("JMP", "somewhere")]) is False
    assert is_block_safe([("JZ", "somewhere")]) is False

def test_waveguide_predication_safety_flag_ambiguity():
    # Diamond writing flags that are immediately consumed outside must be skipped
    prog = [
        ("MOV", "R1", 0),
        ("CMP", "R1", 0),
        ("JZ", "target"),
        ("ADD", "R2", "R2", 10),
        "target:",
        ("JZ", "outside_target"),
        ("MOV", "R3", 1),
        "outside_target:",
        ("HALT",)
    ]
    clean_insts = clean_program(prog)
    labels = {}
    cleaned_instrs_list = []
    for inst in clean_insts:
        if isinstance(inst, str) and inst.endswith(":"):
            labels[inst[:-1]] = len(cleaned_instrs_list)
        else:
            cleaned_instrs_list.append(inst)
            
    diamonds, skipped = detect_waveguide_branch_diamonds(cleaned_instrs_list, labels)
    assert not any(d.cond_pc == 2 for d in diamonds)
    assert any("flag effects would be externally visible" in s["reason"] for s in skipped)

def test_waveguide_predication_evaluation():
    from sol_waveguide_branch_control import execute_waveguide_branch_instruction
    labels = {"target": 10}
    
    # JZ
    inst_jz = WideWordProgramInstruction(op="JZ", dst="target", src1=None, src2=None)
    dec, _ = execute_waveguide_branch_instruction(inst_jz, pc=0, flags={"zero": 1}, labels=labels)
    assert dec.taken is True
    dec, _ = execute_waveguide_branch_instruction(inst_jz, pc=0, flags={"zero": 0}, labels=labels)
    assert dec.taken is False
    
    # JNZ
    inst_jnz = WideWordProgramInstruction(op="JNZ", dst="target", src1=None, src2=None)
    dec, _ = execute_waveguide_branch_instruction(inst_jnz, pc=0, flags={"zero": 1}, labels=labels)
    assert dec.taken is False
    dec, _ = execute_waveguide_branch_instruction(inst_jnz, pc=0, flags={"zero": 0}, labels=labels)
    assert dec.taken is True
    
    # JC
    inst_jc = WideWordProgramInstruction(op="JC", dst="target", src1=None, src2=None)
    dec, _ = execute_waveguide_branch_instruction(inst_jc, pc=0, flags={"carry": 1}, labels=labels)
    assert dec.taken is True
    dec, _ = execute_waveguide_branch_instruction(inst_jc, pc=0, flags={"carry": 0}, labels=labels)
    assert dec.taken is False
    
    # JNC
    inst_jnc = WideWordProgramInstruction(op="JNC", dst="target", src1=None, src2=None)
    dec, _ = execute_waveguide_branch_instruction(inst_jnc, pc=0, flags={"carry": 1}, labels=labels)
    assert dec.taken is False
    dec, _ = execute_waveguide_branch_instruction(inst_jnc, pc=0, flags={"carry": 0}, labels=labels)
    assert dec.taken is True

    # JB
    inst_jb = WideWordProgramInstruction(op="JB", dst="target", src1=None, src2=None)
    dec, _ = execute_waveguide_branch_instruction(inst_jb, pc=0, flags={"borrow": 1}, labels=labels)
    assert dec.taken is True
    dec, _ = execute_waveguide_branch_instruction(inst_jb, pc=0, flags={"borrow": 0}, labels=labels)
    assert dec.taken is False

    # JNB
    inst_jnb = WideWordProgramInstruction(op="JNB", dst="target", src1=None, src2=None)
    dec, _ = execute_waveguide_branch_instruction(inst_jnb, pc=0, flags={"borrow": 1}, labels=labels)
    assert dec.taken is False
    dec, _ = execute_waveguide_branch_instruction(inst_jnb, pc=0, flags={"borrow": 0}, labels=labels)
    assert dec.taken is True

def test_waveguide_predication_skip_taken_execution():
    for w in (32, 64):
        # Branch skip, condition taken (R2 must NOT be updated)
        prog = [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("MOV", "R2", 100),
            "target:",
            ("HALT",)
        ]
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w, enable_branch_predication=True)
        report = execute_waveguide_control_memory_program(prog, state, config)
        
        assert report.success
        assert report.oracle_match
        assert state.registers["R2"] == 0
        assert report.branch_predication_report["diamonds_predicated"] == 1

def test_waveguide_predication_skip_not_taken_execution():
    for w in (32, 64):
        # Branch skip, condition not taken (R2 MUST be updated)
        prog = [
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("MOV", "R2", 100),
            "target:",
            ("HALT",)
        ]
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w, enable_branch_predication=True)
        report = execute_waveguide_control_memory_program(prog, state, config)
        
        assert report.success
        assert report.oracle_match
        assert state.registers["R2"] == 100
        assert report.branch_predication_report["diamonds_predicated"] == 1

def test_waveguide_predication_ifelse_then_selected_execution():
    for w in (32, 64):
        prog = [
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            ("MOV", "R2", 100),
            ("JMP", "end_label"),
            "else_label:",
            ("MOV", "R2", 200),
            "end_label:",
            ("HALT",)
        ]
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w, enable_branch_predication=True)
        report = execute_waveguide_control_memory_program(prog, state, config)
        
        assert report.success
        assert report.oracle_match
        assert state.registers["R2"] == 100
        assert report.branch_predication_report["diamonds_predicated"] == 1

def test_waveguide_predication_ifelse_else_selected_execution():
    for w in (32, 64):
        prog = [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            ("MOV", "R2", 100),
            ("JMP", "end_label"),
            "else_label:",
            ("MOV", "R2", 200),
            "end_label:",
            ("HALT",)
        ]
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w, enable_branch_predication=True)
        report = execute_waveguide_control_memory_program(prog, state, config)
        
        assert report.success
        assert report.oracle_match
        assert state.registers["R2"] == 200
        assert report.branch_predication_report["diamonds_predicated"] == 1

def test_waveguide_predication_equivalence_to_raw():
    for w in (32, 64):
        # A complex program with a predicated diamond in the middle
        prog = [
            ("MOV", "R3", 5),
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            ("ADD", "R2", "R3", 10),
            ("JMP", "end_label"),
            "else_label:",
            ("ADD", "R2", "R3", 20),
            "end_label:",
            ("ADD", "R4", "R2", 50),
            ("HALT",)
        ]
        
        # 1. Raw strict (predication disabled)
        state_raw = build_waveguide_control_memory_state(width=w)
        config_raw = WaveguideControlMemoryBridgeConfig(width=w, enable_branch_predication=False)
        report_raw = execute_waveguide_control_memory_program(prog, state_raw, config_raw)
        
        # 2. Predicated only
        state_pred = build_waveguide_control_memory_state(width=w)
        config_pred = WaveguideControlMemoryBridgeConfig(width=w, enable_branch_predication=True, enable_pipeline_compaction=False, enable_scoreboard_scheduling=False)
        report_pred = execute_waveguide_control_memory_program(prog, state_pred, config_pred)
        
        assert report_raw.success
        assert report_pred.success
        assert state_raw.registers == state_pred.registers
        assert state_raw.flags == state_pred.flags
        assert state_raw.pc == state_pred.pc

def test_waveguide_predication_composability():
    for w in (32, 64):
        # A program with prelude, predicated diamond, multiply loop (compacted), and epilogue (scheduled)
        from sol_waveguide_optimization_benchmark import make_shift_add_multiply_program
        prog = [
            ("MOV", "R10", 100),
            ("MOV", "R11", 200),
            ("ADD", "R12", "R10", 5),
            ("ADD", "R13", "R11", 10),
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            ("ADD", "R2", "R2", 10),
            ("JMP", "end_label"),
            "else_label:",
            ("ADD", "R2", "R2", 20),
            "end_label:",
        ] + make_shift_add_multiply_program(5, 4)[:-1] + [
            ("ADD", "R8", "R3", "R12"),
            ("ADD", "R9", "R8", "R13"),
            ("HALT",)
        ]
        
        # Enable all optimizations
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(
            width=w,
            enable_branch_predication=True,
            enable_pipeline_compaction=True,
            enable_scoreboard_scheduling=True
        )
        report = execute_waveguide_control_memory_program(prog, state, config)
        
        assert report.success
        assert report.oracle_match
        assert report.branch_predication_report["diamonds_predicated"] == 1
        assert report.pipeline_compaction_report["windows_compacted"] == 1
        assert report.scoreboard_scheduler_report is not None

def test_waveguide_predication_trace_replay_audit():
    w = 32
    prog = [
        ("MOV", "R1", 1),
        ("CMP", "R1", 0),
        ("JZ", "target"),
        ("ADD", "R2", "R2", 10),
        "target:",
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=w)
    config = WaveguideControlMemoryBridgeConfig(width=w, enable_branch_predication=True)
    report = execute_waveguide_control_memory_program(prog, state, config)
    
    assert report.success
    # Validate trace metadata
    md_ok, md_err = validate_waveguide_trace_metadata(report.trace_steps, len(prog), w)
    assert md_ok, md_err
    
    # Replay trace step-by-step
    rep_ok, rep_err, rep_state = replay_waveguide_execution_trace(w, report.trace_steps)
    assert rep_ok, rep_err
    assert rep_state["registers"]["R2"] == 10
    
    # Reject malformed trace metadata
    class BadStep:
        def __init__(self, step, meta):
            self.step_index = step.step_index
            self.pc_before = step.pc_before
            self.pc_after = step.pc_after
            self.instruction = step.instruction
            self.layer_used = step.layer_used
            self.sol_result = step.sol_result
            self.oracle_result = step.oracle_result
            self.sol_flags = step.sol_flags
            self.oracle_flags = step.oracle_flags
            self.match = step.match
            self.branch_trace = step.branch_trace
            self.memory_trace = step.memory_trace
            self.scheduler_metadata = step.scheduler_metadata
            self.predication_metadata = meta
            
    # Find the predicated step in trace
    pred_step = next(s for s in report.trace_steps if hasattr(s, "predication_metadata") and s.predication_metadata is not None)
    pred_step_index = report.trace_steps.index(pred_step)
    
    # Modify strategy to be invalid
    bad_meta = dict(pred_step.predication_metadata)
    bad_meta["lowering_strategy"] = "invalid_strategy"
    
    bad_steps = list(report.trace_steps)
    bad_steps[pred_step_index] = BadStep(pred_step, bad_meta)
    
    md_ok, md_err = validate_waveguide_trace_metadata(bad_steps, len(prog), w)
    assert not md_ok
    assert "lowering strategy" in md_err
    
    # Modify memory effects to be True
    bad_meta2 = dict(pred_step.predication_metadata)
    bad_meta2["memory_effects"] = True
    
    bad_steps2 = list(report.trace_steps)
    bad_steps2[pred_step_index] = BadStep(pred_step, bad_meta2)
    
    md_ok, md_err = validate_waveguide_trace_metadata(bad_steps2, len(prog), w)
    assert not md_ok
    assert "memory effects" in md_err

def test_waveguide_strict_proof_predication_matrix():
    # Build strict proof program case
    prog = [
        ("MOV", "R1", 1),
        ("CMP", "R1", 0),
        ("JZ", "target"),
        ("ADD", "R2", "R2", 10),
        "target:",
        ("HALT",)
    ]
    case = StrictBackendProgramCase(name="pred_test_case", program=prog, width=32)
    res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
    
    assert res.validated
    assert res.failed_instruction_count == 0
    assert res.fallback_instruction_count == 0
    
    # Verify capability matrix asserts support for predication features
    matrix = build_strict_backend_support_matrix([res])
    pdm_matrix = matrix.matrix["pdm_waveguide_microcoded_strict"]
    
    assert pdm_matrix["supports_branch_diamond_predication"] == "validated"
    assert pdm_matrix["supports_conditional_select_lowering"] == "validated"
