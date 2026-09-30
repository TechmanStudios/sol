# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Runner Dry-Run Transcript Validator / Transcript Auditor.
Independently reloads the no-op dry-run transcript, recomputes all event digests,
validates the runner invocation envelope reference, and produces a transcript audit report.
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
from sol_waveguide_package_runner_noop_dry_run_transcript import (
    validate_waveguide_package_runner_noop_dry_run_transcript,
    hash_waveguide_package_runner_noop_dry_run_transcript,
    hash_waveguide_package_runner_noop_dry_run_event
)
from sol_waveguide_package_assembly_runner_invocation_envelope import (
    validate_waveguide_package_assembly_runner_invocation_envelope,
    hash_waveguide_package_assembly_runner_invocation_envelope
)


@dataclass
class WaveguidePackageRunnerTranscriptAuditCase:
    transcript_audit_case_id: str
    package_runner_noop_dry_run_transcript_id: str
    package_runner_noop_dry_run_transcript_path: str
    noop_dry_run_transcript_digest_recorded: str
    noop_dry_run_transcript_digest_recomputed: str
    noop_dry_run_transcript_digest_match: bool
    noop_dry_run_event_id: str
    noop_dry_run_event_digest_recorded: str
    noop_dry_run_event_digest_recomputed: str
    noop_dry_run_event_digest_match: bool
    event_index: int
    event_type: str
    event_status: str
    transcript_audit_status: str  # transcript_event_audit_verified, etc.
    source_runner_invocation_envelope_digest_recorded: str
    source_runner_invocation_envelope_digest_recomputed: str
    source_runner_invocation_envelope_digest_match: bool
    source_runner_invocation_envelope_valid: bool
    source_runner_invocation_envelope_status: str
    source_runner_readiness_report_digest: str
    source_run_execution_blueprint_digest: str
    phase_index: int
    phase_type: str
    phase_digest: str
    expected_input_reference: str
    expected_output_reference: str
    target_package_path: str
    artifact_digest: str
    event_action: str
    event_result: str
    operation_skipped: bool
    skipped_operation_kind: str
    skip_reason: str
    noop_boundary_verified: bool
    skipped_operation_verified: bool
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
    transcript_audit_case_digest: str = ""


@dataclass
class WaveguidePackageRunnerTranscriptAuditReport:
    transcript_audit_report_id: str
    transcript_audit_report_version: int
    transcript_audit_report_status: str  # package_runner_noop_transcript_audit_verified, etc.
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
    audited_cases: List[WaveguidePackageRunnerTranscriptAuditCase]
    verified_transcript_audit_cases: List[str]
    blocked_transcript_audit_cases: List[str]
    warning_transcript_audit_cases: List[str]
    invalid_transcript_audit_cases: List[str]
    verified_transcript_audit_count: int
    blocked_transcript_audit_count: int
    warning_transcript_audit_count: int
    invalid_transcript_audit_count: int
    verified_noop_event_count: int
    blocked_noop_event_count: int
    warning_noop_event_count: int
    invalid_noop_event_count: int
    total_noop_event_count: int
    blueprint_phase_count: int
    planned_execution_step_count: int
    total_authorized_file_count: int
    expected_input_count: int
    expected_output_count: int
    skipped_operation_count: int
    event_types_indexed: List[str]
    phase_types_indexed: List[str]
    target_package_sections: List[str]
    target_package_paths: List[str]
    expected_input_references: List[str]
    expected_output_references: List[str]
    artifact_digests: List[str]
    phase_digests: List[str]
    noop_event_digests: List[str]
    transcript_audit_case_digests: List[str]
    event_sequence_verified: bool
    event_counts_verified: bool
    skipped_operation_matrix_verified: bool
    noop_boundary_verified: bool
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
    transcript_audit_report_digest: str = ""


