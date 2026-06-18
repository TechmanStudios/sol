# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Strict WideWord Backend Execution Proof validation test campaign.
"""

import json
import random
import pytest
from dataclasses import asdict

from sol_lane_fabric import LaneFabric
from sol_wideword_computation_validation import (
    WideWordVirtualVM,
    OracleWideWordVM,
    run_oracle_program,
    compare_sol_program_to_oracle,
    mask_for_width
)
from sol_strict_backend_execution_proof import (
    StrictBackendProofConfig,
    StrictBackendProgramCase,
    StrictBackendProgramResult,
    run_strict_backend_program_case,
    run_strict_backend_batch,
    build_strict_backend_support_matrix,
    summarize_strict_backend_proof,
    snapshot_active_state,
    verify_active_state
)
from sol_court_supervised_promotion import (
    review_strict_backend_execution_report,
    review_strict_backend_ranger_packet
)
from coding_library.sovereign_domain.rangers.strict_backend_ranger import StrictBackendRanger

from tests.test_wideword_waveguide_program_execution import (
    make_arithmetic_chain_program,
    make_sum_loop_program,
    make_fibonacci_loop_program,
    make_popcount_program,
    make_crc_mixing_program,
    make_shift_add_multiply_program,
    make_restoring_division_program
)


def test_strict_backend_config_disallows_fallback():
    prog = [
        ("MOV", "R1", 10),
        ("ADD", "R2", "R1", 20),
        ("HALT",)
    ]
    # For sequencer_shadow_strict, MOV/HALT are unsupported, fallback is forbidden.
    # Therefore, it should fail validation with unsupported_instruction.
    case = StrictBackendProgramCase(name="HaltTest", program=prog, width=32)
    res = run_strict_backend_program_case(case, backend="sequencer_shadow_strict")
    assert not res.validated
    assert res.fallback_instruction_count == 0
    assert res.unsupported_instruction_count > 0
    assert res.unavailable_reason == "unsupported_instruction"


def test_lane_fabric_strict_register_chain_32_64():
    for width in (32, 64):
        prog = make_arithmetic_chain_program(100, 200)
        case = StrictBackendProgramCase(name="RegChain", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="lane_fabric_strict")
        assert res.validated
        assert res.oracle_match
        assert res.failed_instruction_count == 0
        assert res.fallback_instruction_count == 0


def test_lane_fabric_strict_sum_loop_32_64():
    for width in (32, 64):
        prog = make_sum_loop_program(10)
        case = StrictBackendProgramCase(name="SumLoop", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="lane_fabric_strict")
        assert res.validated
        assert res.oracle_match


def test_lane_fabric_strict_fibonacci_loop_32_64():
    for width in (32, 64):
        prog = make_fibonacci_loop_program(12)
        case = StrictBackendProgramCase(name="FibLoop", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="lane_fabric_strict")
        assert res.validated
        assert res.oracle_match


def test_lane_fabric_strict_popcount_32_64():
    for width in (32, 64):
        prog = make_popcount_program(0xF5, width)
        case = StrictBackendProgramCase(name="Popcount", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="lane_fabric_strict")
        assert res.validated
        assert res.oracle_match


def test_lane_fabric_strict_crc_xor_shift_32_64():
    for width in (32, 64):
        prog = make_crc_mixing_program(0x12345678, width)
        case = StrictBackendProgramCase(name="CrcLoop", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="lane_fabric_strict")
        assert res.validated
        assert res.oracle_match


def test_lane_fabric_strict_shift_add_multiply_32_64():
    for width in (32, 64):
        prog = make_shift_add_multiply_program(15, 6)
        case = StrictBackendProgramCase(name="ShiftAddMult", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="lane_fabric_strict")
        assert res.validated
        assert res.oracle_match


def test_lane_fabric_strict_division_scaffold_32_64():
    for width in (32, 64):
        prog = make_restoring_division_program(10, 3)
        case = StrictBackendProgramCase(name="RestoringDiv", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="lane_fabric_strict")
        assert res.validated
        assert res.oracle_match


def test_hybrid_shadow_reports_layer_distribution():
    prog = [
        ("MOV", "R1", 10),      # lane_fabric_vm
        ("ADD", "R2", "R1", 20),  # pdm_waveguide_shadow / sequencer_shadow
        ("HALT",)
    ]
    case = StrictBackendProgramCase(name="HybridDist", program=prog, width=32)
    res = run_strict_backend_program_case(case, backend="hybrid_shadow")
    assert res.validated
    assert len(res.trace_steps) > 0
    # Should contain layers used
    layers = [step["layer_used"] for step in res.trace_steps]
    assert "lane_fabric_vm" in layers


def test_hybrid_shadow_passes_oracle_with_fallback_accounting():
    prog = make_arithmetic_chain_program(100, 200)
    case = StrictBackendProgramCase(name="HybridOracle", program=prog, width=32)
    res = run_strict_backend_program_case(case, backend="hybrid_shadow")
    assert res.validated
    assert res.oracle_match


def test_sequencer_strict_reports_pass_or_unavailable_truthfully():
    # Sequencer cannot execute jumps or MOV cleanly in strict mode
    prog = make_sum_loop_program(5)
    case = StrictBackendProgramCase(name="SeqStrictSum", program=prog, width=32)
    res = run_strict_backend_program_case(case, backend="sequencer_shadow_strict")
    assert not res.validated
    # Should classify the failure reason as unsupported_instruction or unsupported_control_flow
    assert res.unavailable_reason in ("unsupported_instruction", "unsupported_control_flow")


def test_pdm_waveguide_strict_reports_pass_or_unavailable_truthfully():
    prog = make_arithmetic_chain_program(10, 20)
    case = StrictBackendProgramCase(name="PdmStrictReg", program=prog, width=64)
    res = run_strict_backend_program_case(case, backend="pdm_waveguide_shadow_strict")
    assert not res.validated
    assert res.unavailable_reason in ("unsupported_instruction", "unsupported_memory_op", "demodulation_unavailable", "unavailable")


def test_strict_backend_report_marks_fallback_as_not_validated():
    prog = [
        ("MOV", "R1", 10),
        ("ADD", "R2", "R1", 20),
        ("HALT",)
    ]
    # Under sequencer_shadow_strict, the MOV/HALT instructions are unsupported,
    # so we fail. We assert that validated is False.
    case = StrictBackendProgramCase(name="FallbackFail", program=prog, width=32)
    res = run_strict_backend_program_case(case, backend="sequencer_shadow_strict")
    assert not res.validated


def test_strict_backend_support_matrix_contains_required_fields():
    # Make a dummy result
    res = StrictBackendProgramResult(
        backend_requested="sequencer_shadow_strict",
        backend_used="sequencer_shadow",
        strict_mode=True,
        width=32,
        program_name="Dummy",
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
        first_failure=None
    )
    matrix = build_strict_backend_support_matrix([res]).matrix
    
    assert "lane_fabric_strict" in matrix
    assert "sequencer_shadow_strict" in matrix
    assert "pdm_waveguide_shadow_strict" in matrix
    assert "hybrid_shadow" in matrix
    
    required_features = [
        "supports_32bit_register_ops",
        "supports_64bit_register_ops",
        "supports_memory_load_store",
        "supports_flags",
        "supports_cmp",
        "supports_conditional_branches",
        "supports_unconditional_branches",
        "supports_shifts",
        "supports_multiplication_scaffold",
        "supports_division_scaffold",
        "supports_full_program_traces",
        "supports_ranger_court_evidence",
        "supports_active_mutation_guard",
        "supports_branch_control",
        "supports_coherent_memory_operations",
        "supports_program_counter_tracking",
        "supports_strict_microcoded_execution",
        "supports_pipeline_compaction",
        "supports_prefix_carry_routing"
    ]
    
    for backend in matrix:
        for feat in required_features:
            assert feat in matrix[backend]
            assert matrix[backend][feat] in ("validated", "partial", "unavailable", "unsupported", "failed")


def test_strict_backend_first_failure_is_deterministic():
    prog = [
        ("MOV", "R1", 10),
        ("ADD", "R2", "R1", 20),
        ("HALT",)
    ]
    case = StrictBackendProgramCase(name="DeterministicFail", program=prog, width=32)
    res1 = run_strict_backend_program_case(case, backend="sequencer_shadow_strict")
    res2 = run_strict_backend_program_case(case, backend="sequencer_shadow_strict")
    assert res1.first_failure == res2.first_failure


def test_strict_backend_report_is_json_serializable():
    cases = [
        StrictBackendProgramCase(name="T1", program=[("MOV", "R1", 10), ("HALT",)], width=32)
    ]
    report = run_strict_backend_batch(cases, backends=["lane_fabric_strict"])
    
    # Serialize to dictionary
    serialized = asdict(report)
    # Convert to JSON
    json_str = json.dumps(serialized)
    assert json_str is not None
    
    # Reload and verify basic report fields
    loaded = json.loads(json_str)
    assert loaded["report_id"] == report.report_id
    assert loaded["success"] == report.success


def test_strict_backend_active_state_guard():
    snap = snapshot_active_state()
    prog = make_arithmetic_chain_program(100, 200)
    case = StrictBackendProgramCase(name="MutationTest", program=prog, width=32)
    run_strict_backend_program_case(case, backend="lane_fabric_strict")
    assert verify_active_state(snap)


def test_court_reviews_strict_backend_proof_report():
    cases = [
        StrictBackendProgramCase(name="T1", program=[("MOV", "R1", 10), ("HALT",)], width=32)
    ]
    report = run_strict_backend_batch(cases, backends=["lane_fabric_strict"])
    
    # Valid report should accept
    decision = review_strict_backend_execution_report(report)
    assert decision.decision == "accept_shadow_strict_backend_proof"
    
    # Mutated report should reject
    report.active_table_mutated = True
    decision_mut = review_strict_backend_execution_report(report)
    assert decision_mut.decision == "reject_strict_backend_proof"


def test_ranger_reviews_strict_backend_proof_report_if_available():
    cases = [
        StrictBackendProgramCase(name="T1", program=[("MOV", "R1", 10), ("HALT",)], width=32)
    ]
    report = run_strict_backend_batch(cases, backends=["lane_fabric_strict"])
    
    ranger = StrictBackendRanger()
    packet = ranger.observe_strict_proof(report)
    assert packet.evidence["validated_backend_count"] > 0
    assert packet.evidence["total_programs"] == 1
    assert not packet.evidence["active_mutation_status"]
    
    decision = review_strict_backend_ranger_packet(packet)
    assert decision.decision == "accept_shadow_strict_backend_proof"


def test_strict_backend_random_batch_lane_fabric():
    rng = random.Random(0x535452494354)
    cases = []
    
    # Generate 5 random cases for reg chain, mult, and popcount
    # (Reduced counts here to keep unit tests fast, full campaign runs on the batch helper)
    for w in (32, 64):
        mask = mask_for_width(w)
        # Register chains
        for i in range(5):
            val1 = rng.randint(0, mask)
            val2 = rng.randint(0, mask)
            cases.append(StrictBackendProgramCase(name=f"RandReg_{w}_{i}", program=make_arithmetic_chain_program(val1, val2), width=w))
        # Multiply
        for i in range(2):
            a = rng.randint(0, mask >> (w // 2))
            b = rng.randint(0, mask >> (w // 2))
            cases.append(StrictBackendProgramCase(name=f"RandMult_{w}_{i}", program=make_shift_add_multiply_program(a, b), width=w))
        # Popcount
        for i in range(2):
            val = rng.randint(0, mask)
            cases.append(StrictBackendProgramCase(name=f"RandPop_{w}_{i}", program=make_popcount_program(val, w), width=w))
            
    report = run_strict_backend_batch(cases, backends=["lane_fabric_strict"])
    assert report.success
    for res in report.results:
        assert res.validated
        assert res.oracle_match


def test_strict_backend_random_batch_hybrid_shadow():
    rng = random.Random(0x535452494354)
    cases = []
    for w in (32, 64):
        mask = mask_for_width(w)
        for i in range(2):
            val1 = rng.randint(0, mask)
            val2 = rng.randint(0, mask)
            cases.append(StrictBackendProgramCase(name=f"RandReg_{w}_{i}", program=make_arithmetic_chain_program(val1, val2), width=w))
            
    report = run_strict_backend_batch(cases, backends=["hybrid_shadow"])
    assert report.success
    for res in report.results:
        assert res.validated
        assert res.oracle_match


def test_existing_waveguide_program_validation_still_passes():
    # Asserts that the existing waveguide program validations still work seamlessly
    vm = WideWordVirtualVM(width=32)
    prog = make_arithmetic_chain_program(100, 200)
    report = vm.run_program_with_backend(prog, backend="lane_fabric_vm")
    assert report.success
    assert report.oracle_match


def test_existing_full_wideword_validation_still_passes():
    # Asserts that basic wide-word computations still function cleanly
    fabric = LaneFabric.for_width(32)
    res = fabric.add_word(10, 20)
    assert res.result == 30


def test_pdm_waveguide_microcoded_strict_register_chain_32_64():
    for width in (32, 64):
        prog = make_arithmetic_chain_program(100, 200)
        case = StrictBackendProgramCase(name="RegChain", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
        assert res.validated
        assert res.oracle_match
        assert res.failed_instruction_count == 0
        assert res.fallback_instruction_count == 0

def test_pdm_waveguide_microcoded_strict_sum_loop_32_64():
    for width in (32, 64):
        prog = make_sum_loop_program(10)
        case = StrictBackendProgramCase(name="SumLoop", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
        assert res.validated
        assert res.oracle_match
        assert res.fallback_instruction_count == 0

def test_pdm_waveguide_microcoded_strict_fibonacci_loop_32_64():
    for width in (32, 64):
        prog = make_fibonacci_loop_program(12)
        case = StrictBackendProgramCase(name="FibLoop", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
        assert res.validated
        assert res.oracle_match
        assert res.fallback_instruction_count == 0

def test_pdm_waveguide_microcoded_strict_popcount_32_64():
    for width in (32, 64):
        prog = make_popcount_program(0xF5, width)
        case = StrictBackendProgramCase(name="Popcount", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
        assert res.validated
        assert res.oracle_match
        assert res.fallback_instruction_count == 0

def test_pdm_waveguide_microcoded_strict_shift_add_multiply_32_64():
    for width in (32, 64):
        prog = make_shift_add_multiply_program(15, 6)
        case = StrictBackendProgramCase(name="ShiftAddMult", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
        assert res.validated
        assert res.oracle_match
        assert res.fallback_instruction_count == 0

def test_pdm_waveguide_microcoded_strict_division_scaffold_32_64():
    for width in (32, 64):
        prog = make_restoring_division_program(10, 3)
        case = StrictBackendProgramCase(name="RestoringDiv", program=prog, width=width)
        res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
        assert res.validated
        assert res.oracle_match
        assert res.fallback_instruction_count == 0

def test_pdm_waveguide_microcoded_strict_reports_no_fallback():
    prog = [
        ("MOV", "R1", 10),
        ("ADD", "R2", "R1", 20),
        ("HALT",)
    ]
    case = StrictBackendProgramCase(name="NoFallback", program=prog, width=32)
    res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
    assert res.validated
    assert res.fallback_instruction_count == 0
    allowed_layers = {"pdm_waveguide_shadow", "waveguide_branch_control", "waveguide_memory_shard", 
                      "waveguide_control_stop", "waveguide_register_transfer", "waveguide_register_init"}
    for step in res.trace_steps:
        assert step["layer_used"] in allowed_layers

