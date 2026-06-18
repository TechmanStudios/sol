# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Release Certification Bundle.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT, hash_file_contents
from sol_waveguide_release_certification_bundle import (
    WaveguideReleaseCertificationBundle,
    build_waveguide_release_certification_bundle,
    validate_waveguide_release_certification_bundle,
    summarize_waveguide_release_certification_bundle,
    export_waveguide_release_certification_bundle,
    compare_waveguide_release_certification_bundles,
    hash_waveguide_release_certification_bundle,
    collect_waveguide_release_certification_artifact_digests,
    validate_waveguide_release_certification_artifact_chain,
    build_waveguide_release_certification_bundle_index,
    get_default_artifact_paths
)


@pytest.fixture
def temp_dir():
    path = os.path.join(REPO_ROOT, "docs", "test_temp")
    os.makedirs(path, exist_ok=True)
    yield path
    if os.path.exists(path):
        for f in os.listdir(path):
            try:
                os.remove(os.path.join(path, f))
            except Exception:
                pass
        try:
            os.rmdir(path)
        except Exception:
            pass


def test_rc1_bundle_build_and_validation():
    # Build RC1 bundle using defaults
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    assert bundle.rc_id == "SOL-WAVEGUIDE-RC1"
    assert bundle.candidate_level == "Foundation"
    assert bundle.certification_status == "certification_ready"
    assert "RELEASE_CERTIFICATION_READY" in bundle.reason_codes
    assert "RELEASE_CERT_MANIFEST_VALID" in bundle.reason_codes
    assert "RELEASE_CERT_RELEASE_GATE_VALID" in bundle.reason_codes
    assert "RELEASE_CERT_PROMOTION_RECORD_VALID" in bundle.reason_codes
    assert "RELEASE_CERT_COURT_VERDICT_APPROVED" in bundle.reason_codes
    assert "RELEASE_CERT_RC_APPROVED_IN_REGISTRY" in bundle.reason_codes
    assert "RELEASE_CERT_RUNTIME_CAPABILITY_VALID" in bundle.reason_codes
    assert "RELEASE_CERT_SESSION_REGISTRY_VALID" in bundle.reason_codes

    # Validate bundle
    is_valid, reasons = validate_waveguide_release_certification_bundle(bundle)
    assert is_valid is True
    assert "RELEASE_CERTIFICATION_READY" in reasons


def test_rc2_bundle_build_and_validation():
    # Build RC2 bundle using defaults
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC2")
    assert bundle.rc_id == "SOL-WAVEGUIDE-RC2"
    assert bundle.candidate_level == "Governed Execution Stack"
    assert bundle.certification_status == "certification_ready"
    assert "RELEASE_CERTIFICATION_READY" in bundle.reason_codes
    
    # Validate bundle
    is_valid, reasons = validate_waveguide_release_certification_bundle(bundle)
    assert is_valid is True
    assert "RELEASE_CERTIFICATION_READY" in reasons


def test_digest_determinism_and_exclusion():
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    
    # Bundle digest is deterministic
    h1 = hash_waveguide_release_certification_bundle(bundle)
    h2 = hash_waveguide_release_certification_bundle(bundle)
    assert h1 == h2
    assert bundle.certification_bundle_digest == h1

    # certification_bundle_digest is excluded from its own digest input
    bundle_dict = asdict(bundle)
    bundle_dict["certification_bundle_digest"] = "different_digest_value"
    h3 = hash_waveguide_release_certification_bundle(bundle_dict)
    assert h1 == h3


def test_rc_id_mismatch_blocks_certification(temp_dir):
    # Copy RC1 manifest but change rc_id inside it
    src_m_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC1_MANIFEST.json")
    with open(src_m_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    
    # Tamper with manifest rc_id
    manifest_data["rc_id"] = "SOL-WAVEGUIDE-RC-TAMPERED"
    temp_m_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RC1_MANIFEST.json")
    with open(temp_m_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    # Build bundle pointing to tampered manifest
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        manifest_path=temp_m_path
    )
    assert bundle.certification_status == "certification_invalid"
    assert "RELEASE_CERT_MANIFEST_INVALID" in bundle.reason_codes
    assert "RELEASE_CERTIFICATION_INVALID" in bundle.reason_codes


def test_missing_manifest_blocks_certification():
    # Build with non-existent manifest path
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        manifest_path="docs/NON_EXISTENT_MANIFEST.json"
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_MANIFEST_INVALID" in bundle.reason_codes
    assert "RELEASE_CERTIFICATION_BLOCKED" in bundle.reason_codes


def test_invalid_manifest_blocks_certification(temp_dir):
    # Write invalid JSON or invalid manifest schema
    temp_m_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RC1_MANIFEST.json")
    with open(temp_m_path, "w", encoding="utf-8") as f:
        json.dump({"rc_id": "SOL-WAVEGUIDE-RC1"}, f)  # Missing schema properties

    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        manifest_path=temp_m_path
    )
    assert bundle.certification_status == "certification_invalid"
    assert "RELEASE_CERT_MANIFEST_INVALID" in bundle.reason_codes


