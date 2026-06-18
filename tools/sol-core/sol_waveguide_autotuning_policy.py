# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Autotuning Policy Module
======================================
Implements deterministic policies to resolve and select the optimal execution form.
"""

from typing import List, Dict, Any, Tuple, Optional
from sol_waveguide_kernel_cost_model import compare_waveguide_execution_forms

# Named Policies
STRICT_ONLY = "STRICT_ONLY"
SAFEST_OPTIMIZED = "SAFEST_OPTIMIZED"
LOWEST_SIMULATED_CYCLES = "LOWEST_SIMULATED_CYCLES"
LOWEST_TRACE_FOOTPRINT = "LOWEST_TRACE_FOOTPRINT"
KERNEL_PREFERRED_SAFE = "KERNEL_PREFERRED_SAFE"
DEBUG_EXPLAIN = "DEBUG_EXPLAIN"

VALID_POLICIES = {
    STRICT_ONLY,
    SAFEST_OPTIMIZED,
    LOWEST_SIMULATED_CYCLES,
    LOWEST_TRACE_FOOTPRINT,
    KERNEL_PREFERRED_SAFE,
    DEBUG_EXPLAIN
}

def build_waveguide_autotuning_policy(
    policy_name: str = STRICT_ONLY,
    fallback_policy: Optional[str] = STRICT_ONLY
) -> Dict[str, Any]:
    """
    Builds the autotuning policy configuration.
    """
    if policy_name not in VALID_POLICIES:
        raise ValueError(f"Unknown autotuning policy: '{policy_name}'")
    return {
        "policy_name": policy_name,
        "fallback_policy": fallback_policy
    }

def resolve_waveguide_autotuning_policy(policy_name: str) -> str:
    """
    Validates and resolves policy name.
    """
    if policy_name not in VALID_POLICIES:
        raise ValueError(f"Invalid autotuning policy name: '{policy_name}'")
    return policy_name

def select_waveguide_execution_form(
    program: Any,
    candidates: List[Dict[str, Any]],
    policy_name: str
) -> Dict[str, Any]:
    """
    Selects the optimal execution form from candidates based on the named policy.
    Returns the decision report dict.
    """
    resolved_policy = resolve_waveguide_autotuning_policy(policy_name)
    
    # 1. Filter out unsafe/unsupported forms for any optimized selection
    # For STRICT_ONLY, we only care about raw_strict.
    
    # Find raw_strict
    raw_strict_candidate = next((c for c in candidates if c["form_id"] == "raw_strict"), None)
    if raw_strict_candidate is None:
        raise ValueError("Critical Error: 'raw_strict' execution form candidate not found.")

    selected_candidate = None
    explanation = ""
    rejections = {}

    # Gather rejections
    for c in candidates:
        reasons = []
        if not c.get("safe", True):
            reasons.append("Marked unsafe")
        if not c.get("semantic_equivalence", True):
            reasons.append("Semantic equivalence not verified")
        if c.get("cost", {}).get("unsupported_penalty", 0) > 0:
            reasons.append("Unsupported penalty active")
        if reasons:
            rejections[c["form_id"]] = reasons

    sorted_candidates = compare_waveguide_execution_forms(candidates)
    safe_equivalent_candidates = [c for c in sorted_candidates if c.get("safe", True) and c.get("semantic_equivalence", True) and c.get("cost", {}).get("unsupported_penalty", 0) == 0]

    if resolved_policy == STRICT_ONLY:
        selected_candidate = raw_strict_candidate
        explanation = "STRICT_ONLY policy: Raw strict execution form selected."
        for c in candidates:
            if c["form_id"] != "raw_strict":
                rejections[c["form_id"]] = rejections.get(c["form_id"], []) + ["Policy forbids optimization"]
                
    elif resolved_policy == SAFEST_OPTIMIZED:
        # Least aggressive optimized form (which is sorted by aggressiveness)
        # Sort key puts lower aggressiveness first if tied, but compare_waveguide_execution_forms sorts cycles first.
        # For SAFEST_OPTIMIZED, we want the safe equivalent candidate with the lowest aggressiveness index that is NOT raw_strict.
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
        
        # Filter safe equivalent candidates that are not raw_strict
        opt_candidates = [c for c in safe_equivalent_candidates if c["form_id"] != "raw_strict"]
        if opt_candidates:
            # Sort by aggressiveness order
            opt_candidates.sort(key=lambda x: aggressiveness_order.index(x["form_id"]) if x["form_id"] in aggressiveness_order else 999)
            selected_candidate = opt_candidates[0]
            explanation = f"SAFEST_OPTIMIZED policy: Selected safest/least-aggressive optimized form '{selected_candidate['form_id']}'."
        else:
            selected_candidate = raw_strict_candidate
            explanation = "SAFEST_OPTIMIZED policy: No optimized form is safe and equivalent. Fell back to raw_strict."
            
    elif resolved_policy == LOWEST_SIMULATED_CYCLES:
        if safe_equivalent_candidates:
            selected_candidate = safe_equivalent_candidates[0]
            explanation = f"LOWEST_SIMULATED_CYCLES policy: Selected lowest cycle form '{selected_candidate['form_id']}' with {selected_candidate['cost']['simulated_cycles']} cycles."
        else:
            selected_candidate = raw_strict_candidate
            explanation = "LOWEST_SIMULATED_CYCLES policy: No optimized form is safe and equivalent. Fell back to raw_strict."

    elif resolved_policy == LOWEST_TRACE_FOOTPRINT:
        if safe_equivalent_candidates:
            # Sort by trace footprint = trace_steps * trace_metadata_weight
            def footprint_key(c):
                cost = c["cost"]
                return (cost["trace_steps"] * cost["trace_metadata_weight"], cost["simulated_cycles"], cost["barrier_count"])
            footprint_sorted = sorted(safe_equivalent_candidates, key=footprint_key)
            selected_candidate = footprint_sorted[0]
            explanation = f"LOWEST_TRACE_FOOTPRINT policy: Selected smallest trace form '{selected_candidate['form_id']}'."
        else:
            selected_candidate = raw_strict_candidate
            explanation = "LOWEST_TRACE_FOOTPRINT policy: No optimized form is safe and equivalent. Fell back to raw_strict."

    elif resolved_policy == KERNEL_PREFERRED_SAFE:
        # Prefer channel_kernelized if it is safe and equivalent and not slower than other forms
        kernel_candidate = next((c for c in safe_equivalent_candidates if c["form_id"] == "channel_kernelized"), None)
        if kernel_candidate:
            # Check if cycles of kernelized form are <= cycles of lowest cycle form
            lowest_cycle_c = safe_equivalent_candidates[0]
            if kernel_candidate["cost"]["simulated_cycles"] <= lowest_cycle_c["cost"]["simulated_cycles"]:
                selected_candidate = kernel_candidate
                explanation = "KERNEL_PREFERRED_SAFE policy: Channel kernelized form is safe and equivalent with optimal cycles."
            else:
                selected_candidate = lowest_cycle_c
                explanation = f"KERNEL_PREFERRED_SAFE policy: Channel kernelized form is slower ({kernel_candidate['cost']['simulated_cycles']} cycles) than lowest cycle form '{lowest_cycle_c['form_id']}' ({lowest_cycle_c['cost']['simulated_cycles']} cycles). Selected lowest cycle form."
        else:
            if safe_equivalent_candidates:
                selected_candidate = safe_equivalent_candidates[0]
                explanation = f"KERNEL_PREFERRED_SAFE policy: Channel kernelized form not available/safe. Selected lowest cycle form '{selected_candidate['form_id']}'."
            else:
                selected_candidate = raw_strict_candidate
                explanation = "KERNEL_PREFERRED_SAFE policy: No optimized form is safe. Selected raw_strict."

    elif resolved_policy == DEBUG_EXPLAIN:
        # Emit explanation without aggressive selection (select raw_strict, but explain all options)
        selected_candidate = raw_strict_candidate
        explanation = "DEBUG_EXPLAIN policy: raw_strict selected. Full candidate report emitted."

    # Mark selected candidate
    for c in candidates:
        c["selected"] = (c["form_id"] == selected_candidate["form_id"])

    # Update skip reasons for not selected candidates
    for c in candidates:
        if not c["selected"]:
            reasons = rejections.get(c["form_id"], [])
            if not reasons:
                reasons = [f"Deprioritized by policy '{resolved_policy}'"]
            c["skip_reasons"] = list(set(c.get("skip_reasons", []) + reasons))

    return {
        "policy_name": resolved_policy,
        "selected_form_id": selected_candidate["form_id"],
        "explanation": explanation,
        "rejections": rejections,
        "candidates": candidates
    }

def validate_waveguide_policy_decision(
    decision: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    policy_name: str
) -> bool:
    """
    Validates policy decision consistency.
    """
    if decision.get("policy_name") != policy_name:
        raise ValueError(f"Decision policy '{decision.get('policy_name')}' does not match expected '{policy_name}'")
        
    sel_id = decision.get("selected_form_id")
    if not sel_id:
        raise ValueError("Decision is missing selected_form_id.")
        
    selected_c = next((c for c in candidates if c["form_id"] == sel_id), None)
    if selected_c is None:
        raise ValueError(f"Selected form ID '{sel_id}' not found in candidate list.")
        
    if not selected_c.get("safe", True) or selected_c.get("cost", {}).get("unsupported_penalty", 0) > 0:
        raise ValueError(f"Policy violated safety constraint: selected form '{sel_id}' is marked unsafe or unsupported.")
        
    return True

def summarize_waveguide_autotuning_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns summary details of the autotuning decision report.
    """
    return {
        "policy_name": report.get("policy_name"),
        "selected_form_id": report.get("selected_form_id"),
        "explanation": report.get("explanation")
    }
