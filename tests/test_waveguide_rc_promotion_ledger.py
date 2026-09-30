# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Signed RC Promotion Ledger
"""

import os
import json
import pytest
from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_release_gate import build_waveguide_rc_release_gate, build_waveguide_rc_delta_report
from sol_waveguide_rc_promotion_ledger import (
    build_waveguide_rc_promotion_record,
    hash_waveguide_rc_manifest,
    hash_waveguide_rc_audit_artifact,
    hash_waveguide_rc_promotion_record,
    validate_waveguide_rc_promotion_record,
    summarize_waveguide_rc_promotion_record,
    export_waveguide_rc_promotion_record,
    compare_waveguide_rc_promotion_records
)


def test_promotion_records_build_successfully():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")

    rec1 = build_waveguide_rc_promotion_record(rc1)
    rec2 = build_waveguide_rc_promotion_record(rc2)

    assert rec1 is not None
    assert rec2 is not None
    assert rec1.candidate_level == "RC1"
    assert rec2.candidate_level == "RC2"


def test_hashing_is_deterministic():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")

    h1 = hash_waveguide_rc_manifest(rc1)
    h2 = hash_waveguide_rc_manifest(rc1)
    assert h1 == h2


def test_record_digest_excludes_self():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)

    rec_dict = rec.__dict__.copy()
    rec_dict["record_digest"] = "different_digest_value_should_be_ignored"

    h1 = hash_waveguide_rc_promotion_record(rec)
    h2 = hash_waveguide_rc_promotion_record(rec_dict)
    assert h1 == h2


def test_clean_candidates_are_promotion_ready():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")

    rec1 = build_waveguide_rc_promotion_record(rc1)
    rec2 = build_waveguide_rc_promotion_record(rc2)

    assert rec1.promotion_status == "promotion_ready"
    assert rec2.promotion_status == "promotion_ready"


def test_blocked_release_gate_produces_blocked_promotion():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    # Inject leakage to cause blocked release gate
    rc1["optimization_profiles"].append("COST_MODEL_DEBUG")

    rec = build_waveguide_rc_promotion_record(rc1)
    assert rec.promotion_status == "promotion_blocked"
    assert "RC_PROMOTION_RELEASE_GATE_NOT_READY" in rec.promotion_reason_codes


def test_missing_docs_produce_blocked_promotion(monkeypatch):
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")

    # Mock os.path.exists to simulate missing files
    def mock_exists(path):
        if "SOL_WAVEGUIDE_RC1_MANIFEST.json" in path:
            return False
        return True

    monkeypatch.setattr(os.path, "exists", mock_exists)

    rec = build_waveguide_rc_promotion_record(rc1)
    assert rec.promotion_status == "promotion_blocked"
    assert "RC_PROMOTION_REQUIRED_DOC_MISSING" in rec.promotion_reason_codes


def test_validation_works_on_clean_records():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)

    ok, reasons = validate_waveguide_rc_promotion_record(rec)
    assert ok is True
    assert "RC_PROMOTION_RECORD_DIGEST_VALID" in reasons
    assert "RC_PROMOTION_MANIFEST_HASH_VALID" in reasons


def test_validation_catches_invalid_record_digest():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)
    rec.record_digest = "corrupted_digest"

    ok, reasons = validate_waveguide_rc_promotion_record(rec)
    assert ok is False
    assert "RC_PROMOTION_RECORD_DIGEST_INVALID" in reasons


def test_validation_catches_manifest_hash_mismatch():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec = build_waveguide_rc_promotion_record(rc1)
    rec.manifest_digest = "mismatched_manifest_digest"

    rec.record_digest = hash_waveguide_rc_promotion_record(rec)

    ok, reasons = validate_waveguide_rc_promotion_record(rec)
    assert ok is False
    assert "RC_PROMOTION_MANIFEST_HASH_MISMATCH" in reasons


def test_summary_and_compare_are_deterministic():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    rec2 = build_waveguide_rc_promotion_record(rc1)

    s1 = summarize_waveguide_rc_promotion_record(rec1)
    s2 = summarize_waveguide_rc_promotion_record(rec2)
    assert s1 == s2

    diff = compare_waveguide_rc_promotion_records(rec1, rec2)
    assert len(diff) == 0


def test_json_files_and_docs_exist_on_disk():
    from sol_waveguide_rc_promotion_ledger import REPO_ROOT

    rc1_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC1.json")
    rc2_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC2.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_PROMOTION_LEDGER.md")

    assert os.path.exists(rc1_json)
    assert os.path.exists(rc2_json)
    assert os.path.exists(doc_path)