def test_missing_release_gate_blocks_certification():
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        release_gate_path="docs/NON_EXISTENT_RELEASE_GATE.json"
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_RELEASE_GATE_BLOCKED" in bundle.reason_codes


def test_blocked_release_gate_blocks_certification(temp_dir):
    # Copy delta audit, change boundary_valid to False
    src_rg_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_DELTA_AUDIT.json")
    with open(src_rg_path, "r", encoding="utf-8") as f:
        rg_data = json.load(f)
    rg_data["boundary_valid"] = False
    temp_rg_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RC_DELTA_AUDIT.json")
    with open(temp_rg_path, "w", encoding="utf-8") as f:
        json.dump(rg_data, f)

    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        release_gate_path=temp_rg_path
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_RELEASE_GATE_BLOCKED" in bundle.reason_codes
    assert "RELEASE_CERTIFICATION_BLOCKED" in bundle.reason_codes


def test_missing_promotion_record_blocks_certification():
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        promotion_record_path="docs/NON_EXISTENT_PROMOTION_RECORD.json"
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_PROMOTION_RECORD_INVALID" in bundle.reason_codes


def test_invalid_promotion_record_blocks_certification(temp_dir):
    # Tamper with promotion record rc_id
    src_pr_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC1.json")
    with open(src_pr_path, "r", encoding="utf-8") as f:
        pr_data = json.load(f)
    pr_data["rc_id"] = "SOL-WAVEGUIDE-RC2"
    temp_pr_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC1.json")
    with open(temp_pr_path, "w", encoding="utf-8") as f:
        json.dump(pr_data, f)

    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        promotion_record_path=temp_pr_path
    )
    assert bundle.certification_status == "certification_invalid"
    assert "RELEASE_CERT_PROMOTION_RECORD_INVALID" in bundle.reason_codes


def test_missing_court_verdict_blocks_certification():
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        court_verdict_path="docs/NON_EXISTENT_COURT_VERDICT.json"
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_COURT_VERDICT_REJECTED" in bundle.reason_codes


def test_non_approved_court_verdict_blocks_certification(temp_dir):
    # Copy verdict, change court_verdict to promotion_rejected
    src_cv_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_COURT_VERDICT_RC1.json")
    with open(src_cv_path, "r", encoding="utf-8") as f:
        cv_data = json.load(f)
    cv_data["court_verdict"] = "promotion_rejected"
    # recalculate its digest since the validator validates it
    from sol_waveguide_rc_promotion_court import hash_waveguide_rc_court_verdict
    cv_data["verdict_digest"] = ""
    cv_data["verdict_digest"] = hash_waveguide_rc_court_verdict(cv_data)

    temp_cv_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RC_COURT_VERDICT_RC1.json")
    with open(temp_cv_path, "w", encoding="utf-8") as f:
        json.dump(cv_data, f)

    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        court_verdict_path=temp_cv_path
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_COURT_VERDICT_REJECTED" in bundle.reason_codes


def test_missing_release_registry_blocks_certification():
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        release_registry_path="docs/NON_EXISTENT_RELEASE_REGISTRY.json"
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_RC_MISSING_FROM_REGISTRY" in bundle.reason_codes


def test_rc_missing_from_release_registry_blocks_certification(temp_dir):
    # Copy release registry, remove RC1 from approved_rc_ids
    src_rr_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    with open(src_rr_path, "r", encoding="utf-8") as f:
        rr_data = json.load(f)
    rr_data["approved_rc_ids"] = [rc for rc in rr_data["approved_rc_ids"] if rc != "SOL-WAVEGUIDE-RC1"]
    
    from sol_waveguide_rc_release_registry import hash_waveguide_rc_release_registry
    rr_data["registry_digest"] = ""
    rr_data["registry_digest"] = hash_waveguide_rc_release_registry(rr_data)

    temp_rr_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    with open(temp_rr_path, "w", encoding="utf-8") as f:
        json.dump(rr_data, f)

    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        release_registry_path=temp_rr_path
    )
    assert bundle.certification_status == "certification_invalid"
    assert "RELEASE_CERT_RC_MISSING_FROM_REGISTRY" in bundle.reason_codes


def test_missing_runtime_capability_blocks_certification():
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        capability_resolution_path="docs/NON_EXISTENT_RUNTIME_CAPABILITY.json"
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_RUNTIME_CAPABILITY_INVALID" in bundle.reason_codes


