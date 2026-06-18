# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Runner Invocation Envelope.
Binds a future runner request to the verified runner-readiness report and blueprint digests.
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
from sol_waveguide_package_assembly_run_blueprint_validator import (
    validate_waveguide_package_runner_readiness_audit_report,
    hash_waveguide_package_runner_readiness_audit_report
)


@dataclass
class WaveguidePackageAssemblyRunnerInvocationEnvelope:
    package_assembly_runner_invocation_envelope_id: str
    package_assembly_runner_invocation_envelope_version: int
    runner_invocation_request_id: str
    runner_invocation_kind: str  # metadata_only_noop_package_runner_invocation, etc.
    runner_invocation_status: str  # package_runner_invocation_ready, etc.
    runner_invocation_decision: str  # authorize_noop_runner_invocation, etc.
    runner_invocation_scope: str
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
    verified_runner_readiness_case_count: int
    blocked_runner_readiness_case_count: int
    warning_runner_readiness_case_count: int
    invalid_runner_readiness_case_count: int
    blueprint_phase_count: int
    ready_blueprint_phase_count: int
    planned_execution_step_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    authorized_target_package_sections: List[str]
    authorized_phase_types: List[str]
    authorized_package_roles: List[str]
    authorized_artifact_types: List[str]
    authorized_rc_scopes: List[str]
    authorized_expected_input_references: List[str]
    authorized_expected_output_references: List[str]
    authorized_target_package_paths: List[str]
    authorized_artifact_digests: List[str]
    authorized_phase_digests: List[str]
    authorized_runner_readiness_case_digests: List[str]
    runner_invocation_constraints: List[str]
    runner_invocation_allowances: List[str]
    runner_invocation_prohibitions: List[str]
    runner_invocation_guard_requirements: List[str]
    runner_invocation_noop_boundary: Dict[str, bool]
    runner_invocation_rollback_noop_policy: Dict[str, Any]
    blocked_operation_attempt_counts: Dict[str, int]
    specific_runner_invocation_authorized: bool
    metadata_only_runner_invocation: bool
    noop_dry_run_authorized: bool
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
    package_assembly_runner_invocation_envelope_digest: str = ""


