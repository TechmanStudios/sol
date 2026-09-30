# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Release Certification Validator / Independent Audit Verifier.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT, hash_file_contents
from sol_waveguide_release_certification_bundle import (
    build_waveguide_release_certification_bundle,
    get_default_artifact_paths
)
from sol_waveguide_release_certification_validator import (
    build_waveguide_release_certification_audit_case,
    validate_waveguide_release_certification_bundle_independently,
    build_waveguide_release_certification_audit_report,
    validate_waveguide_release_certification_audit_report,
    summarize_waveguide_release_certification_audit_report,
    export_waveguide_release_certification_audit_report,
    compare_waveguide_release_certification_audit_reports,
    hash_waveguide_release_certification_audit_case,
    hash_waveguide_release_certification_audit_report,
    recompute_waveguide_release_certification_artifact_digest,
    validate_waveguide_release_certification_artifact_digests,
    load_waveguide_release_certification_artifact_chain,
    WaveguideReleaseCertificationAuditCase,
    WaveguideReleaseCertificationAuditReport
)


@pytest.fixture
def temp_dir():
    path = os.path.join(REPO_ROOT, "docs", "test_validator_temp")
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


def test_rc1_audit_case_build_and_validation():
    # 1. RC1 audit case can be built.
    # Load canonical RC1 bundle
    bundle_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json")
    assert os.path.exists(bundle_path)

    case = build_waveguide_release_certification_audit_case(bundle_path)
    assert isinstance(case, WaveguideReleaseCertificationAuditCase)
    assert case.rc_id == "SOL-WAVEGUIDE-RC1"
    assert case.certification_bundle_id == "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1"
    
    # 3. RC1 audit case validates as audit_verified.
    assert case.audit_status == "audit_verified"
    assert "RELEASE_AUDIT_VERIFIED" in case.reason_codes
    assert "RELEASE_AUDIT_BUNDLE_DIGEST_MATCH" in case.reason_codes
    assert "RELEASE_AUDIT_BUNDLE_VALID" in case.reason_codes
    assert "RELEASE_AUDIT_MANIFEST_VALID" in case.reason_codes
    assert "RELEASE_AUDIT_RELEASE_GATE_VALID" in case.reason_codes
    assert "RELEASE_AUDIT_PROMOTION_RECORD_VALID" in case.reason_codes
    assert "RELEASE_AUDIT_COURT_VERDICT_APPROVED" in case.reason_codes
    assert "RELEASE_AUDIT_RC_APPROVED_IN_REGISTRY" in case.reason_codes
    assert "RELEASE_AUDIT_RUNTIME_CAPABILITY_VALID" in case.reason_codes
    assert "RELEASE_AUDIT_SESSION_REGISTRY_VALID" in case.reason_codes
    assert "RELEASE_AUDIT_SESSION_COUNTS_MATCH" in case.reason_codes
    assert "RELEASE_AUDIT_INDEXES_MATCH" in case.reason_codes
    assert "RELEASE_AUDIT_SOFTWARE_CAVEAT_INCLUDED" in case.reason_codes


def test_rc2_audit_case_build_and_validation():
    # 2. RC2 audit case can be built.
    # Load canonical RC2 bundle
    bundle_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC2.json")
    assert os.path.exists(bundle_path)

    case = build_waveguide_release_certification_audit_case(bundle_path)
    assert isinstance(case, WaveguideReleaseCertificationAuditCase)
    assert case.rc_id == "SOL-WAVEGUIDE-RC2"
    assert case.certification_bundle_id == "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC2"

    # 4. RC2 audit case validates as audit_verified.
    assert case.audit_status == "audit_verified"
    assert "RELEASE_AUDIT_VERIFIED" in case.reason_codes


def test_audit_case_digest_determinism_and_exclusion():
    bundle_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json")
    case = build_waveguide_release_certification_audit_case(bundle_path)

    # 5. Audit case digest is deterministic.
    d1 = hash_waveguide_release_certification_audit_case(case)
    d2 = hash_waveguide_release_certification_audit_case(case)
    assert d1 == d2
    assert case.audit_case_digest == d1

    # 6. audit_case_digest is excluded from its own digest input.
    c_dict = asdict(case)
    c_dict["audit_case_digest"] = "different_digest_value"
    d3 = hash_waveguide_release_certification_audit_case(c_dict)
    assert d1 == d3


