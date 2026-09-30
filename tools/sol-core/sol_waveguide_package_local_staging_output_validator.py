# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Local Staging Output Validator.
Independently verifies the Local Staging Output Manifest, recomputes staged file digests,
enforces boundaries, and generates an audit report.
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
from sol_waveguide_package_local_staging_output_manifest import (
    validate_waveguide_package_local_staging_output_manifest,
    validate_waveguide_package_local_staging_output_entry,
    resolve_waveguide_package_local_staging_root,
    validate_waveguide_package_local_staging_target_path
)


@dataclass
class WaveguidePackageLocalStagingOutputAuditCase:
    local_staging_output_audit_case_id: str
    source_local_staging_output_manifest_digest: str
    source_local_staging_output_manifest_valid: bool
    source_controlled_local_staging_run_record_digest: str
    source_controlled_local_staging_plan_digest: str
    local_staging_output_entry_id: str
    local_staging_output_entry_digest_recorded: str
    local_staging_output_entry_digest_recomputed: str
    local_staging_output_entry_digest_match: bool
    audit_status: str  # local_staging_output_audit_verified, etc.
    source_artifact_path: str
    source_artifact_digest_expected: str
    target_staging_relative_path: str
    target_staged_file_exists: bool
    target_staged_file_digest_recorded: str
    target_staged_file_digest_recomputed: str
    target_staged_file_digest_match: bool
    target_digest_matches_source: bool
    target_size_matches_source: bool
    target_path_inside_staging_root: bool
    unexpected_file: bool
    missing_file: bool
    duplicate_target_path: bool
    physical_operation_boundary_valid: bool
    archive_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    local_staging_output_audit_case_digest: str = ""


@dataclass
class WaveguidePackageLocalStagingOutputAuditReport:
    local_staging_output_audit_report_id: str
    local_staging_output_audit_report_version: int
    local_staging_output_audit_report_status: str  # package_local_staging_output_verified, etc.
    source_local_staging_output_manifest_digest: str
    source_controlled_local_staging_run_record_digest: str
    source_controlled_local_staging_plan_digest: str
    audited_cases: List[WaveguidePackageLocalStagingOutputAuditCase]
    verified_local_staging_output_audit_cases: List[str]
    blocked_local_staging_output_audit_cases: List[str]
    warning_local_staging_output_audit_cases: List[str]
    invalid_local_staging_output_audit_cases: List[str]
    verified_local_staging_output_audit_count: int
    blocked_local_staging_output_audit_count: int
    warning_local_staging_output_audit_count: int
    invalid_local_staging_output_audit_count: int
    expected_file_count: int
    staged_file_count: int
    verified_file_count: int
    missing_file_count: int
    unexpected_file_count: int
    digest_mismatch_count: int
    invalid_file_count: int
    target_package_sections: List[str]
    source_artifact_paths: List[str]
    source_artifact_digests: List[str]
    target_staging_relative_paths: List[str]
    target_staged_file_digests: List[str]
    directory_creation_performed: bool
    file_copy_performed: bool
    archive_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    physical_operation_boundary_valid: bool
    reason_codes: List[str]
    software_validation_caveat: str
    local_staging_output_audit_report_digest: str = ""


def hash_waveguide_package_local_staging_output_audit_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an audit case excluding local_staging_output_audit_case_digest.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or dataclass instance")

    c_copy = dict(c_dict)
    c_copy.pop("local_staging_output_audit_case_digest", None)
    return hash_data(c_copy)


def hash_waveguide_package_local_staging_output_audit_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an audit report excluding local_staging_output_audit_report_digest.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or dataclass instance")

    r_copy = dict(r_dict)
    r_copy.pop("local_staging_output_audit_report_digest", None)
    return hash_data(r_copy)


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


def recompute_waveguide_package_local_staging_output_manifest_digest(manifest: Any) -> str:
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    m_copy = dict(m_dict)
    m_copy.pop("local_staging_output_manifest_digest", None)
    return hash_data(m_copy)


def recompute_waveguide_package_local_staging_output_entry_digest(entry: Any) -> str:
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    e_copy = dict(e_dict)
    e_copy.pop("local_staging_output_entry_digest", None)
    return hash_data(e_copy)


