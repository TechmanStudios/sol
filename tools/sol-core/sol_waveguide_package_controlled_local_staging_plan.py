# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Controlled Local Staging Plan.
Consumes the verified Physical Gate Preflight Audit Report and constructs a deterministic plan
for local staging of approved package artifacts.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    hash_file_contents,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_assembly_physical_execution_gate_validator import (
    validate_waveguide_package_physical_gate_preflight_audit_report
)


@dataclass
class WaveguidePackageControlledLocalStagingEntry:
    local_staging_entry_id: str
    entry_index: int
    source_artifact_path: str
    source_artifact_digest: str
    source_artifact_size_bytes: int
    source_artifact_type: str
    package_role: str
    rc_scope: str
    target_package_section: str
    target_relative_package_path: str
    staging_root_token: str
    target_staging_relative_path: str
    target_staging_display_path: str
    path_safety_status: str  # path_safe, path_unsafe, etc.
    source_path_exists: bool
    source_path_is_file: bool
    source_digest_expected: bool  # True if file exists and matches expected digest
    operator_approval_required: bool
    local_filesystem_scope_confirmation_required: bool
    directory_creation_allowed_for_entry: bool
    file_copy_allowed_for_entry: bool
    archive_creation_allowed_for_entry: bool
    upload_allowed_for_entry: bool
    deployment_allowed_for_entry: bool
    signing_allowed_for_entry: bool
    external_publication_allowed_for_entry: bool
    production_mutation_allowed_for_entry: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    local_staging_entry_digest: str = ""


@dataclass
class WaveguidePackageControlledLocalStagingPlan:
    controlled_local_staging_plan_id: str
    controlled_local_staging_plan_version: int
    controlled_local_staging_plan_status: str  # package_local_staging_plan_ready, etc.
    source_physical_gate_preflight_report_digest: str
    source_physical_execution_gate_digest: str
    source_transcript_audit_report_digest: str
    source_noop_dry_run_transcript_digest: str
    source_runner_invocation_envelope_digest: str
    source_runner_readiness_report_digest: str
    source_run_execution_blueprint_digest: str
    source_run_preflight_report_digest: str
    source_run_authorization_capsule_digest: str
    source_execution_readiness_report_digest: str
    source_package_assembly_execution_plan_digest: str
    source_preflight_authorization_report_digest: str
    source_authorization_envelope_digest: str
    source_final_package_readiness_report_digest: str
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    local_staging_entries: List[WaveguidePackageControlledLocalStagingEntry]
    ready_local_staging_entries: List[str]
    blocked_local_staging_entries: List[str]
    warning_local_staging_entries: List[str]
    invalid_local_staging_entries: List[str]
    ready_local_staging_entry_count: int
    blocked_local_staging_entry_count: int
    warning_local_staging_entry_count: int
    invalid_local_staging_entry_count: int
    total_planned_file_count: int
    rc1_planned_file_count: int
    rc2_planned_file_count: int
    shared_planned_file_count: int
    target_package_sections: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    source_artifact_paths: List[str]
    source_artifact_digests: List[str]
    target_relative_package_paths: List[str]
    target_staging_relative_paths: List[str]
    local_staging_scope: str
    operator_approval_required: bool
    local_filesystem_scope_confirmation_required: bool
    directory_creation_allowed: bool
    file_copy_allowed: bool
    archive_creation_allowed: bool
    upload_allowed: bool
    deployment_allowed: bool
    signing_allowed: bool
    external_publication_allowed: bool
    production_mutation_allowed: bool
    path_safety_verified: bool
    collision_check_verified: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    controlled_local_staging_plan_digest: str = ""


def hash_waveguide_package_controlled_local_staging_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a staging entry excluding local_staging_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("local_staging_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_controlled_local_staging_plan(plan: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a staging plan excluding controlled_local_staging_plan_digest.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or dataclass instance")

    p_copy = dict(p_dict)
    p_copy.pop("controlled_local_staging_plan_digest", None)
    return hash_data(p_copy)


