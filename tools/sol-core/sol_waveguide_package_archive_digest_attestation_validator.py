# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Digest Attestation Validator.
Independently verifies the Digest Attestation, recomputes digests,
verifies that no real key signing occurred, and produces an audit report.
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
from sol_waveguide_package_archive_digest_attestation import (
    validate_waveguide_package_archive_digest_attestation,
    validate_waveguide_package_archive_digest_attestation_statement,
    hash_waveguide_package_archive_digest_attestation_statement,
    hash_waveguide_package_archive_digest_attestation,
    recompute_waveguide_package_archive_digest_for_attestation
)


@dataclass
class WaveguidePackageArchiveDigestAttestationAuditCase:
    archive_digest_attestation_audit_case_id: str
    source_package_archive_digest_attestation_digest: str
    source_package_archive_digest_attestation_valid: bool
    source_package_archive_signing_gate_digest: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_digest_attestation_statement_id: str
    archive_digest_attestation_statement_digest_recorded: str
    archive_digest_attestation_statement_digest_recomputed: str
    archive_digest_attestation_statement_digest_match: bool
    attestation_audit_status: str  # archive_digest_attestation_audit_verified, etc.
    archive_candidate_digest: str
    archive_format: str
    archive_filename: str
    archive_display_path: str
    archive_file_digest_recorded: str
    archive_file_digest_recomputed: str
    archive_file_digest_match: bool
    attestation_kind: str
    attestation_algorithm: str
    attestation_hash_algorithm: str
    real_signature_claimed: bool
    real_key_signing_used: bool
    external_signing_used: bool
    timestamp_authority_used: bool
    private_key_material_loaded: bool
    credentials_loaded: bool
    network_access_used: bool
    digest_attestation_performed: bool
    real_key_signature_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    deployment_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    operation_boundary_valid: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_digest_attestation_audit_case_digest: str = ""


@dataclass
class WaveguidePackageArchiveDigestAttestationAuditReport:
    package_archive_digest_attestation_audit_report_id: str
    package_archive_digest_attestation_audit_report_version: int
    package_archive_digest_attestation_audit_report_status: str  # package_archive_digest_attestation_verified, etc.
    source_package_archive_digest_attestation_digest: str
    source_package_archive_signing_gate_digest: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_file_digest_recorded: str
    archive_file_digest_recomputed: str
    archive_file_digest_match: bool
    audited_cases: List[WaveguidePackageArchiveDigestAttestationAuditCase]
    verified_archive_digest_attestation_audit_cases: List[str]
    blocked_archive_digest_attestation_audit_cases: List[str]
    warning_archive_digest_attestation_audit_cases: List[str]
    invalid_archive_digest_attestation_audit_cases: List[str]
    verified_archive_digest_attestation_audit_count: int
    blocked_archive_digest_attestation_audit_count: int
    warning_archive_digest_attestation_audit_count: int
    invalid_archive_digest_attestation_audit_count: int
    archive_candidate_digest: str
    archive_format: str
    archive_filename: str
    archive_display_path: str
    archive_file_size_bytes: int
    attestation_kind: str
    attestation_algorithm: str
    attestation_hash_algorithm: str
    digest_attestation_verified: bool
    real_signature_absent_verified: bool
    real_key_signing_absent_verified: bool
    private_key_material_absent_verified: bool
    credentials_absent_verified: bool
    network_access_absent_verified: bool
    operation_boundary_valid: bool
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    deployment_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_archive_digest_attestation_audit_report_digest: str = ""


def hash_waveguide_package_archive_digest_attestation_audit_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an audit case,
    excluding archive_digest_attestation_audit_case_digest.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or dataclass instance")

    c_copy = dict(c_dict)
    c_copy.pop("archive_digest_attestation_audit_case_digest", None)
    return hash_data(c_copy)


def hash_waveguide_package_archive_digest_attestation_audit_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an audit report,
    excluding package_archive_digest_attestation_audit_report_digest.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or dataclass instance")

    r_copy = dict(r_dict)
    r_copy.pop("package_archive_digest_attestation_audit_report_digest", None)
    return hash_data(r_copy)


def recompute_waveguide_package_archive_digest_attestation_digest(att_dict: Dict[str, Any]) -> str:
    return hash_waveguide_package_archive_digest_attestation(att_dict)


def recompute_waveguide_package_archive_digest_attestation_statement_digest(stmt_dict: Dict[str, Any]) -> str:
    return hash_waveguide_package_archive_digest_attestation_statement(stmt_dict)


