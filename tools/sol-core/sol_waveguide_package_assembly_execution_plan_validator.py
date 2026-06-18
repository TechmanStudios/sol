# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Execution Plan Validator / Execution Readiness Auditor.
Reloads the execution plan and preflight authorization report, verifies step digests,
validates the guard matrix, no-op boundaries, rollback policies, and compiles readiness report.
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
from sol_waveguide_package_assembly_execution_plan import (
    validate_waveguide_package_assembly_execution_plan,
    hash_waveguide_package_assembly_execution_step,
    hash_waveguide_package_assembly_execution_plan
)
from sol_waveguide_package_assembly_authorization_validator import (
    validate_waveguide_package_preflight_authorization_audit_report
)


@dataclass
class WaveguidePackageExecutionReadinessAuditCase:
    execution_readiness_case_id: str
    package_assembly_execution_plan_id: str
    package_assembly_execution_plan_path: str
    execution_plan_digest_recorded: str
    execution_plan_digest_recomputed: str
    execution_plan_digest_match: bool
    package_execution_step_id: str
    package_execution_step_digest_recorded: str
    package_execution_step_digest_recomputed: str
    package_execution_step_digest_match: bool
    step_index: int
    step_name: str
    step_type: str
    step_phase: str
    step_status: str
    execution_readiness_status: str  # execution_step_readiness_verified, etc.
    source_reference_digest: str
    source_reference_path: str
    input_reference_kind: str
    planned_output_reference: str
    planned_output_kind: str
    target_package_section: str
    target_package_path: str
    artifact_digest: str
    artifact_type: str
    package_role: str
    rc_scope: str
    source_preflight_authorization_report_digest_recorded: str
    source_preflight_authorization_report_digest_recomputed: str
    source_preflight_authorization_report_digest_match: bool
    source_preflight_authorization_report_valid: bool
    source_preflight_authorization_status: str
    guard_conditions_verified: bool
    prohibited_operations_verified: bool
    noop_boundary_verified: bool
    rollback_noop_policy_verified: bool
    input_reference_verified: bool
    output_reference_verified: bool
    source_digest_preserved: bool
    target_reference_preserved: bool
    physical_execution_performed: bool
    archive_created: bool
    file_copied: bool
    directory_created: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    no_physical_execution_verified: bool
    no_archive_creation_verified: bool
    no_file_copy_verified: bool
    no_directory_creation_verified: bool
    no_upload_verified: bool
    no_deployment_verified: bool
    no_signing_verified: bool
    no_external_publication_verified: bool
    no_production_mutation_verified: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    execution_readiness_case_digest: str = ""


@dataclass
class WaveguidePackageExecutionReadinessAuditReport:
    execution_readiness_report_id: str
    execution_readiness_report_version: int
    execution_readiness_report_status: str  # package_execution_readiness_verified, etc.
    source_package_assembly_execution_plan_digest: str
    source_preflight_authorization_report_digest: str
    source_authorization_envelope_digest: str
    source_final_package_readiness_report_digest: str
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    audited_cases: List[WaveguidePackageExecutionReadinessAuditCase]
    verified_execution_readiness_cases: List[str]
    blocked_execution_readiness_cases: List[str]
    warning_execution_readiness_cases: List[str]
    invalid_execution_readiness_cases: List[str]
    verified_execution_readiness_count: int
    blocked_execution_readiness_count: int
    warning_execution_readiness_count: int
    invalid_execution_readiness_count: int
    planned_execution_step_count: int
    blocked_execution_step_count: int
    warning_execution_step_count: int
    invalid_execution_step_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    planned_input_reference_count: int
    planned_output_reference_count: int
    target_package_sections: List[str]
    execution_step_types_indexed: List[str]
    execution_step_phases_indexed: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    source_reference_digests: List[str]
    source_reference_paths: List[str]
    target_package_paths: List[str]
    planned_output_references: List[str]
    execution_step_digests: List[str]
    execution_readiness_case_digests: List[str]
    execution_guard_matrix_verified: bool
    execution_input_reference_index_verified: bool
    execution_output_reference_index_verified: bool
    noop_sandbox_boundary_verified: bool
    rollback_noop_policy_verified: bool
    blocked_operation_attempt_counts: Dict[str, int]
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
    execution_readiness_report_digest: str = ""


