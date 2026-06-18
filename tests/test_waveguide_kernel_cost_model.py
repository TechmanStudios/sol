# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Kernel Cost Model + Deterministic Autotuning Policy Bridge
"""

import pytest
import json
from typing import List, Dict, Any

from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_waveguide_kernel_cost_model import (
    build_waveguide_cost_model_config,
    estimate_waveguide_execution_cost,
    estimate_waveguide_trace_footprint,
    estimate_waveguide_barrier_cost,
    compare_waveguide_execution_forms,
    validate_waveguide_cost_model_report,
    summarize_waveguide_cost_model_report
)
from sol_waveguide_autotuning_policy import (
    build_waveguide_autotuning_policy,
    select_waveguide_execution_form,
    validate_waveguide_policy_decision,
    summarize_waveguide_autotuning_report
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_waveguide_trace_replay import validate_waveguide_trace_metadata
from sol_waveguide_optimization_benchmark import (
    build_waveguide_benchmark_suite,
    run_waveguide_benchmark_case
)
from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_strict_backend_execution_proof import build_strict_backend_support_matrix

@pytest.fixture
def mock_clean_instructions():
    return [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=10, src2=None),
        WideWordProgramInstruction(op="ADD", dst="R2", src1="R1", src2=5),
        WideWordProgramInstruction(op="WG_CHAN_FENCE", dst=None, src1=None, src2=None),
        WideWordProgramInstruction(op="HALT", dst=None, src1=None, src2=None)
    ]

@pytest.fixture
def mock_pass_manager_report():
    return {
        "profile_id": "FULL_SAFE_OPTIMIZED",
        "raw_instruction_count": 4,
        "passes": [
            {"pass_id": "program_adaptation", "enabled": True, "skipped": False},
            {"pass_id": "pipeline_compaction", "enabled": True, "skipped": True},
            {"pass_id": "scoreboard_scheduling", "enabled": True, "skipped": False}
        ],
        "enable_waveguide_channel_state": True,
        "enable_micro_isa_v1_candidates": True,
        "recognized_kernels": []
    }

# 1. Cost Model Construction Tests
def test_cost_model_config_construction():
    cfg = build_waveguide_cost_model_config(
        enable_cost_model=True,
        enable_deterministic_autotuning=True,
        autotuning_policy="SAFEST_OPTIMIZED"
    )
    assert cfg["enable_cost_model"] is True
    assert cfg["enable_deterministic_autotuning"] is True
    assert cfg["autotuning_policy"] == "SAFEST_OPTIMIZED"
    assert cfg["unsupported_penalty"] == 1000000
    
    # Verify report serializability
    serialized = json.dumps(cfg)
    assert serialized is not None

def test_cost_model_estimates(mock_clean_instructions, mock_pass_manager_report):
    config = build_waveguide_cost_model_config(enable_cost_model=True)
    
    # 1. Barrier cost check
    b_cost = estimate_waveguide_barrier_cost(mock_clean_instructions)
    assert b_cost == 2  # WG_CHAN_FENCE and HALT
    
    # 2. Trace footprint check
    footprint = estimate_waveguide_trace_footprint(mock_pass_manager_report)
    assert footprint > 0
    assert isinstance(footprint, int)
    
    # 3. Overall cost model evaluation
    cost = estimate_waveguide_execution_cost(
        mock_clean_instructions,
        mock_pass_manager_report,
        scheduler_report=None,
        config=config
    )
    
    assert cost["simulated_cycles"] == 4
    assert cost["barrier_count"] == 2
    assert cost["unsupported_penalty"] == 0
    
    report = {
        "form_id": "full_safe_optimized",
        "safe": True,
        "semantic_equivalence": True,
        "cost": cost
    }
    
    assert validate_waveguide_cost_model_report(report) is True
    
    summary = summarize_waveguide_cost_model_report(report)
    assert summary["form_id"] == "full_safe_optimized"
    assert summary["simulated_cycles"] == 4

def test_cost_model_unsupported_penalty(mock_clean_instructions, mock_pass_manager_report):
    config = build_waveguide_cost_model_config(enable_cost_model=True)
    
    # If the program has v1 ops but PM report has enable_micro_isa_v1_candidates=False
    mock_clean_instructions_v1 = [
        WideWordProgramInstruction(op="WG_CHAN_SEND", dst=0, src1="R1", src2=None),
        WideWordProgramInstruction(op="HALT", dst=None, src1=None, src2=None)
    ]
    
    pm_report_no_v1 = dict(mock_pass_manager_report)
    pm_report_no_v1["enable_micro_isa_v1_candidates"] = False
    pm_report_no_v1["enable_waveguide_channel_state"] = False
    
    cost = estimate_waveguide_execution_cost(
        mock_clean_instructions_v1,
        pm_report_no_v1,
        scheduler_report=None,
        config=config
    )
    assert cost["unsupported_penalty"] == 2000000  # both v1 and channel state disabled

# 2. Execution-Form Comparison
def test_execution_form_comparison():
    forms = [
        {
            "form_id": "raw_strict",
            "safe": True,
            "semantic_equivalence": True,
            "cost": {"simulated_cycles": 10, "barrier_count": 2, "trace_steps": 10, "trace_metadata_weight": 1, "unsupported_penalty": 0}
        },
        {
            "form_id": "full_safe_optimized",
            "safe": True,
            "semantic_equivalence": True,
            "cost": {"simulated_cycles": 6, "barrier_count": 2, "trace_steps": 6, "trace_metadata_weight": 5, "unsupported_penalty": 0}
        },
        {
            "form_id": "channel_kernelized",
            "safe": True,
            "semantic_equivalence": True,
            "cost": {"simulated_cycles": 4, "barrier_count": 1, "trace_steps": 4, "trace_metadata_weight": 8, "unsupported_penalty": 0}
        },
        {
            "form_id": "safe_local",
            "safe": False,
            "semantic_equivalence": False,
            "cost": {"simulated_cycles": 8, "barrier_count": 2, "trace_steps": 8, "trace_metadata_weight": 2, "unsupported_penalty": 500000}
        }
    ]
    
    ranked = compare_waveguide_execution_forms(forms)
    assert ranked[0]["form_id"] == "channel_kernelized"       # lowest cycles, safe
    assert ranked[1]["form_id"] == "full_safe_optimized"      # next lowest cycles, safe
    assert ranked[2]["form_id"] == "raw_strict"               # highest cycles, safe
    assert ranked[3]["form_id"] == "safe_local"               # unsafe, ranked last

# 3. Autotuning Policies
def test_autotuning_policies():
    candidates = [
        {
            "form_id": "raw_strict",
            "safe": True,
            "semantic_equivalence": True,
            "cost": {"simulated_cycles": 10, "barrier_count": 2, "trace_steps": 10, "trace_metadata_weight": 1, "unsupported_penalty": 0}
        },
        {
            "form_id": "safe_local",
            "safe": True,
            "semantic_equivalence": True,
            "cost": {"simulated_cycles": 8, "barrier_count": 2, "trace_steps": 8, "trace_metadata_weight": 2, "unsupported_penalty": 0}
        },
        {
            "form_id": "full_safe_optimized",
            "safe": True,
            "semantic_equivalence": True,
            "cost": {"simulated_cycles": 6, "barrier_count": 2, "trace_steps": 6, "trace_metadata_weight": 4, "unsupported_penalty": 0}
        },
        {
            "form_id": "channel_kernelized",
            "safe": True,
            "semantic_equivalence": True,
            "cost": {"simulated_cycles": 4, "barrier_count": 1, "trace_steps": 4, "trace_metadata_weight": 8, "unsupported_penalty": 0}
        }
    ]
    
    # A. STRICT_ONLY
    dec = select_waveguide_execution_form(None, [dict(c) for c in candidates], "STRICT_ONLY")
    assert dec["selected_form_id"] == "raw_strict"
    assert validate_waveguide_policy_decision(dec, dec["candidates"], "STRICT_ONLY") is True
    
    # B. SAFEST_OPTIMIZED
    dec = select_waveguide_execution_form(None, [dict(c) for c in candidates], "SAFEST_OPTIMIZED")
    assert dec["selected_form_id"] == "safe_local"  # least aggressive optimized form
    
    # C. LOWEST_SIMULATED_CYCLES
    dec = select_waveguide_execution_form(None, [dict(c) for c in candidates], "LOWEST_SIMULATED_CYCLES")
    assert dec["selected_form_id"] == "channel_kernelized"
    
    # D. LOWEST_TRACE_FOOTPRINT
    dec = select_waveguide_execution_form(None, [dict(c) for c in candidates], "LOWEST_TRACE_FOOTPRINT")
    # trace footprint = trace_steps * trace_metadata_weight
    # raw_strict = 10 * 1 = 10
    # safe_local = 8 * 2 = 16
    # full_safe_optimized = 6 * 4 = 24
    # channel_kernelized = 4 * 8 = 32
    assert dec["selected_form_id"] == "raw_strict"  # raw_strict has smallest footprint
    
    # E. KERNEL_PREFERRED_SAFE
    dec = select_waveguide_execution_form(None, [dict(c) for c in candidates], "KERNEL_PREFERRED_SAFE")
    assert dec["selected_form_id"] == "channel_kernelized"
    
    # F. Invalid policy raises ValueError
    with pytest.raises(ValueError):
        select_waveguide_execution_form(None, candidates, "INVALID_POLICY")

# 4. Pass Manager + Control Memory Bridge Integration
def test_pass_manager_cost_model_integration():
    program = [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=10),
        WideWordProgramInstruction(op="STORE", dst="R1", src1=100),
        WideWordProgramInstruction(op="LOAD", dst="R2", src1=100),
        # Multiplication loop
        WideWordProgramInstruction(op="MOV", dst="R3", src1=0),
        WideWordProgramInstruction(op="MOV", dst="R4", src1=5),
        WideWordProgramInstruction(op="MOV", dst="R5", src1=2),
        "loop:",
        WideWordProgramInstruction(op="CMP", dst="R5", src1=0),
        WideWordProgramInstruction(op="JZ", dst="done"),
        WideWordProgramInstruction(op="AND", dst="R6", src1="R5", src2=1),
        WideWordProgramInstruction(op="JZ", dst="shift"),
        WideWordProgramInstruction(op="ADD", dst="R3", src1="R3", src2="R4"),
        "shift:",
        WideWordProgramInstruction(op="SHL", dst="R4", src1="R4", src2=1),
        WideWordProgramInstruction(op="SHR", dst="R5", src1="R5", src2=1),
        WideWordProgramInstruction(op="JMP", dst="loop"),
        "done:",
        WideWordProgramInstruction(op="ADD", dst="R2", src1="R2", src2="R3"),
        WideWordProgramInstruction(op="HALT")
    ]
    # Set shard A for STORE, shard B for LOAD
    program[1].shard = "A"
    program[1].width = 32
    program[2].shard = "B"
    program[2].width = 32
    
    # Enable cost model and autotuning LOWEST_SIMULATED_CYCLES
    cfg = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_pipeline_compaction=True,
        enable_scoreboard_scheduling=True,
        enable_branch_predication=True,
        enable_memory_alias_analysis=True,
        enable_cost_model=True,
        enable_deterministic_autotuning=True,
        autotuning_policy="LOWEST_SIMULATED_CYCLES"
    )
    
    state = build_waveguide_control_memory_state(width=32, config=cfg)
    rep = execute_waveguide_control_memory_program(program, state, config=cfg)
    
    assert rep.success is True
    pm_report = rep.pass_manager_report
    assert pm_report is not None
    assert "cost_model_report" in pm_report
    assert "autotuning_metadata" in pm_report
    
    # Selected form should be full_safe_optimized (since channel is not enabled, channel forms are unsupported)
    assert pm_report["autotuning_metadata"]["selected_form_id"] == "full_safe_optimized"
    
    # Replay should pass successfully
    ok, err = validate_waveguide_trace_metadata(rep.trace_steps, len(program), width=32, pass_manager_report=pm_report)
    assert ok is True, f"Trace validation error: {err}"

# 5. Benchmark Integration Tests
def test_cost_model_benchmark_cases():
    suite = build_waveguide_benchmark_suite(32)
    case_ids = [c["case_id"] for c in suite]
    
    # Assert new cases are registered in the suite
    assert "cost_model_raw_vs_full_optimized" in case_ids
    assert "cost_model_channel_dependency_vs_kernelized" in case_ids
    assert "autotune_strict_only_selects_raw" in case_ids
    assert "autotune_lowest_cycles_selects_safe_fastest" in case_ids
    assert "autotune_lowest_trace_selects_smallest_trace" in case_ids
    assert "autotune_kernel_preferred_safe" in case_ids

def test_run_cost_model_benchmark_case():
    suite = build_waveguide_benchmark_suite(32)
    case = next(c for c in suite if c["case_id"] == "cost_model_raw_vs_full_optimized")
    
    # Run benchmark case using standard harness
    rep = run_waveguide_benchmark_case(case, width=32)
    assert rep["modes"]["raw_strict"]["success"] is True
    assert rep["modes"]["full_optimized"]["success"] is True
    assert rep["case_id"] == "cost_model_raw_vs_full_optimized"

# 6. Strict Proof + Manifest extension verification
def test_strict_proof_capabilities():
    matrix = build_strict_backend_support_matrix([])
    m = matrix.matrix
    
    # Validate new capability extension metadata stubs exist
    for b in ("lane_fabric_strict", "hybrid_shadow", "pdm_waveguide_microcoded_strict"):
        assert m[b]["supports_waveguide_kernel_cost_model"] == "validated"
        assert m[b]["supports_deterministic_autotuning_policy"] == "validated"
        assert m[b]["supports_cost_model_trace_replay_validation"] == "validated"

def test_manifest_cost_model_section():
    manifest = build_waveguide_rc_manifest()
    assert "cost_model_and_autotuning" in manifest
    c_m = manifest["cost_model_and_autotuning"]
    assert c_m["enabled_by_default"] is False
    assert c_m["primary_metric"] == "deterministic_simulated_cycles"
    assert "STRICT_ONLY" in c_m["policies"]
    assert "SAFEST_OPTIMIZED" in c_m["policies"]
