# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Governed Pass Replay Verifier
"""

import os
import json
import pytest

from sol_waveguide_governed_pass_replay import (
    build_waveguide_governed_pass_replay_case,
    verify_waveguide_governed_pass_replay,
    validate_waveguide_governed_pass_replay_report,
    summarize_waveguide_governed_pass_replay_report,
    export_waveguide_governed_pass_replay_report,
    compare_waveguide_governed_pass_replay_reports,
    hash_waveguide_governed_pass_replay_case,
    hash_waveguide_governed_pass_replay_report,
    replay_waveguide_registered_safe_handler,
    verify_waveguide_replay_entry,
    KNOWN_PAYLOADS,
    WaveguideGovernedPassReplayCase
)
from sol_waveguide_execution_trace_ledger import (
    build_waveguide_execution_trace_entry
)
from sol_waveguide_rc_promotion_ledger import REPO_ROOT


def load_standard_test_fixtures():
    ledger_path = "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json"
    full_led_path = os.path.join(REPO_ROOT, ledger_path)
    with open(full_led_path, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    # Find the entries
    entry_rc1_exec = None
    entry_rc2_exec = None
    entry_rc1_rej = None

    for entry in ledger["entries"]:
        if entry["rc_id"] == "SOL-WAVEGUIDE-RC1" and entry["execution_status"] == "trace_executed":
            entry_rc1_exec = entry
        elif entry["rc_id"] == "SOL-WAVEGUIDE-RC2" and entry["execution_status"] == "trace_executed":
            entry_rc2_exec = entry
        elif entry["rc_id"] == "SOL-WAVEGUIDE-RC1" and entry["execution_status"] == "trace_rejected":
            entry_rc1_rej = entry

    return ledger, entry_rc1_exec, entry_rc2_exec, entry_rc1_rej


def test_replay_cases_can_be_built():
    ledger, entry1, entry2, entry3 = load_standard_test_fixtures()

    # Load execution records
    with open(os.path.join(REPO_ROOT, entry1["execution_record_path"]), "r", encoding="utf-8") as f:
        rec1 = json.load(f)
    with open(os.path.join(REPO_ROOT, entry2["execution_record_path"]), "r", encoding="utf-8") as f:
        rec2 = json.load(f)
    with open(os.path.join(REPO_ROOT, entry3["execution_record_path"]), "r", encoding="utf-8") as f:
        rec3 = json.load(f)

    case1 = build_waveguide_governed_pass_replay_case(entry1, rec1, "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json", ledger["ledger_digest"], "ledger_valid")
    case2 = build_waveguide_governed_pass_replay_case(entry2, rec2, "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json", ledger["ledger_digest"], "ledger_valid")
    case3 = build_waveguide_governed_pass_replay_case(entry3, rec3, "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json", ledger["ledger_digest"], "ledger_valid")

    assert case1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert case2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert case3.rc_id == "SOL-WAVEGUIDE-RC1"

    assert case1.replay_case_status == "replay_case_ready"
    assert case2.replay_case_status == "replay_case_ready"
    assert case3.replay_case_status == "replay_case_rejected_record"


def test_replay_case_digest_excludes_self():
    _, entry, _, _ = load_standard_test_fixtures()
    with open(os.path.join(REPO_ROOT, entry["execution_record_path"]), "r", encoding="utf-8") as f:
        rec = json.load(f)

    case = build_waveguide_governed_pass_replay_case(entry, rec, "dummy", "digest", "valid")
    case_dict = case.__dict__.copy()
    case_dict["replay_case_digest"] = "different_value"

    d1 = hash_waveguide_governed_pass_replay_case(case)
    d2 = hash_waveguide_governed_pass_replay_case(case_dict)
    assert d1 == d2


def test_replay_report_digest_excludes_self():
    ledger_path = "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json"
    report = verify_waveguide_governed_pass_replay(ledger_path)
    r_dict = report.__dict__.copy()
    r_dict["replay_report_digest"] = "different_value"

    d1 = hash_waveguide_governed_pass_replay_report(report)
    d2 = hash_waveguide_governed_pass_replay_report(r_dict)
    assert d1 == d2


def test_standard_records_replay_successfully():
    ledger, entry1, entry2, entry3 = load_standard_test_fixtures()

    with open(os.path.join(REPO_ROOT, entry1["execution_record_path"]), "r", encoding="utf-8") as f:
        rec1 = json.load(f)
    with open(os.path.join(REPO_ROOT, entry2["execution_record_path"]), "r", encoding="utf-8") as f:
        rec2 = json.load(f)
    with open(os.path.join(REPO_ROOT, entry3["execution_record_path"]), "r", encoding="utf-8") as f:
        rec3 = json.load(f)

    case1 = build_waveguide_governed_pass_replay_case(entry1, rec1, "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json", ledger["ledger_digest"], "ledger_valid")
    case2 = build_waveguide_governed_pass_replay_case(entry2, rec2, "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json", ledger["ledger_digest"], "ledger_valid")
    case3 = build_waveguide_governed_pass_replay_case(entry3, rec3, "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json", ledger["ledger_digest"], "ledger_valid")

    ok1, reasons1 = verify_waveguide_replay_entry(case1, execution_record=rec1, trace_entry=entry1)
    ok2, reasons2 = verify_waveguide_replay_entry(case2, execution_record=rec2, trace_entry=entry2)
    ok3, reasons3 = verify_waveguide_replay_entry(case3, execution_record=rec3, trace_entry=entry3)

    assert ok1 is True
    assert ok2 is True
    assert ok3 is True

    assert case1.replay_status == "replay_verified"
    assert case2.replay_status == "replay_verified"
    assert case3.replay_status == "replay_rejected_record_verified"

    assert "PASS_REPLAY_OUTPUT_DIGEST_MATCH" in reasons1
    assert "PASS_REPLAY_OUTPUT_DIGEST_MATCH" in reasons2
    assert "PASS_REPLAY_REJECTED_RECORD_NOT_REPLAYED" in reasons3


def test_tampered_execution_record_fails():
    _, entry, _, _ = load_standard_test_fixtures()
    with open(os.path.join(REPO_ROOT, entry["execution_record_path"]), "r", encoding="utf-8") as f:
        rec = json.load(f)

    case = build_waveguide_governed_pass_replay_case(entry, rec, "ledger", "digest", "valid")

    # Tamper with record content so it doesn't match case's record digest
    case.execution_record_digest = "tampered_digest"

    ok, reasons = verify_waveguide_replay_entry(case, execution_record=rec, trace_entry=entry)
    assert ok is False
    assert case.replay_status == "replay_failed"
    assert "PASS_REPLAY_RECORD_DIGEST_MISMATCH" in reasons


def test_tampered_output_digest_fails():
    _, entry, _, _ = load_standard_test_fixtures()
    with open(os.path.join(REPO_ROOT, entry["execution_record_path"]), "r", encoding="utf-8") as f:
        rec = json.load(f)

    case = build_waveguide_governed_pass_replay_case(entry, rec, "ledger", "digest", "valid")

    # Tamper with output digest in the case
    case.recorded_output_payload_digest = "tampered_digest"

    # Must recompute case digest if we mutate it
    case.replay_case_digest = hash_waveguide_governed_pass_replay_case(case)

    ok, reasons = verify_waveguide_replay_entry(case, execution_record=rec, trace_entry=entry)
    assert ok is False
    assert case.replay_status == "replay_failed"
    assert "PASS_REPLAY_OUTPUT_DIGEST_MISMATCH" in reasons


def test_missing_handler_fails():
    _, entry, _, _ = load_standard_test_fixtures()
    with open(os.path.join(REPO_ROOT, entry["execution_record_path"]), "r", encoding="utf-8") as f:
        rec = json.load(f)

    case = build_waveguide_governed_pass_replay_case(entry, rec, "ledger", "digest", "valid")

    # Request an unregistered pass
    case.requested_pass = "nonexistent_pass"
    case.replay_case_digest = hash_waveguide_governed_pass_replay_case(case)

    ok, reasons = verify_waveguide_replay_entry(case, execution_record=rec, trace_entry=entry)
    assert ok is False
    assert case.replay_status == "replay_failed"
    assert "PASS_REPLAY_HANDLER_MISSING" in reasons


def test_invalid_trace_entry_fails():
    _, entry, _, _ = load_standard_test_fixtures()
    with open(os.path.join(REPO_ROOT, entry["execution_record_path"]), "r", encoding="utf-8") as f:
        rec = json.load(f)

    case = build_waveguide_governed_pass_replay_case(entry, rec, "ledger", "digest", "valid")

    # Tamper trace entry digest
    entry_copy = dict(entry)
    entry_copy["trace_entry_digest"] = "tampered"

    ok, reasons = verify_waveguide_replay_entry(case, execution_record=rec, trace_entry=entry_copy)
    assert ok is False
    assert case.replay_status == "replay_failed"
    assert "PASS_REPLAY_TRACE_ENTRY_INVALID" in reasons


def test_invalid_governed_execution_record_fails():
    _, entry, _, _ = load_standard_test_fixtures()
    with open(os.path.join(REPO_ROOT, entry["execution_record_path"]), "r", encoding="utf-8") as f:
        rec = json.load(f)

    # Tamper execution record digest so the record itself fails internally
    rec_copy = dict(rec)
    rec_copy["execution_record_digest"] = "tampered"

    case = build_waveguide_governed_pass_replay_case(entry, rec_copy, "ledger", "digest", "valid")
    # Make sure we matching the record digest reference
    case.execution_record_digest = "tampered"
    case.replay_case_digest = hash_waveguide_governed_pass_replay_case(case)

    ok, reasons = verify_waveguide_replay_entry(case, execution_record=rec_copy, trace_entry=entry)
    assert ok is False
    assert case.replay_status == "replay_failed"
    assert "PASS_REPLAY_EXECUTION_RECORD_INVALID" in reasons


def test_replay_report_builds_and_validates():
    ledger_path = "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json"
    report = verify_waveguide_governed_pass_replay(ledger_path)

    assert report.replay_report_status == "replay_report_verified"
    assert report.verified_execution_count == 2
    assert report.verified_rejection_count == 1
    assert report.failed_replay_count == 0
    assert report.skipped_replay_count == 0

    ok, reasons = validate_waveguide_governed_pass_replay_report(report)
    assert ok is True
    assert "PASS_REPLAY_REPORT_VERIFIED" in reasons


def test_invalid_trace_ledger_fails_report():
    # Load and invalidate the ledger
    ledger, _, _, _ = load_standard_test_fixtures()
    ledger["ledger_digest"] = "tampered"

    report = verify_waveguide_governed_pass_replay(ledger)
    assert report.replay_report_status == "replay_report_failed"
    assert "PASS_REPLAY_LEDGER_INVALID" in report.reason_codes


def test_report_lists_sorted_and_unique():
    ledger_path = "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json"
    report = verify_waveguide_governed_pass_replay(ledger_path)

    assert report.handler_ids_replayed == sorted(report.handler_ids_replayed)
    assert report.source_execution_record_digests == sorted(report.source_execution_record_digests)
    assert report.source_trace_entry_digests == sorted(report.source_trace_entry_digests)


def test_report_summary_and_export():
    ledger_path = "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json"
    report = verify_waveguide_governed_pass_replay(ledger_path)

    summary = summarize_waveguide_governed_pass_replay_report(report)
    assert "SOL WAVEGUIDE GOVERNED PASS REPLAY REPORT SUMMARY" in summary
    assert "Report ID: SOL-WAVEGUIDE-GOVERNED-PASS-REPLAY-REPORT" in summary

    # Export check
    temp_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_REPLAY_REPORT_TEMP.json"
    full_temp_path = os.path.join(REPO_ROOT, temp_path)
    export_waveguide_governed_pass_replay_report(report, full_temp_path)
    
    assert os.path.exists(full_temp_path)
    with open(full_temp_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["replay_report_digest"] == report.replay_report_digest
    
    os.remove(full_temp_path)


def test_artifact_files_exist():
    # Report JSON exists
    rep_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_REPLAY_REPORT.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_REPLAY.md")

    assert os.path.exists(rep_path)
    assert os.path.exists(doc_path)
