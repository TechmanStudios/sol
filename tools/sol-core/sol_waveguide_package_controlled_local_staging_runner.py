# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Controlled Local Staging Runner.
Consumes the Controlled Local Staging Plan and performs controlled copying of the approved files
to a validated local filesystem directory.
"""

import os
import json
import shutil
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
from sol_waveguide_package_controlled_local_staging_plan import (
    validate_waveguide_package_controlled_local_staging_plan,
    validate_waveguide_package_local_staging_path_safety
)


@dataclass
class WaveguidePackageLocalStagingCopyRecord:
    local_staging_copy_record_id: str
    copy_index: int
    copy_status: str  # local_staging_copy_completed, local_staging_copy_blocked, etc.
    source_artifact_path: str
    source_artifact_digest_expected: str
    source_artifact_digest_actual: str
    source_artifact_digest_match: bool
    source_artifact_size_bytes: int
    target_staging_relative_path: str
    target_staging_display_path: str
    target_staged_file_digest: str
    target_staged_file_size_bytes: int
    target_digest_matches_source: bool
    directory_created_for_copy: bool
    file_copied: bool
    overwrite_performed: bool
    source_path_exists: bool
    target_path_inside_staging_root: bool
    path_safety_verified: bool
    archive_created: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    local_staging_copy_record_digest: str = ""


@dataclass
class WaveguidePackageControlledLocalStagingRunRecord:
    controlled_local_staging_run_record_id: str
    controlled_local_staging_run_record_version: int
    controlled_local_staging_run_status: str  # package_local_staging_run_completed, etc.
    source_controlled_local_staging_plan_digest: str
    local_staging_scope: str
    staging_root_token: str
    staging_root_display_path: str
    operator_approved: bool
    local_filesystem_scope_confirmed: bool
    clean_existing_staging_root: bool
    allow_overwrite: bool
    copy_records: List[WaveguidePackageLocalStagingCopyRecord]
    completed_copy_records: List[str]
    blocked_copy_records: List[str]
    warning_copy_records: List[str]
    invalid_copy_records: List[str]
    completed_copy_count: int
    blocked_copy_count: int
    warning_copy_count: int
    invalid_copy_count: int
    total_planned_file_count: int
    total_copied_file_count: int
    target_package_sections: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    source_artifact_paths: List[str]
    source_artifact_digests: List[str]
    target_staging_relative_paths: List[str]
    target_staged_file_digests: List[str]
    created_directory_count: int
    copied_file_count: int
    overwritten_file_count: int
    archive_created_count: int
    upload_count: int
    deployment_count: int
    signing_count: int
    external_publication_count: int
    production_mutation_count: int
    directory_creation_performed: bool
    file_copy_performed: bool
    archive_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    controlled_local_staging_run_record_digest: str = ""


def hash_waveguide_package_local_staging_copy_record(record: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a copy record excluding local_staging_copy_record_digest.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    elif isinstance(record, dict):
        r_dict = dict(record)
    else:
        raise TypeError("record must be a dictionary or dataclass instance")

    r_copy = dict(r_dict)
    r_copy.pop("local_staging_copy_record_digest", None)
    return hash_data(r_copy)


def hash_waveguide_package_controlled_local_staging_run_record(run_record: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a run record excluding controlled_local_staging_run_record_digest.
    """
    if hasattr(run_record, "__dict__"):
        rr_dict = asdict(run_record)
    elif isinstance(run_record, dict):
        rr_dict = dict(run_record)
    else:
        raise TypeError("run_record must be a dictionary or dataclass instance")

    rr_copy = dict(rr_dict)
    rr_copy.pop("controlled_local_staging_run_record_digest", None)
    return hash_data(rr_copy)


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


def resolve_waveguide_package_local_staging_root(staging_root: str) -> str:
    """
    Resolves, normalizes, and validates the local staging root directory path.
    Raises ValueError if staging root is deemed unsafe.
    """
    if not staging_root:
        raise ValueError("Staging root path is empty or missing")

    abs_root = os.path.abspath(staging_root)
    normalized = abs_root.replace("\\", "/")

    # Unsafe folder checks
    abs_repo = os.path.abspath(REPO_ROOT)
    if abs_root == abs_repo:
        raise ValueError("Staging root cannot be the repository root directory")

    abs_home = os.path.abspath(os.path.expanduser("~"))
    if abs_root == abs_home:
        raise ValueError("Staging root cannot be the user home directory")

    # Filesystem drive root or partition root check
    parent = os.path.dirname(abs_root)
    if parent == abs_root:
        raise ValueError("Staging root cannot be a filesystem drive/partition root directory")

    return normalized


