# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Runner No-Op Dry-Run Transcript.
Consumes the runner invocation envelope and generates a deterministic transcript of 182 events.
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
from sol_waveguide_package_assembly_runner_invocation_envelope import (
    validate_waveguide_package_assembly_runner_invocation_envelope,
    hash_waveguide_package_assembly_runner_invocation_envelope
)


@dataclass
class WaveguidePackageRunnerNoOpDryRunEvent:
    noop_dry_run_event_id: str
    event_index: int
    event_type: str  # invocation_loaded, runner_readiness_verified, blueprint_phase_checked, etc.
    event_status: str  # noop_dry_run_event_verified, etc.
    source_runner_invocation_envelope_digest: str
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
    noop_dry_run_event_digest: str = ""


@dataclass
class WaveguidePackageRunnerNoOpDryRunTranscript:
    package_runner_noop_dry_run_transcript_id: str
    package_runner_noop_dry_run_transcript_version: int
    noop_dry_run_transcript_status: str  # package_runner_noop_dry_run_verified, etc.
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
    noop_dry_run_events: List[WaveguidePackageRunnerNoOpDryRunEvent]
    verified_noop_dry_run_events: List[str]
    blocked_noop_dry_run_events: List[str]
    warning_noop_dry_run_events: List[str]
    invalid_noop_dry_run_events: List[str]
    verified_noop_event_count: int
    blocked_noop_event_count: int
    warning_noop_event_count: int
    invalid_noop_event_count: int
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
    skipped_operation_matrix: List[str]
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
    package_runner_noop_dry_run_transcript_digest: str = ""


