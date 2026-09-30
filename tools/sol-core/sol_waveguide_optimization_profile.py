# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Optimization Profile Module
=========================================
Defines standard optimization profiles and configures backend flags.
"""

from typing import Dict, Any, Optional

# Named Profiles
RAW_STRICT = "RAW_STRICT"
SAFE_LOCAL = "SAFE_LOCAL"
SAFE_CONTROL = "SAFE_CONTROL"
SAFE_MEMORY = "SAFE_MEMORY"
FULL_SAFE_OPTIMIZED = "FULL_SAFE_OPTIMIZED"
BENCHMARK_MATRIX = "BENCHMARK_MATRIX"
DEBUG_TRACE_AUDIT = "DEBUG_TRACE_AUDIT"
V1_CANDIDATE_EXPERIMENTAL = "V1_CANDIDATE_EXPERIMENTAL"

# New Autotune/Cost Model Profiles
COST_MODEL_DEBUG = "COST_MODEL_DEBUG"
AUTOTUNE_SAFE = "AUTOTUNE_SAFE"
AUTOTUNE_LOWEST_CYCLES = "AUTOTUNE_LOWEST_CYCLES"
KERNEL_AUTOTUNE_SAFE = "KERNEL_AUTOTUNE_SAFE"

PROFILES = {
    RAW_STRICT: {
        "enable_pipeline_compaction": False,
        "enable_scoreboard_scheduling": False,
        "enable_branch_predication": False,
        "enable_memory_alias_analysis": False,
        "enable_micro_isa_v1_candidates": False,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    SAFE_LOCAL: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": False,
        "enable_branch_predication": False,
        "enable_memory_alias_analysis": False,
        "enable_micro_isa_v1_candidates": False,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    SAFE_CONTROL: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": False,
        "enable_micro_isa_v1_candidates": False,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    SAFE_MEMORY: {
        "enable_pipeline_compaction": False,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": False,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": False,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    FULL_SAFE_OPTIMIZED: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": False,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    BENCHMARK_MATRIX: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": False,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    DEBUG_TRACE_AUDIT: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": False,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    V1_CANDIDATE_EXPERIMENTAL: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": True,
        "enable_cost_model": False,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    COST_MODEL_DEBUG: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": True,
        "enable_cost_model": True,
        "enable_deterministic_autotuning": False,
        "autotuning_policy": None,
    },
    AUTOTUNE_SAFE: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": True,
        "enable_cost_model": True,
        "enable_deterministic_autotuning": True,
        "autotuning_policy": "SAFEST_OPTIMIZED",
    },
    AUTOTUNE_LOWEST_CYCLES: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": True,
        "enable_cost_model": True,
        "enable_deterministic_autotuning": True,
        "autotuning_policy": "LOWEST_SIMULATED_CYCLES",
    },
    KERNEL_AUTOTUNE_SAFE: {
        "enable_pipeline_compaction": True,
        "enable_scoreboard_scheduling": True,
        "enable_branch_predication": True,
        "enable_memory_alias_analysis": True,
        "enable_micro_isa_v1_candidates": True,
        "enable_cost_model": True,
        "enable_deterministic_autotuning": True,
        "autotuning_policy": "KERNEL_PREFERRED_SAFE",
    }
}

def validate_waveguide_optimization_profile(profile_id: str) -> bool:
    """
    Validates if a profile_id is known. Raises ValueError if not.
    """
    if profile_id not in PROFILES:
        raise ValueError(f"Unknown optimization profile: '{profile_id}'")
    return True

def build_waveguide_optimization_profile(profile_id: str) -> Dict[str, Any]:
    """
    Returns config dictionary for a given profile_id.
    """
    validate_waveguide_optimization_profile(profile_id)
    return dict(PROFILES[profile_id])

def resolve_waveguide_optimization_profile(config: Any) -> str:
    """
    Given a config object (e.g. WaveguideControlMemoryBridgeConfig),
    identifies which profile most closely matches its current flags,
    or returns "CUSTOM" if no standard profile matches.
    """
    comp = getattr(config, "enable_pipeline_compaction", False)
    sched = getattr(config, "enable_scoreboard_scheduling", False)
    pred = getattr(config, "enable_branch_predication", False)
    alias = getattr(config, "enable_memory_alias_analysis", False)
    v1_cand = getattr(config, "enable_micro_isa_v1_candidates", False)
    cost = getattr(config, "enable_cost_model", False)
    tune = getattr(config, "enable_deterministic_autotuning", False)
    policy = getattr(config, "autotuning_policy", None)
    
    for p_id, p_flags in PROFILES.items():
        if (p_flags["enable_pipeline_compaction"] == comp and
            p_flags["enable_scoreboard_scheduling"] == sched and
            p_flags["enable_branch_predication"] == pred and
            p_flags["enable_memory_alias_analysis"] == alias and
            p_flags.get("enable_micro_isa_v1_candidates", False) == v1_cand and
            p_flags.get("enable_cost_model", False) == cost and
            p_flags.get("enable_deterministic_autotuning", False) == tune and
            p_flags.get("autotuning_policy", None) == policy):
            return p_id
            
    return "CUSTOM"

def profile_to_waveguide_execution_config(profile_id: str, width: int, memory_slots: int = 65536) -> Any:
    """
    Resolves a profile to a WaveguideControlMemoryBridgeConfig instance.
    """
    from sol_waveguide_control_memory_bridge import WaveguideControlMemoryBridgeConfig
    validate_waveguide_optimization_profile(profile_id)
    flags = PROFILES[profile_id]
    return WaveguideControlMemoryBridgeConfig(
        width=width,
        memory_slots=memory_slots,
        enable_pipeline_compaction=flags["enable_pipeline_compaction"],
        enable_scoreboard_scheduling=flags["enable_scoreboard_scheduling"],
        enable_branch_predication=flags["enable_branch_predication"],
        enable_memory_alias_analysis=flags["enable_memory_alias_analysis"],
        enable_micro_isa_v1_candidates=flags["enable_micro_isa_v1_candidates"],
        enable_cost_model=flags.get("enable_cost_model", False),
        enable_deterministic_autotuning=flags.get("enable_deterministic_autotuning", False),
        autotuning_policy=flags.get("autotuning_policy", None),
        optimization_profile=profile_id
    )

def summarize_waveguide_optimization_profile(profile_id: str) -> Dict[str, Any]:
    """
    Returns summary details of the given profile.
    """
    validate_waveguide_optimization_profile(profile_id)
    return {
        "profile_id": profile_id,
        "flags": PROFILES[profile_id]
    }
