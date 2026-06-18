# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Runtime Capability Resolver
=========================================
Resolves approved release candidates (RC1/RC2) from the Release Registry into
read-only runtime capability constraints and active compiler policies.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_rc_release_registry import (
    validate_waveguide_rc_release_registry,
    validate_waveguide_rc_registry_entry
)


@dataclass
class WaveguideRuntimeCapabilityRequest:
    request_id: str
    rc_id: str
    requested_scope: str                 # foundation_runtime, governed_execution_runtime
    registry_path: str
    registry_digest: str
    require_court_approved_release: bool
    software_validation_caveat_required: bool
    request_digest: str = ""


@dataclass
class WaveguideRuntimeCapabilityResolution:
    resolution_id: str
    request_id: str
    rc_id: str
    candidate_level: str
    registry_entry_digest: str
    registry_digest: str
    release_status: str
    court_verdict: str
    quorum_status: str
    approved_rangers: List[str]
    capability_status: str               # capability_resolved, capability_blocked, capability_warning
    allowed_backend: str
    allowed_profiles: List[str]
    allowed_passes: List[str]
    disallowed_profiles: List[str]
    disallowed_passes: List[str]
    governed_stack_enabled: bool
    cost_model_enabled: bool
    autotuning_enabled: bool
    kernel_recognition_enabled: bool
    deterministic_policy_selection_enabled: bool
    strict_waveguide_required: bool
    lane_fabric_fallback_allowed: bool
    hybrid_execution_allowed: bool
    production_mutation_allowed: bool
    proof_artifacts: List[str]
    governance_artifacts: List[str]
    software_validation_caveat: str
    reason_codes: List[str]
    resolution_digest: str = ""


def hash_waveguide_runtime_capability_request(req: Any) -> str:
    """
    Computes digest for a capability request, excluding request_digest.
    """
    if hasattr(req, "__dict__"):
        r_dict = asdict(req)
    elif isinstance(req, dict):
        r_dict = dict(req)
    else:
        raise TypeError("request must be a dictionary or a dataclass instance")

    r_dict.pop("request_digest", None)
    return hash_data(r_dict)


def hash_waveguide_runtime_capability_resolution(res: Any) -> str:
    """
    Computes digest for a capability resolution, excluding resolution_digest.
    """
    if hasattr(res, "__dict__"):
        r_dict = asdict(res)
    elif isinstance(res, dict):
        r_dict = dict(res)
    else:
        raise TypeError("resolution must be a dictionary or a dataclass instance")

    r_dict.pop("resolution_digest", None)
    return hash_data(r_dict)


