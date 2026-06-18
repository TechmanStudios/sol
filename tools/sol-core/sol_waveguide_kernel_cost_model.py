# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Microprogram Kernel Cost Model
===========================================
Statically estimates and compares execution costs across equivalent forms.
"""

from typing import List, Dict, Any, Tuple, Optional
import json

from sol_micro_isa_v1_candidates import V1_CANDIDATE_OPCODES

def build_waveguide_cost_model_config(
    enable_cost_model: bool = False,
    enable_deterministic_autotuning: bool = False,
    autotuning_policy: Optional[str] = None,
    unsupported_penalty: int = 1000000,
    safety_penalty: int = 500000,
    skip_penalty: int = 10000
) -> Dict[str, Any]:
    """
    Builds the configuration dictionary for the waveguide kernel cost model.
    """
    return {
        "enable_cost_model": enable_cost_model,
        "enable_deterministic_autotuning": enable_deterministic_autotuning,
        "autotuning_policy": autotuning_policy,
        "unsupported_penalty": unsupported_penalty,
        "safety_penalty": safety_penalty,
        "skip_penalty": skip_penalty
    }

def estimate_waveguide_barrier_cost(clean_instructions: List[Any]) -> int:
    """
    Statically counts barrier instructions in the instruction stream.
    """
    barrier_ops = {"WG_CHAN_FENCE", "FENCE", "HALT"}
    count = 0
    for inst in clean_instructions:
        op = inst.op.upper() if hasattr(inst, "op") else ""
        if op in barrier_ops:
            count += 1
    return count

def estimate_waveguide_trace_footprint(pass_manager_report: Dict[str, Any]) -> int:
    """
    Estimates trace footprint based on instruction count and enabled passes.
    """
    # Footprint is deterministic and proportional to active optimizations
    raw_count = pass_manager_report.get("raw_instruction_count", 0)
    profile_id = pass_manager_report.get("profile_id", "CUSTOM")
    
    # We assign weight factors based on the complexity/metadata attached per step
    base_weight = 1
    if pass_manager_report.get("enable_waveguide_channel_state", False):
        base_weight += 2
        
    for p in pass_manager_report.get("passes", []):
        if p["enabled"] and not p["skipped"]:
            if p["pass_id"] == "scoreboard_scheduling":
                base_weight += 3
            elif p["pass_id"] == "branch_predication":
                base_weight += 2
            elif p["pass_id"] == "memory_alias_analysis":
                base_weight += 1
            elif p["pass_id"] == "channel_dependency_analysis":
                base_weight += 2
            elif p["pass_id"] == "channel_kernel_recognition":
                base_weight += 4

    return raw_count * base_weight

def estimate_waveguide_execution_cost(
    clean_instructions: List[Any],
    pass_manager_report: Dict[str, Any],
    scheduler_report: Optional[Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Estimates deterministic execution cost across multiple dimensions.
    """
    # 1. Base simulated cycles
    raw_ins_count = len(clean_instructions)
    simulated_cycles = raw_ins_count
    wavefront_count = 0
    barrier_count = estimate_waveguide_barrier_cost(clean_instructions)
    compacted_windows = 0
    
    # If scoreboard scheduler report is present
    if scheduler_report is not None:
        simulated_cycles = getattr(scheduler_report, "scheduled_cycle_estimate", raw_ins_count)
        wavefront_count = getattr(scheduler_report, "wavefront_batches", 0)
        barrier_count = len(getattr(scheduler_report, "barriers", []))
    else:
        # Check if compaction savings can be estimated from pass manager report
        compaction_savings = pass_manager_report.get("compacted_cycles_saved", 0)
        simulated_cycles = max(1, raw_ins_count - compaction_savings)

    # 2. Count compacted windows
    for p in pass_manager_report.get("passes", []):
        if p["pass_id"] == "pipeline_compaction" and p["enabled"] and not p["skipped"]:
            compacted_windows = pass_manager_report.get("compacted_windows_count", 0)

    # 3. Penalties
    safety_penalty = 0
    unsupported_penalty = 0
    skip_penalty = 0
    
    # Check if candidate form is unsupported by configuration
    has_v1_ops = any(hasattr(inst, "op") and inst.op.upper() in V1_CANDIDATE_OPCODES for inst in clean_instructions)
    if has_v1_ops and not pass_manager_report.get("enable_micro_isa_v1_candidates", False):
        unsupported_penalty += config.get("unsupported_penalty", 1000000)
        
    channel_ops = {"WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE", "WG_CHAN_FENCE"}
    has_channel_ops = any(hasattr(inst, "op") and inst.op.upper() in channel_ops for inst in clean_instructions)
    if has_channel_ops and not pass_manager_report.get("enable_waveguide_channel_state", False):
        unsupported_penalty += config.get("unsupported_penalty", 1000000)

    # Count skipped passes penalty
    for p in pass_manager_report.get("passes", []):
        if p["enabled"] and p["skipped"]:
            skip_penalty += config.get("skip_penalty", 10000)

    # Footprint
    trace_steps = simulated_cycles
    trace_metadata_weight = estimate_waveguide_trace_footprint(pass_manager_report)

    # Recognized kernels
    recognized_kernels = len(pass_manager_report.get("recognized_kernels", []))

    return {
        "simulated_cycles": simulated_cycles,
        "wavefront_count": wavefront_count,
        "barrier_count": barrier_count,
        "compacted_windows": compacted_windows,
        "scheduled_batches": wavefront_count,
        "recognized_kernels": recognized_kernels,
        "trace_steps": trace_steps,
        "trace_metadata_weight": trace_metadata_weight,
        "safety_penalty": safety_penalty,
        "skip_penalty": skip_penalty,
        "unsupported_penalty": unsupported_penalty,
        "semantic_equivalence_required": pass_manager_report.get("semantic_equivalence_required", True),
        "trace_replay_required": pass_manager_report.get("trace_replay_required", True)
    }

