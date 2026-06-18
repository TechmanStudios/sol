# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Governed Compiler Invocation Envelope
"""

import os
import json
import pytest

from sol_waveguide_governed_compiler_invocation import (
    build_waveguide_governed_compiler_invocation_request,
    execute_waveguide_governed_compiler_invocation,
    validate_waveguide_governed_compiler_invocation_record,
    summarize_waveguide_governed_compiler_invocation_record,
    export_waveguide_governed_compiler_invocation_record,
    compare_waveguide_governed_compiler_invocation_records,
    hash_waveguide_governed_compiler_invocation_request,
    hash_waveguide_governed_compiler_invocation_record,
    build_waveguide_invocation_pass_plan,
    KNOWN_PAYLOADS
)
from sol_waveguide_rc_promotion_ledger import REPO_ROOT


def test_invocation_requests_can_be_built():
    req1 = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"]
    )
    req2 = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC2",
        compiler_profile="COST_MODEL_DEBUG",
        requested_pass_sequence=["pipeline_compaction", "cost_model_evaluation"]
    )

    assert req1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert req2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert req1.invocation_request_id == "SOL-WAVEGUIDE-COMPILER-INVOCATION-REQUEST-RC1"
    assert req2.invocation_request_id == "SOL-WAVEGUIDE-COMPILER-INVOCATION-REQUEST-RC2"


def test_request_digest_excludes_self_and_is_deterministic():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"]
    )
    req_dict = req.__dict__.copy()
    req_dict["invocation_request_digest"] = "different_value"

    d1 = hash_waveguide_governed_compiler_invocation_request(req)
    d2 = hash_waveguide_governed_compiler_invocation_request(req_dict)
    assert d1 == d2


def test_pass_plan_order_preservation():
    rc1_seq = ["pipeline_compaction"]
    rc2_seq = ["pipeline_compaction", "cost_model_evaluation", "deterministic_policy_selection"]

    plan1 = build_waveguide_invocation_pass_plan("SOL-WAVEGUIDE-RC1", "FULL_SAFE_OPTIMIZED", rc1_seq)
    plan2 = build_waveguide_invocation_pass_plan("SOL-WAVEGUIDE-RC2", "COST_MODEL_DEBUG", rc2_seq)

    assert [item.requested_pass for item in plan1] == rc1_seq
    assert [item.requested_pass for item in plan2] == rc2_seq

    assert [item.pass_index for item in plan1] == [0]
    assert [item.pass_index for item in plan2] == [0, 1, 2]


def test_rc1_invocation_executes_compaction():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        input_payload={"input_size": 100}
    )
    rec = execute_waveguide_governed_compiler_invocation(req, input_payload={"input_size": 100})

    assert rec.invocation_status == "invocation_verified"
    assert rec.executed_pass_count == 1
    assert rec.rejected_pass_count == 0
    assert rec.verified_execution_count == 1
    assert rec.verified_rejection_count == 0
    assert rec.failed_replay_count == 0
    assert "SOL-PASS-HANDLER-PIPELINE-COMPACTION-V1" in rec.handler_ids_used

    ok, reasons = validate_waveguide_governed_compiler_invocation_record(rec)
    assert ok is True
    assert "COMPILER_INVOCATION_VERIFIED" in reasons


def test_rc2_invocation_executes_governed_passes():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC2",
        compiler_profile="COST_MODEL_DEBUG",
        requested_pass_sequence=["pipeline_compaction", "cost_model_evaluation", "deterministic_policy_selection"],
        input_payload={"cycles": 200}
    )
    rec = execute_waveguide_governed_compiler_invocation(req, input_payload={"cycles": 200})

    assert rec.invocation_status == "invocation_verified"
    assert rec.executed_pass_count == 3
    assert rec.rejected_pass_count == 0
    assert rec.verified_execution_count == 3
    assert rec.verified_rejection_count == 0
    assert rec.failed_replay_count == 0
    assert "SOL-PASS-HANDLER-COST-MODEL-EVALUATION-V1" in rec.handler_ids_used
    assert "SOL-PASS-HANDLER-DETERMINISTIC-POLICY-SELECTION-V1" in rec.handler_ids_used

    ok, reasons = validate_waveguide_governed_compiler_invocation_record(rec)
    assert ok is True


def test_rc1_governed_pass_rejection():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="COST_MODEL_DEBUG",
        requested_pass_sequence=["cost_model_evaluation"],
        input_payload={"cycles": 200}
    )
    rec = execute_waveguide_governed_compiler_invocation(req, input_payload={"cycles": 200})

    assert rec.invocation_status == "invocation_rejected_verified"
    assert rec.executed_pass_count == 0
    assert rec.rejected_pass_count == 1
    assert rec.verified_execution_count == 0
    assert rec.verified_rejection_count == 1
    assert rec.failed_replay_count == 0

    ok, reasons = validate_waveguide_governed_compiler_invocation_record(rec)
    assert ok is True
    assert "COMPILER_INVOCATION_REJECTIONS_VERIFIED" in reasons


def test_forbidden_parameters_block_invocation():
    # 1. LaneFabric fallback requested
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        lane_fabric_fallback_requested=True
    )
    rec = execute_waveguide_governed_compiler_invocation(req)
    assert rec.invocation_status == "invocation_blocked"
    assert "COMPILER_INVOCATION_LANEFABRIC_FALLBACK_FORBIDDEN" in rec.reason_codes

    # 2. Hybrid execution requested
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        hybrid_execution_requested=True
    )
    rec = execute_waveguide_governed_compiler_invocation(req)
    assert rec.invocation_status == "invocation_blocked"
    assert "COMPILER_INVOCATION_HYBRID_EXECUTION_FORBIDDEN" in rec.reason_codes

    # 3. Production mutation requested
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        production_mutation_requested=True
    )
    rec = execute_waveguide_governed_compiler_invocation(req)
    assert rec.invocation_status == "invocation_blocked"
    assert "COMPILER_INVOCATION_PRODUCTION_MUTATION_FORBIDDEN" in rec.reason_codes


def test_missing_software_caveat_fails():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        software_validation_caveat_required=False
    )
    rec = execute_waveguide_governed_compiler_invocation(req)
    assert rec.invocation_status == "invocation_failed"


def test_invalid_capability_resolution_fails():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"]
    )
    # Tamper resolution digest
    req.capability_resolution_digest = "tampered"
    
    rec = execute_waveguide_governed_compiler_invocation(req)
    assert rec.invocation_status == "invocation_blocked"


def test_invocation_record_digest_excludes_self_and_is_deterministic():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        input_payload={"input_size": 100}
    )
    rec = execute_waveguide_governed_compiler_invocation(req, input_payload={"input_size": 100})
    rec_dict = rec.__dict__.copy()
    rec_dict["invocation_record_digest"] = "different_value"

    d1 = hash_waveguide_governed_compiler_invocation_record(rec)
    d2 = hash_waveguide_governed_compiler_invocation_record(rec_dict)
    assert d1 == d2


def test_summary_and_export():
    req = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        input_payload={"input_size": 100}
    )
    rec = execute_waveguide_governed_compiler_invocation(req, input_payload={"input_size": 100})

    summary = summarize_waveguide_governed_compiler_invocation_record(rec)
    assert "SOL WAVEGUIDE GOVERNED COMPILER INVOCATION SUMMARY" in summary

    temp_path = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_TEMP.json"
    full_temp = os.path.join(REPO_ROOT, temp_path)
    export_waveguide_governed_compiler_invocation_record(rec, full_temp)

    assert os.path.exists(full_temp)
    with open(full_temp, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["invocation_record_digest"] == rec.invocation_record_digest
    os.remove(full_temp)


def test_artifacts_exist():
    rc1_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json")
    rc2_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC2.json")
    rej_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_REJECTION_EXAMPLE.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION.md")

    assert os.path.exists(rc1_path)
    assert os.path.exists(rc2_path)
    assert os.path.exists(rej_path)
    assert os.path.exists(doc_path)