def validate_waveguide_package_local_staging_run_request(
    staging_plan: Any,
    staging_root: str,
    operator_approved: bool,
    local_filesystem_scope_confirmed: bool
) -> Tuple[bool, List[str]]:
    """
    Validates staging run pre-conditions before executing copies.
    """
    errors = []
    if not operator_approved:
        errors.append("Operator approval is required")
    if not local_filesystem_scope_confirmed:
        errors.append("Local filesystem scope confirmation is required")

    try:
        resolve_waveguide_package_local_staging_root(staging_root)
    except ValueError as e:
        errors.append(str(e))

    valid_plan, plan_errs = validate_waveguide_package_controlled_local_staging_plan(staging_plan)
    if not valid_plan:
        errors.extend(plan_errs)

    p_dict = asdict(staging_plan) if hasattr(staging_plan, "__dict__") else dict(staging_plan)
    if p_dict.get("controlled_local_staging_plan_status") != "package_local_staging_plan_ready":
        errors.append("Staging plan status is not package_local_staging_plan_ready")

    return len(errors) == 0, errors


def validate_waveguide_package_local_staging_target_path(
    staging_root: str,
    target_relative_path: str
) -> bool:
    """
    Ensures target path does not escape the staging root directory.
    """
    if not validate_waveguide_package_local_staging_path_safety(target_relative_path):
        return False
    try:
        norm_root = resolve_waveguide_package_local_staging_root(staging_root)
        abs_target = os.path.abspath(os.path.join(norm_root, target_relative_path))
        # Use commonpath to enforce boundaries
        common = os.path.commonpath([os.path.abspath(norm_root), abs_target])
        if os.path.abspath(common) != os.path.abspath(norm_root):
            return False
        return True
    except Exception:
        return False


def build_waveguide_package_controlled_local_staging_run_request(
    staging_plan: Any,
    staging_root: str,
    operator_approved: bool = False,
    local_filesystem_scope_confirmed: bool = False,
    clean_existing_staging_root: bool = False,
    allow_overwrite: bool = False
) -> Dict[str, Any]:
    return {
        "staging_plan": staging_plan,
        "staging_root": staging_root,
        "operator_approved": operator_approved,
        "local_filesystem_scope_confirmed": local_filesystem_scope_confirmed,
        "clean_existing_staging_root": clean_existing_staging_root,
        "allow_overwrite": allow_overwrite
    }


