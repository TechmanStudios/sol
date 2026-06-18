# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Attested Archive Candidate Index.
Consumes the Digest Attestation Audit Report and registers the archive candidate
as a digest-attested local archive candidate in a local candidate index.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_archive_digest_attestation_validator import (
    validate_waveguide_package_archive_digest_attestation_audit_report
)


@dataclass
class WaveguidePackageAttestedArchiveCandidateEntry:
    attested_archive_candidate_entry_id: str
    attested_archive_candidate_status: str  # attested_archive_candidate_verified, etc.
    attested_archive_candidate_kind: str
    source_package_archive_digest_attestation_audit_report_digest: str
    source_package_archive_digest_attestation_digest: str
    source_package_archive_signing_gate_digest: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_format: str
    archive_filename: str
    archive_display_path: str
    archive_file_digest: str
    archive_file_size_bytes: int
    archive_candidate_digest: str
    digest_attestation_status: str
    digest_attestation_verified: bool
    real_signature_status: str
    real_signature_absent_verified: bool
    real_key_signing_absent_verified: bool
    private_key_material_absent_verified: bool
    credentials_absent_verified: bool
    network_access_absent_verified: bool
    signing_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    external_publication_performed: bool
    deployment_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    attested_archive_candidate_entry_digest: str = ""


@dataclass
class WaveguidePackageAttestedArchiveCandidateIndex:
    package_attested_archive_candidate_index_id: str
    package_attested_archive_candidate_index_version: int
    package_attested_archive_candidate_index_status: str  # package_attested_archive_candidate_index_valid, etc.
    source_package_archive_digest_attestation_audit_report_digest: str
    source_package_archive_digest_attestation_digest: str
    source_package_archive_signing_gate_digest: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    attested_archive_candidates: List[WaveguidePackageAttestedArchiveCandidateEntry]
    verified_attested_archive_candidates: List[str]
    blocked_attested_archive_candidates: List[str]
    warning_attested_archive_candidates: List[str]
    invalid_attested_archive_candidates: List[str]
    verified_attested_archive_candidate_count: int
    blocked_attested_archive_candidate_count: int
    warning_attested_archive_candidate_count: int
    invalid_attested_archive_candidate_count: int
    current_attested_archive_candidate_digest: str
    current_attested_archive_candidate_format: str
    current_attested_archive_candidate_display_path: str
    current_attested_archive_candidate_size_bytes: int
    archive_formats_indexed: List[str]
    attested_archive_candidate_digests_indexed: List[str]
    attested_archive_candidate_statuses_indexed: List[str]
    digest_attestation_statuses_indexed: List[str]
    digest_attestation_status: str
    real_signature_status: str
    signing_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    external_publication_performed: bool
    deployment_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_attested_archive_candidate_index_digest: str = ""


def hash_waveguide_package_attested_archive_candidate_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an entry,
    excluding attested_archive_candidate_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("attested_archive_candidate_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_attested_archive_candidate_index(index_obj: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an index,
    excluding package_attested_archive_candidate_index_digest.
    """
    if hasattr(index_obj, "__dict__"):
        i_dict = asdict(index_obj)
    elif isinstance(index_obj, dict):
        i_dict = dict(index_obj)
    else:
        raise TypeError("index_obj must be a dictionary or dataclass instance")

    i_copy = dict(i_dict)
    i_copy.pop("package_attested_archive_candidate_index_digest", None)
    return hash_data(i_copy)


def index_waveguide_package_attested_archive_candidates_by_status(
    entries: List[WaveguidePackageAttestedArchiveCandidateEntry]
) -> Dict[str, List[str]]:
    indexed = {
        "verified": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for e in entries:
        status = e.attested_archive_candidate_status
        if status == "attested_archive_candidate_verified":
            indexed["verified"].append(e.attested_archive_candidate_entry_id)
        elif status == "attested_archive_candidate_blocked":
            indexed["blocked"].append(e.attested_archive_candidate_entry_id)
        elif status == "attested_archive_candidate_warning":
            indexed["warning"].append(e.attested_archive_candidate_entry_id)
        else:
            indexed["invalid"].append(e.attested_archive_candidate_entry_id)
    return indexed


def index_waveguide_package_attested_archive_candidates_by_format(
    entries: List[WaveguidePackageAttestedArchiveCandidateEntry]
) -> List[str]:
    return sorted(list(set(e.archive_format for e in entries)))


def index_waveguide_package_attested_archive_candidates_by_digest(
    entries: List[WaveguidePackageAttestedArchiveCandidateEntry]
) -> List[str]:
    return sorted(list(set(e.archive_file_digest for e in entries)))


def index_waveguide_package_attested_archive_candidates_by_attestation_status(
    entries: List[WaveguidePackageAttestedArchiveCandidateEntry]
) -> List[str]:
    return sorted(list(set(e.digest_attestation_status for e in entries)))


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


def build_waveguide_package_attested_archive_candidate_entry(
    report_dict: Dict[str, Any],
    index: int
) -> WaveguidePackageAttestedArchiveCandidateEntry:
    """
    Builds a single attested archive candidate entry from a verified audit report.
    """
    report_status = report_dict.get("package_archive_digest_attestation_audit_report_status", "")
    report_digest = report_dict.get("package_archive_digest_attestation_audit_report_digest", "")

    status = "attested_archive_candidate_verified"
    reason_codes = ["ATTESTED_CANDIDATE_VERIFIED"]

    if report_status != "package_archive_digest_attestation_verified":
        status = "attested_archive_candidate_blocked"
        reason_codes = ["AUDIT_REPORT_NOT_VERIFIED"]

    # Enforce prohibitions
    upload_performed = report_dict.get("upload_performed", False)
    deployment_performed = report_dict.get("deployment_performed", False)
    publication_performed = report_dict.get("external_publication_performed", False)
    production_mutation_performed = report_dict.get("production_mutation_performed", False)

    if upload_performed or deployment_performed or publication_performed or production_mutation_performed:
        status = "attested_archive_candidate_invalid"
        reason_codes.append("CANDIDATE_MUTATION_VIOLATION")

    if not report_dict.get("archive_file_digest_recomputed"):
        status = "attested_archive_candidate_invalid"
        reason_codes.append("MISSING_ARCHIVE_DIGEST")

    entry = WaveguidePackageAttestedArchiveCandidateEntry(
        attested_archive_candidate_entry_id=f"SOL-WAVEGUIDE-ATTESTED-ARCHIVE-ENTRY-{index:03d}",
        attested_archive_candidate_status=status,
        attested_archive_candidate_kind="local_digest_attested_zip_archive_candidate",
        source_package_archive_digest_attestation_audit_report_digest=report_digest,
        source_package_archive_digest_attestation_digest=report_dict.get("source_package_archive_digest_attestation_digest", ""),
        source_package_archive_signing_gate_digest=report_dict.get("source_package_archive_signing_gate_digest", ""),
        source_package_archive_signing_plan_digest=report_dict.get("source_package_archive_signing_plan_digest", ""),
        source_package_archive_release_candidate_index_digest=report_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=report_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=report_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=report_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=report_dict.get("source_package_archive_plan_digest", ""),
        archive_format=report_dict.get("archive_format", "zip"),
        archive_filename=report_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
        archive_display_path=report_dict.get("archive_display_path", ""),
        archive_file_digest=report_dict.get("archive_file_digest_recomputed", ""),
        archive_file_size_bytes=report_dict.get("archive_file_size_bytes", 0),
        archive_candidate_digest=report_dict.get("archive_candidate_digest", ""),
        digest_attestation_status="verified" if report_status == "package_archive_digest_attestation_verified" else "failed",
        digest_attestation_verified=report_dict.get("digest_attestation_verified", False),
        real_signature_status="not_performed",
        real_signature_absent_verified=report_dict.get("real_signature_absent_verified", False),
        real_key_signing_absent_verified=report_dict.get("real_key_signing_absent_verified", False),
        private_key_material_absent_verified=report_dict.get("private_key_material_absent_verified", False),
        credentials_absent_verified=report_dict.get("credentials_absent_verified", False),
        network_access_absent_verified=report_dict.get("network_access_absent_verified", False),
        signing_status="not_performed",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        signing_performed=report_dict.get("signing_performed", False),
        real_key_signature_performed=report_dict.get("real_key_signature_performed", False),
        digest_attestation_performed=report_dict.get("digest_attestation_performed", False),
        external_signing_performed=report_dict.get("external_signing_performed", False),
        timestamp_authority_performed=report_dict.get("timestamp_authority_performed", False),
        upload_performed=upload_performed,
        external_publication_performed=publication_performed,
        deployment_performed=deployment_performed,
        production_mutation_performed=production_mutation_performed,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.attested_archive_candidate_entry_digest = hash_waveguide_package_attested_archive_candidate_entry(entry)
    return entry


def validate_waveguide_package_attested_archive_candidate_entry(
    entry: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates an attested archive candidate entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    # Verify digest
    recorded = e_dict.get("attested_archive_candidate_entry_digest", "")
    if not recorded:
        errors.append("Missing entry digest")
    else:
        recomputed = hash_waveguide_package_attested_archive_candidate_entry(e_dict)
        if recomputed != recorded:
            errors.append(f"Entry digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    # Enforce prohibitions
    prohibitions = [
        ("real_signature_status", "not_performed"),
        ("real_signature_absent_verified", True),
        ("real_key_signing_absent_verified", True),
        ("private_key_material_absent_verified", True),
        ("credentials_absent_verified", True),
        ("network_access_absent_verified", True),
        ("upload_performed", False),
        ("external_publication_performed", False),
        ("deployment_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if e_dict.get(key) != expected:
            errors.append(f"{key} must be {expected}")

    # Validate entry status
    if e_dict.get("attested_archive_candidate_status") != "attested_archive_candidate_verified":
        errors.append("Attested candidate status is not verified")

    if not e_dict.get("archive_file_digest"):
        errors.append("Missing archive file digest")

    return len(errors) == 0, errors


def build_waveguide_package_attested_archive_candidate_index(
    audit_report_path_or_dict: Any
) -> WaveguidePackageAttestedArchiveCandidateIndex:
    """
    Builds the Attested Archive Candidate Index from the Audit Report.
    """
    rep_dict = _load_dict(audit_report_path_or_dict) or {}
    rep_digest = rep_dict.get("package_archive_digest_attestation_audit_report_digest", "")
    rep_status = rep_dict.get("package_archive_digest_attestation_audit_report_status", "")

    status = "package_attested_archive_candidate_index_valid"
    reason_codes = ["ATTESTED_ARCHIVE_CANDIDATE_INDEX_VALID"]

    valid_rep, rep_errs = validate_waveguide_package_archive_digest_attestation_audit_report(rep_dict)
    if not valid_rep or rep_status != "package_archive_digest_attestation_verified":
        status = "package_attested_archive_candidate_index_blocked"
        reason_codes = ["AUDIT_REPORT_NOT_VERIFIED"]

    # Check for upload/deployment/mutate violations in audit report
    upload_performed = rep_dict.get("upload_performed", False)
    deployment_performed = rep_dict.get("deployment_performed", False)
    publication_performed = rep_dict.get("external_publication_performed", False)
    production_mutation_performed = rep_dict.get("production_mutation_performed", False)

    if upload_performed or deployment_performed or publication_performed or production_mutation_performed:
        status = "package_attested_archive_candidate_index_invalid"
        reason_codes.append("CANDIDATE_MUTATION_VIOLATION")

    entries = []
    # Currently assuming 1 verified candidate from the verified audit report
    if status != "package_attested_archive_candidate_index_invalid" and status != "package_attested_archive_candidate_index_blocked":
        entry = build_waveguide_package_attested_archive_candidate_entry(rep_dict, 0)
        entries.append(entry)

    indexed = index_waveguide_package_attested_archive_candidates_by_status(entries)
    
    verified_ids = indexed["verified"]
    blocked_ids = indexed["blocked"]
    warning_ids = indexed["warning"]
    invalid_ids = indexed["invalid"]

    if len(invalid_ids) > 0 or len(blocked_ids) > 0:
        status = "package_attested_archive_candidate_index_invalid"
        reason_codes.append("INDEX_ENTRIES_INVALID_OR_BLOCKED")

    formats_indexed = index_waveguide_package_attested_archive_candidates_by_format(entries)
    digests_indexed = index_waveguide_package_attested_archive_candidates_by_digest(entries)
    statuses_indexed = sorted(list(set(e.attested_archive_candidate_status for e in entries)))
    att_statuses_indexed = index_waveguide_package_attested_archive_candidates_by_attestation_status(entries)

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

    current_digest = digests_indexed[0] if len(digests_indexed) > 0 else ""
    current_format = formats_indexed[0] if len(formats_indexed) > 0 else ""
    current_display = rep_dict.get("archive_display_path", "")
    current_size = rep_dict.get("archive_file_size_bytes", 0)

    index_obj = WaveguidePackageAttestedArchiveCandidateIndex(
        package_attested_archive_candidate_index_id="SOL-WAVEGUIDE-PACKAGE-ATTESTED-ARCHIVE-CANDIDATE-INDEX",
        package_attested_archive_candidate_index_version=1,
        package_attested_archive_candidate_index_status=status,
        source_package_archive_digest_attestation_audit_report_digest=rep_digest,
        source_package_archive_digest_attestation_digest=rep_dict.get("source_package_archive_digest_attestation_digest", ""),
        source_package_archive_signing_gate_digest=rep_dict.get("source_package_archive_signing_gate_digest", ""),
        source_package_archive_signing_plan_digest=rep_dict.get("source_package_archive_signing_plan_digest", ""),
        source_package_archive_release_candidate_index_digest=rep_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=rep_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=rep_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=rep_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=rep_dict.get("source_package_archive_plan_digest", ""),
        attested_archive_candidates=entries,
        verified_attested_archive_candidates=verified_ids,
        blocked_attested_archive_candidates=blocked_ids,
        warning_attested_archive_candidates=warning_ids,
        invalid_attested_archive_candidates=invalid_ids,
        verified_attested_archive_candidate_count=len(verified_ids),
        blocked_attested_archive_candidate_count=len(blocked_ids),
        warning_attested_archive_candidate_count=len(warning_ids),
        invalid_attested_archive_candidate_count=len(invalid_ids),
        current_attested_archive_candidate_digest=current_digest,
        current_attested_archive_candidate_format=current_format,
        current_attested_archive_candidate_display_path=current_display,
        current_attested_archive_candidate_size_bytes=current_size,
        archive_formats_indexed=formats_indexed,
        attested_archive_candidate_digests_indexed=digests_indexed,
        attested_archive_candidate_statuses_indexed=statuses_indexed,
        digest_attestation_statuses_indexed=att_statuses_indexed,
        digest_attestation_status="verified" if status == "package_attested_archive_candidate_index_valid" else "failed",
        real_signature_status="not_performed",
        signing_status="not_performed",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        signing_performed=rep_dict.get("signing_performed", False),
        real_key_signature_performed=rep_dict.get("real_key_signature_performed", False),
        digest_attestation_performed=rep_dict.get("digest_attestation_performed", False),
        external_signing_performed=rep_dict.get("external_signing_performed", False),
        timestamp_authority_performed=rep_dict.get("timestamp_authority_performed", False),
        upload_performed=upload_performed,
        external_publication_performed=publication_performed,
        deployment_performed=deployment_performed,
        production_mutation_performed=production_mutation_performed,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    index_obj.package_attested_archive_candidate_index_digest = hash_waveguide_package_attested_archive_candidate_index(index_obj)
    return index_obj


def validate_waveguide_package_attested_archive_candidate_index(
    index_obj: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates a top-level Attested Archive Candidate Index.
    """
    i_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    errors = []

    # Verify digest
    recorded = i_dict.get("package_attested_archive_candidate_index_digest", "")
    if not recorded:
        errors.append("Missing index digest")
    else:
        recomputed = hash_waveguide_package_attested_archive_candidate_index(i_dict)
        if recomputed != recorded:
            errors.append(f"Index digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if i_dict.get("package_attested_archive_candidate_index_id") != "SOL-WAVEGUIDE-PACKAGE-ATTESTED-ARCHIVE-CANDIDATE-INDEX":
        errors.append("Invalid index ID")

    # Enforce prohibitions
    prohibitions = [
        ("real_signature_status", "not_performed"),
        ("upload_performed", False),
        ("external_publication_performed", False),
        ("deployment_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if i_dict.get(key) != expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Check entries
    entries = i_dict.get("attested_archive_candidates", [])
    for e in entries:
        ok, errs = validate_waveguide_package_attested_archive_candidate_entry(e)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_package_attested_archive_candidate_index(index_obj: Any) -> str:
    """
    Generates a human-readable summary of the Attested Candidate Index.
    """
    i_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    lines = [
        "=============================================================",
        "        SOL WAVEGUIDE ATTESTED ARCHIVE CANDIDATE INDEX",
        "=============================================================",
        f"Index ID:         {i_dict.get('package_attested_archive_candidate_index_id')}",
        f"Status:           {i_dict.get('package_attested_archive_candidate_index_status')}",
        f"Index Digest:     {i_dict.get('package_attested_archive_candidate_index_digest')}",
        f"Candidate Format: {i_dict.get('current_attested_archive_candidate_format')}",
        f"Candidate Digest: {i_dict.get('current_attested_archive_candidate_digest')}",
        f"Attest Status:    {i_dict.get('digest_attestation_status')}",
        f"Real Sign Status: {i_dict.get('real_signature_status')}",
        f"Verified count:   {i_dict.get('verified_attested_archive_candidate_count')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in i_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_attested_archive_candidate_index(index_obj: Any, output_path: str) -> None:
    """
    Exports the Attested Candidate Index to a JSON file.
    """
    i_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(i_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_attested_archive_candidate_indexes(idx_a: Any, idx_b: Any) -> Dict[str, Any]:
    """
    Compares two Attested Candidate Indexes.
    """
    dict_a = asdict(idx_a) if hasattr(idx_a, "__dict__") else dict(idx_a)
    dict_b = asdict(idx_b) if hasattr(idx_b, "__dict__") else dict(idx_b)

    differences = {}
    for key in (
        "package_attested_archive_candidate_index_status",
        "current_attested_archive_candidate_digest",
        "verified_attested_archive_candidate_count"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
