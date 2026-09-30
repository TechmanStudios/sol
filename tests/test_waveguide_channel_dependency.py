# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Channel Independence Analysis + Channelized Kernel Scheduler Bridge
"""

import pytest
from typing import List, Dict, Any
from dataclasses import dataclass, field

from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_waveguide_channel_dependency import (
    build_waveguide_channel_access,
    build_waveguide_channel_dependency_record,
    classify_waveguide_channel_hazard,
    validate_waveguide_channel_batch_safety,
    summarize_waveguide_channel_dependency_report
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_waveguide_trace_replay import (
    replay_waveguide_execution_trace,
    validate_waveguide_channel_dependency_metadata
)
from sol_waveguide_optimization_benchmark import (
    build_waveguide_benchmark_suite,
    run_waveguide_benchmark_case
)
from sol_micro_isa_v1_spec import build_micro_isa_v1_opcode_spec
from sol_micro_isa_v1_capability_matrix import (
    build_micro_isa_v1_capability_matrix,
    summarize_micro_isa_v1_capability_matrix
)
from sol_strict_backend_execution_proof import (
    build_strict_backend_support_matrix,
    StrictBackendProgramResult
)


@dataclass
class MockInstructionTraceStep:
    step_index: int
    pc_before: int
    pc_after: int
    instruction: Any
    layer_used: str
    sol_result: int
    oracle_result: int
    sol_flags: Dict[str, int] = field(default_factory=lambda: {"zero": 0, "carry": 0, "overflow": 0, "sign": 0, "borrow": 0})
    oracle_flags: Dict[str, int] = field(default_factory=lambda: {"zero": 0, "carry": 0, "overflow": 0, "sign": 0, "borrow": 0})
    match: bool = True
    scheduler_metadata: Dict[str, Any] = None
    waveguide_channel_metadata: Dict[str, Any] = None


# 1. Channel Access Metadata Tests
def test_channel_access_metadata():
    # SEND metadata
    send_inst = WideWordProgramInstruction(op="WG_CHAN_SEND", dst=2, src1="R5", src2=None)
    metadata = [{
        "candidate_opcode": "WG_CHAN_SEND",
        "original_instruction_obj": send_inst,
        "v0_pc_range": [5]
    }]
    access = build_waveguide_channel_access(None, 5, metadata)
    assert access is not None
    assert access["opcode"] == "WG_CHAN_SEND"
    assert access["writes_channels"] == [2]
    assert access["reads_registers"] == ["R5"]

    # RECV metadata
    recv_inst = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R7", src1=3, src2=None)
    metadata = [{
        "candidate_opcode": "WG_CHAN_RECV",
        "original_instruction_obj": recv_inst,
        "v0_pc_range": [10]
    }]
    access = build_waveguide_channel_access(None, 10, metadata)
    assert access is not None
    assert access["opcode"] == "WG_CHAN_RECV"
    assert access["reads_channels"] == [3]
    assert access["writes_registers"] == ["R7"]

    # ROUTE metadata
    route_inst = WideWordProgramInstruction(op="WG_CHAN_ROUTE", dst=4, src1=2, src2="R3")
    metadata = [{
        "candidate_opcode": "WG_CHAN_ROUTE",
        "original_instruction_obj": route_inst,
        "v0_pc_range": [12]
    }]
    access = build_waveguide_channel_access(None, 12, metadata)
    assert access is not None
    assert access["opcode"] == "WG_CHAN_ROUTE"
    assert access["reads_channels"] == [2]
    assert access["writes_channels"] == [4]
    assert access["reads_registers"] == ["R3"]

    # FENCE metadata
    fence_inst = WideWordProgramInstruction(op="WG_CHAN_FENCE", dst=None, src1=None, src2=None)
    metadata = [{
        "candidate_opcode": "WG_CHAN_FENCE",
        "original_instruction_obj": fence_inst,
        "v0_pc_range": [15]
    }]
    access = build_waveguide_channel_access(None, 15, metadata)
    assert access is not None
    assert access["opcode"] == "WG_CHAN_FENCE"
    assert access["is_global_barrier"] is True


# 2. Hazard Classification Tests
def test_channel_hazard_classification():
    h_send_c0 = {
        "pc": 1, "opcode": "WG_CHAN_SEND", "reads_channels": [], "writes_channels": [0],
        "reads_registers": ["R5"], "writes_registers": [], "is_global_barrier": False
    }
    h_send_c1 = {
        "pc": 2, "opcode": "WG_CHAN_SEND", "reads_channels": [], "writes_channels": [1],
        "reads_registers": ["R6"], "writes_registers": [], "is_global_barrier": False
    }
    h_send_c0_dup = {
        "pc": 3, "opcode": "WG_CHAN_SEND", "reads_channels": [], "writes_channels": [0],
        "reads_registers": ["R7"], "writes_registers": [], "is_global_barrier": False
    }
    h_recv_c0_r1 = {
        "pc": 4, "opcode": "WG_CHAN_RECV", "reads_channels": [0], "writes_channels": [],
        "reads_registers": [], "writes_registers": ["R1"], "is_global_barrier": False
    }
    h_recv_c1_r1 = {
        "pc": 5, "opcode": "WG_CHAN_RECV", "reads_channels": [1], "writes_channels": [],
        "reads_registers": [], "writes_registers": ["R1"], "is_global_barrier": False
    }
    h_recv_c1_r2 = {
        "pc": 6, "opcode": "WG_CHAN_RECV", "reads_channels": [1], "writes_channels": [],
        "reads_registers": [], "writes_registers": ["R2"], "is_global_barrier": False
    }
    h_route_c0_to_c1 = {
        "pc": 7, "opcode": "WG_CHAN_ROUTE", "reads_channels": [0], "writes_channels": [1],
        "reads_registers": [], "writes_registers": [], "is_global_barrier": False
    }
    h_fence = {
        "pc": 8, "opcode": "WG_CHAN_FENCE", "reads_channels": [], "writes_channels": [],
        "reads_registers": [], "writes_registers": [], "is_global_barrier": True
    }

    # SEND/SEND diff channel -> no hazard
    assert classify_waveguide_channel_hazard(h_send_c0, h_send_c1) == "NO_CHANNEL_HAZARD"

    # SEND/SEND same channel -> WAW
    assert classify_waveguide_channel_hazard(h_send_c0, h_send_c0_dup) == "CHANNEL_WAW"

    # SEND/RECV same channel -> RAW
    assert classify_waveguide_channel_hazard(h_send_c0, h_recv_c0_r1) == "CHANNEL_RAW"

    # RECV/RECV diff channels diff regs -> no hazard
    assert classify_waveguide_channel_hazard(h_recv_c0_r1, h_recv_c1_r2) == "NO_CHANNEL_HAZARD"

    # RECV/RECV diff channels same reg -> register write conflict (CHANNEL_UNKNOWN)
    assert classify_waveguide_channel_hazard(h_recv_c0_r1, h_recv_c1_r1) == "CHANNEL_UNKNOWN"

    # ROUTE/RECV sharing channel -> conflict
    assert classify_waveguide_channel_hazard(h_route_c0_to_c1, h_recv_c1_r2) == "CHANNEL_RAW"

    # FENCE -> global barrier hazard
    assert classify_waveguide_channel_hazard(h_send_c0, h_fence) == "CHANNEL_GLOBAL_FENCE"


# 3. Scheduler Integration Tests
def test_scheduler_independent_batching():
    # Program with independent sends
    prog = [
        ("LOAD_IMM", "R1", 10),
        ("LOAD_IMM", "R2", 20),
        ("WG_CHAN_SEND", 0, "R1"),
        ("WG_CHAN_SEND", 1, "R2"),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_micro_isa_v1_candidates=True,
        enable_waveguide_channel_state=True,
        enable_scoreboard_scheduling=True,
        enable_channel_independence_analysis=True
    )
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success

    # Verify that the two sends are batched in the same wavefront
    sends_wf = []
    for step in report.trace_steps:
        c_meta = getattr(step, "waveguide_channel_metadata", None)
        if c_meta and c_meta.get("channel_opcode") == "WG_CHAN_SEND":
            meta = step.scheduler_metadata
            assert meta is not None
            assert meta["channel_dependency_analysis_enabled"] is True
            sends_wf.append(meta["channel_wavefront_id"])
    
    assert len(sends_wf) == 2
    assert sends_wf[0] == sends_wf[1], "Independent sends should share the same wavefront ID"


def test_scheduler_dependent_no_batching():
    # Program with dependent send/receive
    prog = [
        ("LOAD_IMM", "R1", 10),
        ("WG_CHAN_SEND", 0, "R1"),
        ("WG_CHAN_RECV", "R2", 0),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_micro_isa_v1_candidates=True,
        enable_waveguide_channel_state=True,
        enable_scoreboard_scheduling=True,
        enable_channel_independence_analysis=True
    )
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success

    # Verify they have different wavefront IDs
    ops_wf = {}
    for step in report.trace_steps:
        c_meta = getattr(step, "waveguide_channel_metadata", None)
        if c_meta:
            op = c_meta.get("channel_opcode")
            if op in ("WG_CHAN_SEND", "WG_CHAN_RECV"):
                ops_wf[op] = step.scheduler_metadata["channel_wavefront_id"]

    assert ops_wf["WG_CHAN_SEND"] != ops_wf["WG_CHAN_RECV"], "RAW dependent channel ops must be scheduled in separate wavefronts"


# 4. Control Bridge Integration
def test_control_bridge_equivalence():
    # Test that enabled vs disabled channel independence analysis matches register state
    prog = [
        ("LOAD_IMM", "R1", 42),
        ("WG_CHAN_SEND", 2, "R1"),
        ("WG_CHAN_RECV", "R3", 2),
        ("HALT",)
    ]

    # Enabled
    state_enabled = build_waveguide_control_memory_state(width=32)
    cfg_enabled = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_micro_isa_v1_candidates=True,
        enable_waveguide_channel_state=True,
        enable_scoreboard_scheduling=True,
        enable_channel_independence_analysis=True
    )
    rep_enabled = execute_waveguide_control_memory_program(prog, state_enabled, cfg_enabled)

    # Disabled
    state_disabled = build_waveguide_control_memory_state(width=32)
    cfg_disabled = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_micro_isa_v1_candidates=True,
        enable_waveguide_channel_state=True,
        enable_scoreboard_scheduling=True,
        enable_channel_independence_analysis=False
    )
    rep_disabled = execute_waveguide_control_memory_program(prog, state_disabled, cfg_disabled)

    assert rep_enabled.success
    assert rep_disabled.success
    assert state_enabled.registers["R3"] == state_disabled.registers["R3"] == 42
    assert state_enabled.channel_state["channels"][2]["value"] == state_disabled.channel_state["channels"][2]["value"]


# 5. Trace Replay Integration
def test_trace_replay_validation():
    # Happy path
    inst_send = WideWordProgramInstruction(op="WG_CHAN_SEND", dst=0, src1="R1", src2=None)
    step1 = MockInstructionTraceStep(
        step_index=0, pc_before=2, pc_after=3, instruction=inst_send, layer_used="pdm_waveguide_shadow",
        sol_result=0, oracle_result=0,
        scheduler_metadata={
            "channel_dependency_analysis_enabled": True,
            "channel_wavefront_id": 1,
            "channel_ops_batched": ["WG_CHAN_SEND", "WG_CHAN_SEND"],
            "channel_hazards_checked": True,
            "channel_hazard_result": "NO_CHANNEL_HAZARD"
        },
        waveguide_channel_metadata={
            "channel_opcode": "WG_CHAN_SEND",
            "channel_id": 0
        }
    )
    
    inst_send2 = WideWordProgramInstruction(op="WG_CHAN_SEND", dst=1, src1="R2", src2=None)
    step2 = MockInstructionTraceStep(
        step_index=1, pc_before=3, pc_after=4, instruction=inst_send2, layer_used="pdm_waveguide_shadow",
        sol_result=0, oracle_result=0,
        scheduler_metadata={
            "channel_dependency_analysis_enabled": True,
            "channel_wavefront_id": 1,
            "channel_ops_batched": ["WG_CHAN_SEND", "WG_CHAN_SEND"],
            "channel_hazards_checked": True,
            "channel_hazard_result": "NO_CHANNEL_HAZARD"
        },
        waveguide_channel_metadata={
            "channel_opcode": "WG_CHAN_SEND",
            "channel_id": 1
        }
    )

    steps = [step1, step2]
    
    # Valid metadata accepted
    ok, err = validate_waveguide_channel_dependency_metadata(step1, steps, enable_channel_independence_analysis=True)
    assert ok, f"Expected validation success: {err}"

    # Conflicting batched channel ops rejected (mutate step2 channel to 0 so they conflict on WAW)
    step2.waveguide_channel_metadata["channel_id"] = 0
    ok, err = validate_waveguide_channel_dependency_metadata(step1, steps, enable_channel_independence_analysis=True)
    assert not ok
    assert "Hazard conflict CHANNEL_WAW" in err

    # Disabled feature emitting active metadata rejected
    step2.waveguide_channel_metadata["channel_id"] = 1
    ok, err = validate_waveguide_channel_dependency_metadata(step1, steps, enable_channel_independence_analysis=False)
    assert not ok
    assert "metadata is active but feature is disabled" in err


# 6. Benchmark Integration
def test_benchmark_integration():
    suite = build_waveguide_benchmark_suite(32)
    case_ids = [c["case_id"] for c in suite]

    # Verify new benchmark cases exist
    expected_cases = [
        "v1_chan_independent_sends_batch",
        "v1_chan_independent_recvs_batch",
        "v1_chan_send_recv_different_channels_batch",
        "v1_chan_send_recv_same_channel_no_batch",
        "v1_chan_route_independent_batch",
        "v1_chan_route_conflict_no_batch",
        "v1_chan_fence_splits_wavefront",
        "v1_chan_mixed_kernel_pipeline",
        "v1_chan_dependency_disabled_matches_barrier_mode"
    ]
    for exp in expected_cases:
        assert exp in case_ids

    # Run one independent and one dependent case to verify savings and equivalence
    rep_batch = run_waveguide_benchmark_case(
        next(c for c in suite if c["case_id"] == "v1_chan_independent_sends_batch"),
        width=32
    )
    assert rep_batch["equivalence"]["full_optimized"] is True
    # independent sends should show cycle reduction when scheduled
    scheduled_cycles = rep_batch["modes"]["scheduled_only"]["cycles"]
    raw_cycles = rep_batch["modes"]["raw_strict"]["cycles"]
    assert scheduled_cycles < raw_cycles, f"Independent sends should compile to fewer cycles under scheduling: {scheduled_cycles} vs {raw_cycles}"

    # Verify fence order case
    rep_fence = run_waveguide_benchmark_case(
        next(c for c in suite if c["case_id"] == "v1_chan_fence_splits_wavefront"),
        width=32
    )
    assert rep_fence["equivalence"]["full_optimized"] is True


# 7. Simulation Acceleration Interaction
def test_simulation_acceleration_interaction():
    suite = build_waveguide_benchmark_suite(32)
    case = next(c for c in suite if c["case_id"] == "v1_chan_mixed_kernel_pipeline")
    rep = run_waveguide_benchmark_case(case, width=32)
    
    # Verify deterministic ordering and mode success
    assert rep["equivalence"]["full_optimized"] is True
    for mode_name, mode in rep["modes"].items():
        if mode.get("success"):
            assert mode["trace_valid"] is True, f"Mode {mode_name} trace invalid: {mode.get('trace_error')}"


# 8. Spec / Matrix / Proof Checks
def test_spec_matrix_proof_capabilities():
    # Spec capability addition
    spec = build_micro_isa_v1_opcode_spec()
    assert "WG_CHAN_SEND" in spec
    assert "WG_CHAN_RECV" in spec
    assert "WG_CHAN_ROUTE" in spec
    assert "WG_CHAN_FENCE" in spec

    # Matrix capability summary addition
    # Create fake matrix
    class DummyMatrix:
        matrix = {
            "pdm_waveguide_microcoded_strict": {
                "WG_CHAN_SEND": "emulated",
                "WG_CHAN_RECV": "emulated",
                "WG_CHAN_ROUTE": "emulated",
                "WG_CHAN_FENCE": "emulated",
                "SELECT": "emulated",
            }
        }
    summary = summarize_micro_isa_v1_capability_matrix(DummyMatrix())
    assert summary.get("supports_v1_channel_independence_analysis") is True
    assert summary.get("supports_v1_channelized_kernel_scheduling") is True

    # Strict Proof Support Matrix addition
    # Create mock result
    res = StrictBackendProgramResult(
        backend_requested="pdm_waveguide_microcoded_strict",
        backend_used="pdm_waveguide_microcoded_strict",
        strict_mode=True,
        width=32,
        program_name="dummy",
        instruction_count=5,
        passed_instruction_count=5,
        failed_instruction_count=0,
        fallback_instruction_count=0,
        unsupported_instruction_count=0,
        unavailable_instruction_count=0,
        oracle_match=True,
        all_instructions_used_requested_backend=True,
        validated=True,
        unavailable_reason=None,
        first_failure=None
    )
    proof_matrix = build_strict_backend_support_matrix([res])
    assert "supports_v1_channel_dependency_analysis" in proof_matrix.matrix["pdm_waveguide_microcoded_strict"]
    assert "supports_v1_channel_independent_wavefront_batching" in proof_matrix.matrix["pdm_waveguide_microcoded_strict"]
    assert "supports_v1_channelized_kernel_benchmarks" in proof_matrix.matrix["pdm_waveguide_microcoded_strict"]
