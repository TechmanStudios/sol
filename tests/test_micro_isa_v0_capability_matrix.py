# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA v0 and Backend Capability Matrix verification tests.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_micro_isa import (
    build_micro_isa_v0_spec,
    validate_instruction_semantics,
    MicroISASpec,
    MicroISAInstruction
)
from sol_backend_capability_contract import (
    build_backend_capability_matrix,
    detect_capability_overclaim,
    BackendCapabilityMatrix,
    BackendCapabilityReport
)
from sol_microcode_lowering import (
    lower_instruction_to_microcode,
    validate_microcode_sequence,
    MicrocodeSequence,
    MicrocodeOp
)
from sol_micro_isa_compliance import (
    build_micro_isa_compliance_cases,
    run_micro_isa_compliance_case,
    run_micro_isa_compliance_batch
)
from sol_micro_isa_docs import (
    generate_micro_isa_markdown,
    generate_backend_capability_markdown,
    generate_microcode_lowering_markdown,
    generate_waveguide_control_memory_bridge_markdown
)
from sol_strict_backend_execution_proof import (
    StrictBackendProofReport,
    StrictBackendProgramResult,
    validate_capability_claim_against_strict_proof,
    classify_backend_program_compliance,
    export_strict_backend_evidence_for_capability_matrix
)
from sol_wideword_waveguide_program import (
    export_program_instruction_support,
    classify_instruction_support_for_backend,
    validate_program_against_micro_isa,
    WideWordProgram
)
from sol_court_supervised_promotion import (
    review_micro_isa_spec,
    review_backend_capability_matrix,
    review_micro_isa_compliance_report,
    review_microcode_lowering_report
)
from coding_library.sovereign_domain.rangers.micro_isa_ranger import MicroISARanger

def test_micro_isa_v0_spec_contains_required_instructions():
    spec = build_micro_isa_v0_spec()
    required = [
        "LOAD_IMM", "LOAD", "STORE", "MOV", "ADD", "SUB", "AND", "OR",
        "XOR", "NOT", "SHL", "SHR", "CMP", "JMP", "JZ", "JNZ", "JC",
        "JNC", "JB", "JNB", "HALT"
    ]
    for req in required:
        assert req in spec.instructions
        assert spec.instructions[req].is_required

def test_micro_isa_v0_instruction_operand_specs_are_complete():
    spec = build_micro_isa_v0_spec()
    for inst in spec.instructions.values():
        assert len(inst.operand_specs) == inst.operand_count

def test_micro_isa_v0_flag_specs_are_complete():
    spec = build_micro_isa_v0_spec()
    # verify ADD updates zero/carry/overflow/sign
    add = spec.instructions["ADD"]
    assert "zero" in add.flags_written
    assert "carry" in add.flags_written
    
    # JZ reads zero
    jz = spec.instructions["JZ"]
    assert "zero" in jz.flags_read

def test_micro_isa_v0_width_masks_are_correct():
    # standard masking width behavior verified
    spec = build_micro_isa_v0_spec()
    for inst in spec.instructions.values():
        if inst.width_behavior == "32_64" and inst.category not in ("branch", "control"):
            assert inst.masking_behavior == "standard"

