# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide RC Release Gate and Delta Audit Harness
"""

import os
import json
import pytest
from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_release_gate import (
    build_waveguide_rc_delta_report,
    compare_waveguide_rc_manifests,
    validate_waveguide_rc_boundary,
    build_waveguide_rc_release_gate,
    summarize_waveguide_rc_release_gate
)


def test_manifest_can_be_built():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    assert rc1 is not None
    assert rc2 is not None


def test_rc1_excludes_governed_features():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    profiles = rc1.get("optimization_profiles", [])
    passes = rc1.get("canonical_pass_order", [])
    assert "cost_model_and_autotuning" not in rc1
    assert "COST_MODEL_DEBUG" not in profiles
    assert "channel_kernel_recognition" not in passes


def test_rc2_includes_governed_features():
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    profiles = rc2.get("optimization_profiles", [])
    passes = rc2.get("canonical_pass_order", [])
    assert "cost_model_and_autotuning" in rc2
    assert "COST_MODEL_DEBUG" in profiles
    assert "channel_kernel_recognition" in passes


def test_delta_report_identifies_rc2_only_features():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    report = build_waveguide_rc_delta_report(rc1, rc2)
    
    assert "COST_MODEL_DEBUG" in report["rc2_only_features"]["profiles"]
    assert "channel_kernel_recognition" in report["rc2_only_features"]["passes"]
    assert "cost_model_and_autotuning" in report["rc2_only_features"]["fields"]
    assert report["boundary_valid"] is True


def test_delta_report_is_deterministic():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    report1 = build_waveguide_rc_delta_report(rc1, rc2)
    report2 = build_waveguide_rc_delta_report(rc1, rc2)
    assert report1 == report2


def test_clean_rc1_produces_release_ready():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    gate = build_waveguide_rc_release_gate(rc1)
    assert gate["verdict"] == "release_ready"
    assert "RC_RELEASE_READY" in gate["reasons"]


def test_clean_rc2_produces_release_ready():
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    gate = build_waveguide_rc_release_gate(rc2)
    assert gate["verdict"] == "release_ready"
    assert "RC_RELEASE_READY" in gate["reasons"]


def test_rc1_leakage_produces_blocked():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    # Simulate leakage by injecting a governed profile
    rc1["optimization_profiles"].append("COST_MODEL_DEBUG")
    
    gate = build_waveguide_rc_release_gate(rc1)
    assert gate["verdict"] == "blocked"
    assert "RC1_GOVERNED_FEATURE_LEAK" in gate["reasons"]


def test_missing_rc2_feature_produces_blocked():
    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    # Simulate missing feature by removing a governed pass
    rc2["canonical_pass_order"].remove("cost_model_evaluation")
    
    gate = build_waveguide_rc_release_gate(rc2)
    assert gate["verdict"] == "blocked"
    assert "RC2_GOVERNED_FEATURE_MISSING" in gate["reasons"]


def test_summary_is_deterministic():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    gate = build_waveguide_rc_release_gate(rc1)
    s1 = summarize_waveguide_rc_release_gate(gate)
    s2 = summarize_waveguide_rc_release_gate(gate)
    assert s1 == s2
    assert "RELEASE_READY" in s1
    assert "Validation is shadow/sandbox software" in s1


def test_audit_json_exists():
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(workspace_dir, "docs")
    audit_path = os.path.join(docs_dir, "SOL_WAVEGUIDE_RC_DELTA_AUDIT.json")
    
    assert os.path.exists(audit_path)
    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["rc1_id"] == "SOL-WAVEGUIDE-RC1"
    assert data["rc2_id"] == "SOL-WAVEGUIDE-RC2"
    assert data["boundary_valid"] is True


def test_release_gate_docs_exist():
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(workspace_dir, "docs")
    doc_path = os.path.join(docs_dir, "SOL_WAVEGUIDE_RC_RELEASE_GATE.md")
    
    assert os.path.exists(doc_path)
