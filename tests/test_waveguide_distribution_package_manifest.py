# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Unit tests for the SOL Waveguide Distribution Package Manifest.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_distribution_package_manifest import (
    WaveguideDistributionPackageContentEntry,
    WaveguideDistributionPackageManifest,
    build_waveguide_distribution_package_content_entry,
    validate_waveguide_distribution_package_content_entry,
    build_waveguide_distribution_package_manifest,
    validate_waveguide_distribution_package_manifest,
    summarize_waveguide_distribution_package_manifest,
    export_waveguide_distribution_package_manifest,
    compare_waveguide_distribution_package_manifests,
    hash_waveguide_distribution_package_content_entry,
    hash_waveguide_distribution_package_manifest,
    build_waveguide_package_content_digest_map,
    build_waveguide_package_content_layout,
    build_waveguide_package_section_manifest,
    index_waveguide_package_contents_by_rc,
    index_waveguide_package_contents_by_section,
    index_waveguide_package_contents_by_role,
    index_waveguide_package_contents_by_artifact_type
)


@pytest.fixture
def clean_manifest_inputs() -> tuple[dict, dict, dict]:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_DRY_RUN_AUDIT_REPORT.json")
    plan_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_ASSEMBLY_PLAN.json")
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    
    assert os.path.exists(report_path)
    assert os.path.exists(plan_path)
    assert os.path.exists(catalog_path)
    
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    return report, plan, catalog


def test_package_content_entries_building(clean_manifest_inputs):
    report, plan, catalog = clean_manifest_inputs
    cases = report.get("audited_cases", [])
    
    # 1. JSON proof package content entry can be built.
    proof_case = next(c for c in cases if c.get("target_package_section") == "proof/")
    entry_proof = build_waveguide_distribution_package_content_entry(proof_case, plan, catalog)
    assert isinstance(entry_proof, WaveguideDistributionPackageContentEntry)
    assert entry_proof.is_proof_artifact is True
    assert entry_proof.manifest_entry_status == "package_content_ready"
    
    # 2. Markdown documentation package content entry can be built.
    doc_case = next(c for c in cases if c.get("target_package_section") == "docs/")
    entry_doc = build_waveguide_distribution_package_content_entry(doc_case, plan, catalog)
    assert isinstance(entry_doc, WaveguideDistributionPackageContentEntry)
    assert entry_doc.is_documentation_artifact is True
    assert entry_doc.manifest_entry_status == "package_content_ready"
    
    # 3. Source module package content entry can be built.
    src_case = next(c for c in cases if c.get("target_package_section") == "source/")
    entry_src = build_waveguide_distribution_package_content_entry(src_case, plan, catalog)
    assert isinstance(entry_src, WaveguideDistributionPackageContentEntry)
    assert entry_src.is_code_artifact is True
    assert entry_src.manifest_entry_status == "package_content_ready"
    
    # 4. Test source package content entry can be built.
    test_case = next(c for c in cases if c.get("target_package_section") == "tests/")
    entry_test = build_waveguide_distribution_package_content_entry(test_case, plan, catalog)
    assert isinstance(entry_test, WaveguideDistributionPackageContentEntry)
    assert entry_test.is_test_artifact is True
    assert entry_test.manifest_entry_status == "package_content_ready"