def test_invalid_runtime_capability_blocks_certification(temp_dir):
    # Copy runtime capability, change rc_id
    src_cr_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    with open(src_cr_path, "r", encoding="utf-8") as f:
        cr_data = json.load(f)
    cr_data["rc_id"] = "SOL-WAVEGUIDE-RC-TAMPERED"

    from sol_waveguide_runtime_capability_resolver import hash_waveguide_runtime_capability_resolution
    cr_data["resolution_digest"] = ""
    cr_data["resolution_digest"] = hash_waveguide_runtime_capability_resolution(cr_data)

    temp_cr_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    with open(temp_cr_path, "w", encoding="utf-8") as f:
        json.dump(cr_data, f)

    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        capability_resolution_path=temp_cr_path
    )
    assert bundle.certification_status == "certification_invalid"
    assert "RELEASE_CERT_RUNTIME_CAPABILITY_INVALID" in bundle.reason_codes


def test_missing_session_registry_blocks_certification():
    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        session_registry_path="docs/NON_EXISTENT_SESSION_REGISTRY.json"
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_SESSION_REGISTRY_INVALID" in bundle.reason_codes


def test_invalid_session_registry_blocks_certification(temp_dir):
    # Copy session registry, change registry_status to session_registry_blocked
    src_sr_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.json")
    with open(src_sr_path, "r", encoding="utf-8") as f:
        sr_data = json.load(f)
    sr_data["registry_status"] = "session_registry_blocked"

    from sol_waveguide_governed_compiler_session_registry import hash_waveguide_governed_compiler_session_registry
    sr_data["registry_digest"] = ""
    sr_data["registry_digest"] = hash_waveguide_governed_compiler_session_registry(sr_data)

    temp_sr_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.json")
    with open(temp_sr_path, "w", encoding="utf-8") as f:
        json.dump(sr_data, f)

    bundle = build_waveguide_release_certification_bundle(
        "SOL-WAVEGUIDE-RC1",
        session_registry_path=temp_sr_path
    )
    assert bundle.certification_status == "certification_blocked"
    assert "RELEASE_CERT_SESSION_REGISTRY_INVALID" in bundle.reason_codes


def test_missing_software_caveat_blocks_certification():
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    
    # Force modify caveat
    bundle.software_validation_caveat = ""
    is_valid, reasons = validate_waveguide_release_certification_bundle(bundle)
    assert is_valid is False
    assert "RELEASE_CERTIFICATION_INVALID" in reasons


def test_registered_session_counts_preserved():
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    assert bundle.registered_session_count == 2
    assert bundle.registered_rejection_session_count == 1
    assert bundle.blocked_session_count == 0
    assert bundle.invalid_session_count == 0
    assert bundle.rc1_session_count == 2
    assert bundle.rc2_session_count == 1
    assert "COST_MODEL_DEBUG" in bundle.compiler_profiles_indexed
    assert "FULL_SAFE_OPTIMIZED" in bundle.compiler_profiles_indexed


def test_artifact_digest_list_is_sorted():
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    assert bundle.artifact_paths == sorted(bundle.artifact_paths)


def test_summary_output_deterministic():
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    s1 = summarize_waveguide_release_certification_bundle(bundle)
    s2 = summarize_waveguide_release_certification_bundle(bundle)
    assert s1 == s2
    assert "SOL WAVEGUIDE RELEASE CERTIFICATION BUNDLE SUMMARY" in s1


def test_json_export_and_compare(temp_dir):
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    export_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json")
    
    export_waveguide_release_certification_bundle(bundle, export_path)
    assert os.path.exists(export_path)
    
    with open(export_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    
    assert loaded["rc_id"] == "SOL-WAVEGUIDE-RC1"
    assert loaded["certification_bundle_digest"] == bundle.certification_bundle_digest

    # Compare
    diffs = compare_waveguide_release_certification_bundles(bundle, loaded)
    assert len(diffs) == 0


def test_artifact_chain_helpers():
    paths = get_default_artifact_paths("SOL-WAVEGUIDE-RC1")
    digests = collect_waveguide_release_certification_artifact_digests("SOL-WAVEGUIDE-RC1", paths)
    assert len(digests) == len(paths)

    ok, reasons = validate_waveguide_release_certification_artifact_chain("SOL-WAVEGUIDE-RC1", paths, digests)
    assert ok is True
    assert "RELEASE_CERTIFICATION_READY" in reasons


def test_bundle_index_building():
    b1 = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    b2 = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC2")
    
    index = build_waveguide_release_certification_bundle_index([b1, b2])
    assert "SOL-WAVEGUIDE-RC1" in index
    assert "SOL-WAVEGUIDE-RC2" in index
    assert index["SOL-WAVEGUIDE-RC1"]["certification_status"] == "certification_ready"
    assert index["SOL-WAVEGUIDE-RC2"]["certification_status"] == "certification_ready"
