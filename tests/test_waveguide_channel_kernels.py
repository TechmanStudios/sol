# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Channelized Microprogram Kernel Library + Pattern Recognizer Bridge
"""

import pytest
import json
from typing import List, Dict, Any
from dataclasses import dataclass, field

from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_waveguide_channel_kernel_library import (
    validate_waveguide_channel_kernel_descriptor,
    build_waveguide_channel_kernel_descriptor,
    get_waveguide_channel_kernel,
    summarize_waveguide_channel_kernel_library
)
from sol_waveguide_channel_kernel_recognizer import (
    detect_waveguide_channel_kernels,
    validate_waveguide_channel_kernel_match,
    summarize_waveguide_channel_kernel_recognition_report
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_waveguide_trace_replay import (
    validate_waveguide_channel_kernel_metadata,
    validate_waveguide_trace_metadata
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
class MockStep:
    step_index: int
    pc_before: int
    pc_after: int
    instruction: Any
    layer_used: str = "waveguide_channel_emulation"
    sol_result: int = 0
    oracle_result: int = 0
    sol_flags: Dict[str, int] = field(default_factory=lambda: {"zero": 0, "carry": 0, "overflow": 0, "sign": 0, "borrow": 0})
    oracle_flags: Dict[str, int] = field(default_factory=lambda: {"zero": 0, "carry": 0, "overflow": 0, "sign": 0, "borrow": 0})
    match: bool = True
    scheduler_metadata: Dict[str, Any] = None
    waveguide_channel_metadata: Dict[str, Any] = None


# 1. Kernel Library Tests
def test_kernel_library_descriptors():
    # Verify build and validation of descriptor
    desc = build_waveguide_channel_kernel_descriptor(
        kernel_id="channel_parallel_load",
        pc_range=[2, 5],
        input_channels=[0, 1],
        output_channels=[0, 1],
        input_registers=["R1", "R2"],
        output_registers=["R3", "R4"]
    )
    assert desc["kernel_id"] == "channel_parallel_load"
    assert desc["sandbox_only"] is True
    
    # Ensure JSON serializable
    serialized = json.dumps(desc)
    assert serialized is not None
    
    # Validation raises errors on invalid descriptors
    invalid_desc = dict(desc)
    invalid_desc["sandbox_only"] = False
    with pytest.raises(ValueError):
        validate_waveguide_channel_kernel_descriptor(invalid_desc)
        
    summary = summarize_waveguide_channel_kernel_library()
    assert "channel_parallel_load" in summary["supported_kernels"]
    assert get_waveguide_channel_kernel("channel_parallel_load") is not None


# 2. Pattern Recognition Tests
def test_pattern_recognition():
    # A. channel_parallel_load
    send1 = WideWordProgramInstruction(op="WG_CHAN_SEND", dst=0, src1="R1", src2=None)
    send2 = WideWordProgramInstruction(op="WG_CHAN_SEND", dst=1, src1="R2", src2=None)
    recv1 = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R3", src1=0, src2=None)
    recv2 = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R4", src1=1, src2=None)
    
    metadata = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send1, "v0_pc_range": [0]},
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send2, "v0_pc_range": [1]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv1, "v0_pc_range": [2]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv2, "v0_pc_range": [3]}
    ]
    recognized, skipped = detect_waveguide_channel_kernels(metadata, enabled=True)
    assert len(recognized) == 1
    assert recognized[0]["kernel_id"] == "channel_parallel_load"
    assert recognized[0]["pc_range"] == [0, 3]

    # B. channel_fanout
    route1 = WideWordProgramInstruction(op="WG_CHAN_ROUTE", dst=1, src1=0, src2=1)
    route2 = WideWordProgramInstruction(op="WG_CHAN_ROUTE", dst=2, src1=0, src2=1)
    recv_f1 = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R3", src1=1, src2=None)
    recv_f2 = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R4", src1=2, src2=None)
    
    metadata_fan = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send1, "v0_pc_range": [0]},
        {"candidate_opcode": "WG_CHAN_ROUTE", "original_instruction_obj": route1, "v0_pc_range": [1]},
        {"candidate_opcode": "WG_CHAN_ROUTE", "original_instruction_obj": route2, "v0_pc_range": [2]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv_f1, "v0_pc_range": [3]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv_f2, "v0_pc_range": [4]}
    ]
    rec_fan, _ = detect_waveguide_channel_kernels(metadata_fan, enabled=True)
    assert len(rec_fan) == 1
    assert rec_fan[0]["kernel_id"] == "channel_fanout"

    # C. channel_fence_order
    fence = WideWordProgramInstruction(op="WG_CHAN_FENCE", dst=None, src1=None, src2=None)
    metadata_fence = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send1, "v0_pc_range": [0]},
        {"candidate_opcode": "WG_CHAN_FENCE", "original_instruction_obj": fence, "v0_pc_range": [1]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv1, "v0_pc_range": [2]}
    ]
    rec_fence, _ = detect_waveguide_channel_kernels(metadata_fence, enabled=True)
    assert len(rec_fence) == 1
    assert rec_fence[0]["kernel_id"] == "channel_fence_order"

    # D. channel_gather
    pack = WideWordProgramInstruction(op="VEC_PACK", dst="R5", src1=None, src2=("R3", "R4", 0, 0))
    metadata_gather = metadata + [
        {"candidate_opcode": "VEC_PACK", "original_instruction_obj": pack, "v0_pc_range": [4]}
    ]
    rec_gather, _ = detect_waveguide_channel_kernels(metadata_gather, enabled=True)
    assert len(rec_gather) == 1
    assert rec_gather[0]["kernel_id"] == "channel_gather"

    # E. channel_route_chain
    route_chain = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send1, "v0_pc_range": [0]},
        {"candidate_opcode": "WG_CHAN_ROUTE", "original_instruction_obj": route1, "v0_pc_range": [1]},
        {"candidate_opcode": "WG_CHAN_ROUTE", "original_instruction_obj": WideWordProgramInstruction(op="WG_CHAN_ROUTE", dst=2, src1=1, src2=1), "v0_pc_range": [2]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv_f2, "v0_pc_range": [3]}
    ]
    rec_chain, _ = detect_waveguide_channel_kernels(route_chain, enabled=True)
    assert len(rec_chain) == 1
    assert rec_chain[0]["kernel_id"] == "channel_route_chain"


# 3. Validation & Safety (Skipping) Tests
def test_skipped_kernels():
    # Malformed dynamic channel (register ID as channel operand)
    send_dyn = WideWordProgramInstruction(op="WG_CHAN_SEND", dst="R5", src1="R1", src2=None)
    metadata_dyn = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send_dyn, "v0_pc_range": [0]}
    ]
    # Opcode signature doesn't match full kernel, so it wouldn't match.
    # Let's match a parallel load signature but with dynamic channel:
    recv_dyn = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R3", src1="R5", src2=None)
    metadata_dyn_full = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send_dyn, "v0_pc_range": [0]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv_dyn, "v0_pc_range": [1]}
    ]
    rec, skipped = detect_waveguide_channel_kernels(metadata_dyn_full, enabled=True)
    assert len(rec) == 0
    assert len(skipped) == 1
    assert skipped[0]["skip_reason"] == "dynamic_channel_id_unsupported"
    
    # Partial match
    partial_meta = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send_dyn, "v0_pc_range": [0]}
    ]
    rec, skipped = detect_waveguide_channel_kernels(partial_meta, enabled=True)
    assert len(rec) == 0

    # Recognition disabled in config
    send1 = WideWordProgramInstruction(op="WG_CHAN_SEND", dst=0, src1="R1", src2=None)
    recv1 = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R3", src1=0, src2=None)
    valid_meta = [
        {"candidate_opcode": "WG_CHAN_SEND", "original_instruction_obj": send1, "v0_pc_range": [0]},
        {"candidate_opcode": "WG_CHAN_RECV", "original_instruction_obj": recv1, "v0_pc_range": [1]}
    ]
    rec, skipped = detect_waveguide_channel_kernels(valid_meta, enabled=False)
    assert len(rec) == 0
    assert len(skipped) == 1
    assert skipped[0]["skip_reason"] == "disabled_in_config"


# 4. Control Bridge & Replay Verification
def test_bridge_kernel_replay():
    # Build control state and run kernel program
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_micro_isa_v1_candidates=True,
        enable_waveguide_channel_state=True,
        enable_channel_independence_analysis=True,
        enable_channel_kernel_recognition=True
    )
    
    # Parallel Load Program
    prog = [
        ("LOAD_IMM", "R1", 15),
        ("LOAD_IMM", "R2", 25),
        ("WG_CHAN_SEND", 0, "R1"),
        ("WG_CHAN_SEND", 1, "R2"),
        ("WG_CHAN_RECV", "R3", 0),
        ("WG_CHAN_RECV", "R4", 1),
        ("HALT",)
    ]
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success is True
    assert state.registers["R3"] == 15
    assert state.registers["R4"] == 25
    
    # Verify that the trace steps contain active kernel metadata
    kernel_steps = [s for s in report.trace_steps if s.scheduler_metadata and s.scheduler_metadata.get("channel_kernel_recognition_enabled")]
    assert len(kernel_steps) > 0
    
    # Verify that disabled kernel recognition does not emit active kernel metadata
    config_disabled = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_micro_isa_v1_candidates=True,
        enable_waveguide_channel_state=True,
        enable_channel_independence_analysis=True,
        enable_channel_kernel_recognition=False
    )
    state_dis = build_waveguide_control_memory_state(width=32)
    report_dis = execute_waveguide_control_memory_program(prog, state_dis, config_disabled)
    assert report_dis.success is True
    kernel_steps_dis = [s for s in report_dis.trace_steps if s.scheduler_metadata and s.scheduler_metadata.get("channel_kernel_recognition_enabled")]
    assert len(kernel_steps_dis) == 0
    
    # Test trace replay validators
    # Valid metadata should pass
    ok, err = validate_waveguide_trace_metadata(report.trace_steps, len(prog), 32, report.pass_manager_report)
    assert ok is True
    
    # Replay with malformed metadata (e.g. invalid pc_range) should fail
    bad_steps = [MockStep(
        step_index=0,
        pc_before=0,
        pc_after=1,
        instruction=WideWordProgramInstruction(op="WG_CHAN_SEND", dst=0, src1="R1", src2=None),
        scheduler_metadata={
            "channel_kernel_recognition_enabled": True,
            "channel_kernel_id": "channel_parallel_load",
            "kernel_pc_range": [0, -1],  # Invalid
            "kernel_wavefronts": ["WF_0_0"],
            "sandbox_only": True,
            "kernel_equivalence_required": True
        }
    )]
    pm_rep = {"enable_channel_kernel_recognition": True}
    ok, err = validate_waveguide_channel_kernel_metadata(bad_steps[0], bad_steps, pm_rep, 32)
    assert ok is False
    
    # Replay with disabled config but active metadata should fail
    pm_rep_disabled = {"enable_channel_kernel_recognition": False}
    ok, err = validate_waveguide_channel_kernel_metadata(report.trace_steps[2], report.trace_steps, pm_rep_disabled, 32)
    assert ok is False


# 5. Benchmark Suite Integration
def test_benchmark_integration():
    suite = build_waveguide_benchmark_suite(32)
    # Ensure our 9 new v1_kernel cases are present
    kernel_cases = [c for c in suite if c["case_id"].startswith("v1_kernel_")]
    assert len(kernel_cases) >= 9
    
    # Run a kernel benchmark case
    case = next(c for c in suite if c["case_id"] == "v1_kernel_channel_parallel_load")
    res = run_waveguide_benchmark_case(case, 32)
    assert res["equivalence"]["full_optimized"] is True
    assert res["v1_details"]["lowering_strategy"] is not None


# 6. Spec, Capability Matrix, and Proof Matrix Tests
def test_spec_and_matrices():
    # V1 spec matrix includes kernel properties
    spec = build_micro_isa_v1_opcode_spec()
    assert spec is not None
    
    # V1 capability matrix includes optional kernel support properties
    mock_matrix_summary = summarize_micro_isa_v1_capability_matrix(
        build_micro_isa_v1_capability_matrix(spec, None)
    )
    assert mock_matrix_summary["supports_v1_channel_kernel_library"] is True
    assert mock_matrix_summary["supports_v1_channel_kernel_recognition"] is True
    
    # Proof matrix has optional kernel capabilities validated
    proof_matrix = build_strict_backend_support_matrix([]).matrix
    assert "pdm_waveguide_microcoded_strict" in proof_matrix
    assert proof_matrix["pdm_waveguide_microcoded_strict"]["supports_v1_channelized_microprogram_kernel_library"] == "validated"
    assert proof_matrix["pdm_waveguide_microcoded_strict"]["supports_v1_channelized_kernel_pattern_recognition"] == "validated"
    assert proof_matrix["pdm_waveguide_microcoded_strict"]["supports_v1_channel_kernel_trace_replay"] == "validated"