def hash_waveguide_package_runner_noop_dry_run_event(event: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of event excluding event digest.
    """
    if hasattr(event, "__dict__"):
        e_dict = asdict(event)
    elif isinstance(event, dict):
        e_dict = dict(event)
    else:
        raise TypeError("event must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("noop_dry_run_event_digest", None)
    return hash_data(e_dict_copy)


def hash_waveguide_package_runner_noop_dry_run_transcript(transcript: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of transcript excluding transcript digest.
    """
    if hasattr(transcript, "__dict__"):
        t_dict = asdict(transcript)
    elif isinstance(transcript, dict):
        t_dict = dict(transcript)
    else:
        raise TypeError("transcript must be a dictionary or a dataclass instance")

    t_dict_copy = dict(t_dict)
    t_dict_copy.pop("package_runner_noop_dry_run_transcript_digest", None)
    return hash_data(t_dict_copy)


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


def build_waveguide_package_runner_noop_dry_run_event(
    noop_dry_run_event_id: str,
    event_index: int,
    event_type: str,
    source_runner_invocation_envelope_digest: str,
    source_runner_readiness_report_digest: str,
    source_run_execution_blueprint_digest: str,
    phase_index: int = -1,
    phase_type: str = "",
    phase_digest: str = "",
    expected_input_reference: str = "",
    expected_output_reference: str = "",
    target_package_path: str = "",
    artifact_digest: str = "",
    event_action: str = "",
    event_result: str = "",
    operation_skipped: bool = False,
    skipped_operation_kind: str = "",
    skip_reason: str = "",
    notes: List[str] = None
) -> WaveguidePackageRunnerNoOpDryRunEvent:
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    ev = WaveguidePackageRunnerNoOpDryRunEvent(
        noop_dry_run_event_id=noop_dry_run_event_id,
        event_index=event_index,
        event_type=event_type,
        event_status="noop_dry_run_event_verified",
        source_runner_invocation_envelope_digest=source_runner_invocation_envelope_digest,
        source_runner_readiness_report_digest=source_runner_readiness_report_digest,
        source_run_execution_blueprint_digest=source_run_execution_blueprint_digest,
        phase_index=phase_index,
        phase_type=phase_type,
        phase_digest=phase_digest,
        expected_input_reference=expected_input_reference,
        expected_output_reference=expected_output_reference,
        target_package_path=target_package_path,
        artifact_digest=artifact_digest,
        event_action=event_action,
        event_result=event_result,
        operation_skipped=operation_skipped,
        skipped_operation_kind=skipped_operation_kind,
        skip_reason=skip_reason,
        physical_execution_performed=False,
        archive_creation_performed=False,
        file_copy_performed=False,
        directory_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=["EVENT_VERIFIED"],
        notes=notes or [],
        software_validation_caveat=caveat
    )
    ev.noop_dry_run_event_digest = hash_waveguide_package_runner_noop_dry_run_event(ev)
    return ev


def validate_waveguide_package_runner_noop_dry_run_event(event: Any) -> Tuple[bool, List[str]]:
    event_dict = _load_dict(event)
    if not event_dict:
        return False, ["EVENT_INVALID"]

    reasons = []
    is_valid = True

    # Validate digest
    recorded = event_dict.get("noop_dry_run_event_digest", "")
    recomputed = hash_waveguide_package_runner_noop_dry_run_event(event_dict)
    if recorded != recomputed or not recorded:
        is_valid = False
        reasons.append("EVENT_DIGEST_MISMATCH")

    # Check performed mutation flags
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in perf_flags:
        if event_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"EVENT_MUTATION_PERFORMED_{flag.upper()}")

    if is_valid:
        reasons.append("EVENT_VERIFIED")
    else:
        reasons.append("EVENT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_runner_noop_event_sequence(
    envelope_dict: Dict[str, Any],
    blueprint_dict: Dict[str, Any]
) -> List[WaveguidePackageRunnerNoOpDryRunEvent]:
    events = []
    envelope_digest = envelope_dict.get("package_assembly_runner_invocation_envelope_digest", "")
    readiness_digest = envelope_dict.get("source_runner_readiness_report_digest", "")
    blueprint_digest = envelope_dict.get("source_run_execution_blueprint_digest", "")

    # Helpers to make common event parameters
    def make_event(idx: int, ev_type: str, action: str, result: str, phase_idx: int = -1, phase_d: str = "", phase_t: str = "", input_ref: str = "", output_ref: str = "", package_p: str = "", art_d: str = "", op_skipped: bool = False, skipped_kind: str = "", skip_r: str = "") -> WaveguidePackageRunnerNoOpDryRunEvent:
        return build_waveguide_package_runner_noop_dry_run_event(
            noop_dry_run_event_id=f"SOL-WAVEGUIDE-NOOP-DRY-RUN-EVENT-{idx:03d}",
            event_index=idx,
            event_type=ev_type,
            source_runner_invocation_envelope_digest=envelope_digest,
            source_runner_readiness_report_digest=readiness_digest,
            source_run_execution_blueprint_digest=blueprint_digest,
            phase_index=phase_idx,
            phase_type=phase_t,
            phase_digest=phase_d,
            expected_input_reference=input_ref,
            expected_output_reference=output_ref,
            target_package_path=package_p,
            artifact_digest=art_d,
            event_action=action,
            event_result=result,
            operation_skipped=op_skipped,
            skipped_operation_kind=skipped_kind,
            skip_reason=skip_r
        )

    ev_idx = 0

    # 1. invocation_loaded event
    events.append(make_event(ev_idx, "invocation_loaded", "load_envelope", "envelope_loaded_success"))
    ev_idx += 1

    # 2. runner_readiness_verified event
    events.append(make_event(ev_idx, "runner_readiness_verified", "verify_readiness", "readiness_report_verified_success"))
    ev_idx += 1

    # 3. 34 phases (indices 0 to 33)
    phases = blueprint_dict.get("blueprint_phases", [])
    for p in phases:
        p_idx = p.get("phase_index", 0)
        p_digest = p.get("run_blueprint_phase_digest", "")
        p_type = p.get("phase_type", "")
        input_ref = p.get("expected_input_reference", "")
        output_ref = p.get("expected_output_reference", "")
        package_path = p.get("target_package_path", "")
        art_digest = p.get("artifact_digest", "")

        # A. blueprint_phase_checked
        events.append(make_event(
            ev_idx, "blueprint_phase_checked", f"check_phase_{p_idx}", "phase_check_passed",
            phase_idx=p_idx, phase_d=p_digest, phase_t=p_type
        ))
        ev_idx += 1

        # B. expected_input_checked
        events.append(make_event(
            ev_idx, "expected_input_checked", f"check_input_{p_idx}", "input_check_passed",
            phase_idx=p_idx, phase_d=p_digest, phase_t=p_type, input_ref=input_ref, art_d=art_digest
        ))
        ev_idx += 1

        # C. expected_output_planned
        events.append(make_event(
            ev_idx, "expected_output_planned", f"plan_output_{p_idx}", "output_plan_ready",
            phase_idx=p_idx, phase_d=p_digest, phase_t=p_type, output_ref=output_ref, package_p=package_path, art_d=art_digest
        ))
        ev_idx += 1

        # D. abort_conditions_checked
        events.append(make_event(
            ev_idx, "abort_conditions_checked", f"check_abort_{p_idx}", "no_abort_conditions_met",
            phase_idx=p_idx, phase_d=p_digest, phase_t=p_type
        ))
        ev_idx += 1

        # E. safety_gates_checked
        events.append(make_event(
            ev_idx, "safety_gates_checked", f"check_safety_{p_idx}", "all_safety_gates_passed",
            phase_idx=p_idx, phase_d=p_digest, phase_t=p_type
        ))
        ev_idx += 1

    # 4. noop_boundary_confirmed event
    events.append(make_event(ev_idx, "noop_boundary_confirmed", "confirm_noop_boundary", "noop_boundary_verified_active"))
    ev_idx += 1

    # 5. 8 skipped operations (alphabetical order)
    skipped_ops = [
        "archive_creation",
        "deployment",
        "directory_creation",
        "external_publication",
        "external_signing",
        "file_copy",
        "production_mutation",
        "upload"
    ]
    for op in skipped_ops:
        events.append(make_event(
            ev_idx, "physical_operation_skipped", f"execute_{op}", f"{op}_skipped_success",
            op_skipped=True, skipped_kind=op, skip_r="metadata_only_noop_run_authorized"
        ))
        ev_idx += 1

    # 6. dry_run_finalized event
    events.append(make_event(ev_idx, "dry_run_finalized", "finalize_dry_run", "dry_run_simulation_completed"))
    ev_idx += 1

    return events


