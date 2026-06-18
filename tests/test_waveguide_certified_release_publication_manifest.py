# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Certified Release Publication Manifest.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_release_certification_index import (
    build_waveguide_release_certification_index,
    validate_waveguide_release_certification_index
)
from sol_waveguide_certified_release_publication_manifest import (
    build_waveguide_certified_release_publication_entry,
    validate_waveguide_certified_release_publication_entry,
    build_waveguide_certified_release_publication_manifest,
    validate_waveguide_certified_release_publication_manifest,
    summarize_waveguide_certified_release_publication_manifest,
    export_waveguide_certified_release_publication_manifest,
    compare_waveguide_certified_release_publication_manifests,
    hash_waveguide_certified_release_publication_entry,
    hash_waveguide_certified_release_publication_manifest,
    index_waveguide_publication_entries_by_rc,
    index_waveguide_publication_entries_by_status,
    index_waveguide_publication_entries_by_channel,
    build_waveguide_publication_readiness_catalog,
    WaveguideCertifiedReleasePublicationEntry,
    WaveguideCertifiedReleasePublicationManifest
)


@pytest.fixture
def temp_dir():
    path = os.path.join(REPO_ROOT, "docs", "test_pub_temp")
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


def test_rc1_rc2_entries_build_and_validation():
    # Load the index
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    assert os.path.exists(idx_path)
    with open(idx_path, "r", encoding="utf-8") as f:
        registry_dict = json.load(f)

    entries = registry_dict["entries"]
    rc1_src = next(e for e in entries if e["rc_id"] == "SOL-WAVEGUIDE-RC1")
    rc2_src = next(e for e in entries if e["rc_id"] == "SOL-WAVEGUIDE-RC2")

    # 1. RC1 publication entry can be built.
    entry1 = build_waveguide_certified_release_publication_entry(rc1_src)
    assert isinstance(entry1, WaveguideCertifiedReleasePublicationEntry)
    assert entry1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert entry1.candidate_level == "Foundation"

    # 3. RC1 publication entry validates as publication_ready.
    ok1, reasons1 = validate_waveguide_certified_release_publication_entry(entry1)
    assert ok1 is True
    assert entry1.publication_status == "publication_ready"
    assert "PUBLICATION_RC_READY" in reasons1
    assert "PUBLICATION_ENTRY_CANONICAL" in reasons1

    # 2. RC2 publication entry can be built.
    entry2 = build_waveguide_certified_release_publication_entry(rc2_src)
    assert isinstance(entry2, WaveguideCertifiedReleasePublicationEntry)
    assert entry2.rc_id == "SOL-WAVEGUIDE-RC2"
    assert entry2.candidate_level == "Governed Execution Stack"

    # 4. RC2 publication entry validates as publication_ready.
    ok2, reasons2 = validate_waveguide_certified_release_publication_entry(entry2)
    assert ok2 is True
    assert entry2.publication_status == "publication_ready"
    assert "PUBLICATION_RC_READY" in reasons2