def hash_waveguide_package_runner_transcript_audit_case(case: Any) -> str:
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
    c_dict_copy.pop("transcript_audit_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_package_runner_transcript_audit_report(report: Any) -> str:
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
    r_dict_copy.pop("transcript_audit_report_digest", None)
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


def recompute_waveguide_package_runner_noop_dry_run_transcript_digest(
    transcript_path_or_dict: Any
) -> str:
    transcript_dict = _load_dict(transcript_path_or_dict)
    if transcript_dict:
        return hash_waveguide_package_runner_noop_dry_run_transcript(transcript_dict)
    return ""


def recompute_waveguide_package_runner_noop_dry_run_event_digest(
    event_dict: Dict[str, Any]
) -> str:
    return hash_waveguide_package_runner_noop_dry_run_event(event_dict)


def validate_waveguide_package_runner_noop_event_sequence(events: List[Any]) -> bool:
    """
    Verifies events sequence indices are contiguous starting from 0.
    """
    for idx, e in enumerate(events):
        e_dict = _load_dict(e)
        if not e_dict or e_dict.get("event_index") != idx:
            return False
    return True


def validate_waveguide_package_runner_noop_event_counts(events: List[Any]) -> bool:
    """
    Verifies exact event counts per event type.
    Total events: 182
    """
    if len(events) != 182:
        return False

    types = [e.get("event_type") for e in [_load_dict(ev) for ev in events] if e]
    counts = {t: types.count(t) for t in set(types)}

    return (
        counts.get("invocation_loaded") == 1 and
        counts.get("runner_readiness_verified") == 1 and
        counts.get("blueprint_phase_checked") == 34 and
        counts.get("expected_input_checked") == 34 and
        counts.get("expected_output_planned") == 34 and
        counts.get("abort_conditions_checked") == 34 and
        counts.get("safety_gates_checked") == 34 and
        counts.get("noop_boundary_confirmed") == 1 and
        counts.get("physical_operation_skipped") == 8 and
        counts.get("dry_run_finalized") == 1
    )


def validate_waveguide_package_runner_noop_skipped_operation_matrix(events: List[Any]) -> bool:
    skipped = []
    for e in events:
        e_dict = _load_dict(e)
        if e_dict and e_dict.get("operation_skipped"):
            kind = e_dict.get("skipped_operation_kind")
            if kind and kind not in skipped:
                skipped.append(kind)
    
    expected = [
        "archive_creation", "deployment", "directory_creation", "external_publication",
        "external_signing", "file_copy", "production_mutation", "upload"
    ]
    return sorted(skipped) == expected


def validate_waveguide_package_runner_noop_boundary_independently(noop: Dict[str, bool]) -> bool:
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


def build_waveguide_package_runner_transcript_audit_case(
    event_dict: Dict[str, Any],
    transcript_dict: Dict[str, Any],
    envelope_dict: Dict[str, Any]
) -> WaveguidePackageRunnerTranscriptAuditCase:
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reasons = ["TRANSCRIPT_AUDIT_CASE_CANONICAL"]
    is_valid = True

    # 1. Transcript digest check
    recorded_transcript_digest = transcript_dict.get("package_runner_noop_dry_run_transcript_digest", "")
    recomputed_transcript_digest = hash_waveguide_package_runner_noop_dry_run_transcript(transcript_dict)
    transcript_digest_match = (recorded_transcript_digest == recomputed_transcript_digest) and (recorded_transcript_digest != "")
    if not transcript_digest_match:
        is_valid = False
        reasons.append("TRANSCRIPT_DIGEST_MISMATCH")

    # 2. Event digest check
    recorded_event_digest = event_dict.get("noop_dry_run_event_digest", "")
    recomputed_event_digest = hash_waveguide_package_runner_noop_dry_run_event(event_dict)
    event_digest_match = (recorded_event_digest == recomputed_event_digest) and (recorded_event_digest != "")
    if not event_digest_match:
        is_valid = False
        reasons.append("TRANSCRIPT_EVENT_DIGEST_MISMATCH")

    # 3. Invocation envelope check
    is_envelope_valid, _ = validate_waveguide_package_assembly_runner_invocation_envelope(envelope_dict)
    recorded_envelope_digest = transcript_dict.get("source_runner_invocation_envelope_digest", "")
    recomputed_envelope_digest = hash_waveguide_package_assembly_runner_invocation_envelope(envelope_dict)
    envelope_digest_match = (recorded_envelope_digest == recomputed_envelope_digest) and (recorded_envelope_digest != "")
    if not envelope_digest_match:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_DIGEST_MISMATCH")
    if not is_envelope_valid or envelope_dict.get("runner_invocation_status") != "package_runner_invocation_ready":
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_INVALID")

    # 4. Noop boundary checks
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
    noop_comb = {}
    for f in auth_flags:
        noop_comb[f] = envelope_dict.get(f, None)
    for f in perf_flags:
        noop_comb[f] = transcript_dict.get(f, None)
    noop_boundary_ok = validate_waveguide_package_runner_noop_boundary_independently(noop_comb)
    if not noop_boundary_ok:
        is_valid = False

    # Check skipped operations
    skipped_ok = True
    if event_dict.get("operation_skipped"):
        skipped_kind = event_dict.get("skipped_operation_kind")
        expected_skipped = [
            "archive_creation", "deployment", "directory_creation", "external_publication",
            "external_signing", "file_copy", "production_mutation", "upload"
        ]
        if skipped_kind not in expected_skipped:
            skipped_ok = False
            is_valid = False

    # Check performed mutation flags
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in perf_flags:
        if event_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"TRANSCRIPT_AUDIT_MUTATION_PERFORMED_{flag.upper()}")

    # Check blocked operations counts
    blocked_counts = transcript_dict.get("blocked_operation_attempt_counts", {})
    has_blocked_attempts = any(blocked_counts.get(k, 0) > 0 for k in blocked_counts)
    if has_blocked_attempts:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_BLOCKED_OPERATION_ATTEMPTED")

    # Status determination
    case_status = "transcript_event_audit_verified" if is_valid else "transcript_event_audit_blocked"
    if is_valid:
        reasons.append("TRANSCRIPT_EVENT_AUDIT_VERIFIED")
    else:
        reasons.append("TRANSCRIPT_EVENT_AUDIT_BLOCKED")

    case = WaveguidePackageRunnerTranscriptAuditCase(
        transcript_audit_case_id=f"SOL-WAVEGUIDE-TRANSCRIPT-AUDIT-CASE-{event_dict.get('noop_dry_run_event_id')}",
        package_runner_noop_dry_run_transcript_id=transcript_dict.get("package_runner_noop_dry_run_transcript_id", ""),
        package_runner_noop_dry_run_transcript_path="",
        noop_dry_run_transcript_digest_recorded=recorded_transcript_digest,
        noop_dry_run_transcript_digest_recomputed=recomputed_transcript_digest,
        noop_dry_run_transcript_digest_match=transcript_digest_match,
        noop_dry_run_event_id=event_dict.get("noop_dry_run_event_id", ""),
        noop_dry_run_event_digest_recorded=recorded_event_digest,
        noop_dry_run_event_digest_recomputed=recomputed_event_digest,
        noop_dry_run_event_digest_match=event_digest_match,
        event_index=event_dict.get("event_index", 0),
        event_type=event_dict.get("event_type", ""),
        event_status=event_dict.get("event_status", ""),
        transcript_audit_status=case_status,
        source_runner_invocation_envelope_digest_recorded=recorded_envelope_digest,
        source_runner_invocation_envelope_digest_recomputed=recomputed_envelope_digest,
        source_runner_invocation_envelope_digest_match=envelope_digest_match,
        source_runner_invocation_envelope_valid=is_envelope_valid,
        source_runner_invocation_envelope_status=envelope_dict.get("runner_invocation_status", ""),
        source_runner_readiness_report_digest=transcript_dict.get("source_runner_readiness_report_digest", ""),
        source_run_execution_blueprint_digest=transcript_dict.get("source_run_execution_blueprint_digest", ""),
        phase_index=event_dict.get("phase_index", -1),
        phase_type=event_dict.get("phase_type", ""),
        phase_digest=event_dict.get("phase_digest", ""),
        expected_input_reference=event_dict.get("expected_input_reference", ""),
        expected_output_reference=event_dict.get("expected_output_reference", ""),
        target_package_path=event_dict.get("target_package_path", ""),
        artifact_digest=event_dict.get("artifact_digest", ""),
        event_action=event_dict.get("event_action", ""),
        event_result=event_dict.get("event_result", ""),
        operation_skipped=event_dict.get("operation_skipped", False),
        skipped_operation_kind=event_dict.get("skipped_operation_kind", ""),
        skip_reason=event_dict.get("skip_reason", ""),
        noop_boundary_verified=noop_boundary_ok,
        skipped_operation_verified=skipped_ok,
        physical_execution_performed=event_dict.get("physical_execution_performed", False),
        archive_creation_performed=event_dict.get("archive_creation_performed", False),
        file_copy_performed=event_dict.get("file_copy_performed", False),
        directory_creation_performed=event_dict.get("directory_creation_performed", False),
        upload_performed=event_dict.get("upload_performed", False),
        deployment_performed=event_dict.get("deployment_performed", False),
        signing_performed=event_dict.get("signing_performed", False),
        external_publication_performed=event_dict.get("external_publication_performed", False),
        production_mutation_performed=event_dict.get("production_mutation_performed", False),
        blocked_operation_attempt_counts=blocked_counts,
        no_physical_execution_verified=event_dict.get("physical_execution_performed") is False,
        no_archive_creation_verified=event_dict.get("archive_creation_performed") is False,
        no_file_copy_verified=event_dict.get("file_copy_performed") is False,
        no_directory_creation_verified=event_dict.get("directory_creation_performed") is False,
        no_upload_verified=event_dict.get("upload_performed") is False,
        no_deployment_verified=event_dict.get("deployment_performed") is False,
        no_signing_verified=event_dict.get("signing_performed") is False,
        no_external_publication_verified=event_dict.get("external_publication_performed") is False,
        no_production_mutation_verified=event_dict.get("production_mutation_performed") is False,
        reason_codes=sorted(list(set(reasons))),
        notes=[],
        software_validation_caveat=caveat
    )
    case.transcript_audit_case_digest = hash_waveguide_package_runner_transcript_audit_case(case)
    return case


