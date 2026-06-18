# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Governed Compiler Session Verifier
"""

import os
import json
import pytest

from sol_waveguide_governed_compiler_session_verifier import (
    build_waveguide_governed_compiler_session_verification_case,
    verify_waveguide_governed_compiler_session,
    validate_waveguide_governed_compiler_session_verification_report,
    summarize_waveguide_governed_compiler_session_verification_report,
    export_waveguide_governed_compiler_session_verification_report,
    compare_waveguide_governed_compiler_session_verification_reports,
    hash_waveguide_governed_compiler_session_verification_case,
    hash_waveguide_governed_compiler_session_verification_report
)
from sol_waveguide_rc_promotion_ledger import REPO_ROOT

def test_session_verification_cases_can_be_built():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    rc2_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_REJECTION_EXAMPLE.json"

    case1 = build_waveguide_governed_compiler_session_verification_case(rc1_path)
    case2 = build_waveguide_governed_compiler_session_verification_case(rc2_path)
    case3 = build_waveguide_governed_compiler_session_verification_case(rej_path)

    assert case1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert case2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert case3.rc_id == "SOL-WAVEGUIDE-RC1"

    assert case1.session_verification_status == "session_verified"
    assert case2.session_verification_status == "session_verified"
    assert case3.session_verification_status == "session_rejection_verified"


def test_session_case_digest_excludes_self_and_is_deterministic():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path)
    case_dict = case.__dict__.copy()
    case_dict["session_case_digest"] = "different_value"

    d1 = hash_waveguide_governed_compiler_session_verification_case(case)
    d2 = hash_waveguide_governed_compiler_session_verification_case(case_dict)
    assert d1 == d2


def test_successful_verifications():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    rc2_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_REJECTION_EXAMPLE.json"

    case1 = build_waveguide_governed_compiler_session_verification_case(rc1_path)
    case2 = build_waveguide_governed_compiler_session_verification_case(rc2_path)
    case3 = build_waveguide_governed_compiler_session_verification_case(rej_path)

    ok1, reasons1 = verify_waveguide_governed_compiler_session(case1)
    ok2, reasons2 = verify_waveguide_governed_compiler_session(case2)
    ok3, reasons3 = verify_waveguide_governed_compiler_session(case3)

    assert ok1 is True
    assert ok2 is True
    assert ok3 is True

    assert "SESSION_VERIFIER_REPORT_VERIFIED" in reasons1
    assert "SESSION_VERIFIER_REPORT_VERIFIED" in reasons2
    assert "SESSION_VERIFIER_REPORT_VERIFIED" in reasons3


def test_tampered_record_digest_fails():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    full_path = os.path.join(REPO_ROOT, rc1_path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Tamper with invocation record digest
    data["invocation_record_digest"] = "tampered"
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path, record_data=data)

    assert case.session_verification_status == "session_failed"
    assert "SESSION_VERIFIER_INVOCATION_DIGEST_INVALID" in case.reason_codes
    
    ok, reasons = verify_waveguide_governed_compiler_session(case)
    assert ok is False


def test_tampered_pass_plan_order_fails():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    full_path = os.path.join(REPO_ROOT, rc1_path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Change order sequence to mismatch pass plan
    data["requested_pass_sequence"] = ["different_pass"]
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path, record_data=data)

    assert case.session_verification_status == "session_failed"
    assert case.pass_plan_order_preserved is False


def test_missing_digests_fail():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    full_path = os.path.join(REPO_ROOT, rc1_path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Clear capability resolution digest
    data_no_cap = data.copy()
    data_no_cap["capability_resolution_digest"] = ""
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path, record_data=data_no_cap)
    assert case.session_verification_status == "session_failed"

    # Clear trace ledger digest
    data_no_ledger = data.copy()
    data_no_ledger["trace_ledger_digest"] = ""
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path, record_data=data_no_ledger)
    assert case.session_verification_status == "session_failed"


def test_tampered_output_digest_fails():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    full_path = os.path.join(REPO_ROOT, rc1_path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["final_output_payload_digest"] = "tampered"
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path, record_data=data)

    assert case.session_verification_status == "session_failed"
    assert "SESSION_VERIFIER_FINAL_OUTPUT_DIGEST_MISMATCH" in case.reason_codes


def test_count_mismatch_fails():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    full_path = os.path.join(REPO_ROOT, rc1_path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["executed_pass_count"] = 5
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path, record_data=data)

    assert case.session_verification_status == "session_failed"


def test_forbidden_parameters_fail():
    rc1_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json"
    full_path = os.path.join(REPO_ROOT, rc1_path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Clear strict waveguide
    data["strict_waveguide_required"] = False
    case = build_waveguide_governed_compiler_session_verification_case(rc1_path, record_data=data)
    assert case.session_verification_status == "session_failed"


def test_report_builder_and_validation():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER_REPORT.json")
    assert os.path.exists(report_path)

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    ok, reasons = validate_waveguide_governed_compiler_session_verification_report(report)
    assert ok is True
    assert "SESSION_VERIFIER_REPORT_DIGEST_VALID" in reasons
    assert "SESSION_VERIFIER_REPORT_VERIFIED" in reasons

    assert report["verified_session_count"] == 2
    assert report["verified_rejection_session_count"] == 1
    assert report["failed_session_count"] == 0
    assert report["blocked_session_count"] == 0
    assert report["rc1_session_count"] == 2
    assert report["rc2_session_count"] == 1


def test_report_digest_excludes_self_and_is_deterministic():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER_REPORT.json")
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    report_dict = report.copy()
    report_dict["session_verification_report_digest"] = "different_value"

    d1 = hash_waveguide_governed_compiler_session_verification_report(report)
    d2 = hash_waveguide_governed_compiler_session_verification_report(report_dict)
    assert d1 == d2


def test_summary_and_export():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER_REPORT.json")
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    summary = summarize_waveguide_governed_compiler_session_verification_report(report)
    assert "SOL WAVEGUIDE GOVERNED COMPILER SESSION VERIFIER" in summary

    temp_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER_REPORT_TEMP.json"
    full_temp = os.path.join(REPO_ROOT, temp_path)
    export_waveguide_governed_compiler_session_verification_report(report, full_temp)

    assert os.path.exists(full_temp)
    with open(full_temp, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["session_verification_report_digest"] == report["session_verification_report_digest"]
    os.remove(full_temp)


def test_artifacts_exist():
    rep_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER_REPORT.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER.md")

    assert os.path.exists(rep_path)
    assert os.path.exists(doc_path)
