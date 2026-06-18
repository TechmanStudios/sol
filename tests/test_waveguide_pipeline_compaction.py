# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Pipeline Compaction
==========================================
Verifies static analysis, prefix carry routing, semantic equivalence of MUL/DIV,
flag preservation, and trace details.
"""

import pytest
from sol_wideword_computation_validation import WideWordProgramInstruction, mask_for_width
from sol_waveguide_pipeline_compaction import (
    build_waveguide_prefix_carry_routes,
    analyze_waveguide_microcode_chain,
    build_waveguide_prefix_carry_routes,
    validate_waveguide_compaction_equivalence
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
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

# 1. Basic analyzer tests
def test_compaction_analyzer_detects_loops():
    # A simple loop
    prog = [
        ("MOV", "R1", 10),
        "loop:",
        ("SUB", "R1", "R1", 1),
        ("CMP", "R1", 0),
        ("JNZ", "loop"),
        ("HALT",)
    ]
    windows = analyze_waveguide_microcode_chain(prog)
    assert len(windows) == 1
    w = windows[0]
    assert w.start_pc == 1  # SUB starts loop
    assert w.end_pc == 3    # JNZ ends loop
    assert w.window_type == "generic_loop"
    assert not w.unsafe

def test_compaction_analyzer_skips_unsafe_memory():
    # Loop containing STORE
    prog = [
        ("MOV", "R1", 10),
        "loop:",
        ("STORE", "R1", "R2"),
        ("SUB", "R1", "R1", 1),
        ("JNZ", "loop"),
        ("HALT",)
    ]
    windows = analyze_waveguide_microcode_chain(prog)
    assert len(windows) == 1
    w = windows[0]
    assert w.unsafe
    assert "unsafe memory operation" in w.unsafe_reason

def test_compaction_analyzer_skips_unsafe_opcode():
    # Loop containing unknown opcode
    prog = [
        ("MOV", "R1", 10),
        "loop:",
        ("UNKNOWN_OP", "R1"),
        ("SUB", "R1", "R1", 1),
        ("JNZ", "loop"),
        ("HALT",)
    ]
    windows = analyze_waveguide_microcode_chain(prog)
    assert len(windows) == 1
    w = windows[0]
    assert w.unsafe
    assert "unknown or unsupported opcode" in w.unsafe_reason


# 2. Multiplication equivalence
@pytest.mark.parametrize("a, b", [
    (0, 0),
    (1, 0),
    (0, 1),
    (1, 1),
    (2, 4),
    (5, 7),
    (15, 6),
    (0xFF, 0xFF), # max 8-bit values
    (12345, 6789), # larger values
])
def test_compaction_multiplication_equivalence(a, b):
    for w in (32, 64):
        prog = make_shift_add_multiply_program(a, b)
        
        # Uncompacted Run
        state_unc = build_waveguide_control_memory_state(width=w)
        config_unc = WaveguideControlMemoryBridgeConfig(width=w, enable_pipeline_compaction=False)
        report_unc = execute_waveguide_control_memory_program(prog, state_unc, config_unc)
        
        # Compacted Run
        state_comp = build_waveguide_control_memory_state(width=w)
        config_comp = WaveguideControlMemoryBridgeConfig(width=w, enable_pipeline_compaction=True)
        report_comp = execute_waveguide_control_memory_program(prog, state_comp, config_comp)
        
        assert report_unc.success
        assert report_comp.success
        assert state_unc.registers["R3"] == state_comp.registers["R3"]
        assert state_unc.flags == state_comp.flags
        
        # Verify compaction report details
        comp_report = report_comp.pipeline_compaction_report
        assert comp_report is not None
        assert comp_report["enabled"] is True
        assert comp_report["windows_compacted"] > 0
        assert comp_report["original_cycles"] >= comp_report["compacted_cycles"]


# 3. Division equivalence
@pytest.mark.parametrize("n, d", [
    (10, 1),
    (10, 10),
    (5, 10),  # dividend smaller than divisor
    (10, 3),  # non-even division
    (0xFF, 0xFF),
    (0, 5),   # zero dividend
])
def test_compaction_division_equivalence(n, d):
    for w in (32, 64):
        prog = make_restoring_division_program(n, d)
        
        # Uncompacted
        state_unc = build_waveguide_control_memory_state(width=w)
        config_unc = WaveguideControlMemoryBridgeConfig(width=w, enable_pipeline_compaction=False)
        report_unc = execute_waveguide_control_memory_program(prog, state_unc, config_unc)
        
        # Compacted
        state_comp = build_waveguide_control_memory_state(width=w)
        config_comp = WaveguideControlMemoryBridgeConfig(width=w, enable_pipeline_compaction=True)
        report_comp = execute_waveguide_control_memory_program(prog, state_comp, config_comp)
        
        assert report_unc.success
        assert report_comp.success
        assert state_unc.registers["R3"] == state_comp.registers["R3"]  # quotient
        assert state_unc.registers["R4"] == state_comp.registers["R4"]  # remainder
        assert state_unc.flags == state_comp.flags

def test_compaction_division_by_zero_handling():
    # Verify divide by zero terminates cleanly on cycle limit by raising TimeoutError
    prog = make_restoring_division_program(10, 0)
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32, enable_pipeline_compaction=True)
    with pytest.raises(TimeoutError):
        execute_waveguide_control_memory_program(prog, state, config)


# 4. Flag preservation
def test_compaction_flag_preservation_popcount():
    # Run popcount and check Z/C/N/B flags match
    prog = make_popcount_program(0xF5, 32)
    
    state_unc = build_waveguide_control_memory_state(width=32)
    config_unc = WaveguideControlMemoryBridgeConfig(width=32, enable_pipeline_compaction=False)
    report_unc = execute_waveguide_control_memory_program(prog, state_unc, config_unc)
    
    state_comp = build_waveguide_control_memory_state(width=32)
    config_comp = WaveguideControlMemoryBridgeConfig(width=32, enable_pipeline_compaction=True)
    report_comp = execute_waveguide_control_memory_program(prog, state_comp, config_comp)
    
    assert report_unc.success
    assert report_comp.success
    assert state_unc.registers["R2"] == state_comp.registers["R2"]
    assert state_unc.flags == state_comp.flags


# 5. Trace preservation
def test_compaction_trace_metadata_preservation():
    prog = make_sum_loop_program(10)
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32, enable_pipeline_compaction=True)
    report = execute_waveguide_control_memory_program(prog, state, config)
    
    assert report.success
    comp_report = report.pipeline_compaction_report
    assert comp_report is not None
    assert comp_report["windows_detected"] == 1
    assert comp_report["windows_compacted"] == 1
    assert comp_report["original_cycles"] > 0
    assert comp_report["compacted_cycles"] > 0
    assert comp_report["cycle_savings"] == comp_report["original_cycles"] - comp_report["compacted_cycles"]
    
    # Check that trace steps generated inside compaction have metadata attached
    has_prefix_metadata = False
    for step in report.trace_steps:
        if hasattr(step, "prefix_carry_metadata") and step.prefix_carry_metadata is not None:
            has_prefix_metadata = True
            meta = step.prefix_carry_metadata
            assert meta["strategy"] == "prefix_carry_group_routing"
            assert "resolved_carries" in meta
            assert "final_carry_out" in meta
            break
            
    assert has_prefix_metadata, "No trace step has prefix carry metadata attached"
