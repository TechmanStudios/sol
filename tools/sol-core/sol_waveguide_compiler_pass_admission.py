# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Compiler Pass Admission Controller for SOL Waveguide RC1 and RC2.
Enforces that requested passes and optimization profiles comply with
read-only capability policies resolved from the release registry.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_runtime_capability_resolver import (
    validate_waveguide_runtime_capability_resolution,
    build_waveguide_runtime_capability_request,
    resolve_waveguide_runtime_capabilities
)


@dataclass
class WaveguidePassAdmissionRequest:
    request_id: str
    rc_id: str
    candidate_level: str
    requested_pass: str
    requested_profile: Optional[str]
    requested_scope: str                 # foundation_pass, governed_execution_pass, profile_selection, optimization_selection
    capability_resolution_path: str
    capability_resolution_digest: str
    strict_waveguide_required: bool
    lane_fabric_fallback_requested: bool
    hybrid_execution_requested: bool
    production_mutation_requested: bool
    software_validation_caveat_required: bool
    request_digest: str = ""


@dataclass
class WaveguidePassAdmissionDecision:
    decision_id: str
    request_id: str
    rc_id: str
    candidate_level: str
    requested_pass: str
    requested_profile: Optional[str]
    requested_scope: str
    capability_resolution_digest: str
    capability_status: str
    admission_status: str               # pass_admitted, pass_blocked, pass_warning
    pass_allowed: bool
    profile_allowed: bool
    strict_waveguide_required: bool
    lane_fabric_fallback_allowed: bool
    hybrid_execution_allowed: bool
    production_mutation_allowed: bool
    reason_codes: List[str]
    notes: str
    software_validation_caveat: str
    decision_digest: str = ""


def hash_waveguide_pass_admission_request(req: Any) -> str:
    """
    Computes digest for a pass admission request, excluding request_digest.
    """
    if hasattr(req, "__dict__"):
        r_dict = asdict(req)
    elif isinstance(req, dict):
        r_dict = dict(req)
    else:
        raise TypeError("request must be a dictionary or a dataclass instance")

    r_dict.pop("request_digest", None)
    return hash_data(r_dict)


def hash_waveguide_pass_admission_decision(dec: Any) -> str:
    """
    Computes digest for an admission decision, excluding decision_digest.
    """
    if hasattr(dec, "__dict__"):
        r_dict = asdict(dec)
    elif isinstance(dec, dict):
        r_dict = dict(dec)
    else:
        raise TypeError("decision must be a dictionary or a dataclass instance")

    r_dict.pop("decision_digest", None)
    return hash_data(r_dict)


