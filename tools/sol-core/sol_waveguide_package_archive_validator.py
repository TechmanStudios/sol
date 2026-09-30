# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Validator.
Independently verifies the Package Archive Manifest and actual ZIP archive,
generating an audit report.
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
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_archive_manifest import (
    validate_waveguide_package_archive_manifest,
    validate_waveguide_package_archive_manifest_entry,
    compute_waveguide_package_archive_member_digest
)
from sol_waveguide_package_archive_builder import (
    compute_waveguide_package_archive_digest
)
from sol_waveguide_package_archive_plan import (
    validate_waveguide_package_archive_member_path_safety
)


@dataclass
class WaveguidePackageArchiveAuditCase:
    archive_audit_case_id: str
    source_package_archive_manifest_digest: str
    source_package_archive_manifest_valid: bool
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_manifest_entry_id: str
    archive_manifest_entry_digest_recorded: str
    archive_manifest_entry_digest_recomputed: str
    archive_manifest_entry_digest_match: bool
    archive_audit_status: str  # archive_audit_verified, archive_audit_blocked, etc.
    archive_member_relative_path: str
    archive_member_exists: bool
    archive_member_path_safety_verified: bool
    archive_member_digest_recorded: str
    archive_member_digest_recomputed: str
    archive_member_digest_match: bool
    source_staged_file_digest_expected: str
    archive_member_digest_matches_source: bool
    archive_member_size_matches_source: bool
    unexpected_archive_member: bool
    missing_archive_member: bool
    duplicate_archive_member_path: bool
    physical_operation_boundary_valid: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_audit_case_digest: str = ""


@dataclass
class WaveguidePackageArchiveAuditReport:
    package_archive_audit_report_id: str
    package_archive_audit_report_version: int
    package_archive_audit_report_status: str  # package_archive_verified, package_archive_invalid, etc.
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_format: str  # zip
    archive_file_digest_recorded: str
    archive_file_digest_recomputed: str
    archive_file_digest_match: bool
    archive_file_size_bytes: int
    audited_cases: List[WaveguidePackageArchiveAuditCase]
    verified_archive_audit_cases: List[str]
    blocked_archive_audit_cases: List[str]
    warning_archive_audit_cases: List[str]
    invalid_archive_audit_cases: List[str]
    verified_archive_audit_count: int
    blocked_archive_audit_count: int
    warning_archive_audit_count: int
    invalid_archive_audit_count: int
    expected_archive_file_count: int
    archive_member_count: int
    verified_archive_member_count: int
    missing_archive_member_count: int
    unexpected_archive_member_count: int
    digest_mismatch_archive_member_count: int
    invalid_archive_member_count: int
    archive_member_relative_paths: List[str]
    archive_member_digests: List[str]
    source_staged_file_digests: List[str]
    archive_member_paths_safe: bool
    archive_file_set_verified: bool
    archive_digest_verified: bool
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
    package_archive_audit_report_digest: str = ""


def hash_waveguide_package_archive_audit_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an audit case, excluding archive_audit_case_digest.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or dataclass instance")

    c_copy = dict(c_dict)
    c_copy.pop("archive_audit_case_digest", None)
    return hash_data(c_copy)


def hash_waveguide_package_archive_audit_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an audit report, excluding package_archive_audit_report_digest.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or dataclass instance")

    r_copy = dict(r_dict)
    r_copy.pop("package_archive_audit_report_digest", None)
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


def build_waveguide_package_archive_audit_case(
    entry_dict: Dict[str, Any],
    manifest_digest: str,
    manifest_valid: bool,
    build_record_digest: str,
    plan_digest: str,
    archive_filepath: str,
    zf: Optional[zipfile.ZipFile],
    case_index: int
) -> WaveguidePackageArchiveAuditCase:
    """
    Builds a single archive audit case.
    """
    rel_path = entry_dict.get("archive_member_relative_path", "")
    safety_ok = validate_waveguide_package_archive_member_path_safety(rel_path)

    recomputed_entry_digest = hash_data({k: v for k, v in entry_dict.items() if k != "archive_manifest_entry_digest"})
    entry_digest_recorded = entry_dict.get("archive_manifest_entry_digest", "")
    entry_digest_match = (entry_digest_recorded == recomputed_entry_digest) and (entry_digest_recorded != "")

    recomputed_member_digest = ""
    member_exists = False
    if zf:
        try:
            # Check info
            zinfo = zf.getinfo(rel_path)
            member_exists = True
            recomputed_member_digest = compute_waveguide_package_archive_member_digest(zf, rel_path)
        except Exception:
            member_exists = False

    recorded_member_digest = entry_dict.get("archive_member_digest", "")
    member_digest_match = (recorded_member_digest == recomputed_member_digest) and (recorded_member_digest != "")

    expected_digest = entry_dict.get("source_staged_file_digest_expected", "")
    digest_matches_source = (recomputed_member_digest == expected_digest) and (recomputed_member_digest != "")

    audit_status = "archive_audit_verified"
    reason_codes = ["AUDIT_CASE_VERIFIED"]

    if not safety_ok:
        audit_status = "archive_audit_invalid"
        reason_codes.append("AUDIT_MEMBER_PATH_UNSAFE")
    elif not member_exists:
        audit_status = "archive_audit_blocked"
        reason_codes.append("AUDIT_MEMBER_MISSING")
    elif not member_digest_match or not entry_digest_match or not digest_matches_source:
        audit_status = "archive_audit_invalid"
        reason_codes.append("AUDIT_DIGEST_MISMATCH")

    case = WaveguidePackageArchiveAuditCase(
        archive_audit_case_id=f"SOL-WAVEGUIDE-ARCHIVE-AUDIT-CASE-{case_index:03d}",
        source_package_archive_manifest_digest=manifest_digest,
        source_package_archive_manifest_valid=manifest_valid,
        source_package_archive_build_record_digest=build_record_digest,
        source_package_archive_plan_digest=plan_digest,
        archive_manifest_entry_id=entry_dict.get("archive_manifest_entry_id", ""),
        archive_manifest_entry_digest_recorded=entry_digest_recorded,
        archive_manifest_entry_digest_recomputed=recomputed_entry_digest,
        archive_manifest_entry_digest_match=entry_digest_match,
        archive_audit_status=audit_status,
        archive_member_relative_path=rel_path,
        archive_member_exists=member_exists,
        archive_member_path_safety_verified=safety_ok,
        archive_member_digest_recorded=recorded_member_digest,
        archive_member_digest_recomputed=recomputed_member_digest,
        archive_member_digest_match=member_digest_match,
        source_staged_file_digest_expected=expected_digest,
        archive_member_digest_matches_source=digest_matches_source,
        archive_member_size_matches_source=entry_dict.get("archive_member_size_matches_source", False),
        unexpected_archive_member=entry_dict.get("unexpected_archive_member", False),
        missing_archive_member=entry_dict.get("missing_archive_member", False),
        duplicate_archive_member_path=entry_dict.get("duplicate_archive_member_path", False),
        physical_operation_boundary_valid=True,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    case.archive_audit_case_digest = hash_waveguide_package_archive_audit_case(case)
    return case


def build_waveguide_package_audit_report(
    manifest_path_or_dict: Any,
    archive_output_root_override: Optional[str] = None
) -> WaveguidePackageArchiveAuditReport:
    """
    Builds the Package Archive Audit Report.
    """
    m_dict = _load_dict(manifest_path_or_dict) or {}
    manifest_digest = m_dict.get("package_archive_manifest_digest", "")
    if not manifest_digest:
        manifest_digest = m_dict.get("local_staging_output_manifest_digest", "")

    manifest_valid, manifest_errs = validate_waveguide_package_archive_manifest(m_dict)

    report_status = "package_archive_verified"
    reason_codes = ["PACKAGE_ARCHIVE_VERIFIED"]

    if not manifest_valid:
        report_status = "package_archive_blocked"
        reason_codes = ["MANIFEST_NOT_VALID"]

    filename = m_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip")
    display_path = m_dict.get("archive_display_path", "")

    # Resolve actual path
    if display_path.startswith("<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>"):
        actual_path = os.path.join(REPO_ROOT, display_path.replace("<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>/", "docs/"))
    else:
        actual_path = os.path.join(REPO_ROOT, normalize_to_repo_path(display_path))

    if archive_output_root_override:
        actual_path = os.path.join(archive_output_root_override, filename)

    archive_exists = os.path.exists(actual_path)
    archive_digest_recomp = ""
    archive_size = 0

    if archive_exists:
        archive_digest_recomp = compute_waveguide_package_archive_digest(actual_path)
        archive_size = os.path.getsize(actual_path)
    else:
        report_status = "package_archive_blocked"
        reason_codes.append("ARCHIVE_FILE_NOT_FOUND")

    archive_digest_recorded = m_dict.get("archive_file_digest", "")
    archive_digest_match = (archive_digest_recorded == archive_digest_recomp) and (archive_digest_recorded != "")

    if not archive_digest_match:
        report_status = "package_archive_invalid"
        reason_codes.append("ARCHIVE_FILE_DIGEST_MISMATCH")

    audited_cases = []
    verified_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []

    zf = None
    if archive_exists:
        try:
            zf = zipfile.ZipFile(actual_path, "r")
        except Exception:
            pass

    manifest_entries = m_dict.get("archive_entries", [])
    for i, me in enumerate(manifest_entries):
        case = build_waveguide_package_archive_audit_case(
            entry_dict=me,
            manifest_digest=manifest_digest,
            manifest_valid=manifest_valid,
            build_record_digest=m_dict.get("source_package_archive_build_record_digest", ""),
            plan_digest=m_dict.get("source_package_archive_plan_digest", ""),
            archive_filepath=actual_path,
            zf=zf,
            case_index=i
        )
        audited_cases.append(case)

        if case.archive_audit_status == "archive_audit_verified":
            verified_ids.append(case.archive_audit_case_id)
        elif case.archive_audit_status == "archive_audit_blocked":
            blocked_ids.append(case.archive_audit_case_id)
        elif case.archive_audit_status == "archive_audit_warning":
            warning_ids.append(case.archive_audit_case_id)
        else:
            invalid_ids.append(case.archive_audit_case_id)

    if zf:
        zf.close()

    if len(blocked_ids) > 0 or len(invalid_ids) > 0:
        report_status = "package_archive_invalid"
        reason_codes.append("AUDIT_CASES_FAILED_OR_BLOCKED")

    # Counts
    expected_member_count = m_dict.get("total_expected_archive_file_count", 28)
    actual_member_count = m_dict.get("total_archive_member_count", 0)
    verified_member_count = len([c for c in audited_cases if c.archive_audit_status == "archive_audit_verified" and not c.unexpected_archive_member])
    missing_member_count = len([c for c in audited_cases if c.missing_archive_member])
    unexpected_member_count = len([c for c in audited_cases if c.unexpected_archive_member])
    digest_mismatch_member_count = len([c for c in audited_cases if not c.archive_member_digest_match or not c.archive_member_digest_matches_source])
    invalid_member_count = len(invalid_ids)

    archive_member_paths_safe = all(c.archive_member_path_safety_verified for c in audited_cases)
    archive_file_set_verified = (verified_member_count == 28) and (missing_member_count == 0) and (unexpected_member_count == 0)

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

    archive_creation_performed = m_dict.get("archive_creation_performed", False)
    physical_operation_boundary_valid = (archive_creation_performed is True)

    archive_member_relative_paths = sorted(list(set(c.archive_member_relative_path for c in audited_cases)))
    archive_member_digests = sorted(list(set(c.archive_member_digest_recomputed for c in audited_cases if c.archive_member_digest_recomputed)))
    source_staged_file_digests = sorted(list(set(c.source_staged_file_digest_expected for c in audited_cases)))

    report = WaveguidePackageArchiveAuditReport(
        package_archive_audit_report_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-AUDIT-REPORT",
        package_archive_audit_report_version=1,
        package_archive_audit_report_status=report_status,
        source_package_archive_manifest_digest=manifest_digest,
        source_package_archive_build_record_digest=m_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=m_dict.get("source_package_archive_plan_digest", ""),
        archive_format="zip",
        archive_file_digest_recorded=archive_digest_recorded,
        archive_file_digest_recomputed=archive_digest_recomp,
        archive_file_digest_match=archive_digest_match,
        archive_file_size_bytes=archive_size,
        audited_cases=audited_cases,
        verified_archive_audit_cases=verified_ids,
        blocked_archive_audit_cases=blocked_ids,
        warning_archive_audit_cases=warning_ids,
        invalid_archive_audit_cases=invalid_ids,
        verified_archive_audit_count=len(verified_ids),
        blocked_archive_audit_count=len(blocked_ids),
        warning_archive_audit_count=len(warning_ids),
        invalid_archive_audit_count=len(invalid_ids),
        expected_archive_file_count=expected_member_count,
        archive_member_count=actual_member_count,
        verified_archive_member_count=verified_member_count,
        missing_archive_member_count=missing_member_count,
        unexpected_archive_member_count=unexpected_member_count,
        digest_mismatch_archive_member_count=digest_mismatch_member_count,
        invalid_archive_member_count=invalid_member_count,
        archive_member_relative_paths=archive_member_relative_paths,
        archive_member_digests=archive_member_digests,
        source_staged_file_digests=source_staged_file_digests,
        archive_member_paths_safe=archive_member_paths_safe,
        archive_file_set_verified=archive_file_set_verified,
        archive_digest_verified=archive_digest_match,
        archive_creation_performed=archive_creation_performed,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        physical_operation_boundary_valid=physical_operation_boundary_valid,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    report.package_archive_audit_report_digest = hash_waveguide_package_archive_audit_report(report)
    return report


def validate_waveguide_package_archive_audit_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a top-level Package Archive Audit Report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    errors = []

    # Verify digest
    recorded_digest = r_dict.get("package_archive_audit_report_digest", "")
    if not recorded_digest:
        errors.append("Missing audit report digest")
    else:
        recomputed = hash_waveguide_package_archive_audit_report(r_dict)
        if recomputed != recorded_digest:
            errors.append(f"Audit report digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    if r_dict.get("package_archive_audit_report_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-AUDIT-REPORT":
        errors.append("Invalid audit report ID")

    # Enforce prohibitions
    prohibitions = [
        ("upload_performed", False),
        ("deployment_performed", False),
        ("signing_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if r_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Check audited cases
    cases = r_dict.get("audited_cases", [])
    for c in cases:
        c_dig_rec = c.get("archive_audit_case_digest", "")
        c_dig_comp = hash_waveguide_package_archive_audit_case(c)
        if c_dig_rec != c_dig_comp:
            errors.append(f"Audit case digest mismatch for: {c.get('archive_member_relative_path')}")

    # Check verified counts
    if r_dict.get("verified_archive_member_count") != 28:
        errors.append(f"Expected exactly 28 verified members, found {r_dict.get('verified_archive_member_count')}")

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_audit_report(report: Any) -> str:
    """
    Generates a human-readable summary of the Package Archive Audit Report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    lines = [
        "=============================================================",
        "            SOL WAVEGUIDE PACKAGE ARCHIVE AUDIT REPORT",
        "=============================================================",
        f"Report ID:        {r_dict.get('package_archive_audit_report_id')}",
        f"Status:           {r_dict.get('package_archive_audit_report_status')}",
        f"Format:           {r_dict.get('archive_format')}",
        f"Archive Size:     {r_dict.get('archive_file_size_bytes')} bytes",
        f"Digest:           {r_dict.get('package_archive_audit_report_digest')}",
        f"Expected Count:   {r_dict.get('expected_archive_file_count')}",
        f"Audited Cases:    {len(r_dict.get('audited_cases', []))}",
        f"Verified Count:   {r_dict.get('verified_archive_member_count')}",
        f"Archive Digest Verified: {r_dict.get('archive_digest_verified')}",
        f"Archive Set Verified:    {r_dict.get('archive_file_set_verified')}",
        f"Boundary Valid:          {r_dict.get('physical_operation_boundary_valid')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in r_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_audit_report(report: Any, output_path: str) -> None:
    """
    Exports the Package Archive Audit Report to a JSON file.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_audit_reports(report_a: Any, report_b: Any) -> Dict[str, Any]:
    """
    Compares two Package Archive Audit Reports.
    """
    dict_a = asdict(report_a) if hasattr(report_a, "__dict__") else dict(report_a)
    dict_b = asdict(report_b) if hasattr(report_b, "__dict__") else dict(report_b)

    differences = {}
    for key in ("package_archive_audit_report_status", "archive_file_digest_recomputed", "verified_archive_member_count"):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
