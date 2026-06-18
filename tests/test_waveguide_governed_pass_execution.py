# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Governed Pass Execution Harness
"""

import os
import json
import pytest

from sol_waveguide_governed_pass_execution import (
    build_waveguide_governed_pass_execution_request,
    execute_waveguide_governed_pass,
    validate_waveguide_governed_pass_execution_record,
    summarize_waveguide_governed_pass_execution_record,
    export_waveguide_governed_pass_execution_record,
    compare_waveguide_governed_pass_execution_records,
    hash_waveguide_governed_pass_execution_request,
    hash_waveguide_governed_pass_execution_record,
    build_waveguide_governed_pass_handler_registry
)
from sol_waveguide_compiler_pass_admission import (
    build_waveguide_pass_admission_request,
    evaluate_waveguide_pass_admission
)
from sol_waveguide_rc_promotion_ledger import REPO_ROOT


def test_execution_request_build():
    req1 = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        requested_pass="pipeline_compaction",
        requested_profile="FULL_SAFE_OPTIMIZED"
    )
    req2 = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC2",
        requested_pass="cost_model_evaluation",
        requested_profile="COST_MODEL_DEBUG"
    )

    assert req1 is not None
    assert req2 is not None
    assert req1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert req2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert req1.requested_pass == "pipeline_compaction"
    assert req2.requested_pass == "cost_model_evaluation"


def test_request_digest_excludes_self():
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    req_dict = req.__dict__.copy()
    req_dict["execution_request_digest"] = "different_digest_value"

    h1 = hash_waveguide_governed_pass_execution_request(req)
    h2 = hash_waveguide_governed_pass_execution_request(req_dict)
    assert h1 == h2


def test_record_digest_excludes_self():
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    rec = execute_waveguide_governed_pass(req)
    rec_dict = rec.__dict__.copy()
    rec_dict["execution_record_digest"] = "different_record_digest_value"

    h1 = hash_waveguide_governed_pass_execution_record(rec)
    h2 = hash_waveguide_governed_pass_execution_record(rec_dict)
    assert h1 == h2


def test_registry_is_deterministic():
    r1 = build_waveguide_governed_pass_handler_registry()
    r2 = build_waveguide_governed_pass_handler_registry()

    assert r1.keys() == r2.keys()
    for key in r1:
        assert r1[key]["handler_id"] == r2[key]["handler_id"]
        assert r1[key]["handler_version"] == r2[key]["handler_version"]


def test_rc1_executes_foundation_pass():
    payload = {"input_size": 100}
    req = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        requested_pass="pipeline_compaction",
        requested_profile="FULL_SAFE_OPTIMIZED",
        input_payload=payload
    )
    rec = execute_waveguide_governed_pass(req, input_payload=payload)
    assert rec.execution_status == "pass_executed"
    assert rec.pass_executed is True
    assert rec.pass_rejected is False
    assert "PASS_EXECUTION_PASS_EXECUTED" in rec.reason_codes
    assert rec.output_payload_digest != ""


def test_rc2_executes_governed_passes():
    passes = ("cost_model_evaluation", "channel_kernel_recognition", "deterministic_policy_selection")
    for pass_name in passes:
        payload = {"kernels": ["add"]} if pass_name == "channel_kernel_recognition" else {"cycles": 100}
        
        req_admission = build_waveguide_pass_admission_request(
            rc_id="SOL-WAVEGUIDE-RC2",
            requested_pass=pass_name,
            requested_profile="COST_MODEL_DEBUG" if pass_name == "cost_model_evaluation" else None
        )
        dec_admission = evaluate_waveguide_pass_admission(req_admission)

        req = build_waveguide_governed_pass_execution_request(
            rc_id="SOL-WAVEGUIDE-RC2",
            requested_pass=pass_name,
            requested_profile="COST_MODEL_DEBUG" if pass_name == "cost_model_evaluation" else None,
            input_payload=payload,
            admission_decision_digest=dec_admission.decision_digest,
            admission_status=dec_admission.admission_status
        )
        rec = execute_waveguide_governed_pass(req, admission_decision=dec_admission, input_payload=payload)
        assert rec.execution_status == "pass_executed"
        assert rec.pass_executed is True
        assert rec.pass_rejected is False
        assert "PASS_EXECUTION_PASS_EXECUTED" in rec.reason_codes


def test_rc1_rejects_governed_passes():
    passes = ("cost_model_evaluation", "channel_kernel_recognition", "deterministic_policy_selection")
    for pass_name in passes:
        req = build_waveguide_governed_pass_execution_request(
            rc_id="SOL-WAVEGUIDE-RC1",
            requested_pass=pass_name,
            requested_profile="COST_MODEL_DEBUG" if pass_name == "cost_model_evaluation" else None
        )
        rec = execute_waveguide_governed_pass(req, input_payload={"cycles": 100})
        assert rec.execution_status == "pass_rejected"
        assert rec.pass_executed is False
        assert rec.pass_rejected is True
        assert "PASS_EXECUTION_PASS_REJECTED" in rec.reason_codes


def test_blocked_or_invalid_admission_blocks():
    # 1. Blocked decision status
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    invalid_decision = {
        "admission_status": "pass_blocked",
        "rc_id": "SOL-WAVEGUIDE-RC1",
        "requested_pass": "pipeline_compaction",
        "decision_digest": "dummy",
        "strict_waveguide_required": True,
        "lane_fabric_fallback_allowed": False,
        "hybrid_execution_allowed": False,
        "production_mutation_allowed": False,
        "software_validation_caveat": "sandbox validation context"
    }
    rec = execute_waveguide_governed_pass(req, admission_decision=invalid_decision)
    assert rec.execution_status == "pass_rejected"

    # 2. RC Mismatch
    invalid_decision["admission_status"] = "pass_admitted"
    invalid_decision["rc_id"] = "SOL-WAVEGUIDE-RC2"
    rec = execute_waveguide_governed_pass(req, admission_decision=invalid_decision)
    assert rec.execution_status == "pass_rejected"

    # 3. Pass Mismatch
    invalid_decision["rc_id"] = "SOL-WAVEGUIDE-RC1"
    invalid_decision["requested_pass"] = "cost_model_evaluation"
    rec = execute_waveguide_governed_pass(req, admission_decision=invalid_decision)
    assert rec.execution_status == "pass_rejected"

    # 4. Profile Mismatch
    invalid_decision["requested_pass"] = "pipeline_compaction"
    invalid_decision["requested_profile"] = "UNEXPECTED_PROFILE"
    rec = execute_waveguide_governed_pass(req, admission_decision=invalid_decision)
    assert rec.execution_status == "pass_rejected"


def test_missing_handler_blocks():
    # Attempt to execute a pass that does not exist in registry
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "non_existent_pass")
    decision = {
        "admission_status": "pass_admitted",
        "rc_id": "SOL-WAVEGUIDE-RC1",
        "requested_pass": "non_existent_pass",
        "decision_digest": "dummy",
        "strict_waveguide_required": True,
        "lane_fabric_fallback_allowed": False,
        "hybrid_execution_allowed": False,
        "production_mutation_allowed": False,
        "software_validation_caveat": "sandbox validation context"
    }
    rec = execute_waveguide_governed_pass(req, admission_decision=decision)
    assert rec.execution_status == "pass_rejected"
    assert "PASS_EXECUTION_HANDLER_MISSING" in rec.reason_codes


def test_safety_violations_block_execution():
    # 1. Fallback allowed
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction", lane_fabric_fallback_allowed=True)
    rec = execute_waveguide_governed_pass(req)
    assert rec.execution_status == "pass_rejected"
    assert "PASS_EXECUTION_LANEFABRIC_FALLBACK_FORBIDDEN" in rec.reason_codes

    # 2. Hybrid execution allowed
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction", hybrid_execution_allowed=True)
    rec = execute_waveguide_governed_pass(req)
    assert rec.execution_status == "pass_rejected"
    assert "PASS_EXECUTION_HYBRID_EXECUTION_FORBIDDEN" in rec.reason_codes

    # 3. Production mutation allowed
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction", production_mutation_allowed=True)
    rec = execute_waveguide_governed_pass(req)
    assert rec.execution_status == "pass_rejected"
    assert "PASS_EXECUTION_PRODUCTION_MUTATION_FORBIDDEN" in rec.reason_codes


def test_missing_software_caveat_blocks_execution():
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    decision = {
        "admission_status": "pass_admitted",
        "rc_id": "SOL-WAVEGUIDE-RC1",
        "requested_pass": "pipeline_compaction",
        "decision_digest": "dummy",
        "strict_waveguide_required": True,
        "lane_fabric_fallback_allowed": False,
        "hybrid_execution_allowed": False,
        "production_mutation_allowed": False,
        "software_validation_caveat": "" # Empty caveat
    }
    rec = execute_waveguide_governed_pass(req, admission_decision=decision)
    assert rec.execution_status == "pass_rejected"


def test_payload_transform_and_digests_are_deterministic():
    req = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        requested_pass="pipeline_compaction",
        input_payload={"input_size": 100}
    )
    rec1 = execute_waveguide_governed_pass(req, input_payload={"input_size": 100})
    rec2 = execute_waveguide_governed_pass(req, input_payload={"input_size": 100})

    assert rec1.input_payload_digest == rec2.input_payload_digest
    assert rec1.output_payload_digest == rec2.output_payload_digest
    assert rec1.execution_record_digest == rec2.execution_record_digest


def test_record_validation():
    # Admitted/Executed record
    req1 = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        requested_pass="pipeline_compaction",
        requested_profile="FULL_SAFE_OPTIMIZED"
    )
    rec1 = execute_waveguide_governed_pass(req1)
    ok1, reasons1 = validate_waveguide_governed_pass_execution_record(rec1)
    assert ok1 is True
    assert "PASS_EXECUTION_RECORD_DIGEST_VALID" in reasons1

    # Rejected record
    req2 = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "cost_model_evaluation")
    rec2 = execute_waveguide_governed_pass(req2)
    ok2, reasons2 = validate_waveguide_governed_pass_execution_record(rec2)
    assert ok2 is False
    assert "PASS_EXECUTION_PASS_REJECTED" in reasons2


def test_summarize_and_compare_are_deterministic():
    req = build_waveguide_governed_pass_execution_request("SOL-WAVEGUIDE-RC1", "pipeline_compaction")
    rec1 = execute_waveguide_governed_pass(req)
    rec2 = execute_waveguide_governed_pass(req)

    s1 = summarize_waveguide_governed_pass_execution_record(rec1)
    s2 = summarize_waveguide_governed_pass_execution_record(rec2)
    assert s1 == s2

    diff = compare_waveguide_governed_pass_execution_records(rec1, rec2)
    assert len(diff) == 0


def test_artifacts_exist_on_disk():
    rc1_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json")
    rc2_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json")
    rej_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION.md")

    assert os.path.exists(rc1_json)
    assert os.path.exists(rc2_json)
    assert os.path.exists(rej_json)
    assert os.path.exists(doc_path)
