# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Physical Execution Gate.
Consumes the verified Transcript Audit Report and defines the metadata gate for future physical run review.
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
from sol_waveguide_package_runner_noop_dry_run_transcript_validator import (
    validate_waveguide_package_runner_transcript_audit_report,
    hash_waveguide_package_runner_transcript_audit_report
)


@dataclass
class WaveguidePackageAssemblyPhysicalExecutionGate:
    package_assembly_physical_execution_gate_id: str
    package_assembly_physical_execution_gate_version: int
    physical_execution_gate_status: str  # package_physical_execution_gate_ready, etc.
    physical_execution_gate_decision: str  # allow_future_physical_execution_request_review, etc.
    physical_execution_gate_scope: str
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
    verified_transcript_audit_case_count: int
    blocked_transcript_audit_case_count: int
    warning_transcript_audit_case_count: int
    invalid_transcript_audit_case_count: int
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
    future_physical_execution_request_allowed: bool
    physical_execution_permitted_by_gate: bool
    requires_explicit_operator_approval: bool
    requires_separate_physical_runner: bool
    requires_gate_preflight_audit: bool
    requires_local_filesystem_scope_confirmation: bool
    requires_archive_creation_still_disabled_until_runner: bool
    requires_upload_still_disabled_until_separate_publication_gate: bool
    gate_constraints: List[str]
    gate_allowances: List[str]
    gate_prohibitions: List[str]
    gate_guard_requirements: List[str]
    gate_noop_boundary: Dict[str, bool]
    gate_rollback_noop_policy: Dict[str, Any]
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
    notes: List[str]
    software_validation_caveat: str
    package_assembly_physical_execution_gate_digest: str = ""