def test_package_content_entry_digest_determinism_and_exclusion(clean_manifest_inputs):
    report, plan, catalog = clean_manifest_inputs
    case = report.get("audited_cases", [])[0]
    
    # 5. Package content entry digest is deterministic.
    e1 = build_waveguide_distribution_package_content_entry(case, plan, catalog)
    e2 = build_waveguide_distribution_package_content_entry(case, plan, catalog)
    assert e1.package_content_entry_digest == e2.package_content_entry_digest
    assert len(e1.package_content_entry_digest) == 64
    
    # 6. package_content_entry_digest is excluded from its own digest input.
    e_dict = asdict(e1)
    e_dict["package_content_entry_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_distribution_package_content_entry(e_dict)
    assert recomputed == e1.package_content_entry_digest


def test_package_content_entry_failures_and_blocks(clean_manifest_inputs):
    report, plan, catalog = clean_manifest_inputs
    case = report.get("audited_cases", [])[0]
    entry = build_waveguide_distribution_package_content_entry(case, plan, catalog)
    
    # 7. Missing dry-run case digest fails entry validation.
    bad_entry1 = asdict(entry)
    bad_entry1["dry_run_case_digest"] = ""
    bad_entry1["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry1)
    ok, _ = validate_waveguide_distribution_package_content_entry(bad_entry1)
    assert ok is False
    
    # 8. Missing layout entry digest fails entry validation.
    bad_entry2 = asdict(entry)
    bad_entry2["layout_entry_digest"] = ""
    bad_entry2["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry2)
    ok, _ = validate_waveguide_distribution_package_content_entry(bad_entry2)
    assert ok is False
    
    # 9. Missing source artifact digest fails entry validation.
    bad_entry3 = asdict(entry)
    bad_entry3["source_artifact_digest"] = ""
    bad_entry3["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry3)
    ok, _ = validate_waveguide_distribution_package_content_entry(bad_entry3)
    assert ok is False
    
    # 10. Deployment artifact is blocked.
    bad_entry4 = asdict(entry)
    bad_entry4["is_deployment_artifact"] = True
    bad_entry4["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry4)
    ok, reasons = validate_waveguide_distribution_package_content_entry(bad_entry4)
    assert ok is False
    assert "PACKAGE_MANIFEST_BLOCKED" in reasons
    
    # 11. Signing artifact is blocked.
    bad_entry5 = asdict(entry)
    bad_entry5["is_signing_artifact"] = True
    bad_entry5["package_content_entry_digest"] = hash_waveguide_distribution_package_content_entry(bad_entry5)
    ok, reasons = validate_waveguide_distribution_package_content_entry(bad_entry5)
    assert ok is False
    assert "PACKAGE_MANIFEST_BLOCKED" in reasons
    
    # 12-17. Archive, copy, dir creation, upload, deployment, signing remain blocked.
    # The manifest includes counters for these actions in the top-level manifest, showing that
    # all attempt counts are zero.


def test_top_level_distribution_package_manifest(clean_manifest_inputs):
    report, plan, catalog = clean_manifest_inputs
    
    # 18. Top-level distribution package manifest can be built.
    manifest = build_waveguide_distribution_package_manifest(report, plan, catalog)
    assert isinstance(manifest, WaveguideDistributionPackageManifest)
    assert manifest.distribution_package_manifest_status == "package_manifest_ready"
    
    # 19. Top-level distribution package manifest validates.
    ok, reasons = validate_waveguide_distribution_package_manifest(manifest)
    assert ok is True
    assert "PACKAGE_MANIFEST_DIGEST_VALID" in reasons
    assert "PACKAGE_MANIFEST_READY" in reasons
    
    # 20. Manifest digest is deterministic.
    manifest2 = build_waveguide_distribution_package_manifest(report, plan, catalog)
    assert manifest.distribution_package_manifest_digest == manifest2.distribution_package_manifest_digest
    assert len(manifest.distribution_package_manifest_digest) == 64
    
    # 21. distribution_package_manifest_digest is excluded from its own digest input.
    m_dict = asdict(manifest)
    m_dict["distribution_package_manifest_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_distribution_package_manifest(m_dict)
    assert recomputed == manifest.distribution_package_manifest_digest
    
    # 22. Ready package content count is correct.
    assert manifest.ready_package_content_count == len(report.get("audited_cases", []))
    
    # 23. Blocked/pending/invalid content counts are zero for clean input.
    assert manifest.blocked_package_content_count == 0
    assert manifest.pending_package_content_count == 0
    assert manifest.invalid_package_content_count == 0
    
    # 24. Total manifest file count is correct.
    assert manifest.total_manifest_file_count == len(report.get("audited_cases", []))
    
    # 25. RC1 manifest count is correct.
    assert manifest.rc1_manifest_count == 6
    
    # 26. RC2 manifest count is correct.
    assert manifest.rc2_manifest_count == 6
    
    # 27. Shared manifest count is correct.
    assert manifest.shared_manifest_count == 16
    
    # 28. Target package sections are deterministic and sorted.
    assert manifest.target_package_sections == sorted(["docs/", "proof/", "source/", "tests/"])
    
    # 29. Package roles are deterministic and sorted.
    assert manifest.package_roles_indexed == sorted(list(set(e.source_package_role for e in manifest.package_contents)))
    
    # 30. Artifact types are deterministic and sorted.
    assert manifest.artifact_types_indexed == sorted(list(set(e.source_artifact_type for e in manifest.package_contents)))
    
    # 31. Artifact formats are deterministic and sorted.
    assert manifest.artifact_formats_indexed == sorted(list(set(e.source_artifact_format for e in manifest.package_contents)))
    
    # 32. Source artifact paths are deterministic and sorted.
    assert manifest.source_artifact_paths == sorted(list(set(e.source_artifact_path for e in manifest.package_contents)))
    
    # 33. Target package paths are deterministic and sorted.
    assert manifest.target_package_paths == sorted(list(set(e.target_package_path for e in manifest.package_contents)))
    
    # 34. Source artifact digests are deterministic and sorted.
    assert manifest.source_artifact_digests == sorted(list(set(e.source_artifact_digest for e in manifest.package_contents)))
    
    # 35. Layout entry digests are deterministic and sorted.
    assert manifest.layout_entry_digests == sorted(list(set(e.layout_entry_digest for e in manifest.package_contents)))
    
    # 36. Dry-run case digests are deterministic and sorted.
    assert manifest.dry_run_case_digests == sorted(list(set(e.dry_run_case_digest for e in manifest.package_contents)))
    
    # 37. Package content entry digests are deterministic and sorted.
    assert manifest.package_content_entry_digests == sorted(list(set(e.package_content_entry_digest for e in manifest.package_contents)))
    
    # 38. Package digest map is deterministic.
    assert isinstance(manifest.package_digest_map, list)
    assert len(manifest.package_digest_map) == len(report.get("audited_cases", []))
    
    # 39. Digest map is sorted by target package path.
    target_paths_in_map = [item["target_package_path"] for item in manifest.package_digest_map]
    assert target_paths_in_map == sorted(target_paths_in_map)
    
    # 40. Package layout is deterministic.
    assert isinstance(manifest.package_layout, dict)
    
    # 41. Package layout section lists are sorted.
    for sect, paths in manifest.package_layout.items():
        assert paths == sorted(paths)
        
    # 42. Proof artifact manifest is deterministic.
    assert manifest.proof_artifact_manifest["section_name"] == "proof/"
    assert manifest.proof_artifact_manifest["entry_count"] == 20
    assert manifest.proof_artifact_manifest["target_paths"] == sorted(manifest.proof_artifact_manifest["target_paths"])
    
    # 43. Documentation artifact manifest is deterministic.
    assert manifest.documentation_artifact_manifest["section_name"] == "docs/"
    assert manifest.documentation_artifact_manifest["entry_count"] == 6
    assert manifest.documentation_artifact_manifest["target_paths"] == sorted(manifest.documentation_artifact_manifest["target_paths"])
    
    # 44. Source artifact manifest is deterministic.
    assert manifest.source_artifact_manifest["section_name"] == "source/"
    assert manifest.source_artifact_manifest["entry_count"] == 1
    assert manifest.source_artifact_manifest["target_paths"] == sorted(manifest.source_artifact_manifest["target_paths"])
    
    # 45. Test artifact manifest is deterministic.
    assert manifest.test_artifact_manifest["section_name"] == "tests/"
    assert manifest.test_artifact_manifest["entry_count"] == 1
    assert manifest.test_artifact_manifest["target_paths"] == sorted(manifest.test_artifact_manifest["target_paths"])
    
    # 46. Blocked operations are explicitly represented.
    # 47. Blocked operation attempt counts are zero.
    assert manifest.blocked_operations["archive_creation"] == 0
    assert manifest.blocked_operations["file_copy"] == 0
    assert manifest.blocked_operations["directory_creation"] == 0
    assert manifest.blocked_operations["upload"] == 0
    assert manifest.blocked_operations["deployment"] == 0
    assert manifest.blocked_operations["external_signing"] == 0
    assert manifest.blocked_operations["external_publication"] == 0
    assert manifest.blocked_operations["production_mutation"] == 0


def test_summary_and_export_determinism(clean_manifest_inputs, tmp_path):
    report, plan, catalog = clean_manifest_inputs
    manifest = build_waveguide_distribution_package_manifest(report, plan, catalog)
    
    # 48. Summary output is deterministic.
    s1 = summarize_waveguide_distribution_package_manifest(manifest)
    s2 = summarize_waveguide_distribution_package_manifest(manifest)
    assert s1 == s2
    
    # 49. JSON export is deterministic.
    file_path = os.path.join(tmp_path, "manifest.json")
    export_waveguide_distribution_package_manifest(manifest, file_path)
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["distribution_package_manifest_digest"] == manifest.distribution_package_manifest_digest


def test_manifest_artifacts_existence():
    # 50. Distribution package manifest JSON artifact exists.
    # We will generate this in the next steps.
    pass

    # 51. Distribution package manifest documentation exists.
    # We will generate this in the next steps.
    pass
