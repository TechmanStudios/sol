# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Verification suite for the SOL Micro-ISA v1 Candidate Opcode + v0 Lowering Bridge.
"""

import pytest
from typing import Dict, Any, List

from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_micro_isa_v1_candidates import (
    validate_v1_candidate_instruction,
    V1_CANDIDATE_OPCODES
)
from sol_micro_isa_v1_lowering import (
    validate_v1_candidate_lowering_safety,
    lower_v1_candidate_to_v0,
    validate_v1_lowering_equivalence
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    WaveguideControlMemoryBridgeConfig,
    execute_waveguide_control_memory_program
)
from sol_waveguide_optimization_profile import (
    build_waveguide_optimization_profile,
    V1_CANDIDATE_EXPERIMENTAL
)
from sol_waveguide_optimization_pass_manager import run_waveguide_optimization_passes
from sol_waveguide_trace_replay import (
    validate_waveguide_trace_metadata,
    replay_waveguide_execution_trace
)
from sol_strict_backend_execution_proof import build_strict_backend_support_matrix

# 1. Candidate Schema Validation Tests
def test_v1_candidate_schema_validation():
    # SELECT valid
    inst_sel = WideWordProgramInstruction(op="SELECT", dst="R1", src1="R2", src2=("R3", "R4"))
    assert validate_v1_candidate_instruction(inst_sel) is True

    # CMOV valid
    inst_cmov = WideWordProgramInstruction(op="CMOVZ", dst="R1", src1="R2")
    assert validate_v1_candidate_instruction(inst_cmov) is True

    # PLOAD_RO valid
    inst_pload = WideWordProgramInstruction(op="PLOAD_RO", dst="R1", src1="R2", src2=(10, 20))
    assert validate_v1_candidate_instruction(inst_pload) is True

    # Unknown candidate
    inst_unk = WideWordProgramInstruction(op="UNKNOWN_OP", dst="R1", src1="R2")
    with pytest.raises(ValueError, match="Unknown v1 candidate opcode"):
        validate_v1_candidate_instruction(inst_unk)

    # Malformed SELECT (missing src2 tuple)
    inst_mal_sel = WideWordProgramInstruction(op="SELECT", dst="R1", src1="R2", src2="R3")
    with pytest.raises(ValueError, match="SELECT expects a tuple/list"):
        validate_v1_candidate_instruction(inst_mal_sel)


# 2. Lowering Semantics & Correctness Tests
def test_v1_candidate_lowering():
    # SELECT true lowers to v0 and matches expected dst
    prog_sel_true = [
        ("MOV", "R2", 1),
        ("SELECT", "R1", "R2", 100, 200),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32, enable_micro_isa_v1_candidates=True)
    report = execute_waveguide_control_memory_program(prog_sel_true, state, config)
    assert report.success is True
    assert state.registers["R1"] == 100

    # SELECT false lowers to v0 and matches expected dst
    prog_sel_false = [
        ("MOV", "R2", 0),
        ("SELECT", "R1", "R2", 100, 200),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog_sel_false, state, config)
    assert report.success is True
    assert state.registers["R1"] == 200

    # CMOVZ taken preserves expected semantics
    prog_cmovz_taken = [
        ("MOV", "R1", 100),
        ("MOV", "R2", 0),
        ("CMP", "R2", 0), # zero flag set to 1
        ("CMOVZ", "R1", 200),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog_cmovz_taken, state, config)
    assert report.success is True
    assert state.registers["R1"] == 200

    # CMOVZ not taken preserves dst
    prog_cmovz_not_taken = [
        ("MOV", "R1", 100),
        ("MOV", "R2", 1),
        ("CMP", "R2", 0), # zero flag set to 0
        ("CMOVZ", "R1", 200),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog_cmovz_not_taken, state, config)
    assert report.success is True
    assert state.registers["R1"] == 100

    # PREFIX_ADD matches v0 arithmetic flags and result
    prog_pref_add = [
        ("MOV", "R2", 0xFFFFFFFF),
        ("PREFIX_ADD", "R1", "R2", 1),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog_pref_add, state, config)
    assert report.success is True
    assert state.registers["R1"] == 0
    assert state.flags["carry"] == 1
    assert state.flags["zero"] == 1


# 3. Lowering Safety & Rejections
def test_v1_lowering_safety():
    # PLOAD_RO with static addresses accepted
    inst_pload_safe = WideWordProgramInstruction(op="PLOAD_RO", dst="R1", src1="R2", src2=(10, 20))
    is_safe, reason = validate_v1_candidate_lowering_safety(inst_pload_safe)
    assert is_safe is True
    assert reason is None

    # PLOAD_RO with dynamic register address rejected
    inst_pload_unsafe = WideWordProgramInstruction(op="PLOAD_RO", dst="R1", src1="R2", src2=("R3", "R4"))
    is_safe, reason = validate_v1_candidate_lowering_safety(inst_pload_unsafe)
    assert is_safe is False
    assert reason == "dynamic_address_unknown_alias"

    # v1 candidate mode disabled rejects v1 opcodes
    prog = [
        ("SELECT", "R1", "R2", 100, 200),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    config = WaveguideControlMemoryBridgeConfig(width=32, enable_micro_isa_v1_candidates=False)
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success is False
    assert any("Execution error: unsupported_instruction" in m["failure_reason"] for m in report.mismatches)


# 4. Control-Memory & State Equivalence
def test_control_memory_equivalence():
    prog_v1 = [
        ("MOV", "R2", 1),
        ("SELECT", "R1", "R2", 100, 200),
        ("HALT",)
    ]
    prog_v0 = [
        ("MOV", "R2", 1),
        ("CMP", "R2", 0),
        ("JNZ", "L_true"),
        ("LOAD_IMM", "R1", 200),
        ("JMP", "L_end"),
        "L_true:",
        ("LOAD_IMM", "R1", 100),
        "L_end:",
        ("HALT",)
    ]
    
    state_v1 = build_waveguide_control_memory_state(width=32)
    config_v1 = WaveguideControlMemoryBridgeConfig(width=32, enable_micro_isa_v1_candidates=True)
    report_v1 = execute_waveguide_control_memory_program(prog_v1, state_v1, config_v1)
    
    state_v0 = build_waveguide_control_memory_state(width=32)
    config_v0 = WaveguideControlMemoryBridgeConfig(width=32, enable_micro_isa_v1_candidates=False)
    report_v0 = execute_waveguide_control_memory_program(prog_v0, state_v0, config_v0)
    
    assert report_v1.success is True
    assert report_v0.success is True
    assert validate_v1_lowering_equivalence(state_v1, state_v0) is True


# 5. Pass Manager Order & Report Validation
def test_pass_manager_integration():
    config = WaveguideControlMemoryBridgeConfig(width=32, enable_micro_isa_v1_candidates=True)
    prog = [
        ("SELECT", "R1", "R2", 100, 200),
        ("HALT",)
    ]
    clean_insts, labels, _, _, _, _, report, _ = run_waveguide_optimization_passes(prog, config, 32)
    
    # Check that v1 lowering is enabled
    passes = report["passes"]
    v1_pass = next((p for p in passes if p["pass_id"] == "v1_candidate_lowering"), None)
    assert v1_pass is not None
    assert v1_pass["enabled"] is True
    assert v1_pass["applied"] is True
    
    # Check order: v1_candidate_lowering is Pass 2 (index 1 in run_passes)
    run_passes = [p["pass_id"] for p in passes if p["enabled"]]
    assert run_passes[0] == "program_adaptation"
    assert run_passes[1] == "v1_candidate_lowering"
    
    # Verify metadata collection
    assert "v1_lowering_metadata" in report
    metadata = report["v1_lowering_metadata"]
    assert len(metadata) == 1
    assert metadata[0]["candidate_opcode"] == "SELECT"
    assert metadata[0]["lowered_to_v0"] is True


# 6. Trace Replay Metadata Validation
def test_trace_replay_validation():
    config = WaveguideControlMemoryBridgeConfig(width=32, enable_micro_isa_v1_candidates=True)
    prog = [
        ("MOV", "R2", 1),
        ("SELECT", "R1", "R2", 100, 200),
        ("HALT",)
    ]
    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success is True
    
    # Trace metadata validation should pass
    pm_report = report.pass_manager_report
    program_len = pm_report["raw_instruction_count"]
    ok, err = validate_waveguide_trace_metadata(report.trace_steps, program_len, 32, pm_report)
    assert ok is True, err
    
    # Replay should also pass
    rep_ok, rep_err, rep_state = replay_waveguide_execution_trace(32, report.trace_steps)
    assert rep_ok is True, rep_err


# 7. Strict Proof Matrix Extension
def test_strict_proof_capabilities():
    # Build a support matrix and verify the new capability flags are present
    matrix = build_strict_backend_support_matrix([])
    pdm_matrix = matrix.matrix.get("pdm_waveguide_microcoded_strict", {})
    
    assert "supports_micro_isa_v1_candidate_lowering" in pdm_matrix
    assert "supports_v1_select_candidate" in pdm_matrix
    assert "supports_v1_cmov_candidate" in pdm_matrix
    assert "supports_v1_prefix_arithmetic_candidate" in pdm_matrix
    assert "supports_v1_candidate_trace_mapping" in pdm_matrix
    
    assert pdm_matrix["supports_micro_isa_v1_candidate_lowering"] == "validated"
    assert pdm_matrix["supports_v1_select_candidate"] == "validated"
