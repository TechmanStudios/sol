# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Compiler Pass Admission Controller
"""

import os
import json
import pytest

from sol_waveguide_compiler_pass_admission import (
    build_waveguide_pass_admission_request,
    evaluate_waveguide_pass_admission,
    validate_waveguide_pass_admission_decision,
    summarize_waveguide_pass_admission_decision,
    export_waveguide_pass_admission_decision,
    compare_waveguide_pass_admission_decisions,
    hash_waveguide_pass_admission_request,
    hash_waveguide_pass_admission_decision
)
from sol_waveguide_rc_promotion_ledger import REPO_ROOT


def test_admission_request_build():
    req1 = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    req2 = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC2", "cost_model_evaluation")

    assert req1 is not None
    assert req2 is not None
    assert req1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert req2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert req1.requested_pass == "pipeline_compaction"
    assert req2.requested_pass == "cost_model_evaluation"


def test_request_digest_excludes_self():
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    req_dict = req.__dict__.copy()
    req_dict["request_digest"] = "different_digest_value"

    h1 = hash_waveguide_pass_admission_request(req)
    h2 = hash_waveguide_pass_admission_request(req_dict)
    assert h1 == h2


def test_decision_digest_excludes_self():
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    dec = evaluate_waveguide_pass_admission(req)
    dec_dict = dec.__dict__.copy()
    dec_dict["decision_digest"] = "different_decision_digest_value"

    h1 = hash_waveguide_pass_admission_decision(dec)
    h2 = hash_waveguide_pass_admission_decision(dec_dict)
    assert h1 == h2


def test_rc1_admits_foundation_pass():
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    dec = evaluate_waveguide_pass_admission(req)
    assert dec.admission_status == "pass_admitted"
    assert dec.pass_allowed is True


def test_rc2_admits_foundation_pass():
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC2", "pipeline_compaction")
    dec = evaluate_waveguide_pass_admission(req)
    assert dec.admission_status == "pass_admitted"
    assert dec.pass_allowed is True


def test_rc1_blocks_governed_passes():
    for blocked_pass in ("channel_kernel_recognition", "cost_model_evaluation", "deterministic_policy_selection"):
        req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", blocked_pass)
        dec = evaluate_waveguide_pass_admission(req)
        assert dec.admission_status == "pass_blocked"
        assert dec.pass_allowed is False
        assert "PASS_ADMISSION_RC1_GOVERNED_PASS_FORBIDDEN" in dec.reason_codes


def test_rc2_admits_governed_passes():
    for admitted_pass in ("channel_kernel_recognition", "cost_model_evaluation", "deterministic_policy_selection"):
        req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC2", admitted_pass)
        dec = evaluate_waveguide_pass_admission(req)
        assert dec.admission_status == "pass_admitted"
        assert dec.pass_allowed is True
        assert "PASS_ADMISSION_RC2_GOVERNED_PASS_ALLOWED" in dec.reason_codes


def test_rc1_blocks_governed_profiles():
    for blocked_profile in ("COST_MODEL_DEBUG", "AUTOTUNE_SAFE", "AUTOTUNE_LOWEST_CYCLES", "KERNEL_AUTOTUNE_SAFE"):
        req = build_waveguide_pass_admission_request(
            rc_id="SOL-WAVEGUIDE-RC1",
            requested_pass="pipeline_compaction",
            requested_profile=blocked_profile
        )
        dec = evaluate_waveguide_pass_admission(req)
        assert dec.admission_status == "pass_blocked"
        assert dec.profile_allowed is False
        assert "PASS_ADMISSION_RC1_GOVERNED_PROFILE_FORBIDDEN" in dec.reason_codes


def test_rc2_admits_governed_profiles():
    for admitted_profile in ("COST_MODEL_DEBUG", "AUTOTUNE_SAFE", "AUTOTUNE_LOWEST_CYCLES", "KERNEL_AUTOTUNE_SAFE"):
        req = build_waveguide_pass_admission_request(
            rc_id="SOL-WAVEGUIDE-RC2",
            requested_pass="pipeline_compaction",
            requested_profile=admitted_profile
        )
        dec = evaluate_waveguide_pass_admission(req)
        assert dec.admission_status == "pass_admitted"
        assert dec.profile_allowed is True
        assert "PASS_ADMISSION_RC2_GOVERNED_PROFILE_ALLOWED" in dec.reason_codes


def test_safety_violations_blocked():
    # 1. LaneFabric Fallback
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction", lane_fabric_fallback_requested=True)
    dec = evaluate_waveguide_pass_admission(req)
    assert dec.admission_status == "pass_blocked"
    assert "PASS_ADMISSION_LANEFABRIC_FALLBACK_FORBIDDEN" in dec.reason_codes

    # 2. Hybrid Execution
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction", hybrid_execution_requested=True)
    dec = evaluate_waveguide_pass_admission(req)
    assert dec.admission_status == "pass_blocked"
    assert "PASS_ADMISSION_HYBRID_EXECUTION_FORBIDDEN" in dec.reason_codes

    # 3. Production Mutation
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction", production_mutation_requested=True)
    dec = evaluate_waveguide_pass_admission(req)
    assert dec.admission_status == "pass_blocked"
    assert "PASS_ADMISSION_PRODUCTION_MUTATION_FORBIDDEN" in dec.reason_codes

    # 4. Strict Waveguide Disabled
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction", strict_waveguide_required=False)
    dec = evaluate_waveguide_pass_admission(req)
    assert dec.admission_status == "pass_blocked"


def test_invalid_capability_resolution_blocks():
    # Pass an invalid capability resolution dictionary
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    invalid_resolution = {
        "resolution_id": "SOL-WAVEGUIDE-RUNTIME-CAPABILITY-RESOLUTION-RC1",
        "rc_id": "SOL-WAVEGUIDE-RC1",
        "capability_status": "capability_blocked",
        "resolution_digest": "invalid_digest"
    }
    dec = evaluate_waveguide_pass_admission(req, capability_resolution=invalid_resolution)
    assert dec.admission_status == "pass_blocked"
    assert "PASS_ADMISSION_CAPABILITY_RESOLUTION_INVALID" in dec.reason_codes


def test_rc_mismatch_blocks():
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC2", "pipeline_compaction")
    # Resolve against RC1 capability record
    capability_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    with open(capability_path, "r", encoding="utf-8") as f:
        res = json.load(f)
    dec = evaluate_waveguide_pass_admission(req, capability_resolution=res)
    assert dec.admission_status == "pass_blocked"
    assert "PASS_ADMISSION_RC_MISMATCH" in dec.reason_codes


def test_missing_software_caveat_blocks():
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    capability_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    with open(capability_path, "r", encoding="utf-8") as f:
        res = json.load(f)
    # Clear software caveat
    res["software_validation_caveat"] = ""
    dec = evaluate_waveguide_pass_admission(req, capability_resolution=res)
    assert dec.admission_status == "pass_blocked"


def test_decision_validation():
    # Valid RC1 decision
    req1 = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    dec1 = evaluate_waveguide_pass_admission(req1)
    ok1, reasons1 = validate_waveguide_pass_admission_decision(dec1)
    assert ok1 is True
    assert "PASS_ADMISSION_DECISION_DIGEST_VALID" in reasons1

    # Valid RC2 decision
    req2 = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC2", "cost_model_evaluation")
    dec2 = evaluate_waveguide_pass_admission(req2)
    ok2, reasons2 = validate_waveguide_pass_admission_decision(dec2)
    assert ok2 is True
    assert "PASS_ADMISSION_DECISION_DIGEST_VALID" in reasons2

    # Blocked decision validation
    req3 = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "cost_model_evaluation")
    dec3 = evaluate_waveguide_pass_admission(req3)
    ok3, reasons3 = validate_waveguide_pass_admission_decision(dec3)
    assert ok3 is False
    assert "PASS_ADMISSION_BLOCKED" in reasons3


def test_summarize_and_compare_are_deterministic():
    req = build_waveguide_pass_admission_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    dec1 = evaluate_waveguide_pass_admission(req)
    dec2 = evaluate_waveguide_pass_admission(req)

    s1 = summarize_waveguide_pass_admission_decision(dec1)
    s2 = summarize_waveguide_pass_admission_decision(dec2)
    assert s1 == s2

    diff = compare_waveguide_pass_admission_decisions(dec1, dec2)
    assert len(diff) == 0


def test_artifacts_and_documentation_exist():
    rc1_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC1.json")
    rc2_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC2.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION.md")

    assert os.path.exists(rc1_json)
    assert os.path.exists(rc2_json)
    assert os.path.exists(doc_path)
