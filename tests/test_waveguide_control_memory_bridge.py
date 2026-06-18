# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Control-Memory Bridge
============================================
Verifies program-counter redirection, memory shard bounds,
and execution bridge correctness across all required test scenarios.
"""

import pytest
from dataclasses import asdict

from sol_wideword_computation_validation import WideWordProgramInstruction, WideWordProgram, mask_for_width
from sol_waveguide_branch_control import (
    build_waveguide_program_counter,
    build_waveguide_branch_gate,
    evaluate_waveguide_branch_condition,
    apply_waveguide_branch_decision,
    execute_waveguide_branch_instruction,
    WaveguideBranchCondition,
    WaveguideBranchDecision
)
from sol_waveguide_memory_shard import (
    build_waveguide_memory_shard,
    validate_waveguide_memory_address,
    execute_waveguide_load,
    execute_waveguide_store,
    snapshot_waveguide_memory_shard,
    compare_waveguide_memory_shards
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_instruction,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from tests.test_strict_backend_execution_proof import (
    snapshot_active_state,
    verify_active_state
)
from tests.test_wideword_waveguide_program_execution import (
    make_arithmetic_chain_program,
    make_sum_loop_program,
    make_fibonacci_loop_program,
    make_popcount_program,
    make_crc_mixing_program,
    make_shift_add_multiply_program,
    make_restoring_division_program
)

def test_waveguide_program_counter_builds_32_64():
    for w in (32, 64):
        pc = build_waveguide_program_counter(width=w, initial_pc=10)
        assert pc.pc == 10
        assert pc.width == w

def test_waveguide_branch_jmp_updates_pc():
    inst = WideWordProgramInstruction(op="JMP", dst="TARGET", src1=None, src2=None)
    labels = {"TARGET": 42}
    dec, trace = execute_waveguide_branch_instruction(inst, pc=5, flags={}, labels=labels)
    assert dec.taken is True
    assert dec.target_pc == 42
    assert trace.pc_after == 42

def test_waveguide_branch_jz_taken_and_not_taken():
    inst = WideWordProgramInstruction(op="JZ", dst="TARGET", src1=None, src2=None)
    labels = {"TARGET": 42}
    
    # Taken
    dec, trace = execute_waveguide_branch_instruction(inst, pc=5, flags={"zero": 1}, labels=labels)
    assert dec.taken is True
    assert dec.target_pc == 42
    
    # Not taken
    dec2, trace2 = execute_waveguide_branch_instruction(inst, pc=5, flags={"zero": 0}, labels=labels)
    assert dec2.taken is False
    assert dec2.target_pc == 6

def test_waveguide_branch_jnz_taken_and_not_taken():
    inst = WideWordProgramInstruction(op="JNZ", dst="TARGET", src1=None, src2=None)
    labels = {"TARGET": 42}
    
    # Taken
    dec, trace = execute_waveguide_branch_instruction(inst, pc=5, flags={"zero": 0}, labels=labels)
    assert dec.taken is True
    assert dec.target_pc == 42
    
    # Not taken
    dec2, trace2 = execute_waveguide_branch_instruction(inst, pc=5, flags={"zero": 1}, labels=labels)
    assert dec2.taken is False
    assert dec2.target_pc == 6

def test_waveguide_branch_jc_jnc():
    inst_jc = WideWordProgramInstruction(op="JC", dst="TARGET", src1=None, src2=None)
    inst_jnc = WideWordProgramInstruction(op="JNC", dst="TARGET", src1=None, src2=None)
    labels = {"TARGET": 42}
    
    dec1, _ = execute_waveguide_branch_instruction(inst_jc, pc=5, flags={"carry": 1}, labels=labels)
    assert dec1.taken is True
    
    dec2, _ = execute_waveguide_branch_instruction(inst_jc, pc=5, flags={"carry": 0}, labels=labels)
    assert dec2.taken is False
    
    dec3, _ = execute_waveguide_branch_instruction(inst_jnc, pc=5, flags={"carry": 1}, labels=labels)
    assert dec3.taken is False
    
    dec4, _ = execute_waveguide_branch_instruction(inst_jnc, pc=5, flags={"carry": 0}, labels=labels)
    assert dec4.taken is True

def test_waveguide_branch_jb_jnb():
    inst_jb = WideWordProgramInstruction(op="JB", dst="TARGET", src1=None, src2=None)
    inst_jnb = WideWordProgramInstruction(op="JNB", dst="TARGET", src1=None, src2=None)
    labels = {"TARGET": 42}
    
    dec1, _ = execute_waveguide_branch_instruction(inst_jb, pc=5, flags={"borrow": 1}, labels=labels)
    assert dec1.taken is True
    
    dec2, _ = execute_waveguide_branch_instruction(inst_jb, pc=5, flags={"borrow": 0}, labels=labels)
    assert dec2.taken is False
    
    dec3, _ = execute_waveguide_branch_instruction(inst_jnb, pc=5, flags={"borrow": 1}, labels=labels)
    assert dec3.taken is False
    
    dec4, _ = execute_waveguide_branch_instruction(inst_jnb, pc=5, flags={"borrow": 0}, labels=labels)
    assert dec4.taken is True

def test_waveguide_memory_shard_builds_32_64():
    for w in (32, 64):
        shard = build_waveguide_memory_shard(width=w, slots=512)
        assert shard.width == w
        assert shard.slots == 512
        assert len(shard.cells) == 0

def test_waveguide_memory_load_store_round_trip_32_64():
    for w in (32, 64):
        shard = build_waveguide_memory_shard(width=w)
        execute_waveguide_store(shard, address=100, value=0xDEADBEEF)
        val = execute_waveguide_load(shard, address=100)
        assert val == (0xDEADBEEF & mask_for_width(w))

def test_waveguide_memory_masks_values_by_width():
    shard32 = build_waveguide_memory_shard(width=32)
    execute_waveguide_store(shard32, address=10, value=0xFFFFFFFFFFFFFFFF)
    assert execute_waveguide_load(shard32, address=10) == 0xFFFFFFFF
    
    shard64 = build_waveguide_memory_shard(width=64)
    execute_waveguide_store(shard64, address=10, value=0xFFFFFFFFFFFFFFFF)
    assert execute_waveguide_load(shard64, address=10) == 0xFFFFFFFFFFFFFFFF

def test_waveguide_memory_rejects_out_of_bounds_address():
    shard = build_waveguide_memory_shard(width=32, slots=100)
    with pytest.raises(IndexError):
        execute_waveguide_store(shard, address=100, value=5)
    with pytest.raises(IndexError):
        execute_waveguide_load(shard, address=100)
    with pytest.raises(IndexError):
        execute_waveguide_store(shard, address=-1, value=5)
    with pytest.raises(IndexError):
        execute_waveguide_load(shard, address=-1)

def test_waveguide_control_memory_register_chain_32_64():
    for w in (32, 64):
        prog = make_arithmetic_chain_program(100, 200)
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w)
        report = execute_waveguide_control_memory_program(prog, state, config)
        assert report.success
        assert report.oracle_match

def test_waveguide_control_memory_sum_loop_32_64():
    for w in (32, 64):
        prog = make_sum_loop_program(10)
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w)
        report = execute_waveguide_control_memory_program(prog, state, config)
        assert report.success
        assert report.oracle_match

def test_waveguide_control_memory_fibonacci_loop_32_64():
    for w in (32, 64):
        prog = make_fibonacci_loop_program(12)
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w)
        report = execute_waveguide_control_memory_program(prog, state, config)
        assert report.success
        assert report.oracle_match

def test_waveguide_control_memory_popcount_32_64():
    for w in (32, 64):
        prog = make_popcount_program(0xF5, w)
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w)
        report = execute_waveguide_control_memory_program(prog, state, config)
        assert report.success
        assert report.oracle_match

def test_waveguide_control_memory_crc_xor_shift_32_64():
    for w in (32, 64):
        prog = make_crc_mixing_program(0x12345678, w)
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w)
        report = execute_waveguide_control_memory_program(prog, state, config)
        assert report.success
        assert report.oracle_match

def test_waveguide_control_memory_shift_add_multiply_32_64():
    for w in (32, 64):
        prog = make_shift_add_multiply_program(15, 6)
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w)
        report = execute_waveguide_control_memory_program(prog, state, config)
        assert report.success
        assert report.oracle_match

def test_waveguide_control_memory_division_scaffold_32_64():
    for w in (32, 64):
        prog = make_restoring_division_program(10, 3)
        state = build_waveguide_control_memory_state(width=w)
        config = WaveguideControlMemoryBridgeConfig(width=w)
        report = execute_waveguide_control_memory_program(prog, state, config)
        assert report.success
        assert report.oracle_match

def test_waveguide_control_memory_trace_matches_oracle():
    prog = [
        ("LOAD_IMM", "R1", 10),
        ("ADD", "R2", "R1", 20),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32)
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success
    assert report.oracle_match
    # Ensure trace steps are recorded
    assert len(report.trace_steps) == 3
    assert report.trace_steps[0].instruction.op == "LOAD_IMM"
    assert report.trace_steps[0].oracle_result == 10
    assert report.trace_steps[1].instruction.op == "ADD"
    assert report.trace_steps[1].oracle_result == 30

def test_waveguide_control_memory_no_lane_fabric_fallback():
    prog = [
        ("LOAD_IMM", "R1", 10),
        ("ADD", "R2", "R1", 20),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32)
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success
    # Verify no fallback to lane_fabric_vm occurred in strict bridge execution
    for step in report.trace_steps:
        assert step.layer_used != "lane_fabric_vm"

def test_waveguide_control_memory_active_state_guard():
    snap = snapshot_active_state()
    prog = [
        ("LOAD_IMM", "R1", 10),
        ("ADD", "R2", "R1", 20),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32)
    execute_waveguide_control_memory_program(prog, state, config)
    assert verify_active_state(snap)