def test_rc1_and_rc2_audit_reports():
    bundle_path_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json")
    bundle_path_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC2.json")

    case_rc1 = build_waveguide_release_certification_audit_case(bundle_path_rc1)
    case_rc2 = build_waveguide_release_certification_audit_case(bundle_path_rc2)

    # 7. RC1 audit report validates.
    report_rc1 = build_waveguide_release_certification_audit_report([case_rc1])
    assert isinstance(report_rc1, WaveguideReleaseCertificationAuditReport)
    assert report_rc1.audit_report_status == "audit_report_verified"
    assert report_rc1.rc1_audit_count == 1
    assert report_rc1.rc2_audit_count == 0
    ok_rc1, reasons_rc1 = validate_waveguide_release_certification_audit_report(report_rc1)
    assert ok_rc1 is True
    assert "RELEASE_AUDIT_REPORT_VERIFIED" in reasons_rc1

    # 8. RC2 audit report validates.
    report_rc2 = build_waveguide_release_certification_audit_report([case_rc2])
    assert report_rc2.audit_report_status == "audit_report_verified"
    assert report_rc2.rc1_audit_count == 0
    assert report_rc2.rc2_audit_count == 1
    ok_rc2, reasons_rc2 = validate_waveguide_release_certification_audit_report(report_rc2)
    assert ok_rc2 is True
    assert "RELEASE_AUDIT_REPORT_VERIFIED" in reasons_rc2

    # 9. Optional combined audit report validates.
    report_combined = build_waveguide_release_certification_audit_report([case_rc1, case_rc2])
    assert report_combined.audit_report_status == "audit_report_verified"
    assert report_combined.rc1_audit_count == 1
    assert report_combined.rc2_audit_count == 1
    ok_combined, reasons_combined = validate_waveguide_release_certification_audit_report(report_combined)
    assert ok_combined is True
    assert "RELEASE_AUDIT_REPORT_VERIFIED" in reasons_combined


def test_audit_report_digest_determinism_and_exclusion():
    bundle_path_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json")
    case_rc1 = build_waveguide_release_certification_audit_case(bundle_path_rc1)
    report = build_waveguide_release_certification_audit_report([case_rc1])

    # 10. Audit report digest is deterministic.
    d1 = hash_waveguide_release_certification_audit_report(report)
    d2 = hash_waveguide_release_certification_audit_report(report)
    assert d1 == d2
    assert report.audit_report_digest == d1

    # 11. audit_report_digest is excluded from its own digest input.
    r_dict = asdict(report)
    r_dict["audit_report_digest"] = "different_digest_value"
    d3 = hash_waveguide_release_certification_audit_report(r_dict)
    assert d1 == d3


def test_bundle_digest_mismatch_fails_audit():
    # 12. Bundle digest mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    # Tamper with recorded digest
    bundle_dict["certification_bundle_digest"] = "tampered_bundle_digest"
    
    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert "RELEASE_AUDIT_BUNDLE_DIGEST_MISMATCH" in case.reason_codes
    assert case.certification_bundle_digest_match is False


def test_bundle_status_not_ready_fails_audit():
    # 13. Bundle status not ready fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["certification_status"] = "certification_invalid"
    
    # Recalculate bundle digest so digest match passes, but status check fails
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert "RELEASE_AUDIT_BUNDLE_CERTIFICATION_READY" not in case.reason_codes


def test_missing_manifest_fails_audit(temp_dir):
    # 14. Missing manifest artifact fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    # Point manifest path to non-existent file
    paths = bundle_dict["artifact_paths"]
    new_paths = []
    for p in paths:
        if "manifest" in p.lower():
            new_paths.append("docs/NON_EXISTENT_MANIFEST.json")
        else:
            new_paths.append(p)
    bundle_dict["artifact_paths"] = sorted(new_paths)
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_blocked"
    assert "docs/NON_EXISTENT_MANIFEST.json" in case.artifact_digest_mismatches
    assert any("Manifest artifact missing" in f for f in case.artifact_validation_failures)


def test_manifest_digest_mismatch_fails_audit(temp_dir):
    # 15. Manifest digest mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    # Tamper with manifest digest
    bundle_dict["manifest_digest"] = "tampered_manifest_digest"
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("manifest" in p.lower() for p in case.artifact_digest_mismatches)


def test_missing_release_gate_fails_audit():
    # 16. Missing release gate artifact fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    new_paths = []
    for p in bundle_dict["artifact_paths"]:
        if "delta_audit" in p.lower():
            new_paths.append("docs/NON_EXISTENT_DELTA_AUDIT.json")
        else:
            new_paths.append(p)
    bundle_dict["artifact_paths"] = sorted(new_paths)
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_blocked"
    assert "docs/NON_EXISTENT_DELTA_AUDIT.json" in case.artifact_digest_mismatches
    assert any("Release gate artifact missing" in f for f in case.artifact_validation_failures)


def test_release_gate_digest_mismatch_fails_audit():
    # 17. Release gate digest mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["release_gate_digest"] = "tampered_gate_digest"
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("delta_audit" in p.lower() for p in case.artifact_digest_mismatches)