def hash_waveguide_package_assembly_physical_execution_gate(gate: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of physical execution gate excluding gate digest.
    """
    if hasattr(gate, "__dict__"):
        g_dict = asdict(gate)
    elif isinstance(gate, dict):
        g_dict = dict(gate)
    else:
        raise TypeError("gate must be a dictionary or a dataclass instance")

    g_dict_copy = dict(g_dict)
    g_dict_copy.pop("package_assembly_physical_execution_gate_digest", None)
    return hash_data(g_dict_copy)


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


def build_waveguide_package_physical_execution_gate_decision(status: str) -> str:
    if status == "package_physical_execution_gate_ready":
        return "allow_future_physical_execution_request_review"
    elif status == "package_physical_execution_gate_blocked":
        return "block_future_physical_execution_request_review"
    elif status == "package_physical_execution_gate_warning":
        return "manual_review_required"
    return "invalid_physical_execution_gate"


def validate_waveguide_package_physical_execution_gate_scope(scope: str) -> bool:
    return scope == "physical_execution_boundary_gate"


def validate_waveguide_package_physical_execution_gate_noop_boundary(noop: Dict[str, bool]) -> bool:
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


def validate_waveguide_package_physical_execution_gate_blocked_operation_counts(counts: Dict[str, int]) -> bool:
    expected_ops = [
        "archive_creation", "deployment", "directory_creation", "external_publication",
        "external_signing", "file_copy", "production_mutation", "upload"
    ]
    return all(counts.get(op, 0) == 0 for op in expected_ops)


def build_waveguide_package_assembly_physical_execution_gate(
    transcript_audit_report_path_or_dict: Any
) -> WaveguidePackageAssemblyPhysicalExecutionGate:
    report_dict = _load_dict(transcript_audit_report_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not report_dict:
        return WaveguidePackageAssemblyPhysicalExecutionGate(
            package_assembly_physical_execution_gate_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-PHYSICAL-EXECUTION-GATE",
            package_assembly_physical_execution_gate_version=1,
            physical_execution_gate_status="package_physical_execution_gate_invalid",
            physical_execution_gate_decision="invalid_physical_execution_gate",
            physical_execution_gate_scope="unknown",
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
            verified_transcript_audit_case_count=0,
            blocked_transcript_audit_case_count=0,
            warning_transcript_audit_case_count=0,
            invalid_transcript_audit_case_count=0,
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
            future_physical_execution_request_allowed=False,
            physical_execution_permitted_by_gate=False,
            requires_explicit_operator_approval=False,
            requires_separate_physical_runner=False,
            requires_gate_preflight_audit=False,
            requires_local_filesystem_scope_confirmation=False,
            requires_archive_creation_still_disabled_until_runner=False,
            requires_upload_still_disabled_until_separate_publication_gate=False,
            gate_constraints=[],
            gate_allowances=[],
            gate_prohibitions=[],
            gate_guard_requirements=[],
            gate_noop_boundary={},
            gate_rollback_noop_policy={},
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
            reason_codes=["TRANSCRIPT_AUDIT_REPORT_INVALID", "PACKAGE_PHYSICAL_EXECUTION_GATE_INVALID"],
            notes=[],
            software_validation_caveat=caveat
        )

    is_report_ok, _ = validate_waveguide_package_runner_transcript_audit_report(report_dict)
    reasons = ["PHYSICAL_GATE_CANONICAL"]
    is_valid = True

    if not is_report_ok or report_dict.get("transcript_audit_report_status") != "package_runner_noop_transcript_audit_verified":
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_INVALID")
    else:
        reasons.append("TRANSCRIPT_AUDIT_REPORT_VALID")

    # Double check audit counts
    verified_cases = report_dict.get("verified_transcript_audit_count", 0)
    blocked_cases = report_dict.get("blocked_transcript_audit_count", 0)
    warning_cases = report_dict.get("warning_transcript_audit_count", 0)
    invalid_cases = report_dict.get("invalid_transcript_audit_count", 0)

    if verified_cases != 182 or blocked_cases > 0 or warning_cases > 0 or invalid_cases > 0:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_CASES_BLOCKED_OR_INVALID")

    # Boundaries
    allowed = True if is_valid else False
    permitted = False

    operator_approval = True if is_valid else False
    separate_runner = True if is_valid else False
    gate_preflight = True if is_valid else False
    local_scope = True if is_valid else False
    archive_disabled = True if is_valid else False
    upload_disabled = True if is_valid else False

    status = "package_physical_execution_gate_ready" if is_valid else "package_physical_execution_gate_invalid"
    decision = build_waveguide_package_physical_execution_gate_decision(status)

    if is_valid:
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_READY")
        reasons.append("PHYSICAL_EXECUTION_REQUEST_REVIEW_ALLOWED")
    else:
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_INVALID")

    constraints = [
        "physical_execution_request_allowed_strictly_for_review",
        "separate_physical_runner_required_for_actual_execution",
        "requires_explicit_operator_approval_on_physical_runner",
        "requires_separate_gate_preflight_audit",
        "requires_local_filesystem_scope_confirmation",
        "requires_archive_creation_still_disabled_until_runner",
        "requires_upload_still_disabled_until_separate_publication_gate"
    ]

    allowances = [
        "future_physical_execution_request_may_be_submitted",
        "future_physical_execution_audit_may_be_performed",
        "controlled_local_filesystem_runner_invocation_allowed_in_next_slice"
    ]

    prohibitions = [
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

    guards = [
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

    gate_noop_boundary = {
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

    gate_rollback_noop_policy = {
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

    gate = WaveguidePackageAssemblyPhysicalExecutionGate(
        package_assembly_physical_execution_gate_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-PHYSICAL-EXECUTION-GATE",
        package_assembly_physical_execution_gate_version=1,
        physical_execution_gate_status=status,
        physical_execution_gate_decision=decision,
        physical_execution_gate_scope="physical_execution_boundary_gate",
        source_transcript_audit_report_digest=report_dict.get("transcript_audit_report_digest", ""),
        source_noop_dry_run_transcript_digest=report_dict.get("source_noop_dry_run_transcript_digest", ""),
        source_runner_invocation_envelope_digest=report_dict.get("source_runner_invocation_envelope_digest", ""),
        source_runner_readiness_report_digest=report_dict.get("source_runner_readiness_report_digest", ""),
        source_run_execution_blueprint_digest=report_dict.get("source_run_execution_blueprint_digest", ""),
        source_run_preflight_report_digest=report_dict.get("source_run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=report_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=report_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=report_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=report_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=report_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=report_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=report_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=report_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=report_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=report_dict.get("source_artifact_catalog_digest", ""),
        verified_transcript_audit_case_count=verified_cases,
        blocked_transcript_audit_case_count=blocked_cases,
        warning_transcript_audit_case_count=warning_cases,
        invalid_transcript_audit_case_count=invalid_cases,
        verified_noop_event_count=report_dict.get("verified_noop_event_count", 0),
        total_noop_event_count=report_dict.get("total_noop_event_count", 0),
        blueprint_phase_count=report_dict.get("blueprint_phase_count", 0),
        planned_execution_step_count=report_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=report_dict.get("total_authorized_file_count", 0),
        skipped_operation_count=report_dict.get("skipped_operation_count", 0),
        event_sequence_verified=report_dict.get("event_sequence_verified", False),
        event_counts_verified=report_dict.get("event_counts_verified", False),
        skipped_operation_matrix_verified=report_dict.get("skipped_operation_matrix_verified", False),
        noop_boundary_verified=report_dict.get("noop_boundary_verified", False),
        future_physical_execution_request_allowed=allowed,
        physical_execution_permitted_by_gate=permitted,
        requires_explicit_operator_approval=operator_approval,
        requires_separate_physical_runner=separate_runner,
        requires_gate_preflight_audit=gate_preflight,
        requires_local_filesystem_scope_confirmation=local_scope,
        requires_archive_creation_still_disabled_until_runner=archive_disabled,
        requires_upload_still_disabled_until_separate_publication_gate=upload_disabled,
        gate_constraints=sorted(constraints),
        gate_allowances=sorted(allowances),
        gate_prohibitions=sorted(prohibitions),
        gate_guard_requirements=sorted(guards),
        gate_noop_boundary=gate_noop_boundary,
        gate_rollback_noop_policy=gate_rollback_noop_policy,
        blocked_operation_attempt_counts=blocked_operation_attempt_counts,
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

    gate.package_assembly_physical_execution_gate_digest = hash_waveguide_package_assembly_physical_execution_gate(gate)
    return gate


def validate_waveguide_package_assembly_physical_execution_gate(gate: Any) -> Tuple[bool, List[str]]:
    gate_dict = _load_dict(gate)
    if not gate_dict:
        return False, ["PACKAGE_PHYSICAL_EXECUTION_GATE_INVALID"]

    reasons = []
    is_valid = True

    if gate_dict.get("package_assembly_physical_execution_gate_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-PHYSICAL-EXECUTION-GATE":
        is_valid = False
        reasons.append("PHYSICAL_GATE_INVALID_ID")

    if gate_dict.get("package_assembly_physical_execution_gate_version") != 1:
        is_valid = False
        reasons.append("PHYSICAL_GATE_INVALID_VERSION")

    # Scope validation
    if not validate_waveguide_package_physical_execution_gate_scope(gate_dict.get("physical_execution_gate_scope", "")):
        is_valid = False
        reasons.append("PHYSICAL_GATE_INVALID_SCOPE")

    # Case counts check
    verified_cases = gate_dict.get("verified_transcript_audit_case_count", 0)
    blocked_cases = gate_dict.get("blocked_transcript_audit_case_count", 0)
    warning_cases = gate_dict.get("warning_transcript_audit_case_count", 0)
    invalid_cases = gate_dict.get("invalid_transcript_audit_case_count", 0)

    if verified_cases != 182 or blocked_cases > 0 or warning_cases > 0 or invalid_cases > 0:
        is_valid = False
        reasons.append("PHYSICAL_GATE_TRANSCRIPT_AUDIT_CASES_BLOCKED_OR_INVALID")

    # Check that allowances, constraints, prohibitions, and guards are present
    req_lists = [
        "gate_constraints", "gate_allowances",
        "gate_prohibitions", "gate_guard_requirements"
    ]
    for lst in req_lists:
        if not gate_dict.get(lst):
            is_valid = False
            reasons.append(f"PHYSICAL_GATE_MISSING_{lst.upper()}")

    # Check matrices, no-op boundary, rollback policy
    if not validate_waveguide_package_physical_execution_gate_noop_boundary(gate_dict.get("gate_noop_boundary", {})):
        is_valid = False
    if gate_dict.get("gate_rollback_noop_policy", {}).get("rollback_required") is not False:
        is_valid = False

    # Check permission values
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

    # Check performed flags
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in perf_flags:
        if gate_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"PHYSICAL_GATE_PERFORMED_FLAG_TRUE_{flag.upper()}")

    # Check blocked operations counts
    if not validate_waveguide_package_physical_execution_gate_blocked_operation_counts(gate_dict.get("blocked_operation_attempt_counts", {})):
        is_valid = False

    # Check gate digest
    recorded_digest = gate_dict.get("package_assembly_physical_execution_gate_digest", "")
    recomputed_digest = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("PHYSICAL_GATE_DIGEST_MISMATCH")

    status = gate_dict.get("physical_execution_gate_status", "")
    if is_valid and status == "package_physical_execution_gate_ready":
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_READY")
    else:
        is_valid = False
        reasons.append("PACKAGE_PHYSICAL_EXECUTION_GATE_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_assembly_physical_execution_gate(gate: Any) -> str:
    gate_dict = _load_dict(gate)
    if not gate_dict:
        return "Invalid Physical Execution Gate"

    status = gate_dict.get("physical_execution_gate_status", "unknown")
    digest = gate_dict.get("package_assembly_physical_execution_gate_digest", "")
    decision = gate_dict.get("physical_execution_gate_decision", "")

    return (
        f"SOL Waveguide Physical Execution Gate Summary:\n"
        f"  Gate Status: {status}\n"
        f"  Gate Decision: {decision}\n"
        f"  Gate Digest: {digest}\n"
    )


def export_waveguide_package_assembly_physical_execution_gate(gate: Any, filepath: str) -> None:
    gate_dict = _load_dict(gate)
    if not gate_dict:
        raise ValueError("Cannot export invalid physical execution gate data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(gate_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_assembly_physical_execution_gates(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def index_waveguide_package_physical_execution_gate_references_by_source(gate: Any) -> Dict[str, str]:
    gate_dict = _load_dict(gate) or {}
    idx = {}
    for key, val in gate_dict.items():
        if key.startswith("source_") and isinstance(val, str) and val:
            idx[key] = val
    return idx