def recompute_waveguide_package_archive_file_digest_for_attestation_audit(archive_filepath: str) -> str:
    return recompute_waveguide_package_archive_digest_for_attestation(archive_filepath)


def validate_waveguide_package_archive_digest_attestation_source_chain_audit(
    att_dict: Dict[str, Any]
) -> bool:
    # Check that upstream digests exist and are valid SHA256 hex strings (64 chars)
    keys = [
        "source_package_archive_signing_gate_digest",
        "source_package_archive_signing_plan_digest",
        "source_package_archive_release_candidate_index_digest",
        "source_package_archive_audit_report_digest",
        "source_package_archive_manifest_digest",
        "source_package_archive_build_record_digest",
        "source_package_archive_plan_digest"
    ]
    for key in keys:
        val = att_dict.get(key, "")
        if not val or len(val) != 64:
            return False
    return True

# support both names to avoid any naming issues
validate_waveguide_package_archive_digest_attestation_source_chain = validate_waveguide_package_archive_digest_attestation_source_chain_audit


def validate_waveguide_package_archive_digest_attestation_no_real_signature(
    att_dict: Dict[str, Any]
) -> bool:
    # Ensure all real signature/signing options are absent
    checks = [
        ("real_signature_claimed", False),
        ("real_key_signing_used", False),
        ("external_signing_used", False),
        ("timestamp_authority_used", False),
        ("private_key_material_loaded", False),
        ("credentials_loaded", False),
        ("network_access_used", False),
    ]
    for key, expected in checks:
        if att_dict.get(key, False) is not expected:
            return False
    return True


def validate_waveguide_package_archive_digest_attestation_operation_boundaries(
    att_dict: Dict[str, Any]
) -> bool:
    # Ensure no network, credential, signing, or deploy operations occurred
    ops = [
        ("real_key_signature_performed", False),
        ("external_signing_performed", False),
        ("timestamp_authority_performed", False),
        ("upload_performed", False),
        ("deployment_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in ops:
        if att_dict.get(key, False) is not expected:
            return False
    return True


def index_waveguide_package_archive_digest_attestation_audit_cases_by_status(
    cases: List[WaveguidePackageArchiveDigestAttestationAuditCase]
) -> Dict[str, List[str]]:
    indexed = {
        "verified": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for c in cases:
        status = c.attestation_audit_status
        if status == "archive_digest_attestation_audit_verified":
            indexed["verified"].append(c.archive_digest_attestation_audit_case_id)
        elif status == "archive_digest_attestation_audit_blocked":
            indexed["blocked"].append(c.archive_digest_attestation_audit_case_id)
        elif status == "archive_digest_attestation_audit_warning":
            indexed["warning"].append(c.archive_digest_attestation_audit_case_id)
        else:
            indexed["invalid"].append(c.archive_digest_attestation_audit_case_id)
    return indexed


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


def build_waveguide_package_archive_digest_attestation_audit_case(
    stmt_dict: Dict[str, Any],
    att_digest: str,
    att_valid: bool,
    index: int,
    archive_filepath: str,
    archive_override_digest: Optional[str] = None
) -> WaveguidePackageArchiveDigestAttestationAuditCase:
    """
    Builds a single digest attestation audit case.
    """
    stmt_digest_recorded = stmt_dict.get("archive_digest_attestation_statement_digest", "")
    stmt_digest_recomputed = recompute_waveguide_package_archive_digest_attestation_statement_digest(stmt_dict)
    stmt_digest_match = (stmt_digest_recorded == stmt_digest_recomputed) and (stmt_digest_recorded != "")

    recorded_file_digest = stmt_dict.get("archive_file_digest_recorded", "")
    if archive_override_digest is not None:
        recomputed_file_digest = archive_override_digest
    else:
        recomputed_file_digest = recompute_waveguide_package_archive_file_digest_for_attestation_audit(archive_filepath)

    file_digest_match = (recorded_file_digest == recomputed_file_digest) and (recorded_file_digest != "")

    no_real_sig = validate_waveguide_package_archive_digest_attestation_no_real_signature(stmt_dict)
    op_bound = validate_waveguide_package_archive_digest_attestation_operation_boundaries(stmt_dict)

    status = "archive_digest_attestation_audit_verified"
    reason_codes = ["AUDIT_CASE_VERIFIED"]

    if not stmt_digest_match:
        status = "archive_digest_attestation_audit_invalid"
        reason_codes.append("STATEMENT_DIGEST_MISMATCH")

    if not file_digest_match:
        status = "archive_digest_attestation_audit_invalid"
        reason_codes.append("FILE_DIGEST_MISMATCH")

    if not no_real_sig:
        status = "archive_digest_attestation_audit_blocked"
        reason_codes.append("REAL_SIGNATURE_DETECTED")

    if not op_bound:
        status = "archive_digest_attestation_audit_blocked"
        reason_codes.append("OPERATION_BOUNDARY_VIOLATION")

    case = WaveguidePackageArchiveDigestAttestationAuditCase(
        archive_digest_attestation_audit_case_id=f"SOL-WAVEGUIDE-ATTESTATION-AUDIT-CASE-{index:03d}",
        source_package_archive_digest_attestation_digest=att_digest,
        source_package_archive_digest_attestation_valid=att_valid,
        source_package_archive_signing_gate_digest=stmt_dict.get("source_package_archive_signing_gate_digest", ""),
        source_package_archive_signing_plan_digest=stmt_dict.get("source_package_archive_signing_plan_digest", ""),
        source_package_archive_release_candidate_index_digest=stmt_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=stmt_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=stmt_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=stmt_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=stmt_dict.get("source_package_archive_plan_digest", ""),
        archive_digest_attestation_statement_id=stmt_dict.get("archive_digest_attestation_statement_id", ""),
        archive_digest_attestation_statement_digest_recorded=stmt_digest_recorded,
        archive_digest_attestation_statement_digest_recomputed=stmt_digest_recomputed,
        archive_digest_attestation_statement_digest_match=stmt_digest_match,
        attestation_audit_status=status,
        archive_candidate_digest=stmt_dict.get("archive_candidate_digest", ""),
        archive_format=stmt_dict.get("archive_format", ""),
        archive_filename=stmt_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
        archive_display_path=stmt_dict.get("archive_display_path", ""),
        archive_file_digest_recorded=recorded_file_digest,
        archive_file_digest_recomputed=recomputed_file_digest,
        archive_file_digest_match=file_digest_match,
        attestation_kind=stmt_dict.get("attestation_kind", ""),
        attestation_algorithm=stmt_dict.get("attestation_algorithm", ""),
        attestation_hash_algorithm=stmt_dict.get("attestation_hash_algorithm", ""),
        real_signature_claimed=stmt_dict.get("real_signature_claimed", False),
        real_key_signing_used=stmt_dict.get("real_key_signing_used", False),
        external_signing_used=stmt_dict.get("external_signing_used", False),
        timestamp_authority_used=stmt_dict.get("timestamp_authority_used", False),
        private_key_material_loaded=stmt_dict.get("private_key_material_loaded", False),
        credentials_loaded=stmt_dict.get("credentials_loaded", False),
        network_access_used=stmt_dict.get("network_access_used", False),
        digest_attestation_performed=stmt_dict.get("digest_attestation_performed", True),
        real_key_signature_performed=stmt_dict.get("real_key_signature_performed", False),
        external_signing_performed=stmt_dict.get("external_signing_performed", False),
        timestamp_authority_performed=stmt_dict.get("timestamp_authority_performed", False),
        upload_performed=stmt_dict.get("upload_performed", False),
        deployment_performed=stmt_dict.get("deployment_performed", False),
        external_publication_performed=stmt_dict.get("external_publication_performed", False),
        production_mutation_performed=stmt_dict.get("production_mutation_performed", False),
        operation_boundary_valid=op_bound,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    case.archive_digest_attestation_audit_case_digest = hash_waveguide_package_archive_digest_attestation_audit_case(case)
    return case


def validate_waveguide_package_archive_digest_attestation_independently(
    att_dict: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Performs basic independent syntax and structure checks on the attestation artifact.
    """
    return validate_waveguide_package_archive_digest_attestation(att_dict)


def build_waveguide_package_archive_digest_attestation_audit_report(
    attestation_path_or_dict: Any,
    archive_filepath_override: Optional[str] = None,
    archive_override_digest: Optional[str] = None
) -> WaveguidePackageArchiveDigestAttestationAuditReport:
    """
    Builds the top-level audit report by verifying the loaded attestation.
    """
    att_dict = _load_dict(attestation_path_or_dict) or {}
    att_digest = att_dict.get("package_archive_digest_attestation_digest", "")
    att_status = att_dict.get("package_archive_digest_attestation_status", "")

    att_valid, att_errs = validate_waveguide_package_archive_digest_attestation_independently(att_dict)

    status = "package_archive_digest_attestation_verified"
    reason_codes = ["DIGEST_ATTESTATION_AUDIT_SUCCESS"]

    if not att_valid or att_status != "package_archive_digest_attested":
        status = "package_archive_digest_attestation_blocked"
        reason_codes = ["DIGEST_ATTESTATION_NOT_READY"]

    archive_filepath = archive_filepath_override or att_dict.get("archive_display_path", "")
    if not archive_filepath:
        archive_filepath = "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"
    statements = att_dict.get("archive_digest_attestation_statements", [])

    cases = []
    verified_ids = []
    blocked_ids = []
    warning_ids = []
    invalid_ids = []
    file_digest_match = False
    recorded_file_digest = att_dict.get("archive_file_digest_recorded", "")
    recomputed_file_digest = ""

    if status == "package_archive_digest_attestation_verified":
        for i, s in enumerate(statements):
            case = build_waveguide_package_archive_digest_attestation_audit_case(
                s, att_digest, att_valid, i, archive_filepath, archive_override_digest=archive_override_digest
            )
            cases.append(case)

        indexed = index_waveguide_package_archive_digest_attestation_audit_cases_by_status(cases)
        verified_ids = indexed["verified"]
        blocked_ids = indexed["blocked"]
        warning_ids = indexed["warning"]
        invalid_ids = indexed["invalid"]

        if len(invalid_ids) > 0 or len(blocked_ids) > 0:
            status = "package_archive_digest_attestation_invalid"
            reason_codes.append("AUDIT_CASES_FAILED")

        # Recompute file digest matches
        if archive_override_digest is not None:
            recomputed_file_digest = archive_override_digest
        else:
            recomputed_file_digest = recompute_waveguide_package_archive_file_digest_for_attestation_audit(archive_filepath)

        file_digest_match = (recorded_file_digest == recomputed_file_digest) and (recorded_file_digest != "")

        if not file_digest_match:
            status = "package_archive_digest_attestation_invalid"
            reason_codes.append("FILE_DIGEST_MISMATCH")
    else:
        if archive_override_digest is not None:
            recomputed_file_digest = archive_override_digest
        else:
            recomputed_file_digest = recompute_waveguide_package_archive_file_digest_for_attestation_audit(archive_filepath)
        file_digest_match = (recorded_file_digest == recomputed_file_digest) and (recorded_file_digest != "")

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

    no_real_sig = validate_waveguide_package_archive_digest_attestation_no_real_signature(att_dict)
    op_bound = validate_waveguide_package_archive_digest_attestation_operation_boundaries(att_dict)

    report = WaveguidePackageArchiveDigestAttestationAuditReport(
        package_archive_digest_attestation_audit_report_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-DIGEST-ATTESTATION-AUDIT-REPORT",
        package_archive_digest_attestation_audit_report_version=1,
        package_archive_digest_attestation_audit_report_status=status,
        source_package_archive_digest_attestation_digest=att_digest,
        source_package_archive_signing_gate_digest=att_dict.get("source_package_archive_signing_gate_digest", ""),
        source_package_archive_signing_plan_digest=att_dict.get("source_package_archive_signing_plan_digest", ""),
        source_package_archive_release_candidate_index_digest=att_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=att_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=att_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=att_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=att_dict.get("source_package_archive_plan_digest", ""),
        archive_file_digest_recorded=recorded_file_digest,
        archive_file_digest_recomputed=recomputed_file_digest,
        archive_file_digest_match=file_digest_match,
        audited_cases=cases,
        verified_archive_digest_attestation_audit_cases=verified_ids,
        blocked_archive_digest_attestation_audit_cases=blocked_ids,
        warning_archive_digest_attestation_audit_cases=warning_ids,
        invalid_archive_digest_attestation_audit_cases=invalid_ids,
        verified_archive_digest_attestation_audit_count=len(verified_ids),
        blocked_archive_digest_attestation_audit_count=len(blocked_ids),
        warning_archive_digest_attestation_audit_count=len(warning_ids),
        invalid_archive_digest_attestation_audit_count=len(invalid_ids),
        archive_candidate_digest=att_dict.get("archive_candidate_digest", ""),
        archive_format=att_dict.get("archive_format", ""),
        archive_filename=att_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
        archive_display_path=att_dict.get("archive_display_path", ""),
        archive_file_size_bytes=att_dict.get("archive_file_size_bytes", 0),
        attestation_kind="local_digest_attestation",
        attestation_algorithm="sha256_digest_binding_statement",
        attestation_hash_algorithm="sha256",
        digest_attestation_verified=(status == "package_archive_digest_attestation_verified"),
        real_signature_absent_verified=no_real_sig,
        real_key_signing_absent_verified=no_real_sig,
        private_key_material_absent_verified=no_real_sig,
        credentials_absent_verified=no_real_sig,
        network_access_absent_verified=no_real_sig,
        operation_boundary_valid=op_bound,
        signing_performed=False,
        real_key_signature_performed=False,
        digest_attestation_performed=att_dict.get("digest_attestation_performed", True),
        external_signing_performed=False,
        timestamp_authority_performed=False,
        upload_performed=False,
        deployment_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    report.package_archive_digest_attestation_audit_report_digest = hash_waveguide_package_archive_digest_attestation_audit_report(report)
    return report


def validate_waveguide_package_archive_digest_attestation_audit_report(
    report: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates a top-level audit report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    errors = []

    # Verify digest
    recorded = r_dict.get("package_archive_digest_attestation_audit_report_digest", "")
    if not recorded:
        errors.append("Missing audit report digest")
    else:
        recomputed = hash_waveguide_package_archive_digest_attestation_audit_report(r_dict)
        if recomputed != recorded:
            errors.append(f"Audit report digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if r_dict.get("package_archive_digest_attestation_audit_report_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-DIGEST-ATTESTATION-AUDIT-REPORT":
        errors.append("Invalid audit report ID")

    # Enforce prohibitions
    prohibitions = [
        ("real_signature_absent_verified", True),
        ("real_key_signing_absent_verified", True),
        ("private_key_material_absent_verified", True),
        ("credentials_absent_verified", True),
        ("network_access_absent_verified", True),
        ("operation_boundary_valid", True),
        ("signing_performed", False),
        ("real_key_signature_performed", False),
        ("external_signing_performed", False),
        ("timestamp_authority_performed", False),
        ("upload_performed", False),
        ("deployment_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if r_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Check audited cases
    cases = r_dict.get("audited_cases", [])
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        # Verify case digest
        c_recorded = c_dict.get("archive_digest_attestation_audit_case_digest", "")
        if not c_recorded:
            errors.append("Missing case digest")
        else:
            c_recomputed = hash_waveguide_package_archive_digest_attestation_audit_case(c_dict)
            if c_recomputed != c_recorded:
                errors.append(f"Case digest mismatch. Recorded: {c_recorded}, Recomputed: {c_recomputed}")

        if c_dict.get("attestation_audit_status") != "archive_digest_attestation_audit_verified":
            errors.append(f"Audit case {c_dict.get('archive_digest_attestation_audit_case_id')} status is not verified")

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_digest_attestation_audit_report(report: Any) -> str:
    """
    Generates a human-readable summary of the Audit Report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    lines = [
        "=============================================================",
        "        SOL WAVEGUIDE DIGEST ATTESTATION AUDIT REPORT",
        "=============================================================",
        f"Report ID:        {r_dict.get('package_archive_digest_attestation_audit_report_id')}",
        f"Status:           {r_dict.get('package_archive_digest_attestation_audit_report_status')}",
        f"Report Digest:    {r_dict.get('package_archive_digest_attestation_audit_report_digest')}",
        f"File Digest Match: {r_dict.get('archive_file_digest_match')}",
        f"Attest Verified:  {r_dict.get('digest_attestation_verified')}",
        f"Real Sign Absent: {r_dict.get('real_signature_absent_verified')}",
        f"Verified cases:   {r_dict.get('verified_archive_digest_attestation_audit_count')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in r_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_digest_attestation_audit_report(report: Any, output_path: str) -> None:
    """
    Exports the Audit Report to a JSON file.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_digest_attestation_audit_reports(rep_a: Any, rep_b: Any) -> Dict[str, Any]:
    """
    Compares two Audit Reports.
    """
    dict_a = asdict(rep_a) if hasattr(rep_a, "__dict__") else dict(rep_a)
    dict_b = asdict(rep_b) if hasattr(rep_b, "__dict__") else dict(rep_b)

    differences = {}
    for key in (
        "package_archive_digest_attestation_audit_report_status",
        "archive_file_digest_match",
        "package_archive_digest_attestation_audit_report_digest"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
