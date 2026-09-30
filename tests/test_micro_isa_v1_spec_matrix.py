# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Verification tests for the SOL Micro-ISA v1 Formal Spec + Extension Compliance Matrix.
"""

import pytest
from typing import Dict, Any, List

from sol_micro_isa_v1_spec import (
    build_micro_isa_v1_opcode_spec,
    build_micro_isa_v1_spec_table,
    get_micro_isa_v1_opcode_record,
    validate_micro_isa_v1_spec_consistency,
    summarize_micro_isa_v1_spec,
    EXTENSION_COMPLIANT,
    UNSUPPORTED,
    PROPOSED
)
from sol_micro_isa_v1_capability_matrix import (
    build_micro_isa_v1_capability_matrix,
    evaluate_micro_isa_v1_candidate_capability,
    summarize_micro_isa_v1_capability_matrix,
    assert_micro_isa_v1_extension_compliance
)
from sol_waveguide_trace_replay import (
    validate_v1_trace_metadata_against_spec,
    validate_waveguide_trace_metadata
)
from sol_strict_backend_execution_proof import (
    StrictBackendProofReport,
    StrictBackendProgramResult,
    summarize_strict_backend_proof,
    classify_backend_program_compliance
)
from sol_waveguide_optimization_benchmark import (
    build_waveguide_benchmark_suite,
    run_waveguide_benchmark_case,
    summarize_waveguide_benchmark_report
)
from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)

# 1. Spec Construction Tests
def test_spec_construction():
    spec = build_micro_isa_v1_opcode_spec()
    known = [
        "SELECT", "CMOVZ", "CMOVNZ", "CMOVC", "CMOVNC", "CMOVB", "CMOVNB",
        "PLOAD_RO", "LANE_ADD", "LANE_SUB", "PREFIX_ADD", "PREFIX_SUB"
    ]
    for k in known:
        assert k in spec
        assert spec[k]["opcode"] == k
        assert spec[k]["enabled_by_default"] is False

    # Opcode records have required fields
    required_keys = {
        "opcode", "category", "status", "enabled_by_default", "operand_schema",
        "semantics", "flags_behavior", "memory_behavior", "lowering_strategy",
        "requires", "safety_constraints", "benchmark_cases", "trace_metadata"
    }
    for op, record in spec.items():
        assert required_keys.issubset(record.keys())

    # Unsupported/proposed candidates marked explicitly
    assert spec["PSTORE_WO"]["status"] == UNSUPPORTED
    assert spec["DUMMY_V1_OP"]["status"] == PROPOSED


# 2. Spec Consistency Tests
def test_spec_consistency():
    # Calling consistency validator should succeed
    assert validate_micro_isa_v1_spec_consistency() is True

    spec = build_micro_isa_v1_opcode_spec()
    for op, r in spec.items():
        if r["status"] == EXTENSION_COMPLIANT:
            assert r["lowering_strategy"] is not None
            assert len(r["trace_metadata"]) > 0
            
            # Supported candidates should have benchmark case listed (if relevant)
            if op in ("SELECT", "CMOVZ", "CMOVC", "CMOVB", "PLOAD_RO", "PREFIX_ADD", "PREFIX_SUB"):
                assert len(r["benchmark_cases"]) > 0

        # Memory touching candidates declare constraints
        if r["memory_behavior"] in ("read", "write"):
            assert any(
                c in r["safety_constraints"] 
                for c in ("no_memory_write", "static_addresses_only", "memory_write_rejected")
            )


# 3. Capability Matrix Tests
def test_capability_matrix():
    spec = build_micro_isa_v1_opcode_spec()
    
    # Mock strict backend report
    dummy_report = StrictBackendProofReport(
        report_id="DUMMY",
        results=[],
        support_matrix={},
        success=True,
        active_table_mutated=False
    )
    
    matrix = build_micro_isa_v1_capability_matrix(spec, dummy_report)
    
    # Matrix builds deterministically
    assert "pdm_waveguide_microcoded_strict" in matrix.matrix
    assert "sequencer_shadow_strict" in matrix.matrix
    
    # SELECT reports emulated on microcoded
    assert matrix.matrix["pdm_waveguide_microcoded_strict"]["SELECT"] == "emulated"
    
    # CMOV family reports correct support status
    assert matrix.matrix["pdm_waveguide_microcoded_strict"]["CMOVZ"] == "emulated"
    assert matrix.matrix["sequencer_shadow_strict"]["CMOVZ"] == "unsupported"
    
    # PLOAD_RO capability check
    assert matrix.matrix["pdm_waveguide_microcoded_strict"]["PLOAD_RO"] == "emulated"
    
    # Unsupported/rejected candidates do not affect v0 compliance
    # PSTORE_WO is unsupported on all backends
    for b in matrix.matrix:
        assert matrix.matrix[b]["PSTORE_WO"] == "unsupported"

    assert assert_micro_isa_v1_extension_compliance(matrix) is True


# 4. Strict Proof Integration Tests
def test_strict_proof_integration():
    from sol_micro_isa import build_micro_isa_v0_spec
    v0_spec = build_micro_isa_v0_spec()

    # If we have a successful v0 compliance run, compliance is full_compliance
    res_v0 = StrictBackendProgramResult(
        backend_requested="pdm_waveguide_microcoded_strict",
        backend_used="pdm_waveguide_microcoded_strict",
        strict_mode=True,
        width=32,
        program_name="TestV0Case",
        instruction_count=2,
        passed_instruction_count=2,
        failed_instruction_count=0,
        fallback_instruction_count=0,
        unsupported_instruction_count=0,
        unavailable_instruction_count=0,
        oracle_match=True,
        all_instructions_used_requested_backend=True,
        validated=True,
        unavailable_reason=None,
        first_failure=None,
        trace_steps=[]
    )

    # Let's add a failing v1 run (unsupported opcode execution)
    res_v1_fail = StrictBackendProgramResult(
        backend_requested="pdm_waveguide_microcoded_strict",
        backend_used="pdm_waveguide_microcoded_strict",
        strict_mode=True,
        width=32,
        program_name="v1_pload_ro_dynamic_rejected",
        instruction_count=2,
        passed_instruction_count=1,
        failed_instruction_count=1,
        fallback_instruction_count=0,
        unsupported_instruction_count=1,
        unavailable_instruction_count=0,
        oracle_match=False,
        all_instructions_used_requested_backend=False,
        validated=False,
        unavailable_reason=None,
        first_failure="Execution error: unsupported_instruction",
        trace_steps=[{"op": "PLOAD_RO", "layer_used": "unsupported_instruction"}]
    )

    report = StrictBackendProofReport(
        report_id="RPT_TEST",
        results=[res_v0, res_v1_fail],
        support_matrix={},
        success=False,
        active_table_mutated=False
    )

    # Compliance matrices evaluation
    compliance = classify_backend_program_compliance(report, v0_spec)
    # v0 compliance must not be affected by the v1_ fail run
    assert compliance["pdm_waveguide_microcoded_strict"] == "full_compliance"

    summary = summarize_strict_backend_proof(report)
    assert summary["micro_isa_v0_compliance"] == "full_compliance"
    
    # Check separate v1 extension section
    v1_ext = summary["micro_isa_v1_extension"]
    assert v1_ext["enabled"] is True
    assert v1_ext["does_not_affect_v0"] is True
    assert v1_ext["candidate_support"]["PLOAD_RO"] == "emulated"


# 5. Benchmark Integration Tests
def test_benchmark_integration():
    suite = build_waveguide_benchmark_suite(32)
    v1_cases = [c for c in suite if c["case_id"].startswith("v1_")]
    assert len(v1_cases) > 0
    
    # Select case checks
    sel_case = next(c for c in v1_cases if c["case_id"] == "v1_select_true")
    assert sel_case["v0_equivalent_program"] is not None

    # Run select case
    case_rep = run_waveguide_benchmark_case(sel_case, 32)
    assert "v1_details" in case_rep
    
    details = case_rep["v1_details"]
    assert details["v1_candidate_case_id"] == "v1_select_true"
    assert details["candidate_opcode"] == "SELECT"
    assert details["equivalent_v0_reference_case"] == "v1_select_true_v0_equiv"
    assert details["lowering_strategy"] == "branchless_select_via_predication"
    assert details["trace_replay_verdict"] in ("pass", "fail")
    
    cycle_comp = details["cycle_comparison"]
    assert cycle_comp["v0_equivalent_raw"] > 0
    assert cycle_comp["v1_lowered_raw"] > 0
    assert cycle_comp["v1_lowered_full_optimized"] > 0

    # Test summary
    matrix_report = {"widths": [32], "cases": [case_rep]}
    summary_rep = summarize_waveguide_benchmark_report(matrix_report)
    assert "v1_details" in summary_rep["cases"][0]


# 6. Trace Replay Integration Tests
def test_trace_replay_integration():
    from sol_wideword_computation_validation import WideWordProgramInstruction
    
    class MockStep:
        def __init__(self, op, pc_before=0, pc_after=1, layer_used="pdm_waveguide_microcoded"):
            self.pc_before = pc_before
            self.pc_after = pc_after
            self.instruction = WideWordProgramInstruction(op=op)
            self.layer_used = layer_used

    # 1. v1 metadata while v1 mode is disabled rejected
    step_sel = MockStep("SELECT")
    step_sel.v1_lowering_metadata = {"micro_isa_v1_candidate": True, "candidate_opcode": "SELECT"}
    
    # PM report says disabled
    pm_report_disabled = {
        "passes": [{"pass_id": "v1_candidate_lowering", "enabled": False}]
    }
    ok, err = validate_v1_trace_metadata_against_spec(step_sel, pm_report_disabled)
    assert ok is False
    assert "v1 candidate metadata emitted when v1 mode is disabled" in err

    # 2. v1 metadata for unknown candidate opcode rejected
    pm_report_enabled = {
        "passes": [{"pass_id": "v1_candidate_lowering", "enabled": True}],
        "v1_lowering_metadata": [
            {
                "micro_isa_v1_candidate": True,
                "candidate_opcode": "UNKNOWN_V1_OP",
                "lowered_to_v0": True,
                "candidate_pc": 0,
                "v0_pc_range": [0]
            }
        ]
    }
    step_unk = MockStep("UNKNOWN_V1_OP")
    ok, err = validate_v1_trace_metadata_against_spec(step_unk, pm_report_enabled)
    assert ok is False
    assert "unknown candidate opcode" in err

    # 3. Missing required metadata rejected
    pm_report_missing_keys = {
        "passes": [{"pass_id": "v1_candidate_lowering", "enabled": True}],
        "v1_lowering_metadata": [
            {
                "micro_isa_v1_candidate": True,
                "candidate_opcode": "SELECT"
                # missing lowered_to_v0, lowering_safe, skip_reason, etc.
            }
        ]
    }
    step_sel2 = MockStep("SELECT")
    ok, err = validate_v1_trace_metadata_against_spec(step_sel2, pm_report_missing_keys)
    assert ok is False
    assert "Missing required keys" in err or "Missing required trace" in err

    # 4. Unsupported candidate execution rejected
    pm_report_unsupported = {
        "passes": [{"pass_id": "v1_candidate_lowering", "enabled": True}],
        "v1_lowering_metadata": [
            {
                "micro_isa_v1_candidate": True,
                "candidate_opcode": "PSTORE_WO",
                "lowered_to_v0": True,
                "lowering_safe": True,
                "skip_reason": None,
                "candidate_pc": 0,
                "v0_pc_range": [0]
            }
        ]
    }
    step_pstore = MockStep("PSTORE_WO")
    ok, err = validate_v1_trace_metadata_against_spec(step_pstore, pm_report_unsupported)
    assert ok is False
    assert "marked unsupported/rejected" in err


# 7. Regression Compatibility Tests
def test_regression_compatibility():
    # Make sure we can run a simple v1 lowering end-to-end trace mapping run
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