def test_missing_promotion_record_fails_audit():
    # 18. Missing promotion record artifact fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    new_paths = []
    for p in bundle_dict["artifact_paths"]:
        if "promotion_record" in p.lower():
            new_paths.append("docs/NON_EXISTENT_PROMOTION_RECORD.json")
        else:
            new_paths.append(p)
    bundle_dict["artifact_paths"] = sorted(new_paths)
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_blocked"
    assert "docs/NON_EXISTENT_PROMOTION_RECORD.json" in case.artifact_digest_mismatches


def test_promotion_record_digest_mismatch_fails_audit():
    # 19. Promotion record digest mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["promotion_record_digest"] = "tampered_pr_digest"
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("promotion_record" in p.lower() for p in case.artifact_digest_mismatches)


def test_missing_court_verdict_fails_audit():
    # 20. Missing court verdict artifact fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    new_paths = []
    for p in bundle_dict["artifact_paths"]:
        if "court_verdict" in p.lower():
            new_paths.append("docs/NON_EXISTENT_COURT_VERDICT.json")
        else:
            new_paths.append(p)
    bundle_dict["artifact_paths"] = sorted(new_paths)
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_blocked"
    assert "docs/NON_EXISTENT_COURT_VERDICT.json" in case.artifact_digest_mismatches


def test_court_verdict_digest_mismatch_fails_audit():
    # 21. Court verdict digest mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["promotion_court_verdict_digest"] = "tampered_cv_digest"
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("court_verdict" in p.lower() for p in case.artifact_digest_mismatches)


def test_missing_release_registry_fails_audit():
    # 22. Missing release registry artifact fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    new_paths = []
    for p in bundle_dict["artifact_paths"]:
        if "release_registry" in p.lower():
            new_paths.append("docs/NON_EXISTENT_RELEASE_REGISTRY.json")
        else:
            new_paths.append(p)
    bundle_dict["artifact_paths"] = sorted(new_paths)
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_blocked"
    assert "docs/NON_EXISTENT_RELEASE_REGISTRY.json" in case.artifact_digest_mismatches


def test_rc_missing_from_release_registry_fails_audit(temp_dir):
    # 23. Target RC missing from release registry fails audit.
    # We copy release registry but tamper with it so approved_rc_ids lacks SOL-WAVEGUIDE-RC1
    src_rr_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    with open(src_rr_path, "r", encoding="utf-8") as f:
        rr_data = json.load(f)
    rr_data["approved_rc_ids"] = [] # empty approved RCs
    
    from sol_waveguide_rc_release_registry import hash_waveguide_rc_release_registry
    rr_data["registry_digest"] = ""
    rr_data["registry_digest"] = hash_waveguide_rc_release_registry(rr_data)
    
    temp_rr_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    with open(temp_rr_path, "w", encoding="utf-8") as f:
        json.dump(rr_data, f)
        
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1", release_registry_path=temp_rr_path)
    bundle_dict = asdict(bundle)
    
    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert case.rc_approved_in_registry is False
    assert any("Target RC not approved" in f for f in case.artifact_validation_failures)


def test_missing_runtime_capability_fails_audit():
    # 24. Missing runtime capability resolution artifact fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    new_paths = []
    for p in bundle_dict["artifact_paths"]:
        if "capability_resolver" in p.lower() or "capability_resolution" in p.lower():
            new_paths.append("docs/NON_EXISTENT_RUNTIME_CAPABILITY.json")
        else:
            new_paths.append(p)
    bundle_dict["artifact_paths"] = sorted(new_paths)
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_blocked"
    assert "docs/NON_EXISTENT_RUNTIME_CAPABILITY.json" in case.artifact_digest_mismatches


def test_runtime_capability_digest_mismatch_fails_audit():
    # 25. Runtime capability digest mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["runtime_capability_resolution_digest"] = "tampered_cr_digest"
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("capability_resolver" in p.lower() or "capability_resolution" in p.lower() for p in case.artifact_digest_mismatches)


def test_runtime_capability_rc_mismatch_fails_audit(temp_dir):
    # 26. Runtime capability RC mismatch fails audit.
    src_cr_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    with open(src_cr_path, "r", encoding="utf-8") as f:
        cr_data = json.load(f)
    cr_data["rc_id"] = "SOL-WAVEGUIDE-RC2"  # mismatch
    
    from sol_waveguide_runtime_capability_resolver import hash_waveguide_runtime_capability_resolution
    cr_data["resolution_digest"] = ""
    cr_data["resolution_digest"] = hash_waveguide_runtime_capability_resolution(cr_data)
    
    temp_cr_path = os.path.join(temp_dir, "SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json")
    with open(temp_cr_path, "w", encoding="utf-8") as f:
        json.dump(cr_data, f)
        
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1", capability_resolution_path=temp_cr_path)
    bundle_dict = asdict(bundle)
    
    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert case.nested_rc_id_consistent is False
    assert any("capability resolution rc_id mismatch" in f.lower() for f in case.artifact_validation_failures)