def compare_waveguide_execution_forms(forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks equivalent execution forms using deterministic priorities.
    Returns forms sorted from most preferred (lowest cost) to least preferred.
    """
    aggressiveness_order = [
        "raw_strict",
        "safe_local",
        "safe_memory",
        "safe_control",
        "full_safe_optimized",
        "v1_lowered_full_safe",
        "channel_dependency",
        "channel_kernelized"
    ]

    def form_sort_key(form: Dict[str, Any]) -> Tuple[int, int, int, int, int, int, int]:
        # 1. Reject unsafe or unsupported forms (higher is worse, so 0 is safe, 1 is unsafe)
        is_unsafe = 1 if (not form.get("safe", True) or form.get("cost", {}).get("unsupported_penalty", 0) > 0) else 0
        
        # 2. Prefer verified semantic equivalence
        is_not_equivalent = 1 if not form.get("semantic_equivalence", True) else 0
        
        cost = form.get("cost", {})
        cycles = cost.get("simulated_cycles", 999999)
        barriers = cost.get("barrier_count", 999999)
        
        # Trace footprint weight
        footprint = cost.get("trace_steps", 999999) * cost.get("trace_metadata_weight", 1)
        
        # Aggressiveness ordering index (lower is less aggressive)
        form_id = form.get("form_id", "")
        agg_idx = aggressiveness_order.index(form_id) if form_id in aggressiveness_order else 999
        
        # Skip penalty
        sk_penalty = cost.get("skip_penalty", 0)
        
        return (is_unsafe, is_not_equivalent, cycles, barriers, footprint, sk_penalty, agg_idx)

    # Sort in ascending order (smaller key value means more preferred)
    return sorted(forms, key=form_sort_key)

def summarize_waveguide_cost_model_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a summary of the cost model evaluation report.
    """
    return {
        "form_id": report.get("form_id", "unknown"),
        "safe": report.get("safe", False),
        "semantic_equivalence": report.get("semantic_equivalence", False),
        "simulated_cycles": report.get("cost", {}).get("simulated_cycles", 0),
        "barrier_count": report.get("cost", {}).get("barrier_count", 0),
        "unsupported_penalty": report.get("cost", {}).get("unsupported_penalty", 0)
    }

def validate_waveguide_cost_model_report(report: Dict[str, Any]) -> bool:
    """
    Validates cost model report format and ensures it is JSON serializable.
    """
    required_keys = {"form_id", "safe", "semantic_equivalence", "cost"}
    missing = required_keys - set(report.keys())
    if missing:
        raise ValueError(f"Missing required cost model report keys: {missing}")
        
    cost = report["cost"]
    required_cost_keys = {
        "simulated_cycles", "wavefront_count", "barrier_count", 
        "trace_steps", "trace_metadata_weight", "unsupported_penalty"
    }
    missing_cost = required_cost_keys - set(cost.keys())
    if missing_cost:
        raise ValueError(f"Missing required cost dimensions in report cost field: {missing_cost}")
        
    # Verify JSON serializability
    try:
        json.dumps(report)
    except Exception as e:
        raise ValueError(f"Cost model report is not JSON serializable: {e}")
        
    return True
