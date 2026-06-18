# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Optimization Benchmark + Trace Replay Harness
====================================================================
Verifies benchmark suite validity, mode matrix correctness, semantic equivalence,
cycle savings reporting, and trace replay auditing checks.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from sol_waveguide_optimization_benchmark import (
    build_waveguide_benchmark_suite,
    run_waveguide_benchmark_case,
    run_waveguide_optimization_matrix,
    summarize_waveguide_benchmark_report as summarize_waveguide_report
)
from sol_waveguide_trace_replay import (
    replay_waveguide_execution_trace,
    validate_waveguide_trace_metadata,
    validate_prefix_carry_trace_metadata,
    validate_scheduler_trace_metadata
)
from sol_wideword_computation_validation import WideWordProgramInstruction

@dataclass
class MockInstructionTrace:
    step_index: int
    pc_before: int
    pc_after: int
    instruction: Any
    layer_used: str
    sol_result: int
    oracle_result: int
    sol_flags: Dict[str, int]
    oracle_flags: Dict[str, int]
    match: bool
    branch_trace: Optional[Any] = None
    memory_trace: Optional[Any] = None
    prefix_carry_metadata: Optional[Dict[str, Any]] = None
    scheduler_metadata: Optional[Dict[str, Any]] = None

# 1. Benchmark suite construction tests
def test_benchmark_suite_construction():
    for w in (32, 64):
        suite = build_waveguide_benchmark_suite(w)
        assert len(suite) > 0
        
        # Verify case IDs are unique
        case_ids = [c["case_id"] for c in suite]
        assert len(case_ids) == len(set(case_ids)), f"Duplicate case IDs found: {case_ids}"
        
        for case in suite:
            assert "case_id" in case
            assert "description" in case
            assert "program" in case
            assert isinstance(case["program"], list)
            assert len(case["program"]) > 0

# 2. Mode matrix execution and equivalence tests
def test_benchmark_case_matrix_execution():
    suite = build_waveguide_benchmark_suite(32)
    # Pick a simple straight-line case
    case = next(c for c in suite if c["case_id"] == "straight_line_alu_mixed")
    
    rep = run_waveguide_benchmark_case(case, width=32)
    assert rep["case_id"] == "straight_line_alu_mixed"
    assert rep["trace_metadata_present"] is True
    
    modes = rep["modes"]
    for mode in ("raw_strict", "compacted_only", "scheduled_only", "compacted_and_scheduled"):
        assert mode in modes
        assert modes[mode]["success"] is True
        assert modes[mode]["cycles"] > 0
        assert "R7" in modes[mode]["registers"]
        
    # Verify semantic equivalence holds
    assert all(rep["equivalence"].values())
    
    # Scheduled only or combined modes should have cycle counts <= raw cycles
    raw_cycles = modes["raw_strict"]["cycles"]
    sch_cycles = modes["scheduled_only"]["cycles"]
    comb_cycles = modes["compacted_and_scheduled"]["cycles"]
    assert sch_cycles <= raw_cycles
    assert comb_cycles <= raw_cycles

# 3. Memory barriers and safety assertions
def test_benchmark_case_memory_barrier():
    suite = build_waveguide_benchmark_suite(32)
    case = next(c for c in suite if c["case_id"] == "memory_behavior_dynamic_barrier")
    
    rep = run_waveguide_benchmark_case(case, width=32)
    assert rep["case_id"] == "memory_behavior_dynamic_barrier"
    assert "expected barrier block" in rep["skipped_optimizations"]
    
    # Since dynamic memory STORE acts as a barrier, scheduling should not optimize across it
    # We assert correctness still holds
    assert all(rep["equivalence"].values())

# 4. Trace Replay Audits: Happy Path
def test_trace_replay_valid():
    suite = build_waveguide_benchmark_suite(32)
    case = next(c for c in suite if c["case_id"] == "straight_line_alu_independent")
    
    from sol_waveguide_control_memory_bridge import (
        build_waveguide_control_memory_state,
        execute_waveguide_control_memory_program,
        WaveguideControlMemoryBridgeConfig
    )
    
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32, enable_scoreboard_scheduling=True, enable_pipeline_compaction=True)
    report = execute_waveguide_control_memory_program(case["program"], state, config)
    
    assert report.success
    
    # Audit metadata
    meta_ok, meta_err = validate_waveguide_trace_metadata(report.trace_steps, len(case["program"]), 32)
    assert meta_ok, f"Metadata validation failed: {meta_err}"
    
    # Replay trace
    replay_ok, replay_err, final_state = replay_waveguide_execution_trace(width=32, trace_steps=report.trace_steps)
    assert replay_ok, f"Trace replay failed: {replay_err}"
    assert final_state["registers"]["R4"] == 15
    assert final_state["registers"]["R5"] == 0xFF ^ 20

# 5. Trace Replay Audits: Rejections of Malformed Data
def test_trace_replay_rejects_malformed_prefix_carry():
    inst = WideWordProgramInstruction(op="ADD", dst="R1", src1="R2", src2=1)
    
    # Malformed strategy
    step_bad_strat = MockInstructionTrace(
        step_index=0, pc_before=0, pc_after=1, instruction=inst, layer_used="pdm_waveguide_shadow",
        sol_result=10, oracle_result=10, sol_flags={}, oracle_flags={}, match=True,
        prefix_carry_metadata={
            "strategy": "incorrect_strategy",
            "lanes": 4,
            "resolved_carries": [0, 0, 0, 0],
            "final_carry_out": 0,
            "signals": [{"generate": 0, "propagate": 0} for _ in range(4)]
        }
    )
    ok, err = validate_prefix_carry_trace_metadata(step_bad_strat, width=32)
    assert not ok
    assert "Invalid prefix-carry strategy" in err
    
    # Missing lanes
    step_bad_lanes = MockInstructionTrace(
        step_index=0, pc_before=0, pc_after=1, instruction=inst, layer_used="pdm_waveguide_shadow",
        sol_result=10, oracle_result=10, sol_flags={}, oracle_flags={}, match=True,
        prefix_carry_metadata={
            "strategy": "prefix_carry_group_routing",
            "lanes": 8,  # expected 4 for 32-bit width
            "resolved_carries": [0, 0, 0, 0],
            "final_carry_out": 0,
            "signals": [{"generate": 0, "propagate": 0} for _ in range(4)]
        }
    )
    ok, err = validate_prefix_carry_trace_metadata(step_bad_lanes, width=32)
    assert not ok
    assert "does not match expected" in err

def test_trace_replay_rejects_malformed_scheduler():
    inst = WideWordProgramInstruction(op="ADD", dst="R1", src1="R2", src2=1)
    
    # Current PC not in original_pcs
    step = MockInstructionTrace(
        step_index=0, pc_before=5, pc_after=6, instruction=inst, layer_used="pdm_waveguide_shadow",
        sol_result=10, oracle_result=10, sol_flags={}, oracle_flags={}, match=True,
        scheduler_metadata={
            "scheduler_enabled": True,
            "wavefront_id": "WF_0_0",
            "batch_index": 0,
            "original_pcs": [0, 1, 2],
            "hazards_checked": True,
            "barrier_reason": None
        }
    )
    ok, err = validate_scheduler_trace_metadata(step)
    assert not ok
    assert "is not present in original_pcs" in err

def test_trace_replay_rejects_pc_mismatch():
    inst = WideWordProgramInstruction(op="MOV", dst="R1", src1=10)
    steps = [
        MockInstructionTrace(
            step_index=0, pc_before=0, pc_after=1, instruction=inst, layer_used="waveguide_register_init",
            sol_result=10, oracle_result=10, sol_flags={}, oracle_flags={}, match=True
        ),
        # Gap in PC: next step expects 2 instead of 1
        MockInstructionTrace(
            step_index=1, pc_before=2, pc_after=3, instruction=inst, layer_used="waveguide_register_init",
            sol_result=10, oracle_result=10, sol_flags={}, oracle_flags={}, match=True
        )
    ]
    ok, err, final = replay_waveguide_execution_trace(width=32, trace_steps=steps)
    assert not ok
    assert "PC mismatch" in err

def test_trace_replay_rejects_alu_result_mismatch():
    inst = WideWordProgramInstruction(op="ADD", dst="R1", src1="R2", src2=5)
    steps = [
        MockInstructionTrace(
            step_index=0, pc_before=0, pc_after=1, instruction=inst, layer_used="pdm_waveguide_shadow",
            sol_result=15, # trace says result is 15, but initial registers were 0 so 0 + 5 should be 5
            oracle_result=15, sol_flags={}, oracle_flags={}, match=True
        )
    ]
    ok, err, final = replay_waveguide_execution_trace(width=32, trace_steps=steps)
    assert not ok
    assert "Local result 5 does not match trace" in err

# 6. Entire matrix suite run
def test_full_benchmark_matrix_report():
    report = run_waveguide_optimization_matrix(widths=[32])
    assert "widths" in report
    assert len(report["cases"]) > 0
    
    summary = summarize_waveguide_report(report)
    assert summary["total_cases_run"] == len(report["cases"])
    assert summary["all_modes_verified_equivalent"] is True
    assert summary["aggregated_cycle_savings"]["compacted_only"] > 0