def hash_waveguide_package_assembly_runner_invocation_envelope(envelope: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of envelope excluding envelope digest.
    """
    if hasattr(envelope, "__dict__"):
        e_dict = asdict(envelope)
    elif isinstance(envelope, dict):
        e_dict = dict(envelope)
    else:
        raise TypeError("envelope must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("package_assembly_runner_invocation_envelope_digest", None)
    return hash_data(e_dict_copy)


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


def build_waveguide_package_runner_invocation_request_identity(readiness_dict: Dict[str, Any]) -> str:
    report_id = readiness_dict.get("runner_readiness_report_id", "UNKNOWN")
    return f"SOL-WAVEGUIDE-RUNNER-INVOCATION-REQUEST-{report_id}"


def build_waveguide_package_runner_invocation_decision(status: str) -> str:
    if status == "package_runner_invocation_ready":
        return "authorize_noop_runner_invocation"
    elif status == "package_runner_invocation_blocked":
        return "block_runner_invocation"
    elif status == "package_runner_invocation_warning":
        return "manual_review_required"
    return "invalid_runner_invocation"


def validate_waveguide_package_runner_invocation_scope(scope: str) -> bool:
    return scope == "metadata_only_noop_run"


def validate_waveguide_package_runner_invocation_noop_boundary(noop: Dict[str, bool]) -> bool:
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


def validate_waveguide_package_runner_invocation_blocked_operation_counts(counts: Dict[str, int]) -> bool:
    expected_ops = [
        "archive_creation", "deployment", "directory_creation", "external_publication",
        "external_signing", "file_copy", "production_mutation", "upload"
    ]
    return all(counts.get(op, 0) == 0 for op in expected_ops)


def build_waveguide_package_assembly_runner_invocation_envelope(
    runner_readiness_report_path_or_dict: Any
) -> WaveguidePackageAssemblyRunnerInvocationEnvelope:
    readiness_dict = _load_dict(runner_readiness_report_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not readiness_dict:
        return WaveguidePackageAssemblyRunnerInvocationEnvelope(
            package_assembly_runner_invocation_envelope_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUNNER-INVOCATION-ENVELOPE",
            package_assembly_runner_invocation_envelope_version=1,
            runner_invocation_request_id="SOL-WAVEGUIDE-RUNNER-INVOCATION-REQUEST-UNKNOWN",
            runner_invocation_kind="metadata_only_noop_package_runner_invocation",
            runner_invocation_status="package_runner_invocation_invalid",
            runner_invocation_decision="invalid_runner_invocation",
            runner_invocation_scope="unknown",
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
            verified_runner_readiness_case_count=0,
            blocked_runner_readiness_case_count=0,
            warning_runner_readiness_case_count=0,
            invalid_runner_readiness_case_count=0,
            blueprint_phase_count=0,
            ready_blueprint_phase_count=0,
            planned_execution_step_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            authorized_target_package_sections=[],
            authorized_phase_types=[],
            authorized_package_roles=[],
            authorized_artifact_types=[],
            authorized_rc_scopes=[],
            authorized_expected_input_references=[],
            authorized_expected_output_references=[],
            target_package_paths=[],
            authorized_target_package_paths=[],
            authorized_artifact_digests=[],
            authorized_phase_digests=[],
            authorized_runner_readiness_case_digests=[],
            runner_invocation_constraints=[],
            runner_invocation_allowances=[],
            runner_invocation_prohibitions=[],
            runner_invocation_guard_requirements=[],
            runner_invocation_noop_boundary={},
            runner_invocation_rollback_noop_policy={},
            blocked_operation_attempt_counts={},
            specific_runner_invocation_authorized=False,
            metadata_only_runner_invocation=False,
            noop_dry_run_authorized=False,
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
            reason_codes=["RUNNER_READINESS_REPORT_INVALID", "PACKAGE_RUNNER_INVOCATION_INVALID"],
            notes=[],
            software_validation_caveat=caveat
        )

    is_readiness_ok, _ = validate_waveguide_package_runner_readiness_audit_report(readiness_dict)
    reasons = ["RUNNER_INVOCATION_CANONICAL"]
    is_valid = True

    if not is_readiness_ok or readiness_dict.get("runner_readiness_report_status") != "package_runner_readiness_verified":
        is_valid = False
        reasons.append("RUNNER_READINESS_REPORT_INVALID")
    else:
        reasons.append("RUNNER_READINESS_REPORT_VALID")

    # Double check case counts
    verified_cases = readiness_dict.get("verified_runner_readiness_count", 0)
    blocked_cases = readiness_dict.get("blocked_runner_readiness_count", 0)
    warning_cases = readiness_dict.get("warning_runner_readiness_count", 0)
    invalid_cases = readiness_dict.get("invalid_runner_readiness_count", 0)

    if verified_cases != 34 or blocked_cases > 0 or warning_cases > 0 or invalid_cases > 0:
        is_valid = False
        reasons.append("RUNNER_READINESS_CASES_BLOCKED_OR_INVALID")

    # Set boundaries
    noop_dry_run_auth = True if is_valid else False
    specific_auth = True if is_valid else False
    metadata_only = True if is_valid else False

    status = "package_runner_invocation_ready" if is_valid else "package_runner_invocation_invalid"
    decision = build_waveguide_package_runner_invocation_decision(status)

    if is_valid:
        reasons.append("PACKAGE_RUNNER_INVOCATION_READY")
        reasons.append("RUNNER_INVOCATION_NOOP_DRY_RUN_AUTHORIZED")
    else:
        reasons.append("PACKAGE_RUNNER_INVOCATION_INVALID")

    constraints = [
        "metadata_only_runner_invocation",
        "specific_future_runner_invocation_only",
        "non_mutating_runner_invocation",
        "requires_runner_readiness_report_digest_match",
        "requires_run_execution_blueprint_digest_match",
        "requires_no_archive_creation",
        "requires_no_file_copy",
        "requires_no_directory_creation",
        "requires_no_upload",
        "requires_no_deployment",
        "requires_no_signing",
        "requires_no_external_publication",
        "requires_no_production_mutation"
    ]

    allowances = [
        "specific_future_runner_invocation_may_be_requested",
        "specific_future_runner_requires_readiness_audit",
        "specific_future_runner_requires_same_blueprint_digest",
        "specific_future_runner_requires_zero_mutation_attempts"
    ]

    prohibitions = [
        "no_archive_creation_by_runner_invocation_envelope",
        "no_file_copy_by_runner_invocation_envelope",
        "no_directory_creation_by_runner_invocation_envelope",
        "no_upload_by_runner_invocation_envelope",
        "no_deployment_by_runner_invocation_envelope",
        "no_signing_by_runner_invocation_envelope",
        "no_external_publication_by_runner_invocation_envelope",
        "no_production_mutation_by_runner_invocation_envelope"
    ]

    guards = [
        "runner_readiness_report_digest_matches",
        "run_execution_blueprint_digest_matches",
        "run_preflight_report_digest_matches",
        "run_authorization_capsule_digest_matches",
        "metadata_only_runner_boundary_acknowledged",
        "future_runner_requires_no_archive_creation_by_envelope",
        "future_runner_requires_no_file_copy_by_envelope",
        "future_runner_requires_no_directory_creation_by_envelope",
        "future_runner_requires_no_upload_by_envelope",
        "future_runner_requires_no_deployment_by_envelope",
        "future_runner_requires_no_signing_by_envelope",
        "future_runner_requires_no_external_publication_by_envelope",
        "future_runner_requires_no_production_mutation_by_envelope"
    ]

    noop_boundary = {
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

    rollback_noop_policy = {
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

    envelope = WaveguidePackageAssemblyRunnerInvocationEnvelope(
        package_assembly_runner_invocation_envelope_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUNNER-INVOCATION-ENVELOPE",
        package_assembly_runner_invocation_envelope_version=1,
        runner_invocation_request_id=build_waveguide_package_runner_invocation_request_identity(readiness_dict),
        runner_invocation_kind="metadata_only_noop_package_runner_invocation",
        runner_invocation_status=status,
        runner_invocation_decision=decision,
        runner_invocation_scope="metadata_only_noop_run",
        source_runner_readiness_report_digest=readiness_dict.get("runner_readiness_report_digest", ""),
        source_run_execution_blueprint_digest=readiness_dict.get("source_run_execution_blueprint_digest", ""),
        source_run_preflight_report_digest=readiness_dict.get("source_run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=readiness_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=readiness_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=readiness_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=readiness_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=readiness_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=readiness_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=readiness_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=readiness_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=readiness_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=readiness_dict.get("source_artifact_catalog_digest", ""),
        verified_runner_readiness_case_count=verified_cases,
        blocked_runner_readiness_case_count=blocked_cases,
        warning_runner_readiness_case_count=warning_cases,
        invalid_runner_readiness_case_count=invalid_cases,
        blueprint_phase_count=readiness_dict.get("blueprint_phase_count", 0),
        ready_blueprint_phase_count=readiness_dict.get("ready_blueprint_phase_count", 0),
        planned_execution_step_count=readiness_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=readiness_dict.get("total_authorized_file_count", 0),
        rc1_authorized_file_count=readiness_dict.get("rc1_authorized_file_count", 0),
        rc2_authorized_file_count=readiness_dict.get("rc2_authorized_file_count", 0),
        shared_authorized_file_count=readiness_dict.get("shared_authorized_file_count", 0),
        authorized_target_package_sections=sorted(readiness_dict.get("target_package_sections", [])),
        authorized_phase_types=sorted(readiness_dict.get("phase_types_indexed", [])),
        authorized_package_roles=sorted(readiness_dict.get("package_roles_indexed", [])),
        authorized_artifact_types=sorted(readiness_dict.get("artifact_types_indexed", [])),
        authorized_rc_scopes=sorted(readiness_dict.get("rc_scopes_indexed", [])),
        authorized_expected_input_references=sorted(readiness_dict.get("expected_input_references", [])),
        authorized_expected_output_references=sorted(readiness_dict.get("expected_output_references", [])),
        authorized_target_package_paths=sorted(readiness_dict.get("target_package_paths", [])),
        authorized_artifact_digests=sorted(readiness_dict.get("artifact_digests", [])),
        authorized_phase_digests=sorted(readiness_dict.get("phase_digests", [])),
        authorized_runner_readiness_case_digests=sorted(readiness_dict.get("runner_readiness_case_digests", [])),
        runner_invocation_constraints=sorted(constraints),
        runner_invocation_allowances=sorted(allowances),
        runner_invocation_prohibitions=sorted(prohibitions),
        runner_invocation_guard_requirements=sorted(guards),
        runner_invocation_noop_boundary=noop_boundary,
        runner_invocation_rollback_noop_policy=rollback_noop_policy,
        blocked_operation_attempt_counts=blocked_operation_attempt_counts,
        specific_runner_invocation_authorized=specific_auth,
        metadata_only_runner_invocation=metadata_only,
        noop_dry_run_authorized=noop_dry_run_auth,
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

    envelope.package_assembly_runner_invocation_envelope_digest = hash_waveguide_package_assembly_runner_invocation_envelope(envelope)
    return envelope


def validate_waveguide_package_assembly_runner_invocation_envelope(envelope: Any) -> Tuple[bool, List[str]]:
    envelope_dict = _load_dict(envelope)
    if not envelope_dict:
        return False, ["PACKAGE_RUNNER_INVOCATION_INVALID"]

    reasons = []
    is_valid = True

    if envelope_dict.get("package_assembly_runner_invocation_envelope_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUNNER-INVOCATION-ENVELOPE":
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_INVALID_ID")

    if envelope_dict.get("package_assembly_runner_invocation_envelope_version") != 1:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_INVALID_VERSION")

    # Scope validation
    if not validate_waveguide_package_runner_invocation_scope(envelope_dict.get("runner_invocation_scope", "")):
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_INVALID_SCOPE")

    # Authorization verification
    if envelope_dict.get("specific_runner_invocation_authorized") is not True:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_NOT_AUTHORIZED")

    if envelope_dict.get("metadata_only_runner_invocation") is not True:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_NOT_METADATA_ONLY")

    if envelope_dict.get("noop_dry_run_authorized") is not True:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_NOOP_DRY_RUN_NOT_AUTHORIZED")

    # Verification counts validation
    verified_cases = envelope_dict.get("verified_runner_readiness_case_count", 0)
    blocked_cases = envelope_dict.get("blocked_runner_readiness_case_count", 0)
    warning_cases = envelope_dict.get("warning_runner_readiness_case_count", 0)
    invalid_cases = envelope_dict.get("invalid_runner_readiness_case_count", 0)

    if verified_cases != 34 or blocked_cases > 0 or warning_cases > 0 or invalid_cases > 0:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_CASES_BLOCKED_OR_INVALID")

    # Check that allowances, constraints, prohibitions, and guards are present
    req_lists = [
        "runner_invocation_constraints", "runner_invocation_allowances",
        "runner_invocation_prohibitions", "runner_invocation_guard_requirements"
    ]
    for lst in req_lists:
        if not envelope_dict.get(lst):
            is_valid = False
            reasons.append(f"RUNNER_INVOCATION_ENVELOPE_MISSING_{lst.upper()}")

    # Check matrices, no-op boundary, rollback policy
    if not validate_waveguide_package_runner_invocation_noop_boundary(envelope_dict.get("runner_invocation_noop_boundary", {})):
        is_valid = False
    if envelope_dict.get("runner_invocation_rollback_noop_policy", {}).get("rollback_required") is not False:
        is_valid = False

    # Check authorized flags
    auth_flags = [
        "physical_execution_authorized", "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized"
    ]
    for flag in auth_flags:
        if envelope_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUNNER_INVOCATION_ENVELOPE_AUTHORIZED_FLAG_TRUE_{flag.upper()}")

    # Check performed flags
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in perf_flags:
        if envelope_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUNNER_INVOCATION_ENVELOPE_PERFORMED_FLAG_TRUE_{flag.upper()}")

    # Check blocked operations counts
    if not validate_waveguide_package_runner_invocation_blocked_operation_counts(envelope_dict.get("blocked_operation_attempt_counts", {})):
        is_valid = False

    # Check envelope digest
    recorded_digest = envelope_dict.get("package_assembly_runner_invocation_envelope_digest", "")
    recomputed_digest = hash_waveguide_package_assembly_runner_invocation_envelope(envelope_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_DIGEST_MISMATCH")

    status = envelope_dict.get("runner_invocation_status", "")
    if is_valid and status == "package_runner_invocation_ready":
        reasons.append("PACKAGE_RUNNER_INVOCATION_READY")
    else:
        is_valid = False
        reasons.append("PACKAGE_RUNNER_INVOCATION_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_assembly_runner_invocation_envelope(envelope: Any) -> str:
    envelope_dict = _load_dict(envelope)
    if not envelope_dict:
        return "Invalid Runner Invocation Envelope"

    status = envelope_dict.get("runner_invocation_status", "unknown")
    digest = envelope_dict.get("package_assembly_runner_invocation_envelope_digest", "")
    req_id = envelope_dict.get("runner_invocation_request_id", "")

    return (
        f"SOL Waveguide Runner Invocation Envelope Summary:\n"
        f"  Invocation Status: {status}\n"
        f"  Request ID: {req_id}\n"
        f"  Envelope Digest: {digest}\n"
    )


def export_waveguide_package_assembly_runner_invocation_envelope(envelope: Any, filepath: str) -> None:
    envelope_dict = _load_dict(envelope)
    if not envelope_dict:
        raise ValueError("Cannot export invalid runner invocation envelope data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(envelope_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_assembly_runner_invocation_envelopes(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def index_waveguide_package_runner_invocation_references_by_source(envelope: Any) -> Dict[str, str]:
    envelope_dict = _load_dict(envelope) or {}
    idx = {}
    for key, val in envelope_dict.items():
        if key.startswith("source_") and isinstance(val, str) and val:
            idx[key] = val
    return idx
