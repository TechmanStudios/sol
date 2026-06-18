# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Scoreboard Scheduler
===========================================
Verifies hazard detection, superblock partitioning, wavefront scheduling,
barrier enforcement, compaction integration, and strict compliance.
"""

import pytest
from sol_wideword_computation_validation import WideWordProgramInstruction, WideWordVirtualVM
from sol_waveguide_scoreboard_scheduler import (
    build_waveguide_instruction_hazards,
    split_waveguide_superblocks,
    schedule_waveguide_superblock,
    build_waveguide_scoreboard
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from tests.test_wideword_waveguide_program_execution import (
    make_arithmetic_chain_program,
    make_sum_loop_program,
    make_shift_add_multiply_program
)

# 1. Hazard metadata tests
def test_scheduler_hazard_registers():
    inst = WideWordProgramInstruction(op="ADD", dst="R1", src1="R2", src2="R3")
    h = build_waveguide_instruction_hazards(inst, 0)
    assert h["pc"] == 0
    assert h["opcode"] == "ADD"
    assert "R1" in h["writes_registers"]
    assert "R2" in h["reads_registers"]
    assert "R3" in h["reads_registers"]
    assert not h["is_barrier"]

def test_scheduler_hazard_flags():
    inst1 = WideWordProgramInstruction(op="CMP", dst="R1", src1="R2")
    h1 = build_waveguide_instruction_hazards(inst1, 0)
    assert "zero" in h1["writes_flags"]
    assert "carry" in h1["writes_flags"]
    
    inst2 = WideWordProgramInstruction(op="JZ", dst="target")
    h2 = build_waveguide_instruction_hazards(inst2, 1)
    assert h2["is_barrier"]
    assert "zero" in h2["reads_flags"]
    assert h2["changes_pc"]

def test_scheduler_hazard_memory_barrier():
    # Dynamic load address is considered unsafe memory and thus a barrier
    inst = WideWordProgramInstruction(op="LOAD", dst="R1", src1="R2")
    h = build_waveguide_instruction_hazards(inst, 0)
    assert h["is_barrier"]
    assert "dynamic" in h["reads_memory"]
    
    # Constant load address is safe
    inst_safe = WideWordProgramInstruction(op="LOAD", dst="R1", src1=10)
    h_safe = build_waveguide_instruction_hazards(inst_safe, 0)
    assert not h_safe["is_barrier"]
    assert 10 in h_safe["reads_memory"]

def test_scheduler_hazard_unknown_opcode():
    inst = WideWordProgramInstruction(op="SKEW_WAVE", dst="R1")
    h = build_waveguide_instruction_hazards(inst, 0)
    assert h["is_barrier"]
    assert "unknown or unsupported opcode" in h["reason"]


# 2. Superblock splitting tests
def test_superblock_splitting_straight_line():
    prog = [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=10),
        WideWordProgramInstruction(op="MOV", dst="R2", src1=20),
        WideWordProgramInstruction(op="ADD", dst="R3", src1="R1", src2="R2")
    ]
    sblocks = split_waveguide_superblocks(prog, [])
    assert len(sblocks) == 1
    assert len(sblocks[0].units) == 3

def test_superblock_splitting_branch_barrier():
    prog = [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=10),
        WideWordProgramInstruction(op="JZ", dst="skip"),
        WideWordProgramInstruction(op="MOV", dst="R2", src1=20)
    ]
    sblocks = split_waveguide_superblocks(prog, [])
    assert len(sblocks) == 2
    assert len(sblocks[0].units) == 2  # MOV + JZ
    assert len(sblocks[1].units) == 1  # MOV


# 3. Wavefront scheduling dependencies
def test_wavefront_batch_scheduling_independent():
    prog = [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=10),
        WideWordProgramInstruction(op="MOV", dst="R2", src1=20)
    ]
    hazards = [build_waveguide_instruction_hazards(inst, i) for i, inst in enumerate(prog)]
    batches = schedule_waveguide_superblock(prog, hazards)
    assert len(batches) == 1
    assert batches[0] == [0, 1]

def test_wavefront_batch_scheduling_raw_dependency():
    prog = [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=10),
        WideWordProgramInstruction(op="ADD", dst="R2", src1="R1", src2=5)
    ]
    hazards = [build_waveguide_instruction_hazards(inst, i) for i, inst in enumerate(prog)]
    batches = schedule_waveguide_superblock(prog, hazards)
    assert len(batches) == 2
    assert batches[0] == [0]
    assert batches[1] == [1]


# 4. Equivalence and bridge integration
def test_scheduler_equivalence_arithmetic_chain():
    for w in (32, 64):
        prog = make_arithmetic_chain_program(100, 200)
        
        # Unscheduled
        state_ser = build_waveguide_control_memory_state(width=w)
        config_ser = WaveguideControlMemoryBridgeConfig(width=w, enable_scoreboard_scheduling=False)
        report_ser = execute_waveguide_control_memory_program(prog, state_ser, config_ser)
        
        # Scheduled
        state_sch = build_waveguide_control_memory_state(width=w)
        config_sch = WaveguideControlMemoryBridgeConfig(width=w, enable_scoreboard_scheduling=True)
        report_sch = execute_waveguide_control_memory_program(prog, state_sch, config_sch)
        
        assert report_ser.success
        assert report_sch.success
        assert state_ser.registers == state_sch.registers
        assert state_ser.flags == state_sch.flags
        
        sch_report = report_sch.scoreboard_scheduler_report
        assert sch_report is not None
        assert sch_report["enabled"] is True
        assert sch_report["superblocks_detected"] > 0
        assert sch_report["scheduled_cycle_estimate"] <= sch_report["serial_cycle_estimate"]


# 5. Compaction + Scheduling Integration
def test_scheduler_compaction_integration_multiply():
    prog = make_shift_add_multiply_program(5, 4)
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_pipeline_compaction=True,
        enable_scoreboard_scheduling=True
    )
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success
    assert state.registers["R3"] == 20
    
    comp_report = report.pipeline_compaction_report
    sch_report = report.scoreboard_scheduler_report
    assert comp_report is not None
    assert sch_report is not None
    
    # Assert scheduler metadata is present on all trace steps
    has_metadata = False
    for step in report.trace_steps:
        assert hasattr(step, "scheduler_metadata")
        meta = step.scheduler_metadata
        if meta:
            has_metadata = True
            assert meta["scheduler_enabled"] is True
            assert "wavefront_id" in meta
            assert "batch_index" in meta
            
    assert has_metadata


# 6. Strict compliance Matrix check
def test_strict_pdm_waveguide_microcoded_scheduling_passes():
    vm = WideWordVirtualVM(width=32)
    prog = [
        ("MOV", "R1", 10),
        ("MOV", "R2", 20),
        ("ADD", "R3", "R1", "R2"),
        ("HALT",)
    ]
    report = vm.run_program_with_backend(prog, backend="pdm_wavecoded_strict", config=None)
    # Since virtual VM run loops use verify proofs and capability checks
    # we can run it through pdm_waveguide_microcoded_strict
    report = vm.run_program_with_backend(prog, backend="pdm_waveguide_microcoded_strict")
    assert report.success
    assert report.oracle_match
    
    # Confirm scheduler report is in metadata
    meta = report.metadata
    assert "scoreboard_scheduler_report" in meta
    sch_rep = meta["scoreboard_scheduler_report"]
    assert sch_rep["enabled"] is True
    assert sch_rep["cycle_savings"] > 0
