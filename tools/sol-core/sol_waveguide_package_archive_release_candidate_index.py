# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Release Candidate Index.
Consumes the Package Archive Audit Report and registers the verified archive
as a local candidate.
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
from sol_waveguide_package_archive_validator import (
    validate_waveguide_package_archive_audit_report
)


@dataclass
class WaveguidePackageArchiveCandidateEntry:
    archive_candidate_entry_id: str
    archive_candidate_status: str  # archive_candidate_verified, archive_candidate_blocked, etc.
    archive_candidate_kind: str  # local_verified_zip_archive_candidate
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_format: str  # zip
    archive_filename: str
    archive_display_path: str
    archive_file_digest: str
    archive_file_size_bytes: int
    expected_archive_file_count: int
    verified_archive_member_count: int
    archive_member_paths_safe: bool
    archive_file_set_verified: bool
    archive_digest_verified: bool
    signing_status: str  # not_performed
    upload_status: str  # not_performed
    publication_status: str  # not_performed
    deployment_status: str  # not_performed
    production_mutation_status: str  # not_performed
    signing_performed: bool
    upload_performed: bool
    external_publication_performed: bool
    deployment_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_candidate_entry_digest: str = ""


@dataclass
class WaveguidePackageArchiveReleaseCandidateIndex:
    package_archive_release_candidate_index_id: str
    package_archive_release_candidate_index_version: int
    package_archive_release_candidate_index_status: str  # package_archive_candidate_index_valid, etc.
    source_package_archive_audit_report_digest: str
    archive_candidates: List[WaveguidePackageArchiveCandidateEntry]
    verified_archive_candidates: List[str]
    blocked_archive_candidates: List[str]
    warning_archive_candidates: List[str]
    invalid_archive_candidates: List[str]
    verified_archive_candidate_count: int
    blocked_archive_candidate_count: int
    warning_archive_candidate_count: int
    invalid_archive_candidate_count: int
    current_archive_candidate_digest: str
    current_archive_candidate_format: str
    current_archive_candidate_display_path: str
    current_archive_candidate_size_bytes: int
    archive_formats_indexed: List[str]
    archive_candidate_digests_indexed: List[str]
    archive_candidate_statuses_indexed: List[str]
    signing_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    signing_performed: bool
    upload_performed: bool
    external_publication_performed: bool
    deployment_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_archive_release_candidate_index_digest: str = ""


