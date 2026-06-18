# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Physical Execution Gate Validator / Gate Preflight Auditor.
Independently verifies the physical execution gate, checks constraints and allowance matrices,
and compiles a gate-preflight audit report.
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
from sol_waveguide_package_assembly_physical_execution_gate import (
    validate_waveguide_package_assembly_physical_execution_gate,
    hash_waveguide_package_assembly_physical_execution_gate
)
from sol_waveguide_package_runner_noop_dry_run_transcript_validator import (
    validate_waveguide_package_runner_transcript_audit_report,
    hash_waveguide_package_runner_transcript_audit_report
)


@dataclass
class WaveguidePackagePhysicalGatePreflightAuditCase:
    physical_gate_preflight_case_id: str
    package_assembly_physical_execution_gate_id: str
    package_assembly_physical_execution_gate_path: str
    physical_execution_gate_digest_recorded: str
    physical_execution_gate_digest_recomputed: str
    physical_execution_gate_digest_match: bool
    physical_execution_gate_status: str
    physical_execution_gate_decision: str
    physical_gate_preflight_status: str  # physical_gate_preflight_verified, etc.
    source_transcript_audit_report_digest_recorded: str
    source_transcript_audit_report_digest_recomputed: str
    source_transcript_audit_report_digest_match: bool
    source_transcript_audit_report_valid: bool
    source_transcript_audit_report_status: str
    future_physical_execution_request_allowed: bool
    physical_execution_permitted_by_gate: bool
    requires_explicit_operator_approval: bool
    requires_separate_physical_runner: bool
    requires_gate_preflight_audit: bool
    requires_local_filesystem_scope_confirmation: bool
    requires_archive_creation_still_disabled_until_runner: bool
    requires_upload_still_disabled_until_separate_publication_gate: bool
    gate_constraints_verified: bool
    gate_allowances_verified: bool
    gate_prohibitions_verified: bool
    gate_guard_requirements_verified: bool
    gate_noop_boundary_verified: bool
    gate_rollback_noop_policy_verified: bool
    gate_boolean_matrix_verified: bool
    blocked_operation_counts_verified: bool
    verified_transcript_audit_case_count: int
    verified_noop_event_count: int
    total_noop_event_count: int
    total_authorized_file_count: int
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
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    physical_gate_preflight_case_digest: str = ""


@dataclass
class WaveguidePackagePhysicalGatePreflightAuditReport:
    physical_gate_preflight_report_id: str
    physical_gate_preflight_report_version: int
    physical_gate_preflight_report_status: str  # package_physical_execution_gate_audit_verified, etc.
    source_physical_execution_gate_digest: str
    source_transcript_audit_report_digest: str
    source_noop_dry_run_transcript_digest: str
    source_runner_invocation_envelope_digest: str
    source_runner_readiness_report_digest: str
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
    audited_cases: List[WaveguidePackagePhysicalGatePreflightAuditCase]
    verified_physical_gate_preflight_cases: List[str]
    blocked_physical_gate_preflight_cases: List[str]
    warning_physical_gate_preflight_cases: List[str]
    invalid_physical_gate_preflight_cases: List[str]
    verified_physical_gate_preflight_count: int
    blocked_physical_gate_preflight_count: int
    warning_physical_gate_preflight_count: int
    invalid_physical_gate_preflight_count: int
    physical_execution_gate_status: str
    physical_execution_gate_decision: str
    future_physical_execution_request_allowed: bool
    physical_execution_permitted_by_gate: bool
    requires_explicit_operator_approval: bool
    requires_separate_physical_runner: bool
    requires_gate_preflight_audit: bool
    requires_local_filesystem_scope_confirmation: bool
    requires_archive_creation_still_disabled_until_runner: bool
    requires_upload_still_disabled_until_separate_publication_gate: bool
    verified_transcript_audit_case_count: int
    verified_noop_event_count: int
    total_noop_event_count: int
    blueprint_phase_count: int
    planned_execution_step_count: int
    total_authorized_file_count: int
    skipped_operation_count: int
    event_sequence_verified: bool
    event_counts_verified: bool
    skipped_operation_matrix_verified: bool
    noop_boundary_verified: bool
    gate_constraints: List[str]
    gate_allowances: List[str]
    gate_prohibitions: List[str]
    gate_guard_requirements: List[str]
    gate_noop_boundary: Dict[str, bool]
    gate_rollback_noop_policy: Dict[str, Any]
    gate_boolean_matrix_verified: bool
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
    physical_gate_preflight_report_digest: str = ""


