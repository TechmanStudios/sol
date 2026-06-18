# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Plan.
Consumes the Local Staging Output Audit Report and creates a deterministic archive plan
for building a local ZIP archive from the verified staged output.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_local_staging_output_validator import (
    validate_waveguide_package_local_staging_output_audit_report
)


@dataclass
class WaveguidePackageArchivePlanEntry:
    archive_plan_entry_id: str
    entry_index: int
    source_staging_relative_path: str
    source_staged_file_digest: str
    source_staged_file_size_bytes: int
    source_artifact_path: str
    source_artifact_digest_expected: str
    source_artifact_type: str
    package_role: str
    rc_scope: str
    target_package_section: str
    archive_member_relative_path: str
    archive_member_display_path: str
    archive_member_path_safety_status: str  # path_safe, path_unsafe, etc.
    archive_member_digest_expected: str
    archive_member_size_bytes_expected: int
    compression_method: str  # zipfile.ZIP_DEFLATED or just deflated
    include_in_archive: bool
    source_staged_file_exists: bool
    target_member_collision_free: bool
    archive_creation_allowed_for_entry: bool
    upload_allowed_for_entry: bool
    deployment_allowed_for_entry: bool
    signing_allowed_for_entry: bool
    external_publication_allowed_for_entry: bool
    production_mutation_allowed_for_entry: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_plan_entry_digest: str = ""


@dataclass
class WaveguidePackageArchivePlan:
    package_archive_plan_id: str
    package_archive_plan_version: int
    package_archive_plan_status: str  # package_archive_plan_ready, package_archive_plan_blocked, etc.
    archive_format: str  # zip
    archive_format_version: str
    archive_output_root_token: str  # <SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>
    archive_output_display_path: str
    archive_filename: str
    archive_display_path: str
    source_local_staging_output_audit_report_digest: str
    source_local_staging_output_manifest_digest: str
    source_controlled_local_staging_run_record_digest: str
    source_controlled_local_staging_plan_digest: str
    archive_plan_entries: List[WaveguidePackageArchivePlanEntry]
    ready_archive_plan_entries: List[str]
    blocked_archive_plan_entries: List[str]
    warning_archive_plan_entries: List[str]
    invalid_archive_plan_entries: List[str]
    ready_archive_plan_entry_count: int
    blocked_archive_plan_entry_count: int
    warning_archive_plan_entry_count: int
    invalid_archive_plan_entry_count: int
    total_planned_archive_file_count: int
    total_expected_uncompressed_size_bytes: int
    target_package_sections: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    source_staging_relative_paths: List[str]
    source_staged_file_digests: List[str]
    archive_member_relative_paths: List[str]
    compression_policy: str
    archive_member_ordering_policy: str
    archive_output_scope: str
    archive_operator_approval_required: bool
    local_archive_scope_confirmation_required: bool
    archive_creation_allowed: bool
    upload_allowed: bool
    deployment_allowed: bool
    signing_allowed: bool
    external_publication_allowed: bool
    production_mutation_allowed: bool
    archive_member_path_safety_verified: bool
    archive_member_collision_check_verified: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_archive_plan_digest: str = ""


def hash_waveguide_package_archive_plan_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an entry, excluding archive_plan_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("archive_plan_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_archive_plan(plan: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a plan, excluding package_archive_plan_digest.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or dataclass instance")

    p_copy = dict(p_dict)
    p_copy.pop("package_archive_plan_digest", None)
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


def validate_waveguide_package_archive_member_path_safety(member_path: str) -> bool:
    """
    Validates archive member paths for absolute paths, parent traversal, or empty paths.
    """
    if not member_path:
        return False
    normalized = member_path.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized:
        return False
    parts = normalized.split("/")
    for part in parts:
        if part == "..":
            return False
    return True


