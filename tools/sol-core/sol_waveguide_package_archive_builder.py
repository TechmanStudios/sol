# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Builder.
Consumes the Package Archive Plan and deterministically builds a local ZIP archive
containing exactly the approved staged files.
"""

import os
import json
import zipfile
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
from sol_waveguide_package_archive_plan import (
    validate_waveguide_package_archive_plan,
    validate_waveguide_package_archive_member_path_safety
)


@dataclass
class WaveguidePackageArchiveMemberBuildRecord:
    archive_member_build_record_id: str
    member_index: int
    member_build_status: str  # archive_member_build_completed, archive_member_build_blocked, etc.
    source_staging_relative_path: str
    source_staged_file_digest_expected: str
    source_staged_file_digest_actual: str
    source_staged_file_digest_match: bool
    source_staged_file_size_bytes: int
    archive_member_relative_path: str
    archive_member_path_safety_verified: bool
    archive_member_written: bool
    archive_member_digest_expected: str
    archive_member_size_bytes_expected: int
    compression_method: str
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_member_build_record_digest: str = ""


@dataclass
class WaveguidePackageArchiveBuildRecord:
    package_archive_build_record_id: str
    package_archive_build_record_version: int
    package_archive_build_status: str  # package_archive_build_completed, package_archive_build_blocked, etc.
    source_package_archive_plan_digest: str
    archive_format: str  # zip
    archive_output_root_token: str  # <SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>
    archive_output_display_path: str
    archive_filename: str
    archive_display_path: str
    archive_file_digest: str
    archive_file_size_bytes: int
    operator_approved: bool
    local_archive_scope_confirmed: bool
    clean_existing_archive_output: bool
    allow_overwrite: bool
    archive_member_records: List[WaveguidePackageArchiveMemberBuildRecord]
    completed_archive_member_records: List[str]
    blocked_archive_member_records: List[str]
    warning_archive_member_records: List[str]
    invalid_archive_member_records: List[str]
    completed_archive_member_count: int
    blocked_archive_member_count: int
    warning_archive_member_count: int
    invalid_archive_member_count: int
    total_planned_archive_file_count: int
    total_archived_file_count: int
    total_uncompressed_size_bytes: int
    target_package_sections: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    source_staging_relative_paths: List[str]
    source_staged_file_digests: List[str]
    archive_member_relative_paths: List[str]
    archive_member_digests: List[str]
    created_archive_count: int
    archive_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_archive_build_record_digest: str = ""


def hash_waveguide_package_archive_member_build_record(record: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a member build record, excluding archive_member_build_record_digest.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    elif isinstance(record, dict):
        r_dict = dict(record)
    else:
        raise TypeError("record must be a dictionary or dataclass instance")

    r_copy = dict(r_dict)
    r_copy.pop("archive_member_build_record_digest", None)
    return hash_data(r_copy)


def hash_waveguide_package_archive_build_record(build_record: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a build record, excluding package_archive_build_record_digest.
    """
    if hasattr(build_record, "__dict__"):
        br_dict = asdict(build_record)
    elif isinstance(build_record, dict):
        br_dict = dict(build_record)
    else:
        raise TypeError("build_record must be a dictionary or dataclass instance")

    br_copy = dict(br_dict)
    br_copy.pop("package_archive_build_record_digest", None)
    return hash_data(br_copy)


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


def resolve_waveguide_package_archive_output_root(output_root: str) -> str:
    """
    Resolves, normalizes, and validates the archive output root directory path.
    Raises ValueError if output root is deemed unsafe.
    """
    if not output_root:
        raise ValueError("Archive output root path is empty or missing")

    abs_root = os.path.abspath(output_root)
    normalized = abs_root.replace("\\", "/")

    abs_repo = os.path.abspath(REPO_ROOT)
    if abs_root == abs_repo:
        raise ValueError("Archive output root cannot be the repository root directory")

    abs_home = os.path.abspath(os.path.expanduser("~"))
    if abs_root == abs_home:
        raise ValueError("Archive output root cannot be the user home directory")

    parent = os.path.dirname(abs_root)
    if parent == abs_root:
        raise ValueError("Archive output root cannot be a filesystem drive/partition root directory")

    return normalized


def validate_waveguide_package_archive_output_path(
    output_root: str,
    filename: str
) -> bool:
    """
    Ensures archive path does not escape the archive output root directory.
    """
    try:
        norm_root = resolve_waveguide_package_archive_output_root(output_root)
        abs_target = os.path.abspath(os.path.join(norm_root, filename))
        common = os.path.commonpath([os.path.abspath(norm_root), abs_target])
        if os.path.abspath(common) != os.path.abspath(norm_root):
            return False
        return True
    except Exception:
        return False


def validate_waveguide_package_archive_build_request(
    archive_plan: Any,
    archive_output_root: str,
    operator_approved: bool,
    local_archive_scope_confirmed: bool
) -> Tuple[bool, List[str]]:
    """
    Validates archive build request pre-conditions.
    """
    errors = []
    if not operator_approved:
        errors.append("Operator approval is required")
    if not local_archive_scope_confirmed:
        errors.append("Local archive scope confirmation is required")

    try:
        resolve_waveguide_package_archive_output_root(archive_output_root)
    except ValueError as e:
        errors.append(str(e))

    valid_plan, plan_errs = validate_waveguide_package_archive_plan(archive_plan)
    if not valid_plan:
        errors.extend(plan_errs)

    p_dict = asdict(archive_plan) if hasattr(archive_plan, "__dict__") else dict(archive_plan)
    if p_dict.get("package_archive_plan_status") != "package_archive_plan_ready":
        errors.append("Archive plan status is not package_archive_plan_ready")

    return len(errors) == 0, errors


def build_waveguide_package_archive_build_request(
    archive_plan: Any,
    archive_output_root: str,
    operator_approved: bool = False,
    local_archive_scope_confirmed: bool = False,
    clean_existing_archive_output: bool = False,
    allow_overwrite: bool = False
) -> Dict[str, Any]:
    return {
        "archive_plan": archive_plan,
        "archive_output_root": archive_output_root,
        "operator_approved": operator_approved,
        "local_archive_scope_confirmed": local_archive_scope_confirmed,
        "clean_existing_archive_output": clean_existing_archive_output,
        "allow_overwrite": allow_overwrite
    }


def compute_waveguide_package_archive_digest(filepath: str) -> str:
    """
    Computes binary SHA256 hex digest of a file on disk.
    """
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def execute_waveguide_package_archive_build(
    archive_plan: Any,
    archive_output_root: str,
    operator_approved: bool = False,
    local_archive_scope_confirmed: bool = False,
    clean_existing_archive_output: bool = False,
    allow_overwrite: bool = False,
    staging_root_override: Optional[str] = None
) -> WaveguidePackageArchiveBuildRecord:
    """
    Executes a deterministic ZIP archive build if approvals are confirmed and path limits are met.
    """
    p_dict = asdict(archive_plan) if hasattr(archive_plan, "__dict__") else dict(archive_plan)
    plan_digest = p_dict.get("package_archive_plan_digest", "")

    valid, errs = validate_waveguide_package_archive_build_request(
        archive_plan, archive_output_root, operator_approved, local_archive_scope_confirmed
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
        blocked_counts["archive_creation"] = 1
        record = WaveguidePackageArchiveBuildRecord(
            package_archive_build_record_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-BUILD-RECORD",
            package_archive_build_record_version=1,
            package_archive_build_status="package_archive_build_blocked",
            source_package_archive_plan_digest=plan_digest,
            archive_format="zip",
            archive_output_root_token="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
            archive_output_display_path="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
            archive_filename=p_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
            archive_display_path=p_dict.get("archive_display_path", "<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
            archive_file_digest="",
            archive_file_size_bytes=0,
            operator_approved=operator_approved,
            local_archive_scope_confirmed=local_archive_scope_confirmed,
            clean_existing_archive_output=clean_existing_archive_output,
            allow_overwrite=allow_overwrite,
            archive_member_records=[],
            completed_archive_member_records=[],
            blocked_archive_member_records=[],
            warning_archive_member_records=[],
            invalid_archive_member_records=[],
            completed_archive_member_count=0,
            blocked_archive_member_count=0,
            warning_archive_member_count=0,
            invalid_archive_member_count=0,
            total_planned_archive_file_count=p_dict.get("total_planned_archive_file_count", 28),
            total_archived_file_count=0,
            total_uncompressed_size_bytes=0,
            target_package_sections=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            rc_scopes_indexed=[],
            source_staging_relative_paths=[],
            source_staged_file_digests=[],
            archive_member_relative_paths=[],
            archive_member_digests=[],
            created_archive_count=0,
            archive_creation_performed=False,
            upload_performed=False,
            deployment_performed=False,
            signing_performed=False,
            external_publication_performed=False,
            production_mutation_performed=False,
            blocked_operation_attempt_counts=blocked_counts,
            reason_codes=["BUILD_REQUEST_BLOCKED"] + errs,
            software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
        )
        record.package_archive_build_record_digest = hash_waveguide_package_archive_build_record(record)
        return record

    # Perform ZIP creation
    resolved_root = resolve_waveguide_package_archive_output_root(archive_output_root)
    archive_filename = p_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip")
    archive_filepath = os.path.join(resolved_root, archive_filename)

    # Overwrite checks
    if os.path.exists(archive_filepath):
        if clean_existing_archive_output or allow_overwrite:
            try:
                os.remove(archive_filepath)
            except Exception as e:
                blocked_counts["archive_creation"] = 1
                record = WaveguidePackageArchiveBuildRecord(
                    package_archive_build_record_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-BUILD-RECORD",
                    package_archive_build_record_version=1,
                    package_archive_build_status="package_archive_build_blocked",
                    source_package_archive_plan_digest=plan_digest,
                    archive_format="zip",
                    archive_output_root_token="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
                    archive_output_display_path=resolved_root,
                    archive_filename=archive_filename,
                    archive_display_path=f"{resolved_root}/{archive_filename}",
                    archive_file_digest="",
                    archive_file_size_bytes=0,
                    operator_approved=operator_approved,
                    local_archive_scope_confirmed=local_archive_scope_confirmed,
                    clean_existing_archive_output=clean_existing_archive_output,
                    allow_overwrite=allow_overwrite,
                    archive_member_records=[],
                    completed_archive_member_records=[],
                    blocked_archive_member_records=[],
                    warning_archive_member_records=[],
                    invalid_archive_member_records=[],
                    completed_archive_member_count=0,
                    blocked_archive_member_count=0,
                    warning_archive_member_count=0,
                    invalid_archive_member_count=0,
                    total_planned_archive_file_count=p_dict.get("total_planned_archive_file_count", 28),
                    total_archived_file_count=0,
                    total_uncompressed_size_bytes=0,
                    target_package_sections=[],
                    package_roles_indexed=[],
                    artifact_types_indexed=[],
                    rc_scopes_indexed=[],
                    source_staging_relative_paths=[],
                    source_staged_file_digests=[],
                    archive_member_relative_paths=[],
                    archive_member_digests=[],
                    created_archive_count=0,
                    archive_creation_performed=False,
                    upload_performed=False,
                    deployment_performed=False,
                    signing_performed=False,
                    external_publication_performed=False,
                    production_mutation_performed=False,
                    blocked_operation_attempt_counts=blocked_counts,
                    reason_codes=["ARCHIVE_OVERWRITE_FAILED", f"Error removing existing archive: {str(e)}"],
                    software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
                )
                record.package_archive_build_record_digest = hash_waveguide_package_archive_build_record(record)
                return record
        else:
            blocked_counts["archive_creation"] = 1
            record = WaveguidePackageArchiveBuildRecord(
                package_archive_build_record_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-BUILD-RECORD",
                package_archive_build_record_version=1,
                package_archive_build_status="package_archive_build_blocked",
                source_package_archive_plan_digest=plan_digest,
                archive_format="zip",
                archive_output_root_token="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
                archive_output_display_path=resolved_root,
                archive_filename=archive_filename,
                archive_display_path=f"{resolved_root}/{archive_filename}",
                archive_file_digest="",
                archive_file_size_bytes=0,
                operator_approved=operator_approved,
                local_archive_scope_confirmed=local_archive_scope_confirmed,
                clean_existing_archive_output=clean_existing_archive_output,
                allow_overwrite=allow_overwrite,
                archive_member_records=[],
                completed_archive_member_records=[],
                blocked_archive_member_records=[],
                warning_archive_member_records=[],
                invalid_archive_member_records=[],
                completed_archive_member_count=0,
                blocked_archive_member_count=0,
                warning_archive_member_count=0,
                invalid_archive_member_count=0,
                total_planned_archive_file_count=p_dict.get("total_planned_archive_file_count", 28),
                total_archived_file_count=0,
                total_uncompressed_size_bytes=0,
                target_package_sections=[],
                package_roles_indexed=[],
                artifact_types_indexed=[],
                rc_scopes_indexed=[],
                source_staging_relative_paths=[],
                source_staged_file_digests=[],
                archive_member_relative_paths=[],
                archive_member_digests=[],
                created_archive_count=0,
                archive_creation_performed=False,
                upload_performed=False,
                deployment_performed=False,
                signing_performed=False,
                external_publication_performed=False,
                production_mutation_performed=False,
                blocked_operation_attempt_counts=blocked_counts,
                reason_codes=["ARCHIVE_ALREADY_EXISTS"],
                software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
            )
            record.package_archive_build_record_digest = hash_waveguide_package_archive_build_record(record)
            return record

    os.makedirs(resolved_root, exist_ok=True)

    member_records = []
    completed_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []

    # Target staging root: where staged files are located.
    # In live system, staging root defaults to 'docs/staged_temp' unless overridden (e.g. by pytest tmp_path)
    stage_root = staging_root_override if staging_root_override else os.path.join(REPO_ROOT, "docs", "staged_temp")

    # Order plan entries deterministically
    plan_entries = p_dict.get("archive_plan_entries", [])
    plan_entries.sort(key=lambda x: x.get("archive_member_relative_path", ""))

    try:
        with zipfile.ZipFile(archive_filepath, "w") as zf:
            for i, pe in enumerate(plan_entries):
                rel_path = pe.get("archive_member_relative_path", "")
                staged_file_path = os.path.join(stage_root, rel_path)

                safety_ok = validate_waveguide_package_archive_member_path_safety(rel_path)

                member_written = False
                status_entry = "archive_member_build_completed"
                actual_digest = ""

                if not safety_ok:
                    status_entry = "archive_member_build_invalid"
                    invalid_ids.append(f"SOL-WAVEGUIDE-ARCHIVE-MEMBER-RECORD-{i:03d}")
                elif not os.path.exists(staged_file_path):
                    status_entry = "archive_member_build_blocked"
                    blocked_ids.append(f"SOL-WAVEGUIDE-ARCHIVE-MEMBER-RECORD-{i:03d}")
                else:
                    try:
                        # Compute actual digest of staged file
                        actual_digest = hash_file_contents(staged_file_path)

                        # Write deterministic ZIP member using ZipInfo
                        zinfo = zipfile.ZipInfo(filename=rel_path)
                        zinfo.date_time = (1980, 1, 1, 0, 0, 0)
                        zinfo.compress_type = zipfile.ZIP_DEFLATED

                        with open(staged_file_path, "rb") as sf:
                            zf.writestr(zinfo, sf.read())

                        member_written = True
                        completed_ids.append(f"SOL-WAVEGUIDE-ARCHIVE-MEMBER-RECORD-{i:03d}")
                    except Exception as e:
                        status_entry = "archive_member_build_invalid"
                        invalid_ids.append(f"SOL-WAVEGUIDE-ARCHIVE-MEMBER-RECORD-{i:03d}")

                expected_digest = pe.get("source_staged_file_digest", "")
                digest_match = (actual_digest == expected_digest) and (actual_digest != "")

                m_rec = WaveguidePackageArchiveMemberBuildRecord(
                    archive_member_build_record_id=f"SOL-WAVEGUIDE-ARCHIVE-MEMBER-RECORD-{i:03d}",
                    member_index=i,
                    member_build_status=status_entry,
                    source_staging_relative_path=rel_path,
                    source_staged_file_digest_expected=expected_digest,
                    source_staged_file_digest_actual=actual_digest,
                    source_staged_file_digest_match=digest_match,
                    source_staged_file_size_bytes=pe.get("source_staged_file_size_bytes", 0),
                    archive_member_relative_path=rel_path,
                    archive_member_path_safety_verified=safety_ok,
                    archive_member_written=member_written,
                    archive_member_digest_expected=expected_digest,
                    archive_member_size_bytes_expected=pe.get("archive_member_size_bytes_expected", 0),
                    compression_method="deflated",
                    upload_performed=False,
                    deployment_performed=False,
                    signing_performed=False,
                    external_publication_performed=False,
                    production_mutation_performed=False,
                    reason_codes=["MEMBER_WRITTEN"] if member_written else ["MEMBER_WRITE_FAILED"],
                    notes=[],
                    software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
                )
                m_rec.archive_member_build_record_digest = hash_waveguide_package_archive_member_build_record(m_rec)
                member_records.append(m_rec)

    except Exception as z_err:
        # Zip compilation failed completely
        blocked_counts["archive_creation"] = 1
        record = WaveguidePackageArchiveBuildRecord(
            package_archive_build_record_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-BUILD-RECORD",
            package_archive_build_record_version=1,
            package_archive_build_status="package_archive_build_invalid",
            source_package_archive_plan_digest=plan_digest,
            archive_format="zip",
            archive_output_root_token="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
            archive_output_display_path=resolved_root,
            archive_filename=archive_filename,
            archive_display_path=f"{resolved_root}/{archive_filename}",
            archive_file_digest="",
            archive_file_size_bytes=0,
            operator_approved=operator_approved,
            local_archive_scope_confirmed=local_archive_scope_confirmed,
            clean_existing_archive_output=clean_existing_archive_output,
            allow_overwrite=allow_overwrite,
            archive_member_records=[],
            completed_archive_member_records=[],
            blocked_archive_member_records=[],
            warning_archive_member_records=[],
            invalid_archive_member_records=[],
            completed_archive_member_count=0,
            blocked_archive_member_count=0,
            warning_archive_member_count=0,
            invalid_archive_member_count=0,
            total_planned_archive_file_count=p_dict.get("total_planned_archive_file_count", 28),
            total_archived_file_count=0,
            total_uncompressed_size_bytes=0,
            target_package_sections=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            rc_scopes_indexed=[],
            source_staging_relative_paths=[],
            source_staged_file_digests=[],
            archive_member_relative_paths=[],
            archive_member_digests=[],
            created_archive_count=0,
            archive_creation_performed=False,
            upload_performed=False,
            deployment_performed=False,
            signing_performed=False,
            external_publication_performed=False,
            production_mutation_performed=False,
            blocked_operation_attempt_counts=blocked_counts,
            reason_codes=["ZIP_CREATION_FAILED", str(z_err)],
            software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
        )
        record.package_archive_build_record_digest = hash_waveguide_package_archive_build_record(record)
        return record

    # Calculate actual archive file metadata
    archive_size = os.path.getsize(archive_filepath)
    archive_digest = compute_waveguide_package_archive_digest(archive_filepath)

    target_package_sections = p_dict.get("target_package_sections", [])
    package_roles_indexed = p_dict.get("package_roles_indexed", [])
    artifact_types_indexed = p_dict.get("artifact_types_indexed", [])
    rc_scopes_indexed = p_dict.get("rc_scopes_indexed", [])
    source_staging_relative_paths = p_dict.get("source_staging_relative_paths", [])
    source_staged_file_digests = p_dict.get("source_staged_file_digests", [])
    archive_member_relative_paths = p_dict.get("archive_member_relative_paths", [])
    archive_member_digests = [e.source_staged_file_digest_actual for e in member_records]

    build_status = "package_archive_build_completed"
    reason_codes = ["PACKAGE_ARCHIVE_BUILD_COMPLETED"]

    if len(completed_ids) < len(plan_entries):
        build_status = "package_archive_build_warning"
        reason_codes.append("PLAN_ENTRIES_MISSING_OR_BLOCKED")

    record = WaveguidePackageArchiveBuildRecord(
        package_archive_build_record_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-BUILD-RECORD",
        package_archive_build_record_version=1,
        package_archive_build_status=build_status,
        source_package_archive_plan_digest=plan_digest,
        archive_format="zip",
        archive_output_root_token="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
        archive_output_display_path=resolved_root,
        archive_filename=archive_filename,
        archive_display_path=f"{resolved_root}/{archive_filename}",
        archive_file_digest=archive_digest,
        archive_file_size_bytes=archive_size,
        operator_approved=operator_approved,
        local_archive_scope_confirmed=local_archive_scope_confirmed,
        clean_existing_archive_output=clean_existing_archive_output,
        allow_overwrite=allow_overwrite,
        archive_member_records=member_records,
        completed_archive_member_records=completed_ids,
        blocked_archive_member_records=blocked_ids,
        warning_archive_member_records=warning_ids,
        invalid_archive_member_records=invalid_ids,
        completed_archive_member_count=len(completed_ids),
        blocked_archive_member_count=len(blocked_ids),
        warning_archive_member_count=len(warning_ids),
        invalid_archive_member_count=len(invalid_ids),
        total_planned_archive_file_count=len(plan_entries),
        total_archived_file_count=len(completed_ids),
        total_uncompressed_size_bytes=sum(e.source_staged_file_size_bytes for e in member_records),
        target_package_sections=target_package_sections,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        rc_scopes_indexed=rc_scopes_indexed,
        source_staging_relative_paths=source_staging_relative_paths,
        source_staged_file_digests=source_staged_file_digests,
        archive_member_relative_paths=archive_member_relative_paths,
        archive_member_digests=archive_member_digests,
        created_archive_count=1,
        archive_creation_performed=True,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    record.package_archive_build_record_digest = hash_waveguide_package_archive_build_record(record)
    return record


def validate_waveguide_package_archive_build_record(build_record: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a WaveguidePackageArchiveBuildRecord.
    """
    br_dict = asdict(build_record) if hasattr(build_record, "__dict__") else dict(build_record)
    errors = []

    # Verify digest
    recorded_digest = br_dict.get("package_archive_build_record_digest", "")
    if not recorded_digest:
        errors.append("Missing build record digest")
    else:
        recomputed = hash_waveguide_package_archive_build_record(br_dict)
        if recomputed != recorded_digest:
            errors.append(f"Build record digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Enforce prohibitions
    prohibitions = [
        ("upload_performed", False),
        ("deployment_performed", False),
        ("signing_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if br_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Check member records
    members = br_dict.get("archive_member_records", [])
    for m in members:
        m_dig_rec = m.get("archive_member_build_record_digest", "")
        m_dig_comp = hash_waveguide_package_archive_member_build_record(m)
        if m_dig_rec != m_dig_comp:
            errors.append(f"Member build record digest mismatch: {m.get('archive_member_relative_path')}")

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_build_record(build_record: Any) -> str:
    """
    Generates a human-readable summary of the Package Archive Build Record.
    """
    br_dict = asdict(build_record) if hasattr(build_record, "__dict__") else dict(build_record)
    lines = [
        "=============================================================",
        "            SOL WAVEGUIDE PACKAGE ARCHIVE BUILD RECORD",
        "=============================================================",
        f"Record ID:        {br_dict.get('package_archive_build_record_id')}",
        f"Status:           {br_dict.get('package_archive_build_status')}",
        f"Format:           {br_dict.get('archive_format')}",
        f"Archive Filename: {br_dict.get('archive_filename')}",
        f"Archive Size:     {br_dict.get('archive_file_size_bytes')} bytes",
        f"Archive Digest:   {br_dict.get('archive_file_digest')}",
        f"Planned members:  {br_dict.get('total_planned_archive_file_count')}",
        f"Archived members: {br_dict.get('total_archived_file_count')}",
        f"Archive Creation Performed: {br_dict.get('archive_creation_performed')}",
        f"Upload/Deploy/Sign Performed: {br_dict.get('upload_performed')} / {br_dict.get('deployment_performed')} / {br_dict.get('signing_performed')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in br_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_build_record(build_record: Any, output_path: str) -> None:
    """
    Exports the Package Archive Build Record to a JSON file.
    """
    br_dict = asdict(build_record) if hasattr(build_record, "__dict__") else dict(build_record)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(br_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_build_records(record_a: Any, record_b: Any) -> Dict[str, Any]:
    """
    Compares two Package Archive Build Records.
    """
    dict_a = asdict(record_a) if hasattr(record_a, "__dict__") else dict(record_a)
    dict_b = asdict(record_b) if hasattr(record_b, "__dict__") else dict(record_b)

    differences = {}
    for key in ("package_archive_build_status", "archive_file_digest", "total_archived_file_count"):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
