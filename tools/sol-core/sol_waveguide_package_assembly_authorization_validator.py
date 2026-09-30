# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Authorization Validator / Preflight Authorization Auditor.
Reloads the authorization envelope and final readiness report strictly as metadata.
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
from sol_waveguide_distribution_package_manifest_validator import (
    validate_waveguide_final_package_readiness_audit_report
)
from sol_waveguide_package_assembly_authorization_envelope import (
    validate_waveguide_package_assembly_authorization_envelope,
    hash_waveguide_package_assembly_authorization_envelope
)


@dataclass
class WaveguidePackagePreflightAuthorizationAuditCase:
    preflight_authorization_case_id: str
    package_assembly_authorization_envelope_id: str
    package_assembly_authorization_envelope_path: str
    authorization_envelope_digest_recorded: str
    authorization_envelope_digest_recomputed: str
    authorization_envelope_digest_match: bool
    authorization_status: str
    authorization_decision: str
    preflight_authorization_status: str  # preflight_authorization_verified, etc.
    source_final_package_readiness_report_digest_recorded: str
    source_final_package_readiness_report_digest_recomputed: str
    source_final_package_readiness_report_digest_match: bool
    source_final_package_readiness_report_valid: bool
    source_final_package_readiness_status: str
    verified_final_package_count: int
    blocked_final_package_count: int
    pending_final_package_count: int
    invalid_final_package_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    metadata_only_authorization: bool
    future_operation_authorized: bool
    archive_creation_authorized: bool
    file_copy_authorized: bool
    directory_creation_authorized: bool
    upload_authorized: bool
    deployment_authorized: bool
    signing_authorized: bool
    external_publication_authorized: bool
    production_mutation_authorized: bool
    blocked_operation_attempt_counts: Dict[str, int]
    authorization_constraints_verified: bool
    authorization_allowances_verified: bool
    authorization_prohibitions_verified: bool
    authorization_boolean_matrix_verified: bool
    blocked_operation_counts_verified: bool
    no_archive_creation_authorized: bool
    no_file_copy_authorized: bool
    no_directory_creation_authorized: bool
    no_upload_authorized: bool
    no_deployment_authorized: bool
    no_signing_authorized: bool
    no_external_publication_authorized: bool
    no_production_mutation_authorized: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    preflight_authorization_case_digest: str = ""


@dataclass
class WaveguidePackagePreflightAuthorizationAuditReport:
    preflight_authorization_report_id: str
    preflight_authorization_report_version: int
    preflight_authorization_report_status: str  # package_preflight_authorization_verified, etc.
    source_authorization_envelope_digest: str
    source_final_package_readiness_report_digest: str
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    audited_cases: List[WaveguidePackagePreflightAuthorizationAuditCase]
    verified_preflight_cases: List[str]
    blocked_preflight_cases: List[str]
    warning_preflight_cases: List[str]
    invalid_preflight_cases: List[str]
    verified_preflight_count: int
    blocked_preflight_count: int
    warning_preflight_count: int
    invalid_preflight_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    authorized_target_package_sections: List[str]
    authorized_package_roles: List[str]
    authorized_artifact_types: List[str]
    authorized_artifact_formats: List[str]
    authorized_source_artifact_paths: List[str]
    authorized_target_package_paths: List[str]
    authorized_source_artifact_digests: List[str]
    authorized_layout_entry_digests: List[str]
    authorized_dry_run_case_digests: List[str]
    authorized_package_content_entry_digests: List[str]
    authorized_final_package_audit_case_digests: List[str]
    authorization_constraints: List[str]
    authorization_allowances: List[str]
    authorization_prohibitions: List[str]
    authorization_boolean_matrix_verified: bool
    blocked_operation_attempt_counts: Dict[str, int]
    archive_creation_authorized: bool
    file_copy_authorized: bool
    directory_creation_authorized: bool
    upload_authorized: bool
    deployment_authorized: bool
    signing_authorized: bool
    external_publication_authorized: bool
    production_mutation_authorized: bool
    archive_creation_attempt_count: int
    file_copy_attempt_count: int
    directory_creation_attempt_count: int
    upload_attempt_count: int
    deployment_attempt_count: int
    signing_attempt_count: int
    external_publication_attempt_count: int
    production_mutation_attempt_count: int
    metadata_only_authorization_verified: bool
    future_operation_authorization_verified: bool
    reason_codes: List[str]
    software_validation_caveat: str
    preflight_authorization_report_digest: str = ""


def hash_waveguide_package_preflight_authorization_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of case excluding case digest.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or a dataclass instance")

    c_dict_copy = dict(c_dict)
    c_dict_copy.pop("preflight_authorization_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_package_preflight_authorization_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of report excluding report digest.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("preflight_authorization_report_digest", None)
    return hash_data(r_dict_copy)


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


def recompute_waveguide_package_assembly_authorization_envelope_digest(
    envelope_path_or_dict: Any
) -> str:
    """
    Recomputes the envelope digest.
    """
    env_dict = _load_dict(envelope_path_or_dict)
    if env_dict:
        return hash_waveguide_package_assembly_authorization_envelope(env_dict)
    return ""


def validate_waveguide_package_authorization_boolean_matrix(envelope_dict: Dict[str, Any]) -> bool:
    """
    Validates the boolean matrix of authorization states.
    """
    return (
        envelope_dict.get("metadata_only_authorization") is True and
        envelope_dict.get("archive_creation_authorized") is False and
        envelope_dict.get("file_copy_authorized") is False and
        envelope_dict.get("directory_creation_authorized") is False and
        envelope_dict.get("upload_authorized") is False and
        envelope_dict.get("deployment_authorized") is False and
        envelope_dict.get("signing_authorized") is False and
        envelope_dict.get("external_publication_authorized") is False and
        envelope_dict.get("production_mutation_authorized") is False
    )


def validate_waveguide_package_authorization_constraints(constraints: List[str]) -> bool:
    """
    Validates presence of required constraints.
    """
    expected = [
        "metadata_only", "non_mutating", "sandbox_validation_only", "future_operation_only",
        "requires_preflight_authorization_audit", "requires_no_archive_creation", "requires_no_file_copy",
        "requires_no_directory_creation", "requires_no_upload", "requires_no_deployment",
        "requires_no_signing", "requires_no_external_publication", "requires_no_production_mutation"
    ]
    return all(item in constraints for item in expected)


def validate_waveguide_package_authorization_allowances(allowances: List[str]) -> bool:
    """
    Validates presence of required allowances.
    """
    expected = [
        "future_package_assembly_may_be_requested",
        "future_package_assembly_requires_preflight_validation",
        "future_package_assembly_requires_same_manifest_digest",
        "future_package_assembly_requires_same_final_readiness_digest",
        "future_package_assembly_requires_zero_blocked_operation_attempts"
    ]
    return all(item in allowances for item in expected)


def validate_waveguide_package_authorization_prohibitions(prohibitions: List[str]) -> bool:
    """
    Validates presence of required prohibitions.
    """
    expected = [
        "no_archive_creation_by_authorization_envelope",
        "no_file_copy_by_authorization_envelope",
        "no_directory_creation_by_authorization_envelope",
        "no_upload_by_authorization_envelope",
        "no_deployment_by_authorization_envelope",
        "no_signing_by_authorization_envelope",
        "no_external_publication_by_authorization_envelope",
        "no_production_mutation_by_authorization_envelope"
    ]
    return all(item in prohibitions for item in expected)


def validate_waveguide_package_authorization_blocked_operation_counts(counts: Dict[str, int]) -> bool:
    """
    Validates all blocked operation counters remain zero.
    """
    expected_ops = [
        "archive_creation", "file_copy", "directory_creation",
        "upload", "deployment", "external_signing",
        "external_publication", "production_mutation"
    ]
    for op in expected_ops:
        if counts.get(op, -1) != 0:
            if op == "external_signing" and counts.get("signing", -1) == 0:
                continue
            return False
    return True


def build_waveguide_package_preflight_authorization_audit_case(
    envelope_path_or_dict: Any,
    report_path_or_dict: Any
) -> WaveguidePackagePreflightAuthorizationAuditCase:
    """
    Builds a preflight authorization audit case validating an envelope.
    """
    env_dict = _load_dict(envelope_path_or_dict) or {}
    report_dict = _load_dict(report_path_or_dict) or {}

    envelope_path = envelope_path_or_dict if isinstance(envelope_path_or_dict, str) else ""

    # Envelope digest checks
    env_digest_recorded = env_dict.get("package_assembly_authorization_envelope_digest", "")
    env_digest_recomputed = recompute_waveguide_package_assembly_authorization_envelope_digest(env_dict)
    env_digest_match = (env_digest_recorded == env_digest_recomputed) and (env_digest_recorded != "")

    # Report digest checks
    report_digest_recorded = env_dict.get("source_final_package_readiness_report_digest", "")
    report_digest_recomputed = report_dict.get("final_package_readiness_report_digest", "")
    report_digest_match = (report_digest_recorded == report_digest_recomputed) and (report_digest_recorded != "")

    # Validate report
    report_valid = False
    if report_dict:
        report_valid, _ = validate_waveguide_final_package_readiness_audit_report(report_dict)

    # Boolean matrix
    boolean_matrix_verified = validate_waveguide_package_authorization_boolean_matrix(env_dict)

    # Constraints / allowances / prohibitions
    constraints_verified = validate_waveguide_package_authorization_constraints(env_dict.get("authorization_constraints", []))
    allowances_verified = validate_waveguide_package_authorization_allowances(env_dict.get("authorization_allowances", []))
    prohibitions_verified = validate_waveguide_package_authorization_prohibitions(env_dict.get("authorization_prohibitions", []))

    # Blocked operation attempt counts
    blocked_counts = env_dict.get("blocked_operation_attempt_counts", {})
    blocked_counts_verified = validate_waveguide_package_authorization_blocked_operation_counts(blocked_counts)

    # Individual flags
    no_archive = env_dict.get("archive_creation_authorized") is False
    no_copy = env_dict.get("file_copy_authorized") is False
    no_dir = env_dict.get("directory_creation_authorized") is False
    no_upload = env_dict.get("upload_authorized") is False
    no_deploy = env_dict.get("deployment_authorized") is False
    no_sign = env_dict.get("signing_authorized") is False
    no_pub = env_dict.get("external_publication_authorized") is False
    no_mutate = env_dict.get("production_mutation_authorized") is False

    reason_codes = [
        "PREFLIGHT_AUTH_CASE_CANONICAL",
        "PREFLIGHT_AUTH_ARCHIVE_CREATION_PROHIBITED",
        "PREFLIGHT_AUTH_FILE_COPY_PROHIBITED",
        "PREFLIGHT_AUTH_DIRECTORY_CREATION_PROHIBITED",
        "PREFLIGHT_AUTH_UPLOAD_PROHIBITED",
        "PREFLIGHT_AUTH_DEPLOYMENT_PROHIBITED",
        "PREFLIGHT_AUTH_SIGNING_PROHIBITED",
        "PREFLIGHT_AUTH_EXTERNAL_PUBLICATION_PROHIBITED",
        "PREFLIGHT_AUTH_PRODUCTION_MUTATION_PROHIBITED"
    ]

    if env_dict:
        reason_codes.append("PREFLIGHT_AUTH_ENVELOPE_LOADED")
    if env_digest_match:
        reason_codes.append("PREFLIGHT_AUTH_ENVELOPE_DIGEST_MATCH")
    else:
        reason_codes.append("PREFLIGHT_AUTH_ENVELOPE_DIGEST_MISMATCH")

    if report_valid:
        reason_codes.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_VALID")
    else:
        reason_codes.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_INVALID")

    if report_digest_match:
        reason_codes.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_DIGEST_MATCH")
    else:
        reason_codes.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_DIGEST_MISMATCH")

    if env_dict.get("authorization_status") == "package_assembly_authorized":
        reason_codes.append("PREFLIGHT_AUTH_STATUS_AUTHORIZED")
    if env_dict.get("authorization_decision") == "authorize_metadata_only_future_assembly":
        reason_codes.append("PREFLIGHT_AUTH_DECISION_METADATA_ONLY_FUTURE_ASSEMBLY")

    v_count = env_dict.get("verified_final_package_count", 0)
    b_count = env_dict.get("blocked_final_package_count", 0)
    p_count = env_dict.get("pending_final_package_count", 0)
    i_count = env_dict.get("invalid_final_package_count", 0)
    total_authorized = env_dict.get("total_authorized_file_count", 0)

    # Check counts match
    report_v_count = report_dict.get("verified_final_package_count", 0)
    counts_valid = (
        v_count == report_v_count and
        v_count > 0 and
        b_count == 0 and
        p_count == 0 and
        i_count == 0 and
        total_authorized == v_count
    )

    if counts_valid:
        reason_codes.append("PREFLIGHT_AUTH_VERIFIED_COUNT_VALID")
        reason_codes.append("PREFLIGHT_AUTH_BLOCKED_COUNT_ZERO")
        reason_codes.append("PREFLIGHT_AUTH_PENDING_COUNT_ZERO")
        reason_codes.append("PREFLIGHT_AUTH_INVALID_COUNT_ZERO")
        reason_codes.append("PREFLIGHT_AUTH_AUTHORIZED_FILE_COUNT_VALID")

    # Check RC counts
    rc1_valid = env_dict.get("rc1_authorized_file_count") == report_dict.get("rc1_final_package_count")
    rc2_valid = env_dict.get("rc2_authorized_file_count") == report_dict.get("rc2_final_package_count")
    shared_valid = env_dict.get("shared_authorized_file_count") == report_dict.get("shared_final_package_count")
    if rc1_valid and rc2_valid and shared_valid:
        reason_codes.append("PREFLIGHT_AUTH_RC_COUNTS_VALID")

    if env_dict.get("metadata_only_authorization") is True:
        reason_codes.append("PREFLIGHT_AUTH_METADATA_ONLY_VERIFIED")
    if env_dict.get("future_operation_authorized") is True:
        reason_codes.append("PREFLIGHT_AUTH_FUTURE_OPERATION_VERIFIED")

    if blocked_counts_verified:
        reason_codes.append("PREFLIGHT_AUTH_BLOCKED_OPERATION_COUNTS_ZERO")
    if constraints_verified:
        reason_codes.append("PREFLIGHT_AUTH_CONSTRAINTS_VERIFIED")
    if allowances_verified:
        reason_codes.append("PREFLIGHT_AUTH_ALLOWANCES_VERIFIED")
    if prohibitions_verified:
        reason_codes.append("PREFLIGHT_AUTH_PROHIBITIONS_VERIFIED")

    caveat = env_dict.get("software_validation_caveat", "")
    if caveat:
        reason_codes.append("PREFLIGHT_AUTH_SOFTWARE_CAVEAT_INCLUDED")

    # Final Preflight Case Status
    preflight_authorization_status = "preflight_authorization_invalid"
    if (env_digest_match and report_digest_match and report_valid and
        env_dict.get("authorization_status") == "package_assembly_authorized" and
        env_dict.get("authorization_decision") == "authorize_metadata_only_future_assembly" and
        counts_valid and rc1_valid and rc2_valid and shared_valid and
        boolean_matrix_verified and constraints_verified and allowances_verified and
        prohibitions_verified and blocked_counts_verified and env_dict.get("future_operation_authorized") is True and
        caveat):
        preflight_authorization_status = "preflight_authorization_verified"
        reason_codes.append("PACKAGE_PREFLIGHT_AUTHORIZATION_VERIFIED")
    elif env_dict.get("authorization_status") == "package_assembly_blocked":
        preflight_authorization_status = "preflight_authorization_blocked"
        reason_codes.append("PACKAGE_PREFLIGHT_AUTHORIZATION_BLOCKED")
    else:
        preflight_authorization_status = "preflight_authorization_invalid"
        reason_codes.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    case_obj = WaveguidePackagePreflightAuthorizationAuditCase(
        preflight_authorization_case_id="SOL-WAVEGUIDE-PREFLIGHT-AUDIT-CASE",
        package_assembly_authorization_envelope_id=env_dict.get("package_assembly_authorization_envelope_id", ""),
        package_assembly_authorization_envelope_path=envelope_path,
        authorization_envelope_digest_recorded=env_digest_recorded,
        authorization_envelope_digest_recomputed=env_digest_recomputed,
        authorization_envelope_digest_match=env_digest_match,
        authorization_status=env_dict.get("authorization_status", ""),
        authorization_decision=env_dict.get("authorization_decision", ""),
        preflight_authorization_status=preflight_authorization_status,
        source_final_package_readiness_report_digest_recorded=report_digest_recorded,
        source_final_package_readiness_report_digest_recomputed=report_digest_recomputed,
        source_final_package_readiness_report_digest_match=report_digest_match,
        source_final_package_readiness_report_valid=report_valid,
        source_final_package_readiness_status=report_dict.get("final_package_readiness_report_status", ""),
        verified_final_package_count=v_count,
        blocked_final_package_count=b_count,
        pending_final_package_count=p_count,
        invalid_final_package_count=i_count,
        total_authorized_file_count=total_authorized,
        rc1_authorized_file_count=env_dict.get("rc1_authorized_file_count", 0),
        rc2_authorized_file_count=env_dict.get("rc2_authorized_file_count", 0),
        shared_authorized_file_count=env_dict.get("shared_authorized_file_count", 0),
        metadata_only_authorization=env_dict.get("metadata_only_authorization", True),
        future_operation_authorized=env_dict.get("future_operation_authorized", False),
        archive_creation_authorized=env_dict.get("archive_creation_authorized", False),
        file_copy_authorized=env_dict.get("file_copy_authorized", False),
        directory_creation_authorized=env_dict.get("directory_creation_authorized", False),
        upload_authorized=env_dict.get("upload_authorized", False),
        deployment_authorized=env_dict.get("deployment_authorized", False),
        signing_authorized=env_dict.get("signing_authorized", False),
        external_publication_authorized=env_dict.get("external_publication_authorized", False),
        production_mutation_authorized=env_dict.get("production_mutation_authorized", False),
        blocked_operation_attempt_counts={
            "archive_creation": blocked_counts.get("archive_creation", 0),
            "file_copy": blocked_counts.get("file_copy", 0),
            "directory_creation": blocked_counts.get("directory_creation", 0),
            "upload": blocked_counts.get("upload", 0),
            "deployment": blocked_counts.get("deployment", 0),
            "external_signing": blocked_counts.get("external_signing", 0) if "external_signing" in blocked_counts else blocked_counts.get("signing", 0),
            "external_publication": blocked_counts.get("external_publication", 0),
            "production_mutation": blocked_counts.get("production_mutation", 0)
        },
        authorization_constraints_verified=constraints_verified,
        authorization_allowances_verified=allowances_verified,
        authorization_prohibitions_verified=prohibitions_verified,
        authorization_boolean_matrix_verified=boolean_matrix_verified,
        blocked_operation_counts_verified=blocked_counts_verified,
        no_archive_creation_authorized=no_archive,
        no_file_copy_authorized=no_copy,
        no_directory_creation_authorized=no_dir,
        no_upload_authorized=no_upload,
        no_deployment_authorized=no_deploy,
        no_signing_authorized=no_sign,
        no_external_publication_authorized=no_pub,
        no_production_mutation_authorized=no_mutate,
        reason_codes=sorted(list(set(reason_codes))),
        notes=[],
        software_validation_caveat=caveat,
        preflight_authorization_case_digest=""
    )
    case_obj.preflight_authorization_case_digest = hash_waveguide_package_preflight_authorization_case(case_obj)
    return case_obj


def validate_waveguide_package_assembly_authorization_envelope_independently(
    envelope_path_or_dict: Any,
    report_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates the envelope and readiness report compatibility.
    """
    env_dict = _load_dict(envelope_path_or_dict)
    report_dict = _load_dict(report_path_or_dict)

    reasons = []
    is_valid = True

    if not env_dict or not report_dict:
        return False, ["PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID"]

    env_ok, env_reasons = validate_waveguide_package_assembly_authorization_envelope(env_dict)
    if not env_ok:
        is_valid = False
        reasons.append("PREFLIGHT_AUTH_ENVELOPE_INVALID")
    else:
        reasons.append("PREFLIGHT_AUTH_ENVELOPE_VALID")

    report_ok, _ = validate_waveguide_final_package_readiness_audit_report(report_dict)
    if not report_ok:
        is_valid = False
        reasons.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_INVALID")
    else:
        reasons.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_VALID")

    # Check digest matching
    env_report_digest = env_dict.get("source_final_package_readiness_report_digest", "")
    r_digest = report_dict.get("final_package_readiness_report_digest", "")
    if env_report_digest != r_digest or not r_digest:
        is_valid = False
        reasons.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_DIGEST_MISMATCH")
    else:
        reasons.append("PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_DIGEST_MATCH")

    if is_valid:
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_VERIFIED")
    else:
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_preflight_authorization_audit_report(
    envelope_path_or_dict: Any,
    report_path_or_dict: Any
) -> WaveguidePackagePreflightAuthorizationAuditReport:
    """
    Builds the top-level preflight authorization audit report.
    """
    env_dict = _load_dict(envelope_path_or_dict)
    report_dict = _load_dict(report_path_or_dict)

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not env_dict or not report_dict:
        report = WaveguidePackagePreflightAuthorizationAuditReport(
            preflight_authorization_report_id="SOL-WAVEGUIDE-PACKAGE-PREFLIGHT-AUTHORIZATION-AUDIT-REPORT",
            preflight_authorization_report_version=1,
            preflight_authorization_report_status="package_preflight_authorization_invalid",
            source_authorization_envelope_digest="",
            source_final_package_readiness_report_digest="",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            audited_cases=[],
            verified_preflight_cases=[],
            blocked_preflight_cases=[],
            warning_preflight_cases=[],
            invalid_preflight_cases=[],
            verified_preflight_count=0,
            blocked_preflight_count=0,
            warning_preflight_count=0,
            invalid_preflight_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            authorized_target_package_sections=[],
            authorized_package_roles=[],
            authorized_artifact_types=[],
            authorized_artifact_formats=[],
            authorized_source_artifact_paths=[],
            authorized_target_package_paths=[],
            authorized_source_artifact_digests=[],
            authorized_layout_entry_digests=[],
            authorized_dry_run_case_digests=[],
            authorized_package_content_entry_digests=[],
            authorized_final_package_audit_case_digests=[],
            authorization_constraints=[],
            authorization_allowances=[],
            authorization_prohibitions=[],
            authorization_boolean_matrix_verified=False,
            blocked_operation_attempt_counts={
                "archive_creation": 0, "file_copy": 0, "directory_creation": 0,
                "upload": 0, "deployment": 0, "external_signing": 0,
                "external_publication": 0, "production_mutation": 0
            },
            archive_creation_authorized=False,
            file_copy_authorized=False,
            directory_creation_authorized=False,
            upload_authorized=False,
            deployment_authorized=False,
            signing_authorized=False,
            external_publication_authorized=False,
            production_mutation_authorized=False,
            archive_creation_attempt_count=0,
            file_copy_attempt_count=0,
            directory_creation_attempt_count=0,
            upload_attempt_count=0,
            deployment_attempt_count=0,
            signing_attempt_count=0,
            external_publication_attempt_count=0,
            production_mutation_attempt_count=0,
            metadata_only_authorization_verified=False,
            future_operation_authorization_verified=False,
            reason_codes=["PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID"],
            software_validation_caveat=caveat,
            preflight_authorization_report_digest=""
        )
        report.preflight_authorization_report_digest = hash_waveguide_package_preflight_authorization_report(report)
        return report

    case = build_waveguide_package_preflight_authorization_audit_case(env_dict, report_dict)
    cases = [case]

    verified_cases = []
    blocked_cases = []
    warning_cases = []
    invalid_cases = []

    case_id = case.preflight_authorization_case_id
    if case.preflight_authorization_status == "preflight_authorization_verified":
        verified_cases.append(case_id)
    elif case.preflight_authorization_status == "preflight_authorization_blocked":
        blocked_cases.append(case_id)
    elif case.preflight_authorization_status == "preflight_authorization_warning":
        warning_cases.append(case_id)
    else:
        invalid_cases.append(case_id)

    # Sorting all lists
    authorized_sections = sorted(env_dict.get("authorized_target_package_sections", []))
    authorized_roles = sorted(env_dict.get("authorized_package_roles", []))
    authorized_types = sorted(env_dict.get("authorized_artifact_types", []))
    authorized_formats = sorted(env_dict.get("authorized_artifact_formats", []))
    authorized_src_paths = sorted(env_dict.get("authorized_source_artifact_paths", []))
    authorized_tgt_paths = sorted(env_dict.get("authorized_target_package_paths", []))
    authorized_src_digs = sorted(env_dict.get("authorized_source_artifact_digests", []))
    authorized_layout_digs = sorted(env_dict.get("authorized_layout_entry_digests", []))
    authorized_case_digs = sorted(env_dict.get("authorized_dry_run_case_digests", []))
    authorized_content_digs = sorted(env_dict.get("authorized_package_content_entry_digests", []))
    authorized_audit_digs = sorted(env_dict.get("authorized_final_package_audit_case_digests", []))

    all_reasons = [
        "PREFLIGHT_AUTH_REPORT_DIGEST_VALID"
    ]
    for c in cases:
        for rc in c.reason_codes:
            if rc not in all_reasons:
                all_reasons.append(rc)

    ind_ok, ind_reasons = validate_waveguide_package_assembly_authorization_envelope_independently(env_dict, report_dict)
    for rc in ind_reasons:
        if rc not in all_reasons:
            all_reasons.append(rc)

    blocked_counts = env_dict.get("blocked_operation_attempt_counts", {})
    blocked_verified = validate_waveguide_package_authorization_blocked_operation_counts(blocked_counts)

    if (len(blocked_cases) > 0 or len(invalid_cases) > 0 or not ind_ok or not blocked_verified or
        not case.authorization_constraints_verified or not case.authorization_allowances_verified or
        not case.authorization_prohibitions_verified or not case.authorization_boolean_matrix_verified):
        report_status = "package_preflight_authorization_invalid"
        all_reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")
    else:
        report_status = "package_preflight_authorization_verified"
        all_reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_VERIFIED")

    report = WaveguidePackagePreflightAuthorizationAuditReport(
        preflight_authorization_report_id="SOL-WAVEGUIDE-PACKAGE-PREFLIGHT-AUTHORIZATION-AUDIT-REPORT",
        preflight_authorization_report_version=1,
        preflight_authorization_report_status=report_status,
        source_authorization_envelope_digest=env_dict.get("package_assembly_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=env_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=env_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=env_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=env_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=env_dict.get("source_artifact_catalog_digest", ""),
        audited_cases=cases,
        verified_preflight_cases=sorted(verified_cases),
        blocked_preflight_cases=sorted(blocked_cases),
        warning_preflight_cases=sorted(warning_cases),
        invalid_preflight_cases=sorted(invalid_cases),
        verified_preflight_count=len(verified_cases),
        blocked_preflight_count=len(blocked_cases),
        warning_preflight_count=len(warning_cases),
        invalid_preflight_count=len(invalid_cases),
        total_authorized_file_count=env_dict.get("total_authorized_file_count", 0),
        rc1_authorized_file_count=env_dict.get("rc1_authorized_file_count", 0),
        rc2_authorized_file_count=env_dict.get("rc2_authorized_file_count", 0),
        shared_authorized_file_count=env_dict.get("shared_authorized_file_count", 0),
        authorized_target_package_sections=authorized_sections,
        authorized_package_roles=authorized_roles,
        authorized_artifact_types=authorized_types,
        authorized_artifact_formats=authorized_formats,
        authorized_source_artifact_paths=authorized_src_paths,
        authorized_target_package_paths=authorized_tgt_paths,
        authorized_source_artifact_digests=authorized_src_digs,
        authorized_layout_entry_digests=authorized_layout_digs,
        authorized_dry_run_case_digests=authorized_case_digs,
        authorized_package_content_entry_digests=authorized_content_digs,
        authorized_final_package_audit_case_digests=authorized_audit_digs,
        authorization_constraints=sorted(env_dict.get("authorization_constraints", [])),
        authorization_allowances=sorted(env_dict.get("authorization_allowances", [])),
        authorization_prohibitions=sorted(env_dict.get("authorization_prohibitions", [])),
        authorization_boolean_matrix_verified=case.authorization_boolean_matrix_verified,
        blocked_operation_attempt_counts={
            "archive_creation": blocked_counts.get("archive_creation", 0),
            "file_copy": blocked_counts.get("file_copy", 0),
            "directory_creation": blocked_counts.get("directory_creation", 0),
            "upload": blocked_counts.get("upload", 0),
            "deployment": blocked_counts.get("deployment", 0),
            "external_signing": blocked_counts.get("external_signing", 0) if "external_signing" in blocked_counts else blocked_counts.get("signing", 0),
            "external_publication": blocked_counts.get("external_publication", 0),
            "production_mutation": blocked_counts.get("production_mutation", 0)
        },
        archive_creation_authorized=env_dict.get("archive_creation_authorized", False),
        file_copy_authorized=env_dict.get("file_copy_authorized", False),
        directory_creation_authorized=env_dict.get("directory_creation_authorized", False),
        upload_authorized=env_dict.get("upload_authorized", False),
        deployment_authorized=env_dict.get("deployment_authorized", False),
        signing_authorized=env_dict.get("signing_authorized", False),
        external_publication_authorized=env_dict.get("external_publication_authorized", False),
        production_mutation_authorized=env_dict.get("production_mutation_authorized", False),
        archive_creation_attempt_count=blocked_counts.get("archive_creation", 0),
        file_copy_attempt_count=blocked_counts.get("file_copy", 0),
        directory_creation_attempt_count=blocked_counts.get("directory_creation", 0),
        upload_attempt_count=blocked_counts.get("upload", 0),
        deployment_attempt_count=blocked_counts.get("deployment", 0),
        signing_attempt_count=blocked_counts.get("external_signing", 0) if "external_signing" in blocked_counts else blocked_counts.get("signing", 0),
        external_publication_attempt_count=blocked_counts.get("external_publication", 0),
        production_mutation_attempt_count=blocked_counts.get("production_mutation", 0),
        metadata_only_authorization_verified=env_dict.get("metadata_only_authorization", False),
        future_operation_authorization_verified=env_dict.get("future_operation_authorized", False),
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=caveat,
        preflight_authorization_report_digest=""
    )
    report.preflight_authorization_report_digest = hash_waveguide_package_preflight_authorization_report(report)
    return report


def validate_waveguide_package_preflight_authorization_audit_report(
    report: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a preflight authorization audit report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    reasons = []
    is_valid = True

    # 1. Digest check
    given_digest = r_dict.get("preflight_authorization_report_digest")
    if not given_digest:
        is_valid = False
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")
    else:
        recomputed = hash_waveguide_package_preflight_authorization_report(r_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")
        else:
            reasons.append("PREFLIGHT_AUTH_REPORT_DIGEST_VALID")

    # 2. Case digest check
    cases = r_dict.get("audited_cases", [])
    case_statuses = []
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        given_c_digest = c_dict.get("preflight_authorization_case_digest")
        if not given_c_digest:
            is_valid = False
            reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")
        else:
            recomputed_c = hash_waveguide_package_preflight_authorization_case(c_dict)
            if recomputed_c != given_c_digest:
                is_valid = False
                reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")
            else:
                reasons.append("PREFLIGHT_AUTH_CASE_DIGEST_VALID")

        status = c_dict.get("preflight_authorization_status")
        case_statuses.append(status)

        if status == "preflight_authorization_verified":
            if (not c_dict.get("authorization_envelope_digest_match") or
                not c_dict.get("source_final_package_readiness_report_digest_match") or
                not c_dict.get("source_final_package_readiness_report_valid") or
                not c_dict.get("authorization_constraints_verified") or
                not c_dict.get("authorization_allowances_verified") or
                not c_dict.get("authorization_prohibitions_verified") or
                not c_dict.get("authorization_boolean_matrix_verified") or
                not c_dict.get("blocked_operation_counts_verified") or
                c_dict.get("future_operation_authorized") is not True):
                is_valid = False
                reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    # 3. Counts match checks
    v_count = r_dict.get("verified_preflight_count", 0)
    b_count = r_dict.get("blocked_preflight_count", 0)
    w_count = r_dict.get("warning_preflight_count", 0)
    i_count = r_dict.get("invalid_preflight_count", 0)

    if (v_count != case_statuses.count("preflight_authorization_verified") or
        b_count != case_statuses.count("preflight_authorization_blocked") or
        w_count != case_statuses.count("preflight_authorization_warning") or
        i_count != case_statuses.count("preflight_authorization_invalid")):
        is_valid = False
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    # 4. Status check
    report_status = r_dict.get("preflight_authorization_report_status")
    if report_status == "package_preflight_authorization_verified":
        if b_count > 0 or i_count > 0 or len(cases) == 0:
            is_valid = False
            reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    # 5. Structure verifications flags
    if not r_dict.get("authorization_boolean_matrix_verified"):
        is_valid = False
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    # 6. Blocked operation counts must be zero
    blocked_counts = r_dict.get("blocked_operation_attempt_counts", {})
    if not validate_waveguide_package_authorization_blocked_operation_counts(blocked_counts):
        is_valid = False
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    if is_valid:
        for code in r_dict.get("reason_codes", []):
            if code.startswith("PREFLIGHT_AUTH_") or code.startswith("PACKAGE_PREFLIGHT_"):
                reasons.append(code)
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_VERIFIED")
    else:
        reasons.append("PACKAGE_PREFLIGHT_AUTHORIZATION_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_preflight_authorization_audit_report(report: Any) -> str:
    """
    Returns a plaintext summary of the report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    lines = [
        "============================================================",
        "      SOL WAVEGUIDE PACKAGE PREFLIGHT AUTHORIZATION REPORT",
        "============================================================",
        f"Report ID:          {r_dict.get('preflight_authorization_report_id')}",
        f"Version:            {r_dict.get('preflight_authorization_report_version')}",
        f"Status:             {r_dict.get('preflight_authorization_report_status', '').upper()}",
        f"Report Digest:      {r_dict.get('preflight_authorization_report_digest')}",
        "------------------------------------------------------------",
        "Verified Cases:"
    ]
    for c in r_dict.get("audited_cases", []):
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        lines.append(
            f"  * Envelope ID: {c_dict.get('package_assembly_authorization_envelope_id')} "
            f"({c_dict.get('preflight_authorization_status')})"
        )
    lines.append("------------------------------------------------------------")
    lines.append("Structure Verifications:")
    lines.append(f"  - Boolean matrix:        {'VERIFIED' if r_dict.get('authorization_boolean_matrix_verified') else 'FAILED'}")
    lines.append(f"  - Metadata-only flag:    {'VERIFIED' if r_dict.get('metadata_only_authorization_verified') else 'FAILED'}")
    lines.append(f"  - Future-operation flag: {'VERIFIED' if r_dict.get('future_operation_authorization_verified') else 'FAILED'}")
    lines.append("------------------------------------------------------------")
    lines.append("Enforced Prohibitions (All must be False):")
    lines.append(f"  - archive_creation:      {r_dict.get('archive_creation_authorized')}")
    lines.append(f"  - file_copy:             {r_dict.get('file_copy_authorized')}")
    lines.append(f"  - directory_creation:    {r_dict.get('directory_creation_authorized')}")
    lines.append(f"  - upload:                {r_dict.get('upload_authorized')}")
    lines.append(f"  - deployment:            {r_dict.get('deployment_authorized')}")
    lines.append(f"  - signing:               {r_dict.get('signing_authorized')}")
    lines.append(f"  - external_publication:  {r_dict.get('external_publication_authorized')}")
    lines.append(f"  - production_mutation:   {r_dict.get('production_mutation_authorized')}")
    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in r_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")
    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("==================================================")
    return "\n".join(lines)


def export_waveguide_package_preflight_authorization_audit_report(
    report: Any,
    filepath: str
) -> None:
    """
    Exports the report to a sorted JSON file.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_preflight_authorization_audit_reports(
    left: Any,
    right: Any
) -> Dict[str, Any]:
    """
    Compares two preflight reports.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)
    diff = {
        "report_id_match": l_dict.get("preflight_authorization_report_id") == r_dict.get("preflight_authorization_report_id"),
        "report_status_match": l_dict.get("preflight_authorization_report_status") == r_dict.get("preflight_authorization_report_status"),
        "report_digest_match": l_dict.get("preflight_authorization_report_digest") == r_dict.get("preflight_authorization_report_digest"),
        "verified_count_diff": l_dict.get("verified_preflight_count", 0) - r_dict.get("verified_preflight_count", 0)
    }
    diff["all_match"] = (
        diff["report_id_match"] and
        diff["report_status_match"] and
        diff["report_digest_match"] and
        diff["verified_count_diff"] == 0
    )
    return diff


def index_waveguide_preflight_authorization_cases_by_status(
    cases: List[Any]
) -> Dict[str, List[Any]]:
    """
    Indexes cases by status.
    """
    idx = {}
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        status = c_dict.get("preflight_authorization_status")
        if status not in idx:
            idx[status] = []
        idx[status].append(c_dict)
    return idx


def index_waveguide_preflight_authorization_cases_by_constraint(
    cases: List[Any]
) -> Dict[str, List[Any]]:
    """
    Indexes cases by constraints.
    """
    idx = {}
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        # We index this case under all envelope constraints
        # Normally a case only has one envelope, but let's be robust
        env_dict = _load_dict(c_dict.get("package_assembly_authorization_envelope_path")) or {}
        constraints = env_dict.get("authorization_constraints", [])
        for constraint in constraints:
            if constraint not in idx:
                idx[constraint] = []
            idx[constraint].append(c_dict)
    return idx
