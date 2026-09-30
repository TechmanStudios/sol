# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Run Authorization Validator / Run Preflight Auditor.
Independently verifies the specific run authorization capsule strictly as metadata.
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
from sol_waveguide_package_assembly_execution_plan_validator import (
    validate_waveguide_package_execution_readiness_audit_report,
    hash_waveguide_package_execution_readiness_audit_report
)
from sol_waveguide_package_assembly_run_authorization_capsule import (
    validate_waveguide_package_assembly_run_authorization_capsule,
    hash_waveguide_package_assembly_run_authorization_capsule
)


@dataclass
class WaveguidePackageRunPreflightAuditCase:
    run_preflight_case_id: str
    package_assembly_run_authorization_capsule_id: str
    package_assembly_run_authorization_capsule_path: str
    run_authorization_capsule_digest_recorded: str
    run_authorization_capsule_digest_recomputed: str
    run_authorization_capsule_digest_match: bool
    run_request_id: str
    run_request_kind: str
    run_authorization_status: str
    run_authorization_decision: str
    run_preflight_status: str  # package_run_preflight_verified, etc.
    source_execution_readiness_report_digest_recorded: str
    source_execution_readiness_report_digest_recomputed: str
    source_execution_readiness_report_digest_match: bool
    source_execution_readiness_report_valid: bool
    source_execution_readiness_report_status: str
    verified_execution_readiness_case_count: int
    blocked_execution_readiness_case_count: int
    warning_execution_readiness_case_count: int
    invalid_execution_readiness_case_count: int
    planned_execution_step_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    specific_future_run_authorized: bool
    metadata_only_run_authorization: bool
    physical_execution_authorized: bool
    archive_creation_authorized: bool
    file_copy_authorized: bool
    directory_creation_authorized: bool
    upload_authorized: bool
    deployment_authorized: bool
    signing_authorized: bool
    external_publication_authorized: bool
    production_mutation_authorized: bool
    physical_execution_performed: bool
    archive_creation_performed: bool
    file_copy_performed: bool
    directory_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    run_constraints_verified: bool
    run_allowances_verified: bool
    run_prohibitions_verified: bool
    run_guard_requirements_verified: bool
    run_noop_boundary_verified: bool
    rollback_noop_policy_verified: bool
    run_boolean_matrix_verified: bool
    blocked_operation_counts_verified: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    run_preflight_case_digest: str = ""


@dataclass
class WaveguidePackageRunPreflightAuditReport:
    run_preflight_report_id: str
    run_preflight_report_version: int
    run_preflight_report_status: str  # package_run_preflight_verified, etc.
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
    audited_cases: List[WaveguidePackageRunPreflightAuditCase]
    verified_run_preflight_cases: List[str]
    blocked_run_preflight_cases: List[str]
    warning_run_preflight_cases: List[str]
    invalid_run_preflight_cases: List[str]
    verified_run_preflight_count: int
    blocked_run_preflight_count: int
    warning_run_preflight_count: int
    invalid_run_preflight_count: int
    run_request_id: str
    run_request_kind: str
    run_authorization_status: str
    run_authorization_decision: str
    planned_execution_step_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    authorized_target_package_sections: List[str]
    authorized_execution_step_types: List[str]
    authorized_execution_step_phases: List[str]
    authorized_package_roles: List[str]
    authorized_artifact_types: List[str]
    authorized_rc_scopes: List[str]
    authorized_source_reference_digests: List[str]
    authorized_source_reference_paths: List[str]
    authorized_target_package_paths: List[str]
    authorized_planned_output_references: List[str]
    authorized_execution_step_digests: List[str]
    authorized_execution_readiness_case_digests: List[str]
    run_constraints: List[str]
    run_allowances: List[str]
    run_prohibitions: List[str]
    run_guard_requirements: List[str]
    run_noop_boundary_verified: bool
    rollback_noop_policy_verified: bool
    run_boolean_matrix_verified: bool
    blocked_operation_attempt_counts: Dict[str, int]
    physical_execution_authorized: bool
    archive_creation_authorized: bool
    file_copy_authorized: bool
    directory_creation_authorized: bool
    upload_authorized: bool
    deployment_authorized: bool
    signing_authorized: bool
    external_publication_authorized: bool
    production_mutation_authorized: bool
    physical_execution_performed: bool
    archive_creation_performed: bool
    file_copy_performed: bool
    directory_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    software_validation_caveat: str
    run_preflight_report_digest: str = ""


def hash_waveguide_package_run_preflight_case(case: Any) -> str:
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
    c_dict_copy.pop("run_preflight_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_package_run_preflight_report(report: Any) -> str:
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
    r_dict_copy.pop("run_preflight_report_digest", None)
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


def recompute_waveguide_package_assembly_run_authorization_capsule_digest(
    capsule_path_or_dict: Any
) -> str:
    capsule_dict = _load_dict(capsule_path_or_dict)
    if capsule_dict:
        return hash_waveguide_package_assembly_run_authorization_capsule(capsule_dict)
    return ""


def validate_waveguide_package_run_authorization_boolean_matrix(capsule_dict: Dict[str, Any]) -> bool:
    """
    Verifies authorizations and performed flags are strictly false.
    """
    auth_flags = [
        "physical_execution_authorized", "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized"
    ]
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    return (
        all(capsule_dict.get(flag) is False for flag in auth_flags) and
        all(capsule_dict.get(flag) is False for flag in perf_flags)
    )


def validate_waveguide_package_run_constraints(constraints: List[str]) -> bool:
    expected = [
        "metadata_only_run_authorization", "specific_future_run_only", "non_mutating_authorization",
        "requires_execution_readiness_report_digest_match", "requires_execution_plan_digest_match",
        "requires_preflight_authorization_digest_match", "requires_same_authorized_file_count",
        "requires_same_execution_step_count", "requires_no_archive_creation", "requires_no_file_copy",
        "requires_no_directory_creation", "requires_no_upload", "requires_no_deployment",
        "requires_no_signing", "requires_no_external_publication", "requires_no_production_mutation",
        "requires_separate_run_preflight_audit"
    ]
    return all(c in constraints for c in expected)


def validate_waveguide_package_run_allowances(allowances: List[str]) -> bool:
    expected = [
        "specific_future_package_assembly_run_may_be_requested", "specific_future_run_requires_run_preflight_audit",
        "specific_future_run_requires_same_execution_readiness_digest", "specific_future_run_requires_same_execution_plan_digest",
        "specific_future_run_requires_same_authorized_file_count", "specific_future_run_requires_zero_mutation_attempts"
    ]
    return all(a in allowances for a in expected)


def validate_waveguide_package_run_prohibitions(prohibitions: List[str]) -> bool:
    expected = [
        "no_archive_creation_by_run_authorization_capsule", "no_file_copy_by_run_authorization_capsule",
        "no_directory_creation_by_run_authorization_capsule", "no_upload_by_run_authorization_capsule",
        "no_deployment_by_run_authorization_capsule", "no_signing_by_run_authorization_capsule",
        "no_external_publication_by_run_authorization_capsule", "no_production_mutation_by_run_authorization_capsule"
    ]
    return all(p in prohibitions for p in expected)


def validate_waveguide_package_run_guard_requirements(guards: List[str]) -> bool:
    expected = [
        "source_execution_readiness_report_digest_matches", "source_package_assembly_execution_plan_digest_matches",
        "source_preflight_authorization_report_digest_matches", "source_authorization_envelope_digest_matches",
        "source_final_package_readiness_report_digest_matches", "source_distribution_package_manifest_digest_matches",
        "source_dry_run_audit_report_digest_matches", "source_package_assembly_plan_digest_matches",
        "source_artifact_catalog_digest_matches", "metadata_only_run_boundary_acknowledged",
        "future_runner_requires_separate_run_preflight_audit", "future_runner_requires_no_archive_creation_by_capsule",
        "future_runner_requires_no_file_copy_by_capsule", "future_runner_requires_no_directory_creation_by_capsule",
        "future_runner_requires_no_upload_by_capsule", "future_runner_requires_no_deployment_by_capsule",
        "future_runner_requires_no_signing_by_capsule", "future_runner_requires_no_external_publication_by_capsule",
        "future_runner_requires_no_production_mutation_by_capsule"
    ]
    return all(g in guards for g in expected)


def validate_waveguide_package_run_noop_boundary(noop: Dict[str, bool]) -> bool:
    auth_flags = [
        "physical_execution_authorized", "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized"
    ]
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    return (
        all(noop.get(f) is False for f in auth_flags) and
        all(noop.get(f) is False for f in perf_flags)
    )


def validate_waveguide_package_run_rollback_noop_policy(policy: Dict[str, Any]) -> bool:
    return (
        policy.get("rollback_required") is False and
        policy.get("rollback_reason") == "no_physical_run_performed" and
        policy.get("rollback_scope") == "metadata_only" and
        policy.get("rollback_operations") == []
    )


def validate_waveguide_package_run_blocked_operation_counts(counts: Dict[str, int]) -> bool:
    expected_ops = [
        "archive_creation", "deployment", "directory_creation", "external_publication",
        "external_signing", "file_copy", "production_mutation", "upload"
    ]
    return all(counts.get(op, 0) == 0 for op in expected_ops)


def build_waveguide_package_run_preflight_case(
    capsule_dict: Dict[str, Any],
    readiness_dict: Dict[str, Any]
) -> WaveguidePackageRunPreflightAuditCase:
    """
    Builds a single run-preflight audit case validating the run authorization capsule.
    """
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reasons = ["RUN_AUTH_CAPSULE_CANONICAL"]
    is_valid = True

    # Validate capsule digest
    recorded_digest = capsule_dict.get("package_assembly_run_authorization_capsule_digest", "")
    recomputed_digest = hash_waveguide_package_assembly_run_authorization_capsule(capsule_dict)
    digest_match = (recorded_digest == recomputed_digest) and (recorded_digest != "")
    if digest_match:
        reasons.append("RUN_AUTH_CAPSULE_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("RUN_AUTH_CAPSULE_DIGEST_MISMATCH")

    # Validate readiness report
    is_readiness_valid, _ = validate_waveguide_package_execution_readiness_audit_report(readiness_dict)
    readiness_digest_recorded = capsule_dict.get("source_execution_readiness_report_digest", "")
    readiness_digest_recomputed = hash_waveguide_package_execution_readiness_audit_report(readiness_dict)
    readiness_digest_match = (readiness_digest_recorded == readiness_digest_recomputed) and (readiness_digest_recorded != "")
    
    if not is_readiness_valid or readiness_dict.get("execution_readiness_report_status") != "package_execution_readiness_verified":
        is_valid = False
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID")
    else:
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_VALID")
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_VERIFIED")

    if not readiness_digest_match:
        is_valid = False

    # Check status and decisions
    if capsule_dict.get("run_authorization_status") != "package_run_authorized":
        is_valid = False
    if capsule_dict.get("run_authorization_decision") != "authorize_specific_future_run":
        is_valid = False
    if capsule_dict.get("specific_future_run_authorized") is not True:
        is_valid = False
    if capsule_dict.get("metadata_only_run_authorization") is not True:
        is_valid = False

    # Check matrices, constraints, guard requirements
    noop_boundary = capsule_dict.get("run_noop_boundary", {})
    noop_ok = validate_waveguide_package_run_noop_boundary(noop_boundary)
    policy_ok = validate_waveguide_package_run_rollback_noop_policy(capsule_dict.get("run_rollback_noop_policy", {}))
    counts_ok = validate_waveguide_package_run_blocked_operation_counts(capsule_dict.get("blocked_operation_attempt_counts", {}))
    
    constraints_ok = validate_waveguide_package_run_constraints(capsule_dict.get("run_constraints", []))
    allowances_ok = validate_waveguide_package_run_allowances(capsule_dict.get("run_allowances", []))
    prohibitions_ok = validate_waveguide_package_run_prohibitions(capsule_dict.get("run_prohibitions", []))
    guards_ok = validate_waveguide_package_run_guard_requirements(capsule_dict.get("run_guard_requirements", []))
    boolean_matrix_ok = validate_waveguide_package_run_authorization_boolean_matrix(capsule_dict)

    if not noop_ok or not policy_ok or not counts_ok or not constraints_ok or not allowances_ok or not prohibitions_ok or not guards_ok or not boolean_matrix_ok:
        is_valid = False

    case_status = "package_run_preflight_verified" if is_valid else "package_run_preflight_invalid"
    if is_valid:
        reasons.append("PACKAGE_RUN_AUTHORIZED")
        reasons.append("RUN_AUTH_SPECIFIC_FUTURE_RUN_ALLOWED")
        reasons.append("RUN_AUTH_METADATA_ONLY")

    case = WaveguidePackageRunPreflightAuditCase(
        run_preflight_case_id=f"SOL-WAVEGUIDE-RUN-PREFLIGHT-CASE-{capsule_dict.get('run_request_id', 'UNKNOWN')}",
        package_assembly_run_authorization_capsule_id=capsule_dict.get("package_assembly_run_authorization_capsule_id", ""),
        package_assembly_run_authorization_capsule_path="",
        run_authorization_capsule_digest_recorded=recorded_digest,
        run_authorization_capsule_digest_recomputed=recomputed_digest,
        run_authorization_capsule_digest_match=digest_match,
        run_request_id=capsule_dict.get("run_request_id", ""),
        run_request_kind=capsule_dict.get("run_request_kind", ""),
        run_authorization_status=capsule_dict.get("run_authorization_status", ""),
        run_authorization_decision=capsule_dict.get("run_authorization_decision", ""),
        run_preflight_status=case_status,
        source_execution_readiness_report_digest_recorded=readiness_digest_recorded,
        source_execution_readiness_report_digest_recomputed=readiness_digest_recomputed,
        source_execution_readiness_report_digest_match=readiness_digest_match,
        source_execution_readiness_report_valid=is_readiness_valid,
        source_execution_readiness_report_status=readiness_dict.get("execution_readiness_report_status", ""),
        verified_execution_readiness_case_count=capsule_dict.get("verified_execution_readiness_case_count", 0),
        blocked_execution_readiness_case_count=capsule_dict.get("blocked_execution_readiness_case_count", 0),
        warning_execution_readiness_case_count=capsule_dict.get("warning_execution_readiness_case_count", 0),
        invalid_execution_readiness_case_count=capsule_dict.get("invalid_execution_readiness_case_count", 0),
        planned_execution_step_count=capsule_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=capsule_dict.get("total_authorized_file_count", 0),
        rc1_authorized_file_count=capsule_dict.get("rc1_authorized_file_count", 0),
        rc2_authorized_file_count=capsule_dict.get("rc2_authorized_file_count", 0),
        shared_authorized_file_count=capsule_dict.get("shared_authorized_file_count", 0),
        specific_future_run_authorized=capsule_dict.get("specific_future_run_authorized", False),
        metadata_only_run_authorization=capsule_dict.get("metadata_only_run_authorization", False),
        physical_execution_authorized=capsule_dict.get("physical_execution_authorized", False),
        archive_creation_authorized=capsule_dict.get("archive_creation_authorized", False),
        file_copy_authorized=capsule_dict.get("file_copy_authorized", False),
        directory_creation_authorized=capsule_dict.get("directory_creation_authorized", False),
        upload_authorized=capsule_dict.get("upload_authorized", False),
        deployment_authorized=capsule_dict.get("deployment_authorized", False),
        signing_authorized=capsule_dict.get("signing_authorized", False),
        external_publication_authorized=capsule_dict.get("external_publication_authorized", False),
        production_mutation_authorized=capsule_dict.get("production_mutation_authorized", False),
        physical_execution_performed=capsule_dict.get("physical_execution_performed", False),
        archive_creation_performed=capsule_dict.get("archive_creation_performed", False),
        file_copy_performed=capsule_dict.get("file_copy_performed", False),
        directory_creation_performed=capsule_dict.get("directory_creation_performed", False),
        upload_performed=capsule_dict.get("upload_performed", False),
        deployment_performed=capsule_dict.get("deployment_performed", False),
        signing_performed=capsule_dict.get("signing_performed", False),
        external_publication_performed=capsule_dict.get("external_publication_performed", False),
        production_mutation_performed=capsule_dict.get("production_mutation_performed", False),
        blocked_operation_attempt_counts=capsule_dict.get("blocked_operation_attempt_counts", {}),
        run_constraints_verified=constraints_ok,
        run_allowances_verified=allowances_ok,
        run_prohibitions_verified=prohibitions_ok,
        run_guard_requirements_verified=guards_ok,
        run_noop_boundary_verified=noop_ok,
        rollback_noop_policy_verified=policy_ok,
        run_boolean_matrix_verified=boolean_matrix_ok,
        blocked_operation_counts_verified=counts_ok,
        reason_codes=sorted(list(set(reasons))),
        notes=[],
        software_validation_caveat=caveat
    )
    case.run_preflight_case_digest = hash_waveguide_package_run_preflight_case(case)
    return case


def validate_waveguide_package_assembly_run_authorization_capsule_independently(
    capsule_path_or_dict: Any,
    readiness_report_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates compatibility between run authorization capsule and readiness report.
    """
    capsule_dict = _load_dict(capsule_path_or_dict)
    readiness_dict = _load_dict(readiness_report_path_or_dict)

    reasons = []
    is_valid = True

    if not capsule_dict or not readiness_dict:
        return False, ["PACKAGE_RUN_PREFLIGHT_INVALID"]

    # Validate capsule structure
    capsule_ok, _ = validate_waveguide_package_assembly_run_authorization_capsule(capsule_dict)
    if not capsule_ok:
        is_valid = False
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID")

    # Validate digests
    recorded = capsule_dict.get("source_execution_readiness_report_digest", "")
    recomputed = hash_waveguide_package_execution_readiness_audit_report(readiness_dict)
    if recorded != recomputed or not recorded:
        is_valid = False
        reasons.append("RUN_AUTH_EXECUTION_READINESS_DIGEST_MISMATCH")

    if is_valid:
        reasons.append("PACKAGE_RUN_PREFLIGHT_VERIFIED")
    else:
        reasons.append("PACKAGE_RUN_PREFLIGHT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_run_preflight_audit_report(
    capsule_path_or_dict: Any,
    readiness_report_path_or_dict: Any
) -> WaveguidePackageRunPreflightAuditReport:
    """
    Builds the top-level run preflight audit report.
    """
    capsule_dict = _load_dict(capsule_path_or_dict)
    readiness_dict = _load_dict(readiness_report_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not capsule_dict or not readiness_dict:
        return WaveguidePackageRunPreflightAuditReport(
            run_preflight_report_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-PREFLIGHT-AUDIT-REPORT",
            run_preflight_report_version=1,
            run_preflight_report_status="package_run_preflight_invalid",
            source_run_authorization_capsule_digest="",
            source_execution_readiness_report_digest="",
            source_package_assembly_execution_plan_digest="",
            source_preflight_authorization_report_digest="",
            source_authorization_envelope_digest="",
            source_final_package_readiness_report_digest="",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            audited_cases=[],
            verified_run_preflight_cases=[],
            blocked_run_preflight_cases=[],
            warning_run_preflight_cases=[],
            invalid_run_preflight_cases=[],
            verified_run_preflight_count=0,
            blocked_run_preflight_count=0,
            warning_run_preflight_count=0,
            invalid_run_preflight_count=0,
            run_request_id="SOL-WAVEGUIDE-RUN-REQUEST-UNKNOWN",
            run_request_kind="metadata_only_future_package_assembly_run",
            run_authorization_status="package_run_invalid",
            run_authorization_decision="invalid_run_authorization",
            planned_execution_step_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            authorized_target_package_sections=[],
            authorized_execution_step_types=[],
            authorized_execution_step_phases=[],
            authorized_package_roles=[],
            authorized_artifact_types=[],
            authorized_rc_scopes=[],
            authorized_source_reference_digests=[],
            authorized_source_reference_paths=[],
            authorized_target_package_paths=[],
            authorized_planned_output_references=[],
            authorized_execution_step_digests=[],
            authorized_execution_readiness_case_digests=[],
            run_constraints=[],
            run_allowances=[],
            run_prohibitions=[],
            run_guard_requirements=[],
            run_noop_boundary_verified=False,
            rollback_noop_policy_verified=False,
            run_boolean_matrix_verified=False,
            blocked_operation_attempt_counts={},
            physical_execution_authorized=False,
            archive_creation_authorized=False,
            file_copy_authorized=False,
            directory_creation_authorized=False,
            upload_authorized=False,
            deployment_authorized=False,
            signing_authorized=False,
            external_publication_authorized=False,
            production_mutation_authorized=False,
            physical_execution_performed=False,
            archive_creation_performed=False,
            file_copy_performed=False,
            directory_creation_performed=False,
            upload_performed=False,
            deployment_performed=False,
            signing_performed=False,
            external_publication_performed=False,
            production_mutation_performed=False,
            reason_codes=["RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID", "PACKAGE_RUN_PREFLIGHT_INVALID"],
            software_validation_caveat=caveat
        )

    # Recompute and validate compatibility
    is_compat_ok, compat_reasons = validate_waveguide_package_assembly_run_authorization_capsule_independently(
        capsule_dict, readiness_dict
    )

    # Build cases
    case = build_waveguide_package_run_preflight_case(capsule_dict, readiness_dict)
    cases = [case]

    verified_cases = [c.run_preflight_case_id for c in cases if c.run_preflight_status == "package_run_preflight_verified"]
    blocked_cases = [c.run_preflight_case_id for c in cases if c.run_preflight_status == "package_run_preflight_blocked"]
    warning_cases = [c.run_preflight_case_id for c in cases if c.run_preflight_status == "package_run_preflight_warning"]
    invalid_cases = [c.run_preflight_case_id for c in cases if c.run_preflight_status == "package_run_preflight_invalid"]

    noop_verified = validate_waveguide_package_run_noop_boundary(capsule_dict.get("run_noop_boundary", {}))
    policy_verified = validate_waveguide_package_run_rollback_noop_policy(capsule_dict.get("run_rollback_noop_policy", {}))
    matrix_verified = validate_waveguide_package_run_authorization_boolean_matrix(capsule_dict)

    is_report_ok = (
        is_compat_ok and
        noop_verified and
        policy_verified and
        matrix_verified and
        len(invalid_cases) == 0 and
        len(blocked_cases) == 0
    )

    report_status = "package_run_preflight_verified" if is_report_ok else "package_run_preflight_invalid"

    reasons = ["RUN_AUTH_CAPSULE_CANONICAL"]
    if is_report_ok:
        reasons.append("PACKAGE_RUN_PREFLIGHT_VERIFIED")
    else:
        reasons.append("PACKAGE_RUN_PREFLIGHT_INVALID")

    # Preserve all digests
    report = WaveguidePackageRunPreflightAuditReport(
        run_preflight_report_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-PREFLIGHT-AUDIT-REPORT",
        run_preflight_report_version=1,
        run_preflight_report_status=report_status,
        source_run_authorization_capsule_digest=capsule_dict.get("package_assembly_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=capsule_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=capsule_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=capsule_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=capsule_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=capsule_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=capsule_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=capsule_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=capsule_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=capsule_dict.get("source_artifact_catalog_digest", ""),
        audited_cases=cases,
        verified_run_preflight_cases=verified_cases,
        blocked_run_preflight_cases=blocked_cases,
        warning_run_preflight_cases=warning_cases,
        invalid_run_preflight_cases=invalid_cases,
        verified_run_preflight_count=len(verified_cases),
        blocked_run_preflight_count=len(blocked_cases),
        warning_run_preflight_count=len(warning_cases),
        invalid_run_preflight_count=len(invalid_cases),
        run_request_id=capsule_dict.get("run_request_id", ""),
        run_request_kind=capsule_dict.get("run_request_kind", ""),
        run_authorization_status=capsule_dict.get("run_authorization_status", ""),
        run_authorization_decision=capsule_dict.get("run_authorization_decision", ""),
        planned_execution_step_count=capsule_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=capsule_dict.get("total_authorized_file_count", 0),
        rc1_authorized_file_count=capsule_dict.get("rc1_authorized_file_count", 0),
        rc2_authorized_file_count=capsule_dict.get("rc2_authorized_file_count", 0),
        shared_authorized_file_count=capsule_dict.get("shared_authorized_file_count", 0),
        authorized_target_package_sections=sorted(capsule_dict.get("authorized_target_package_sections", [])),
        authorized_execution_step_types=sorted(capsule_dict.get("authorized_execution_step_types", [])),
        authorized_execution_step_phases=sorted(capsule_dict.get("authorized_execution_step_phases", [])),
        authorized_package_roles=sorted(capsule_dict.get("authorized_package_roles", [])),
        authorized_artifact_types=sorted(capsule_dict.get("authorized_artifact_types", [])),
        authorized_rc_scopes=sorted(capsule_dict.get("authorized_rc_scopes", [])),
        authorized_source_reference_digests=sorted(capsule_dict.get("authorized_source_reference_digests", [])),
        authorized_source_reference_paths=sorted(capsule_dict.get("authorized_source_reference_paths", [])),
        authorized_target_package_paths=sorted(capsule_dict.get("authorized_target_package_paths", [])),
        authorized_planned_output_references=sorted(capsule_dict.get("authorized_planned_output_references", [])),
        authorized_execution_step_digests=sorted(capsule_dict.get("authorized_execution_step_digests", [])),
        authorized_execution_readiness_case_digests=sorted(capsule_dict.get("authorized_execution_readiness_case_digests", [])),
        run_constraints=sorted(capsule_dict.get("run_constraints", [])),
        run_allowances=sorted(capsule_dict.get("run_allowances", [])),
        run_prohibitions=sorted(capsule_dict.get("run_prohibitions", [])),
        run_guard_requirements=sorted(capsule_dict.get("run_guard_requirements", [])),
        run_noop_boundary_verified=noop_verified,
        rollback_noop_policy_verified=policy_verified,
        run_boolean_matrix_verified=matrix_verified,
        blocked_operation_attempt_counts=capsule_dict.get("blocked_operation_attempt_counts", {}),
        physical_execution_authorized=capsule_dict.get("physical_execution_authorized", False),
        archive_creation_authorized=capsule_dict.get("archive_creation_authorized", False),
        file_copy_authorized=capsule_dict.get("file_copy_authorized", False),
        directory_creation_authorized=capsule_dict.get("directory_creation_authorized", False),
        upload_authorized=capsule_dict.get("upload_authorized", False),
        deployment_authorized=capsule_dict.get("deployment_authorized", False),
        signing_authorized=capsule_dict.get("signing_authorized", False),
        external_publication_authorized=capsule_dict.get("external_publication_authorized", False),
        production_mutation_authorized=capsule_dict.get("production_mutation_authorized", False),
        physical_execution_performed=capsule_dict.get("physical_execution_performed", False),
        archive_creation_performed=capsule_dict.get("archive_creation_performed", False),
        file_copy_performed=capsule_dict.get("file_copy_performed", False),
        directory_creation_performed=capsule_dict.get("directory_creation_performed", False),
        upload_performed=capsule_dict.get("upload_performed", False),
        deployment_performed=capsule_dict.get("deployment_performed", False),
        signing_performed=capsule_dict.get("signing_performed", False),
        external_publication_performed=capsule_dict.get("external_publication_performed", False),
        production_mutation_performed=capsule_dict.get("production_mutation_performed", False),
        reason_codes=sorted(list(set(reasons))),
        software_validation_caveat=caveat
    )
    report.run_preflight_report_digest = hash_waveguide_package_run_preflight_report(report)
    return report


def validate_waveguide_package_run_preflight_audit_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Validates a run preflight report structure and recomputed digests.
    """
    report_dict = _load_dict(report)
    if not report_dict:
        return False, ["PACKAGE_RUN_PREFLIGHT_INVALID"]

    reasons = []
    is_valid = True

    if report_dict.get("run_preflight_report_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-PREFLIGHT-AUDIT-REPORT":
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_INVALID_ID")

    if report_dict.get("run_preflight_report_version") != 1:
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_INVALID_VERSION")

    # Validate cases
    cases = report_dict.get("audited_cases", [])
    if not cases:
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_MISSING_CASES")
    else:
        for c in cases:
            recorded = c.get("run_preflight_case_digest", "")
            recomputed = hash_waveguide_package_run_preflight_case(c)
            if recorded != recomputed or not recorded:
                is_valid = False
                reasons.append("RUN_PREFLIGHT_CASE_DIGEST_MISMATCH")

    # Validate matrix and boundary flags
    if report_dict.get("run_noop_boundary_verified") is not True:
        is_valid = False
    if report_dict.get("rollback_noop_policy_verified") is not True:
        is_valid = False
    if report_dict.get("run_boolean_matrix_verified") is not True:
        is_valid = False

    # Check that performed and authorized flags in report are false
    flag_fields = [
        "physical_execution_authorized", "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized",
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in flag_fields:
        if report_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUN_PREFLIGHT_REPORT_MUTATION_PERFORMED_{flag.upper()}")

    # Check report digest
    recorded_digest = report_dict.get("run_preflight_report_digest", "")
    recomputed_digest = hash_waveguide_package_run_preflight_report(report_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_DIGEST_MISMATCH")

    status = report_dict.get("run_preflight_report_status", "")
    if is_valid and status == "package_run_preflight_verified":
        reasons.append("PACKAGE_RUN_PREFLIGHT_VERIFIED")
    else:
        is_valid = False
        reasons.append("PACKAGE_RUN_PREFLIGHT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_run_preflight_audit_report(report: Any) -> str:
    report_dict = _load_dict(report)
    if not report_dict:
        return "Invalid Run Preflight Audit Report"

    status = report_dict.get("run_preflight_report_status", "unknown")
    digest = report_dict.get("run_preflight_report_digest", "")
    run_id = report_dict.get("run_request_id", "")

    return (
        f"SOL Waveguide Run Preflight Audit Report Summary:\n"
        f"  Report Status: {status}\n"
        f"  Run Request ID: {run_id}\n"
        f"  Report Digest: {digest}\n"
        f"  Authorized File Count: {report_dict.get('total_authorized_file_count')}\n"
    )


def export_waveguide_package_run_preflight_audit_report(report: Any, filepath: str) -> None:
    report_dict = _load_dict(report)
    if not report_dict:
        raise ValueError("Cannot export invalid run preflight report data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_run_preflight_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs
