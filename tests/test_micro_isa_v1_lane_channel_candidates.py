# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for the SOL Micro-ISA v1 Lane/Vector + Waveguide Channel Candidate Bridge.
"""

import pytest
from typing import List, Dict, Any

from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_micro_isa_v1_candidates import (
    validate_v1_candidate_instruction,
    V1_CANDIDATE_OPCODES
)
from sol_micro_isa_v1_lowering import (
    validate_v1_candidate_lowering_safety,
    lower_v1_candidate_to_v0
)
from sol_micro_isa_v1_spec import (
    build_micro_isa_v1_opcode_spec,
    get_micro_isa_v1_opcode_record,
    EXTENSION_COMPLIANT,
    UNSUPPORTED
)
from sol_micro_isa_v1_capability_matrix import (
    build_micro_isa_v1_capability_matrix,
    evaluate_micro_isa_v1_candidate_capability
)
from sol_strict_backend_execution_proof import build_strict_backend_support_matrix
from sol_waveguide_scoreboard_scheduler import split_waveguide_superblocks
from sol_waveguide_trace_replay import (
    validate_v1_lane_vector_trace_metadata,
    validate_v1_waveguide_channel_trace_metadata
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_waveguide_optimization_benchmark import build_waveguide_benchmark_suite

# Mock trace step class for testing replay validator
class MockTraceStep:
    def __init__(self, pc_before=0, pc_after=1, layer_used="pdm_waveguide_shadow", v1_lowering_metadata=None):
        self.pc_before = pc_before
        self.pc_after = pc_after
        self.layer_used = layer_used
        self.v1_lowering_metadata = v1_lowering_metadata

# 1. Schema Validation Tests
def test_candidate_schema_validation():
    # Valid VEC_PACK
    inst = WideWordProgramInstruction(op="VEC_PACK", dst="R1", src1=None, src2=("R2", "R3", 42, "R5"))
    assert validate_v1_candidate_instruction(inst) is True

    # Invalid VEC_PACK: wrong tuple size
    inst_bad = WideWordProgramInstruction(op="VEC_PACK", dst="R1", src1=None, src2=("R2", "R3"))
    with pytest.raises(ValueError, match="expects a 4-tuple"):
        validate_v1_candidate_instruction(inst_bad)

    # Valid VEC_UNPACK
    inst = WideWordProgramInstruction(op="VEC_UNPACK", dst="R1", src1=None, src2=("R2", "R3", "R4", "R5"))
    assert validate_v1_candidate_instruction(inst) is True

    # Invalid VEC_UNPACK: non-register destination
    inst_bad = WideWordProgramInstruction(op="VEC_UNPACK", dst="R1", src1=None, src2=("R2", "R3", 10, "R5"))
    with pytest.raises(ValueError, match="dst 2 must be a register"):
        validate_v1_candidate_instruction(inst_bad)

    # Valid VEC_BROADCAST
    inst = WideWordProgramInstruction(op="VEC_BROADCAST", dst="R1", src1="R2", src2=None)
    assert validate_v1_candidate_instruction(inst) is True

    # Valid VEC_EXTRACT
    inst = WideWordProgramInstruction(op="VEC_EXTRACT", dst="R1", src1="R2", src2=2)
    assert validate_v1_candidate_instruction(inst) is True

    # Invalid VEC_EXTRACT: out-of-bounds lane index
    inst_bad = WideWordProgramInstruction(op="VEC_EXTRACT", dst="R1", src1="R2", src2=5)
    with pytest.raises(ValueError, match="lane_index must be an integer in"):
        validate_v1_candidate_instruction(inst_bad)

    # Valid VEC_INSERT
    inst = WideWordProgramInstruction(op="VEC_INSERT", dst="R1", src1="R2", src2=(1, 42))
    assert validate_v1_candidate_instruction(inst) is True

    # Invalid VEC_INSERT: invalid lane index
    inst_bad = WideWordProgramInstruction(op="VEC_INSERT", dst="R1", src1="R2", src2=(4, "R3"))
    with pytest.raises(ValueError, match="lane_index must be an integer in"):
        validate_v1_candidate_instruction(inst_bad)

    # Valid VEC_LANE_ADD
    inst = WideWordProgramInstruction(op="VEC_LANE_ADD", dst="R1", src1="R2", src2=("R3", 0xF))
    assert validate_v1_candidate_instruction(inst) is True

    # Invalid VEC_LANE_ADD: invalid mask
    inst_bad = WideWordProgramInstruction(op="VEC_LANE_ADD", dst="R1", src1="R2", src2=("R3", 20))
    with pytest.raises(ValueError, match="mask must be an integer in"):
        validate_v1_candidate_instruction(inst_bad)

    # Valid WG_CHAN_FENCE
    inst = WideWordProgramInstruction(op="WG_CHAN_FENCE", dst=None, src1=None, src2=None)
    assert validate_v1_candidate_instruction(inst) is True

    # Invalid WG_CHAN_FENCE: unexpected operands
    inst_bad = WideWordProgramInstruction(op="WG_CHAN_FENCE", dst="R1", src1=None, src2=None)
    with pytest.raises(ValueError, match="does not expect any operands"):
        validate_v1_candidate_instruction(inst_bad)

    # Valid WG_CHAN_SEND
    inst = WideWordProgramInstruction(op="WG_CHAN_SEND", dst="CH0", src1="R1", src2=None)
    assert validate_v1_candidate_instruction(inst) is True

    # Invalid WG_CHAN_SEND: src2 not None
    inst_bad = WideWordProgramInstruction(op="WG_CHAN_SEND", dst="CH0", src1="R1", src2=42)
    with pytest.raises(ValueError, match="does not expect a src2 operand"):
        validate_v1_candidate_instruction(inst_bad)

# 2. Lowering Correctness & Safety Verification
def test_candidate_lowering_and_execution():
    # Setup state and config
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32)
    config.enable_micro_isa_v1_candidates = True
    config.micro_isa_version = "v1"

    # Test VEC_PACK execution
    # Pack R2=0x12, R3=0x34, R4=0x56, R5=0x78 -> R1
    prog = [
        ("MOV", "R2", 0x12),
        ("MOV", "R3", 0x34),
        ("MOV", "R4", 0x56),
        ("MOV", "R5", 0x78),
        ("VEC_PACK", "R1", "R2", "R3", "R4", "R5"),
        ("HALT",)
    ]
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success is True
    assert state.registers["R1"] == 0x78563412

    # Test VEC_UNPACK execution
    # Unpack R1=0x78563412 -> R2, R3, R4, R5
    state_up = build_waveguide_control_memory_state(width=32)
    prog_up = [
        ("LOAD_IMM", "R1", 0x78563412),
        ("VEC_UNPACK", "R1", "R2", "R3", "R4", "R5"),
        ("HALT",)
    ]
    report_up = execute_waveguide_control_memory_program(prog_up, state_up, config)
    assert report_up.success is True
    assert state_up.registers["R2"] == 0x12
    assert state_up.registers["R3"] == 0x34
    assert state_up.registers["R4"] == 0x56
    assert state_up.registers["R5"] == 0x78

    # Test VEC_BROADCAST execution
    # Broadcast R2=0xAB -> R1
    state_bc = build_waveguide_control_memory_state(width=32)
    prog_bc = [
        ("MOV", "R2", 0xAB),
        ("VEC_BROADCAST", "R1", "R2"),
        ("HALT",)
    ]
    report_bc = execute_waveguide_control_memory_program(prog_bc, state_bc, config)
    assert report_bc.success is True
    assert state_bc.registers["R1"] == 0xABABABAB

    # Test VEC_EXTRACT execution
    # Extract lane 2 from R2=0x78563412 -> R1
    state_ext = build_waveguide_control_memory_state(width=32)
    prog_ext = [
        ("LOAD_IMM", "R2", 0x78563412),
        ("VEC_EXTRACT", "R1", "R2", 2),
        ("HALT",)
    ]
    report_ext = execute_waveguide_control_memory_program(prog_ext, state_ext, config)
    assert report_ext.success is True
    assert state_ext.registers["R1"] == 0x56

    # Test VEC_INSERT execution
    # Insert 0x99 into lane 1 of R2=0x78563412 -> R1
    state_ins = build_waveguide_control_memory_state(width=32)
    prog_ins = [
        ("LOAD_IMM", "R2", 0x78563412),
        ("MOV", "R3", 0x99),
        ("VEC_INSERT", "R1", "R2", 1, "R3"),
        ("HALT",)
    ]
    report_ins = execute_waveguide_control_memory_program(prog_ins, state_ins, config)
    assert report_ins.success is True
    assert state_ins.registers["R1"] == 0x78569912

    # Test VEC_MASK_SELECT execution
    state_sel = build_waveguide_control_memory_state(width=32)
    prog_sel = [
        ("LOAD_IMM", "R2", 0x11223344),
        ("LOAD_IMM", "R3", 0x55667788),
        ("MOV", "R4", 0b1010),
        ("VEC_MASK_SELECT", "R1", "R4", "R2", "R3"),
        ("HALT",)
    ]
    report_sel = execute_waveguide_control_memory_program(prog_sel, state_sel, config)
    assert report_sel.success is True
    # Mask is 0b1010.
    # Lane 0 (bit 0=0) -> R3 lane 0 = 0x88
    # Lane 1 (bit 1=1) -> R2 lane 1 = 0x33
    # Lane 2 (bit 2=0) -> R3 lane 2 = 0x66
    # Lane 3 (bit 3=1) -> R2 lane 3 = 0x11
    # Expected result: 0x11663388
    assert state_sel.registers["R1"] == 0x11663388

# 3. Carry/Borrow Isolation Tests
def test_carry_borrow_isolation():
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32)
    config.enable_micro_isa_v1_candidates = True
    config.micro_isa_version = "v1"

    # Test lane ADD carry isolation:
    # A = 0x00FF00FF
    # B = 0x00010001
    # If carry bleeds, Lane 1 (bits 8-15) and Lane 3 (bits 24-31) would become 0x01 due to carries from Lane 0 and Lane 2.
    # With carry isolation, Lane 0 overflows and becomes 0x00, Lane 1 remains 0x00, Lane 2 overflows and becomes 0x00, Lane 3 remains 0x00.
    # Expected result: 0x00000000
    prog_carry = [
        ("LOAD_IMM", "R2", 0x00FF00FF),
        ("LOAD_IMM", "R3", 0x00010001),
        ("VEC_LANE_ADD", "R1", "R2", "R3", 0xF),
        ("HALT",)
    ]
    report_carry = execute_waveguide_control_memory_program(prog_carry, state, config)
    assert report_carry.success is True
    assert state.registers["R1"] == 0x00000000

    # Test lane SUB borrow isolation:
    # A = 0x00000000
    # B = 0x00010001
    # If borrow bleeds, Lane 1 and Lane 3 would borrow and wrap.
    # With borrow isolation, Lane 0 becomes 0xFF, Lane 1 remains 0x00, Lane 2 becomes 0xFF, Lane 3 remains 0x00.
    # Expected result: 0x00FF00FF
    state_borrow = build_waveguide_control_memory_state(width=32)
    prog_borrow = [
        ("LOAD_IMM", "R2", 0x00000000),
        ("LOAD_IMM", "R3", 0x00010001),
        ("VEC_LANE_SUB", "R1", "R2", "R3", 0xF),
        ("HALT",)
    ]
    report_borrow = execute_waveguide_control_memory_program(prog_borrow, state_borrow, config)
    assert report_borrow.success is True
    assert state_borrow.registers["R1"] == 0x00FF00FF

# 4. Channel Safety & Scheduling Barrier Tests
def test_channel_safety_and_scheduling_barrier():
    # Unsupported channel write (WG_CHAN_SEND) must fail safety analysis
    inst_send = WideWordProgramInstruction(op="WG_CHAN_SEND", dst="CH0", src1="R1", src2=None)
    safe, reason = validate_v1_candidate_lowering_safety(inst_send)
    assert safe is False
    assert reason == "unsupported_waveguide_channel_operation"

    # Unsupported channel read (WG_CHAN_RECV) must fail safety analysis
    inst_recv = WideWordProgramInstruction(op="WG_CHAN_RECV", dst="R1", src1="CH0", src2=None)
    safe, reason = validate_v1_candidate_lowering_safety(inst_recv)
    assert safe is False
    assert reason == "unsupported_waveguide_channel_operation"

    # WG_CHAN_FENCE must lower to a no-op MOV R0, R0
    inst_fence = WideWordProgramInstruction(op="WG_CHAN_FENCE", dst=None, src1=None, src2=None)
    lowered, label_counter, metadata = lower_v1_candidate_to_v0(inst_fence, label_counter=0)
    assert metadata["lowered_to_v0"] is True
    assert len(lowered) == 1
    assert lowered[0].op == "MOV"
    assert lowered[0].dst == "R0"
    assert lowered[0].src1 == "R0"

    # WG_CHAN_FENCE must act as a scheduling barrier splitting superblocks
    clean_insts = [
        WideWordProgramInstruction(op="ADD", dst="R1", src1="R2", src2=1),
        WideWordProgramInstruction(op="MOV", dst="R0", src1="R0"), # fence
        WideWordProgramInstruction(op="SUB", dst="R3", src1="R4", src2=1)
    ]
    # Set fence v0 PC range to [1]
    lowering_meta = [{
        "candidate_opcode": "WG_CHAN_FENCE",
        "lowered_to_v0": True,
        "v0_pc_range": [1]
    }]
    superblocks = split_waveguide_superblocks(clean_insts, windows=[], v1_lowering_metadata=lowering_meta)
    # The fence should have split the program into two superblocks
    assert len(superblocks) == 2
    assert superblocks[0].units[0].op == "ADD"
    assert superblocks[0].units[1].op == "MOV" # fence ends first superblock as barrier
    assert superblocks[1].units[0].op == "SUB"

# 5. Spec & Capability Matrix Integration
def test_spec_and_capability_matrix():
    spec = build_micro_isa_v1_opcode_spec()
    assert "VEC_PACK" in spec
    assert "WG_CHAN_FENCE" in spec
    assert "WG_CHAN_SEND" in spec

    # Verify vector pack is compliant
    assert spec["VEC_PACK"]["status"] == EXTENSION_COMPLIANT
    # Verify channel send is unsupported
    assert spec["WG_CHAN_SEND"]["status"] == UNSUPPORTED

    # Verify capability evaluation
    tier_vec = evaluate_micro_isa_v1_candidate_capability(
        backend="pdm_waveguide_microcoded_strict",
        opcode="VEC_PACK",
        spec=spec,
        strict_backend_report=None
    )
    assert tier_vec == "emulated"

    tier_send = evaluate_micro_isa_v1_candidate_capability(
        backend="pdm_waveguide_microcoded_strict",
        opcode="WG_CHAN_SEND",
        spec=spec,
        strict_backend_report=None
    )
    assert tier_send == "unsupported"

# 6. Trace Replay Integration
def test_trace_replay_audits():
    # Valid vector extract trace metadata must pass
    step_valid = MockTraceStep(pc_before=5)
    report_valid = {
        "passes": [{"pass_id": "v1_candidate_lowering", "enabled": True}],
        "v1_lowering_metadata": [{
            "candidate_opcode": "VEC_EXTRACT",
            "lowered_to_v0": True,
            "v0_pc_range": [5],
            "src2": 2 # lane 2
        }]
    }
    ok, err = validate_v1_lane_vector_trace_metadata(step_valid, report_valid)
    assert ok is True

    # Invalid vector extract trace metadata (out-of-bounds lane) must fail
    report_invalid = {
        "passes": [{"pass_id": "v1_candidate_lowering", "enabled": True}],
        "v1_lowering_metadata": [{
            "candidate_opcode": "VEC_EXTRACT",
            "lowered_to_v0": True,
            "v0_pc_range": [5],
            "src2": 5 # lane index out of bounds
        }]
    }
    ok, err = validate_v1_lane_vector_trace_metadata(step_valid, report_invalid)
    assert ok is False
    assert "lane index 5 is out of bounds" in err

    # Execution metadata for unsupported channel SEND must fail channel trace audit
    report_chan_err = {
        "passes": [{"pass_id": "v1_candidate_lowering", "enabled": True}],
        "v1_lowering_metadata": [{
            "candidate_opcode": "WG_CHAN_SEND",
            "lowered_to_v0": True,
            "v0_pc_range": [5]
        }]
    }
    ok, err = validate_v1_waveguide_channel_trace_metadata(step_valid, report_chan_err)
    assert ok is False
    assert "Unsupported channel operation WG_CHAN_SEND attempted execution" in err

# 7. Benchmark Suite Verification
def test_benchmark_suite_verification():
    suite = build_waveguide_benchmark_suite(width=32)
    case_ids = [c["case_id"] for c in suite]
    # Check that new vector cases exist
    assert "v1_vec_pack_u32" in case_ids
    assert "v1_wg_chan_fence_barrier" in case_ids
    assert "v1_wg_chan_send_rejected" in case_ids

# 8. Strict Proof Integration
def test_strict_proof_integration():
    matrix = build_strict_backend_support_matrix(results=[])
    # The microcoded strict backend support matrix should contain our new capability flags
    caps = matrix.matrix.get("pdm_waveguide_microcoded_strict", {})
    assert caps.get("supports_v1_vector_lane_candidate_lowering") == "validated"
    assert caps.get("supports_v1_waveguide_channel_fence_candidate") == "validated"
    assert caps.get("supports_v1_vec_pack_candidate") == "validated"
