# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Runner No-Op Dry-Run Transcript.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_runner_noop_dry_run_transcript import (
    WaveguidePackageRunnerNoOpDryRunEvent,
    WaveguidePackageRunnerNoOpDryRunTranscript,
    build_waveguide_package_runner_noop_dry_run_event,
    validate_waveguide_package_runner_noop_dry_run_event,
    build_waveguide_package_runner_noop_dry_run_transcript,
    validate_waveguide_package_runner_noop_dry_run_transcript,
    summarize_waveguide_package_runner_noop_dry_run_transcript,
    export_waveguide_package_runner_noop_dry_run_transcript,
    compare_waveguide_package_runner_noop_dry_run_transcripts,
    hash_waveguide_package_runner_noop_dry_run_event,
    hash_waveguide_package_runner_noop_dry_run_transcript,
    validate_waveguide_package_runner_noop_skipped_operations,
    validate_waveguide_package_runner_noop_boundary
)


@pytest.fixture
def clean_envelope() -> dict:
    envelope_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUNNER_INVOCATION_ENVELOPE.json")
    assert os.path.exists(envelope_path), "Missing runner invocation envelope JSON"
    with open(envelope_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_dry_run_event_build_and_validation(clean_envelope):
    # 1. No-op dry-run event builds.
    event = WaveguidePackageRunnerNoOpDryRunEvent(
        noop_dry_run_event_id="SOL-WAVEGUIDE-NOOP-DRY-RUN-EVENT-000",
        event_index=0,
        event_type="invocation_loaded",
        event_status="noop_dry_run_event_verified",
        source_runner_invocation_envelope_digest=clean_envelope.get("package_assembly_runner_invocation_envelope_digest"),
        source_runner_readiness_report_digest=clean_envelope.get("source_runner_readiness_report_digest"),
        source_run_execution_blueprint_digest=clean_envelope.get("source_run_execution_blueprint_digest"),
        phase_index=-1,
        phase_type="",
        phase_digest="",
        expected_input_reference="",
        expected_output_reference="",
        target_package_path="",
        artifact_digest="",
        event_action="load_envelope",
        event_result="envelope_loaded_success",
        operation_skipped=False,
        skipped_operation_kind="",
        skip_reason="",
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
        notes=[],
        software_validation_caveat="Sandbox validation caveat"
    )
    event.noop_dry_run_event_digest = hash_waveguide_package_runner_noop_dry_run_event(event)

    # 2. No-op dry-run event validates.
    ok, reasons = validate_waveguide_package_runner_noop_dry_run_event(event)
    assert ok is True
    assert "EVENT_VERIFIED" in reasons or len(reasons) == 0


def test_dry_run_event_digest_determinism_and_exclusion(clean_envelope):
    # Helper to build simple event
    def build_test_event():
        ev = WaveguidePackageRunnerNoOpDryRunEvent(
            noop_dry_run_event_id="SOL-WAVEGUIDE-NOOP-DRY-RUN-EVENT-000",
            event_index=0,
            event_type="invocation_loaded",
            event_status="noop_dry_run_event_verified",
            source_runner_invocation_envelope_digest=clean_envelope.get("package_assembly_runner_invocation_envelope_digest"),
            source_runner_readiness_report_digest=clean_envelope.get("source_runner_readiness_report_digest"),
            source_run_execution_blueprint_digest=clean_envelope.get("source_run_execution_blueprint_digest"),
            phase_index=-1,
            phase_type="",
            phase_digest="",
            expected_input_reference="",
            expected_output_reference="",
            target_package_path="",
            artifact_digest="",
            event_action="load_envelope",
            event_result="envelope_loaded_success",
            operation_skipped=False,
            skipped_operation_kind="",
            skip_reason="",
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
            notes=[],
            software_validation_caveat="Sandbox validation caveat"
        )
        ev.noop_dry_run_event_digest = hash_waveguide_package_runner_noop_dry_run_event(ev)
        return ev

    # 3. Event digest is deterministic.
    e1 = build_test_event()
    e2 = build_test_event()
    assert e1.noop_dry_run_event_digest == e2.noop_dry_run_event_digest
    assert len(e1.noop_dry_run_event_digest) == 64

    # 4. noop_dry_run_event_digest is excluded from its own digest input.
    e_dict = asdict(e1)
    e_dict["noop_dry_run_event_digest"] = "MUTATED_EVENT_SELF_DIGEST"
    recomputed = hash_waveguide_package_runner_noop_dry_run_event(e_dict)
    assert recomputed == e1.noop_dry_run_event_digest


def test_dry_run_event_validation_failures(clean_envelope):
    base_event = WaveguidePackageRunnerNoOpDryRunEvent(
        noop_dry_run_event_id="SOL-WAVEGUIDE-NOOP-DRY-RUN-EVENT-000",
        event_index=0,
        event_type="invocation_loaded",
        event_status="noop_dry_run_event_verified",
        source_runner_invocation_envelope_digest=clean_envelope.get("package_assembly_runner_invocation_envelope_digest"),
        source_runner_readiness_report_digest=clean_envelope.get("source_runner_readiness_report_digest"),
        source_run_execution_blueprint_digest=clean_envelope.get("source_run_execution_blueprint_digest"),
        phase_index=-1,
        phase_type="",
        phase_digest="",
        expected_input_reference="",
        expected_output_reference="",
        target_package_path="",
        artifact_digest="",
        event_action="load_envelope",
        event_result="envelope_loaded_success",
        operation_skipped=False,
        skipped_operation_kind="",
        skip_reason="",
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
        notes=[],
        software_validation_caveat="Sandbox validation caveat"
    )

    # 5. Any performed mutation flag true blocks event.
    mutation_perf_fields = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for field in mutation_perf_fields:
        e_dict = asdict(base_event)
        e_dict[field] = True
        e_dict["noop_dry_run_event_digest"] = hash_waveguide_package_runner_noop_dry_run_event(e_dict)
        ok, _ = validate_waveguide_package_runner_noop_dry_run_event(e_dict)
        assert not ok


def test_transcript_build_and_validation(clean_envelope):
    # 6. Transcript builds.
    transcript = build_waveguide_package_runner_noop_dry_run_transcript(clean_envelope)
    assert isinstance(transcript, WaveguidePackageRunnerNoOpDryRunTranscript)
    assert transcript.noop_dry_run_transcript_status == "package_runner_noop_dry_run_verified"

    # 7. Transcript validates.
    ok, reasons = validate_waveguide_package_runner_noop_dry_run_transcript(transcript)
    assert ok is True
    assert "PACKAGE_RUNNER_NOOP_DRY_RUN_VERIFIED" in reasons


def test_transcript_digest_determinism_and_exclusion(clean_envelope):
    # 8. Transcript digest is deterministic.
    t1 = build_waveguide_package_runner_noop_dry_run_transcript(clean_envelope)
    t2 = build_waveguide_package_runner_noop_dry_run_transcript(clean_envelope)
    assert t1.package_runner_noop_dry_run_transcript_digest == t2.package_runner_noop_dry_run_transcript_digest

    # 9. package_runner_noop_dry_run_transcript_digest is excluded from its own digest input.
    t_dict = asdict(t1)
    t_dict["package_runner_noop_dry_run_transcript_digest"] = "MUTATED_TRANSCRIPT_SELF_DIGEST"
    recomputed = hash_waveguide_package_runner_noop_dry_run_transcript(t_dict)
    assert recomputed == t1.package_runner_noop_dry_run_transcript_digest


def test_transcript_validation_failures(clean_envelope):
    # 10. Runner invocation validation failure blocks transcript.
    bad_envelope = dict(clean_envelope, runner_invocation_status="package_runner_invocation_invalid")
    t = build_waveguide_package_runner_noop_dry_run_transcript(bad_envelope)
    assert t.noop_dry_run_transcript_status == "package_runner_noop_dry_run_invalid"

    # 11. Runner invocation status not ready blocks transcript.
    bad_envelope2 = dict(clean_envelope, runner_invocation_status="package_runner_invocation_blocked")
    t2 = build_waveguide_package_runner_noop_dry_run_transcript(bad_envelope2)
    assert t2.noop_dry_run_transcript_status == "package_runner_noop_dry_run_invalid"


def test_transcript_event_sequence_properties(clean_envelope):
    transcript = build_waveguide_package_runner_noop_dry_run_transcript(clean_envelope)
    events = transcript.noop_dry_run_events

    # 12. Event sequence is deterministic (contiguous event indices starting from 0).
    for idx, e in enumerate(events):
        assert e.event_index == idx

    # 13. Event count is 182.
    assert len(events) == 182

    # 14. Blueprint phase checks count is 34.
    phase_checks = [e for e in events if e.event_type == "blueprint_phase_checked"]
    assert len(phase_checks) == 34

    # 15. Expected input checks count is 34.
    input_checks = [e for e in events if e.event_type == "expected_input_checked"]
    assert len(input_checks) == 34

    # 16. Expected output planned count is 34.
    output_plans = [e for e in events if e.event_type == "expected_output_planned"]
    assert len(output_plans) == 34

    # 17. Abort condition check count is 34.
    abort_checks = [e for e in events if e.event_type == "abort_conditions_checked"]
    assert len(abort_checks) == 34

    # 18. Safety gate check count is 34.
    safety_checks = [e for e in events if e.event_type == "safety_gates_checked"]
    assert len(safety_checks) == 34

    # 19. Physical operation skipped count is 8.
    skipped_ops = [e for e in events if e.event_type == "physical_operation_skipped"]
    assert len(skipped_ops) == 8


def test_skipped_operation_matrix_and_boundaries(clean_envelope):
    transcript = build_waveguide_package_runner_noop_dry_run_transcript(clean_envelope)

    # 20. Skipped operation matrix verifies.
    assert validate_waveguide_package_runner_noop_skipped_operations(transcript.noop_dry_run_events) is True

    # 21. No-op boundary verifies.
    assert transcript.noop_boundary_verified is True

    # 22. All mutation performed flags remain false.
    perf_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in perf_flags:
        assert getattr(transcript, flag) is False


def test_transcript_artifacts_exist():
    # 23. JSON artifact exists.
    json_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT.json")
    assert os.path.exists(json_path)

    # 24. Documentation exists.
    md_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT.md")
    assert os.path.exists(md_path)