def hash_waveguide_package_archive_candidate_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a candidate entry, excluding archive_candidate_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("archive_candidate_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_archive_release_candidate_index(index_obj: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of the candidate index, excluding package_archive_release_candidate_index_digest.
    """
    if hasattr(index_obj, "__dict__"):
        i_dict = asdict(index_obj)
    elif isinstance(index_obj, dict):
        i_dict = dict(index_obj)
    else:
        raise TypeError("index_obj must be a dictionary or dataclass instance")

    i_copy = dict(i_dict)
    i_copy.pop("package_archive_release_candidate_index_digest", None)
    return hash_data(i_copy)


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


def build_waveguide_package_archive_candidate_entry(
    audit_report: Dict[str, Any],
    index: int
) -> WaveguidePackageArchiveCandidateEntry:
    """
    Builds an archive candidate entry from a verified audit report.
    """
    report_digest = audit_report.get("package_archive_audit_report_digest", "")
    report_status = audit_report.get("package_archive_audit_report_status", "")

    status = "archive_candidate_verified"
    reason_codes = ["CANDIDATE_VERIFIED"]

    if report_status != "package_archive_verified":
        status = "archive_candidate_blocked"
        reason_codes = ["AUDIT_REPORT_NOT_VERIFIED"]

    # Enforce performance boundaries checks
    signing_performed = audit_report.get("signing_performed", False)
    upload_performed = audit_report.get("upload_performed", False)
    publication_performed = audit_report.get("external_publication_performed", False)
    deployment_performed = audit_report.get("deployment_performed", False)
    production_mutation_performed = audit_report.get("production_mutation_performed", False)

    if signing_performed or upload_performed or publication_performed or deployment_performed or production_mutation_performed:
        status = "archive_candidate_invalid"
        reason_codes.append("CANDIDATE_MUTATION_VIOLATION")

    if not audit_report.get("archive_file_digest_recomputed"):
        status = "archive_candidate_invalid"
        reason_codes.append("MISSING_ARCHIVE_DIGEST")

    entry = WaveguidePackageArchiveCandidateEntry(
        archive_candidate_entry_id=f"SOL-WAVEGUIDE-ARCHIVE-CANDIDATE-ENTRY-{index:03d}",
        archive_candidate_status=status,
        archive_candidate_kind="local_verified_zip_archive_candidate",
        source_package_archive_audit_report_digest=report_digest,
        source_package_archive_manifest_digest=audit_report.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=audit_report.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=audit_report.get("source_package_archive_plan_digest", ""),
        archive_format=audit_report.get("archive_format", "zip"),
        archive_filename=audit_report.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
        archive_display_path=audit_report.get("archive_display_path", ""),
        archive_file_digest=audit_report.get("archive_file_digest_recomputed", ""),
        archive_file_size_bytes=audit_report.get("archive_file_size_bytes", 0),
        expected_archive_file_count=audit_report.get("expected_archive_file_count", 28),
        verified_archive_member_count=audit_report.get("verified_archive_member_count", 0),
        archive_member_paths_safe=audit_report.get("archive_member_paths_safe", False),
        archive_file_set_verified=audit_report.get("archive_file_set_verified", False),
        archive_digest_verified=audit_report.get("archive_digest_verified", False),
        signing_status="not_performed",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        signing_performed=signing_performed,
        upload_performed=upload_performed,
        external_publication_performed=publication_performed,
        deployment_performed=deployment_performed,
        production_mutation_performed=production_mutation_performed,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.archive_candidate_entry_digest = hash_waveguide_package_archive_candidate_entry(entry)
    return entry


def validate_waveguide_package_archive_candidate_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates an archive candidate entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    recorded = e_dict.get("archive_candidate_entry_digest", "")
    if not recorded:
        errors.append("Missing candidate entry digest")
    else:
        recomputed = hash_waveguide_package_archive_candidate_entry(e_dict)
        if recomputed != recorded:
            errors.append(f"Candidate entry digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    # Enforce prohibitions
    prohibitions = [
        ("signing_performed", False),
        ("upload_performed", False),
        ("external_publication_performed", False),
        ("deployment_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if e_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    if not e_dict.get("archive_file_digest"):
        errors.append("Missing archive file digest")

    if e_dict.get("archive_candidate_status") != "archive_candidate_verified":
        errors.append("Archive candidate status is not archive_candidate_verified")

    return len(errors) == 0, errors


def build_waveguide_package_archive_release_candidate_index(
    audit_report_path_or_dict: Any
) -> WaveguidePackageArchiveReleaseCandidateIndex:
    """
    Builds the Release Candidate Index from the audit report.
    """
    report_dict = _load_dict(audit_report_path_or_dict) or {}
    report_digest = report_dict.get("package_archive_audit_report_digest", "")
    report_status = report_dict.get("package_archive_audit_report_status", "")

    index_status = "package_archive_candidate_index_valid"
    reason_codes = ["PACKAGE_ARCHIVE_CANDIDATE_INDEX_VALID"]

    valid_report, report_errs = validate_waveguide_package_archive_audit_report(report_dict)

    if not valid_report:
        index_status = "package_archive_candidate_index_blocked"
        reason_codes = ["AUDIT_REPORT_NOT_VALID"]

    candidates = []
    verified_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []

    # Check report status
    if report_status == "package_archive_verified":
        entry = build_waveguide_package_archive_candidate_entry(report_dict, 0)
        candidates.append(entry)

        # Independent validate candidate entry
        ok, errs = validate_waveguide_package_archive_candidate_entry(entry)
        if ok:
            verified_ids.append(entry.archive_candidate_entry_id)
        else:
            invalid_ids.append(entry.archive_candidate_entry_id)
            index_status = "package_archive_candidate_index_invalid"
            reason_codes.append("CANDIDATE_ENTRY_INVALID")
    else:
        index_status = "package_archive_candidate_index_blocked"
        reason_codes.append("SOURCE_REPORT_NOT_VERIFIED")

    # Index values
    archive_formats_indexed = sorted(list(set(c.archive_format for c in candidates)))
    archive_candidate_digests_indexed = sorted(list(set(c.archive_file_digest for c in candidates if c.archive_file_digest)))
    archive_candidate_statuses_indexed = sorted(list(set(c.archive_candidate_status for c in candidates)))

    current_digest = ""
    current_format = ""
    current_display = ""
    current_size = 0

    if len(candidates) > 0:
        curr = candidates[0]
        current_digest = curr.archive_file_digest
        current_format = curr.archive_format
        current_display = curr.archive_display_path
        current_size = curr.archive_file_size_bytes

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

    index_obj = WaveguidePackageArchiveReleaseCandidateIndex(
        package_archive_release_candidate_index_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-RELEASE-CANDIDATE-INDEX",
        package_archive_release_candidate_index_version=1,
        package_archive_release_candidate_index_status=index_status,
        source_package_archive_audit_report_digest=report_digest,
        archive_candidates=candidates,
        verified_archive_candidates=verified_ids,
        blocked_archive_candidates=blocked_ids,
        warning_archive_candidates=warning_ids,
        invalid_archive_candidates=invalid_ids,
        verified_archive_candidate_count=len(verified_ids),
        blocked_archive_candidate_count=len(blocked_ids),
        warning_archive_candidate_count=len(warning_ids),
        invalid_archive_candidate_count=len(invalid_ids),
        current_archive_candidate_digest=current_digest,
        current_archive_candidate_format=current_format,
        current_archive_candidate_display_path=current_display,
        current_archive_candidate_size_bytes=current_size,
        archive_formats_indexed=archive_formats_indexed,
        archive_candidate_digests_indexed=archive_candidate_digests_indexed,
        archive_candidate_statuses_indexed=archive_candidate_statuses_indexed,
        signing_status="not_performed",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        signing_performed=False,
        upload_performed=False,
        external_publication_performed=False,
        deployment_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    index_obj.package_archive_release_candidate_index_digest = hash_waveguide_package_archive_release_candidate_index(index_obj)
    return index_obj


def validate_waveguide_package_archive_release_candidate_index(index_obj: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a WaveguidePackageArchiveReleaseCandidateIndex.
    """
    idx_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    errors = []

    # Verify digest
    recorded_digest = idx_dict.get("package_archive_release_candidate_index_digest", "")
    if not recorded_digest:
        errors.append("Missing index digest")
    else:
        recomputed = hash_waveguide_package_archive_release_candidate_index(idx_dict)
        if recomputed != recorded_digest:
            errors.append(f"Index digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    if idx_dict.get("package_archive_release_candidate_index_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-RELEASE-CANDIDATE-INDEX":
        errors.append("Invalid release candidate index ID")

    # Enforce prohibitions
    prohibitions = [
        ("signing_performed", False),
        ("upload_performed", False),
        ("external_publication_performed", False),
        ("deployment_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if idx_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Check candidates
    candidates = idx_dict.get("archive_candidates", [])
    for c in candidates:
        ok, errs = validate_waveguide_package_archive_candidate_entry(c)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_release_candidate_index(index_obj: Any) -> str:
    """
    Generates a human-readable summary of the Candidate Index.
    """
    idx_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    lines = [
        "=============================================================",
        "        SOL WAVEGUIDE PACKAGE ARCHIVE RC INDEX",
        "=============================================================",
        f"Index ID:         {idx_dict.get('package_archive_release_candidate_index_id')}",
        f"Status:           {idx_dict.get('package_archive_release_candidate_index_status')}",
        f"Digest:           {idx_dict.get('package_archive_release_candidate_index_digest')}",
        f"Candidate Format: {idx_dict.get('current_archive_candidate_format')}",
        f"Candidate Digest: {idx_dict.get('current_archive_candidate_digest')}",
        f"Candidate Size:   {idx_dict.get('current_archive_candidate_size_bytes')} bytes",
        f"Verified count:   {idx_dict.get('verified_archive_candidate_count')}",
        f"Signing status:   {idx_dict.get('signing_status')}",
        f"Upload status:    {idx_dict.get('upload_status')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in idx_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_release_candidate_index(index_obj: Any, output_path: str) -> None:
    """
    Exports the Candidate Index to a JSON file.
    """
    idx_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(idx_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_release_candidate_indexes(index_a: Any, index_b: Any) -> Dict[str, Any]:
    """
    Compares two Candidate Indexes.
    """
    dict_a = asdict(index_a) if hasattr(index_a, "__dict__") else dict(index_a)
    dict_b = asdict(index_b) if hasattr(index_b, "__dict__") else dict(index_b)

    differences = {}
    for key in ("package_archive_release_candidate_index_status", "current_archive_candidate_digest", "verified_archive_candidate_count"):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