def hash_waveguide_package_physical_gate_preflight_audit_case(case: Any) -> str:
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
    c_dict_copy.pop("physical_gate_preflight_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_package_physical_gate_preflight_audit_report(report: Any) -> str:
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
    r_dict_copy.pop("physical_gate_preflight_report_digest", None)
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


def recompute_waveguide_package_assembly_physical_execution_gate_digest(
    gate_path_or_dict: Any
) -> str:
    gate_dict = _load_dict(gate_path_or_dict)
    if gate_dict:
        return hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    return ""


def validate_waveguide_package_physical_gate_boolean_matrix(gate_dict: Dict[str, Any]) -> bool:
    """
    Verifies performed mutation flags in gate are strictly false.
    """
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    return all(gate_dict.get(flag) is False for flag in perf_flags)


def validate_waveguide_package_physical_gate_constraints(constraints: List[str]) -> bool:
    expected = [
        "physical_execution_request_allowed_strictly_for_review",
        "separate_physical_runner_required_for_actual_execution",
        "requires_explicit_operator_approval_on_physical_runner",
        "requires_separate_gate_preflight_audit",
        "requires_local_filesystem_scope_confirmation",
        "requires_archive_creation_still_disabled_until_runner",
        "requires_upload_still_disabled_until_separate_publication_gate"
    ]
    return all(c in constraints for c in expected)


def validate_waveguide_package_physical_gate_allowances(allowances: List[str]) -> bool:
    expected = [
        "future_physical_execution_request_may_be_submitted",
        "future_physical_execution_audit_may_be_performed",
        "controlled_local_filesystem_runner_invocation_allowed_in_next_slice"
    ]
    return all(a in allowances for a in expected)


def validate_waveguide_package_physical_gate_prohibitions(prohibitions: List[str]) -> bool:
    expected = [
        "no_direct_physical_execution_permitted_by_execution_gate",
        "no_archive_creation_permitted_by_execution_gate",
        "no_file_copy_permitted_by_execution_gate",
        "no_directory_creation_permitted_by_execution_gate",
        "no_upload_permitted_by_execution_gate",
        "no_deployment_permitted_by_execution_gate",
        "no_signing_permitted_by_execution_gate",
        "no_external_publication_permitted_by_execution_gate",
        "no_production_mutation_permitted_by_execution_gate"
    ]
    return all(p in prohibitions for p in expected)


def validate_waveguide_package_physical_gate_guard_requirements(guards: List[str]) -> bool:
    expected = [
        "transcript_audit_report_digest_matches",
        "noop_dry_run_transcript_digest_matches",
        "runner_invocation_envelope_digest_matches",
        "runner_readiness_report_digest_matches",
        "run_execution_blueprint_digest_matches",
        "separate_physical_runner_boundary_acknowledged",
        "direct_physical_execution_remains_disabled",
        "direct_archive_creation_remains_disabled",
        "direct_file_copy_remains_disabled",
        "direct_directory_creation_remains_disabled",
        "direct_upload_remains_disabled",
        "direct_deployment_remains_disabled",
        "direct_signing_remains_disabled",
        "direct_external_publication_remains_disabled",
        "direct_production_mutation_remains_disabled"
    ]
    return all(g in guards for g in expected)


def validate_waveguide_package_physical_gate_noop_boundary(noop: Dict[str, bool]) -> bool:
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


def validate_waveguide_package_physical_gate_rollback_noop_policy(policy: Dict[str, Any]) -> bool:
    return (
        policy.get("rollback_required") is False and
        policy.get("rollback_reason") == "no_physical_run_performed" and
        policy.get("rollback_scope") == "metadata_only" and
        policy.get("rollback_operations") == []
    )


def validate_waveguide_package_physical_gate_blocked_operation_counts(counts: Dict[str, int]) -> bool:
    expected_ops = [
        "archive_creation", "deployment", "directory_creation", "external_publication",
        "external_signing", "file_copy", "production_mutation", "upload"
    ]
    return all(counts.get(op, 0) == 0 for op in expected_ops)


def build_waveguide_package_physical_gate_preflight_audit_case(
    gate_dict: Dict[str, Any],
    report_dict: Dict[str, Any]
) -> WaveguidePackagePhysicalGatePreflightAuditCase:
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reasons = ["PHYSICAL_GATE_PREFLIGHT_CASE_CANONICAL"]
    is_valid = True

    # 1. Gate digest check
    recorded_gate_digest = gate_dict.get("package_assembly_physical_execution_gate_digest", "")
    recomputed_gate_digest = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    gate_digest_match = (recorded_gate_digest == recomputed_gate_digest) and (recorded_gate_digest != "")
    if not gate_digest_match:
        is_valid = False
        reasons.append("PHYSICAL_GATE_DIGEST_MISMATCH")

    # 2. Transcript audit report validation
    is_report_valid, _ = validate_waveguide_package_runner_transcript_audit_report(report_dict)
    recorded_report_digest = gate_dict.get("source_transcript_audit_report_digest", "")
    recomputed_report_digest = hash_waveguide_package_runner_transcript_audit_report(report_dict)
    report_digest_match = (recorded_report_digest == recomputed_report_digest) and (recorded_report_digest != "")
    if not report_digest_match:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_DIGEST_MISMATCH")
    if not is_report_valid or report_dict.get("transcript_audit_report_status") != "package_runner_noop_transcript_audit_verified":
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_INVALID")

    # 3. Decision matrices and logic checks
    constraints_ok = validate_waveguide_package_physical_gate_constraints(gate_dict.get("gate_constraints", []))
    allowances_ok = validate_waveguide_package_physical_gate_allowances(gate_dict.get("gate_allowances", []))
    prohibitions_ok = validate_waveguide_package_physical_gate_prohibitions(gate_dict.get("gate_prohibitions", []))
    guards_ok = validate_waveguide_package_physical_gate_guard_requirements(gate_dict.get("gate_guard_requirements", []))
    noop_ok = validate_waveguide_package_physical_gate_noop_boundary(gate_dict.get("gate_noop_boundary", {}))
    policy_ok = validate_waveguide_package_physical_gate_rollback_noop_policy(gate_dict.get("gate_rollback_noop_policy", {}))
    boolean_matrix_ok = validate_waveguide_package_physical_gate_boolean_matrix(gate_dict)
    counts_ok = validate_waveguide_package_physical_gate_blocked_operation_counts(gate_dict.get("blocked_operation_attempt_counts", {}))

    if not constraints_ok or not allowances_ok or not prohibitions_ok or not guards_ok or not noop_ok or not policy_ok or not boolean_matrix_ok or not counts_ok:
        is_valid = False

    # Check status and decision
    if gate_dict.get("physical_execution_gate_status") != "package_physical_execution_gate_ready":
        is_valid = False
        reasons.append("PHYSICAL_EXECUTION_GATE_STATUS_NOT_READY")
    if gate_dict.get("physical_execution_gate_decision") != "allow_future_physical_execution_request_review":
        is_valid = False
        reasons.append("PHYSICAL_EXECUTION_GATE_DECISION_MISMATCH")

    # Check requirement flags
    if gate_dict.get("future_physical_execution_request_allowed") is not True:
        is_valid = False
    if gate_dict.get("physical_execution_permitted_by_gate") is not False:
        is_valid = False
    if gate_dict.get("requires_explicit_operator_approval") is not True:
        is_valid = False
    if gate_dict.get("requires_separate_physical_runner") is not True:
        is_valid = False
    if gate_dict.get("requires_gate_preflight_audit") is not True:
        is_valid = False
    if gate_dict.get("requires_local_filesystem_scope_confirmation") is not True:
        is_valid = False

    case_status = "physical_gate_preflight_verified" if is_valid else "physical_gate_preflight_blocked"
    if is_valid:
        reasons.append("PHYSICAL_GATE_PREFLIGHT_VERIFIED")
        reasons.append("FUTURE_PHYSICAL_EXECUTION_REQUEST_ALLOWED")
        reasons.append("PHYSICAL_EXECUTION_RESTRICTED_BY_GATE")
    else:
        reasons.append("PHYSICAL_GATE_PREFLIGHT_BLOCKED")

    case = WaveguidePackagePhysicalGatePreflightAuditCase(
        physical_gate_preflight_case_id=f"SOL-WAVEGUIDE-PHYSICAL-GATE-CASE-{gate_dict.get('package_assembly_physical_execution_gate_id')}",
        package_assembly_physical_execution_gate_id=gate_dict.get("package_assembly_physical_execution_gate_id", ""),
        package_assembly_physical_execution_gate_path="",
        physical_execution_gate_digest_recorded=recorded_gate_digest,
        physical_execution_gate_digest_recomputed=recomputed_gate_digest,
        physical_execution_gate_digest_match=gate_digest_match,
        physical_execution_gate_status=gate_dict.get("physical_execution_gate_status", ""),
        physical_execution_gate_decision=gate_dict.get("physical_execution_gate_decision", ""),
        physical_gate_preflight_status=case_status,
        source_transcript_audit_report_digest_recorded=recorded_report_digest,
        source_transcript_audit_report_digest_recomputed=recomputed_report_digest,
        source_transcript_audit_report_digest_match=report_digest_match,
        source_transcript_audit_report_valid=is_report_valid,
        source_transcript_audit_report_status=report_dict.get("transcript_audit_report_status", ""),
        future_physical_execution_request_allowed=gate_dict.get("future_physical_execution_request_allowed", False),
        physical_execution_permitted_by_gate=gate_dict.get("physical_execution_permitted_by_gate", False),
        requires_explicit_operator_approval=gate_dict.get("requires_explicit_operator_approval", False),
        requires_separate_physical_runner=gate_dict.get("requires_separate_physical_runner", False),
        requires_gate_preflight_audit=gate_dict.get("requires_gate_preflight_audit", False),
        requires_local_filesystem_scope_confirmation=gate_dict.get("requires_local_filesystem_scope_confirmation", False),
        requires_archive_creation_still_disabled_until_runner=gate_dict.get("requires_archive_creation_still_disabled_until_runner", False),
        requires_upload_still_disabled_until_separate_publication_gate=gate_dict.get("requires_upload_still_disabled_until_separate_publication_gate", False),
        gate_constraints_verified=constraints_ok,
        gate_allowances_verified=allowances_ok,
        gate_prohibitions_verified=prohibitions_ok,
        gate_guard_requirements_verified=guards_ok,
        gate_noop_boundary_verified=noop_ok,
        gate_rollback_noop_policy_verified=policy_ok,
        gate_boolean_matrix_verified=boolean_matrix_ok,
        blocked_operation_counts_verified=counts_ok,
        verified_transcript_audit_case_count=gate_dict.get("verified_transcript_audit_case_count", 0),
        verified_noop_event_count=gate_dict.get("verified_noop_event_count", 0),
        total_noop_event_count=gate_dict.get("total_noop_event_count", 0),
        total_authorized_file_count=gate_dict.get("total_authorized_file_count", 0),
        physical_execution_performed=gate_dict.get("physical_execution_performed", False),
        archive_creation_performed=gate_dict.get("archive_creation_performed", False),
        file_copy_performed=gate_dict.get("file_copy_performed", False),
        directory_creation_performed=gate_dict.get("directory_creation_performed", False),
        upload_performed=gate_dict.get("upload_performed", False),
        deployment_performed=gate_dict.get("deployment_performed", False),
        signing_performed=gate_dict.get("signing_performed", False),
        external_publication_performed=gate_dict.get("external_publication_performed", False),
        production_mutation_performed=gate_dict.get("production_mutation_performed", False),
        blocked_operation_attempt_counts=gate_dict.get("blocked_operation_attempt_counts", {}),
        reason_codes=sorted(list(set(reasons))),
        notes=[],
        software_validation_caveat=caveat
    )
    case.physical_gate_preflight_case_digest = hash_waveguide_package_physical_gate_preflight_audit_case(case)
    return case


def validate_waveguide_package_assembly_physical_execution_gate_independently(
    gate_path_or_dict: Any,
    report_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    gate_dict = _load_dict(gate_path_or_dict)
    report_dict = _load_dict(report_path_or_dict)

    reasons = []
    is_valid = True

    if not gate_dict or not report_dict:
        return False, ["PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_INVALID"]

    gate_ok, _ = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    report_ok, _ = validate_waveguide_package_runner_transcript_audit_report(report_dict)

    if not gate_ok:
        is_valid = False
        reasons.append("PHYSICAL_EXECUTION_GATE_INVALID")
    if not report_ok:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_INVALID")

    # Cross check digests
    recorded_report_digest = gate_dict.get("source_transcript_audit_report_digest", "")
    recomputed_report_digest = hash_waveguide_package_runner_transcript_audit_report(report_dict)
    if recorded_report_digest != recomputed_report_digest or not recorded_report_digest:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_DIGEST_MISMATCH")

    if is_valid:
        reasons.append("PACKAGE_PHYSICAL_GATE_AUDIT_VERIFIED")
    else:
        reasons.append("PACKAGE_PHYSICAL_GATE_AUDIT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_physical_gate_preflight_audit_report(
    gate_path_or_dict: Any,
    report_path_or_dict: Any
) -> WaveguidePackagePhysicalGatePreflightAuditReport:
    gate_dict = _load_dict(gate_path_or_dict)
    report_dict = _load_dict(report_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not gate_dict or not report_dict:
        return WaveguidePackagePhysicalGatePreflightAuditReport(
            physical_gate_preflight_report_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-PHYSICAL-EXECUTION-GATE-PREFLIGHT-AUDIT-REPORT",
            physical_gate_preflight_report_version=1,
            physical_gate_preflight_report_status="package_physical_execution_gate_audit_invalid",
            source_physical_execution_gate_digest="",
            source_transcript_audit_report_digest="",
            source_noop_dry_run_transcript_digest="",
            source_runner_invocation_envelope_digest="",
            source_runner_readiness_report_digest="",
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
            verified_physical_gate_preflight_cases=[],
            blocked_physical_gate_preflight_cases=[],
            warning_physical_gate_preflight_cases=[],
            invalid_physical_gate_preflight_cases=[],
            verified_physical_gate_preflight_count=0,
            blocked_physical_gate_preflight_count=0,
            warning_physical_gate_preflight_count=0,
            invalid_physical_gate_preflight_count=0,
            physical_execution_gate_status="package_physical_execution_gate_invalid",
            physical_execution_gate_decision="invalid_physical_execution_gate",
            future_physical_execution_request_allowed=False,
            physical_execution_permitted_by_gate=False,
            requires_explicit_operator_approval=False,
            requires_separate_physical_runner=False,
            requires_gate_preflight_audit=False,
            requires_local_filesystem_scope_confirmation=False,
            requires_archive_creation_still_disabled_until_runner=False,
            requires_upload_still_disabled_until_separate_publication_gate=False,
            verified_transcript_audit_case_count=0,
            verified_noop_event_count=0,
            total_noop_event_count=0,
            blueprint_phase_count=0,
            planned_execution_step_count=0,
            total_authorized_file_count=0,
            skipped_operation_count=0,
            event_sequence_verified=False,
            event_counts_verified=False,
            skipped_operation_matrix_verified=False,
            noop_boundary_verified=False,
            gate_constraints=[],
            gate_allowances=[],
            gate_prohibitions=[],
            gate_guard_requirements=[],
            gate_noop_boundary={},
            gate_rollback_noop_policy={},
            gate_boolean_matrix_verified=False,
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
            reason_codes=["PHYSICAL_GATE_INVALID", "PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_INVALID"],
            software_validation_caveat=caveat
        )

    is_compat_ok, compat_reasons = validate_waveguide_package_assembly_physical_execution_gate_independently(
        gate_dict, report_dict
    )

    case = build_waveguide_package_physical_gate_preflight_audit_case(gate_dict, report_dict)
    cases = [case]

    verified_cases = [c.physical_gate_preflight_case_id for c in cases if c.physical_gate_preflight_status == "physical_gate_preflight_verified"]
    blocked_cases = [c.physical_gate_preflight_case_id for c in cases if c.physical_gate_preflight_status == "physical_gate_preflight_blocked"]
    warning_cases = [c.physical_gate_preflight_case_id for c in cases if c.physical_gate_preflight_status == "physical_gate_preflight_warning"]
    invalid_cases = [c.physical_gate_preflight_case_id for c in cases if c.physical_gate_preflight_status == "physical_gate_preflight_invalid"]

    noop_boundary_ok = validate_waveguide_package_physical_gate_noop_boundary(gate_dict.get("gate_noop_boundary", {}))
    policy_ok = validate_waveguide_package_physical_gate_rollback_noop_policy(gate_dict.get("gate_rollback_noop_policy", {}))
    boolean_matrix_ok = validate_waveguide_package_physical_gate_boolean_matrix(gate_dict)
    counts_ok = validate_waveguide_package_physical_gate_blocked_operation_counts(gate_dict.get("blocked_operation_attempt_counts", {}))

    is_report_ok = (
        is_compat_ok and
        noop_boundary_ok and
        policy_ok and
        boolean_matrix_ok and
        counts_ok and
        len(blocked_cases) == 0 and
        len(invalid_cases) == 0
    )

    report_status = "package_physical_execution_gate_audit_verified" if is_report_ok else "package_physical_execution_gate_audit_invalid"
    reasons = ["PHYSICAL_GATE_PREFLIGHT_REPORT_CANONICAL"]
    if is_report_ok:
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_VERIFIED")
    else:
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_INVALID")

    report = WaveguidePackagePhysicalGatePreflightAuditReport(
        physical_gate_preflight_report_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-PHYSICAL-EXECUTION-GATE-PREFLIGHT-AUDIT-REPORT",
        physical_gate_preflight_report_version=1,
        physical_gate_preflight_report_status=report_status,
        source_physical_execution_gate_digest=gate_dict.get("package_assembly_physical_execution_gate_digest", ""),
        source_transcript_audit_report_digest=gate_dict.get("source_transcript_audit_report_digest", ""),
        source_noop_dry_run_transcript_digest=gate_dict.get("source_noop_dry_run_transcript_digest", ""),
        source_runner_invocation_envelope_digest=gate_dict.get("source_runner_invocation_envelope_digest", ""),
        source_runner_readiness_report_digest=gate_dict.get("source_runner_readiness_report_digest", ""),
        source_run_execution_blueprint_digest=gate_dict.get("source_run_execution_blueprint_digest", ""),
        source_run_preflight_report_digest=gate_dict.get("source_run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=gate_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=gate_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=gate_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=gate_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=gate_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=gate_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=gate_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=gate_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=gate_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=gate_dict.get("source_artifact_catalog_digest", ""),
        audited_cases=cases,
        verified_physical_gate_preflight_cases=verified_cases,
        blocked_physical_gate_preflight_cases=blocked_cases,
        warning_physical_gate_preflight_cases=warning_cases,
        invalid_physical_gate_preflight_cases=invalid_cases,
        verified_physical_gate_preflight_count=len(verified_cases),
        blocked_physical_gate_preflight_count=len(blocked_cases),
        warning_physical_gate_preflight_count=len(warning_cases),
        invalid_physical_gate_preflight_count=len(invalid_cases),
        physical_execution_gate_status=gate_dict.get("physical_execution_gate_status", ""),
        physical_execution_gate_decision=gate_dict.get("physical_execution_gate_decision", ""),
        future_physical_execution_request_allowed=gate_dict.get("future_physical_execution_request_allowed", False),
        physical_execution_permitted_by_gate=gate_dict.get("physical_execution_permitted_by_gate", False),
        requires_explicit_operator_approval=gate_dict.get("requires_explicit_operator_approval", False),
        requires_separate_physical_runner=gate_dict.get("requires_separate_physical_runner", False),
        requires_gate_preflight_audit=gate_dict.get("requires_gate_preflight_audit", False),
        requires_local_filesystem_scope_confirmation=gate_dict.get("requires_local_filesystem_scope_confirmation", False),
        requires_archive_creation_still_disabled_until_runner=gate_dict.get("requires_archive_creation_still_disabled_until_runner", False),
        requires_upload_still_disabled_until_separate_publication_gate=gate_dict.get("requires_upload_still_disabled_until_separate_publication_gate", False),
        verified_transcript_audit_case_count=gate_dict.get("verified_transcript_audit_case_count", 0),
        verified_noop_event_count=gate_dict.get("verified_noop_event_count", 0),
        total_noop_event_count=gate_dict.get("total_noop_event_count", 0),
        blueprint_phase_count=gate_dict.get("blueprint_phase_count", 0),
        planned_execution_step_count=gate_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=gate_dict.get("total_authorized_file_count", 0),
        skipped_operation_count=gate_dict.get("skipped_operation_count", 0),
        event_sequence_verified=gate_dict.get("event_sequence_verified", False),
        event_counts_verified=gate_dict.get("event_counts_verified", False),
        skipped_operation_matrix_verified=gate_dict.get("skipped_operation_matrix_verified", False),
        noop_boundary_verified=gate_dict.get("noop_boundary_verified", False),
        gate_constraints=sorted(gate_dict.get("gate_constraints", [])),
        gate_allowances=sorted(gate_dict.get("gate_allowances", [])),
        gate_prohibitions=sorted(gate_dict.get("gate_prohibitions", [])),
        gate_guard_requirements=sorted(gate_dict.get("gate_guard_requirements", [])),
        gate_noop_boundary=gate_dict.get("gate_noop_boundary", {}),
        gate_rollback_noop_policy=gate_dict.get("gate_rollback_noop_policy", {}),
        gate_boolean_matrix_verified=boolean_matrix_ok,
        blocked_operation_attempt_counts=gate_dict.get("blocked_operation_attempt_counts", {}),
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
    report.physical_gate_preflight_report_digest = hash_waveguide_package_physical_gate_preflight_audit_report(report)
    return report


def validate_waveguide_package_physical_gate_preflight_audit_report(report: Any) -> Tuple[bool, List[str]]:
    report_dict = _load_dict(report)
    if not report_dict:
        return False, ["PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_INVALID"]

    reasons = []
    is_valid = True

    if report_dict.get("physical_gate_preflight_report_id") != "SOL-WAVEGUIDE-PACKAGE-ASVISION-GATE-PREFLIGHT-AUDIT-REPORT" and report_dict.get("physical_gate_preflight_report_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-PHYSICAL-EXECUTION-GATE-PREFLIGHT-AUDIT-REPORT":
        # Let's verify both identity IDs
        if report_dict.get("physical_gate_preflight_report_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-PHYSICAL-EXECUTION-GATE-PREFLIGHT-AUDIT-REPORT":
            is_valid = False
            reasons.append("PHYSICAL_GATE_PREFLIGHT_REPORT_INVALID_ID")

    if report_dict.get("physical_gate_preflight_report_version") != 1:
        is_valid = False
        reasons.append("PHYSICAL_GATE_PREFLIGHT_REPORT_INVALID_VERSION")

    # Validate cases
    cases = report_dict.get("audited_cases", [])
    if not cases or len(cases) != 1:
        is_valid = False
        reasons.append("PHYSICAL_GATE_PREFLIGHT_REPORT_CASE_COUNT_MISMATCH")
    else:
        for c in cases:
            recorded = c.get("physical_gate_preflight_case_digest", "")
            recomputed = hash_waveguide_package_physical_gate_preflight_audit_case(c)
            if recorded != recomputed or not recorded:
                is_valid = False
                reasons.append("PHYSICAL_GATE_PREFLIGHT_CASE_DIGEST_MISMATCH")

    # Validate gate matrices
    if report_dict.get("gate_boolean_matrix_verified") is not True:
        is_valid = False

    # Check performed flags
    flag_fields = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in flag_fields:
        if report_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"PHYSICAL_GATE_PREFLIGHT_REPORT_MUTATION_PERFORMED_{flag.upper()}")

    # Check report digest
    recorded_digest = report_dict.get("physical_gate_preflight_report_digest", "")
    recomputed_digest = hash_waveguide_package_physical_gate_preflight_audit_report(report_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("PHYSICAL_GATE_PREFLIGHT_REPORT_DIGEST_MISMATCH")

    status = report_dict.get("physical_gate_preflight_report_status", "")
    if is_valid and status == "package_physical_execution_gate_audit_verified":
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_VERIFIED")
    else:
        is_valid = False
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_physical_gate_preflight_audit_report(report: Any) -> str:
    report_dict = _load_dict(report)
    if not report_dict:
        return "Invalid Gate Preflight Audit Report"

    status = report_dict.get("physical_gate_preflight_report_status", "unknown")
    digest = report_dict.get("physical_gate_preflight_report_digest", "")

    return (
        f"SOL Waveguide Physical Execution Gate Preflight Audit Report Summary:\n"
        f"  Report Status: {status}\n"
        f"  Report Digest: {digest}\n"
    )


def export_waveguide_package_physical_gate_preflight_audit_report(report: Any, filepath: str) -> None:
    report_dict = _load_dict(report)
    if not report_dict:
        raise ValueError("Cannot export invalid gate preflight audit report data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_physical_gate_preflight_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs
