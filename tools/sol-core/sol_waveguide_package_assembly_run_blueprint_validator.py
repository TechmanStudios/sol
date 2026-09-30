# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Run Blueprint Validator / Runner Readiness Auditor.
Independently reloads the run execution blueprint, validates sequence and matrices,
and compiles a deterministic runner-readiness audit report.
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
from sol_waveguide_package_assembly_run_execution_blueprint import (
    validate_waveguide_package_assembly_run_execution_blueprint,
    hash_waveguide_package_assembly_run_execution_blueprint,
    hash_waveguide_package_run_blueprint_phase
)
from sol_waveguide_package_assembly_run_authorization_validator import (
    validate_waveguide_package_run_preflight_audit_report,
    hash_waveguide_package_run_preflight_report
)


@dataclass
class WaveguidePackageRunnerReadinessAuditCase:
    runner_readiness_case_id: str
    package_assembly_run_execution_blueprint_id: str
    package_assembly_run_execution_blueprint_path: str
    run_blueprint_digest_recorded: str
    run_blueprint_digest_recomputed: str
    run_blueprint_digest_match: bool
    run_blueprint_phase_id: str
    run_blueprint_phase_digest_recorded: str
    run_blueprint_phase_digest_recomputed: str
    run_blueprint_phase_digest_match: bool
    phase_index: int
    phase_name: str
    phase_type: str
    phase_status: str
    runner_readiness_status: str  # runner_readiness_verified, runner_readiness_blocked, etc.
    source_run_preflight_report_digest_recorded: str
    source_run_preflight_report_digest_recomputed: str
    source_run_preflight_report_digest_match: bool
    source_run_preflight_report_valid: bool
    source_run_preflight_report_status: str
    source_run_authorization_capsule_digest: str
    source_execution_readiness_report_digest: str
    source_package_assembly_execution_plan_digest: str
    expected_input_reference: str
    expected_input_kind: str
    expected_output_reference: str
    expected_output_kind: str
    target_package_section: str
    target_package_path: str
    artifact_digest: str
    artifact_type: str
    package_role: str
    rc_scope: str
    required_guard_conditions_verified: bool
    abort_conditions_verified: bool
    safety_gates_verified: bool
    prohibited_operations_verified: bool
    noop_boundary_verified: bool
    rollback_noop_policy_verified: bool
    expected_input_verified: bool
    expected_output_verified: bool
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
    runner_readiness_case_digest: str = ""


@dataclass
class WaveguidePackageRunnerReadinessAuditReport:
    runner_readiness_report_id: str
    runner_readiness_report_version: int
    runner_readiness_report_status: str  # package_runner_readiness_verified, etc.
    source_run_execution_blueprint_digest: str
    source_run_preflight_report_digest: str
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
    audited_cases: List[WaveguidePackageRunnerReadinessAuditCase]
    verified_runner_readiness_cases: List[str]
    blocked_runner_readiness_cases: List[str]
    warning_runner_readiness_cases: List[str]
    invalid_runner_readiness_cases: List[str]
    verified_runner_readiness_count: int
    blocked_runner_readiness_count: int
    warning_runner_readiness_count: int
    invalid_runner_readiness_count: int
    blueprint_phase_count: int
    ready_blueprint_phase_count: int
    blocked_blueprint_phase_count: int
    warning_blueprint_phase_count: int
    invalid_blueprint_phase_count: int
    planned_execution_step_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    expected_input_count: int
    expected_output_count: int
    target_package_sections: List[str]
    phase_types_indexed: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    expected_input_references: List[str]
    expected_output_references: List[str]
    target_package_paths: List[str]
    artifact_digests: List[str]
    phase_digests: List[str]
    runner_readiness_case_digests: List[str]
    abort_condition_matrix_verified: bool
    safety_gate_matrix_verified: bool
    expected_input_index_verified: bool
    expected_output_index_verified: bool
    noop_boundary_verified: bool
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
    runner_readiness_report_digest: str = ""


def hash_waveguide_package_runner_readiness_audit_case(case: Any) -> str:
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
    c_dict_copy.pop("runner_readiness_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_package_runner_readiness_audit_report(report: Any) -> str:
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
    r_dict_copy.pop("runner_readiness_report_digest", None)
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


def recompute_waveguide_package_assembly_run_execution_blueprint_digest(
    blueprint_path_or_dict: Any
) -> str:
    blueprint_dict = _load_dict(blueprint_path_or_dict)
    if blueprint_dict:
        return hash_waveguide_package_assembly_run_execution_blueprint(blueprint_dict)
    return ""


def recompute_waveguide_package_run_blueprint_phase_digest(
    phase_dict: Dict[str, Any]
) -> str:
    return hash_waveguide_package_run_blueprint_phase(phase_dict)


def validate_waveguide_package_run_blueprint_phase_sequence(phases: List[Any]) -> bool:
    """
    Verifies phases sequence is contiguous starting from index 0.
    """
    for idx, p in enumerate(phases):
        p_dict = _load_dict(p)
        if not p_dict or p_dict.get("phase_index") != idx:
            return False
    return True


def validate_waveguide_package_run_abort_condition_matrix(matrix: List[str]) -> bool:
    expected = [
        "execution_readiness_digest_mismatch",
        "preflight_report_digest_mismatch",
        "authorization_capsule_digest_mismatch",
        "plan_digest_mismatch",
        "step_digest_mismatch",
        "physical_execution_authorized_is_true",
        "mutation_flag_is_true",
        "blocked_operation_attempt_count_nonzero",
        "non_contiguous_phase_index",
        "file_count_mismatch"
    ]
    return all(m in matrix for m in expected)


def validate_waveguide_package_run_safety_gate_matrix(matrix: List[str]) -> bool:
    expected = [
        "preflight_audit_report_verified",
        "run_authorization_capsule_verified",
        "execution_readiness_report_verified",
        "execution_plan_verified",
        "metadata_only_boundary_active",
        "zero_blocked_operation_attempts",
        "all_phases_valid"
    ]
    return all(m in matrix for m in expected)


def validate_waveguide_package_run_expected_input_index(
    recorded: Dict[str, str], blueprint_phases: List[Any]
) -> bool:
    from sol_waveguide_package_assembly_run_execution_blueprint import build_waveguide_package_run_expected_input_index
    expected = build_waveguide_package_run_expected_input_index(blueprint_phases)
    return recorded == expected


def validate_waveguide_package_run_expected_output_index(
    recorded: Dict[str, str], blueprint_phases: List[Any]
) -> bool:
    from sol_waveguide_package_assembly_run_execution_blueprint import build_waveguide_package_run_expected_output_index
    expected = build_waveguide_package_run_expected_output_index(blueprint_phases)
    return recorded == expected


def validate_waveguide_package_run_blueprint_noop_boundary(noop: Dict[str, bool]) -> bool:
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


def validate_waveguide_package_run_blueprint_rollback_noop_policy(policy: Dict[str, Any]) -> bool:
    return (
        policy.get("rollback_required") is False and
        policy.get("rollback_reason") == "no_physical_run_performed" and
        policy.get("rollback_scope") == "metadata_only" and
        policy.get("rollback_operations") == []
    )


def build_waveguide_package_runner_readiness_audit_case(
    phase_dict: Dict[str, Any],
    blueprint_dict: Dict[str, Any],
    preflight_dict: Dict[str, Any]
) -> WaveguidePackageRunnerReadinessAuditCase:
    """
    Builds a single runner readiness audit case for a blueprint phase.
    """
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reasons = ["RUNNER_READINESS_CASE_CANONICAL"]
    is_valid = True

    # 1. Blueprint digest check
    recorded_blueprint_digest = blueprint_dict.get("package_assembly_run_execution_blueprint_digest", "")
    recomputed_blueprint_digest = hash_waveguide_package_assembly_run_execution_blueprint(blueprint_dict)
    blueprint_digest_match = (recorded_blueprint_digest == recomputed_blueprint_digest) and (recorded_blueprint_digest != "")
    if not blueprint_digest_match:
        is_valid = False
        reasons.append("RUN_BLUEPRINT_DIGEST_MISMATCH")

    # 2. Phase digest check
    recorded_phase_digest = phase_dict.get("run_blueprint_phase_digest", "")
    recomputed_phase_digest = hash_waveguide_package_run_blueprint_phase(phase_dict)
    phase_digest_match = (recorded_phase_digest == recomputed_phase_digest) and (recorded_phase_digest != "")
    if not phase_digest_match:
        is_valid = False
        reasons.append("RUN_BLUEPRINT_PHASE_DIGEST_MISMATCH")

    # 3. Preflight report verification
    is_preflight_valid, _ = validate_waveguide_package_run_preflight_audit_report(preflight_dict)
    recorded_preflight_digest = blueprint_dict.get("source_run_preflight_report_digest", "")
    recomputed_preflight_digest = hash_waveguide_package_run_preflight_report(preflight_dict)
    preflight_digest_match = (recorded_preflight_digest == recomputed_preflight_digest) and (recorded_preflight_digest != "")
    if not preflight_digest_match:
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_DIGEST_MISMATCH")
    if not is_preflight_valid or preflight_dict.get("run_preflight_report_status") != "package_run_preflight_verified":
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_INVALID")

    # 4. Matrices and boundaries verification
    guards_verified = all(g in preflight_dict.get("run_guard_requirements", []) for g in phase_dict.get("required_guard_conditions", []))
    abort_verified = validate_waveguide_package_run_abort_condition_matrix(phase_dict.get("abort_conditions", []))
    safety_verified = validate_waveguide_package_run_safety_gate_matrix(phase_dict.get("safety_gates", []))
    prohibited_verified = all(p in preflight_dict.get("run_prohibitions", []) for p in phase_dict.get("prohibited_operations", []))
    noop_verified = validate_waveguide_package_run_blueprint_noop_boundary(phase_dict.get("noop_boundary", {}))
    policy_verified = validate_waveguide_package_run_blueprint_rollback_noop_policy(phase_dict.get("run_rollback_noop_policy", {}))

    if not guards_verified or not abort_verified or not safety_verified or not prohibited_verified or not noop_verified or not policy_verified:
        is_valid = False

    # Check input/output verification status
    input_verified = True
    output_verified = True
    if phase_dict.get("phase_type") == "artifact_instruction_planning":
        input_ref = phase_dict.get("expected_input_reference")
        output_ref = phase_dict.get("expected_output_reference")
        if not input_ref or input_ref not in preflight_dict.get("authorized_source_reference_paths", []):
            input_verified = False
            is_valid = False
        if not output_ref or output_ref not in preflight_dict.get("authorized_target_package_paths", []):
            output_verified = False
            is_valid = False

    # Check performed mutation flags
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in perf_flags:
        if phase_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUNNER_READINESS_MUTATION_PERFORMED_{flag.upper()}")

    # Check blocked operations counts
    blocked_counts = blueprint_dict.get("blocked_operation_attempt_counts", {})
    has_blocked_attempts = any(blocked_counts.get(k, 0) > 0 for k in blocked_counts)
    if has_blocked_attempts:
        is_valid = False
        reasons.append("RUNNER_READINESS_BLOCKED_OPERATION_ATTEMPTED")

    # Final readiness status
    case_status = "runner_readiness_verified" if is_valid else "runner_readiness_blocked"
    if is_valid:
        reasons.append("RUNNER_READINESS_VERIFIED")
    else:
        reasons.append("RUNNER_READINESS_BLOCKED")

    case = WaveguidePackageRunnerReadinessAuditCase(
        runner_readiness_case_id=f"SOL-WAVEGUIDE-RUNNER-READINESS-CASE-{phase_dict.get('run_blueprint_phase_id')}",
        package_assembly_run_execution_blueprint_id=blueprint_dict.get("package_assembly_run_execution_blueprint_id", ""),
        package_assembly_run_execution_blueprint_path="",
        run_blueprint_digest_recorded=recorded_blueprint_digest,
        run_blueprint_digest_recomputed=recomputed_blueprint_digest,
        run_blueprint_digest_match=blueprint_digest_match,
        run_blueprint_phase_id=phase_dict.get("run_blueprint_phase_id", ""),
        run_blueprint_phase_digest_recorded=recorded_phase_digest,
        run_blueprint_phase_digest_recomputed=recomputed_phase_digest,
        run_blueprint_phase_digest_match=phase_digest_match,
        phase_index=phase_dict.get("phase_index", 0),
        phase_name=phase_dict.get("phase_name", ""),
        phase_type=phase_dict.get("phase_type", ""),
        phase_status=phase_dict.get("phase_status", ""),
        runner_readiness_status=case_status,
        source_run_preflight_report_digest_recorded=recorded_preflight_digest,
        source_run_preflight_report_digest_recomputed=recomputed_preflight_digest,
        source_run_preflight_report_digest_match=preflight_digest_match,
        source_run_preflight_report_valid=is_preflight_valid,
        source_run_preflight_report_status=preflight_dict.get("run_preflight_report_status", ""),
        source_run_authorization_capsule_digest=blueprint_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=blueprint_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=blueprint_dict.get("source_package_assembly_execution_plan_digest", ""),
        expected_input_reference=phase_dict.get("expected_input_reference", ""),
        expected_input_kind=phase_dict.get("expected_input_kind", "none"),
        expected_output_reference=phase_dict.get("expected_output_reference", ""),
        expected_output_kind=phase_dict.get("expected_output_kind", "none"),
        target_package_section=phase_dict.get("target_package_section", ""),
        target_package_path=phase_dict.get("target_package_path", ""),
        artifact_digest=phase_dict.get("artifact_digest", ""),
        artifact_type=phase_dict.get("artifact_type", ""),
        package_role=phase_dict.get("package_role", ""),
        rc_scope=phase_dict.get("rc_scope", ""),
        required_guard_conditions_verified=guards_verified,
        abort_conditions_verified=abort_verified,
        safety_gates_verified=safety_verified,
        prohibited_operations_verified=prohibited_verified,
        noop_boundary_verified=noop_verified,
        rollback_noop_policy_verified=policy_verified,
        expected_input_verified=input_verified,
        expected_output_verified=output_verified,
        physical_execution_performed=phase_dict.get("physical_execution_performed", False),
        archive_creation_performed=phase_dict.get("archive_creation_performed", False),
        file_copy_performed=phase_dict.get("file_copy_performed", False),
        directory_creation_performed=phase_dict.get("directory_creation_performed", False),
        upload_performed=phase_dict.get("upload_performed", False),
        deployment_performed=phase_dict.get("deployment_performed", False),
        signing_performed=phase_dict.get("signing_performed", False),
        external_publication_performed=phase_dict.get("external_publication_performed", False),
        production_mutation_performed=phase_dict.get("production_mutation_performed", False),
        blocked_operation_attempt_counts=blocked_counts,
        no_physical_execution_verified=phase_dict.get("physical_execution_performed") is False,
        no_archive_creation_verified=phase_dict.get("archive_creation_performed") is False,
        no_file_copy_verified=phase_dict.get("file_copy_performed") is False,
        no_directory_creation_verified=phase_dict.get("directory_creation_performed") is False,
        no_upload_verified=phase_dict.get("upload_performed") is False,
        no_deployment_verified=phase_dict.get("deployment_performed") is False,
        no_signing_verified=phase_dict.get("signing_performed") is False,
        no_external_publication_verified=phase_dict.get("external_publication_performed") is False,
        no_production_mutation_verified=phase_dict.get("production_mutation_performed") is False,
        reason_codes=sorted(list(set(reasons))),
        notes=[],
        software_validation_caveat=caveat
    )
    case.runner_readiness_case_digest = hash_waveguide_package_runner_readiness_audit_case(case)
    return case


def validate_waveguide_package_assembly_run_execution_blueprint_independently(
    blueprint_path_or_dict: Any,
    preflight_report_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    blueprint_dict = _load_dict(blueprint_path_or_dict)
    preflight_dict = _load_dict(preflight_report_path_or_dict)

    reasons = []
    is_valid = True

    if not blueprint_dict or not preflight_dict:
        return False, ["PACKAGE_RUNNER_READINESS_INVALID"]

    blueprint_ok, _ = validate_waveguide_package_assembly_run_execution_blueprint(blueprint_dict)
    preflight_ok, _ = validate_waveguide_package_run_preflight_audit_report(preflight_dict)

    if not blueprint_ok:
        is_valid = False
        reasons.append("RUN_BLUEPRINT_INVALID")
    if not preflight_ok:
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_INVALID")

    # Cross check digests
    recorded_preflight_digest = blueprint_dict.get("source_run_preflight_report_digest", "")
    recomputed_preflight_digest = hash_waveguide_package_run_preflight_report(preflight_dict)
    if recorded_preflight_digest != recomputed_preflight_digest or not recorded_preflight_digest:
        is_valid = False
        reasons.append("RUN_PREFLIGHT_REPORT_DIGEST_MISMATCH")

    if is_valid:
        reasons.append("PACKAGE_RUNNER_READINESS_VERIFIED")
    else:
        reasons.append("PACKAGE_RUNNER_READINESS_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_runner_readiness_audit_report(
    blueprint_path_or_dict: Any,
    preflight_report_path_or_dict: Any
) -> WaveguidePackageRunnerReadinessAuditReport:
    blueprint_dict = _load_dict(blueprint_path_or_dict)
    preflight_dict = _load_dict(preflight_report_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not blueprint_dict or not preflight_dict:
        return WaveguidePackageRunnerReadinessAuditReport(
            runner_readiness_report_id="SOL-WAVEGUIDE-PACKAGE-RUNNER-READINESS-AUDIT-REPORT",
            runner_readiness_report_version=1,
            runner_readiness_report_status="package_runner_readiness_invalid",
            source_run_execution_blueprint_digest="",
            source_run_preflight_report_digest="",
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
            verified_runner_readiness_cases=[],
            blocked_runner_readiness_cases=[],
            warning_runner_readiness_cases=[],
            invalid_runner_readiness_cases=[],
            verified_runner_readiness_count=0,
            blocked_runner_readiness_count=0,
            warning_runner_readiness_count=0,
            invalid_runner_readiness_count=0,
            blueprint_phase_count=0,
            ready_blueprint_phase_count=0,
            blocked_blueprint_phase_count=0,
            warning_blueprint_phase_count=0,
            invalid_blueprint_phase_count=0,
            planned_execution_step_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            expected_input_count=0,
            expected_output_count=0,
            target_package_sections=[],
            phase_types_indexed=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            rc_scopes_indexed=[],
            expected_input_references=[],
            expected_output_references=[],
            target_package_paths=[],
            artifact_digests=[],
            phase_digests=[],
            runner_readiness_case_digests=[],
            abort_condition_matrix_verified=False,
            safety_gate_matrix_verified=False,
            expected_input_index_verified=False,
            expected_output_index_verified=False,
            noop_boundary_verified=False,
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
            reason_codes=["RUN_BLUEPRINT_INVALID", "PACKAGE_RUNNER_READINESS_INVALID"],
            software_validation_caveat=caveat
        )

    is_compat_ok, compat_reasons = validate_waveguide_package_assembly_run_execution_blueprint_independently(
        blueprint_dict, preflight_dict
    )

    phases = blueprint_dict.get("blueprint_phases", [])
    cases = []
    for p in phases:
        case = build_waveguide_package_runner_readiness_audit_case(p, blueprint_dict, preflight_dict)
        cases.append(case)

    # Index by status
    verified_cases = [c.runner_readiness_case_id for c in cases if c.runner_readiness_status == "runner_readiness_verified"]
    blocked_cases = [c.runner_readiness_case_id for c in cases if c.runner_readiness_status == "runner_readiness_blocked"]
    warning_cases = [c.runner_readiness_case_id for c in cases if c.runner_readiness_status == "runner_readiness_warning"]
    invalid_cases = [c.runner_readiness_case_id for c in cases if c.runner_readiness_status == "runner_readiness_invalid"]

    # Readiness validations
    sequence_ok = validate_waveguide_package_run_blueprint_phase_sequence(phases)
    abort_ok = validate_waveguide_package_run_abort_condition_matrix(blueprint_dict.get("abort_condition_matrix", []))
    safety_ok = validate_waveguide_package_run_safety_gate_matrix(blueprint_dict.get("safety_gate_matrix", []))
    input_idx_ok = validate_waveguide_package_run_expected_input_index(blueprint_dict.get("expected_input_index", {}), phases)
    output_idx_ok = validate_waveguide_package_run_expected_output_index(blueprint_dict.get("expected_output_index", {}), phases)
    noop_ok = validate_waveguide_package_run_blueprint_noop_boundary(blueprint_dict.get("noop_boundary", {}))
    policy_ok = validate_waveguide_package_run_blueprint_rollback_noop_policy(blueprint_dict.get("rollback_noop_policy", {}))

    is_report_ok = (
        is_compat_ok and
        sequence_ok and
        abort_ok and
        safety_ok and
        input_idx_ok and
        output_idx_ok and
        noop_ok and
        policy_ok and
        len(phases) == 34 and
        len(blocked_cases) == 0 and
        len(invalid_cases) == 0
    )

    report_status = "package_runner_readiness_verified" if is_report_ok else "package_runner_readiness_invalid"
    reasons = ["RUNNER_READINESS_REPORT_CANONICAL"]
    if is_report_ok:
        reasons.append("PACKAGE_RUNNER_READINESS_VERIFIED")
    else:
        reasons.append("PACKAGE_RUNNER_READINESS_INVALID")

    # Indices
    target_package_sections = sorted(blueprint_dict.get("target_package_sections", []))
    phase_types_indexed = sorted(blueprint_dict.get("phase_types_indexed", []))
    package_roles_indexed = sorted(blueprint_dict.get("package_roles_indexed", []))
    artifact_types_indexed = sorted(blueprint_dict.get("artifact_types_indexed", []))
    rc_scopes_indexed = sorted(blueprint_dict.get("rc_scopes_indexed", []))
    expected_input_references = sorted(blueprint_dict.get("expected_input_references", []))
    expected_output_references = sorted(blueprint_dict.get("expected_output_references", []))
    target_package_paths = sorted(blueprint_dict.get("target_package_paths", []))
    artifact_digests = sorted(blueprint_dict.get("artifact_digests", []))
    phase_digests = sorted(blueprint_dict.get("phase_digests", []))
    runner_readiness_case_digests = sorted([c.runner_readiness_case_digest for c in cases])

    report = WaveguidePackageRunnerReadinessAuditReport(
        runner_readiness_report_id="SOL-WAVEGUIDE-PACKAGE-RUNNER-READINESS-AUDIT-REPORT",
        runner_readiness_report_version=1,
        runner_readiness_report_status=report_status,
        source_run_execution_blueprint_digest=blueprint_dict.get("package_assembly_run_execution_blueprint_digest", ""),
        source_run_preflight_report_digest=blueprint_dict.get("source_run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=blueprint_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=blueprint_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=blueprint_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=blueprint_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=blueprint_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=blueprint_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=blueprint_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=blueprint_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=blueprint_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=blueprint_dict.get("source_artifact_catalog_digest", ""),
        audited_cases=cases,
        verified_runner_readiness_cases=verified_cases,
        blocked_runner_readiness_cases=blocked_cases,
        warning_runner_readiness_cases=warning_cases,
        invalid_runner_readiness_cases=invalid_cases,
        verified_runner_readiness_count=len(verified_cases),
        blocked_runner_readiness_count=len(blocked_cases),
        warning_runner_readiness_count=len(warning_cases),
        invalid_runner_readiness_count=len(invalid_cases),
        blueprint_phase_count=len(phases),
        ready_blueprint_phase_count=blueprint_dict.get("ready_blueprint_phase_count", 0),
        blocked_blueprint_phase_count=blueprint_dict.get("blocked_blueprint_phase_count", 0),
        warning_blueprint_phase_count=blueprint_dict.get("warning_blueprint_phase_count", 0),
        invalid_blueprint_phase_count=blueprint_dict.get("invalid_blueprint_phase_count", 0),
        planned_execution_step_count=blueprint_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=blueprint_dict.get("total_authorized_file_count", 0),
        rc1_authorized_file_count=blueprint_dict.get("rc1_authorized_file_count", 0),
        rc2_authorized_file_count=blueprint_dict.get("rc2_authorized_file_count", 0),
        shared_authorized_file_count=blueprint_dict.get("shared_authorized_file_count", 0),
        expected_input_count=blueprint_dict.get("expected_input_count", 0),
        expected_output_count=blueprint_dict.get("expected_output_count", 0),
        target_package_sections=target_package_sections,
        phase_types_indexed=phase_types_indexed,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        rc_scopes_indexed=rc_scopes_indexed,
        expected_input_references=expected_input_references,
        expected_output_references=expected_output_references,
        target_package_paths=target_package_paths,
        artifact_digests=artifact_digests,
        phase_digests=phase_digests,
        runner_readiness_case_digests=runner_readiness_case_digests,
        abort_condition_matrix_verified=abort_ok,
        safety_gate_matrix_verified=safety_ok,
        expected_input_index_verified=input_idx_ok,
        expected_output_index_verified=output_idx_ok,
        noop_boundary_verified=noop_ok,
        rollback_noop_policy_verified=policy_ok,
        blocked_operation_attempt_counts=blueprint_dict.get("blocked_operation_attempt_counts", {}),
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
        software_validation_caveat=caveat
    )

    report.runner_readiness_report_digest = hash_waveguide_package_runner_readiness_audit_report(report)
    return report


def validate_waveguide_package_runner_readiness_audit_report(report: Any) -> Tuple[bool, List[str]]:
    report_dict = _load_dict(report)
    if not report_dict:
        return False, ["PACKAGE_RUNNER_READINESS_INVALID"]

    reasons = []
    is_valid = True

    if report_dict.get("runner_readiness_report_id") != "SOL-WAVEGUIDE-PACKAGE-RUNNER-READINESS-AUDIT-REPORT":
        is_valid = False
        reasons.append("RUNNER_READINESS_REPORT_INVALID_ID")

    if report_dict.get("runner_readiness_report_version") != 1:
        is_valid = False
        reasons.append("RUNNER_READINESS_REPORT_INVALID_VERSION")

    # Validate cases
    cases = report_dict.get("audited_cases", [])
    if not cases or len(cases) != 34:
        is_valid = False
        reasons.append("RUNNER_READINESS_REPORT_CASE_COUNT_MISMATCH")
    else:
        for c in cases:
            recorded = c.get("runner_readiness_case_digest", "")
            recomputed = hash_waveguide_package_runner_readiness_audit_case(c)
            if recorded != recomputed or not recorded:
                is_valid = False
                reasons.append("RUNNER_READINESS_CASE_DIGEST_MISMATCH")

    # Verify noop boundary and policy
    if report_dict.get("noop_boundary_verified") is not True:
        is_valid = False
    if report_dict.get("rollback_noop_policy_verified") is not True:
        is_valid = False
    if report_dict.get("abort_condition_matrix_verified") is not True:
        is_valid = False
    if report_dict.get("safety_gate_matrix_verified") is not True:
        is_valid = False

    # Check that performed flags in report are false
    flag_fields = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in flag_fields:
        if report_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUNNER_READINESS_REPORT_MUTATION_PERFORMED_{flag.upper()}")

    # Check report digest
    recorded_digest = report_dict.get("runner_readiness_report_digest", "")
    recomputed_digest = hash_waveguide_package_runner_readiness_audit_report(report_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("RUNNER_READINESS_REPORT_DIGEST_MISMATCH")

    status = report_dict.get("runner_readiness_report_status", "")
    if is_valid and status == "package_runner_readiness_verified":
        reasons.append("PACKAGE_RUNNER_READINESS_VERIFIED")
    else:
        is_valid = False
        reasons.append("PACKAGE_RUNNER_READINESS_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_runner_readiness_audit_report(report: Any) -> str:
    report_dict = _load_dict(report)
    if not report_dict:
        return "Invalid Runner Readiness Audit Report"

    status = report_dict.get("runner_readiness_report_status", "unknown")
    digest = report_dict.get("runner_readiness_report_digest", "")
    cases_count = report_dict.get("verified_runner_readiness_count", 0)

    return (
        f"SOL Waveguide Runner Readiness Audit Report Summary:\n"
        f"  Report Status: {status}\n"
        f"  Report Digest: {digest}\n"
        f"  Verified Cases: {cases_count}\n"
    )


def export_waveguide_package_runner_readiness_audit_report(report: Any, filepath: str) -> None:
    report_dict = _load_dict(report)
    if not report_dict:
        raise ValueError("Cannot export invalid runner readiness report data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_runner_readiness_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def index_waveguide_runner_readiness_cases_by_status(cases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for c in cases:
        c_dict = _load_dict(c)
        if c_dict:
            status = c_dict.get("runner_readiness_status", "unknown")
            idx.setdefault(status, []).append(c_dict)
    return idx


def index_waveguide_runner_readiness_cases_by_phase_type(cases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for c in cases:
        c_dict = _load_dict(c)
        if c_dict:
            ptype = c_dict.get("phase_type", "unknown")
            idx.setdefault(ptype, []).append(c_dict)
    return idx