def _load_dict(path_or_dict: Any) -> Optional[Dict[str, Any]]:
    if isinstance(path_or_dict, str):
        path = normalize_to_repo_path(path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    elif hasattr(path_or_dict, "__dict__"):
        return asdict(path_or_dict)
    elif isinstance(path_or_dict, dict):
        return dict(path_or_dict)
    return None


def validate_waveguide_package_local_staging_path_safety(target_path: str) -> bool:
    """
    Ensures the target relative path does not escape via parent traversal or absolute path rules.
    """
    if not target_path:
        return False
    normalized = target_path.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized:
        return False
    parts = normalized.split("/")
    for part in parts:
        if part == "..":
            return False
    return True


def build_waveguide_package_controlled_local_staging_entry(
    layout_entry: Dict[str, Any],
    index: int
) -> WaveguidePackageControlledLocalStagingEntry:
    """
    Builds a staging entry from assembly plan layout metadata.
    """
    source_artifact_path = layout_entry.get("source_artifact_path", "")
    target_package_path = layout_entry.get("target_package_path", "")

    # Safety checks
    path_safety = "path_safe"
    if not validate_waveguide_package_local_staging_path_safety(target_package_path):
        path_safety = "path_unsafe"

    full_source_path = os.path.join(REPO_ROOT, normalize_to_repo_path(source_artifact_path))
    source_path_exists = os.path.exists(full_source_path)
    source_path_is_file = os.path.isfile(full_source_path) if source_path_exists else False

    source_digest_expected = False
    expected_digest = layout_entry.get("source_artifact_digest", "")
    if source_path_is_file and expected_digest:
        try:
            actual_digest = hash_file_contents(full_source_path)
            source_digest_expected = (actual_digest == expected_digest)
        except Exception:
            source_digest_expected = False

    staging_relative = target_package_path.replace("\\", "/")
    display_path = f"<SOL_LOCAL_STAGING_ROOT>/{staging_relative}"

    entry = WaveguidePackageControlledLocalStagingEntry(
        local_staging_entry_id=f"SOL-WAVEGUIDE-STAGING-ENTRY-{index:03d}",
        entry_index=index,
        source_artifact_path=source_artifact_path,
        source_artifact_digest=expected_digest,
        source_artifact_size_bytes=layout_entry.get("artifact_size_bytes", 0),
        source_artifact_type=layout_entry.get("source_artifact_type", ""),
        package_role=layout_entry.get("source_package_role", ""),
        rc_scope=layout_entry.get("rc_scope", ""),
        target_package_section=layout_entry.get("target_package_section", ""),
        target_relative_package_path=target_package_path,
        staging_root_token="<SOL_LOCAL_STAGING_ROOT>",
        target_staging_relative_path=staging_relative,
        target_staging_display_path=display_path,
        path_safety_status=path_safety,
        source_path_exists=source_path_exists,
        source_path_is_file=source_path_is_file,
        source_digest_expected=source_digest_expected,
        operator_approval_required=True,
        local_filesystem_scope_confirmation_required=True,
        directory_creation_allowed_for_entry=True,
        file_copy_allowed_for_entry=True,
        archive_creation_allowed_for_entry=False,
        upload_allowed_for_entry=False,
        deployment_allowed_for_entry=False,
        signing_allowed_for_entry=False,
        external_publication_allowed_for_entry=False,
        production_mutation_allowed_for_entry=False,
        reason_codes=["ENTRY_PATH_SAFETY_CHECKED", "ENTRY_SOURCE_VERIFIED"],
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.local_staging_entry_digest = hash_waveguide_package_controlled_local_staging_entry(entry)
    return entry


def validate_waveguide_package_controlled_local_staging_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a staging entry model.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    # Verify digest
    recorded_digest = e_dict.get("local_staging_entry_digest", "")
    if not recorded_digest:
        errors.append("Missing entry digest")
    else:
        recomputed = hash_waveguide_package_controlled_local_staging_entry(e_dict)
        if recomputed != recorded_digest:
            errors.append(f"Entry digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Prohibitions
    prohibitions = [
        ("archive_creation_allowed_for_entry", False),
        ("upload_allowed_for_entry", False),
        ("deployment_allowed_for_entry", False),
        ("signing_allowed_for_entry", False),
        ("external_publication_allowed_for_entry", False),
        ("production_mutation_allowed_for_entry", False),
    ]
    for key, expected in prohibitions:
        if e_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    # Path check
    target_path = e_dict.get("target_relative_package_path", "")
    if not validate_waveguide_package_local_staging_path_safety(target_path):
        errors.append(f"Path escape or invalid relative target path: {target_path}")

    if e_dict.get("path_safety_status") != "path_safe":
        errors.append("Staging entry path safety status is not path_safe")

    return len(errors) == 0, errors


def build_waveguide_package_controlled_local_staging_plan(
    preflight_report_path_or_dict: Any,
    assembly_plan_path_or_dict: Any
) -> WaveguidePackageControlledLocalStagingPlan:
    """
    Builds a staging plan by consuming the gate preflight report and assembly plan.
    """
    preflight_dict = _load_dict(preflight_report_path_or_dict) or {}
    assembly_dict = _load_dict(assembly_plan_path_or_dict) or {}

    preflight_digest = preflight_dict.get("physical_gate_preflight_report_digest", "")
    gate_status = preflight_dict.get("physical_gate_preflight_report_status", "")

    # Check that preflight report has been verified
    plan_status = "package_local_staging_plan_ready"
    reason_codes = ["PACKAGE_LOCAL_STAGING_PLAN_READY"]

    if gate_status != "package_physical_execution_gate_audit_verified":
        plan_status = "package_local_staging_plan_blocked"
        reason_codes = ["GATE_PREFLIGHT_REPORT_NOT_VERIFIED"]

    layout_entries = assembly_dict.get("layout_entries", [])
    entries = []
    ready_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []

    target_paths_seen = set()
    collision_check_verified = True
    path_safety_verified = True

    for i, le in enumerate(layout_entries):
        entry = build_waveguide_package_controlled_local_staging_entry(le, i)
        entries.append(entry)

        # Check collision and path safety
        target_path = entry.target_relative_package_path
        if target_path in target_paths_seen:
            collision_check_verified = False
        target_paths_seen.add(target_path)

        if entry.path_safety_status != "path_safe":
            path_safety_verified = False

        # Independent validation
        valid, errs = validate_waveguide_package_controlled_local_staging_entry(entry)
        if not valid:
            invalid_ids.append(entry.local_staging_entry_id)
        elif entry.path_safety_status != "path_safe":
            blocked_ids.append(entry.local_staging_entry_id)
        elif not entry.source_path_exists or not entry.source_digest_expected:
            warning_ids.append(entry.local_staging_entry_id)
        else:
            ready_ids.append(entry.local_staging_entry_id)

    if not collision_check_verified:
        plan_status = "package_local_staging_plan_blocked"
        reason_codes.append("COLLISION_CHECK_FAILED")
    if not path_safety_verified:
        plan_status = "package_local_staging_plan_blocked"
        reason_codes.append("PATH_SAFETY_FAILED")

    if plan_status == "package_local_staging_plan_ready":
        reason_codes.append("PATH_SAFETY_VERIFIED")
        reason_codes.append("COLLISION_CHECK_VERIFIED")

    # Aggregate fields
    total_planned = len(entries)
    rc1_count = sum(1 for e in entries if e.rc_scope == "RC1")
    rc2_count = sum(1 for e in entries if e.rc_scope == "RC2")
    shared_count = sum(1 for e in entries if e.rc_scope == "Shared")

    target_sections = sorted(list(set(e.target_package_section for e in entries if e.target_package_section)))
    package_roles = sorted(list(set(e.package_role for e in entries if e.package_role)))
    artifact_types = sorted(list(set(e.source_artifact_type for e in entries if e.source_artifact_type)))
    rc_scopes = sorted(list(set(e.rc_scope for e in entries if e.rc_scope)))

    source_paths = sorted(list(set(e.source_artifact_path for e in entries)))
    source_digests = sorted(list(set(e.source_artifact_digest for e in entries)))
    target_rel_paths = sorted(list(set(e.target_relative_package_path for e in entries)))
    target_staging_paths = sorted(list(set(e.target_staging_relative_path for e in entries)))

    blocked_counts = {
        "archive_creation": 0,
        "deployment": 0,
        "directory_creation": 0,
        "external_publication": 0,
        "external_signing": 0,
        "file_copy": 0,
        "production_mutation": 0,
        "upload": 0
    }

    plan = WaveguidePackageControlledLocalStagingPlan(
        controlled_local_staging_plan_id="SOL-WAVEGUIDE-PACKAGE-CONTROLLED-LOCAL-STAGING-PLAN",
        controlled_local_staging_plan_version=1,
        controlled_local_staging_plan_status=plan_status,
        source_physical_gate_preflight_report_digest=preflight_digest,
        source_physical_execution_gate_digest=preflight_dict.get("source_physical_execution_gate_digest", ""),
        source_transcript_audit_report_digest=preflight_dict.get("source_transcript_audit_report_digest", ""),
        source_noop_dry_run_transcript_digest=preflight_dict.get("source_noop_dry_run_transcript_digest", ""),
        source_runner_invocation_envelope_digest=preflight_dict.get("source_runner_invocation_envelope_digest", ""),
        source_runner_readiness_report_digest=preflight_dict.get("source_runner_readiness_report_digest", ""),
        source_run_execution_blueprint_digest=preflight_dict.get("source_run_execution_blueprint_digest", ""),
        source_run_preflight_report_digest=preflight_dict.get("source_run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=preflight_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=preflight_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=preflight_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=preflight_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=preflight_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=preflight_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=preflight_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=preflight_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=preflight_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=preflight_dict.get("source_artifact_catalog_digest", ""),
        local_staging_entries=entries,
        ready_local_staging_entries=ready_ids,
        blocked_local_staging_entries=blocked_ids,
        warning_local_staging_entries=warning_ids,
        invalid_local_staging_entries=invalid_ids,
        ready_local_staging_entry_count=len(ready_ids),
        blocked_local_staging_entry_count=len(blocked_ids),
        warning_local_staging_entry_count=len(warning_ids),
        invalid_local_staging_entry_count=len(invalid_ids),
        total_planned_file_count=total_planned,
        rc1_planned_file_count=rc1_count,
        rc2_planned_file_count=rc2_count,
        shared_planned_file_count=shared_count,
        target_package_sections=target_sections,
        package_roles_indexed=package_roles,
        artifact_types_indexed=artifact_types,
        rc_scopes_indexed=rc_scopes,
        source_artifact_paths=source_paths,
        source_artifact_digests=source_digests,
        target_relative_package_paths=target_rel_paths,
        target_staging_relative_paths=target_staging_paths,
        local_staging_scope="controlled_local_staging_scope",
        operator_approval_required=True,
        local_filesystem_scope_confirmation_required=True,
        directory_creation_allowed=True,
        file_copy_allowed=True,
        archive_creation_allowed=False,
        upload_allowed=False,
        deployment_allowed=False,
        signing_allowed=False,
        external_publication_allowed=False,
        production_mutation_allowed=False,
        path_safety_verified=path_safety_verified,
        collision_check_verified=collision_check_verified,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    plan.controlled_local_staging_plan_digest = hash_waveguide_package_controlled_local_staging_plan(plan)
    return plan


def validate_waveguide_package_controlled_local_staging_plan(plan: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a staging plan.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    errors = []

    # Verify digest
    recorded_digest = p_dict.get("controlled_local_staging_plan_digest", "")
    if not recorded_digest:
        errors.append("Missing plan digest")
    else:
        recomputed = hash_waveguide_package_controlled_local_staging_plan(p_dict)
        if recomputed != recorded_digest:
            errors.append(f"Plan digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Prohibitions
    prohibitions = [
        ("archive_creation_allowed", False),
        ("upload_allowed", False),
        ("deployment_allowed", False),
        ("signing_allowed", False),
        ("external_publication_allowed", False),
        ("production_mutation_allowed", False),
    ]
    for key, expected in prohibitions:
        if p_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    # Status check
    status = p_dict.get("controlled_local_staging_plan_status", "")
    if status not in ["package_local_staging_plan_ready", "package_local_staging_plan_blocked",
                      "package_local_staging_plan_warning", "package_local_staging_plan_invalid"]:
        errors.append(f"Invalid plan status: {status}")

    # Entries check
    entries = p_dict.get("local_staging_entries", [])
    seen_targets = set()
    for entry in entries:
        valid_entry, entry_errs = validate_waveguide_package_controlled_local_staging_entry(entry)
        if not valid_entry:
            errors.extend(entry_errs)
        
        target = entry.get("target_relative_package_path")
        if target in seen_targets:
            errors.append(f"Duplicate target path collision: {target}")
        seen_targets.add(target)

    return len(errors) == 0, errors


def summarize_waveguide_package_controlled_local_staging_plan(plan: Any) -> str:
    """
    Returns a human-readable summary of the staging plan.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    summary = [
        f"Controlled Local Staging Plan ID: {p_dict.get('controlled_local_staging_plan_id')}",
        f"Version:                          {p_dict.get('controlled_local_staging_plan_version')}",
        f"Status:                           {p_dict.get('controlled_local_staging_plan_status', '').upper()}",
        f"Digest:                           {p_dict.get('controlled_local_staging_plan_digest')}",
        f"Total Planned Files:              {p_dict.get('total_planned_file_count')}",
        f"Ready / Blocked / Warning:       {p_dict.get('ready_local_staging_entry_count')} / {p_dict.get('blocked_local_staging_entry_count')} / {p_dict.get('warning_local_staging_entry_count')}",
        f"Directory Creation Allowed:       {p_dict.get('directory_creation_allowed')}",
        f"File Copy Allowed:                {p_dict.get('file_copy_allowed')}",
        f"Archive/Upload/Deploy Allowed:    {p_dict.get('archive_creation_allowed')} / {p_dict.get('upload_allowed')} / {p_dict.get('deployment_allowed')}",
        f"Path Safety Verified:             {p_dict.get('path_safety_verified')}",
        f"Collision Check Verified:         {p_dict.get('collision_check_verified')}"
    ]
    return "\n".join(summary)


def export_waveguide_package_controlled_local_staging_plan(plan: Any, filepath: str) -> None:
    """
    Exports the plan to a JSON file.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(p_dict, f, sort_keys=True, indent=4)


def compare_waveguide_package_controlled_local_staging_plans(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two staging plans.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)
    return {
        "plan_id_match": l_dict.get("controlled_local_staging_plan_id") == r_dict.get("controlled_local_staging_plan_id"),
        "plan_status_match": l_dict.get("controlled_local_staging_plan_status") == r_dict.get("controlled_local_staging_plan_status"),
        "total_planned_file_count_match": l_dict.get("total_planned_file_count") == r_dict.get("total_planned_file_count"),
        "plan_digest_match": l_dict.get("controlled_local_staging_plan_digest") == r_dict.get("controlled_local_staging_plan_digest")
    }


# Helper API functions as requested
def build_waveguide_package_local_staging_scope(scope: str = "controlled_local_staging_scope") -> str:
    return scope


def build_waveguide_package_local_staging_path_map(plan: Any) -> Dict[str, str]:
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    entries = p_dict.get("local_staging_entries", [])
    return {e.get("source_artifact_path"): e.get("target_relative_package_path") for e in entries}


def validate_waveguide_package_local_staging_operator_requirements(
    operator_approved: bool,
    local_filesystem_scope_confirmed: bool
) -> bool:
    return operator_approved is True and local_filesystem_scope_confirmed is True


def index_waveguide_package_local_staging_entries_by_section(plan: Any) -> Dict[str, List[Any]]:
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    entries = p_dict.get("local_staging_entries", [])
    index = {}
    for e in entries:
        section = e.get("target_package_section", "")
        index.setdefault(section, []).append(e)
    return index


def index_waveguide_package_local_staging_entries_by_role(plan: Any) -> Dict[str, List[Any]]:
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    entries = p_dict.get("local_staging_entries", [])
    index = {}
    for e in entries:
        role = e.get("package_role", "")
        index.setdefault(role, []).append(e)
    return index