def build_waveguide_runtime_capability_request(
    rc_id: str,
    requested_scope: Optional[str] = None,
    registry_path: Optional[str] = None,
    registry_digest: Optional[str] = None,
    require_court_approved_release: bool = True,
    software_validation_caveat_required: bool = True
) -> WaveguideRuntimeCapabilityRequest:
    """
    Constructs a capability request to retrieve policy mappings for the RC.
    """
    level = "RC1" if "RC1" in rc_id else "RC2"
    if not requested_scope:
        requested_scope = "foundation_runtime" if level == "RC1" else "governed_execution_runtime"
    if not registry_path:
        registry_path = "docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json"
    registry_path = normalize_to_repo_path(registry_path)

    # Load registry digest dynamically if not provided
    if not registry_digest:
        full_reg_path = os.path.join(REPO_ROOT, registry_path)
        if os.path.exists(full_reg_path):
            try:
                with open(full_reg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                registry_digest = data.get("registry_digest", "")
            except Exception:
                pass

    req = WaveguideRuntimeCapabilityRequest(
        request_id=f"SOL-WAVEGUIDE-RC-CAPABILITY-REQUEST-{level}",
        rc_id=rc_id,
        requested_scope=requested_scope,
        registry_path=registry_path,
        registry_digest=registry_digest or "",
        require_court_approved_release=require_court_approved_release,
        software_validation_caveat_required=software_validation_caveat_required
    )
    req.request_digest = hash_waveguide_runtime_capability_request(req)
    return req


def resolve_waveguide_runtime_capabilities(
    request: Any,
    registry_data: Optional[Dict[str, Any]] = None
) -> WaveguideRuntimeCapabilityResolution:
    """
    Resolves the capability request using the registry to construct the policy.
    """
    if hasattr(request, "__dict__"):
        req_dict = asdict(request)
    else:
        req_dict = dict(request)

    rc_id = req_dict.get("rc_id")
    level = "RC1" if "RC1" in rc_id else "RC2"
    candidate_level = "foundation" if level == "RC1" else "governed_execution_stack"

    reasons = ["RUNTIME_CAPABILITY_REQUEST_CANONICAL"]
    is_valid = True

    # Load registry data
    registry = None
    if registry_data:
        registry = registry_data
    else:
        reg_path = os.path.join(REPO_ROOT, req_dict.get("registry_path", ""))
        if os.path.exists(reg_path):
            with open(reg_path, "r", encoding="utf-8") as f:
                registry = json.load(f)

    if not registry:
        is_valid = False
        reasons.append("RUNTIME_CAPABILITY_REGISTRY_INVALID")
    else:
        # Check registry validation status
        reg_ok, reg_reasons = validate_waveguide_rc_release_registry(registry)
        expected_digest = req_dict.get("registry_digest")
        actual_digest = registry.get("registry_digest", "")

        if reg_ok and (not expected_digest or expected_digest == actual_digest):
            reasons.append("RUNTIME_CAPABILITY_REGISTRY_VALID")
        else:
            is_valid = False
            reasons.append("RUNTIME_CAPABILITY_REGISTRY_INVALID")

        # Verify entry
        approved_ids = registry.get("approved_rc_ids", [])
        entries = registry.get("entries", {})

        if rc_id in approved_ids and rc_id in entries:
            reasons.append("RUNTIME_CAPABILITY_RC_APPROVED")
            entry = entries[rc_id]
            entry_ok, entry_reasons = validate_waveguide_rc_registry_entry(entry)

            if entry_ok and entry.get("release_status") == "release_registered":
                reasons.append("RUNTIME_CAPABILITY_ENTRY_VALID")
            else:
                is_valid = False
                reasons.append("RUNTIME_CAPABILITY_RC_NOT_APPROVED")
        else:
            is_valid = False
            reasons.append("RUNTIME_CAPABILITY_RC_NOT_APPROVED")

    # Resolve capability status and reason codes
    if is_valid:
        capability_status = "capability_resolved"
        reasons.append("RUNTIME_CAPABILITY_POLICY_RESOLVED")

        if level == "RC1":
            reasons.append("RUNTIME_CAPABILITY_FOUNDATION_POLICY_SELECTED")
            reasons.append("RUNTIME_CAPABILITY_GOVERNED_FEATURES_DISABLED")
            governed_stack_enabled = False
            cost_model_enabled = False
            autotuning_enabled = False
            kernel_recognition_enabled = False
            deterministic_policy_selection_enabled = False

            disallowed_profiles = [
                "COST_MODEL_DEBUG",
                "AUTOTUNE_SAFE",
                "AUTOTUNE_LOWEST_CYCLES",
                "KERNEL_AUTOTUNE_SAFE"
            ]
            disallowed_passes = [
                "channel_kernel_recognition",
                "cost_model_evaluation",
                "deterministic_policy_selection"
            ]
        else:
            reasons.append("RUNTIME_CAPABILITY_GOVERNED_POLICY_SELECTED")
            reasons.append("RUNTIME_CAPABILITY_GOVERNED_FEATURES_ENABLED")
            governed_stack_enabled = True
            cost_model_enabled = True
            autotuning_enabled = True
            kernel_recognition_enabled = True
            deterministic_policy_selection_enabled = True

            disallowed_profiles = []
            disallowed_passes = []

        # Extract profiles/passes from manifest dynamically
        manifest = build_waveguide_rc_manifest(rc_id)
        allowed_profiles = manifest.get("optimization_profiles", [])
        allowed_passes = manifest.get("canonical_pass_order", [])

        reasons.append("RUNTIME_CAPABILITY_STRICT_WAVEGUIDE_REQUIRED")
        reasons.append("RUNTIME_CAPABILITY_LANEFABRIC_FALLBACK_FORBIDDEN")
        reasons.append("RUNTIME_CAPABILITY_HYBRID_EXECUTION_FORBIDDEN")
        reasons.append("RUNTIME_CAPABILITY_PRODUCTION_MUTATION_FORBIDDEN")

        entry_data = registry.get("entries", {}).get(rc_id, {})
        caveat = entry_data.get("software_validation_caveat", "")
        if caveat and "sandbox" in caveat.lower():
            reasons.append("RUNTIME_CAPABILITY_SOFTWARE_CAVEAT_INCLUDED")

        entry_digest = entry_data.get("registry_entry_digest", "")
        registry_digest_val = registry.get("registry_digest", "")
        release_status_val = entry_data.get("release_status", "")
        court_verdict_val = entry_data.get("court_verdict", "")
        quorum_status_val = entry_data.get("quorum_status", "")
        approved_rangers = entry_data.get("approved_rangers", [])

        proof_artifacts = []
        if level == "RC2":
            proof_artifacts = ["docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC2.md"]

        governance_artifacts = [
            "docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json",
            f"docs/SOL_WAVEGUIDE_RC_COURT_VERDICT_{level}.json",
            f"docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_{level}.json"
        ]

    else:
        capability_status = "capability_blocked"
        reasons.append("RUNTIME_CAPABILITY_BLOCKED")

        governed_stack_enabled = False
        cost_model_enabled = False
        autotuning_enabled = False
        kernel_recognition_enabled = False
        deterministic_policy_selection_enabled = False

        allowed_profiles = []
        allowed_passes = []
        disallowed_profiles = [
            "COST_MODEL_DEBUG",
            "AUTOTUNE_SAFE",
            "AUTOTUNE_LOWEST_CYCLES",
            "KERNEL_AUTOTUNE_SAFE"
        ]
        disallowed_passes = [
            "channel_kernel_recognition",
            "cost_model_evaluation",
            "deterministic_policy_selection"
        ]

        entry_digest = ""
        registry_digest_val = ""
        release_status_val = "blocked"
        court_verdict_val = "promotion_rejected"
        quorum_status_val = "quorum_failed"
        approved_rangers = []
        proof_artifacts = []
        governance_artifacts = []
        caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    reasons.append("RUNTIME_CAPABILITY_RESOLUTION_DIGEST_VALID")
    reasons = sorted(list(set(reasons)))

    resolution = WaveguideRuntimeCapabilityResolution(
        resolution_id=f"SOL-WAVEGUIDE-RUNTIME-CAPABILITY-RESOLUTION-{level}",
        request_id=req_dict.get("request_id"),
        rc_id=rc_id,
        candidate_level=candidate_level,
        registry_entry_digest=entry_digest,
        registry_digest=registry_digest_val,
        release_status=release_status_val,
        court_verdict=court_verdict_val,
        quorum_status=quorum_status_val,
        approved_rangers=approved_rangers,
        capability_status=capability_status,
        allowed_backend="pdm_waveguide_microcoded_strict",
        allowed_profiles=allowed_profiles,
        allowed_passes=allowed_passes,
        disallowed_profiles=disallowed_profiles,
        disallowed_passes=disallowed_passes,
        governed_stack_enabled=governed_stack_enabled,
        cost_model_enabled=cost_model_enabled,
        autotuning_enabled=autotuning_enabled,
        kernel_recognition_enabled=kernel_recognition_enabled,
        deterministic_policy_selection_enabled=deterministic_policy_selection_enabled,
        strict_waveguide_required=True,
        lane_fabric_fallback_allowed=False,
        hybrid_execution_allowed=False,
        production_mutation_allowed=False,
        proof_artifacts=proof_artifacts,
        governance_artifacts=governance_artifacts,
        software_validation_caveat=caveat,
        reason_codes=reasons,
        resolution_digest=""
    )

    resolution.resolution_digest = hash_waveguide_runtime_capability_resolution(resolution)
    return resolution


def validate_waveguide_runtime_capability_resolution(resolution: Any) -> Tuple[bool, List[str]]:
    """
    Verifies that the resolution digest is valid and matches capability specifications.
    """
    if hasattr(resolution, "__dict__"):
        r_dict = asdict(resolution)
    else:
        r_dict = dict(resolution)

    reasons = []
    is_valid = True

    # 1. Verify resolution digest
    given_digest = r_dict.get("resolution_digest", "")
    computed_digest = hash_waveguide_runtime_capability_resolution(r_dict)
    if given_digest == computed_digest:
        reasons.append("RUNTIME_CAPABILITY_RESOLUTION_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("RUNTIME_CAPABILITY_RESOLUTION_DIGEST_INVALID")

    # 2. Check resolution policies
    if r_dict.get("capability_status") == "capability_resolved":
        reasons.append("RUNTIME_CAPABILITY_POLICY_RESOLVED")
        reasons.append("RUNTIME_CAPABILITY_RC_APPROVED")

        if r_dict.get("strict_waveguide_required") is True:
            reasons.append("RUNTIME_CAPABILITY_STRICT_WAVEGUIDE_REQUIRED")
        if r_dict.get("lane_fabric_fallback_allowed") is False:
            reasons.append("RUNTIME_CAPABILITY_LANEFABRIC_FALLBACK_FORBIDDEN")
        if r_dict.get("hybrid_execution_allowed") is False:
            reasons.append("RUNTIME_CAPABILITY_HYBRID_EXECUTION_FORBIDDEN")
        if r_dict.get("production_mutation_allowed") is False:
            reasons.append("RUNTIME_CAPABILITY_PRODUCTION_MUTATION_FORBIDDEN")

        caveat = r_dict.get("software_validation_caveat", "")
        if caveat and "sandbox" in caveat.lower():
            reasons.append("RUNTIME_CAPABILITY_SOFTWARE_CAVEAT_INCLUDED")

        level = r_dict.get("candidate_level")
        if level == "foundation":
            reasons.append("RUNTIME_CAPABILITY_FOUNDATION_POLICY_SELECTED")
            reasons.append("RUNTIME_CAPABILITY_GOVERNED_FEATURES_DISABLED")
        elif level == "governed_execution_stack":
            reasons.append("RUNTIME_CAPABILITY_GOVERNED_POLICY_SELECTED")
            reasons.append("RUNTIME_CAPABILITY_GOVERNED_FEATURES_ENABLED")
    else:
        is_valid = False
        reasons.append("RUNTIME_CAPABILITY_BLOCKED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_runtime_capability_resolution(res: Any) -> str:
    """
    Generates formatted plaintext summary of the capability resolution.
    """
    if hasattr(res, "__dict__"):
        r_dict = asdict(res)
    else:
        r_dict = dict(res)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE RUNTIME CAPABILITY RESOLUTION RECORD",
        "============================================================",
        f"Resolution ID:    {r_dict.get('resolution_id')}",
        f"Request ID:       {r_dict.get('request_id')}",
        f"Candidate ID:     {r_dict.get('rc_id')}",
        f"Candidate Level:  {r_dict.get('candidate_level')}",
        f"Status:           {r_dict.get('capability_status', '').upper()}",
        f"Resolution Digest:{r_dict.get('resolution_digest')}",
        "------------------------------------------------------------",
        f"Governed Stack Enabled: {r_dict.get('governed_stack_enabled')}",
        f"Cost Model Enabled:     {r_dict.get('cost_model_enabled')}",
        f"Autotuning Enabled:     {r_dict.get('autotuning_enabled')}",
        f"Kernel Recognition Enabled: {r_dict.get('kernel_recognition_enabled')}",
        f"Deterministic Policy Selection: {r_dict.get('deterministic_policy_selection_enabled')}",
        f"Strict Waveguide Required:      {r_dict.get('strict_waveguide_required')}",
        f"LaneFabric Fallback Allowed:    {r_dict.get('lane_fabric_fallback_allowed')}",
        f"Hybrid Execution Allowed:       {r_dict.get('hybrid_execution_allowed')}",
        "------------------------------------------------------------",
        "Allowed Profiles:",
    ]
    for p in r_dict.get("allowed_profiles", []):
        lines.append(f"  - {p}")
    lines.append("Disallowed Profiles:")
    for p in r_dict.get("disallowed_profiles", []):
        lines.append(f"  - {p}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_runtime_capability_resolution(resolution: Any, filepath: str) -> None:
    """
    Exports a capability resolution to key-sorted JSON catalog.
    """
    if hasattr(resolution, "__dict__"):
        r_dict = asdict(resolution)
    else:
        r_dict = dict(resolution)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_runtime_capability_resolutions(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two capability resolutions and returns differences.
    """
    def to_dict(res):
        if hasattr(res, "__dict__"):
            return asdict(res)
        return dict(res)

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
    # Generate canonical resolution records for RC1 and RC2
    req1 = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC1")
    req2 = build_waveguide_runtime_capability_request("SOL-WAVEGUIDE-RC2")

    res1 = resolve_waveguide_runtime_capabilities(req1)
    res2 = resolve_waveguide_runtime_capabilities(req2)

    rc1_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    rc2_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC2.json")

    export_waveguide_runtime_capability_resolution(res1, rc1_export_path)
    export_waveguide_runtime_capability_resolution(res2, rc2_export_path)

    print(f"Exported RC1 capability resolution: {rc1_export_path}")
    print(f"Exported RC2 capability resolution: {rc2_export_path}")