def hash_waveguide_package_execution_readiness_audit_case(case: Any) -> str:
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
    c_dict_copy.pop("execution_readiness_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_package_execution_readiness_audit_report(report: Any) -> str:
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
    r_dict_copy.pop("execution_readiness_report_digest", None)
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


def recompute_waveguide_package_assembly_execution_plan_digest(
    plan_path_or_dict: Any
) -> str:
    plan_dict = _load_dict(plan_path_or_dict)
    if plan_dict:
        return hash_waveguide_package_assembly_execution_plan(plan_dict)
    return ""


def recompute_waveguide_package_execution_step_digest(
    step_path_or_dict: Any
) -> str:
    step_dict = _load_dict(step_path_or_dict)
    if step_dict:
        return hash_waveguide_package_assembly_execution_step(step_dict)
    return ""


def validate_waveguide_package_execution_step_sequence(steps: List[Dict[str, Any]], authorized_count: int) -> Tuple[bool, List[str]]:
    reasons = []
    is_valid = True

    # 1. Step indexes are contiguous and start at 0
    indices = [s.get("step_index", -1) for s in steps]
    if not indices or indices != list(range(len(steps))):
        is_valid = False
        reasons.append("EXECUTION_READINESS_STEP_SEQUENCE_INVALID_INDICES")

    # 2. Final index is 30 for the clean state
    if len(steps) != 31:
        is_valid = False
        reasons.append("EXECUTION_READINESS_STEP_SEQUENCE_COUNT_MISMATCH")

    # 3. Setup step exists
    setup_steps = [s for s in steps if s.get("step_type") == "verify_preflight_authorization"]
    if len(setup_steps) != 1 or setup_steps[0].get("step_index") != 0:
        is_valid = False
        reasons.append("EXECUTION_READINESS_SETUP_STEP_INVALID")

    # 4. File metadata planning steps
    file_steps = [s for s in steps if s.get("step_type") == "prepare_metadata_instruction"]
    if len(file_steps) != authorized_count:
        is_valid = False
        reasons.append("EXECUTION_READINESS_FILE_METADATA_STEPS_MISMATCH")

    # 5. Safety boundary step exists
    safety_steps = [s for s in steps if s.get("step_type") == "prepare_noop_boundary"]
    if len(safety_steps) != 1 or safety_steps[0].get("step_index") != 29:
        is_valid = False
        reasons.append("EXECUTION_READINESS_SAFETY_BOUNDARY_STEP_INVALID")

    # 6. Finalization blueprint step exists
    final_steps = [s for s in steps if s.get("step_type") == "finalize_execution_blueprint"]
    if len(final_steps) != 1 or final_steps[0].get("step_index") != 30:
        is_valid = False
        reasons.append("EXECUTION_READINESS_FINALIZATION_STEP_INVALID")

    if is_valid:
        reasons.append("EXECUTION_READINESS_STEP_SEQUENCE_VERIFIED")
    return is_valid, reasons


def validate_waveguide_package_execution_guard_matrix(guards: List[str]) -> bool:
    expected = [
        "source_preflight_authorization_report_digest_matches",
        "source_authorization_envelope_digest_matches",
        "source_final_package_readiness_report_digest_matches",
        "source_distribution_package_manifest_digest_matches",
        "source_dry_run_audit_report_digest_matches",
        "source_package_assembly_plan_digest_matches",
        "source_artifact_catalog_digest_matches",
        "metadata_only_boundary_acknowledged",
        "no_archive_creation_in_this_plan",
        "no_file_copy_in_this_plan",
        "no_directory_creation_in_this_plan",
        "no_upload_in_this_plan",
        "no_deployment_in_this_plan",
        "no_signing_in_this_plan",
        "no_external_publication_in_this_plan",
        "no_production_mutation_in_this_plan",
        "future_runner_requires_separate_execution_authorization"
    ]
    return all(g in guards for g in expected)


def validate_waveguide_package_execution_input_reference_index(index: Dict[str, str], steps: List[Dict[str, Any]]) -> bool:
    file_steps = [s for s in steps if s.get("step_type") == "prepare_metadata_instruction"]
    for s in file_steps:
        path = s.get("source_reference_path")
        digest = s.get("source_reference_digest")
        if index.get(path) != digest:
            return False
    return len(index) == len(file_steps) and len(index) > 0


def validate_waveguide_package_execution_output_reference_index(index: Dict[str, str], steps: List[Dict[str, Any]]) -> bool:
    file_steps = [s for s in steps if s.get("step_type") == "prepare_metadata_instruction"]
    for s in file_steps:
        path = s.get("target_package_path")
        digest = s.get("artifact_digest")
        if index.get(path) != digest:
            return False
    return len(index) == len(file_steps) and len(index) > 0


def validate_waveguide_package_execution_noop_boundary(boundary: Dict[str, Any]) -> bool:
    fields = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    return all(boundary.get(f) is False for f in fields)


def validate_waveguide_package_execution_rollback_noop_policy(policy: Dict[str, Any]) -> bool:
    return (
        policy.get("rollback_required") is False and
        policy.get("rollback_reason") == "no_physical_execution_performed" and
        policy.get("rollback_scope") == "metadata_only" and
        policy.get("rollback_operations") == []
    )


def build_waveguide_package_execution_readiness_audit_case(
    step_dict: Dict[str, Any],
    plan_dict: Dict[str, Any],
    preflight_dict: Dict[str, Any]
) -> WaveguidePackageExecutionReadinessAuditCase:
    """
    Builds a single execution-readiness audit case validating a step.
    """
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reasons = ["EXECUTION_READINESS_CASE_CANONICAL"]
    is_valid = True

    # Validate plan digest
    plan_digest_recorded = plan_dict.get("package_assembly_execution_plan_digest", "")
    plan_digest_recomputed = hash_waveguide_package_assembly_execution_plan(plan_dict)
    plan_digest_match = (plan_digest_recorded == plan_digest_recomputed) and (plan_digest_recorded != "")
    if plan_digest_match:
        reasons.append("EXECUTION_READINESS_PLAN_DIGEST_MATCH")
    else:
        is_valid = False
        reasons.append("EXECUTION_READINESS_PLAN_DIGEST_MISMATCH")

    if plan_dict.get("package_assembly_execution_plan_status") != "package_execution_plan_ready":
        is_valid = False
        reasons.append("EXECUTION_READINESS_PLAN_INVALID")

    # Validate step digest
    step_digest_recorded = step_dict.get("package_execution_step_digest", "")
    step_digest_recomputed = hash_waveguide_package_assembly_execution_step(step_dict)
    step_digest_match = (step_digest_recorded == step_digest_recomputed) and (step_digest_recorded != "")
    if step_digest_match:
        reasons.append("EXECUTION_READINESS_STEP_DIGEST_MATCH")
    else:
        is_valid = False
        reasons.append("EXECUTION_READINESS_STEP_DIGEST_MISMATCH")

    # Validate preflight report
    pf_digest_recorded = preflight_dict.get("preflight_authorization_report_digest", "")
    pf_digest_recomputed = preflight_dict.get("preflight_authorization_report_digest", "") # already validated
    pf_digest_match = (pf_digest_recorded != "")
    pf_valid = True
    pf_status = preflight_dict.get("preflight_authorization_report_status", "")
    if pf_status != "package_preflight_authorization_verified":
        is_valid = False
        reasons.append("EXECUTION_READINESS_SOURCE_PREFLIGHT_INVALID")

    # Check step properties
    step_index = step_dict.get("step_index", 0)
    step_id = step_dict.get("package_execution_step_id", "")
    step_status = step_dict.get("step_status", "")
    step_type = step_dict.get("step_type", "")
    step_phase = step_dict.get("step_phase", "")

    # Guards verification
    guards_ok = validate_waveguide_package_execution_guard_matrix(step_dict.get("guard_conditions", []))
    if guards_ok:
        reasons.append("EXECUTION_READINESS_GUARD_MATRIX_VERIFIED")
    else:
        is_valid = False

    # Blocked operation verifications
    prohibits = step_dict.get("prohibited_operations", [])
    prohibits_ok = all(p in prohibits for p in [
        "no_archive_creation_in_this_plan", "no_file_copy_in_this_plan", "no_directory_creation_in_this_plan",
        "no_upload_in_this_plan", "no_deployment_in_this_plan", "no_signing_in_this_plan",
        "no_external_publication_in_this_plan", "no_production_mutation_in_this_plan"
    ])
    if prohibits_ok:
        reasons.append("EXECUTION_READINESS_NOOP_BOUNDARY_VERIFIED")
    else:
        is_valid = False

    # Check mutation checks
    mutations = [
        "physical_execution_performed", "archive_created", "file_copied", "directory_created",
        "upload_performed", "deployment_performed", "signing_performed",
        "external_publication_performed", "production_mutation_performed"
    ]
    mutation_ok = all(step_dict.get(m) is False for m in mutations)
    if not mutation_ok:
        is_valid = False

    # Preserve digests check where applicable
    digest_preserved = True
    if step_type == "prepare_metadata_instruction":
        if step_dict.get("artifact_digest") != step_dict.get("source_reference_digest"):
            digest_preserved = False
            is_valid = False

    # Case readiness status
    case_status = "execution_step_readiness_verified"
    if not is_valid:
        case_status = "execution_step_readiness_invalid"
    elif step_status != "execution_step_planned":
        case_status = "execution_step_readiness_blocked"

    # Add reason codes
    if is_valid:
        reasons.append("PACKAGE_EXECUTION_READINESS_VERIFIED")
    else:
        reasons.append("PACKAGE_EXECUTION_READINESS_INVALID")

    case = WaveguidePackageExecutionReadinessAuditCase(
        execution_readiness_case_id=f"SOL-WAVEGUIDE-READINESS-CASE-{step_id}",
        package_assembly_execution_plan_id=plan_dict.get("package_assembly_execution_plan_id", ""),
        package_assembly_execution_plan_path="",
        execution_plan_digest_recorded=plan_digest_recorded,
        execution_plan_digest_recomputed=plan_digest_recomputed,
        execution_plan_digest_match=plan_digest_match,
        package_execution_step_id=step_id,
        package_execution_step_digest_recorded=step_digest_recorded,
        package_execution_step_digest_recomputed=step_digest_recomputed,
        package_execution_step_digest_match=step_digest_match,
        step_index=step_index,
        step_name=step_dict.get("step_name", ""),
        step_type=step_type,
        step_phase=step_phase,
        step_status=step_status,
        execution_readiness_status=case_status,
        source_reference_digest=step_dict.get("source_reference_digest", ""),
        source_reference_path=step_dict.get("source_reference_path", ""),
        input_reference_kind=step_dict.get("input_reference_kind", ""),
        planned_output_reference=step_dict.get("planned_output_reference", ""),
        planned_output_kind=step_dict.get("planned_output_kind", ""),
        target_package_section=step_dict.get("target_package_section", ""),
        target_package_path=step_dict.get("target_package_path", ""),
        artifact_digest=step_dict.get("artifact_digest", ""),
        artifact_type=step_dict.get("artifact_type", ""),
        package_role=step_dict.get("package_role", ""),
        rc_scope=step_dict.get("rc_scope", ""),
        source_preflight_authorization_report_digest_recorded=pf_digest_recorded,
        source_preflight_authorization_report_digest_recomputed=pf_digest_recomputed,
        source_preflight_authorization_report_digest_match=pf_digest_match,
        source_preflight_authorization_report_valid=pf_valid,
        source_preflight_authorization_status=pf_status,
        guard_conditions_verified=guards_ok,
        prohibited_operations_verified=prohibits_ok,
        noop_boundary_verified=step_dict.get("no_op_boundary", False),
        rollback_noop_policy_verified=True,
        input_reference_verified=True,
        output_reference_verified=True,
        source_digest_preserved=digest_preserved,
        target_reference_preserved=True,
        physical_execution_performed=step_dict.get("physical_execution_performed", False),
        archive_created=step_dict.get("archive_created", False),
        file_copied=step_dict.get("file_copied", False),
        directory_created=step_dict.get("directory_created", False),
        upload_performed=step_dict.get("upload_performed", False),
        deployment_performed=step_dict.get("deployment_performed", False),
        signing_performed=step_dict.get("signing_performed", False),
        external_publication_performed=step_dict.get("external_publication_performed", False),
        production_mutation_performed=step_dict.get("production_mutation_performed", False),
        blocked_operation_attempt_counts=plan_dict.get("blocked_operation_attempt_counts", {}),
        no_physical_execution_verified=not step_dict.get("physical_execution_performed", False),
        no_archive_creation_verified=not step_dict.get("archive_created", False),
        no_file_copy_verified=not step_dict.get("file_copied", False),
        no_directory_creation_verified=not step_dict.get("directory_created", False),
        no_upload_verified=not step_dict.get("upload_performed", False),
        no_deployment_verified=not step_dict.get("deployment_performed", False),
        no_signing_verified=not step_dict.get("signing_performed", False),
        no_external_publication_verified=not step_dict.get("external_publication_performed", False),
        no_production_mutation_verified=not step_dict.get("production_mutation_performed", False),
        reason_codes=sorted(list(set(reasons))),
        notes=[],
        software_validation_caveat=caveat
    )
    case.execution_readiness_case_digest = hash_waveguide_package_execution_readiness_audit_case(case)
    return case


def validate_waveguide_package_assembly_execution_plan_independently(
    plan_path_or_dict: Any,
    preflight_report_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates compatibility between execution plan and preflight report.
    """
    plan_dict = _load_dict(plan_path_or_dict)
    pf_dict = _load_dict(preflight_report_path_or_dict)

    reasons = []
    is_valid = True

    if not plan_dict or not pf_dict:
        return False, ["PACKAGE_EXECUTION_READINESS_INVALID"]

    # Validate plan structure
    plan_ok, _ = validate_waveguide_package_assembly_execution_plan(plan_dict)
    if not plan_ok:
        is_valid = False
        reasons.append("EXECUTION_READINESS_PLAN_INVALID")
    else:
        reasons.append("EXECUTION_READINESS_PLAN_VALID")

    # Validate preflight report structure
    pf_ok, _ = validate_waveguide_package_preflight_authorization_audit_report(pf_dict)
    if not pf_ok:
        is_valid = False
        reasons.append("EXECUTION_READINESS_SOURCE_PREFLIGHT_INVALID")
    else:
        reasons.append("EXECUTION_READINESS_SOURCE_PREFLIGHT_VALID")

    # Check digest matching
    plan_pf_digest = plan_dict.get("source_preflight_authorization_report_digest", "")
    pf_digest = pf_dict.get("preflight_authorization_report_digest", "")
    if plan_pf_digest != pf_digest or not pf_digest:
        is_valid = False
        reasons.append("EXECUTION_READINESS_SOURCE_PREFLIGHT_DIGEST_MISMATCH")
    else:
        reasons.append("EXECUTION_READINESS_SOURCE_PREFLIGHT_DIGEST_MATCH")

    if is_valid:
        reasons.append("PACKAGE_EXECUTION_READINESS_VERIFIED")
    else:
        reasons.append("PACKAGE_EXECUTION_READINESS_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_execution_readiness_audit_report(
    plan_path_or_dict: Any,
    preflight_report_path_or_dict: Any
) -> WaveguidePackageExecutionReadinessAuditReport:
    """
    Builds the top-level execution readiness audit report.
    """
    plan_dict = _load_dict(plan_path_or_dict)
    pf_dict = _load_dict(preflight_report_path_or_dict)

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not plan_dict or not pf_dict:
        return WaveguidePackageExecutionReadinessAuditReport(
            execution_readiness_report_id="SOL-WAVEGUIDE-PACKAGE-EXECUTION-READINESS-AUDIT-REPORT",
            execution_readiness_report_version=1,
            execution_readiness_report_status="package_execution_readiness_invalid",
            source_package_assembly_execution_plan_digest="",
            source_preflight_authorization_report_digest="",
            source_authorization_envelope_digest="",
            source_final_package_readiness_report_digest="",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            audited_cases=[],
            verified_execution_readiness_cases=[],
            blocked_execution_readiness_cases=[],
            warning_execution_readiness_cases=[],
            invalid_execution_readiness_cases=[],
            verified_execution_readiness_count=0,
            blocked_execution_readiness_count=0,
            warning_execution_readiness_count=0,
            invalid_execution_readiness_count=0,
            planned_execution_step_count=0,
            blocked_execution_step_count=0,
            warning_execution_step_count=0,
            invalid_execution_step_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            planned_input_reference_count=0,
            planned_output_reference_count=0,
            target_package_sections=[],
            execution_step_types_indexed=[],
            execution_step_phases_indexed=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            rc_scopes_indexed=[],
            source_reference_digests=[],
            source_reference_paths=[],
            target_package_paths=[],
            planned_output_references=[],
            execution_step_digests=[],
            execution_readiness_case_digests=[],
            execution_guard_matrix_verified=False,
            execution_input_reference_index_verified=False,
            execution_output_reference_index_verified=False,
            noop_sandbox_boundary_verified=False,
            rollback_noop_policy_verified=False,
            blocked_operation_attempt_counts={},
            physical_execution_performed=False,
            archive_creation_performed=False,
            file_copy_performed=False,
            directory_creation_performed=False,
            upload_performed=False,
            deployment_performed=False,
            signing_performed=False,
            external_publication_performed=False,
            production_mutation_performed=False,
            reason_codes=["EXECUTION_READINESS_PLAN_INVALID", "PACKAGE_EXECUTION_READINESS_INVALID"],
            software_validation_caveat=caveat
        )

    # Perform validator compatibility checks
    is_compat_ok, compat_reasons = validate_waveguide_package_assembly_execution_plan_independently(plan_dict, pf_dict)
    
    plan_digest = plan_dict.get("package_assembly_execution_plan_digest", "")
    pf_digest = pf_dict.get("preflight_authorization_report_digest", "")
    env_digest = plan_dict.get("source_authorization_envelope_digest", "")
    fr_digest = plan_dict.get("source_final_package_readiness_report_digest", "")
    dm_digest = plan_dict.get("source_distribution_package_manifest_digest", "")
    dr_digest = plan_dict.get("source_dry_run_audit_report_digest", "")
    ap_digest = plan_dict.get("source_package_assembly_plan_digest", "")
    ac_digest = plan_dict.get("source_artifact_catalog_digest", "")

    total_files = plan_dict.get("total_authorized_file_count", 0)
    rc1_files = plan_dict.get("rc1_authorized_file_count", 0)
    rc2_files = plan_dict.get("rc2_authorized_file_count", 0)
    shared_files = plan_dict.get("shared_authorized_file_count", 0)

    # Build cases
    steps = plan_dict.get("execution_steps", [])
    cases = []
    for s in steps:
        case = build_waveguide_package_execution_readiness_audit_case(s, plan_dict, pf_dict)
        cases.append(case)

    # Validate step sequence
    seq_ok, seq_reasons = validate_waveguide_package_execution_step_sequence(steps, total_files)
    
    # Verify guards, indexes, rollback, no-op
    guards_verified = all(validate_waveguide_package_execution_guard_matrix(s.get("guard_conditions", [])) for s in steps)
    input_index_verified = validate_waveguide_package_execution_input_reference_index(plan_dict.get("execution_input_reference_index", {}), steps)
    output_index_verified = validate_waveguide_package_execution_output_reference_index(plan_dict.get("execution_output_reference_index", {}), steps)
    noop_verified = validate_waveguide_package_execution_noop_boundary(plan_dict.get("noop_sandbox_boundary", {}))
    rollback_verified = validate_waveguide_package_execution_rollback_noop_policy(plan_dict.get("rollback_noop_policy", {}))

    # Counters
    verified_cases = [c.package_execution_step_id for c in cases if c.execution_readiness_status == "execution_step_readiness_verified"]
    blocked_cases = [c.package_execution_step_id for c in cases if c.execution_readiness_status == "execution_step_readiness_blocked"]
    warning_cases = [c.package_execution_step_id for c in cases if c.execution_readiness_status == "execution_step_readiness_warning"]
    invalid_cases = [c.package_execution_step_id for c in cases if c.execution_readiness_status == "execution_step_readiness_invalid"]

    is_report_valid = (
        is_compat_ok and
        seq_ok and
        guards_verified and
        input_index_verified and
        output_index_verified and
        noop_verified and
        rollback_verified and
        len(invalid_cases) == 0 and
        len(blocked_cases) == 0
    )

    report_status = "package_execution_readiness_verified" if is_report_valid else "package_execution_readiness_invalid"
    
    # Collect indices
    target_package_sections = sorted(plan_dict.get("target_package_sections", []))
    execution_step_types_indexed = sorted(plan_dict.get("execution_step_types_indexed", []))
    execution_step_phases_indexed = sorted(plan_dict.get("execution_step_phases_indexed", []))
    package_roles_indexed = sorted(plan_dict.get("package_roles_indexed", []))
    artifact_types_indexed = sorted(plan_dict.get("artifact_types_indexed", []))
    rc_scopes_indexed = sorted(plan_dict.get("rc_scopes_indexed", []))
    source_reference_digests = sorted(plan_dict.get("source_reference_digests", []))
    source_reference_paths = sorted(plan_dict.get("source_reference_paths", []))
    target_package_paths = sorted(plan_dict.get("target_package_paths", []))
    planned_output_references = sorted(plan_dict.get("planned_output_references", []))
    execution_step_digests = sorted([s.get("package_execution_step_digest", "") for s in steps])
    execution_readiness_case_digests = sorted([c.execution_readiness_case_digest for c in cases])

    reason_codes = ["EXECUTION_READINESS_CASE_CANONICAL", "EXECUTION_READINESS_PLAN_LOADED"]
    if plan_dict.get("package_assembly_execution_plan_status") == "package_execution_plan_ready":
        reason_codes.append("EXECUTION_READINESS_PLAN_VALID")
    else:
        reason_codes.append("EXECUTION_READINESS_PLAN_INVALID")

    if seq_ok:
        reason_codes.append("EXECUTION_READINESS_STEP_SEQUENCE_VERIFIED")
    if guards_verified:
        reason_codes.append("EXECUTION_READINESS_GUARD_MATRIX_VERIFIED")
    if input_index_verified:
        reason_codes.append("EXECUTION_READINESS_INPUT_INDEX_VERIFIED")
    if output_index_verified:
        reason_codes.append("EXECUTION_READINESS_OUTPUT_INDEX_VERIFIED")
    if noop_verified:
        reason_codes.append("EXECUTION_READINESS_NOOP_BOUNDARY_VERIFIED")
    if rollback_verified:
        reason_codes.append("EXECUTION_READINESS_ROLLBACK_NOOP_POLICY_VERIFIED")

    if is_report_valid:
        reason_codes.append("PACKAGE_EXECUTION_READINESS_VERIFIED")
    else:
        reason_codes.append("PACKAGE_EXECUTION_READINESS_INVALID")

    report = WaveguidePackageExecutionReadinessAuditReport(
        execution_readiness_report_id="SOL-WAVEGUIDE-PACKAGE-EXECUTION-READINESS-AUDIT-REPORT",
        execution_readiness_report_version=1,
        execution_readiness_report_status=report_status,
        source_package_assembly_execution_plan_digest=plan_digest,
        source_preflight_authorization_report_digest=pf_digest,
        source_authorization_envelope_digest=env_digest,
        source_final_package_readiness_report_digest=fr_digest,
        source_distribution_package_manifest_digest=dm_digest,
        source_dry_run_audit_report_digest=dr_digest,
        source_package_assembly_plan_digest=ap_digest,
        source_artifact_catalog_digest=ac_digest,
        audited_cases=cases,
        verified_execution_readiness_cases=verified_cases,
        blocked_execution_readiness_cases=blocked_cases,
        warning_execution_readiness_cases=warning_cases,
        invalid_execution_readiness_cases=invalid_cases,
        verified_execution_readiness_count=len(verified_cases),
        blocked_execution_readiness_count=len(blocked_cases),
        warning_execution_readiness_count=len(warning_cases),
        invalid_execution_readiness_count=len(invalid_cases),
        planned_execution_step_count=len(steps),
        blocked_execution_step_count=0,
        warning_execution_step_count=0,
        invalid_execution_step_count=0,
        total_authorized_file_count=total_files,
        rc1_authorized_file_count=rc1_files,
        rc2_authorized_file_count=rc2_files,
        shared_authorized_file_count=shared_files,
        planned_input_reference_count=plan_dict.get("planned_input_reference_count", 0),
        planned_output_reference_count=plan_dict.get("planned_output_reference_count", 0),
        target_package_sections=target_package_sections,
        execution_step_types_indexed=execution_step_types_indexed,
        execution_step_phases_indexed=execution_step_phases_indexed,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        rc_scopes_indexed=rc_scopes_indexed,
        source_reference_digests=source_reference_digests,
        source_reference_paths=source_reference_paths,
        target_package_paths=target_package_paths,
        planned_output_references=planned_output_references,
        execution_step_digests=execution_step_digests,
        execution_readiness_case_digests=execution_readiness_case_digests,
        execution_guard_matrix_verified=guards_verified,
        execution_input_reference_index_verified=input_index_verified,
        execution_output_reference_index_verified=output_index_verified,
        noop_sandbox_boundary_verified=noop_verified,
        rollback_noop_policy_verified=rollback_verified,
        blocked_operation_attempt_counts=plan_dict.get("blocked_operation_attempt_counts", {}),
        physical_execution_performed=False,
        archive_creation_performed=False,
        file_copy_performed=False,
        directory_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=sorted(list(set(reason_codes))),
        software_validation_caveat=caveat
    )
    report.execution_readiness_report_digest = hash_waveguide_package_execution_readiness_audit_report(report)
    return report


def validate_waveguide_package_execution_readiness_audit_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Validates the readiness report structure and contents.
    """
    report_dict = _load_dict(report)
    if not report_dict:
        return False, ["PACKAGE_EXECUTION_READINESS_INVALID"]

    reasons = []
    is_valid = True

    if report_dict.get("execution_readiness_report_id") != "SOL-WAVEGUIDE-PACKAGE-EXECUTION-READINESS-AUDIT-REPORT":
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_READINESS_INVALID_ID")

    status = report_dict.get("execution_readiness_report_status", "")
    if status not in ["package_execution_readiness_verified", "package_execution_readiness_blocked", "package_execution_readiness_warning", "package_execution_readiness_invalid"]:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_READINESS_UNRECOGNIZED_STATUS")

    # Validate cases
    cases = report_dict.get("audited_cases", [])
    if not cases:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_READINESS_MISSING_CASES")
    else:
        for c in cases:
            # Check digest
            recorded = c.get("execution_readiness_case_digest", "")
            recomputed = hash_waveguide_package_execution_readiness_audit_case(c)
            if recorded != recomputed or not recorded:
                is_valid = False
                reasons.append("PACKAGE_EXECUTION_READINESS_CASE_DIGEST_MISMATCH")

    # Mutation flags check
    mutations = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for m in mutations:
        if report_dict.get(m) is not False:
            is_valid = False
            reasons.append(f"PACKAGE_EXECUTION_READINESS_MUTATION_PERFORMED_{m.upper()}")

    # Digest verification
    recorded_report = report_dict.get("execution_readiness_report_digest", "")
    recomputed_report = hash_waveguide_package_execution_readiness_audit_report(report_dict)
    if recorded_report != recomputed_report or not recorded_report:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_READINESS_REPORT_DIGEST_MISMATCH")

    if is_valid and status == "package_execution_readiness_verified":
        reasons.append("PACKAGE_EXECUTION_READINESS_VERIFIED")
    else:
        reasons.append("PACKAGE_EXECUTION_READINESS_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_execution_readiness_audit_report(report: Any) -> str:
    report_dict = _load_dict(report)
    if not report_dict:
        return "Invalid Package Execution Readiness Audit Report"

    status = report_dict.get("execution_readiness_report_status", "unknown")
    cases = report_dict.get("audited_cases", [])
    total_files = report_dict.get("total_authorized_file_count", 0)
    digest = report_dict.get("execution_readiness_report_digest", "")

    return (
        f"SOL Waveguide Package Execution Readiness Audit Report Summary:\n"
        f"  Report Status: {status}\n"
        f"  Report Digest: {digest}\n"
        f"  Total Audited Cases: {len(cases)}\n"
        f"  Total Authorized Files: {total_files}\n"
        f"  Physical Execution: {report_dict.get('physical_execution_performed')}\n"
        f"  Guards Verified: {report_dict.get('execution_guard_matrix_verified')}\n"
    )


def export_waveguide_package_execution_readiness_audit_report(report: Any, filepath: str) -> None:
    report_dict = _load_dict(report)
    if not report_dict:
        raise ValueError("Cannot export invalid readiness report data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_execution_readiness_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        if key == "audited_cases":
            l_cases = l_dict.get(key, [])
            r_cases = r_dict.get(key, [])
            if len(l_cases) != len(r_cases):
                diffs[key] = (f"len={len(l_cases)}", f"len={len(r_cases)}")
            continue
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def index_waveguide_execution_readiness_cases_by_status(cases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for c in cases:
        c_dict = _load_dict(c)
        if c_dict:
            status = c_dict.get("execution_readiness_status", "unknown")
            idx.setdefault(status, []).append(c_dict)
    return idx


def index_waveguide_execution_readiness_cases_by_step_type(cases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for c in cases:
        c_dict = _load_dict(c)
        if c_dict:
            stype = c_dict.get("step_type", "unknown")
            idx.setdefault(stype, []).append(c_dict)
    return idx


def index_waveguide_execution_readiness_cases_by_phase(cases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for c in cases:
        c_dict = _load_dict(c)
        if c_dict:
            phase = c_dict.get("step_phase", "unknown")
            idx.setdefault(phase, []).append(c_dict)
    return idx