def build_waveguide_package_local_staging_output_audit_case(
    entry_dict: Dict[str, Any],
    manifest_digest: str,
    manifest_valid: bool,
    run_digest: str,
    plan_digest: str,
    staging_root: str,
    case_index: int
) -> WaveguidePackageLocalStagingOutputAuditCase:
    """
    Builds a single independent audit case from an output entry.
    """
    entry_id = entry_dict.get("local_staging_output_entry_id", "")
    entry_digest = entry_dict.get("local_staging_output_entry_digest", "")

    # Recompute entry digest
    recomp_entry_digest = recompute_waveguide_package_local_staging_output_entry_digest(entry_dict)
    entry_digest_match = (recomp_entry_digest == entry_digest)

    rel_path = entry_dict.get("target_staging_relative_path", "")
    expected_digest = entry_dict.get("source_artifact_digest_expected", "")

    exists = False
    recomputed_file_digest = ""
    file_digest_match = False
    digest_matches_source = False
    size_matches_source = False
    inside = validate_waveguide_package_local_staging_target_path(staging_root, rel_path)

    # Recompute file digest on disk
    norm_root = ""
    try:
        norm_root = resolve_waveguide_package_local_staging_root(staging_root)
    except ValueError:
        pass

    if inside and norm_root:
        full_tgt = os.path.join(norm_root, rel_path)
        if os.path.exists(full_tgt) and os.path.isfile(full_tgt):
            exists = True
            try:
                recomputed_file_digest = hash_file_contents(full_tgt)
                file_digest_match = (recomputed_file_digest == entry_dict.get("target_staged_file_digest", ""))
                is_self_referential = ("_CATALOG" in rel_path or "_PLAN" in rel_path or "_MANIFEST" in rel_path) if rel_path else False
                if is_self_referential:
                    actual_digest_recorded = entry_dict.get("target_staged_file_digest", "")
                    digest_matches_source = (recomputed_file_digest == actual_digest_recorded) if actual_digest_recorded else False
                else:
                    digest_matches_source = (recomputed_file_digest == expected_digest) if expected_digest else False
                size_matches_source = (os.path.getsize(full_tgt) == entry_dict.get("target_staged_file_size_bytes", 0))
            except Exception:
                pass

    # Boundary evaluation
    boundary_valid = inside
    prohibited_performed = (
        entry_dict.get("archive_creation_performed", False) or
        entry_dict.get("upload_performed", False) or
        entry_dict.get("deployment_performed", False) or
        entry_dict.get("signing_performed", False) or
        entry_dict.get("external_publication_performed", False) or
        entry_dict.get("production_mutation_performed", False)
    )
    if prohibited_performed:
        boundary_valid = False

    audit_status = "local_staging_output_audit_verified"
    reasons = ["AUDIT_CASE_VERIFIED"]

    if not manifest_valid:
        audit_status = "local_staging_output_audit_invalid"
        reasons = ["MANIFEST_INVALID"]
    elif not entry_digest_match:
        audit_status = "local_staging_output_audit_invalid"
        reasons = ["ENTRY_DIGEST_MISMATCH"]
    elif not exists:
        if entry_dict.get("missing_file"):
            audit_status = "local_staging_output_audit_verified"
            reasons = ["FILE_MISSING_CONFIRMED"]
        else:
            audit_status = "local_staging_output_audit_blocked"
            reasons = ["FILE_NOT_FOUND"]
    elif not file_digest_match:
        audit_status = "local_staging_output_audit_blocked"
        reasons = ["FILE_DIGEST_CHANGED_ON_DISK"]
    elif not digest_matches_source and not entry_dict.get("unexpected_file"):
        audit_status = "local_staging_output_audit_blocked"
        reasons = ["FILE_DIGEST_MISMATCH_WITH_SOURCE"]
    elif entry_dict.get("unexpected_file"):
        audit_status = "local_staging_output_audit_blocked"
        reasons = ["UNEXPECTED_FILE_DETECTED"]
    elif not boundary_valid:
        audit_status = "local_staging_output_audit_blocked"
        reasons = ["BOUNDARY_VIOLATION"]

    case = WaveguidePackageLocalStagingOutputAuditCase(
        local_staging_output_audit_case_id=f"SOL-WAVEGUIDE-AUDIT-CASE-{case_index:03d}",
        source_local_staging_output_manifest_digest=manifest_digest,
        source_local_staging_output_manifest_valid=manifest_valid,
        source_controlled_local_staging_run_record_digest=run_digest,
        source_controlled_local_staging_plan_digest=plan_digest,
        local_staging_output_entry_id=entry_id,
        local_staging_output_entry_digest_recorded=entry_digest,
        local_staging_output_entry_digest_recomputed=recomp_entry_digest,
        local_staging_output_entry_digest_match=entry_digest_match,
        audit_status=audit_status,
        source_artifact_path=entry_dict.get("source_artifact_path", ""),
        source_artifact_digest_expected=expected_digest,
        target_staging_relative_path=rel_path,
        target_staged_file_exists=exists,
        target_staged_file_digest_recorded=entry_dict.get("target_staged_file_digest", ""),
        target_staged_file_digest_recomputed=recomputed_file_digest,
        target_staged_file_digest_match=file_digest_match,
        target_digest_matches_source=digest_matches_source,
        target_size_matches_source=size_matches_source,
        target_path_inside_staging_root=inside,
        unexpected_file=entry_dict.get("unexpected_file", False),
        missing_file=entry_dict.get("missing_file", False),
        duplicate_target_path=entry_dict.get("duplicate_target_path", False),
        physical_operation_boundary_valid=boundary_valid,
        archive_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=reasons,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    case.local_staging_output_audit_case_digest = hash_waveguide_package_local_staging_output_audit_case(case)
    return case


def validate_waveguide_package_local_staging_output_manifest_independently(
    manifest_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    return validate_waveguide_package_local_staging_output_manifest(manifest_path_or_dict)


def build_waveguide_package_local_staging_output_audit_report(
    manifest_path_or_dict: Any,
    staging_root: str
) -> WaveguidePackageLocalStagingOutputAuditReport:
    """
    Independently reloads the manifest, recomputes case digests, checks boundaries,
    and produces the local staging output audit report.
    """
    m_dict = _load_dict(manifest_path_or_dict) or {}
    manifest_digest = m_dict.get("local_staging_output_manifest_digest", "")
    run_digest = m_dict.get("source_controlled_local_staging_run_record_digest", "")
    plan_digest = m_dict.get("source_controlled_local_staging_plan_digest", "")

    # Independent validation
    manifest_valid, m_errs = validate_waveguide_package_local_staging_output_manifest(m_dict)

    entries = m_dict.get("output_entries", [])
    cases = []
    verified_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []

    verified_file_cnt = 0
    missing_file_cnt = 0
    unexpected_file_cnt = 0
    mismatch_cnt = 0
    invalid_file_cnt = 0

    overall_boundary_valid = True

    for i, entry_dict in enumerate(entries):
        case = build_waveguide_package_local_staging_output_audit_case(
            entry_dict, manifest_digest, manifest_valid, run_digest, plan_digest, staging_root, i
        )
        cases.append(case)

        if not case.physical_operation_boundary_valid:
            overall_boundary_valid = False

        c_status = case.audit_status
        cid = case.local_staging_output_audit_case_id

        if c_status == "local_staging_output_audit_verified":
            verified_ids.append(cid)
            if not case.missing_file:
                verified_file_cnt += 1
            else:
                missing_file_cnt += 1
        elif c_status == "local_staging_output_audit_blocked":
            blocked_ids.append(cid)
            if case.unexpected_file:
                unexpected_file_cnt += 1
            elif not case.target_digest_matches_source:
                mismatch_cnt += 1
        elif c_status == "local_staging_output_audit_warning":
            warning_ids.append(cid)
        else:
            invalid_ids.append(cid)
            invalid_file_cnt += 1

    report_status = "package_local_staging_output_verified"
    reasons = ["AUDIT_REPORT_VERIFIED"]

    if not manifest_valid:
        report_status = "package_local_staging_output_invalid"
        reasons.append("MANIFEST_INVALID")
    elif blocked_ids:
        report_status = "package_local_staging_output_blocked"
        reasons.append("AUDIT_CONTAINS_BLOCKED_CASES")
    elif invalid_ids:
        report_status = "package_local_staging_output_invalid"
        reasons.append("AUDIT_CONTAINS_INVALID_CASES")

    if not overall_boundary_valid:
        report_status = "package_local_staging_output_blocked"
        reasons.append("BOUNDARY_VIOLATION_DETECTED")

    # Aggregate lists
    target_sections = sorted(list(set(m_dict.get("target_package_sections", []))))
    source_paths = sorted(list(set(case.source_artifact_path for case in cases if case.source_artifact_path)))
    source_digests = sorted(list(set(case.source_artifact_digest_expected for case in cases if case.source_artifact_digest_expected)))
    target_rel_paths = sorted(list(set(case.target_staging_relative_path for case in cases)))
    staged_digests = sorted(list(set(case.target_staged_file_digest_recomputed for case in cases if case.target_staged_file_digest_recomputed)))

    report = WaveguidePackageLocalStagingOutputAuditReport(
        local_staging_output_audit_report_id="SOL-WAVEGUIDE-LOCAL-STAGING-OUTPUT-AUDIT-REPORT",
        local_staging_output_audit_report_version=1,
        local_staging_output_audit_report_status=report_status,
        source_local_staging_output_manifest_digest=manifest_digest,
        source_controlled_local_staging_run_record_digest=run_digest,
        source_controlled_local_staging_plan_digest=plan_digest,
        audited_cases=cases,
        verified_local_staging_output_audit_cases=verified_ids,
        blocked_local_staging_output_audit_cases=blocked_ids,
        warning_local_staging_output_audit_cases=warning_ids,
        invalid_local_staging_output_audit_cases=invalid_ids,
        verified_local_staging_output_audit_count=len(verified_ids),
        blocked_local_staging_output_audit_count=len(blocked_ids),
        warning_local_staging_output_audit_count=len(warning_ids),
        invalid_local_staging_output_audit_count=len(invalid_ids),
        expected_file_count=m_dict.get("total_expected_file_count", 0),
        staged_file_count=m_dict.get("total_staged_file_count", 0),
        verified_file_count=verified_file_cnt,
        missing_file_count=missing_file_cnt,
        unexpected_file_count=unexpected_file_cnt,
        digest_mismatch_count=mismatch_cnt,
        invalid_file_count=invalid_file_cnt,
        target_package_sections=target_sections,
        source_artifact_paths=source_paths,
        source_artifact_digests=source_digests,
        target_staging_relative_paths=target_rel_paths,
        target_staged_file_digests=staged_digests,
        directory_creation_performed=m_dict.get("directory_creation_performed", False),
        file_copy_performed=m_dict.get("file_copy_performed", False),
        archive_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=m_dict.get("blocked_operation_attempt_counts", {}),
        physical_operation_boundary_valid=overall_boundary_valid,
        reason_codes=reasons,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    report.local_staging_output_audit_report_digest = hash_waveguide_package_local_staging_output_audit_report(report)
    return report


def validate_waveguide_package_local_staging_output_audit_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates the audit report structure.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    errors = []

    # Verify digest
    recorded_digest = r_dict.get("local_staging_output_audit_report_digest", "")
    if not recorded_digest:
        errors.append("Missing audit report digest")
    else:
        recomputed = hash_waveguide_package_local_staging_output_audit_report(r_dict)
        if recomputed != recorded_digest:
            errors.append(f"Audit report digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Prohibitions
    prohibitions = [
        ("archive_creation_performed", False),
        ("upload_performed", False),
        ("deployment_performed", False),
        ("signing_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if r_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    # Verify cases
    cases = r_dict.get("audited_cases", [])
    for c in cases:
        c_copy = dict(c)
        c_digest = c_copy.get("local_staging_output_audit_case_digest", "")
        if not c_digest:
            errors.append("Missing audit case digest")
        else:
            recomp = hash_waveguide_package_local_staging_output_audit_case(c_copy)
            if recomp != c_digest:
                errors.append(f"Audit case digest mismatch. Recorded: {c_digest}, Recomputed: {recomp}")

    return len(errors) == 0, errors


def summarize_waveguide_package_local_staging_output_audit_report(report: Any) -> str:
    """
    Returns a human-readable summary of the audit report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    summary = [
        f"Audit Report Status:             {r_dict.get('local_staging_output_audit_report_status', '').upper()}",
        f"Verified / Blocked / Warning:    {r_dict.get('verified_local_staging_output_audit_count')} / {r_dict.get('blocked_local_staging_output_audit_count')} / {r_dict.get('warning_local_staging_output_audit_count')}",
        f"Expected / Staged files count:   {r_dict.get('expected_file_count')} / {r_dict.get('staged_file_count')}",
        f"Verified file count:             {r_dict.get('verified_file_count')}",
        f"Missing / Unexpected count:      {r_dict.get('missing_file_count')} / {r_dict.get('unexpected_file_count')}",
        f"Digest mismatch / Invalid files: {r_dict.get('digest_mismatch_count')} / {r_dict.get('invalid_file_count')}",
        f"Boundary Valid:                  {r_dict.get('physical_operation_boundary_valid')}",
        f"Report Digest:                   {r_dict.get('local_staging_output_audit_report_digest')}"
    ]
    return "\n".join(summary)


def export_waveguide_package_local_staging_output_audit_report(report: Any, filepath: str) -> None:
    """
    Exports the audit report to a JSON file.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, sort_keys=True, indent=4)


def compare_waveguide_package_local_staging_output_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two audit reports.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)
    return {
        "report_status_match": l_dict.get("local_staging_output_audit_report_status") == r_dict.get("local_staging_output_audit_report_status"),
        "verified_count_match": l_dict.get("verified_local_staging_output_audit_count") == r_dict.get("verified_local_staging_output_audit_count"),
        "report_digest_match": l_dict.get("local_staging_output_audit_report_digest") == r_dict.get("local_staging_output_audit_report_digest")
    }


def validate_waveguide_package_local_staged_file_set(
    staging_root: str,
    expected_relative_paths: List[str]
) -> Tuple[bool, List[str]]:
    """
    Helper API: checks if files on disk strictly match the expected set.
    """
    errors = []
    staged_files = scan_waveguide_package_local_staging_directory(staging_root)
    staged_set = set(staged_files)
    expected_set = set(expected_relative_paths)

    missing = expected_set - staged_set
    unexpected = staged_set - expected_set

    for m in missing:
        errors.append(f"Missing expected staged file: {m}")
    for u in unexpected:
        errors.append(f"Unexpected file in staging directory: {u}")

    return len(errors) == 0, errors


def validate_waveguide_package_local_staged_file_digest_matches(
    staging_root: str,
    relative_path: str,
    expected_digest: str
) -> bool:
    """
    Helper API: recomputes staged file digest and compares it with expected digest.
    """
    try:
        norm_root = resolve_waveguide_package_local_staging_root(staging_root)
        full_tgt = os.path.join(norm_root, relative_path)
        if os.path.exists(full_tgt):
            actual = hash_file_contents(full_tgt)
            return actual == expected_digest
    except Exception:
        pass
    return False


def validate_waveguide_package_local_staged_operation_boundaries(
    archive_creation_performed: bool,
    upload_performed: bool,
    deployment_performed: bool,
    signing_performed: bool,
    external_publication_performed: bool,
    production_mutation_performed: bool
) -> bool:
    """
    Helper API: checks if boundary prohibitions were violated.
    """
    prohibited = (
        archive_creation_performed or
        upload_performed or
        deployment_performed or
        signing_performed or
        external_publication_performed or
        production_mutation_performed
    )
    return not prohibited


def index_waveguide_package_local_staging_output_audit_cases_by_status(
    report: Any
) -> Dict[str, List[Any]]:
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    cases = r_dict.get("audited_cases", [])
    index = {}
    for c in cases:
        status = c.get("audit_status", "")
        index.setdefault(status, []).append(c)
    return index