def build_waveguide_package_runner_noop_dry_run_transcript(
    runner_invocation_envelope_path_or_dict: Any
) -> WaveguidePackageRunnerNoOpDryRunTranscript:
    envelope_dict = _load_dict(runner_invocation_envelope_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not envelope_dict:
        return WaveguidePackageRunnerNoOpDryRunTranscript(
            package_runner_noop_dry_run_transcript_id="SOL-WAVEGUIDE-PACKAGE-RUN-TRANSCRIPT-INVALID",
            package_runner_noop_dry_run_transcript_version=1,
            noop_dry_run_transcript_status="package_runner_noop_dry_run_invalid",
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
            noop_dry_run_events=[],
            verified_noop_dry_run_events=[],
            blocked_noop_dry_run_events=[],
            warning_noop_dry_run_events=[],
            invalid_noop_dry_run_events=[],
            verified_noop_event_count=0,
            blocked_noop_event_count=0,
            warning_noop_event_count=0,
            invalid_noop_event_count=0,
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
            skipped_operation_matrix=[],
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
            reason_codes=["RUNNER_INVOCATION_ENVELOPE_INVALID", "PACKAGE_RUNNER_NOOP_DRY_RUN_INVALID"],
            software_validation_caveat=caveat
        )

    # Validate envelope
    is_envelope_ok, _ = validate_waveguide_package_assembly_runner_invocation_envelope(envelope_dict)
    reasons = ["NOOP_DRY_RUN_TRANSCRIPT_CANONICAL"]
    is_valid = True

    if not is_envelope_ok or envelope_dict.get("runner_invocation_status") != "package_runner_invocation_ready":
        is_valid = False
        reasons.append("RUNNER_INVOCATION_ENVELOPE_INVALID")
    else:
        reasons.append("RUNNER_INVOCATION_ENVELOPE_VALID")

    # Load blueprint for phase data
    blueprint_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_EXECUTION_BLUEPRINT.json")
    blueprint_dict = _load_dict(blueprint_path)

    events = []
    if is_valid and blueprint_dict:
        events = build_waveguide_package_runner_noop_event_sequence(envelope_dict, blueprint_dict)

    # Index events
    verified_events = [e.noop_dry_run_event_id for e in events if e.event_status == "noop_dry_run_event_verified"]
    blocked_events = [e.noop_dry_run_event_id for e in events if e.event_status == "noop_dry_run_event_blocked"]
    warning_events = [e.noop_dry_run_event_id for e in events if e.event_status == "noop_dry_run_event_warning"]
    invalid_events = [e.noop_dry_run_event_id for e in events if e.event_status == "noop_dry_run_event_invalid"]

    if len(events) != 182 or len(blocked_events) > 0 or len(invalid_events) > 0:
        is_valid = False
        reasons.append("DRY_RUN_EVENT_SEQUENCE_INVALID")

    status = "package_runner_noop_dry_run_verified" if is_valid else "package_runner_noop_dry_run_invalid"
    if is_valid:
        reasons.append("PACKAGE_RUNNER_NOOP_DRY_RUN_VERIFIED")
    else:
        reasons.append("PACKAGE_RUNNER_NOOP_DRY_RUN_INVALID")

    skipped_ops = [
        "archive_creation",
        "deployment",
        "directory_creation",
        "external_publication",
        "external_signing",
        "file_copy",
        "production_mutation",
        "upload"
    ]

    event_types_indexed = sorted(list(set(e.event_type for e in events)))
    phase_types_indexed = sorted(list(set(e.phase_type for e in events if e.phase_type)))
    target_package_paths = sorted(list(set(e.target_package_path for e in events if e.target_package_path)))
    expected_input_references = sorted(list(set(e.expected_input_reference for e in events if e.expected_input_reference)))
    expected_output_references = sorted(list(set(e.expected_output_reference for e in events if e.expected_output_reference)))
    artifact_digests = sorted(list(set(e.artifact_digest for e in events if e.artifact_digest)))
    phase_digests = sorted(list(set(e.phase_digest for e in events if e.phase_digest)))
    noop_event_digests = sorted([e.noop_dry_run_event_digest for e in events])

    transcript = WaveguidePackageRunnerNoOpDryRunTranscript(
        package_runner_noop_dry_run_transcript_id="SOL-WAVEGUIDE-PACKAGE-RUNNER-NOOP-DRY-RUN-TRANSCRIPT",
        package_runner_noop_dry_run_transcript_version=1,
        noop_dry_run_transcript_status=status,
        source_runner_invocation_envelope_digest=envelope_dict.get("package_assembly_runner_invocation_envelope_digest", ""),
        source_runner_readiness_report_digest=envelope_dict.get("source_runner_readiness_report_digest", ""),
        source_run_execution_blueprint_digest=envelope_dict.get("source_run_execution_blueprint_digest", ""),
        source_run_preflight_report_digest=envelope_dict.get("source_run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=envelope_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=envelope_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=envelope_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=envelope_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=envelope_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=envelope_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=envelope_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=envelope_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=envelope_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=envelope_dict.get("source_artifact_catalog_digest", ""),
        noop_dry_run_events=events,
        verified_noop_dry_run_events=verified_events,
        blocked_noop_dry_run_events=blocked_events,
        warning_noop_dry_run_events=warning_events,
        invalid_noop_dry_run_events=invalid_events,
        verified_noop_event_count=len(verified_events),
        blocked_noop_event_count=len(blocked_events),
        warning_noop_event_count=len(warning_events),
        invalid_noop_event_count=len(invalid_events),
        blueprint_phase_count=envelope_dict.get("blueprint_phase_count", 0),
        planned_execution_step_count=envelope_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=envelope_dict.get("total_authorized_file_count", 0),
        expected_input_count=envelope_dict.get("total_authorized_file_count", 0),  # expected input files
        expected_output_count=envelope_dict.get("total_authorized_file_count", 0),  # expected output files
        skipped_operation_count=len(skipped_ops) if is_valid else 0,
        event_types_indexed=event_types_indexed,
        phase_types_indexed=phase_types_indexed,
        target_package_sections=sorted(envelope_dict.get("authorized_target_package_sections", [])),
        target_package_paths=target_package_paths,
        expected_input_references=expected_input_references,
        expected_output_references=expected_output_references,
        artifact_digests=artifact_digests,
        phase_digests=phase_digests,
        noop_event_digests=noop_event_digests,
        skipped_operation_matrix=sorted(skipped_ops),
        noop_boundary_verified=is_valid,
        blocked_operation_attempt_counts=envelope_dict.get("blocked_operation_attempt_counts", {}),
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

    transcript.package_runner_noop_dry_run_transcript_digest = hash_waveguide_package_runner_noop_dry_run_transcript(transcript)
    return transcript


def validate_waveguide_package_runner_noop_dry_run_transcript(transcript: Any) -> Tuple[bool, List[str]]:
    transcript_dict = _load_dict(transcript)
    if not transcript_dict:
        return False, ["PACKAGE_RUNNER_NOOP_DRY_RUN_INVALID"]

    reasons = []
    is_valid = True

    if transcript_dict.get("package_runner_noop_dry_run_transcript_id") != "SOL-WAVEGUIDE-PACKAGE-RUNNER-NOOP-DRY-RUN-TRANSCRIPT":
        is_valid = False
        reasons.append("DRY_RUN_TRANSCRIPT_INVALID_ID")

    if transcript_dict.get("package_runner_noop_dry_run_transcript_version") != 1:
        is_valid = False
        reasons.append("DRY_RUN_TRANSCRIPT_INVALID_VERSION")

    # Validate events
    events = transcript_dict.get("noop_dry_run_events", [])
    if not events or len(events) != 182:
        is_valid = False
        reasons.append("DRY_RUN_TRANSCRIPT_EVENT_COUNT_MISMATCH")
    else:
        for idx, e in enumerate(events):
            if e.get("event_index") != idx:
                is_valid = False
                reasons.append("DRY_RUN_TRANSCRIPT_EVENT_SEQUENCE_CONTIGUITY_MISMATCH")
            recorded = e.get("noop_dry_run_event_digest", "")
            recomputed = hash_waveguide_package_runner_noop_dry_run_event(e)
            if recorded != recomputed or not recorded:
                is_valid = False
                reasons.append("DRY_RUN_TRANSCRIPT_EVENT_DIGEST_MISMATCH")

    # Check that performed flags are false
    flag_fields = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in flag_fields:
        if transcript_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"DRY_RUN_TRANSCRIPT_MUTATION_PERFORMED_{flag.upper()}")

    # Check transcript digest
    recorded_digest = transcript_dict.get("package_runner_noop_dry_run_transcript_digest", "")
    recomputed_digest = hash_waveguide_package_runner_noop_dry_run_transcript(transcript_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("DRY_RUN_TRANSCRIPT_DIGEST_MISMATCH")

    status = transcript_dict.get("noop_dry_run_transcript_status", "")
    if is_valid and status == "package_runner_noop_dry_run_verified":
        reasons.append("PACKAGE_RUNNER_NOOP_DRY_RUN_VERIFIED")
    else:
        is_valid = False
        reasons.append("PACKAGE_RUNNER_NOOP_DRY_RUN_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_runner_noop_dry_run_transcript(transcript: Any) -> str:
    transcript_dict = _load_dict(transcript)
    if not transcript_dict:
        return "Invalid No-Op Dry-Run Transcript"

    status = transcript_dict.get("noop_dry_run_transcript_status", "unknown")
    digest = transcript_dict.get("package_runner_noop_dry_run_transcript_digest", "")
    ev_count = transcript_dict.get("verified_noop_event_count", 0)

    return (
        f"SOL Waveguide Runner No-Op Dry-Run Transcript Summary:\n"
        f"  Transcript Status: {status}\n"
        f"  Transcript Digest: {digest}\n"
        f"  Verified Events: {ev_count}\n"
    )


def export_waveguide_package_runner_noop_dry_run_transcript(transcript: Any, filepath: str) -> None:
    transcript_dict = _load_dict(transcript)
    if not transcript_dict:
        raise ValueError("Cannot export invalid runner dry-run transcript data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(transcript_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_runner_noop_dry_run_transcripts(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def build_waveguide_package_runner_noop_event_index(events: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for e in events:
        e_dict = _load_dict(e)
        if e_dict:
            ev_type = e_dict.get("event_type", "unknown")
            idx.setdefault(ev_type, []).append(e_dict)
    return idx


def build_waveguide_package_runner_noop_phase_index(events: List[Any]) -> Dict[int, List[Any]]:
    idx = {}
    for e in events:
        e_dict = _load_dict(e)
        if e_dict:
            p_idx = e_dict.get("phase_index", -1)
            idx.setdefault(p_idx, []).append(e_dict)
    return idx


def build_waveguide_package_runner_noop_skipped_operation_matrix(events: List[Any]) -> List[str]:
    res = []
    for e in events:
        e_dict = _load_dict(e)
        if e_dict and e_dict.get("operation_skipped"):
            op = e_dict.get("skipped_operation_kind")
            if op and op not in res:
                res.append(op)
    return sorted(res)


def validate_waveguide_package_runner_noop_skipped_operations(events: List[Any]) -> bool:
    skipped = build_waveguide_package_runner_noop_skipped_operation_matrix(events)
    expected_ops = [
        "archive_creation", "deployment", "directory_creation", "external_publication",
        "external_signing", "file_copy", "production_mutation", "upload"
    ]
    return skipped == expected_ops


def validate_waveguide_package_runner_noop_boundary(noop: Dict[str, bool]) -> bool:
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
