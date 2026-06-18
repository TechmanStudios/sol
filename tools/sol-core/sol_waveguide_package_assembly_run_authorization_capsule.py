# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Run Authorization Capsule.
Consumes the execution-readiness audit report to authorize a specific future run request.
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
    validate_waveguide_package_execution_readiness_audit_report
)


@dataclass
class WaveguidePackageAssemblyRunAuthorizationCapsule:
    package_assembly_run_authorization_capsule_id: str
    package_assembly_run_authorization_capsule_version: int
    run_request_id: str
    run_request_kind: str
    run_authorization_status: str  # package_run_authorized, package_run_blocked, etc.
    run_authorization_decision: str  # authorize_specific_future_run, block_specific_future_run, etc.
    run_authorization_scope: str  # metadata_only
    source_execution_readiness_report_digest: str
    source_package_assembly_execution_plan_digest: str
    source_preflight_authorization_report_digest: str
    source_authorization_envelope_digest: str
    source_final_package_readiness_report_digest: str
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    verified_execution_readiness_case_count: int
    blocked_execution_readiness_case_count: int
    warning_execution_readiness_case_count: int
    invalid_execution_readiness_case_count: int
    planned_execution_step_count: int
    blocked_execution_step_count: int
    warning_execution_step_count: int
    invalid_execution_step_count: int
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
    run_noop_boundary: Dict[str, bool]
    run_rollback_noop_policy: Dict[str, Any]
    blocked_operation_attempt_counts: Dict[str, int]
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
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    package_assembly_run_authorization_capsule_digest: str = ""


def hash_waveguide_package_assembly_run_authorization_capsule(capsule: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of capsule excluding the self-referential digest.
    """
    if hasattr(capsule, "__dict__"):
        c_dict = asdict(capsule)
    elif isinstance(capsule, dict):
        c_dict = dict(capsule)
    else:
        raise TypeError("capsule must be a dictionary or a dataclass instance")

    c_dict_copy = dict(c_dict)
    c_dict_copy.pop("package_assembly_run_authorization_capsule_digest", None)
    return hash_data(c_dict_copy)


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


def build_waveguide_package_assembly_run_request_identity(readiness_report_dict: Dict[str, Any]) -> str:
    """
    Creates a deterministic run request identity based on the report digest.
    """
    digest = readiness_report_dict.get("execution_readiness_report_digest", "")
    if not digest:
        return "SOL-WAVEGUIDE-RUN-REQUEST-UNKNOWN"
    return f"SOL-WAVEGUIDE-RUN-REQUEST-{digest[:16].upper()}"


def build_waveguide_package_assembly_run_authorization_decision(is_valid: bool) -> str:
    """
    Returns the run authorization decision based on validation outcome.
    """
    return "authorize_specific_future_run" if is_valid else "invalid_run_authorization"


def validate_waveguide_package_assembly_run_scope(capsule_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates specific run scope flags to verify it remains metadata-only.
    """
    reasons = []
    is_valid = True

    if capsule_dict.get("run_authorization_scope") != "metadata_only":
        is_valid = False
        reasons.append("RUN_AUTH_SCOPE_INVALID")

    # Authorizations must be False
    auth_flags = [
        "physical_execution_authorized", "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized"
    ]
    for flag in auth_flags:
        if capsule_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUN_AUTH_PROHIBITED_AUTHORIZATION_{flag.upper()}")

    # Performed flags must be False
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in perf_flags:
        if capsule_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUN_AUTH_MUTATION_PERFORMED_{flag.upper()}")

    return is_valid, reasons


def validate_waveguide_package_assembly_run_blocked_operation_fields(capsule_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Verifies blocked operation attempt counts are all zero.
    """
    reasons = []
    is_valid = True

    counts = capsule_dict.get("blocked_operation_attempt_counts", {})
    if not isinstance(counts, dict):
        is_valid = False
        reasons.append("RUN_AUTH_BLOCKED_OPERATION_COUNTS_INVALID")
        return is_valid, reasons

    expected_ops = [
        "archive_creation", "deployment", "directory_creation", "external_publication",
        "external_signing", "file_copy", "production_mutation", "upload"
    ]
    for op in expected_ops:
        if counts.get(op, 0) != 0:
            is_valid = False
            reasons.append(f"RUN_AUTH_BLOCKED_OPERATION_ATTEMPT_NONZERO_{op.upper()}")

    return is_valid, reasons


def index_waveguide_package_run_authorization_references_by_source(capsule_dict: Dict[str, Any]) -> Dict[str, str]:
    """
    Indexes the preserved source digests.
    """
    res = {}
    keys = [
        "source_execution_readiness_report_digest",
        "source_package_assembly_execution_plan_digest",
        "source_preflight_authorization_report_digest",
        "source_authorization_envelope_digest",
        "source_final_package_readiness_report_digest",
        "source_distribution_package_manifest_digest",
        "source_dry_run_audit_report_digest",
        "source_package_assembly_plan_digest",
        "source_artifact_catalog_digest"
    ]
    for k in keys:
        if k in capsule_dict:
            res[k] = capsule_dict[k]
    return res


def build_waveguide_package_assembly_run_authorization_capsule(
    readiness_report_path_or_dict: Any
) -> WaveguidePackageAssemblyRunAuthorizationCapsule:
    """
    Builds the deterministic Package Assembly Run Authorization Capsule.
    """
    readiness_dict = _load_dict(readiness_report_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not readiness_dict:
        return WaveguidePackageAssemblyRunAuthorizationCapsule(
            package_assembly_run_authorization_capsule_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-AUTHORIZATION-CAPSULE",
            package_assembly_run_authorization_capsule_version=1,
            run_request_id="SOL-WAVEGUIDE-RUN-REQUEST-UNKNOWN",
            run_request_kind="metadata_only_future_package_assembly_run",
            run_authorization_status="package_run_invalid",
            run_authorization_decision="invalid_run_authorization",
            run_authorization_scope="metadata_only",
            source_execution_readiness_report_digest="",
            source_package_assembly_execution_plan_digest="",
            source_preflight_authorization_report_digest="",
            source_authorization_envelope_digest="",
            source_final_package_readiness_report_digest="",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            verified_execution_readiness_case_count=0,
            blocked_execution_readiness_case_count=0,
            warning_execution_readiness_case_count=0,
            invalid_execution_readiness_case_count=0,
            planned_execution_step_count=0,
            blocked_execution_step_count=0,
            warning_execution_step_count=0,
            invalid_execution_step_count=0,
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
            run_noop_boundary={},
            run_rollback_noop_policy={},
            blocked_operation_attempt_counts={},
            specific_future_run_authorized=False,
            metadata_only_run_authorization=True,
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
            reason_codes=["RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID", "PACKAGE_RUN_INVALID"],
            notes=[],
            software_validation_caveat=caveat
        )

    # Validate the source report structure
    is_readiness_ok, _ = validate_waveguide_package_execution_readiness_audit_report(readiness_dict)
    readiness_status = readiness_dict.get("execution_readiness_report_status", "")

    reasons = ["RUN_AUTH_CAPSULE_CANONICAL"]
    is_valid = True

    if not is_readiness_ok or readiness_status != "package_execution_readiness_verified":
        is_valid = False
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID")
    else:
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_VALID")
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_VERIFIED")

    # Extract source properties
    rd_digest = readiness_dict.get("execution_readiness_report_digest", "")
    plan_digest = readiness_dict.get("source_package_assembly_execution_plan_digest", "")
    pf_digest = readiness_dict.get("source_preflight_authorization_report_digest", "")
    env_digest = readiness_dict.get("source_authorization_envelope_digest", "")
    fr_digest = readiness_dict.get("source_final_package_readiness_report_digest", "")
    dm_digest = readiness_dict.get("source_distribution_package_manifest_digest", "")
    dr_digest = readiness_dict.get("source_dry_run_audit_report_digest", "")
    ap_digest = readiness_dict.get("source_package_assembly_plan_digest", "")
    ac_digest = readiness_dict.get("source_artifact_catalog_digest", "")

    if rd_digest:
        reasons.append("RUN_AUTH_EXECUTION_READINESS_DIGEST_REFERENCED")
    if plan_digest:
        reasons.append("RUN_AUTH_EXECUTION_PLAN_DIGEST_REFERENCED")
    if pf_digest:
        reasons.append("RUN_AUTH_PREFLIGHT_AUTHORIZATION_DIGEST_REFERENCED")
    if env_digest:
        reasons.append("RUN_AUTH_AUTHORIZATION_ENVELOPE_DIGEST_REFERENCED")
    if fr_digest:
        reasons.append("RUN_AUTH_FINAL_PACKAGE_READINESS_DIGEST_REFERENCED")
    if dm_digest:
        reasons.append("RUN_AUTH_PACKAGE_MANIFEST_DIGEST_REFERENCED")
    if dr_digest:
        reasons.append("RUN_AUTH_DRY_RUN_REPORT_DIGEST_REFERENCED")
    if ap_digest:
        reasons.append("RUN_AUTH_ASSEMBLY_PLAN_DIGEST_REFERENCED")
    if ac_digest:
        reasons.append("RUN_AUTH_ARTIFACT_CATALOG_DIGEST_REFERENCED")

    # Case counts
    ver_cases_count = readiness_dict.get("verified_execution_readiness_count", 0)
    blk_cases_count = readiness_dict.get("blocked_execution_readiness_count", 0)
    wrn_cases_count = readiness_dict.get("warning_execution_readiness_count", 0)
    inv_cases_count = readiness_dict.get("invalid_execution_readiness_count", 0)

    if blk_cases_count != 0 or wrn_cases_count != 0 or inv_cases_count != 0 or ver_cases_count == 0:
        is_valid = False
        if ver_cases_count == 0:
            reasons.append("RUN_AUTH_VERIFIED_CASE_COUNT_INVALID")
        if blk_cases_count != 0:
            reasons.append("RUN_AUTH_BLOCKED_COUNT_NONZERO")
        if wrn_cases_count != 0:
            reasons.append("RUN_AUTH_WARNING_COUNT_NONZERO")
        if inv_cases_count != 0:
            reasons.append("RUN_AUTH_INVALID_COUNT_NONZERO")
    else:
        reasons.append("RUN_AUTH_VERIFIED_CASE_COUNT_VALID")
        reasons.append("RUN_AUTH_BLOCKED_COUNT_ZERO")
        reasons.append("RUN_AUTH_WARNING_COUNT_ZERO")
        reasons.append("RUN_AUTH_INVALID_COUNT_ZERO")

    # Step counts
    step_count = readiness_dict.get("planned_execution_step_count", 0)
    if step_count == 0:
        is_valid = False
        reasons.append("RUN_AUTH_STEP_COUNT_INVALID")
    else:
        reasons.append("RUN_AUTH_STEP_COUNT_VALID")

    total_files = readiness_dict.get("total_authorized_file_count", 0)
    rc1_files = readiness_dict.get("rc1_authorized_file_count", 0)
    rc2_files = readiness_dict.get("rc2_authorized_file_count", 0)
    shared_files = readiness_dict.get("shared_authorized_file_count", 0)

    if total_files == 0 or rc1_files + rc2_files + shared_files != total_files:
        is_valid = False
        reasons.append("RUN_AUTH_AUTHORIZED_FILE_COUNT_INVALID")
    else:
        reasons.append("RUN_AUTH_AUTHORIZED_FILE_COUNT_VALID")
        reasons.append("RUN_AUTH_RC_COUNTS_VALID")

    # Authorize decision
    run_id = build_waveguide_package_assembly_run_request_identity(readiness_dict)
    decision = build_waveguide_package_assembly_run_authorization_decision(is_valid)

    status = "package_run_authorized" if is_valid else "package_run_invalid"
    if is_valid:
        reasons.append("RUN_AUTH_SPECIFIC_FUTURE_RUN_ALLOWED")
        reasons.append("RUN_AUTH_METADATA_ONLY")
        reasons.append("PACKAGE_RUN_AUTHORIZED")
    else:
        reasons.append("PACKAGE_RUN_INVALID")

    # Sort arrays deterministically
    authorized_target_package_sections = sorted(readiness_dict.get("target_package_sections", []))
    authorized_execution_step_types = sorted(readiness_dict.get("execution_step_types_indexed", []))
    authorized_execution_step_phases = sorted(readiness_dict.get("execution_step_phases_indexed", []))
    authorized_package_roles = sorted(readiness_dict.get("package_roles_indexed", []))
    authorized_artifact_types = sorted(readiness_dict.get("artifact_types_indexed", []))
    authorized_rc_scopes = sorted(readiness_dict.get("rc_scopes_indexed", []))
    authorized_source_reference_digests = sorted(readiness_dict.get("source_reference_digests", []))
    authorized_source_reference_paths = sorted(readiness_dict.get("source_reference_paths", []))
    authorized_target_package_paths = sorted(readiness_dict.get("target_package_paths", []))
    authorized_planned_output_references = sorted(readiness_dict.get("planned_output_references", []))
    authorized_execution_step_digests = sorted(readiness_dict.get("execution_step_digests", []))
    authorized_execution_readiness_case_digests = sorted(readiness_dict.get("execution_readiness_case_digests", []))

    # Add standard lists
    run_constraints = [
        "metadata_only_run_authorization",
        "specific_future_run_only",
        "non_mutating_authorization",
        "requires_execution_readiness_report_digest_match",
        "requires_execution_plan_digest_match",
        "requires_preflight_authorization_digest_match",
        "requires_same_authorized_file_count",
        "requires_same_execution_step_count",
        "requires_no_archive_creation",
        "requires_no_file_copy",
        "requires_no_directory_creation",
        "requires_no_upload",
        "requires_no_deployment",
        "requires_no_signing",
        "requires_no_external_publication",
        "requires_no_production_mutation",
        "requires_separate_run_preflight_audit"
    ]
    run_allowances = [
        "specific_future_package_assembly_run_may_be_requested",
        "specific_future_run_requires_run_preflight_audit",
        "specific_future_run_requires_same_execution_readiness_digest",
        "specific_future_run_requires_same_execution_plan_digest",
        "specific_future_run_requires_same_authorized_file_count",
        "specific_future_run_requires_zero_mutation_attempts"
    ]
    run_prohibitions = [
        "no_archive_creation_by_run_authorization_capsule",
        "no_file_copy_by_run_authorization_capsule",
        "no_directory_creation_by_run_authorization_capsule",
        "no_upload_by_run_authorization_capsule",
        "no_deployment_by_run_authorization_capsule",
        "no_signing_by_run_authorization_capsule",
        "no_external_publication_by_run_authorization_capsule",
        "no_production_mutation_by_run_authorization_capsule"
    ]
    run_guard_requirements = [
        "source_execution_readiness_report_digest_matches",
        "source_package_assembly_execution_plan_digest_matches",
        "source_preflight_authorization_report_digest_matches",
        "source_authorization_envelope_digest_matches",
        "source_final_package_readiness_report_digest_matches",
        "source_distribution_package_manifest_digest_matches",
        "source_dry_run_audit_report_digest_matches",
        "source_package_assembly_plan_digest_matches",
        "source_artifact_catalog_digest_matches",
        "metadata_only_run_boundary_acknowledged",
        "future_runner_requires_separate_run_preflight_audit",
        "future_runner_requires_no_archive_creation_by_capsule",
        "future_runner_requires_no_file_copy_by_capsule",
        "future_runner_requires_no_directory_creation_by_capsule",
        "future_runner_requires_no_upload_by_capsule",
        "future_runner_requires_no_deployment_by_capsule",
        "future_runner_requires_no_signing_by_capsule",
        "future_runner_requires_no_external_publication_by_capsule",
        "future_runner_requires_no_production_mutation_by_capsule"
    ]

    reasons.append("RUN_AUTH_PHYSICAL_EXECUTION_PROHIBITED")
    reasons.append("RUN_AUTH_ARCHIVE_CREATION_PROHIBITED")
    reasons.append("RUN_AUTH_FILE_COPY_PROHIBITED")
    reasons.append("RUN_AUTH_DIRECTORY_CREATION_PROHIBITED")
    reasons.append("RUN_AUTH_UPLOAD_PROHIBITED")
    reasons.append("RUN_AUTH_DEPLOYMENT_PROHIBITED")
    reasons.append("RUN_AUTH_SIGNING_PROHIBITED")
    reasons.append("RUN_AUTH_EXTERNAL_PUBLICATION_PROHIBITED")
    reasons.append("RUN_AUTH_PRODUCTION_MUTATION_PROHIBITED")

    reasons.append("RUN_AUTH_NO_PHYSICAL_EXECUTION_PERFORMED")
    reasons.append("RUN_AUTH_NO_ARCHIVE_CREATED")
    reasons.append("RUN_AUTH_NO_FILE_COPY_PERFORMED")
    reasons.append("RUN_AUTH_NO_DIRECTORY_CREATED")
    reasons.append("RUN_AUTH_NO_UPLOAD_PERFORMED")
    reasons.append("RUN_AUTH_NO_DEPLOYMENT_PERFORMED")
    reasons.append("RUN_AUTH_NO_SIGNING_PERFORMED")
    reasons.append("RUN_AUTH_NO_EXTERNAL_PUBLICATION_PERFORMED")
    reasons.append("RUN_AUTH_NO_PRODUCTION_MUTATION_PERFORMED")

    reasons.append("RUN_AUTH_BLOCKED_OPERATION_COUNTS_ZERO")
    reasons.append("RUN_AUTH_CONSTRAINTS_INCLUDED")
    reasons.append("RUN_AUTH_ALLOWANCES_INCLUDED")
    reasons.append("RUN_AUTH_PROHIBITIONS_INCLUDED")
    reasons.append("RUN_AUTH_GUARD_REQUIREMENTS_INCLUDED")
    reasons.append("RUN_AUTH_NOOP_BOUNDARY_INCLUDED")
    reasons.append("RUN_AUTH_ROLLBACK_NOOP_POLICY_INCLUDED")
    reasons.append("RUN_AUTH_SOFTWARE_CAVEAT_INCLUDED")

    run_noop_boundary = {
        "physical_execution_authorized": False,
        "archive_creation_authorized": False,
        "file_copy_authorized": False,
        "directory_creation_authorized": False,
        "upload_authorized": False,
        "deployment_authorized": False,
        "signing_authorized": False,
        "external_publication_authorized": False,
        "production_mutation_authorized": False,
        "physical_execution_performed": False,
        "archive_creation_performed": False,
        "file_copy_performed": False,
        "directory_creation_performed": False,
        "upload_performed": False,
        "deployment_performed": False,
        "signing_performed": False,
        "external_publication_performed": False,
        "production_mutation_performed": False
    }

    run_rollback_noop_policy = {
        "rollback_required": False,
        "rollback_reason": "no_physical_run_performed",
        "rollback_scope": "metadata_only",
        "rollback_operations": []
    }

    blocked_operation_attempt_counts = {
        "archive_creation": 0,
        "deployment": 0,
        "directory_creation": 0,
        "external_publication": 0,
        "external_signing": 0,
        "file_copy": 0,
        "production_mutation": 0,
        "upload": 0
    }

    capsule = WaveguidePackageAssemblyRunAuthorizationCapsule(
        package_assembly_run_authorization_capsule_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-AUTHORIZATION-CAPSULE",
        package_assembly_run_authorization_capsule_version=1,
        run_request_id=run_id,
        run_request_kind="metadata_only_future_package_assembly_run",
        run_authorization_status=status,
        run_authorization_decision=decision,
        run_authorization_scope="metadata_only",
        source_execution_readiness_report_digest=rd_digest,
        source_package_assembly_execution_plan_digest=plan_digest,
        source_preflight_authorization_report_digest=pf_digest,
        source_authorization_envelope_digest=env_digest,
        source_final_package_readiness_report_digest=fr_digest,
        source_distribution_package_manifest_digest=dm_digest,
        source_dry_run_audit_report_digest=dr_digest,
        source_package_assembly_plan_digest=ap_digest,
        source_artifact_catalog_digest=ac_digest,
        verified_execution_readiness_case_count=ver_cases_count,
        blocked_execution_readiness_case_count=blk_cases_count,
        warning_execution_readiness_case_count=wrn_cases_count,
        invalid_execution_readiness_case_count=inv_cases_count,
        planned_execution_step_count=step_count,
        blocked_execution_step_count=0,
        warning_execution_step_count=0,
        invalid_execution_step_count=0,
        total_authorized_file_count=total_files,
        rc1_authorized_file_count=rc1_files,
        rc2_authorized_file_count=rc2_files,
        shared_authorized_file_count=shared_files,
        authorized_target_package_sections=authorized_target_package_sections,
        authorized_execution_step_types=authorized_execution_step_types,
        authorized_execution_step_phases=authorized_execution_step_phases,
        authorized_package_roles=authorized_package_roles,
        authorized_artifact_types=authorized_artifact_types,
        authorized_rc_scopes=authorized_rc_scopes,
        authorized_source_reference_digests=authorized_source_reference_digests,
        authorized_source_reference_paths=authorized_source_reference_paths,
        authorized_target_package_paths=authorized_target_package_paths,
        authorized_planned_output_references=authorized_planned_output_references,
        authorized_execution_step_digests=authorized_execution_step_digests,
        authorized_execution_readiness_case_digests=authorized_execution_readiness_case_digests,
        run_constraints=sorted(run_constraints),
        run_allowances=sorted(run_allowances),
        run_prohibitions=sorted(run_prohibitions),
        run_guard_requirements=sorted(run_guard_requirements),
        run_noop_boundary=run_noop_boundary,
        run_rollback_noop_policy=run_rollback_noop_policy,
        blocked_operation_attempt_counts=blocked_operation_attempt_counts,
        specific_future_run_authorized=is_valid,
        metadata_only_run_authorization=True,
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
        reason_codes=sorted(list(set(reasons))),
        notes=[],
        software_validation_caveat=caveat
    )

    capsule.package_assembly_run_authorization_capsule_digest = hash_waveguide_package_assembly_run_authorization_capsule(capsule)
    return capsule


def validate_waveguide_package_assembly_run_authorization_capsule(capsule: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a run authorization capsule structure and logic.
    """
    capsule_dict = _load_dict(capsule)
    if not capsule_dict:
        return False, ["PACKAGE_RUN_INVALID"]

    reasons = []
    is_valid = True

    # Check ID and version
    if capsule_dict.get("package_assembly_run_authorization_capsule_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-AUTHORIZATION-CAPSULE":
        is_valid = False
        reasons.append("RUN_AUTH_CAPSULE_INVALID_ID")

    if capsule_dict.get("package_assembly_run_authorization_capsule_version") != 1:
        is_valid = False
        reasons.append("RUN_AUTH_CAPSULE_INVALID_VERSION")

    # Check digests
    recorded_digest = capsule_dict.get("package_assembly_run_authorization_capsule_digest", "")
    recomputed_digest = hash_waveguide_package_assembly_run_authorization_capsule(capsule_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("RUN_AUTH_CAPSULE_DIGEST_MISMATCH")
    else:
        reasons.append("RUN_AUTH_CAPSULE_DIGEST_VALID")

    # Validate readiness report references
    rd_digest = capsule_dict.get("source_execution_readiness_report_digest", "")
    if not rd_digest:
        is_valid = False
        reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID")

    # Load readiness report and validate
    default_readiness_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_EXECUTION_READINESS_AUDIT_REPORT.json")
    readiness_report = None
    if os.path.exists(default_readiness_path):
        readiness_report = _load_dict(default_readiness_path)

    if readiness_report:
        # Check digest matches
        recorded_rd_digest = readiness_report.get("execution_readiness_report_digest", "")
        if rd_digest != recorded_rd_digest:
            is_valid = False
            reasons.append("RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID")
    else:
        # If not on disk, we still validate the structural counts and properties inside capsule
        pass

    # Verify counts
    ver_count = capsule_dict.get("verified_execution_readiness_case_count", 0)
    blk_count = capsule_dict.get("blocked_execution_readiness_case_count", 0)
    wrn_count = capsule_dict.get("warning_execution_readiness_case_count", 0)
    inv_count = capsule_dict.get("invalid_execution_readiness_case_count", 0)

    if ver_count == 0:
        is_valid = False
        reasons.append("RUN_AUTH_VERIFIED_CASE_COUNT_INVALID")
    if blk_count != 0:
        is_valid = False
        reasons.append("RUN_AUTH_BLOCKED_COUNT_NONZERO")
    if wrn_count != 0:
        is_valid = False
        reasons.append("RUN_AUTH_WARNING_COUNT_NONZERO")
    if inv_count != 0:
        is_valid = False
        reasons.append("RUN_AUTH_INVALID_COUNT_NONZERO")

    planned_steps = capsule_dict.get("planned_execution_step_count", 0)
    if planned_steps == 0:
        is_valid = False
        reasons.append("RUN_AUTH_STEP_COUNT_INVALID")

    total_files = capsule_dict.get("total_authorized_file_count", 0)
    rc1_files = capsule_dict.get("rc1_authorized_file_count", 0)
    rc2_files = capsule_dict.get("rc2_authorized_file_count", 0)
    shared_files = capsule_dict.get("shared_authorized_file_count", 0)

    if total_files == 0 or rc1_files + rc2_files + shared_files != total_files:
        is_valid = False
        reasons.append("RUN_AUTH_AUTHORIZED_FILE_COUNT_INVALID")

    # Authorize decision constraints
    if capsule_dict.get("specific_future_run_authorized") is not True:
        is_valid = False
        reasons.append("RUN_AUTH_SPECIFIC_FUTURE_RUN_PROHIBITED")

    if capsule_dict.get("metadata_only_run_authorization") is not True:
        is_valid = False
        reasons.append("RUN_AUTH_NOT_METADATA_ONLY")

    # Scope validation
    scope_ok, scope_reasons = validate_waveguide_package_assembly_run_scope(capsule_dict)
    if not scope_ok:
        is_valid = False
        reasons.extend(scope_reasons)

    # Blocked operations validation
    blocked_ok, blocked_reasons = validate_waveguide_package_assembly_run_blocked_operation_fields(capsule_dict)
    if not blocked_ok:
        is_valid = False
        reasons.extend(blocked_reasons)

    # Lists verification
    required_lists = ["run_constraints", "run_allowances", "run_prohibitions", "run_guard_requirements"]
    for lst in required_lists:
        if not capsule_dict.get(lst):
            is_valid = False
            reasons.append(f"RUN_AUTH_MISSING_{lst.upper()}")

    if not capsule_dict.get("software_validation_caveat"):
        is_valid = False
        reasons.append("RUN_AUTH_MISSING_SOFTWARE_CAVEAT")

    # Final status check
    status = capsule_dict.get("run_authorization_status", "")
    if is_valid and status == "package_run_authorized":
        reasons.append("PACKAGE_RUN_AUTHORIZED")
    else:
        is_valid = False
        reasons.append("PACKAGE_RUN_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_assembly_run_authorization_capsule(capsule: Any) -> str:
    """
    Produces a summary description of the run authorization capsule.
    """
    capsule_dict = _load_dict(capsule)
    if not capsule_dict:
        return "Invalid Run Authorization Capsule"

    status = capsule_dict.get("run_authorization_status", "unknown")
    run_id = capsule_dict.get("run_request_id", "unknown")
    digest = capsule_dict.get("package_assembly_run_authorization_capsule_digest", "")

    return (
        f"SOL Waveguide Package Assembly Run Authorization Capsule Summary:\n"
        f"  Status: {status}\n"
        f"  Run Request ID: {run_id}\n"
        f"  Digest: {digest}\n"
        f"  Authorized Files: {capsule_dict.get('total_authorized_file_count')}\n"
        f"  Metadata-Only: {capsule_dict.get('metadata_only_run_authorization')}\n"
    )


def export_waveguide_package_assembly_run_authorization_capsule(capsule: Any, filepath: str) -> None:
    """
    Exports the run authorization capsule as canonical JSON.
    """
    capsule_dict = _load_dict(capsule)
    if not capsule_dict:
        raise ValueError("Cannot export invalid run authorization capsule data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(capsule_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_assembly_run_authorization_capsules(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two capsules and lists differences.
    """
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs
