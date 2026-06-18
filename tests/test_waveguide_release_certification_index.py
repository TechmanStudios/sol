# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Release Certification Index / RC Audit Registry.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT, hash_file_contents
from sol_waveguide_release_certification_validator import (
    build_waveguide_release_certification_audit_case
)
from sol_waveguide_release_certification_index import (
    build_waveguide_release_certification_index_entry,
    validate_waveguide_release_certification_index_entry,
    build_waveguide_release_certification_index,
    validate_waveguide_release_certification_index,
    summarize_waveguide_release_certification_index,
    export_waveguide_release_certification_index,
    compare_waveguide_release_certification_indexes,
    hash_waveguide_release_certification_index_entry,
    hash_waveguide_release_certification_index,
    index_waveguide_release_certification_entries_by_rc,
    index_waveguide_release_certification_entries_by_status,
    index_waveguide_release_certification_entries_by_candidate_level,
    build_waveguide_release_certification_audit_timeline,
    WaveguideReleaseCertificationIndexEntry,
    WaveguideReleaseCertificationIndex
)


@pytest.fixture
def temp_dir():
    path = os.path.join(REPO_ROOT, "docs", "test_index_temp")
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


def test_rc1_entry_build_and_validation():
    # 1. RC1 audit registry entry can be built.
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    assert os.path.exists(report_path)

    entry = build_waveguide_release_certification_index_entry(report_path)
    assert isinstance(entry, WaveguideReleaseCertificationIndexEntry)
    assert entry.rc_id == "SOL-WAVEGUIDE-RC1"
    assert entry.candidate_level == "Foundation"
    assert entry.audit_report_status == "audit_report_verified"
    assert entry.audit_case_status == "audit_verified"

    # 3. RC1 entry validates as audit_registered.
    ok, reasons = validate_waveguide_release_certification_index_entry(entry)
    assert ok is True
    assert entry.audit_status == "audit_registered"
    assert "RELEASE_CERT_INDEX_AUDIT_REGISTERED" in reasons
    assert "RELEASE_CERT_INDEX_ENTRY_CANONICAL" in reasons


def test_rc2_entry_build_and_validation():
    # 2. RC2 audit registry entry can be built.
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")
    assert os.path.exists(report_path)

    entry = build_waveguide_release_certification_index_entry(report_path)
    assert isinstance(entry, WaveguideReleaseCertificationIndexEntry)
    assert entry.rc_id == "SOL-WAVEGUIDE-RC2"
    assert entry.candidate_level == "Governed Execution Stack"

    # 4. RC2 entry validates as audit_registered.
    ok, reasons = validate_waveguide_release_certification_index_entry(entry)
    assert ok is True
    assert entry.audit_status == "audit_registered"
    assert "RELEASE_CERT_INDEX_AUDIT_REGISTERED" in reasons
    assert "RELEASE_CERT_INDEX_ENTRY_CANONICAL" in reasons


def test_entry_digest_determinism_and_exclusion():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    entry = build_waveguide_release_certification_index_entry(report_path)

    # 5. Registry entry digest is deterministic.
    d1 = hash_waveguide_release_certification_index_entry(entry)
    d2 = hash_waveguide_release_certification_index_entry(entry)
    assert d1 == d2
    assert entry.registry_entry_digest == d1

    # 6. registry_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["registry_entry_digest"] = "different_digest_value"
    d3 = hash_waveguide_release_certification_index_entry(e_dict)
    assert d1 == d3


def test_missing_digests_fail_entry_validation():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    entry = build_waveguide_release_certification_index_entry(report_path)

    # 7. Missing certification bundle digest fails entry validation.
    e_no_bundle = asdict(entry)
    e_no_bundle["certification_bundle_digest"] = ""
    # Recalculate digest to isolate the validation rule
    e_no_bundle["registry_entry_digest"] = hash_waveguide_release_certification_index_entry(e_no_bundle)
    ok, _ = validate_waveguide_release_certification_index_entry(e_no_bundle)
    assert ok is False

    # 8. Missing audit report digest fails entry validation.
    e_no_report = asdict(entry)
    e_no_report["audit_report_digest"] = ""
    e_no_report["registry_entry_digest"] = hash_waveguide_release_certification_index_entry(e_no_report)
    ok, _ = validate_waveguide_release_certification_index_entry(e_no_report)
    assert ok is False

    # 9. Missing audit case digest fails entry validation.
    e_no_case = asdict(entry)
    e_no_case["audit_case_digest"] = ""
    e_no_case["registry_entry_digest"] = hash_waveguide_release_certification_index_entry(e_no_case)
    ok, _ = validate_waveguide_release_certification_index_entry(e_no_case)
    assert ok is False


def test_mismatch_counts_fail_verified_entry_validation():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    entry = build_waveguide_release_certification_index_entry(report_path)

    # 10. Nonzero artifact digest mismatch count fails verified entry validation.
    e_mismatch = asdict(entry)
    e_mismatch["artifact_digest_mismatch_count"] = 1
    e_mismatch["registry_entry_digest"] = hash_waveguide_release_certification_index_entry(e_mismatch)
    ok, _ = validate_waveguide_release_certification_index_entry(e_mismatch)
    assert ok is False

    # 11. Nonzero artifact validation failure count fails verified entry validation.
    e_failure = asdict(entry)
    e_failure["artifact_validation_failure_count"] = 1
    e_failure["registry_entry_digest"] = hash_waveguide_release_certification_index_entry(e_failure)
    ok, _ = validate_waveguide_release_certification_index_entry(e_failure)
    assert ok is False