def execute_waveguide_package_controlled_local_staging_run(
    staging_plan: Any,
    staging_root: str,
    operator_approved: bool = False,
    local_filesystem_scope_confirmed: bool = False,
    clean_existing_staging_root: bool = False,
    allow_overwrite: bool = False
) -> WaveguidePackageControlledLocalStagingRunRecord:
    """
    Executes the copies described in the staging plan if all conditions and gates are satisfied.
    """
    p_dict = asdict(staging_plan) if hasattr(staging_plan, "__dict__") else dict(staging_plan)
    plan_digest = p_dict.get("controlled_local_staging_plan_digest", "")

    # Pre-flight gate check
    valid, errs = validate_waveguide_package_local_staging_run_request(
        staging_plan, staging_root, operator_approved, local_filesystem_scope_confirmed
    )

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

    if not valid:
        # Construct a blocked run record and do not modify filesystem
        blocked_counts["file_copy"] = len(p_dict.get("local_staging_entries", []))
        run_record = WaveguidePackageControlledLocalStagingRunRecord(
            controlled_local_staging_run_record_id="SOL-WAVEGUIDE-STAGING-RUN-RECORD",
            controlled_local_staging_run_record_version=1,
            controlled_local_staging_run_status="package_local_staging_run_blocked",
            source_controlled_local_staging_plan_digest=plan_digest,
            local_staging_scope="controlled_local_staging_scope",
            staging_root_token="<SOL_LOCAL_STAGING_ROOT>",
            staging_root_display_path=str(staging_root),
            operator_approved=operator_approved,
            local_filesystem_scope_confirmed=local_filesystem_scope_confirmed,
            clean_existing_staging_root=clean_existing_staging_root,
            allow_overwrite=allow_overwrite,
            copy_records=[],
            completed_copy_records=[],
            blocked_copy_records=[],
            warning_copy_records=[],
            invalid_copy_records=[],
            completed_copy_count=0,
            blocked_copy_count=len(p_dict.get("local_staging_entries", [])),
            warning_copy_count=0,
            invalid_copy_count=0,
            total_planned_file_count=len(p_dict.get("local_staging_entries", [])),
            total_copied_file_count=0,
            target_package_sections=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            rc_scopes_indexed=[],
            source_artifact_paths=[],
            source_artifact_digests=[],
            target_staging_relative_paths=[],
            target_staged_file_digests=[],
            created_directory_count=0,
            copied_file_count=0,
            overwritten_file_count=0,
            archive_created_count=0,
            upload_count=0,
            deployment_count=0,
            signing_count=0,
            external_publication_count=0,
            production_mutation_count=0,
            directory_creation_performed=False,
            file_copy_performed=False,
            archive_creation_performed=False,
            upload_performed=False,
            deployment_performed=False,
            signing_performed=False,
            external_publication_performed=False,
            production_mutation_performed=False,
            blocked_operation_attempt_counts=blocked_counts,
            reason_codes=["RUN_BLOCKED_BY_SAFETY_GATES"] + errs,
            software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
        )
        run_record.controlled_local_staging_run_record_digest = hash_waveguide_package_controlled_local_staging_run_record(run_record)
        return run_record

    # Perform directory clean if requested
    norm_root = resolve_waveguide_package_local_staging_root(staging_root)
    if clean_existing_staging_root and os.path.exists(norm_root):
        # Double check to prevent removing repo root or user home
        if norm_root not in [os.path.abspath(REPO_ROOT).replace("\\", "/"), os.path.abspath(os.path.expanduser("~")).replace("\\", "/")]:
            shutil.rmtree(norm_root, ignore_errors=True)

    os.makedirs(norm_root, exist_ok=True)

    entries = p_dict.get("local_staging_entries", [])
    copy_records = []
    completed_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []

    created_dirs = set()
    overwritten_count = 0
    copied_count = 0

    for entry_dict in entries:
        src_rel = entry_dict.get("source_artifact_path", "")
        tgt_rel = entry_dict.get("target_relative_package_path", "")
        expected_digest = entry_dict.get("source_artifact_digest", "")

        src_full = os.path.join(REPO_ROOT, normalize_to_repo_path(src_rel))
        tgt_full = os.path.join(norm_root, tgt_rel)

        src_exists = os.path.exists(src_full)
        inside_root = validate_waveguide_package_local_staging_target_path(norm_root, tgt_rel)

        copy_status = "local_staging_copy_completed"
        file_copied = False
        overwrite_performed = False
        dir_created = False
        reason_codes = ["COPY_SUCCESS"]

        actual_src_digest = ""
        staged_digest = ""
        staged_size = 0

        if not src_exists:
            copy_status = "local_staging_copy_blocked"
            reason_codes = ["SOURCE_NOT_FOUND"]
            blocked_counts["file_copy"] += 1
        elif not inside_root:
            copy_status = "local_staging_copy_blocked"
            reason_codes = ["TARGET_PATH_ESCAPE"]
            blocked_counts["file_copy"] += 1
        else:
            try:
                actual_src_digest = hash_file_contents(src_full)
                if os.path.exists(tgt_full):
                    if not allow_overwrite:
                        copy_status = "local_staging_copy_blocked"
                        reason_codes = ["TARGET_EXISTS_OVERWRITE_DISABLED"]
                        blocked_counts["file_copy"] += 1
                    else:
                        overwrite_performed = True
                
                if copy_status == "local_staging_copy_completed":
                    # Create parent dir
                    parent_dir = os.path.dirname(tgt_full)
                    if not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)
                        dir_created = True
                        created_dirs.add(parent_dir)

                    # Binary copy
                    with open(src_full, "rb") as sf:
                        content = sf.read()
                    with open(tgt_full, "wb") as tf:
                        tf.write(content)

                    file_copied = True
                    copied_count += 1
                    if overwrite_performed:
                        overwritten_count += 1
                    
                    staged_digest = hash_file_contents(tgt_full)
                    staged_size = os.path.getsize(tgt_full)
            except Exception as e:
                copy_status = "local_staging_copy_invalid"
                reason_codes = [f"COPY_ERROR: {str(e)}"]

        is_self_referential = ("_CATALOG" in src_rel or "_PLAN" in src_rel or "_MANIFEST" in src_rel)
        if is_self_referential:
            digest_matches = (staged_digest == actual_src_digest) if staged_digest else False
        else:
            digest_matches = (staged_digest == expected_digest) if staged_digest else False

        record = WaveguidePackageLocalStagingCopyRecord(
            local_staging_copy_record_id=f"SOL-WAVEGUIDE-COPY-RECORD-{entry_dict.get('entry_index'):03d}",
            copy_index=entry_dict.get("entry_index"),
            copy_status=copy_status,
            source_artifact_path=src_rel,
            source_artifact_digest_expected=expected_digest,
            source_artifact_digest_actual=actual_src_digest,
            source_artifact_digest_match=(actual_src_digest == expected_digest),
            source_artifact_size_bytes=entry_dict.get("source_artifact_size_bytes", 0),
            target_staging_relative_path=entry_dict.get("target_staging_relative_path"),
            target_staging_display_path=entry_dict.get("target_staging_display_path"),
            target_staged_file_digest=staged_digest,
            target_staged_file_size_bytes=staged_size,
            target_digest_matches_source=digest_matches,
            directory_created_for_copy=dir_created,
            file_copied=file_copied,
            overwrite_performed=overwrite_performed,
            source_path_exists=src_exists,
            target_path_inside_staging_root=inside_root,
            path_safety_verified=inside_root,
            archive_created=False,
            upload_performed=False,
            deployment_performed=False,
            signing_performed=False,
            external_publication_performed=False,
            production_mutation_performed=False,
            reason_codes=reason_codes,
            notes=[],
            software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
        )
        record.local_staging_copy_record_digest = hash_waveguide_package_local_staging_copy_record(record)
        copy_records.append(record)

        rec_id = record.local_staging_copy_record_id
        if copy_status == "local_staging_copy_completed":
            completed_ids.append(rec_id)
        elif copy_status == "local_staging_copy_blocked":
            blocked_ids.append(rec_id)
        elif copy_status == "local_staging_copy_warning":
            warning_ids.append(rec_id)
        else:
            invalid_ids.append(rec_id)

    run_status = "package_local_staging_run_completed"
    if blocked_ids:
        run_status = "package_local_staging_run_blocked"
    elif invalid_ids:
        run_status = "package_local_staging_run_invalid"

    # Aggregates
    target_sections = sorted(list(set(e.get("target_package_section") for e in entries if e.get("target_package_section"))))
    package_roles = sorted(list(set(e.get("package_role") for e in entries if e.get("package_role"))))
    artifact_types = sorted(list(set(e.get("source_artifact_type") for e in entries if e.get("source_artifact_type"))))
    rc_scopes = sorted(list(set(e.get("rc_scope") for e in entries if e.get("rc_scope"))))

    source_paths = sorted(list(set(e.source_artifact_path for e in copy_records)))
    source_digests = sorted(list(set(e.source_artifact_digest_expected for e in copy_records)))
    target_rel_paths = sorted(list(set(e.target_staging_relative_path for e in copy_records)))
    staged_digests = sorted(list(set(e.target_staged_file_digest for e in copy_records if e.target_staged_file_digest)))

    run_record = WaveguidePackageControlledLocalStagingRunRecord(
        controlled_local_staging_run_record_id="SOL-WAVEGUIDE-STAGING-RUN-RECORD",
        controlled_local_staging_run_record_version=1,
        controlled_local_staging_run_status=run_status,
        source_controlled_local_staging_plan_digest=plan_digest,
        local_staging_scope="controlled_local_staging_scope",
        staging_root_token="<SOL_LOCAL_STAGING_ROOT>",
        staging_root_display_path=str(staging_root).replace("\\", "/"),
        operator_approved=operator_approved,
        local_filesystem_scope_confirmed=local_filesystem_scope_confirmed,
        clean_existing_staging_root=clean_existing_staging_root,
        allow_overwrite=allow_overwrite,
        copy_records=copy_records,
        completed_copy_records=completed_ids,
        blocked_copy_records=blocked_ids,
        warning_copy_records=warning_ids,
        invalid_copy_records=invalid_ids,
        completed_copy_count=len(completed_ids),
        blocked_copy_count=len(blocked_ids),
        warning_copy_count=len(warning_ids),
        invalid_copy_count=len(invalid_ids),
        total_planned_file_count=len(entries),
        total_copied_file_count=copied_count,
        target_package_sections=target_sections,
        package_roles_indexed=package_roles,
        artifact_types_indexed=artifact_types,
        rc_scopes_indexed=rc_scopes,
        source_artifact_paths=source_paths,
        source_artifact_digests=source_digests,
        target_staging_relative_paths=target_rel_paths,
        target_staged_file_digests=staged_digests,
        created_directory_count=len(created_dirs),
        copied_file_count=copied_count,
        overwritten_file_count=overwritten_count,
        archive_created_count=0,
        upload_count=0,
        deployment_count=0,
        signing_count=0,
        external_publication_count=0,
        production_mutation_count=0,
        directory_creation_performed=(len(created_dirs) > 0),
        file_copy_performed=(copied_count > 0),
        archive_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=["STAGING_RUN_COMPLETED"] if not blocked_ids else ["STAGING_RUN_BLOCKED"],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    run_record.controlled_local_staging_run_record_digest = hash_waveguide_package_controlled_local_staging_run_record(run_record)
    return run_record


def validate_waveguide_package_controlled_local_staging_run_record(run_record: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a staging run record structure.
    """
    rr_dict = asdict(run_record) if hasattr(run_record, "__dict__") else dict(run_record)
    errors = []

    # Verify digest
    recorded_digest = rr_dict.get("controlled_local_staging_run_record_digest", "")
    if not recorded_digest:
        errors.append("Missing run record digest")
    else:
        recomputed = hash_waveguide_package_controlled_local_staging_run_record(rr_dict)
        if recomputed != recorded_digest:
            errors.append(f"Run record digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Prohibitions
    prohibitions = [
        ("archive_creation_performed", False),
        ("upload_performed", False),
        ("deployment_performed", False),
        ("signing_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
        ("archive_created_count", 0),
        ("upload_count", 0),
        ("deployment_count", 0),
        ("signing_count", 0),
        ("external_publication_count", 0),
        ("production_mutation_count", 0),
    ]
    for key, expected in prohibitions:
        if rr_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    # Verify copy records
    copy_recs = rr_dict.get("copy_records", [])
    for cr in copy_recs:
        cr_copy = dict(cr)
        cr_digest = cr_copy.get("local_staging_copy_record_digest", "")
        if not cr_digest:
            errors.append("Missing copy record digest")
        else:
            recomp = hash_waveguide_package_local_staging_copy_record(cr_copy)
            if recomp != cr_digest:
                errors.append(f"Copy record digest mismatch. Recorded: {cr_digest}, Recomputed: {recomp}")

        # Boundaries
        if cr_copy.get("archive_created") or cr_copy.get("upload_performed") or cr_copy.get("deployment_performed") or cr_copy.get("signing_performed"):
            errors.append("Copy record violated boundaries")

    return len(errors) == 0, errors


def summarize_waveguide_package_controlled_local_staging_run_record(run_record: Any) -> str:
    """
    Returns a human-readable summary of the run record.
    """
    rr_dict = asdict(run_record) if hasattr(run_record, "__dict__") else dict(run_record)
    summary = [
        f"Staging Run Status:              {rr_dict.get('controlled_local_staging_run_status', '').upper()}",
        f"Staging Root Display:            {rr_dict.get('staging_root_display_path')}",
        f"Operator Approved:               {rr_dict.get('operator_approved')}",
        f"Filesystem Scope Confirmed:      {rr_dict.get('local_filesystem_scope_confirmed')}",
        f"Completed / Blocked copies:      {rr_dict.get('completed_copy_count')} / {rr_dict.get('blocked_copy_count')}",
        f"Created directories / copied:    {rr_dict.get('created_directory_count')} / {rr_dict.get('copied_file_count')}",
        f"Overwritten files:               {rr_dict.get('overwritten_file_count')}",
        f"Archive/Upload/Deploy performed: {rr_dict.get('archive_creation_performed')} / {rr_dict.get('upload_performed')} / {rr_dict.get('deployment_performed')}",
        f"Run Record Digest:               {rr_dict.get('controlled_local_staging_run_record_digest')}"
    ]
    return "\n".join(summary)


def export_waveguide_package_controlled_local_staging_run_record(run_record: Any, filepath: str) -> None:
    """
    Exports the run record to a JSON file.
    """
    rr_dict = asdict(run_record) if hasattr(run_record, "__dict__") else dict(run_record)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(rr_dict, f, sort_keys=True, indent=4)


def compare_waveguide_package_controlled_local_staging_run_records(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two staging run records.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)
    return {
        "run_status_match": l_dict.get("controlled_local_staging_run_status") == r_dict.get("controlled_local_staging_run_status"),
        "total_copied_file_count_match": l_dict.get("total_copied_file_count") == r_dict.get("total_copied_file_count"),
        "run_record_digest_match": l_dict.get("controlled_local_staging_run_record_digest") == r_dict.get("controlled_local_staging_run_record_digest")
    }


def index_waveguide_package_local_staging_copy_records_by_status(run_record: Any) -> Dict[str, List[Any]]:
    rr_dict = asdict(run_record) if hasattr(run_record, "__dict__") else dict(run_record)
    copy_recs = rr_dict.get("copy_records", [])
    index = {}
    for cr in copy_recs:
        status = cr.get("copy_status", "")
        index.setdefault(status, []).append(cr)
    return index