def build_waveguide_pass_admission_request(
    rc_id: str,
    requested_pass: str,
    requested_profile: Optional[str] = None,
    requested_scope: Optional[str] = None,
    capability_resolution_path: Optional[str] = None,
    capability_resolution_digest: Optional[str] = None,
    strict_waveguide_required: bool = True,
    lane_fabric_fallback_requested: bool = False,
    hybrid_execution_requested: bool = False,
    production_mutation_requested: bool = False,
    software_validation_caveat_required: bool = True
) -> WaveguidePassAdmissionRequest:
    """
    Constructs an admission request record.
    """
    level = "RC1" if "RC1" in rc_id else "RC2"
    candidate_level = "foundation" if level == "RC1" else "governed_execution_stack"

    if not requested_scope:
        if requested_profile:
            requested_scope = "profile_selection"
        else:
            requested_scope = "foundation_pass" if level == "RC1" else "governed_execution_pass"

    if not capability_resolution_path:
        capability_resolution_path = f"docs/SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_{level}.json"
    capability_resolution_path = normalize_to_repo_path(capability_resolution_path)

    # Load capability resolution digest dynamically if not provided
    if not capability_resolution_digest:
        full_res_path = os.path.join(REPO_ROOT, capability_resolution_path)
        if os.path.exists(full_res_path):
            try:
                with open(full_res_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                capability_resolution_digest = data.get("resolution_digest", "")
            except Exception:
                pass

    req = WaveguidePassAdmissionRequest(
        request_id=f"SOL-WAVEGUIDE-PASS-ADMISSION-REQUEST-{level}",
        rc_id=rc_id,
        candidate_level=candidate_level,
        requested_pass=requested_pass,
        requested_profile=requested_profile,
        requested_scope=requested_scope,
        capability_resolution_path=capability_resolution_path,
        capability_resolution_digest=capability_resolution_digest or "",
        strict_waveguide_required=strict_waveguide_required,
        lane_fabric_fallback_requested=lane_fabric_fallback_requested,
        hybrid_execution_requested=hybrid_execution_requested,
        production_mutation_requested=production_mutation_requested,
        software_validation_caveat_required=software_validation_caveat_required
    )
    req.request_digest = hash_waveguide_pass_admission_request(req)
    return req


def evaluate_waveguide_pass_admission(
    request: Any,
    capability_resolution: Optional[Dict[str, Any]] = None
) -> WaveguidePassAdmissionDecision:
    """
    Evaluates pass admission based on request constraints and capability policies.
    """
    if hasattr(request, "__dict__"):
        req_dict = asdict(request)
    else:
        req_dict = dict(request)

    rc_id = req_dict.get("rc_id")
    level = "RC1" if "RC1" in rc_id else "RC2"
    candidate_level = req_dict.get("candidate_level")
    requested_pass = req_dict.get("requested_pass")
    requested_profile = req_dict.get("requested_profile")

    reasons = ["PASS_ADMISSION_REQUEST_CANONICAL"]
    is_valid = True

    # 1. Load capability resolution
    resolution = None
    if capability_resolution:
        resolution = capability_resolution
    else:
        res_path = os.path.join(REPO_ROOT, req_dict.get("capability_resolution_path", ""))
        if os.path.exists(res_path):
            with open(res_path, "r", encoding="utf-8") as f:
                resolution = json.load(f)

    # Governed feature sets
    governed_passes = {
        "channel_kernel_recognition",
        "cost_model_evaluation",
        "deterministic_policy_selection"
    }
    governed_profiles = {
        "COST_MODEL_DEBUG",
        "AUTOTUNE_SAFE",
        "AUTOTUNE_LOWEST_CYCLES",
        "KERNEL_AUTOTUNE_SAFE"
    }

    if not resolution:
        is_valid = False
        reasons.append("PASS_ADMISSION_CAPABILITY_RESOLUTION_INVALID")
        capability_status = "capability_blocked"
        resolution_digest = ""
        allowed_passes = []
        disallowed_passes = list(governed_passes)
        allowed_profiles = []
        disallowed_profiles = list(governed_profiles)
        caveat = ""
    else:
        # Validate capability resolution
        res_ok, res_reasons = validate_waveguide_runtime_capability_resolution(resolution)
        resolution_digest = resolution.get("resolution_digest", "")

        # Check resolution digest
        req_res_digest = req_dict.get("capability_resolution_digest")
        if req_res_digest and req_res_digest != resolution_digest:
            is_valid = False

        if res_ok and is_valid:
            reasons.append("PASS_ADMISSION_CAPABILITY_RESOLUTION_VALID")
        else:
            is_valid = False
            reasons.append("PASS_ADMISSION_CAPABILITY_RESOLUTION_INVALID")

        capability_status = resolution.get("capability_status", "capability_blocked")
        if capability_status == "capability_resolved":
            reasons.append("PASS_ADMISSION_CAPABILITY_RESOLVED")
        else:
            is_valid = False
            reasons.append("PASS_ADMISSION_CAPABILITY_NOT_RESOLVED")

        # Verify RC Match
        res_rc_id = resolution.get("rc_id")
        if rc_id == res_rc_id:
            reasons.append("PASS_ADMISSION_RC_MATCH")
        else:
            is_valid = False
            reasons.append("PASS_ADMISSION_RC_MISMATCH")

        allowed_passes = resolution.get("allowed_passes", [])
        disallowed_passes = resolution.get("disallowed_passes", [])
        allowed_profiles = resolution.get("allowed_profiles", [])
        disallowed_profiles = resolution.get("disallowed_profiles", [])
        caveat = resolution.get("software_validation_caveat", "")

    # Safety constraint enforcement
    strict_waveguide = req_dict.get("strict_waveguide_required", True)
    if not strict_waveguide or (resolution and resolution.get("strict_waveguide_required") is False):
        is_valid = False
        reasons.append("PASS_ADMISSION_BLOCKED")
    else:
        reasons.append("PASS_ADMISSION_STRICT_WAVEGUIDE_REQUIRED")

    if req_dict.get("lane_fabric_fallback_requested", False):
        is_valid = False
        reasons.append("PASS_ADMISSION_LANEFABRIC_FALLBACK_FORBIDDEN")
    
    if req_dict.get("hybrid_execution_requested", False):
        is_valid = False
        reasons.append("PASS_ADMISSION_HYBRID_EXECUTION_FORBIDDEN")

    if req_dict.get("production_mutation_requested", False):
        is_valid = False
        reasons.append("PASS_ADMISSION_PRODUCTION_MUTATION_FORBIDDEN")

    # Caveat validation
    if req_dict.get("software_validation_caveat_required", True):
        if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
            reasons.append("PASS_ADMISSION_SOFTWARE_CAVEAT_INCLUDED")
        else:
            is_valid = False

    # Check allowed/disallowed passes and profiles
    pass_allowed = False
    if is_valid:
        if requested_pass in allowed_passes and requested_pass not in disallowed_passes:
            pass_allowed = True
            reasons.append("PASS_ADMISSION_PASS_ALLOWED")
        else:
            reasons.append("PASS_ADMISSION_PASS_BLOCKED")

    profile_allowed = True
    if is_valid and requested_profile:
        if requested_profile in allowed_profiles and requested_profile not in disallowed_profiles:
            profile_allowed = True
            reasons.append("PASS_ADMISSION_PROFILE_ALLOWED")
        else:
            profile_allowed = False
            reasons.append("PASS_ADMISSION_PROFILE_BLOCKED")

    # Add RC1/RC2 specific reason codes
    if level == "RC1":
        if requested_pass in governed_passes:
            reasons.append("PASS_ADMISSION_RC1_GOVERNED_PASS_FORBIDDEN")
            pass_allowed = False
        if requested_profile in governed_profiles:
            reasons.append("PASS_ADMISSION_RC1_GOVERNED_PROFILE_FORBIDDEN")
            profile_allowed = False
    else: # RC2
        if requested_pass in governed_passes and pass_allowed:
            reasons.append("PASS_ADMISSION_RC2_GOVERNED_PASS_ALLOWED")
        if requested_profile in governed_profiles and profile_allowed:
            reasons.append("PASS_ADMISSION_RC2_GOVERNED_PROFILE_ALLOWED")

    # Final decision state
    if is_valid and pass_allowed and profile_allowed:
        admission_status = "pass_admitted"
        reasons.append("PASS_ADMISSION_ADMITTED")
        notes = f"Pass {requested_pass} is admitted under candidate level {candidate_level}."
    else:
        admission_status = "pass_blocked"
        reasons.append("PASS_ADMISSION_BLOCKED")
        notes = f"Pass {requested_pass} (profile: {requested_profile}) is blocked due to policy violations."

    reasons = sorted(list(set(reasons)))

    decision = WaveguidePassAdmissionDecision(
        decision_id=f"SOL-WAVEGUIDE-PASS-ADMISSION-DECISION-{level}",
        request_id=req_dict.get("request_id"),
        rc_id=rc_id,
        candidate_level=candidate_level,
        requested_pass=requested_pass,
        requested_profile=requested_profile,
        requested_scope=req_dict.get("requested_scope"),
        capability_resolution_digest=resolution_digest,
        capability_status=capability_status,
        admission_status=admission_status,
        pass_allowed=pass_allowed,
        profile_allowed=profile_allowed,
        strict_waveguide_required=True,
        lane_fabric_fallback_allowed=False,
        hybrid_execution_allowed=False,
        production_mutation_allowed=False,
        reason_codes=reasons,
        notes=notes,
        software_validation_caveat=caveat,
        decision_digest=""
    )

    decision.decision_digest = hash_waveguide_pass_admission_decision(decision)
    return decision


def validate_waveguide_pass_admission_decision(decision: Any) -> Tuple[bool, List[str]]:
    """
    Verifies the integrity of the pass admission decision record and its digests.
    """
    if hasattr(decision, "__dict__"):
        d_dict = asdict(decision)
    else:
        d_dict = dict(decision)

    reasons = []
    is_valid = True

    # 1. Verify decision digest
    given_digest = d_dict.get("decision_digest", "")
    computed_digest = hash_waveguide_pass_admission_decision(d_dict)
    if given_digest == computed_digest:
        reasons.append("PASS_ADMISSION_DECISION_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("PASS_ADMISSION_DECISION_DIGEST_INVALID")

    # 2. Check safety policies
    if d_dict.get("admission_status") == "pass_admitted":
        reasons.append("PASS_ADMISSION_ADMITTED")

        if d_dict.get("strict_waveguide_required") is True:
            reasons.append("PASS_ADMISSION_STRICT_WAVEGUIDE_REQUIRED")
        if d_dict.get("lane_fabric_fallback_allowed") is False:
            reasons.append("PASS_ADMISSION_LANEFABRIC_FALLBACK_FORBIDDEN")
        if d_dict.get("hybrid_execution_allowed") is False:
            reasons.append("PASS_ADMISSION_HYBRID_EXECUTION_FORBIDDEN")
        if d_dict.get("production_mutation_allowed") is False:
            reasons.append("PASS_ADMISSION_PRODUCTION_MUTATION_FORBIDDEN")

        caveat = d_dict.get("software_validation_caveat", "")
        if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
            reasons.append("PASS_ADMISSION_SOFTWARE_CAVEAT_INCLUDED")

        rc_id = d_dict.get("rc_id")
        if "RC1" in rc_id:
            reasons.append("PASS_ADMISSION_CAPABILITY_RESOLUTION_VALID")
            reasons.append("PASS_ADMISSION_CAPABILITY_RESOLVED")
        elif "RC2" in rc_id:
            reasons.append("PASS_ADMISSION_CAPABILITY_RESOLUTION_VALID")
            reasons.append("PASS_ADMISSION_CAPABILITY_RESOLVED")
    else:
        is_valid = False
        reasons.append("PASS_ADMISSION_BLOCKED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_pass_admission_decision(decision: Any) -> str:
    """
    Generates deterministic plaintext summary of the admission decision.
    """
    if hasattr(decision, "__dict__"):
        d_dict = asdict(decision)
    else:
        d_dict = dict(decision)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE COMPILER PASS ADMISSION DECISION RECORD",
        "============================================================",
        f"Decision ID:       {d_dict.get('decision_id')}",
        f"Request ID:        {d_dict.get('request_id')}",
        f"Candidate ID:      {d_dict.get('rc_id')}",
        f"Candidate Level:   {d_dict.get('candidate_level')}",
        f"Requested Pass:    {d_dict.get('requested_pass')}",
        f"Requested Profile: {d_dict.get('requested_profile')}",
        f"Admission Status:  {d_dict.get('admission_status', '').upper()}",
        f"Decision Digest:   {d_dict.get('decision_digest')}",
        "------------------------------------------------------------",
        f"Pass Allowed:      {d_dict.get('pass_allowed')}",
        f"Profile Allowed:   {d_dict.get('profile_allowed')}",
        f"Strict Waveguide Required:      {d_dict.get('strict_waveguide_required')}",
        f"LaneFabric Fallback Allowed:    {d_dict.get('lane_fabric_fallback_allowed')}",
        f"Hybrid Execution Allowed:       {d_dict.get('hybrid_execution_allowed')}",
        f"Production Mutation Allowed:    {d_dict.get('production_mutation_allowed')}",
        "------------------------------------------------------------",
        f"Notes: {d_dict.get('notes')}",
        "============================================================"
    ]
    return "\n".join(lines)


def export_waveguide_pass_admission_decision(decision: Any, filepath: str) -> None:
    """
    Exports admission decision record to key-sorted JSON catalog.
    """
    if hasattr(decision, "__dict__"):
        d_dict = asdict(decision)
    else:
        d_dict = dict(decision)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(d_dict, f, indent=4, sort_keys=True)


def compare_waveguide_pass_admission_decisions(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two admission decisions and returns differences.
    """
    def to_dict(dec):
        if hasattr(dec, "__dict__"):
            return asdict(dec)
        return dict(dec)

    left_dict = to_dict(left)
    right_dict = to_dict(right)

    diffs = {}
    for key in set(left_dict.keys()) | set(right_dict.keys()):
        val_l = left_dict.get(key)
        val_r = right_dict.get(key)
        if val_l != val_r:
            diffs[key] = {
                "left": val_l,
                "right": val_r
            }
    return diffs


if __name__ == "__main__":
    # Self-generate standard admitted decisions for RC1 and RC2
    req1 = build_waveguide_pass_admission_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        requested_pass="pipeline_compaction",
        requested_profile="FULL_SAFE_OPTIMIZED"
    )
    req2 = build_waveguide_pass_admission_request(
        rc_id="SOL-WAVEGUIDE-RC2",
        requested_pass="cost_model_evaluation",
        requested_profile="COST_MODEL_DEBUG"
    )

    dec1 = evaluate_waveguide_pass_admission(req1)
    dec2 = evaluate_waveguide_pass_admission(req2)

    rc1_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC1.json")
    rc2_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC2.json")

    export_waveguide_pass_admission_decision(dec1, rc1_export_path)
    export_waveguide_pass_admission_decision(dec2, rc2_export_path)

    print(f"Exported RC1 admission decision: {rc1_export_path}")
    print(f"Exported RC2 admission decision: {rc2_export_path}")
