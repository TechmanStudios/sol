# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Candidate Release Gate and Delta Audit Harness
===================================================================
Verifies candidate boundaries between RC1 (Foundation) and RC2 (Governed Stack),
applying deterministic validation rules and generating audit artifacts.
"""

from typing import Dict, Any, List, Tuple, Optional
from sol_waveguide_rc_manifest import validate_waveguide_rc_manifest_consistency

# Allowed RC2-only governed execution stack features
GOVERNED_PROFILES = {
    "COST_MODEL_DEBUG",
    "AUTOTUNE_SAFE",
    "AUTOTUNE_LOWEST_CYCLES",
    "KERNEL_AUTOTUNE_SAFE"
}

GOVERNED_PASSES = {
    "channel_kernel_recognition",
    "cost_model_evaluation",
    "deterministic_policy_selection"
}

GOVERNED_FIELDS = {
    "cost_model_and_autotuning"
}

FOUNDATION_PROFILES = {
    "RAW_STRICT",
    "SAFE_LOCAL",
    "SAFE_CONTROL",
    "SAFE_MEMORY",
    "FULL_SAFE_OPTIMIZED",
    "BENCHMARK_MATRIX",
    "DEBUG_TRACE_AUDIT",
    "V1_CANDIDATE_EXPERIMENTAL"
}

FOUNDATION_PASSES = {
    "program_adaptation",
    "v1_candidate_lowering",
    "memory_alias_analysis",
    "channel_dependency_analysis",
    "branch_predication",
    "pipeline_compaction",
    "scoreboard_scheduling",
    "execution_plan_validation",
    "trace_metadata_preparation"
}


def build_waveguide_rc_delta_report(rc1_manifest: Dict[str, Any], rc2_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes differences and boundaries between RC1 and RC2 manifests.
    """
    # 1. Compare profiles
    rc1_profiles = set(rc1_manifest.get("optimization_profiles", []))
    rc2_profiles = set(rc2_manifest.get("optimization_profiles", []))
    
    shared_profiles = list(rc1_profiles & rc2_profiles)
    rc1_only_profiles = list(rc1_profiles - rc2_profiles)
    rc2_only_profiles = list(rc2_profiles - rc1_profiles)
    
    # 2. Compare passes
    rc1_passes = set(rc1_manifest.get("canonical_pass_order", []))
    rc2_passes = set(rc2_manifest.get("canonical_pass_order", []))
    
    shared_passes = list(rc1_passes & rc2_passes)
    rc1_only_passes = list(rc1_passes - rc2_passes)
    rc2_only_passes = list(rc2_passes - rc1_passes)
    
    # 3. Compare fields
    rc1_keys = set(rc1_manifest.keys())
    rc2_keys = set(rc2_manifest.keys())
    
    shared_keys = list(rc1_keys & rc2_keys)
    rc1_only_keys = list(rc1_keys - rc2_keys)
    rc2_only_keys = list(rc2_keys - rc1_keys)

    # 4. Check boundaries and leakage
    leakage_profiles = list(rc1_profiles & GOVERNED_PROFILES)
    leakage_passes = list(rc1_passes & GOVERNED_PASSES)
    leakage_fields = list(rc1_keys & GOVERNED_FIELDS)
    
    governed_leakage = []
    if leakage_profiles:
        governed_leakage.append(f"leakage_profiles: {sorted(leakage_profiles)}")
    if leakage_passes:
        governed_leakage.append(f"leakage_passes: {sorted(leakage_passes)}")
    if leakage_fields:
        governed_leakage.append(f"leakage_fields: {sorted(leakage_fields)}")
        
    # 5. Check missing governed features from RC2
    missing_profiles_rc2 = list(GOVERNED_PROFILES - rc2_profiles)
    missing_passes_rc2 = list(GOVERNED_PASSES - rc2_passes)
    missing_fields_rc2 = list(GOVERNED_FIELDS - rc2_keys)
    
    missing_governed_rc2 = []
    if missing_profiles_rc2:
        missing_governed_rc2.append(f"missing_profiles: {sorted(missing_profiles_rc2)}")
    if missing_passes_rc2:
        missing_governed_rc2.append(f"missing_passes: {sorted(missing_passes_rc2)}")
    if missing_fields_rc2:
        missing_governed_rc2.append(f"missing_fields: {sorted(missing_fields_rc2)}")
        
    # 6. Check unexpected additions
    all_allowed_profiles = FOUNDATION_PROFILES | GOVERNED_PROFILES
    all_allowed_passes = FOUNDATION_PASSES | GOVERNED_PASSES
    
    unexpected_profiles = sorted(list(rc2_profiles - all_allowed_profiles))
    unexpected_passes = sorted(list(rc2_passes - all_allowed_passes))
    
    unexpected_additions = []
    if unexpected_profiles:
        unexpected_additions.append(f"unexpected_profiles: {unexpected_profiles}")
    if unexpected_passes:
        unexpected_additions.append(f"unexpected_passes: {unexpected_passes}")

    # Determine boundary check status
    boundary_ok, boundary_reasons = validate_waveguide_rc_boundary(rc1_manifest, rc2_manifest)

    return {
        "rc1_id": rc1_manifest.get("rc_id"),
        "rc2_id": rc2_manifest.get("rc_id"),
        "shared_features": {
            "profiles": sorted(shared_profiles),
            "passes": sorted(shared_passes),
            "fields": sorted(shared_keys)
        },
        "rc1_only_features": {
            "profiles": sorted(rc1_only_profiles),
            "passes": sorted(rc1_only_passes),
            "fields": sorted(rc1_only_keys)
        },
        "rc2_only_features": {
            "profiles": sorted(rc2_only_profiles),
            "passes": sorted(rc2_only_passes),
            "fields": sorted(rc2_only_keys)
        },
        "governed_feature_leakage": governed_leakage,
        "missing_governed_features_rc2": missing_governed_rc2,
        "unexpected_additions": unexpected_additions,
        "boundary_valid": boundary_ok,
        "boundary_reasons": boundary_reasons,
        "caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation."
    }


