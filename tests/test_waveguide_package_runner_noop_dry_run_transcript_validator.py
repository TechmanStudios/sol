# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Runner No-Op Dry-Run Transcript Validator.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_runner_noop_dry_run_transcript_validator import (
    WaveguidePackageRunnerTranscriptAuditCase,
    WaveguidePackageRunnerTranscriptAuditReport,
    build_waveguide_package_runner_transcript_audit_case,
    validate_waveguide_package_runner_noop_dry_run_transcript_independently,
    build_waveguide_package_runner_transcript_audit_report,
    validate_waveguide_package_runner_transcript_audit_report,
    summarize_waveguide_package_runner_transcript_audit_report,
    export_waveguide_package_runner_transcript_audit_report,
    compare_waveguide_package_runner_transcript_audit_reports,
    hash_waveguide_package_runner_transcript_audit_case,
    hash_waveguide_package_runner_transcript_audit_report
)


@pytest.fixture
def clean_envelope() -> dict:
    envelope_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUNNER_INVOCATION_ENVELOPE.json")
    assert os.path.exists(envelope_path), "Missing runner invocation envelope JSON"
    with open(envelope_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def clean_transcript() -> dict:
    transcript_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT.json")
    assert os.path.exists(transcript_path), "Missing runner dry-run transcript JSON"
    with open(transcript_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_audit_case_build_and_validation(clean_envelope, clean_transcript):
    event = clean_transcript["noop_dry_run_events"][0]
    # 1. Transcript audit case can be built.
    case = build_waveguide_package_runner_transcript_audit_case(event, clean_transcript, clean_envelope)
    assert isinstance(case, WaveguidePackageRunnerTranscriptAuditCase)
    
    # 2. Transcript audit case validates (status verified).
    assert case.transcript_audit_status == "transcript_event_audit_verified"
    
    # 3. Transcript audit case digest is deterministic.
    digest1 = hash_waveguide_package_runner_transcript_audit_case(case)
    digest2 = hash_waveguide_package_runner_transcript_audit_case(case)
    assert digest1 == digest2
    assert case.transcript_audit_case_digest == digest1

    # 4. transcript_audit_case_digest is excluded from its own digest input.
    case_dict = asdict(case)
    case_dict["transcript_audit_case_digest"] = "DUMMY_VALUE"
    digest_with_dummy = hash_waveguide_package_runner_transcript_audit_case(case_dict)
    assert digest_with_dummy == digest1


def test_transcript_digest_mismatch_blocks_audit(clean_envelope, clean_transcript):
    event = clean_transcript["noop_dry_run_events"][0]
    # 5. Transcript digest mismatch blocks audit.
    bad_transcript = dict(clean_transcript)
    bad_transcript["package_runner_noop_dry_run_transcript_digest"] = "wrong_digest"
    case = build_waveguide_package_runner_transcript_audit_case(event, bad_transcript, clean_envelope)
    assert case.transcript_audit_status == "transcript_event_audit_blocked"


def test_event_digest_mismatch_blocks_audit(clean_envelope, clean_transcript):
    event = dict(clean_transcript["noop_dry_run_events"][0])
    # 6. Event digest mismatch blocks audit.
    event["noop_dry_run_event_digest"] = "wrong_event_digest"
    case = build_waveguide_package_runner_transcript_audit_case(event, clean_transcript, clean_envelope)
    assert case.transcript_audit_status == "transcript_event_audit_blocked"


def test_runner_invocation_envelope_issues(clean_envelope, clean_transcript):
    event = clean_transcript["noop_dry_run_events"][0]
    
    # 7. Runner invocation validation failure blocks audit.
    bad_envelope = dict(clean_envelope)
    bad_envelope["package_assembly_runner_invocation_envelope_digest"] = "wrong_env_digest"
    case = build_waveguide_package_runner_transcript_audit_case(event, clean_transcript, bad_envelope)
    assert case.transcript_audit_status == "transcript_event_audit_blocked"

    # 8. Runner invocation status not ready blocks audit.
    bad_envelope2 = dict(clean_envelope)
    bad_envelope2["runner_invocation_status"] = "package_runner_invocation_failed"
    # recalculate its digest to make it valid structurally, but status is not ready
    from sol_waveguide_package_assembly_runner_invocation_envelope import hash_waveguide_package_assembly_runner_invocation_envelope
    bad_envelope2["package_assembly_runner_invocation_envelope_digest"] = hash_waveguide_package_assembly_runner_invocation_envelope(bad_envelope2)
    
    # We must also update the digest referenced by transcript to not trigger digest mismatch
    bad_transcript = dict(clean_transcript)
    bad_transcript["source_runner_invocation_envelope_digest"] = bad_envelope2["package_assembly_runner_invocation_envelope_digest"]
    
    case = build_waveguide_package_runner_transcript_audit_case(event, bad_transcript, bad_envelope2)
    assert case.transcript_audit_status == "transcript_event_audit_blocked"


def test_mutation_flags_and_blocked_attempts_block_audit(clean_envelope, clean_transcript):
    event = dict(clean_transcript["noop_dry_run_events"][0])
    
    # 13. Any performed mutation flag true blocks audit.
    event["physical_execution_performed"] = True
    case = build_waveguide_package_runner_transcript_audit_case(event, clean_transcript, clean_envelope)
    assert case.transcript_audit_status == "transcript_event_audit_blocked"

    # 14. Nonzero blocked operation count blocks audit.
    bad_transcript = dict(clean_transcript)
    bad_transcript["blocked_operation_attempt_counts"] = {
        "archive_creation": 1,
        "deployment": 0,
        "directory_creation": 0,
        "external_publication": 0,
        "external_signing": 0,
        "file_copy": 0,
        "production_mutation": 0,
        "upload": 0
    }
    event2 = clean_transcript["noop_dry_run_events"][0]
    case2 = build_waveguide_package_runner_transcript_audit_case(event2, bad_transcript, clean_envelope)
    assert case2.transcript_audit_status == "transcript_event_audit_blocked"


def test_report_building_and_validation(clean_envelope, clean_transcript):
    # 15. Top-level transcript audit report builds.
    report = build_waveguide_package_runner_transcript_audit_report(clean_transcript, clean_envelope)
    assert isinstance(report, WaveguidePackageRunnerTranscriptAuditReport)

    # 16. Top-level transcript audit report validates.
    ok, reasons = validate_waveguide_package_runner_transcript_audit_report(report)
    assert ok is True
    assert "PACKAGE_RUNNER_NOOP_TRANSCRIPT_AUDIT_VERIFIED" in reasons

    # 17. Transcript audit report digest is deterministic.
    digest1 = hash_waveguide_package_runner_transcript_audit_report(report)
    digest2 = hash_waveguide_package_runner_transcript_audit_report(report)
    assert digest1 == digest2
    assert report.transcript_audit_report_digest == digest1

    # 18. transcript_audit_report_digest is excluded from its own digest input.
    rep_dict = asdict(report)
    rep_dict["transcript_audit_report_digest"] = "DUMMY"
    digest_with_dummy = hash_waveguide_package_runner_transcript_audit_report(rep_dict)
    assert digest_with_dummy == digest1

    # 19. Verified transcript audit case count is 182.
    assert report.verified_transcript_audit_count == 182
    assert len(report.audited_cases) == 182

    # 20. Event counts are verified.
    assert report.event_counts_verified is True
    assert report.event_sequence_verified is True
    assert report.skipped_operation_matrix_verified is True


def test_bad_event_counts_and_sequence_block_report(clean_envelope, clean_transcript):
    # 9. Event sequence mismatch blocks audit.
    # 10. Event count mismatch blocks audit.
    # 11. Skipped operation matrix mismatch blocks audit.
    # 12. No-op boundary missing/invalid blocks audit.
    bad_transcript = dict(clean_transcript)
    # truncate events
    bad_transcript["noop_dry_run_events"] = clean_transcript["noop_dry_run_events"][:-1]
    
    # We must recompute the transcript digest so that is_compat_ok doesn't fail on transcript digest mismatch.
    # Let's import the hashing function.
    from sol_waveguide_package_runner_noop_dry_run_transcript import hash_waveguide_package_runner_noop_dry_run_transcript
    bad_transcript["package_runner_noop_dry_run_transcript_digest"] = hash_waveguide_package_runner_noop_dry_run_transcript(bad_transcript)

    report = build_waveguide_package_runner_transcript_audit_report(bad_transcript, clean_envelope)
    assert report.transcript_audit_report_status == "package_runner_noop_transcript_audit_invalid"


def test_artifacts_exist():
    # 21. Transcript audit JSON artifact exists.
    json_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT_AUDIT_REPORT.json")
    assert os.path.exists(json_path)

    # 22. Transcript audit documentation exists.
    md_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT_VALIDATOR.md")
    assert os.path.exists(md_path)