def test_missing_caveat_fails_entry_validation():
    # 12. Missing software caveat fails entry validation.
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    entry = build_waveguide_release_certification_index_entry(report_path)

    e_no_caveat = asdict(entry)
    e_no_caveat["software_validation_caveat"] = ""
    e_no_caveat["registry_entry_digest"] = hash_waveguide_release_certification_index_entry(e_no_caveat)
    ok, _ = validate_waveguide_release_certification_index_entry(e_no_caveat)
    assert ok is False


def test_top_level_registry_build_and_validation():
    # 13. Top-level audit registry can be built from RC1 and RC2 audit reports.
    report_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    report_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")

    index = build_waveguide_release_certification_index([report_rc1, report_rc2])
    assert isinstance(index, WaveguideReleaseCertificationIndex)
    
    # 14. Top-level audit registry validates.
    ok, reasons = validate_waveguide_release_certification_index(index)
    assert ok is True
    assert index.audit_registry_status == "audit_registry_valid"
    assert "RELEASE_CERT_INDEX_VALID" in reasons
    assert "RELEASE_CERT_INDEX_REGISTRY_DIGEST_VALID" in reasons


def test_registry_digest_determinism_and_exclusion():
    report_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    report_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")

    index = build_waveguide_release_certification_index([report_rc1, report_rc2])

    # 15. Registry digest is deterministic.
    d1 = hash_waveguide_release_certification_index(index)
    d2 = hash_waveguide_release_certification_index(index)
    assert d1 == d2
    assert index.audit_registry_digest == d1

    # 16. audit_registry_digest is excluded from its own digest input.
    i_dict = asdict(index)
    i_dict["audit_registry_digest"] = "different_digest_value"
    d3 = hash_waveguide_release_certification_index(i_dict)
    assert d1 == d3


def test_registry_counts_are_correct():
    report_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    report_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")

    index = build_waveguide_release_certification_index([report_rc1, report_rc2])

    # 17. Registered audit count is correct.
    assert index.registered_audit_count == 2

    # 18. Failed/blocked/invalid counts are zero for clean inputs.
    assert index.failed_audit_count == 0
    assert index.blocked_audit_count == 0
    assert index.invalid_audit_count == 0

    # 19. RC1 audit count is correct.
    assert index.rc1_audit_count == 1

    # 20. RC2 audit count is correct.
    assert index.rc2_audit_count == 1


def test_registry_sorted_lists():
    report_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    report_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")

    index = build_waveguide_release_certification_index([report_rc1, report_rc2])

    # 21. Verified RC list is deterministic and sorted.
    assert index.verified_rcs == ["SOL-WAVEGUIDE-RC1", "SOL-WAVEGUIDE-RC2"]

    # 22. Failed RC list is deterministic and sorted.
    assert index.failed_rcs == []

    # 23. Blocked RC list is deterministic and sorted.
    assert index.blocked_rcs == []

    # 24. Pending RC list is deterministic and sorted.
    # If release registry has RC1 and RC2, pending_rcs should be empty list
    assert index.pending_rcs == []

    # 25. Candidate levels are deterministic and sorted.
    assert index.candidate_levels_indexed == ["Foundation", "Governed Execution Stack"]

    # 26. Certification bundle IDs are deterministic and sorted.
    assert index.certification_bundle_ids == [
        "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC1",
        "SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-RC2"
    ]

    # 27. Certification bundle digests are deterministic and sorted.
    assert index.certification_bundle_digests == sorted(index.certification_bundle_digests)

    # 28. Audit report digests are deterministic and sorted.
    assert index.audit_report_digests == sorted(index.audit_report_digests)

    # 29. Audit case digests are deterministic and sorted.
    assert index.audit_case_digests == sorted(index.audit_case_digests)

    # 30. Final output payload digests are deterministic and sorted.
    assert index.final_output_payload_digests == sorted(index.final_output_payload_digests)


def test_registry_timeline():
    report_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    report_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")

    index = build_waveguide_release_certification_index([report_rc2, report_rc1]) # reverse input order

    # 31. Audit timeline is deterministic.
    timeline1 = build_waveguide_release_certification_audit_timeline(index.entries)
    timeline2 = build_waveguide_release_certification_audit_timeline(index.entries)
    assert timeline1 == timeline2

    # 32. Audit timeline orders RC1 before RC2.
    assert index.audit_timeline[0]["rc_id"] == "SOL-WAVEGUIDE-RC1"
    assert index.audit_timeline[1]["rc_id"] == "SOL-WAVEGUIDE-RC2"
    assert index.audit_timeline[0]["timeline_index"] == 1
    assert index.audit_timeline[1]["timeline_index"] == 2


def test_summary_and_export_determinism(temp_dir):
    report_rc1 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json")
    report_rc2 = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json")

    index = build_waveguide_release_certification_index([report_rc1, report_rc2])

    # 33. Summary output is deterministic.
    s1 = summarize_waveguide_release_certification_index(index)
    s2 = summarize_waveguide_release_certification_index(index)
    assert s1 == s2
    assert "SOL WAVEGUIDE RELEASE CERTIFICATION INDEX SUMMARY" in s1

    # 34. JSON export is deterministic.
    exp1 = os.path.join(temp_dir, "index1.json")
    exp2 = os.path.join(temp_dir, "index2.json")

    export_waveguide_release_certification_index(index, exp1)
    export_waveguide_release_certification_index(index, exp2)

    with open(exp1, "r") as f1, open(exp2, "r") as f2:
        content1 = f1.read()
        content2 = f2.read()

    assert content1 == content2


def test_artifacts_exist():
    # 35. Release certification index JSON artifact exists.
    p_index = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json")
    assert os.path.exists(p_index)

    # 36. Release certification index documentation exists.
    p_doc = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.md")
    assert os.path.exists(p_doc)
