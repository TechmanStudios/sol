# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Verification suite for the SOL Waveguide Optimization Profile + Pass Manager Bridge.
"""

import pytest
from typing import Dict, Any, List

from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_waveguide_optimization_profile import (
    validate_waveguide_optimization_profile,
    build_waveguide_optimization_profile,
    resolve_waveguide_optimization_profile,
    profile_to_waveguide_execution_config,
    summarize_waveguide_optimization_profile,
    RAW_STRICT,
    SAFE_LOCAL,
    SAFE_CONTROL,
    SAFE_MEMORY,
    FULL_SAFE_OPTIMIZED,
    DEBUG_TRACE_AUDIT
)
from sol_waveguide_optimization_pass_manager import (
    validate_waveguide_pass_order,
    build_waveguide_pass_pipeline,
    run_waveguide_optimization_passes,
    summarize_waveguide_pass_manager_report
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    WaveguideControlMemoryBridgeConfig,
    execute_waveguide_control_memory_program
)
from sol_waveguide_trace_replay import (
    validate_waveguide_trace_metadata,
    validate_waveguide_pass_manager_trace_metadata,
    replay_waveguide_execution_trace
)
from sol_strict_backend_execution_proof import build_strict_backend_support_matrix

# 1. Profile Resolution Tests
def test_profile_resolution():
    # Test valid profiles
    assert validate_waveguide_optimization_profile(RAW_STRICT) is True
    assert validate_waveguide_optimization_profile(FULL_SAFE_OPTIMIZED) is True
    
    # Test invalid profile
    with pytest.raises(ValueError, match="Unknown optimization profile"):
        validate_waveguide_optimization_profile("INVALID_PROFILE")
        
    # Check flags for RAW_STRICT
    raw_flags = build_waveguide_optimization_profile(RAW_STRICT)
    assert raw_flags["enable_pipeline_compaction"] is False
    assert raw_flags["enable_scoreboard_scheduling"] is False
    assert raw_flags["enable_branch_predication"] is False
    assert raw_flags["enable_memory_alias_analysis"] is False
    
    # Check flags for FULL_SAFE_OPTIMIZED
    opt_flags = build_waveguide_optimization_profile(FULL_SAFE_OPTIMIZED)
    assert opt_flags["enable_pipeline_compaction"] is True
    assert opt_flags["enable_scoreboard_scheduling"] is True
    assert opt_flags["enable_branch_predication"] is True
    assert opt_flags["enable_memory_alias_analysis"] is True
    
    # Resolve config to profile
    config_raw = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_pipeline_compaction=False,
        enable_scoreboard_scheduling=False,
        enable_branch_predication=False,
        enable_memory_alias_analysis=False
    )
    assert resolve_waveguide_optimization_profile(config_raw) == RAW_STRICT
    
    # Test profile to config converter
    config_opt = profile_to_waveguide_execution_config(FULL_SAFE_OPTIMIZED, width=64)
    assert config_opt.width == 64
    assert config_opt.enable_pipeline_compaction is True
    assert config_opt.enable_scoreboard_scheduling is True
    assert config_opt.enable_branch_predication is True
    assert config_opt.enable_memory_alias_analysis is True
    assert config_opt.optimization_profile == FULL_SAFE_OPTIMIZED

# 2. Pass Order Validation Tests
def test_pass_order_validation():
    # Valid order
    valid_order = ["program_adaptation", "memory_alias_analysis", "scoreboard_scheduling"]
    assert validate_waveguide_pass_order(valid_order) is True
    
    # Invalid order: scheduler before program adaptation
    invalid_order = ["scoreboard_scheduling", "program_adaptation"]
    with pytest.raises(ValueError, match="Invalid pass execution order"):
        validate_waveguide_pass_order(invalid_order)
        
    # Test pipeline building
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_pipeline_compaction=True,
        enable_scoreboard_scheduling=True,
        enable_branch_predication=False,
        enable_memory_alias_analysis=True
    )
    pipeline = build_waveguide_pass_pipeline(config)
    assert "program_adaptation" in pipeline
    assert "memory_alias_analysis" in pipeline
    assert "pipeline_compaction" in pipeline
    assert "scoreboard_scheduling" in pipeline
    assert "branch_predication" not in pipeline

# 3. Control-Memory Bridge Integration Tests
def test_control_memory_bridge_profile_integration():
    # Straight-line ALU program
    program = [
        ("MOV", "R1", 10),
        ("MOV", "R2", 20),
        ("ADD", "R3", "R1", "R2"),
        ("HALT",)
    ]
    
    # Execute under RAW_STRICT profile
    state_raw = build_waveguide_control_memory_state(width=32)
    config_raw = WaveguideControlMemoryBridgeConfig(width=32, optimization_profile=RAW_STRICT)
    report_raw = execute_waveguide_control_memory_program(program, state_raw, config_raw)
    
    assert report_raw.success is True
    assert state_raw.registers["R3"] == 30
    assert report_raw.pass_manager_report is not None
    assert report_raw.pass_manager_report["profile_id"] == RAW_STRICT
    
    # Execute under FULL_SAFE_OPTIMIZED profile
    state_opt = build_waveguide_control_memory_state(width=32)
    config_opt = WaveguideControlMemoryBridgeConfig(width=32, optimization_profile=FULL_SAFE_OPTIMIZED)
    report_opt = execute_waveguide_control_memory_program(program, state_opt, config_opt)
    
    assert report_opt.success is True
    assert state_opt.registers["R3"] == 30
    assert report_opt.pass_manager_report["profile_id"] == FULL_SAFE_OPTIMIZED
    
    # Verify both states are equivalent
    assert state_raw.registers == state_opt.registers
    assert state_raw.flags == state_opt.flags

# 4. Trace Replay Integration & Validation
def test_trace_replay_pass_manager_validation():
    # Mock trace step
    class MockStep:
        def __init__(self):
            self.pc_before = 0
            self.pc_after = 1
            self.scheduler_metadata = None
            self.predication_metadata = None
            self.memory_alias_metadata = None
            
    step = MockStep()
    
    # 1. Active metadata but pass manager report is missing
    # scheduler metadata active but report is None
    step.scheduler_metadata = {"scheduler_enabled": True}
    ok, err = validate_waveguide_pass_manager_trace_metadata([step], None, 32, enforce_missing_report=True)
    assert ok is False
    assert "has scheduler_metadata but pass manager report is missing" in err
    
    # 2. Disabled pass emitting active metadata
    pm_report = {
        "profile_id": RAW_STRICT,
        "passes": [
            {"pass_id": "program_adaptation", "enabled": True},
            {"pass_id": "memory_alias_analysis", "enabled": False},
            {"pass_id": "branch_predication", "enabled": False},
            {"pass_id": "pipeline_compaction", "enabled": False},
            {"pass_id": "scoreboard_scheduling", "enabled": False},
            {"pass_id": "execution_plan_validation", "enabled": True},
            {"pass_id": "trace_metadata_preparation", "enabled": True}
        ],
        "raw_instruction_count": 5,
        "optimized_plan_units": 3
    }
    
    # Scheduler metadata present but scoreboard_scheduling pass is disabled
    ok2, err2 = validate_waveguide_pass_manager_trace_metadata([step], pm_report, 32)
    assert ok2 is False
    assert "scoreboard_scheduling pass is disabled" in err2
    
    # Clear scheduler metadata, should pass
    step.scheduler_metadata = None
    ok3, err3 = validate_waveguide_pass_manager_trace_metadata([step], pm_report, 32)
    assert ok3 is True

# 5. Strict Capability Matrix Proof Verification
def test_strict_proof_capabilities():
    matrix_report = build_strict_backend_support_matrix([])
    capabilities = matrix_report.matrix["pdm_waveguide_microcoded_strict"]
    
    assert "supports_optimization_profiles" in capabilities
    assert "supports_waveguide_pass_manager" in capabilities
    assert "supports_unified_optimization_reports" in capabilities
    assert capabilities["supports_optimization_profiles"] == "validated"
    assert capabilities["supports_waveguide_pass_manager"] == "validated"
    assert capabilities["supports_unified_optimization_reports"] == "validated"