def compare_waveguide_rc_manifests(left_manifest: Dict[str, Any], right_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares two manifest dictionaries generically and returns differences.
    """
    left_profiles = set(left_manifest.get("optimization_profiles", []))
    right_profiles = set(right_manifest.get("optimization_profiles", []))
    
    left_passes = set(left_manifest.get("canonical_pass_order", []))
    right_passes = set(right_manifest.get("canonical_pass_order", []))
    
    return {
        "profiles": {
            "added": sorted(list(right_profiles - left_profiles)),
            "removed": sorted(list(left_profiles - right_profiles))
        },
        "passes": {
            "added": sorted(list(right_passes - left_passes)),
            "removed": sorted(list(left_passes - right_passes))
        }
    }


def validate_waveguide_rc_boundary(rc1_manifest: Dict[str, Any], rc2_manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Ensures RC1 Foundation is clean of governed stack features and RC2 includes them.
    """
    reasons = []
    is_valid = True
    
    # 1. Check RC1 leakage
    rc1_profiles = set(rc1_manifest.get("optimization_profiles", []))
    rc1_passes = set(rc1_manifest.get("canonical_pass_order", []))
    rc1_keys = set(rc1_manifest.keys())
    
    leaked_profiles = rc1_profiles & GOVERNED_PROFILES
    leaked_passes = rc1_passes & GOVERNED_PASSES
    leaked_fields = rc1_keys & GOVERNED_FIELDS
    
    if leaked_profiles or leaked_passes or leaked_fields:
        is_valid = False
        reasons.append("RC1_GOVERNED_FEATURE_LEAK")
        
    # 2. Check RC2 missing features
    rc2_profiles = set(rc2_manifest.get("optimization_profiles", []))
    rc2_passes = set(rc2_manifest.get("canonical_pass_order", []))
    rc2_keys = set(rc2_manifest.keys())
    
    missing_profiles = GOVERNED_PROFILES - rc2_profiles
    missing_passes = GOVERNED_PASSES - rc2_passes
    missing_fields = GOVERNED_FIELDS - rc2_keys
    
    if missing_profiles or missing_passes or missing_fields:
        is_valid = False
        reasons.append("RC2_GOVERNED_FEATURE_MISSING")
        
    # 3. Check missing foundation features
    missing_f_profiles_rc1 = FOUNDATION_PROFILES - rc1_profiles
    missing_f_passes_rc1 = FOUNDATION_PASSES - rc1_passes
    missing_f_profiles_rc2 = FOUNDATION_PROFILES - rc2_profiles
    missing_f_passes_rc2 = FOUNDATION_PASSES - rc2_passes
    
    if missing_f_profiles_rc1 or missing_f_passes_rc1:
        is_valid = False
        reasons.append("RC1_FOUNDATION_FEATURE_MISSING")
        
    if missing_f_profiles_rc2 or missing_f_passes_rc2:
        # If foundation features are missing from RC2
        is_valid = False
        if "RC1_FOUNDATION_FEATURE_MISSING" not in reasons:
            reasons.append("RC1_FOUNDATION_FEATURE_MISSING")

    # 4. Check for identity/id mismatch
    if rc1_manifest.get("rc_id") != "SOL-WAVEGUIDE-RC1" or rc2_manifest.get("rc_id") != "SOL-WAVEGUIDE-RC2":
        # Mismatch notes but not necessarily blocked unless leakage or missing
        pass

    if is_valid:
        reasons.append("RC_DELTA_MATCHES_EXPECTATION")
        
    return is_valid, reasons


def build_waveguide_rc_release_gate(candidate_manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a candidate manifest against release gate boundary guidelines.
    """
    verdict = "release_ready"
    reasons = []
    notes = []
    
    # 1. Run consistency validation
    try:
        ok = validate_waveguide_rc_manifest_consistency(candidate_manifest)
        if ok:
            reasons.append("RC_MANIFEST_SCHEMA_VALID")
    except Exception as e:
        verdict = "blocked"
        reasons.append("RC_RELEASE_BLOCKED")
        notes.append(f"Consistency validation failed: {str(e)}")
        return {
            "rc_id": candidate_manifest.get("rc_id"),
            "verdict": verdict,
            "reasons": reasons,
            "notes": notes,
            "caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation."
        }
        
    rc_id = candidate_manifest.get("rc_id")
    profiles = set(candidate_manifest.get("optimization_profiles", []))
    passes = set(candidate_manifest.get("canonical_pass_order", []))
    keys = set(candidate_manifest.keys())
    
    if rc_id in ("SOL-WAVEGUIDE-RC1", "SOL_WAVEGUIDE_RC1"):
        # Check foundation features are present
        missing_f_profiles = FOUNDATION_PROFILES - profiles
        missing_f_passes = FOUNDATION_PASSES - passes
        if missing_f_profiles or missing_f_passes:
            verdict = "blocked"
            reasons.append("RC1_FOUNDATION_FEATURE_MISSING")
            notes.append(f"Missing foundation profiles: {sorted(list(missing_f_profiles))}, passes: {sorted(list(missing_f_passes))}")
            
        # Check leakage
        leaked_profiles = profiles & GOVERNED_PROFILES
        leaked_passes = passes & GOVERNED_PASSES
        leaked_fields = keys & GOVERNED_FIELDS
        if leaked_profiles or leaked_passes or leaked_fields:
            verdict = "blocked"
            reasons.append("RC1_GOVERNED_FEATURE_LEAK")
            notes.append(f"Leaked profiles: {sorted(list(leaked_profiles))}, passes: {sorted(list(leaked_passes))}, fields: {sorted(list(leaked_fields))}")
            
    elif rc_id in ("SOL-WAVEGUIDE-RC2", "SOL_WAVEGUIDE_RC2"):
        # Check foundation features are present
        missing_f_profiles = FOUNDATION_PROFILES - profiles
        missing_f_passes = FOUNDATION_PASSES - passes
        if missing_f_profiles or missing_f_passes:
            verdict = "blocked"
            reasons.append("RC1_FOUNDATION_FEATURE_MISSING")
            notes.append(f"Missing foundation profiles: {sorted(list(missing_f_profiles))}, passes: {sorted(list(missing_f_passes))}")

        # Check governed features are present
        missing_g_profiles = GOVERNED_PROFILES - profiles
        missing_g_passes = GOVERNED_PASSES - passes
        missing_g_fields = GOVERNED_FIELDS - keys
        if missing_g_profiles or missing_g_passes or missing_g_fields:
            verdict = "blocked"
            reasons.append("RC2_GOVERNED_FEATURE_MISSING")
            notes.append(f"Missing RC2 governed profiles: {sorted(list(missing_g_profiles))}, passes: {sorted(list(missing_g_passes))}, fields: {sorted(list(missing_g_fields))}")
            
        # Check for unexpected additions
        all_allowed_profiles = FOUNDATION_PROFILES | GOVERNED_PROFILES
        all_allowed_passes = FOUNDATION_PASSES | GOVERNED_PASSES
        unexpected_profiles = profiles - all_allowed_profiles
        unexpected_passes = passes - all_allowed_passes
        if unexpected_profiles or unexpected_passes:
            if verdict != "blocked":
                verdict = "warning"
            reasons.append("RC2_UNEXPECTED_FEATURE")
            notes.append(f"Unexpected profiles: {sorted(list(unexpected_profiles))}, passes: {sorted(list(unexpected_passes))}")
            
    else:
        verdict = "blocked"
        reasons.append("RC_RELEASE_BLOCKED")
        notes.append(f"Unknown release candidate identity / rc_id: '{rc_id}'")

    if verdict == "release_ready":
        reasons.append("RC_RELEASE_READY")
        notes.append("All boundary and manifest consistency checks passed successfully.")
    else:
        if "RC_RELEASE_BLOCKED" not in reasons and verdict == "blocked":
            reasons.append("RC_RELEASE_BLOCKED")

    return {
        "rc_id": rc_id,
        "verdict": verdict,
        "reasons": sorted(list(set(reasons))),
        "notes": notes,
        "caveat": "Validation is shadow/sandbox software validation, not quantum hardware validation."
    }


def summarize_waveguide_rc_release_gate(report: Dict[str, Any]) -> str:
    """
    Creates a deterministic human-readable text summary of the release gate evaluation report.
    """
    lines = [
        "============================================================",
        " SOL WAVEGUIDE RELEASE CANDIDATE RELEASE GATE AUDIT SUMMARY",
        "============================================================",
        f"Candidate ID:     {report.get('rc_id')}",
        f"Release Verdict:  {report.get('verdict', '').upper()}",
        "Reason Codes:",
    ]
    for code in report.get("reasons", []):
        lines.append(f"  - {code}")
        
    lines.append("Audit Notes:")
    for note in report.get("notes", []):
        lines.append(f"  * {note}")
        
    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {report.get('caveat')}")
    lines.append("============================================================")
    
    return "\n".join(lines)
