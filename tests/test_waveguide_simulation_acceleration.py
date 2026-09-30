# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Simulation Performance Acceleration Bridge
"""

import pytest
import copy
from sol_waveguide_simulation_acceleration import (
    build_waveguide_acceleration_config,
    optimize_waveguide_trace_allocation,
    run_waveguide_benchmark_batch_serial,
    run_waveguide_benchmark_batch_accelerated,
    run_waveguide_trace_replay_batch_serial,
    run_waveguide_trace_replay_batch_accelerated,
    summarize_waveguide_acceleration_report,
    validate_waveguide_acceleration_equivalence
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_waveguide_optimization_benchmark import (
    build_waveguide_benchmark_suite,
    run_waveguide_benchmark_case,
    run_waveguide_optimization_matrix_batch
)
from sol_waveguide_trace_replay import (
    run_waveguide_trace_replay_batch
)
from sol_strict_backend_execution_proof import (
    build_strict_backend_support_matrix
)

# 1. Acceleration config defaults are serial-safe.
def test_acceleration_config_defaults():
    cfg = build_waveguide_acceleration_config()
    assert cfg["enable_simulation_acceleration"] is False
    assert cfg["enable_offline_benchmark_parallelism"] is False
    assert cfg["enable_offline_trace_replay_parallelism"] is False
    assert cfg["max_workers"] == 1

# 2. Compact trace mode does not alter final semantic state.
def test_compact_trace_mode_semantics():
    prog = [
        ("LOAD_IMM", "R1", 10),
        ("LOAD_IMM", "R2", 20),
        ("ADD", "R3", "R1", "R2"),
        ("HALT",)
    ]
    
    # Run normal mode
    cfg_normal = WaveguideControlMemoryBridgeConfig(
        width=32,
        optimization_profile="FULL_SAFE_OPTIMIZED"
    )
    state_normal = build_waveguide_control_memory_state(width=32)
    report_normal = execute_waveguide_control_memory_program(prog, state_normal, cfg_normal)
    
    # Run compact trace mode
    cfg_compact = WaveguideControlMemoryBridgeConfig(
        width=32,
        optimization_profile="FULL_SAFE_OPTIMIZED",
        enable_simulation_acceleration=True,
        enable_compact_trace_mode=True
    )
    state_compact = build_waveguide_control_memory_state(width=32)
    report_compact = execute_waveguide_control_memory_program(prog, state_compact, cfg_compact)
    
    # Verify final semantic state registers match
    assert state_normal.registers == state_compact.registers
    assert report_normal.success == report_compact.success
    
    # Verify trace steps are stripped of massive dumps in compact mode
    assert len(report_compact.trace_steps) > 0
    step0 = report_compact.trace_steps[0]
    assert step0.scheduler_metadata is None
    assert step0.branch_trace is None
    assert step0.memory_trace is None
    assert getattr(step0, "memory_alias_metadata", None) is None

# 3 & 4. Serial and Accelerated benchmark batches match.
def test_benchmark_batch_equivalence():
    suite = build_waveguide_benchmark_suite(32)
    # Pick a subset to keep the test fast
    subset_cases = suite[:3]
    
    batch_input = [{"case": c, "width": 32} for c in subset_cases]
    
    # Run serial batch
    cfg_serial = build_waveguide_acceleration_config(
        enable_simulation_acceleration=True,
        enable_offline_benchmark_parallelism=False,
        max_workers=1
    )
    res_serial = run_waveguide_optimization_matrix_batch(batch_input, cfg_serial)
    
    # Run accelerated parallel batch
    cfg_accel = build_waveguide_acceleration_config(
        enable_simulation_acceleration=True,
        enable_offline_benchmark_parallelism=True,
        max_workers=2
    )
    res_accel = run_waveguide_optimization_matrix_batch(batch_input, cfg_accel)
    
    # Validate equivalence
    eq = validate_waveguide_acceleration_equivalence(res_serial["cases"], res_accel["cases"])
    assert eq is True
    
    # Deterministic sorting check
    assert res_accel["cases"][0]["case_id"] <= res_accel["cases"][1]["case_id"]

# 5 & 6. Serial and Accelerated trace replay batches match.
def test_trace_replay_batch_equivalence():
    prog = [
        ("LOAD_IMM", "R1", 100),
        ("HALT",)
    ]
    cfg = WaveguideControlMemoryBridgeConfig(width=32, optimization_profile="FULL_SAFE_OPTIMIZED")
    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog, state, cfg)
    
    replay_cases = [
        {
            "case_id": "test_case_A",
            "width": 32,
            "trace_steps": report.trace_steps
        },
        {
            "case_id": "test_case_B",
            "width": 32,
            "trace_steps": report.trace_steps
        }
    ]
    
    # Run serial
    cfg_serial = build_waveguide_acceleration_config(
        enable_simulation_acceleration=True,
        enable_offline_trace_replay_parallelism=False,
        max_workers=1
    )
    res_serial = run_waveguide_trace_replay_batch(replay_cases, cfg_serial)
    
    # Run accelerated
    cfg_accel = build_waveguide_acceleration_config(
        enable_simulation_acceleration=True,
        enable_offline_trace_replay_parallelism=True,
        max_workers=2
    )
    res_accel = run_waveguide_trace_replay_batch(replay_cases, cfg_accel)
    
    # Validate equivalence
    eq = validate_waveguide_acceleration_equivalence(res_serial["results"], res_accel["results"])
    assert eq is True
    
    # Check deterministic ordering
    assert res_accel["results"][0]["case_id"] == "test_case_A"
    assert res_accel["results"][1]["case_id"] == "test_case_B"

# 7 & 8 & 9. Acceleration metadata audits.
def test_acceleration_metadata_audits():
    cfg = build_waveguide_acceleration_config(
        enable_simulation_acceleration=True,
        max_workers=4
    )
    report = summarize_waveguide_acceleration_report(cfg, "offline_benchmark_batch")
    
    # Verify constraints: core execution is not parallelized, no pytest parallelism
    assert report["simulation_acceleration_enabled"] is True
    assert report["core_execution_parallelized"] is False
    assert report["pytest_parallelism_used"] is False
    assert report["parallel_workers"] == 4
    assert report["deterministic_result_ordering"] is True

# 10. Strict proof and v0 compliance are unaffected.
def test_strict_proof_unaffected():
    support_matrix_obj = build_strict_backend_support_matrix(results=[])
    matrix = support_matrix_obj.matrix
    # Check that core feature supports exist and are validated
    assert matrix["pdm_waveguide_microcoded_strict"]["supports_strict_microcoded_execution"] == "validated"
    assert matrix["pdm_waveguide_microcoded_strict"]["supports_memory_alias_analysis"] == "validated"
