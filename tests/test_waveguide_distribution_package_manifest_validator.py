# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Distribution Package Manifest Validator.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_distribution_package_manifest import (
    hash_waveguide_distribution_package_content_entry,
    hash_waveguide_distribution_package_manifest
)
from sol_waveguide_distribution_package_manifest_validator import (
    WaveguideFinalPackageReadinessAuditCase,
    WaveguideFinalPackageReadinessAuditReport,
    build_waveguide_final_package_readiness_audit_case,
    validate_waveguide_distribution_package_manifest_independently,
    build_waveguide_final_package_readiness_audit_report,
    validate_waveguide_final_package_readiness_audit_report,
    summarize_waveguide_final_package_readiness_audit_report,
    export_waveguide_final_package_readiness_audit_report,
    compare_waveguide_final_package_readiness_audit_reports,
    hash_waveguide_final_package_readiness_audit_case,
    hash_waveguide_final_package_readiness_audit_report,
    recompute_waveguide_distribution_package_manifest_digest,
    recompute_waveguide_package_content_entry_digest,
    validate_waveguide_package_manifest_digest_map,
    validate_waveguide_package_manifest_layout,
    validate_waveguide_package_section_manifests,
    validate_waveguide_blocked_operation_counters,
    index_waveguide_final_package_readiness_cases_by_rc,
    index_waveguide_final_package_readiness_cases_by_status,
    index_waveguide_final_package_readiness_cases_by_section
)


@pytest.fixture
def clean_validator_inputs() -> tuple[dict, dict]:
    manifest_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_MANIFEST.json")
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_DRY_RUN_AUDIT_REPORT.json")
    
    assert os.path.exists(manifest_path), "Missing manifest JSON"
    assert os.path.exists(report_path), "Missing dry-run report JSON"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
        
    return manifest, report


def test_final_audit_cases_building(clean_validator_inputs):
    manifest, report = clean_validator_inputs
    entries = manifest.get("package_contents", [])
    
    # 1. JSON proof final package audit case can be built.
    proof_entry = next(e for e in entries if e.get("target_package_section") == "proof/")
    case_proof = build_waveguide_final_package_readiness_audit_case(proof_entry, manifest, report)
    assert isinstance(case_proof, WaveguideFinalPackageReadinessAuditCase)
    assert case_proof.is_proof_artifact is True
    assert case_proof.final_package_readiness_status == "final_package_content_verified"
    
    # 2. Markdown documentation final package audit case can be built.
    doc_entry = next(e for e in entries if e.get("target_package_section") == "docs/")
    case_doc = build_waveguide_final_package_readiness_audit_case(doc_entry, manifest, report)
    assert isinstance(case_doc, WaveguideFinalPackageReadinessAuditCase)
    assert case_doc.is_documentation_artifact is True
    assert case_doc.final_package_readiness_status == "final_package_content_verified"
    
    # 3. Source module final package audit case can be built.
    src_entry = next(e for e in entries if e.get("target_package_section") == "source/")
    case_src = build_waveguide_final_package_readiness_audit_case(src_entry, manifest, report)
    assert isinstance(case_src, WaveguideFinalPackageReadinessAuditCase)
    assert case_src.is_code_artifact is True
    assert case_src.final_package_readiness_status == "final_package_content_verified"
    
    # 4. Test source final package audit case can be built.
    test_entry = next(e for e in entries if e.get("target_package_section") == "tests/")
    case_test = build_waveguide_final_package_readiness_audit_case(test_entry, manifest, report)
    assert isinstance(case_test, WaveguideFinalPackageReadinessAuditCase)
    assert case_test.is_test_artifact is True
    assert case_test.final_package_readiness_status == "final_package_content_verified"


def test_final_audit_case_digest_determinism_and_exclusion(clean_validator_inputs):
    manifest, report = clean_validator_inputs
    entry = manifest.get("package_contents", [])[0]
    
    # 5. Final package audit case digest is deterministic.
    c1 = build_waveguide_final_package_readiness_audit_case(entry, manifest, report)
    c2 = build_waveguide_final_package_readiness_audit_case(entry, manifest, report)
    assert c1.final_package_audit_case_digest == c2.final_package_audit_case_digest
    assert len(c1.final_package_audit_case_digest) == 64
    
    # 6. final_package_audit_case_digest is excluded from its own digest input.
    c_dict = asdict(c1)
    c_dict["final_package_audit_case_digest"] = "MUTATED_SELF_DIGEST_FOR_EXCLUSION_CHECK"
    recomputed = hash_waveguide_final_package_readiness_audit_case(c_dict)
    assert recomputed == c1.final_package_audit_case_digest


def test_final_audit_failures_and_blocks(clean_validator_inputs):
    manifest, report = clean_validator_inputs
    entry = manifest.get("package_contents", [])[0]
    
    # 7. Package manifest digest mismatch blocks/fails audit.
    bad_manifest = dict(manifest)
    bad_manifest["distribution_package_manifest_digest"] = "mismatched_digest"
    case = build_waveguide_final_package_readiness_audit_case(entry, bad_manifest, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    assert "FINAL_PACKAGE_MANIFEST_DIGEST_MISMATCH" in case.reason_codes
    
    # 8. Package content entry digest mismatch blocks/fails audit.
    bad_entry = dict(entry)
    bad_entry["package_content_entry_digest"] = "mismatched_digest"
    case = build_waveguide_final_package_readiness_audit_case(bad_entry, manifest, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    assert "FINAL_PACKAGE_CONTENT_ENTRY_DIGEST_MISMATCH" in case.reason_codes
    
    # 9. Missing source dry-run audit report blocks audit.
    case = build_waveguide_final_package_readiness_audit_case(entry, manifest, {})
    assert case.final_package_readiness_status == "final_package_content_invalid"
    assert "FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_INVALID" in case.reason_codes
    
    # 10. Source dry-run audit report validation failure blocks audit.
    bad_report = dict(report)
    bad_report["audited_cases"] = []  # invalid report cases
    bad_report["package_dry_run_report_digest"] = "invalid"
    case = build_waveguide_final_package_readiness_audit_case(entry, manifest, bad_report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    
    # 11. Source dry-run audit report digest mismatch blocks audit.
    bad_report_digest = dict(report)
    bad_report_digest["package_dry_run_report_digest"] = "mismatched_digest_value"
    case = build_waveguide_final_package_readiness_audit_case(entry, manifest, bad_report_digest)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    assert "FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_DIGEST_MISMATCH" in case.reason_codes
    
    # 12. Missing dry-run case digest blocks audit.
    bad_entry1 = dict(entry)
    bad_entry1["dry_run_case_digest"] = ""
    bad_entry1["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry1)
    case = build_waveguide_final_package_readiness_audit_case(bad_entry1, manifest, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    
    # 13. Missing layout entry digest blocks audit.
    bad_entry2 = dict(entry)
    bad_entry2["layout_entry_digest"] = ""
    bad_entry2["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry2)
    case = build_waveguide_final_package_readiness_audit_case(bad_entry2, manifest, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    
    # 14. Missing source artifact digest blocks audit.
    bad_entry3 = dict(entry)
    bad_entry3["source_artifact_digest"] = ""
    bad_entry3["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry3)
    case = build_waveguide_final_package_readiness_audit_case(bad_entry3, manifest, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    
    # 15. Unsafe target package path blocks audit.
    bad_entry4 = dict(entry)
    bad_entry4["target_package_path"] = "proof/../../bad.json"
    bad_entry4["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry4)
    case = build_waveguide_final_package_readiness_audit_case(bad_entry4, manifest, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    
    # 16. Package digest map omission blocks audit.
    bad_manifest1 = dict(manifest)
    bad_manifest1["package_digest_map"] = []  # omit
    bad_manifest1["distribution_package_manifest_digest"] = hash_waveguide_distribution_package_manifest(bad_manifest1)
    case = build_waveguide_final_package_readiness_audit_case(entry, bad_manifest1, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    
    # 17. Package layout omission blocks audit.
    bad_manifest2 = dict(manifest)
    bad_manifest2["package_layout"] = {}  # omit
    bad_manifest2["distribution_package_manifest_digest"] = hash_waveguide_distribution_package_manifest(bad_manifest2)
    case = build_waveguide_final_package_readiness_audit_case(entry, bad_manifest2, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    
    # 18. Section manifest omission blocks audit.
    bad_manifest3 = dict(manifest)
    bad_manifest3["proof_artifact_manifest"] = {}  # omit
    bad_manifest3["distribution_package_manifest_digest"] = hash_waveguide_distribution_package_manifest(bad_manifest3)
    case = build_waveguide_final_package_readiness_audit_case(entry, bad_manifest3, report)
    # If the entry was proof section, it fails.
    if entry.get("target_package_section") == "proof/":
        assert case.final_package_readiness_status == "final_package_content_invalid"

    # 19-26. Nonzero attempt counts block audit.
    ops = [
        "archive_creation", "file_copy", "directory_creation",
        "upload", "deployment", "external_signing", "external_publication", "production_mutation"
    ]
    for idx, op in enumerate(ops):
        bad_manifest_op = dict(manifest)
        bad_manifest_op["blocked_operations"] = dict(manifest["blocked_operations"])
        bad_manifest_op["blocked_operations"][op] = 1  # violation
        bad_manifest_op["distribution_package_manifest_digest"] = hash_waveguide_distribution_package_manifest(bad_manifest_op)
        case = build_waveguide_final_package_readiness_audit_case(entry, bad_manifest_op, report)
        assert case.final_package_readiness_status == "final_package_content_invalid"

    # 27. Missing software caveat blocks audit.
    bad_entry_c = dict(entry)
    bad_entry_c["software_validation_caveat"] = ""
    bad_entry_c["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry_c)
    case = build_waveguide_final_package_readiness_audit_case(bad_entry_c, manifest, report)
    assert case.final_package_readiness_status == "final_package_content_invalid"
    assert "FINAL_PACKAGE_SOFTWARE_CAVEAT_INCLUDED" not in case.reason_codes


def test_top_level_final_readiness_report(clean_validator_inputs):
    manifest, report = clean_validator_inputs
    
    # 28. Top-level final package-readiness audit report can be built.
    report_obj = build_waveguide_final_package_readiness_audit_report(manifest, report)
    assert isinstance(report_obj, WaveguideFinalPackageReadinessAuditReport)
    assert report_obj.final_package_readiness_report_status == "final_package_readiness_verified"
    
    # 29. Top-level final package-readiness audit report validates.
    ok, reasons = validate_waveguide_final_package_readiness_audit_report(report_obj)
    assert ok is True
    assert "FINAL_PACKAGE_READINESS_REPORT_DIGEST_VALID" in reasons
    assert "FINAL_PACKAGE_READINESS_VERIFIED" in reasons
    
    # 30. Final package-readiness report digest is deterministic.
    report_obj2 = build_waveguide_final_package_readiness_audit_report(manifest, report)
    assert report_obj.final_package_readiness_report_digest == report_obj2.final_package_readiness_report_digest
    assert len(report_obj.final_package_readiness_report_digest) == 64
    
    # 31. final_package_readiness_report_digest is excluded from its own digest input.
    r_dict = asdict(report_obj)
    r_dict["final_package_readiness_report_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_final_package_readiness_audit_report(r_dict)
    assert recomputed == report_obj.final_package_readiness_report_digest
    
    # 32. Verified final package count is correct.
    assert report_obj.verified_final_package_count == len(manifest.get("package_contents", []))
    
    # 33. Blocked/pending/invalid counts are zero for clean input.
    assert report_obj.blocked_final_package_count == 0
    assert report_obj.pending_final_package_count == 0
    assert report_obj.invalid_final_package_count == 0
    
    # 34. Total final package file count is correct.
    assert report_obj.total_final_package_file_count == len(manifest.get("package_contents", []))
    
    # 35. RC1 final package count is correct.
    assert report_obj.rc1_final_package_count == 6
    
    # 36. RC2 final package count is correct.
    assert report_obj.rc2_final_package_count == 6
    
    # 37. Shared final package count is correct.
    assert report_obj.shared_final_package_count == 16
    
    # 38. Target package sections are deterministic and sorted.
    assert report_obj.target_package_sections == sorted(["docs/", "proof/", "source/", "tests/"])
    
    # 39. Package roles are deterministic and sorted.
    assert report_obj.package_roles_indexed == sorted(list(set(c.source_package_role for c in report_obj.audited_cases)))
    
    # 40. Artifact types are deterministic and sorted.
    assert report_obj.artifact_types_indexed == sorted(list(set(c.source_artifact_type for c in report_obj.audited_cases)))
    
    # 41. Artifact formats are deterministic and sorted.
    assert report_obj.artifact_formats_indexed == sorted(list(set(c.source_artifact_format for c in report_obj.audited_cases)))
    
    # 42. Source artifact paths are deterministic and sorted.
    assert report_obj.source_artifact_paths == sorted(list(set(c.source_artifact_path for c in report_obj.audited_cases)))
    
    # 43. Target package paths are deterministic and sorted.
    assert report_obj.target_package_paths == sorted(list(set(c.target_package_path for c in report_obj.audited_cases)))
    
    # 44. Source artifact digests are deterministic and sorted.
    assert report_obj.source_artifact_digests == sorted(list(set(c.source_artifact_digest for c in report_obj.audited_cases)))
    
    # 45. Layout entry digests are deterministic and sorted.
    assert report_obj.layout_entry_digests == sorted(list(set(c.layout_entry_digest for c in report_obj.audited_cases)))
    
    # 46. Dry-run case digests are deterministic and sorted.
    assert report_obj.dry_run_case_digests == sorted(list(set(c.dry_run_case_digest for c in report_obj.audited_cases)))
    
    # 47. Package content entry digests are deterministic and sorted.
    assert report_obj.package_content_entry_digests == sorted(list(set(c.package_content_entry_digest_recorded for c in report_obj.audited_cases)))
    
    # 48. Final package audit case digests are deterministic and sorted.
    assert report_obj.final_package_audit_case_digests == sorted(list(set(c.final_package_audit_case_digest for c in report_obj.audited_cases)))
    
    # 49. Package digest map is verified.
    assert report_obj.package_digest_map_verified is True
    
    # 50. Package layout is verified.
    assert report_obj.package_layout_verified is True
    
    # 51. Proof artifact manifest is verified.
    assert report_obj.proof_artifact_manifest_verified is True
    
    # 52. Documentation artifact manifest is verified.
    assert report_obj.documentation_artifact_manifest_verified is True
    
    # 53. Source artifact manifest is verified.
    assert report_obj.source_artifact_manifest_verified is True
    
    # 54. Test artifact manifest is verified.
    assert report_obj.test_artifact_manifest_verified is True
    
    # 55. Blocked operations are verified.
    assert report_obj.blocked_operations_verified is True
    
    # 56. All blocked operation attempt counts are zero for clean input.
    assert report_obj.archive_creation_attempt_count == 0
    assert report_obj.file_copy_attempt_count == 0
    assert report_obj.directory_creation_attempt_count == 0
    assert report_obj.upload_attempt_count == 0
    assert report_obj.deployment_attempt_count == 0
    assert report_obj.signing_attempt_count == 0
    assert report_obj.external_publication_attempt_count == 0
    assert report_obj.production_mutation_attempt_count == 0


def test_summary_and_export_determinism(clean_validator_inputs, tmp_path):
    manifest, report = clean_validator_inputs
    report_obj = build_waveguide_final_package_readiness_audit_report(manifest, report)
    
    # 57. Summary output is deterministic.
    s1 = summarize_waveguide_final_package_readiness_audit_report(report_obj)
    s2 = summarize_waveguide_final_package_readiness_audit_report(report_obj)
    assert s1 == s2
    
    # 58. JSON export is deterministic.
    file_path = os.path.join(tmp_path, "final_readiness_report.json")
    export_waveguide_final_package_readiness_audit_report(report_obj, file_path)
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["final_package_readiness_report_digest"] == report_obj.final_package_readiness_report_digest
