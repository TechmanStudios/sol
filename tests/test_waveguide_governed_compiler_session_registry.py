# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Governed Compiler Session Registry.
"""

import os
import json
import pytest

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_governed_compiler_session_registry import (
    WaveguideGovernedCompilerSessionRegistryEntry,
    WaveguideGovernedCompilerSessionRegistry,
    hash_waveguide_governed_compiler_session_registry_entry,
    hash_waveguide_governed_compiler_session_registry,
    build_waveguide_governed_compiler_session_registry_entry,
    validate_waveguide_governed_compiler_session_registry_entry,
    build_waveguide_governed_compiler_session_registry,
    validate_waveguide_governed_compiler_session_registry,
    summarize_waveguide_governed_compiler_session_registry,
    export_waveguide_governed_compiler_session_registry,
    compare_waveguide_governed_compiler_session_registries,
    index_waveguide_governed_compiler_sessions_by_status,
    index_waveguide_governed_compiler_sessions_by_rc,
    index_waveguide_governed_compiler_sessions_by_profile
)

REPORT_PATH = "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_VERIFIER_REPORT.json"

@pytest.fixture
def clean_report_data():
    full_path = os.path.join(REPO_ROOT, REPORT_PATH)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_registry_entry_can_be_built(clean_report_data):
    # RC1 verified session entry can be built
    case_rc1_ok = clean_report_data["cases"][0]
    entry_rc1 = build_waveguide_governed_compiler_session_registry_entry(case_rc1_ok)
    assert entry_rc1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert entry_rc1.session_verification_status == "session_registered"
    assert entry_rc1.compiler_profile == "FULL_SAFE_OPTIMIZED"

    # RC2 verified session entry can be built
    case_rc2_ok = clean_report_data["cases"][1]
    entry_rc2 = build_waveguide_governed_compiler_session_registry_entry(case_rc2_ok)
    assert entry_rc2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert entry_rc2.session_verification_status == "session_registered"
    assert entry_rc2.compiler_profile == "COST_MODEL_DEBUG"

    # RC1 rejection-verified session entry can be built
    case_rej_ok = clean_report_data["cases"][2]
    entry_rej = build_waveguide_governed_compiler_session_registry_entry(case_rej_ok)
    assert entry_rej.rc_id == "SOL-WAVEGUIDE-RC1"
    assert entry_rej.session_verification_status == "session_rejection_registered"
    assert entry_rej.compiler_profile == "COST_MODEL_DEBUG"

def test_entry_digest_is_deterministic_and_excludes_self(clean_report_data):
    case_rc1_ok = clean_report_data["cases"][0]
    entry = build_waveguide_governed_compiler_session_registry_entry(case_rc1_ok)
    
    # Registry entry digest is deterministic
    h1 = hash_waveguide_governed_compiler_session_registry_entry(entry)
    h2 = hash_waveguide_governed_compiler_session_registry_entry(entry)
    assert h1 == h2

    # registry_entry_digest is excluded from its own digest input
    entry_dict = entry.__dict__.copy()
    entry_dict["registry_entry_digest"] = "different_digest"
    h3 = hash_waveguide_governed_compiler_session_registry_entry(entry_dict)
    assert h1 == h3

def test_clean_entries_validate(clean_report_data):
    # RC1 verified session entry validates
    entry_rc1 = build_waveguide_governed_compiler_session_registry_entry(clean_report_data["cases"][0])
    ok_rc1, reasons_rc1 = validate_waveguide_governed_compiler_session_registry_entry(entry_rc1)
    assert ok_rc1 is True
    assert "SESSION_REGISTRY_ENTRY_DIGEST_VALID" in reasons_rc1

    # RC2 verified session entry validates
    entry_rc2 = build_waveguide_governed_compiler_session_registry_entry(clean_report_data["cases"][1])
    ok_rc2, reasons_rc2 = validate_waveguide_governed_compiler_session_registry_entry(entry_rc2)
    assert ok_rc2 is True

    # RC1 rejection-verified session entry validates
    entry_rej = build_waveguide_governed_compiler_session_registry_entry(clean_report_data["cases"][2])
    ok_rej, reasons_rej = validate_waveguide_governed_compiler_session_registry_entry(entry_rej)
    assert ok_rej is True

def test_missing_required_digests_fail_validation(clean_report_data):
    case = clean_report_data["cases"][0]
    
    # Missing invocation digest fails entry validation
    case_no_inv = case.copy()
    case_no_inv["invocation_record_digest"] = ""
    entry = build_waveguide_governed_compiler_session_registry_entry(case_no_inv)
    ok, _ = validate_waveguide_governed_compiler_session_registry_entry(entry)
    assert ok is False

    # Missing session case digest fails entry validation
    case_no_case = case.copy()
    case_no_case["session_case_digest"] = ""
    entry = build_waveguide_governed_compiler_session_registry_entry(case_no_case)
    ok, _ = validate_waveguide_governed_compiler_session_registry_entry(entry)
    assert ok is False

    # Missing trace ledger digest fails entry validation
    case_no_trace = case.copy()
    case_no_trace["trace_ledger_digest"] = ""
    entry = build_waveguide_governed_compiler_session_registry_entry(case_no_trace)
    ok, _ = validate_waveguide_governed_compiler_session_registry_entry(entry)
    assert ok is False

    # Missing replay report digest fails entry validation
    case_no_replay = case.copy()
    case_no_replay["replay_report_digest"] = ""
    entry = build_waveguide_governed_compiler_session_registry_entry(case_no_replay)
    ok, _ = validate_waveguide_governed_compiler_session_registry_entry(entry)
    assert ok is False

    # Missing final output payload digest fails entry validation
    case_no_output = case.copy()
    case_no_output["recorded_final_output_payload_digest"] = ""
    entry = build_waveguide_governed_compiler_session_registry_entry(case_no_output)
    ok, _ = validate_waveguide_governed_compiler_session_registry_entry(entry)
    assert ok is False

    # Missing software caveat fails entry validation
    case_no_caveat = case.copy()
    case_no_caveat["software_validation_caveat"] = ""
    entry = build_waveguide_governed_compiler_session_registry_entry(case_no_caveat)
    ok, _ = validate_waveguide_governed_compiler_session_registry_entry(entry)
    assert ok is False

def test_top_level_registry_lifecycle(clean_report_data):
    # Top-level registry can be built from all clean session cases
    registry = build_waveguide_governed_compiler_session_registry(REPORT_PATH, report_data=clean_report_data)
    assert registry.registry_id == "SOL-WAVEGUIDE-GOVERNED-COMPILER-SESSION-REGISTRY"
    assert registry.registry_status == "session_registry_valid"

    # Top-level registry validates
    ok, reasons = validate_waveguide_governed_compiler_session_registry(registry)
    assert ok is True
    assert "SESSION_REGISTRY_DIGEST_VALID" in reasons
    assert "SESSION_REGISTRY_VALID" in reasons

    # Registry digest is deterministic and registry_digest is excluded from its own digest input
    h1 = hash_waveguide_governed_compiler_session_registry(registry)
    h2 = hash_waveguide_governed_compiler_session_registry(registry)
    assert h1 == h2

    reg_dict = registry.__dict__.copy()
    reg_dict["registry_digest"] = "different_registry_digest"
    h3 = hash_waveguide_governed_compiler_session_registry(reg_dict)
    assert h1 == h3

def test_registry_counts_and_indexing(clean_report_data):
    registry = build_waveguide_governed_compiler_session_registry(REPORT_PATH, report_data=clean_report_data)
    
    # Registered session count is correct (2 verified sessions)
    assert registry.registered_session_count == 2
    # Registered rejection session count is correct (1 rejection-verified session)
    assert registry.registered_rejection_session_count == 1
    # Blocked/invalid counts are zero for clean artifacts
    assert registry.blocked_session_count == 0
    assert registry.invalid_session_count == 0

    # RC1 session count is correct
    assert registry.rc1_session_count == 2
    # RC2 session count is correct
    assert registry.rc2_session_count == 1

    # Compiler profiles are deterministic and sorted
    assert registry.compiler_profiles_indexed == ["COST_MODEL_DEBUG", "FULL_SAFE_OPTIMIZED"]

    # Pass sequences are indexed deterministically
    assert registry.pass_sequences_indexed == [
        ["cost_model_evaluation"],
        ["pipeline_compaction"],
        ["pipeline_compaction", "cost_model_evaluation", "deterministic_policy_selection"]
    ]

    # Handler IDs are deterministic and sorted
    assert registry.handler_ids_indexed == [
        "SOL-PASS-HANDLER-COST-MODEL-EVALUATION-V1",
        "SOL-PASS-HANDLER-DETERMINISTIC-POLICY-SELECTION-V1",
        "SOL-PASS-HANDLER-PIPELINE-COMPACTION-V1"
    ]

    # Nested digest reference lists are sorted deterministically
    assert registry.invocation_record_digests == sorted(registry.invocation_record_digests)
    assert registry.session_case_digests == sorted(registry.session_case_digests)
    assert registry.trace_ledger_digests == sorted(registry.trace_ledger_digests)
    assert registry.replay_report_digests == sorted(registry.replay_report_digests)
    assert registry.final_output_payload_digests == sorted(registry.final_output_payload_digests)

def test_summary_and_json_export(clean_report_data):
    registry = build_waveguide_governed_compiler_session_registry(REPORT_PATH, report_data=clean_report_data)
    
    # Summary output is deterministic
    summary = summarize_waveguide_governed_compiler_session_registry(registry)
    assert "SOL WAVEGUIDE GOVERNED COMPILER SESSION REGISTRY" in summary
    assert "Registry Digest:" in summary

    # JSON export is deterministic
    temp_path = os.path.join(REPO_ROOT, "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY_TEST_TEMP.json")
    export_waveguide_governed_compiler_session_registry(registry, temp_path)
    assert os.path.exists(temp_path)
    with open(temp_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["registry_digest"] == registry.registry_digest
    os.remove(temp_path)

def test_helper_indexes(clean_report_data):
    registry = build_waveguide_governed_compiler_session_registry(REPORT_PATH, report_data=clean_report_data)
    entries_serialized = registry.entries
    
    indexed_status = index_waveguide_governed_compiler_sessions_by_status(entries_serialized)
    assert len(indexed_status["session_registered"]) == 2
    assert len(indexed_status["session_rejection_registered"]) == 1

    indexed_rc = index_waveguide_governed_compiler_sessions_by_rc(entries_serialized)
    assert len(indexed_rc["SOL-WAVEGUIDE-RC1"]) == 2
    assert len(indexed_rc["SOL-WAVEGUIDE-RC2"]) == 1

    indexed_profile = index_waveguide_governed_compiler_sessions_by_profile(entries_serialized)
    assert len(indexed_profile["COST_MODEL_DEBUG"]) == 2
    assert len(indexed_profile["FULL_SAFE_OPTIMIZED"]) == 1

def test_compare_registries(clean_report_data):
    r1 = build_waveguide_governed_compiler_session_registry(REPORT_PATH, report_data=clean_report_data)
    r2 = build_waveguide_governed_compiler_session_registry(REPORT_PATH, report_data=clean_report_data)
    diffs = compare_waveguide_governed_compiler_session_registries(r1, r2)
    assert diffs == {}

def test_artifacts_exist():
    # Session registry JSON artifact exists
    json_path = os.path.join(REPO_ROOT, "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.json")
    # Session registry documentation exists
    doc_path = os.path.join(REPO_ROOT, "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.md")

    assert os.path.exists(json_path)
    assert os.path.exists(doc_path)
