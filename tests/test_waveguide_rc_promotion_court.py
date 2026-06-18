# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Court-Supervised Promotion Flow
"""

import os
import json
import pytest
from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_promotion_ledger import build_waveguide_rc_promotion_record
from sol_waveguide_rc_promotion_court import (
    build_waveguide_rc_promotion_case,
    validate_waveguide_rc_promotion_case,
    build_waveguide_rc_court_panel,
    evaluate_waveguide_rc_ranger_attestation,
    build_waveguide_rc_court_verdict,
    hash_waveguide_rc_promotion_case,
    hash_waveguide_rc_court_verdict,
    summarize_waveguide_rc_court_verdict,
    export_waveguide_rc_court_verdict,
    compare_waveguide_rc_court_verdicts,
    RangerAttestation
)


def test_promotion_case_and_verdict_build():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)

    case = build_waveguide_rc_promotion_case(rec)
    panel = build_waveguide_rc_court_panel(rec)
    verdict = build_waveguide_rc_court_verdict(case, panel)

    assert case is not None
    assert verdict is not None
    assert case.candidate_level == "RC1"
    assert verdict.court_verdict == "promotion_approved"


def test_case_and_verdict_digests_exclude_self():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)

    case = build_waveguide_rc_promotion_case(rec)
    case_dict = case.__dict__.copy()
    case_dict["case_digest"] = "ignored_case_digest_value"

    h_c1 = hash_waveguide_rc_promotion_case(case)
    h_c2 = hash_waveguide_rc_promotion_case(case_dict)
    assert h_c1 == h_c2

    panel = build_waveguide_rc_court_panel(rec)
    verdict = build_waveguide_rc_court_verdict(case, panel)
    verdict_dict = verdict.__dict__.copy()
    verdict_dict["verdict_digest"] = "ignored_verdict_digest_value"

    h_v1 = hash_waveguide_rc_court_verdict(verdict)
    h_v2 = hash_waveguide_rc_court_verdict(verdict_dict)
    assert h_v1 == h_v2


def test_ranger_panel_is_approved_for_clean_manifests():
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    rec = build_waveguide_rc_promotion_record(rc2)
    panel = build_waveguide_rc_court_panel(rec)

    for att in panel:
        assert att.status == "approved"
        assert "RC_COURT_RANGER_APPROVED" in att.reason_codes


def test_blocked_promotion_record_produces_rejected_verdict():
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    rc2["canonical_pass_order"].remove("cost_model_evaluation")
    rec = build_waveguide_rc_promotion_record(rc2)

    case = build_waveguide_rc_promotion_case(rec)
    panel = build_waveguide_rc_court_panel(rec)
    verdict = build_waveguide_rc_court_verdict(case, panel)

    assert verdict.court_verdict == "promotion_rejected"
    assert "RC_COURT_RANGER_REJECTED" in verdict.reason_codes


def test_missing_required_ranger_produces_quorum_failure():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)

    case = build_waveguide_rc_promotion_case(rec)
    panel = build_waveguide_rc_court_panel(rec)
    panel = [att for att in panel if att.ranger_id != "ReleaseGateRanger"]

    verdict = build_waveguide_rc_court_verdict(case, panel)
    assert verdict.court_verdict == "promotion_rejected"
    assert verdict.quorum_status == "quorum_failed"
    assert "RC_COURT_QUORUM_FAILED" in verdict.reason_codes


def test_rejected_ranger_produces_rejected_verdict():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)

    case = build_waveguide_rc_promotion_case(rec)
    panel = build_waveguide_rc_court_panel(rec)

    for i, att in enumerate(panel):
        if att.ranger_id == "RegressionAuditRanger":
            panel[i] = RangerAttestation(
                attestation_id=att.attestation_id,
                ranger_id=att.ranger_id,
                scope=att.scope,
                status="rejected",
                reason_codes=["RC_COURT_RANGER_REJECTED"],
                notes=["Mocked failure"],
                input_digest=att.input_digest
            )

    verdict = build_waveguide_rc_court_verdict(case, panel)
    assert verdict.court_verdict == "promotion_rejected"
    assert "RC_COURT_RANGER_REJECTED" in verdict.reason_codes


def test_case_validation_works_on_clean_cases():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)
    case = build_waveguide_rc_promotion_case(rec)

    ok, reasons = validate_waveguide_rc_promotion_case(case)
    assert ok is True
    assert "RC_COURT_CASE_CANONICAL" in reasons
    assert "RC_COURT_PROMOTION_RECORD_VALID" in reasons


def test_verdict_summary_and_compare_are_deterministic():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)
    case = build_waveguide_rc_promotion_case(rec)
    panel = build_waveguide_rc_court_panel(rec)
    verdict1 = build_waveguide_rc_court_verdict(case, panel)
    verdict2 = build_waveguide_rc_court_verdict(case, panel)

    s1 = summarize_waveguide_rc_court_verdict(verdict1)
    s2 = summarize_waveguide_rc_court_verdict(verdict2)
    assert s1 == s2

    diff = compare_waveguide_rc_court_verdicts(verdict1, verdict2)
    assert len(diff) == 0


def test_json_verdicts_exist_on_disk():
    from sol_waveguide_rc_promotion_court import REPO_ROOT

    rc1_verdict_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_COURT_VERDICT_RC1.json")
    rc2_verdict_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_COURT_VERDICT_RC2.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_PROMOTION_COURT.md")

    assert os.path.exists(rc1_verdict_json)
    assert os.path.exists(rc2_verdict_json)
    assert os.path.exists(doc_path)