def test_missing_session_registry_fails_audit():
    # 27. Missing session registry artifact fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    new_paths = []
    for p in bundle_dict["artifact_paths"]:
        if "session_registry" in p.lower():
            new_paths.append("docs/NON_EXISTENT_SESSION_REGISTRY.json")
        else:
            new_paths.append(p)
    bundle_dict["artifact_paths"] = sorted(new_paths)
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_blocked"
    assert "docs/NON_EXISTENT_SESSION_REGISTRY.json" in case.artifact_digest_mismatches


def test_session_registry_digest_mismatch_fails_audit():
    # 28. Session registry digest mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["compiler_session_registry_digest"] = "tampered_sr_digest"
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("session_registry" in p.lower() for p in case.artifact_digest_mismatches)


def test_session_registry_count_mismatch_fails_audit():
    # 29. Session registry count mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["registered_session_count"] = 99999  # count mismatch
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("Session registry counts mismatch" in f for f in case.artifact_validation_failures)


def test_session_registry_index_mismatch_fails_audit():
    # 30. Session registry index mismatch fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["compiler_profiles_indexed"] = ["TAMPERED_PROFILE"]  # index mismatch
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("Session registry indexed lists mismatch" in f for f in case.artifact_validation_failures)


def test_missing_software_caveat_fails_audit():
    # 31. Missing software caveat fails audit.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    bundle_dict["software_validation_caveat"] = ""
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert case.audit_status == "audit_failed"
    assert any("Software validation caveat is missing or invalid" in f for f in case.artifact_validation_failures)


def test_mismatch_and_failure_counts_correct():
    # 32. Artifact digest mismatch count is correct.
    # 33. Artifact validation failure count is correct.
    bundle = build_waveguide_release_certification_bundle("SOL-WAVEGUIDE-RC1")
    bundle_dict = asdict(bundle)
    
    # Introduce multiple mismatches
    bundle_dict["manifest_digest"] = "tampered1"
    bundle_dict["release_gate_digest"] = "tampered2"
    bundle_dict["software_validation_caveat"] = ""
    
    from sol_waveguide_release_certification_bundle import hash_waveguide_release_certification_bundle
    bundle_dict["certification_bundle_digest"] = hash_waveguide_release_certification_bundle(bundle_dict)

    case = build_waveguide_release_certification_audit_case(bundle_dict)
    assert len(case.artifact_digest_mismatches) == 2
    assert len(case.artifact_validation_failures) == 1
    
    report = build_waveguide_release_certification_audit_report([case])
    assert report.artifact_digest_mismatch_count == 2
    assert report.artifact_validation_failure_count == 1


def test_audit_json_artifacts_exist():
    # 34. RC1 audit JSON artifact exists.
    # 35. RC2 audit JSON artifact exists.
    # 36. Optional combined audit JSON artifact exists, if implemented.
    # 37. Audit validator documentation exists.
    
    # We will generate and export the actual artifacts at the end, so these tests will verify they are there.
    # Wait, in pytest, we'll verify they exist under their expected paths.
    p_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    p_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")
    p_comb = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT.json")
    p_doc = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_VALIDATOR.md")
    
    assert os.path.exists(p_rc1)
    assert os.path.exists(p_rc2)
    assert os.path.exists(p_comb)
    assert os.path.exists(p_doc)


def test_summary_and_export_determinism(temp_dir):
    # 38. Summary output is deterministic.
    # 39. JSON export is deterministic.
    bundle_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json")
    case = build_waveguide_release_certification_audit_case(bundle_path)
    report = build_waveguide_release_certification_audit_report([case])

    s1 = summarize_waveguide_release_certification_audit_report(report)
    s2 = summarize_waveguide_release_certification_audit_report(report)
    assert s1 == s2
    assert "SOL WAVEGUIDE RELEASE CERTIFICATION AUDIT REPORT SUMMARY" in s1

    exp1 = os.path.join(temp_dir, "exp1.json")
    exp2 = os.path.join(temp_dir, "exp2.json")

    export_waveguide_release_certification_audit_report(report, exp1)
    export_waveguide_release_certification_audit_report(report, exp2)

    with open(exp1, "r") as f1, open(exp2, "r") as f2:
        content1 = f1.read()
        content2 = f2.read()

    assert content1 == content2
    
    # 40. Existing release certification bundle tests still pass.
    # We will verify this by running pytest.