def validate_waveguide_package_runner_noop_dry_run_transcript_independently(
    transcript_path_or_dict: Any,
    envelope_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    transcript_dict = _load_dict(transcript_path_or_dict)
    envelope_dict = _load_dict(envelope_path_or_dict)

    reasons = []
    is_valid = True

    if not transcript_dict or not envelope_dict:
        return False, ["PACKAGE_RUNNER_TRANSCRIPT_AUDIT_INVALID"]

    transcript_ok, _ = validate_waveguide_package_runner_noop_dry_run_transcript(transcript_dict)
    envelope_ok, _ = validate_waveguide_package_assembly_runner_invocation_envelope(envelope_dict)

    if not transcript_ok:
        is_valid = False
        reasons.append("RUN_TRANSCRIPT_INVALID")
    if not envelope_ok:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_INVALID")

    # Cross check digests
    recorded_envelope_digest = transcript_dict.get("source_runner_invocation_envelope_digest", "")
    recomputed_envelope_digest = hash_waveguide_package_assembly_runner_invocation_envelope(envelope_dict)
    if recorded_envelope_digest != recomputed_envelope_digest or not recorded_envelope_digest:
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_DIGEST_MISMATCH")

    if is_valid:
        reasons.append("PACKAGE_RUNNER_TRANSCRIPT_AUDIT_VERIFIED")
    else:
        reasons.append("PACKAGE_RUNNER_TRANSCRIPT_AUDIT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_runner_transcript_audit_report(
    transcript_path_or_dict: Any,
    envelope_path_or_dict: Any
) -> WaveguidePackageRunnerTranscriptAuditReport:
    transcript_dict = _load_dict(transcript_path_or_dict)
    envelope_dict = _load_dict(envelope_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not transcript_dict or not envelope_dict:
        return WaveguidePackageRunnerTranscriptAuditReport(
            transcript_audit_report_id="SOL-WAVEGUIDE-PACKAGE-RUNNER-NOOP-DRY-RUN-TRANSCRIPT-AUDIT-REPORT",
            transcript_audit_report_version=1,
            transcript_audit_report_status="package_runner_noop_transcript_audit_invalid",
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
            verified_transcript_audit_cases=[],
            blocked_transcript_audit_cases=[],
            warning_transcript_audit_cases=[],
            invalid_transcript_audit_cases=[],
            verified_transcript_audit_count=0,
            blocked_transcript_audit_count=0,
            warning_transcript_audit_count=0,
            invalid_transcript_audit_count=0,
            verified_noop_event_count=0,
            blocked_noop_event_count=0,
            warning_noop_event_count=0,
            invalid_noop_event_count=0,
            total_noop_event_count=0,
            blueprint_phase_count=0,
            planned_execution_step_count=0,
            total_authorized_file_count=0,
            expected_input_count=0,
            expected_output_count=0,
            skipped_operation_count=0,
            event_types_indexed=[],
            phase_types_indexed=[],
            target_package_sections=[],
            target_package_paths=[],
            expected_input_references=[],
            expected_output_references=[],
            artifact_digests=[],
            phase_digests=[],
            noop_event_digests=[],
            transcript_audit_case_digests=[],
            event_sequence_verified=False,
            event_counts_verified=False,
            skipped_operation_matrix_verified=False,
            noop_boundary_verified=False,
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
            reason_codes=["RUN_TRANSCRIPT_INVALID", "PACKAGE_RUNNER_TRANSCRIPT_AUDIT_INVALID"],
            software_validation_caveat=caveat
        )

    is_compat_ok, compat_reasons = validate_waveguide_package_runner_noop_dry_run_transcript_independently(
        transcript_dict, envelope_dict
    )

    events = transcript_dict.get("noop_dry_run_events", [])
    cases = []
    for e in events:
        case = build_waveguide_package_runner_transcript_audit_case(e, transcript_dict, envelope_dict)
        cases.append(case)

    # Status index
    verified_cases = [c.transcript_audit_case_id for c in cases if c.transcript_audit_status == "transcript_event_audit_verified"]
    blocked_cases = [c.transcript_audit_case_id for c in cases if c.transcript_audit_status == "transcript_event_audit_blocked"]
    warning_cases = [c.transcript_audit_case_id for c in cases if c.transcript_audit_status == "transcript_event_audit_warning"]
    invalid_cases = [c.transcript_audit_case_id for c in cases if c.transcript_audit_status == "transcript_event_audit_invalid"]

    # Auditing checks
    sequence_ok = validate_waveguide_package_runner_noop_event_sequence(events)
    counts_ok = validate_waveguide_package_runner_noop_event_counts(events)
    skipped_ok = validate_waveguide_package_runner_noop_skipped_operation_matrix(events)
    
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
    noop_comb = {}
    for f in auth_flags:
        noop_comb[f] = envelope_dict.get(f, None)
    for f in perf_flags:
        noop_comb[f] = transcript_dict.get(f, None)
    noop_ok = validate_waveguide_package_runner_noop_boundary_independently(noop_comb)

    is_report_ok = (
        is_compat_ok and
        sequence_ok and
        counts_ok and
        skipped_ok and
        noop_ok and
        len(events) == 182 and
        len(blocked_cases) == 0 and
        len(invalid_cases) == 0
    )

    report_status = "package_runner_noop_transcript_audit_verified" if is_report_ok else "package_runner_noop_transcript_audit_invalid"
    reasons = ["TRANSCRIPT_AUDIT_REPORT_CANONICAL"]
    if is_report_ok:
        reasons.append("PACKAGE_RUNNER_NOOP_TRANSCRIPT_AUDIT_VERIFIED")
    else:
        reasons.append("PACKAGE_RUNNER_NOOP_TRANSCRIPT_AUDIT_INVALID")

    # Indices
    event_types_indexed = sorted(transcript_dict.get("event_types_indexed", []))
    phase_types_indexed = sorted(transcript_dict.get("phase_types_indexed", []))
    target_package_sections = sorted(transcript_dict.get("target_package_sections", []))
    target_package_paths = sorted(transcript_dict.get("target_package_paths", []))
    expected_input_references = sorted(transcript_dict.get("expected_input_references", []))
    expected_output_references = sorted(transcript_dict.get("expected_output_references", []))
    artifact_digests = sorted(transcript_dict.get("artifact_digests", []))
    phase_digests = sorted(transcript_dict.get("phase_digests", []))
    noop_event_digests = sorted(transcript_dict.get("noop_event_digests", []))
    transcript_audit_case_digests = sorted([c.transcript_audit_case_digest for c in cases])

    report = WaveguidePackageRunnerTranscriptAuditReport(
        transcript_audit_report_id="SOL-WAVEGUIDE-PACKAGE-RUNNER-NOOP-DRY-RUN-TRANSCRIPT-AUDIT-REPORT",
        transcript_audit_report_version=1,
        transcript_audit_report_status=report_status,
        source_noop_dry_run_transcript_digest=transcript_dict.get("package_runner_noop_dry_run_transcript_digest", ""),
        source_runner_invocation_envelope_digest=transcript_dict.get("source_runner_invocation_envelope_digest", ""),
        source_runner_readiness_report_digest=transcript_dict.get("source_runner_readiness_report_digest", ""),
        source_run_execution_blueprint_digest=transcript_dict.get("source_run_execution_blueprint_digest", ""),
        source_run_preflight_report_digest=transcript_dict.get("source_run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=transcript_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=transcript_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=transcript_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=transcript_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=transcript_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=transcript_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=transcript_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=transcript_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=transcript_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=transcript_dict.get("source_artifact_catalog_digest", ""),
        audited_cases=cases,
        verified_transcript_audit_cases=verified_cases,
        blocked_transcript_audit_cases=blocked_cases,
        warning_transcript_audit_cases=warning_cases,
        invalid_transcript_audit_cases=invalid_cases,
        verified_transcript_audit_count=len(verified_cases),
        blocked_transcript_audit_count=len(blocked_cases),
        warning_transcript_audit_count=len(warning_cases),
        invalid_transcript_audit_count=len(invalid_cases),
        verified_noop_event_count=transcript_dict.get("verified_noop_event_count", 0),
        blocked_noop_event_count=transcript_dict.get("blocked_noop_event_count", 0),
        warning_noop_event_count=transcript_dict.get("warning_noop_event_count", 0),
        invalid_noop_event_count=transcript_dict.get("invalid_noop_event_count", 0),
        total_noop_event_count=len(events),
        blueprint_phase_count=transcript_dict.get("blueprint_phase_count", 0),
        planned_execution_step_count=transcript_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=transcript_dict.get("total_authorized_file_count", 0),
        expected_input_count=transcript_dict.get("expected_input_count", 0),
        expected_output_count=transcript_dict.get("expected_output_count", 0),
        skipped_operation_count=transcript_dict.get("skipped_operation_count", 0),
        event_types_indexed=event_types_indexed,
        phase_types_indexed=phase_types_indexed,
        target_package_sections=target_package_sections,
        target_package_paths=target_package_paths,
        expected_input_references=expected_input_references,
        expected_output_references=expected_output_references,
        artifact_digests=artifact_digests,
        phase_digests=phase_digests,
        noop_event_digests=noop_event_digests,
        transcript_audit_case_digests=transcript_audit_case_digests,
        event_sequence_verified=sequence_ok,
        event_counts_verified=counts_ok,
        skipped_operation_matrix_verified=skipped_ok,
        noop_boundary_verified=noop_ok,
        blocked_operation_attempt_counts=transcript_dict.get("blocked_operation_attempt_counts", {}),
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
    report.transcript_audit_report_digest = hash_waveguide_package_runner_transcript_audit_report(report)
    return report


def validate_waveguide_package_runner_transcript_audit_report(report: Any) -> Tuple[bool, List[str]]:
    report_dict = _load_dict(report)
    if not report_dict:
        return False, ["PACKAGE_RUNNER_TRANSCRIPT_AUDIT_INVALID"]

    reasons = []
    is_valid = True

    if report_dict.get("transcript_audit_report_id") != "SOL-WAVEGUIDE-PACKAGE-RUNNER-NOOP-DRY-RUN-TRANSCRIPT-AUDIT-REPORT":
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_INVALID_ID")

    if report_dict.get("transcript_audit_report_version") != 1:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_INVALID_VERSION")

    # Validate cases
    cases = report_dict.get("audited_cases", [])
    if not cases or len(cases) != 182:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_CASE_COUNT_MISMATCH")
    else:
        for c in cases:
            recorded = c.get("transcript_audit_case_digest", "")
            recomputed = hash_waveguide_package_runner_transcript_audit_case(c)
            if recorded != recomputed or not recorded:
                is_valid = False
                reasons.append("TRANSCRIPT_AUDIT_CASE_DIGEST_MISMATCH")

    # Verify audit reports
    if report_dict.get("event_sequence_verified") is not True:
        is_valid = False
    if report_dict.get("event_counts_verified") is not True:
        is_valid = False
    if report_dict.get("skipped_operation_matrix_verified") is not True:
        is_valid = False
    if report_dict.get("noop_boundary_verified") is not True:
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
            reasons.append(f"TRANSCRIPT_AUDIT_REPORT_MUTATION_PERFORMED_{flag.upper()}")

    # Check report digest
    recorded_digest = report_dict.get("transcript_audit_report_digest", "")
    recomputed_digest = hash_waveguide_package_runner_transcript_audit_report(report_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("TRANSCRIPT_AUDIT_REPORT_DIGEST_MISMATCH")

    status = report_dict.get("transcript_audit_report_status", "")
    if is_valid and status == "package_runner_noop_transcript_audit_verified":
        reasons.append("PACKAGE_RUNNER_NOOP_TRANSCRIPT_AUDIT_VERIFIED")
    else:
        is_valid = False
        reasons.append("PACKAGE_RUNNER_NOOP_TRANSCRIPT_AUDIT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_runner_transcript_audit_report(report: Any) -> str:
    report_dict = _load_dict(report)
    if not report_dict:
        return "Invalid Transcript Audit Report"

    status = report_dict.get("transcript_audit_report_status", "unknown")
    digest = report_dict.get("transcript_audit_report_digest", "")
    verified_cases = report_dict.get("verified_transcript_audit_count", 0)

    return (
        f"SOL Waveguide Runner Transcript Audit Report Summary:\n"
        f"  Report Status: {status}\n"
        f"  Report Digest: {digest}\n"
        f"  Verified Cases: {verified_cases}\n"
    )


def export_waveguide_package_runner_transcript_audit_report(report: Any, filepath: str) -> None:
    report_dict = _load_dict(report)
    if not report_dict:
        raise ValueError("Cannot export invalid transcript audit report data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_runner_transcript_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def index_waveguide_package_runner_transcript_events_by_type(events: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for e in events:
        e_dict = _load_dict(e)
        if e_dict:
            ev_type = e_dict.get("event_type", "unknown")
            idx.setdefault(ev_type, []).append(e_dict)
    return idx


def index_waveguide_package_runner_transcript_audit_cases_by_status(cases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for c in cases:
        c_dict = _load_dict(c)
        if c_dict:
            status = c_dict.get("transcript_audit_status", "unknown")
            idx.setdefault(status, []).append(c_dict)
    return idx