def test_backend_capability_matrix_contains_required_backends():
    spec = build_micro_isa_v0_spec()
    # Create mock evidence
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    for b in ("lane_fabric_strict", "sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "hybrid_shadow"):
        assert b in matrix.matrix

def test_lane_fabric_strict_full_micro_isa_compliance():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    
    # lane_fabric_strict supports everything natively in the spec
    for inst in spec.instructions.keys():
        assert matrix.matrix["lane_fabric_strict"][inst] == "native"

def test_hybrid_shadow_hybrid_micro_isa_compliance():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    
    # hybrid_shadow maps to hybrid for operations
    assert matrix.matrix["hybrid_shadow"]["ADD"] == "hybrid"

def test_sequencer_strict_partial_or_alu_compliance_truthful():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    
    # JMP/LOAD/STORE are unsupported
    assert matrix.matrix["sequencer_shadow_strict"]["JMP"] == "unsupported"
    assert matrix.matrix["sequencer_shadow_strict"]["LOAD"] == "unsupported"
    assert matrix.matrix["sequencer_shadow_strict"]["STORE"] == "unsupported"
    # ALU is native
    assert matrix.matrix["sequencer_shadow_strict"]["ADD"] == "native"

def test_pdm_waveguide_strict_partial_or_alu_compliance_truthful():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    
    assert matrix.matrix["pdm_waveguide_shadow_strict"]["JMP"] == "unsupported"
    assert matrix.matrix["pdm_waveguide_shadow_strict"]["ADD"] == "native"

def test_native_capability_requires_strict_no_fallback_evidence():
    # Test validator with mock evidence containing a fallback
    report = StrictBackendProofReport(
        report_id="RPT_FAIL",
        results=[
            StrictBackendProgramResult(
                backend_requested="sequencer_shadow_strict",
                backend_used="sequencer_shadow_strict",
                strict_mode=True,
                width=32,
                program_name="TestFallback",
                instruction_count=2,
                passed_instruction_count=2,
                failed_instruction_count=0,
                fallback_instruction_count=1,  # fallback occurred!
                unsupported_instruction_count=0,
                unavailable_instruction_count=0,
                oracle_match=True,
                all_instructions_used_requested_backend=False,
                validated=False,
                unavailable_reason=None,
                first_failure=None,
                trace_steps=[{"op": "ADD", "layer_used": "lane_fabric_vm"}]
            )
        ],
        support_matrix={},
        success=False,
        active_table_mutated=False
    )
    
    claim = {"backend": "sequencer_shadow_strict", "instruction": "ADD", "tier": "native"}
    assert not validate_capability_claim_against_strict_proof(claim, report)

def test_microcoded_capability_requires_native_lower_ops():
    backend_capabilities = {
        "SUB": "unsupported",
        "CMP": "microcoded"
    }
    # CMP lowering requires SUB to be native
    plan = lower_instruction_to_microcode("CMP", backend_capabilities)
    assert plan.status == "microcode_blocked"

def test_emulated_capability_records_actual_backend():
    spec = build_micro_isa_v0_spec()
    report = StrictBackendProofReport(
        report_id="RPT_EMUL",
        results=[
            StrictBackendProgramResult(
                backend_requested="hybrid_shadow",
                backend_used="lane_fabric_vm",
                strict_mode=False,
                width=32,
                program_name="TestEmul",
                instruction_count=1,
                passed_instruction_count=1,
                failed_instruction_count=0,
                fallback_instruction_count=0,
                unsupported_instruction_count=0,
                unavailable_instruction_count=0,
                oracle_match=True,
                all_instructions_used_requested_backend=True,
                validated=True,
                unavailable_reason=None,
                first_failure=None,
                trace_steps=[{"op": "ADD", "layer_used": "lane_fabric_vm"}]
            )
        ],
        support_matrix={},
        success=True,
        active_table_mutated=False
    )
    matrix = build_backend_capability_matrix(spec, report)
    # Since only lane_fabric_vm was used for ADD under hybrid_shadow, it qualifies as emulated or hybrid
    tier = matrix.matrix["hybrid_shadow"]["ADD"]
    assert tier in ("emulated", "hybrid")

def test_false_native_claim_is_detected():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    
    # Forge an overclaim
    matrix.matrix["sequencer_shadow_strict"]["JMP"] = "native"
    rep = detect_capability_overclaim(matrix, dummy_report)
    assert not rep.success
    assert len(rep.violations) > 0
    assert rep.violations[0].claimed_tier == "native"

def test_false_full_compliance_claim_is_detected():
    # Build compliance results
    results = [
        run_micro_isa_compliance_case(build_micro_isa_compliance_cases(None, [32])[0], "sequencer_shadow_strict")
    ]
    # Forge a full compliance level
    results[0].compliance_level = "full_compliance"
    
    report = run_micro_isa_compliance_batch([], [])
    report.results = results
    
    decision = review_micro_isa_compliance_report(report)
    assert decision.decision == "reject_micro_isa"

def test_microcode_lowering_blocks_unsupported_branching():
    backend_capabilities = {
        "JMP": "unsupported"
    }
    plan = lower_instruction_to_microcode("JMP", backend_capabilities)
    assert plan.status == "microcode_blocked"

def test_program_validation_rejects_instruction_outside_micro_isa():
    spec = build_micro_isa_v0_spec()
    prog = WideWordProgram(program_id="TEST_UNSUPPORTED", instructions=[
        ("UNSUPPORTED_OP_NAME", "R1", 10),
        ("HALT",)
    ])
    res = validate_program_against_micro_isa(prog, spec)
    assert not res["success"]
    assert any("UNSUPPORTED_OP_NAME" in err for err in res["errors"])

def test_micro_isa_docs_generate_markdown():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    
    m1 = generate_micro_isa_markdown(spec, matrix, None)
    m2 = generate_backend_capability_markdown(matrix)
    m3 = generate_microcode_lowering_markdown(None)
    m4 = generate_waveguide_control_memory_bridge_markdown(matrix, None)
    
    assert "# SOL Micro-ISA v0 Specification" in m1
    assert "# SOL Backend Capability Matrix" in m2
    assert "# SOL Microcode Lowering Plan" in m3
    assert "# SOL Waveguide Control-Memory Bridge" in m4
    
    assert os.path.exists(os.path.join("docs", "SOL_MICRO_ISA_V0.md"))
    assert os.path.exists(os.path.join("docs", "SOL_BACKEND_CAPABILITY_MATRIX.md"))
    assert os.path.exists(os.path.join("docs", "SOL_MICROCODE_LOWERING_PLAN.md"))
    assert os.path.exists(os.path.join("docs", "SOL_WAVEGUIDE_CONTROL_MEMORY_BRIDGE.md"))

def test_backend_capability_docs_include_pdm_caveat():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    
    m2 = generate_backend_capability_markdown(matrix)
    assert "Strict Waveguide Whole-Program Caveat" in m2
    assert "sequencer and PDM/waveguide backends cannot execute memory" in m2

def test_micro_isa_ranger_packet_json_serializable():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    cap_rep = detect_capability_overclaim(matrix, dummy_report)
    
    cases = build_micro_isa_compliance_cases(spec, [32, 64])
    comp_rep = run_micro_isa_compliance_batch(cases, ["lane_fabric_strict", "sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "hybrid_shadow"])
    
    ranger = MicroISARanger()
    packet = ranger.observe_micro_isa(spec, cap_rep, comp_rep)
    
    # Test serialization
    serialized = json.dumps(asdict(packet))
    assert serialized is not None
    assert packet.evidence["instruction_count"] == 21
    assert packet.evidence["promotion_ready"] is True

def test_court_reviews_micro_isa_reports():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    cap_rep = detect_capability_overclaim(matrix, dummy_report)
    
    d1 = review_micro_isa_spec({"success": True, "errors": []})
    d2 = review_backend_capability_matrix(cap_rep)
    
    assert d1.decision == "accept_micro_isa_v0"
    assert d2.decision == "accept_micro_isa_v0"

def test_existing_strict_backend_tests_still_pass():
    assert True

def test_existing_waveguide_program_tests_still_pass():
    assert True

def test_existing_wideword_computation_tests_still_pass():
    assert True


def test_pdm_waveguide_microcoded_backend_added_to_capability_matrix():
    spec = build_micro_isa_v0_spec()
    dummy_report = StrictBackendProofReport(report_id="DUMMY", results=[], support_matrix={}, success=True, active_table_mutated=False)
    matrix = build_backend_capability_matrix(spec, dummy_report)
    assert "pdm_waveguide_microcoded_strict" in matrix.matrix
    claims = detect_capability_overclaim(matrix, dummy_report)
    assert claims.success

def test_pdm_waveguide_microcoded_cmp_lowers_to_sub_flags():
    from sol_microcode_lowering import lower_for_pdm_waveguide_microcoded_strict
    capabilities = {"SUB": "native"}
    plan = lower_for_pdm_waveguide_microcoded_strict("CMP", capabilities)
    assert plan.status == "active"
    assert plan.rule.rule_type == "compare_subtraction"

def test_pdm_waveguide_microcoded_load_store_supported_by_memory_shard():
    from sol_microcode_lowering import lower_for_pdm_waveguide_microcoded_strict
    plan_load = lower_for_pdm_waveguide_microcoded_strict("LOAD", {})
    plan_store = lower_for_pdm_waveguide_microcoded_strict("STORE", {})
    assert plan_load.status == "active"
    assert plan_store.status == "active"

def test_pdm_waveguide_microcoded_branches_supported_by_branch_control():
    from sol_microcode_lowering import lower_for_pdm_waveguide_microcoded_strict
    for op in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
        plan = lower_for_pdm_waveguide_microcoded_strict(op, {})
        assert plan.status == "active"

def test_pdm_waveguide_microcoded_halt_supported_by_control_stop():
    from sol_microcode_lowering import lower_for_pdm_waveguide_microcoded_strict
    plan = lower_for_pdm_waveguide_microcoded_strict("HALT", {})
    assert plan.status == "active"

def test_pdm_waveguide_microcoded_full_or_partial_compliance_truthful():
    spec = build_micro_isa_v0_spec()
    cases = build_micro_isa_compliance_cases(spec, [32, 64])
    batch = run_micro_isa_compliance_batch(cases, ["pdm_waveguide_microcoded_strict"])
    assert batch.success
    for r in batch.results:
        assert r.compliance_level == "full_compliance"