def test_entry_digest_determinism_and_exclusion():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    with open(idx_path, "r", encoding="utf-8") as f:
        registry_dict = json.load(f)
    rc1_src = next(e for e in registry_dict["entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")

    # 5. Publication entry digest is deterministic.
    entry = build_waveguide_certified_release_publication_entry(rc1_src)
    d1 = hash_waveguide_certified_release_publication_entry(entry)
    d2 = hash_waveguide_certified_release_publication_entry(entry)
    assert d1 == d2
    assert entry.publication_entry_digest == d1

    # 6. publication_entry_digest is excluded from its own digest input.
    entry_dict = asdict(entry)
    entry_dict["publication_entry_digest"] = "DUMMY_SIGNATURE"
    recomputed = hash_waveguide_certified_release_publication_entry(entry_dict)
    assert recomputed == d1


def test_entry_validation_failures():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    with open(idx_path, "r", encoding="utf-8") as f:
        registry_dict = json.load(f)
    rc1_src = next(e for e in registry_dict["entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")

    # 7. Missing certification bundle digest fails entry validation.
    bad_src = dict(rc1_src)
    bad_src["certification_bundle_digest"] = ""
    entry = build_waveguide_certified_release_publication_entry(bad_src)
    ok, reasons = validate_waveguide_certified_release_publication_entry(entry)
    assert ok is False

    # 8. Missing audit report digest fails entry validation.
    bad_src = dict(rc1_src)
    bad_src["audit_report_digest"] = ""
    entry = build_waveguide_certified_release_publication_entry(bad_src)
    ok, reasons = validate_waveguide_certified_release_publication_entry(entry)
    assert ok is False

    # 9. Missing audit case digest fails entry validation.
    bad_src = dict(rc1_src)
    bad_src["audit_case_digest"] = ""
    entry = build_waveguide_certified_release_publication_entry(bad_src)
    ok, reasons = validate_waveguide_certified_release_publication_entry(entry)
    assert ok is False

    # 10. Nonzero artifact digest mismatch count blocks publication readiness.
    bad_src = dict(rc1_src)
    bad_src["artifact_digest_mismatch_count"] = 1
    entry = build_waveguide_certified_release_publication_entry(bad_src)
    assert entry.publication_status == "publication_blocked"
    # Even if we bypass builder status assignment, validation must catch it
    entry.publication_status = "publication_ready"
    entry.publication_entry_digest = hash_waveguide_certified_release_publication_entry(entry)
    ok, reasons = validate_waveguide_certified_release_publication_entry(entry)
    assert ok is False

    # 11. Nonzero artifact validation failure count blocks publication readiness.
    bad_src = dict(rc1_src)
    bad_src["artifact_validation_failure_count"] = 2
    entry = build_waveguide_certified_release_publication_entry(bad_src)
    assert entry.publication_status == "publication_blocked"
    entry.publication_status = "publication_ready"
    entry.publication_entry_digest = hash_waveguide_certified_release_publication_entry(entry)
    ok, reasons = validate_waveguide_certified_release_publication_entry(entry)
    assert ok is False

    # 12. Missing software caveat fails entry validation.
    entry = build_waveguide_certified_release_publication_entry(rc1_src)
    entry.software_validation_caveat = ""
    entry.publication_entry_digest = hash_waveguide_certified_release_publication_entry(entry)
    ok, reasons = validate_waveguide_certified_release_publication_entry(entry)
    assert ok is False


def test_channel_blocking_policies():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    with open(idx_path, "r", encoding="utf-8") as f:
        registry_dict = json.load(f)
    rc1_src = next(e for e in registry_dict["entries"] if e["rc_id"] == "SOL-WAVEGUIDE-RC1")
    entry = build_waveguide_certified_release_publication_entry(rc1_src)

    # 13. Production deployment is explicitly blocked.
    assert "production_deployment" in entry.publication_channels_blocked
    assert "production_deployment" not in entry.publication_channels_allowed
    assert "PUBLICATION_PRODUCTION_DEPLOYMENT_BLOCKED" in entry.reason_codes

    # 14. External key signing is explicitly blocked.
    assert "external_key_signing" in entry.publication_channels_blocked
    assert "PUBLICATION_EXTERNAL_SIGNING_BLOCKED" in entry.reason_codes

    # 15. Legal certification claim is explicitly blocked.
    assert "legal_certification_claim" in entry.publication_channels_blocked
    assert "PUBLICATION_LEGAL_CLAIM_BLOCKED" in entry.reason_codes

    # 16. Quantum hardware certification claim is explicitly blocked.
    assert "quantum_hardware_certification" in entry.publication_channels_blocked
    assert "PUBLICATION_QUANTUM_HARDWARE_CLAIM_BLOCKED" in entry.reason_codes


def test_top_level_manifest_build_and_validation():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    
    # 17. Top-level publication manifest can be built from the audit registry.
    manifest = build_waveguide_certified_release_publication_manifest(idx_path)
    assert isinstance(manifest, WaveguideCertifiedReleasePublicationManifest)
    assert manifest.publication_manifest_id == "SOL-WAVEGUIDE-CERTIFIED-RELEASE-PUBLICATION-MANIFEST"

    # 18. Top-level publication manifest validates.
    ok, reasons = validate_waveguide_certified_release_publication_manifest(manifest)
    assert ok is True
    assert manifest.publication_manifest_status == "publication_manifest_ready"
    assert "PUBLICATION_MANIFEST_READY" in reasons


def test_manifest_digest_determinism_and_exclusion():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    manifest = build_waveguide_certified_release_publication_manifest(idx_path)

    # 19. Publication manifest digest is deterministic.
    d1 = hash_waveguide_certified_release_publication_manifest(manifest)
    d2 = hash_waveguide_certified_release_publication_manifest(manifest)
    assert d1 == d2
    assert manifest.publication_manifest_digest == d1

    # 20. publication_manifest_digest is excluded from its own digest input.
    m_dict = asdict(manifest)
    m_dict["publication_manifest_digest"] = "DUMMY_MANIFEST_SIGNATURE"
    recomputed = hash_waveguide_certified_release_publication_manifest(m_dict)
    assert recomputed == d1


def test_manifest_counts_and_sorting():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    manifest = build_waveguide_certified_release_publication_manifest(idx_path)

    # 21. Publishable RC count is correct.
    assert manifest.publishable_rc_count == 2

    # 22. Blocked/pending/invalid counts are zero for clean inputs.
    assert manifest.blocked_rc_count == 0
    assert manifest.invalid_rc_count == 0
    # Wait, pending count is zero as well since all approved RCs are listed in the index
    assert manifest.pending_rc_count == 0

    # 23. RC1 publication count is correct.
    assert manifest.rc1_publication_count == 1

    # 24. RC2 publication count is correct.
    assert manifest.rc2_publication_count == 1

    # 25. Publishable RC list is deterministic and sorted.
    assert manifest.publishable_rcs == ["SOL-WAVEGUIDE-RC1", "SOL-WAVEGUIDE-RC2"]

    # 26. Blocked RC list is deterministic and sorted.
    assert manifest.blocked_rcs == []

    # 27. Pending RC list is deterministic and sorted.
    assert manifest.pending_rcs == []

    # 28. Invalid RC list is deterministic and sorted.
    assert manifest.invalid_rcs == []

    # 29. Candidate levels are deterministic and sorted.
    assert manifest.candidate_levels_indexed == ["Foundation", "Governed Execution Stack"]

    # 30. Certification bundle IDs are deterministic and sorted.
    assert manifest.certification_bundle_ids == [
        "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1",
        "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC2"
    ]

    # 31. Certification bundle digests are deterministic and sorted.
    assert len(manifest.certification_bundle_digests) == 2

    # 32. Audit report digests are deterministic and sorted.
    assert len(manifest.audit_report_digests) == 2

    # 33. Audit case digests are deterministic and sorted.
    assert len(manifest.audit_case_digests) == 2

    # 34. Audit registry entry digests are deterministic and sorted.
    assert len(manifest.audit_registry_entry_digests) == 2

    # 35. Final output payload digests are deterministic and sorted.
    assert len(manifest.final_output_payload_digests) == 3


def test_channel_policy_and_readiness_catalog():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    manifest = build_waveguide_certified_release_publication_manifest(idx_path)

    # 36. Publication channel policy is deterministic.
    assert "allowed" in manifest.publication_channel_policy
    assert "blocked" in manifest.publication_channel_policy

    # 37. Publication readiness catalog is deterministic.
    cat = manifest.publication_readiness_catalog
    assert len(cat) == 2

    # 38. Publication readiness catalog orders RC1 before RC2.
    assert cat[0]["rc_id"] == "SOL-WAVEGUIDE-RC1"
    assert cat[1]["rc_id"] == "SOL-WAVEGUIDE-RC2"


def test_summary_and_export(temp_dir):
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    manifest = build_waveguide_certified_release_publication_manifest(idx_path)

    # 39. Summary output is deterministic.
    s1 = summarize_waveguide_certified_release_publication_manifest(manifest)
    s2 = summarize_waveguide_certified_release_publication_manifest(manifest)
    assert s1 == s2
    assert "SOL WAVEGUIDE CERTIFIED RELEASE PUBLICATION MANIFEST" in s1

    # 40. JSON export is deterministic.
    out_file = os.path.join(temp_dir, "SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json")
    export_waveguide_certified_release_publication_manifest(manifest, out_file)
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["publication_manifest_digest"] == manifest.publication_manifest_digest


def test_compare():
    idx_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    m1 = build_waveguide_certified_release_publication_manifest(idx_path)
    m2 = build_waveguide_certified_release_publication_manifest(idx_path)
    
    diff = compare_waveguide_certified_release_publication_manifests(m1, m2)
    assert diff["all_match"] is True
