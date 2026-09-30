# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Publication Manifest Validator / Distribution Readiness Auditor.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_publication_manifest_validator import (
    build_waveguide_distribution_readiness_audit_case,
    validate_waveguide_publication_manifest_independently,
    build_waveguide_distribution_readiness_audit_report,
    validate_waveguide_distribution_readiness_audit_report,
    summarize_waveguide_distribution_readiness_audit_report,
    export_waveguide_distribution_readiness_audit_report,
    compare_waveguide_distribution_readiness_audit_reports,
    hash_waveguide_distribution_readiness_audit_case,
    hash_waveguide_distribution_readiness_audit_report,
    recompute_waveguide_publication_manifest_digest,
    recompute_waveguide_publication_entry_digest,
    validate_waveguide_distribution_channel_policy,
    index_waveguide_distribution_readiness_cases_by_rc,
    index_waveguide_distribution_readiness_cases_by_status,
    index_waveguide_distribution_readiness_cases_by_channel,
    WaveguideDistributionReadinessAuditCase,
    WaveguideDistributionReadinessAuditReport
)


@pytest.fixture
def temp_dir():
    path = os.path.join(REPO_ROOT, "docs", "test_auditor_temp")
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


def test_rc1_rc2_cases_build_and_validation():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")

    assert os.path.exists(pub_manifest_path)
    assert os.path.exists(registry_path)

    with open(pub_manifest_path, "r", encoding="utf-8") as f:
        pub_dict = json.load(f)
    
    rc1_pub_src = next(e for e in pub_dict["publication_entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")
    rc2_pub_src = next(e for e in pub_dict["publication_entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC2")

    # 1. RC1 distribution audit case can be built.
    case1 = build_waveguide_distribution_readiness_audit_case(rc1_pub_src, pub_manifest_path, registry_path)
    assert isinstance(case1, WaveguideDistributionReadinessAuditCase)
    assert case1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert case1.candidate_level == "Foundation"

    # 3. RC1 distribution audit case validates as distribution_ready.
    ok1, reasons1 = validate_waveguide_distribution_readiness_audit_report(
        build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)
    )
    assert ok1 is True
    assert case1.distribution_readiness_status == "distribution_ready"
    assert "DISTRIBUTION_RC_READY" in case1.reason_codes
    assert "DISTRIBUTION_AUDIT_CASE_CANONICAL" in case1.reason_codes

    # 2. RC2 distribution audit case can be built.
    case2 = build_waveguide_distribution_readiness_audit_case(rc2_pub_src, pub_manifest_path, registry_path)
    assert isinstance(case2, WaveguideDistributionReadinessAuditCase)
    assert case2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert case2.candidate_level == "Governed Execution Stack"

    # 4. RC2 distribution audit case validates as distribution_ready.
    assert case2.distribution_readiness_status == "distribution_ready"
    assert "DISTRIBUTION_RC_READY" in case2.reason_codes


def test_case_digest_determinism_and_exclusion():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    with open(pub_manifest_path, "r", encoding="utf-8") as f:
        pub_dict = json.load(f)
    rc1_pub_src = next(e for e in pub_dict["publication_entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")

    # 5. Distribution audit case digest is deterministic.
    case = build_waveguide_distribution_readiness_audit_case(rc1_pub_src, pub_manifest_path, registry_path)
    d1 = hash_waveguide_distribution_readiness_audit_case(case)
    d2 = hash_waveguide_distribution_readiness_audit_case(case)
    assert d1 == d2
    assert case.distribution_audit_case_digest == d1

    # 6. distribution_audit_case_digest is excluded from its own digest input.
    c_dict = asdict(case)
    c_dict["distribution_audit_case_digest"] = "DUMMY_SIGNATURE"
    recomputed = hash_waveguide_distribution_readiness_audit_case(c_dict)
    assert recomputed == d1


def test_digest_and_registry_failures():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    with open(pub_manifest_path, "r", encoding="utf-8") as f:
        pub_dict = json.load(f)
    rc1_pub_src = next(e for e in pub_dict["publication_entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")

    # 7. Publication manifest digest mismatch blocks or fails audit.
    bad_manifest = dict(pub_dict)
    bad_manifest["publication_manifest_digest"] = "mismatch"
    case = build_waveguide_distribution_readiness_audit_case(rc1_pub_src, bad_manifest, registry_path)
    assert "DISTRIBUTION_PUBLICATION_MANIFEST_DIGEST_MISMATCH" in case.reason_codes
    assert case.distribution_readiness_status == "distribution_blocked"

    # 8. Publication entry digest mismatch blocks or fails audit.
    bad_entry = dict(rc1_pub_src)
    bad_entry["publication_entry_digest"] = "mismatch"
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert "DISTRIBUTION_PUBLICATION_ENTRY_DIGEST_MISMATCH" in case.reason_codes
    assert case.distribution_readiness_status == "distribution_blocked"

    # 9. Missing source audit registry blocks audit.
    case = build_waveguide_distribution_readiness_audit_case(rc1_pub_src, pub_manifest_path, None)
    assert "DISTRIBUTION_SOURCE_AUDIT_REGISTRY_INVALID" in case.reason_codes
    assert case.distribution_readiness_status == "distribution_blocked"

    # 10. Source audit registry validation failure blocks audit.
    with open(registry_path, "r", encoding="utf-8") as f:
        reg_dict = json.load(f)
    bad_registry = dict(reg_dict)
    bad_registry["audit_registry_digest"] = "mismatch"
    case = build_waveguide_distribution_readiness_audit_case(rc1_pub_src, pub_manifest_path, bad_registry)
    assert "DISTRIBUTION_SOURCE_AUDIT_REGISTRY_INVALID" in case.reason_codes
    assert case.distribution_readiness_status == "distribution_blocked"

    # 11. Source audit registry digest mismatch blocks audit.
    bad_manifest2 = dict(pub_dict)
    bad_manifest2["source_audit_registry_digest"] = "mismatch"
    case = build_waveguide_distribution_readiness_audit_case(rc1_pub_src, bad_manifest2, registry_path)
    assert "DISTRIBUTION_SOURCE_AUDIT_REGISTRY_DIGEST_MISMATCH" in case.reason_codes
    assert case.distribution_readiness_status == "distribution_blocked"


def test_status_failures():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    with open(pub_manifest_path, "r", encoding="utf-8") as f:
        pub_dict = json.load(f)
    rc1_pub_src = next(e for e in pub_dict["publication_entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")

    # 12. Publication status not ready blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["publication_status"] = "publication_blocked"
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 13. Audit status not verified blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["audit_status"] = "audit_failed"
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 14. Audit report status not verified blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["audit_report_status"] = "audit_report_invalid"
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 15. Nonzero artifact digest mismatch count blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["artifact_digest_mismatch_count"] = 1
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 16. Nonzero artifact validation failure count blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["artifact_validation_failure_count"] = 2
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 17. Target RC not approved blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["target_rc_approved"] = False
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 18. Invalid runtime capability blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["runtime_capability_valid"] = False
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 19. Invalid compiler session registry blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["compiler_session_registry_valid"] = False
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"


def test_allowed_and_blocked_channels():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    with open(pub_manifest_path, "r", encoding="utf-8") as f:
        pub_dict = json.load(f)
    rc1_pub_src = next(e for e in pub_dict["publication_entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")

    # 20. Production deployment in allowed channels blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["publication_channels_allowed"] = ["internal_distribution", "production_deployment"]
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 21. External key signing in allowed channels blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["publication_channels_allowed"] = ["internal_distribution", "external_key_signing"]
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 22. Legal certification claim in allowed channels blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["publication_channels_allowed"] = ["internal_distribution", "legal_certification_claim"]
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 23. Quantum hardware certification in allowed channels blocks distribution readiness.
    bad_entry = dict(rc1_pub_src)
    bad_entry["publication_channels_allowed"] = ["internal_distribution", "quantum_hardware_certification"]
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"

    # 24. Missing software caveat blocks audit.
    bad_entry = dict(rc1_pub_src)
    bad_entry["software_validation_caveat"] = ""
    case = build_waveguide_distribution_readiness_audit_case(bad_entry, pub_manifest_path, registry_path)
    assert case.distribution_readiness_status == "distribution_blocked"


def test_top_level_report():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")

    # 25. Top-level distribution readiness audit report can be built.
    report = build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)
    assert isinstance(report, WaveguideDistributionReadinessAuditReport)

    # 26. Top-level distribution readiness audit report validates.
    ok, reasons = validate_waveguide_distribution_readiness_audit_report(report)
    assert ok is True
    assert report.distribution_audit_report_status == "distribution_readiness_verified"
    assert "DISTRIBUTION_READINESS_VERIFIED" in reasons


def test_report_digest_determinism_and_exclusion():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    report = build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)

    # 27. Distribution audit report digest is deterministic.
    d1 = hash_waveguide_distribution_readiness_audit_report(report)
    d2 = hash_waveguide_distribution_readiness_audit_report(report)
    assert d1 == d2
    assert report.distribution_audit_report_digest == d1

    # 28. distribution_audit_report_digest is excluded from its own digest input.
    r_dict = asdict(report)
    r_dict["distribution_audit_report_digest"] = "DUMMY_SIGNATURE"
    recomputed = hash_waveguide_distribution_readiness_audit_report(r_dict)
    assert recomputed == d1


def test_report_counts_and_sorting():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    report = build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)

    # 29. Distribution-ready count is correct.
    assert report.distribution_ready_count == 2

    # 30. Blocked/pending/invalid counts are zero for clean inputs.
    assert report.distribution_blocked_count == 0
    assert report.distribution_pending_count == 0
    assert report.distribution_invalid_count == 0

    # 31. RC1 distribution count is correct.
    assert report.rc1_distribution_count == 1

    # 32. RC2 distribution count is correct.
    assert report.rc2_distribution_count == 1

    # 33. Distribution-ready RC list is deterministic and sorted.
    assert report.distribution_ready_rcs == ["SOL-WAVEGUIDE-RC1", "SOL-WAVEGUIDE-RC2"]

    # 34. Blocked RC list is deterministic and sorted.
    assert report.distribution_blocked_rcs == []

    # 35. Pending RC list is deterministic and sorted.
    assert report.distribution_pending_rcs == []

    # 36. Invalid RC list is deterministic and sorted.
    assert report.distribution_invalid_rcs == []

    # 37. Candidate levels are deterministic and sorted.
    assert report.candidate_levels_indexed == ["Foundation", "Governed Execution Stack"]

    # 38. Certification bundle IDs are deterministic and sorted.
    assert report.certification_bundle_ids == [
        "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1",
        "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC2"
    ]

    # 39. Certification bundle digests are deterministic and sorted.
    assert len(report.certification_bundle_digests) == 2

    # 40. Audit report digests are deterministic and sorted.
    assert len(report.audit_report_digests) == 2

    # 41. Audit case digests are deterministic and sorted.
    assert len(report.audit_case_digests) == 2

    # 42. Audit registry entry digests are deterministic and sorted.
    assert len(report.audit_registry_entry_digests) == 2

    # 43. Publication entry digests are deterministic and sorted.
    assert len(report.publication_entry_digests) == 2

    # 44. Final output payload digests are deterministic and sorted.
    assert len(report.final_output_payload_digests) == 3


def test_channel_policies_and_metadata():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    report = build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)

    # 45. Allowed channels are deterministic and sorted.
    assert report.allowed_channels_indexed == [
        "artifact_catalog_publication",
        "documentation_publication",
        "internal_distribution"
    ]

    # 46. Blocked channels are deterministic and sorted.
    assert report.blocked_channels_indexed == [
        "external_key_signing",
        "legal_certification_claim",
        "production_deployment",
        "quantum_hardware_certification"
    ]

    # 47. Forbidden channels are confirmed blocked.
    assert report.forbidden_channels_blocked is True

    # 48. Metadata-only channels are confirmed.
    assert report.metadata_only_channels_verified is True


def test_summary_and_export(temp_dir):
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    report = build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)

    # 49. Summary output is deterministic.
    s1 = summarize_waveguide_distribution_readiness_audit_report(report)
    s2 = summarize_waveguide_distribution_readiness_audit_report(report)
    assert s1 == s2
    assert "SOL WAVEGUIDE DISTRIBUTION READINESS AUDIT REPORT" in s1

    # 50. JSON export is deterministic.
    out_file = os.path.join(temp_dir, "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    export_waveguide_distribution_readiness_audit_report(report, out_file)
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["distribution_audit_report_digest"] == report.distribution_audit_report_digest


def test_compare():
    pub_manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    r1 = build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)
    r2 = build_waveguide_distribution_readiness_audit_report(pub_manifest_path, registry_path)

    diff = compare_waveguide_distribution_readiness_audit_reports(r1, r2)
    assert diff["all_match"] is True