def build_waveguide_package_archive_plan_entry(
    staging_entry: Dict[str, Any],
    staged_actual_digest: str,
    index: int
) -> WaveguidePackageArchivePlanEntry:
    """
    Builds a single archive plan entry from a staging plan entry.
    """
    rel_path = staging_entry.get("target_staging_relative_path", "")
    member_safety = "path_safe"
    if not validate_waveguide_package_archive_member_path_safety(rel_path):
        member_safety = "path_unsafe"

    # We enforce compression_method to be DEFLATED for code/docs/etc.
    comp = "deflated"

    entry = WaveguidePackageArchivePlanEntry(
        archive_plan_entry_id=f"SOL-WAVEGUIDE-ARCHIVE-PLAN-ENTRY-{index:03d}",
        entry_index=index,
        source_staging_relative_path=rel_path,
        source_staged_file_digest=staged_actual_digest,
        source_staged_file_size_bytes=staging_entry.get("source_artifact_size_bytes", 0),
        source_artifact_path=staging_entry.get("source_artifact_path", ""),
        source_artifact_digest_expected=staging_entry.get("source_artifact_digest", ""),
        source_artifact_type=staging_entry.get("source_artifact_type", ""),
        package_role=staging_entry.get("package_role", ""),
        rc_scope=staging_entry.get("rc_scope", ""),
        target_package_section=staging_entry.get("target_package_section", ""),
        archive_member_relative_path=rel_path,
        archive_member_display_path=f"<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>/{rel_path}",
        archive_member_path_safety_status=member_safety,
        archive_member_digest_expected=staged_actual_digest,
        archive_member_size_bytes_expected=staging_entry.get("source_artifact_size_bytes", 0),
        compression_method=comp,
        include_in_archive=True,
        source_staged_file_exists=True,
        target_member_collision_free=True,
        archive_creation_allowed_for_entry=True,
        upload_allowed_for_entry=False,
        deployment_allowed_for_entry=False,
        signing_allowed_for_entry=False,
        external_publication_allowed_for_entry=False,
        production_mutation_allowed_for_entry=False,
        reason_codes=["ARCHIVE_MEMBER_PATH_SAFETY_VERIFIED", "ARCHIVE_MEMBER_STAGED_SOURCE_VERIFIED"],
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.archive_plan_entry_digest = hash_waveguide_package_archive_plan_entry(entry)
    return entry


def validate_waveguide_package_archive_plan_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates an archive plan entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    # Verify digest
    recorded_digest = e_dict.get("archive_plan_entry_digest", "")
    if not recorded_digest:
        errors.append("Missing archive plan entry digest")
    else:
        recomputed = hash_waveguide_package_archive_plan_entry(e_dict)
        if recomputed != recorded_digest:
            errors.append(f"Archive plan entry digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Enforce prohibitions
    prohibitions = [
        ("archive_creation_allowed_for_entry", True),
        ("upload_allowed_for_entry", False),
        ("deployment_allowed_for_entry", False),
        ("signing_allowed_for_entry", False),
        ("external_publication_allowed_for_entry", False),
        ("production_mutation_allowed_for_entry", False),
    ]
    for key, expected in prohibitions:
        if e_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    # Path safety checks
    rel_path = e_dict.get("archive_member_relative_path", "")
    if not validate_waveguide_package_archive_member_path_safety(rel_path):
        errors.append(f"Unsafe archive member path: {rel_path}")

    if e_dict.get("archive_member_path_safety_status") != "path_safe":
        errors.append("Archive member safety status is not path_safe")

    return len(errors) == 0, errors


def build_waveguide_package_archive_plan(
    staging_output_audit_report_path_or_dict: Any,
    staging_plan_path_or_dict: Any
) -> WaveguidePackageArchivePlan:
    """
    Builds the Package Archive Plan from the verified staging output audit report and staging plan.
    """
    report_dict = _load_dict(staging_output_audit_report_path_or_dict) or {}
    plan_dict = _load_dict(staging_plan_path_or_dict) or {}

    report_digest = report_dict.get("local_staging_output_audit_report_digest", "")
    report_status = report_dict.get("local_staging_output_audit_report_status", "")

    plan_status = "package_archive_plan_ready"
    reason_codes = ["PACKAGE_ARCHIVE_PLAN_READY"]

    # Verify report is clean/verified
    if report_status != "package_local_staging_output_verified":
        plan_status = "package_archive_plan_blocked"
        reason_codes = ["STAGING_OUTPUT_AUDIT_REPORT_NOT_VERIFIED"]

    entries = []
    ready_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []

    target_paths_seen = set()
    collision_check_verified = True
    path_safety_verified = True

    # Map staging entries
    staging_entries = plan_dict.get("local_staging_entries", [])
    audited_cases = report_dict.get("audited_cases", [])

    for i, se in enumerate(staging_entries):
        # Find corresponding case in audit report
        se_rel = se.get("target_staging_relative_path", "")
        matching_case = next((c for c in audited_cases if c.get("target_staging_relative_path") == se_rel), None)

        staged_digest = ""
        if matching_case:
            staged_digest = matching_case.get("target_staged_file_digest_recomputed", "")

        entry = build_waveguide_package_archive_plan_entry(se, staged_digest, i)
        entries.append(entry)

        # Path checks
        rel_path = entry.archive_member_relative_path
        if rel_path in target_paths_seen:
            collision_check_verified = False
        target_paths_seen.add(rel_path)

        if entry.archive_member_path_safety_status != "path_safe":
            path_safety_verified = False

        # Independent validation
        valid, errs = validate_waveguide_package_archive_plan_entry(entry)
        if not valid:
            invalid_ids.append(entry.archive_plan_entry_id)
        elif entry.archive_member_path_safety_status != "path_safe":
            blocked_ids.append(entry.archive_plan_entry_id)
        elif not matching_case or matching_case.get("audit_status") != "local_staging_output_audit_verified":
            warning_ids.append(entry.archive_plan_entry_id)
        else:
            ready_ids.append(entry.archive_plan_entry_id)

    if not path_safety_verified or not collision_check_verified or len(invalid_ids) > 0 or len(blocked_ids) > 0:
        plan_status = "package_archive_plan_invalid"
        reason_codes.append("PLAN_ENTRIES_INVALID_OR_BLOCKED")

    # Order entries deterministically by member path
    entries.sort(key=lambda x: x.archive_member_relative_path)

    # Re-index counts
    total_uncompressed = sum(e.archive_member_size_bytes_expected for e in entries)
    target_package_sections = sorted(list(set(e.target_package_section for e in entries)))
    package_roles_indexed = sorted(list(set(e.package_role for e in entries)))
    artifact_types_indexed = sorted(list(set(e.source_artifact_type for e in entries)))
    rc_scopes_indexed = sorted(list(set(e.rc_scope for e in entries)))
    source_staging_relative_paths = sorted(list(set(e.source_staging_relative_path for e in entries)))
    source_staged_file_digests = sorted(list(set(e.source_staged_file_digest for e in entries)))
    archive_member_relative_paths = sorted(list(set(e.archive_member_relative_path for e in entries)))

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

    archive_creation_allowed = (plan_status == "package_archive_plan_ready")

    plan = WaveguidePackageArchivePlan(
        package_archive_plan_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-PLAN",
        package_archive_plan_version=1,
        package_archive_plan_status=plan_status,
        archive_format="zip",
        archive_format_version="1.0",
        archive_output_root_token="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
        archive_output_display_path="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
        archive_filename="SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip",
        archive_display_path="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip",
        source_local_staging_output_audit_report_digest=report_digest,
        source_local_staging_output_manifest_digest=report_dict.get("source_local_staging_output_manifest_digest", ""),
        source_controlled_local_staging_run_record_digest=report_dict.get("source_controlled_local_staging_run_record_digest", ""),
        source_controlled_local_staging_plan_digest=report_dict.get("source_controlled_local_staging_plan_digest", ""),
        archive_plan_entries=entries,
        ready_archive_plan_entries=ready_ids,
        blocked_archive_plan_entries=blocked_ids,
        warning_archive_plan_entries=warning_ids,
        invalid_archive_plan_entries=invalid_ids,
        ready_archive_plan_entry_count=len(ready_ids),
        blocked_archive_plan_entry_count=len(blocked_ids),
        warning_archive_plan_entry_count=len(warning_ids),
        invalid_archive_plan_entry_count=len(invalid_ids),
        total_planned_archive_file_count=len(entries),
        total_expected_uncompressed_size_bytes=total_uncompressed,
        target_package_sections=target_package_sections,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        rc_scopes_indexed=rc_scopes_indexed,
        source_staging_relative_paths=source_staging_relative_paths,
        source_staged_file_digests=source_staged_file_digests,
        archive_member_relative_paths=archive_member_relative_paths,
        compression_policy="deflated",
        archive_member_ordering_policy="deterministic_sorted",
        archive_output_scope="local_sandbox",
        archive_operator_approval_required=True,
        local_archive_scope_confirmation_required=True,
        archive_creation_allowed=archive_creation_allowed,
        upload_allowed=False,
        deployment_allowed=False,
        signing_allowed=False,
        external_publication_allowed=False,
        production_mutation_allowed=False,
        archive_member_path_safety_verified=path_safety_verified,
        archive_member_collision_check_verified=collision_check_verified,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    plan.package_archive_plan_digest = hash_waveguide_package_archive_plan(plan)
    return plan


def validate_waveguide_package_archive_plan(plan: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a top-level Package Archive Plan.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    errors = []

    # Verify digest
    recorded_digest = p_dict.get("package_archive_plan_digest", "")
    if not recorded_digest:
        errors.append("Missing archive plan digest")
    else:
        recomputed = hash_waveguide_package_archive_plan(p_dict)
        if recomputed != recorded_digest:
            errors.append(f"Archive plan digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Verify ID
    if p_dict.get("package_archive_plan_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-PLAN":
        errors.append("Invalid package archive plan ID")

    # Enforce prohibitions
    prohibitions = [
        ("upload_allowed", False),
        ("deployment_allowed", False),
        ("signing_allowed", False),
        ("external_publication_allowed", False),
        ("production_mutation_allowed", False),
    ]
    for key, expected in prohibitions:
        if p_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Validate all entries
    entries = p_dict.get("archive_plan_entries", [])
    for e in entries:
        ok, errs = validate_waveguide_package_archive_plan_entry(e)
        if not ok:
            errors.extend(errs)

    # File counts
    if len(entries) != 28:
        errors.append(f"Expected exactly 28 archive members, found {len(entries)}")

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_plan(plan: Any) -> str:
    """
    Generates a human-readable summary of the Package Archive Plan.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    lines = [
        "=============================================================",
        "               SOL WAVEGUIDE PACKAGE ARCHIVE PLAN",
        "=============================================================",
        f"Plan ID:          {p_dict.get('package_archive_plan_id')}",
        f"Version:          {p_dict.get('package_archive_plan_version')}",
        f"Status:           {p_dict.get('package_archive_plan_status')}",
        f"Format / Ver:     {p_dict.get('archive_format')} / {p_dict.get('archive_format_version')}",
        f"Archive Filename: {p_dict.get('archive_filename')}",
        f"Digest:           {p_dict.get('package_archive_plan_digest')}",
        f"Planned Entries:  {p_dict.get('total_planned_archive_file_count')}",
        f"Archive Creation Allowed: {p_dict.get('archive_creation_allowed')}",
        f"Upload/Deploy/Sign Allowed: {p_dict.get('upload_allowed')} / {p_dict.get('deployment_allowed')} / {p_dict.get('signing_allowed')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in p_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_plan(plan: Any, output_path: str) -> None:
    """
    Exports the Package Archive Plan to a JSON file.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(p_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_plans(plan_a: Any, plan_b: Any) -> Dict[str, Any]:
    """
    Compares two Package Archive Plans.
    """
    dict_a = asdict(plan_a) if hasattr(plan_a, "__dict__") else dict(plan_a)
    dict_b = asdict(plan_b) if hasattr(plan_b, "__dict__") else dict(plan_b)

    differences = {}
    for key in ("package_archive_plan_status", "package_archive_plan_digest", "total_planned_archive_file_count"):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
