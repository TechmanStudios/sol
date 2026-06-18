# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Certified Artifact Catalog / Distribution Package Index.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_certified_artifact_catalog import (
    build_waveguide_certified_artifact_catalog_entry,
    validate_waveguide_certified_artifact_catalog_entry,
    build_waveguide_certified_artifact_catalog,
    validate_waveguide_certified_artifact_catalog,
    summarize_waveguide_certified_artifact_catalog,
    export_waveguide_certified_artifact_catalog,
    compare_waveguide_certified_artifact_catalogs,
    hash_waveguide_certified_artifact_catalog_entry,
    hash_waveguide_certified_artifact_catalog,
    compute_waveguide_catalog_artifact_digest,
    index_waveguide_catalog_entries_by_rc,
    index_waveguide_catalog_entries_by_artifact_type,
    index_waveguide_catalog_entries_by_package_role,
    index_waveguide_catalog_entries_by_distribution_status,
    build_waveguide_distribution_package_inventory,
    WaveguideCertifiedArtifactCatalogEntry,
    WaveguideCertifiedArtifactCatalog
)


@pytest.fixture
def temp_dir():
    path = os.path.join(REPO_ROOT, "docs", "test_catalog_temp")
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


def test_catalog_entries_build_and_validation():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    assert os.path.exists(report_path)

    # 1. JSON proof artifact catalog entry can be built.
    entry_json = build_waveguide_certified_artifact_catalog_entry("docs/SOL_WAVEGUIDE_RC1_MANIFEST.json", report_path, "RC1")
    assert isinstance(entry_json, WaveguideCertifiedArtifactCatalogEntry)
    assert entry_json.artifact_format == "json"
    assert entry_json.is_proof_artifact is True
    assert entry_json.distribution_status == "artifact_distribution_ready"
    ok1, r1 = validate_waveguide_certified_artifact_catalog_entry(entry_json)
    assert ok1 is True

    # 2. Markdown documentation artifact catalog entry can be built.
    entry_md = build_waveguide_certified_artifact_catalog_entry("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE.md", report_path, "Shared")
    assert isinstance(entry_md, WaveguideCertifiedArtifactCatalogEntry)
    assert entry_md.artifact_format == "markdown"
    assert entry_md.is_documentation_artifact is True
    ok2, r2 = validate_waveguide_certified_artifact_catalog_entry(entry_md)
    assert ok2 is True

    # 3. Source module artifact catalog entry can be built.
    entry_src = build_waveguide_certified_artifact_catalog_entry("tools/sol-core/sol_waveguide_certified_artifact_catalog.py", report_path, "Shared")
    assert isinstance(entry_src, WaveguideCertifiedArtifactCatalogEntry)
    assert entry_src.artifact_format == "python"
    assert entry_src.is_code_artifact is True
    assert entry_src.package_role == "implementation_source"
    ok3, r3 = validate_waveguide_certified_artifact_catalog_entry(entry_src)
    assert ok3 is True

    # 4. Test source artifact catalog entry can be built.
    entry_test = build_waveguide_certified_artifact_catalog_entry("tests/test_waveguide_certified_artifact_catalog.py", report_path, "Shared")
    assert isinstance(entry_test, WaveguideCertifiedArtifactCatalogEntry)
    assert entry_test.artifact_format == "python"
    assert entry_test.package_role == "test_source"
    ok4, r4 = validate_waveguide_certified_artifact_catalog_entry(entry_test)
    assert ok4 is True


def test_entry_digest_determinism_and_exclusion():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    entry = build_waveguide_certified_artifact_catalog_entry("docs/SOL_WAVEGUIDE_RC1_MANIFEST.json", report_path)

    # 5. Catalog entry digest is deterministic.
    d1 = hash_waveguide_certified_artifact_catalog_entry(entry)
    d2 = hash_waveguide_certified_artifact_catalog_entry(entry)
    assert d1 == d2
    assert entry.artifact_catalog_entry_digest == d1

    # 6. artifact_catalog_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["artifact_catalog_entry_digest"] = "DUMMY_ENTRY_SIGNATURE"
    recomputed = hash_waveguide_certified_artifact_catalog_entry(e_dict)
    assert recomputed == d1


def test_entry_validation_failures():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")

    # 7. Missing artifact path blocks or invalidates entry.
    entry = build_waveguide_certified_artifact_catalog_entry("docs/SOL_WAVEGUIDE_RC1_MANIFEST.json", report_path)
    entry.artifact_path = ""
    entry.artifact_catalog_entry_digest = hash_waveguide_certified_artifact_catalog_entry(entry)
    ok, reasons = validate_waveguide_certified_artifact_catalog_entry(entry)
    assert ok is False

    # 8. Artifact digest mismatch blocks or invalidates entry.
    entry = build_waveguide_certified_artifact_catalog_entry("docs/SOL_WAVEGUIDE_RC1_MANIFEST.json", report_path)
    entry.artifact_digest = "mismatch"
    entry.artifact_catalog_entry_digest = hash_waveguide_certified_artifact_catalog_entry(entry)
    ok, reasons = validate_waveguide_certified_artifact_catalog_entry(entry)
    assert ok is False


def test_blocked_deployment_and_signing_artifacts():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")

    # 9. Deployment artifact is blocked.
    # We pass a path containing deployment marker to trigger deployment classification
    entry_dep = build_waveguide_certified_artifact_catalog_entry("docs/deploy_manifest.json", report_path)
    assert entry_dep.is_deployment_artifact is True
    assert entry_dep.distribution_status == "artifact_distribution_blocked"
    assert "ARTIFACT_CATALOG_DEPLOYMENT_BLOCKED" in entry_dep.reason_codes

    # 10. External signing artifact is blocked.
    entry_sign = build_waveguide_certified_artifact_catalog_entry("docs/signing_keys.json", report_path)
    assert entry_sign.is_signing_artifact is True
    assert entry_sign.distribution_status == "artifact_distribution_blocked"
    assert "ARTIFACT_CATALOG_EXTERNAL_SIGNING_BLOCKED" in entry_sign.reason_codes

    # 11. Allowed channels are metadata-only.
    assert "production_deployment" not in entry_dep.allowed_distribution_channels
    assert "external_key_signing" not in entry_dep.allowed_distribution_channels

    # 12. Forbidden channels remain blocked.
    assert "production_deployment" in entry_dep.blocked_distribution_channels
    assert "external_key_signing" in entry_dep.blocked_distribution_channels


def test_top_level_catalog():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")

    # 13. Top-level artifact catalog can be built.
    catalog = build_waveguide_certified_artifact_catalog(report_path)
    assert isinstance(catalog, WaveguideCertifiedArtifactCatalog)

    # 14. Top-level artifact catalog validates.
    ok, reasons = validate_waveguide_certified_artifact_catalog(catalog)
    # The self-referential json catalog doesn't exist yet during build_waveguide_certified_artifact_catalog,
    # so its status is pending, but since pending doesn't fail overall catalog validation, this should be valid!
    assert ok is True
    assert catalog.artifact_catalog_status == "artifact_catalog_valid"


def test_catalog_digest_determinism_and_exclusion():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    catalog = build_waveguide_certified_artifact_catalog(report_path)

    # 15. Catalog digest is deterministic.
    d1 = hash_waveguide_certified_artifact_catalog(catalog)
    d2 = hash_waveguide_certified_artifact_catalog(catalog)
    assert d1 == d2
    assert catalog.artifact_catalog_digest == d1

    # 16. artifact_catalog_digest is excluded from its own digest input.
    c_dict = asdict(catalog)
    c_dict["artifact_catalog_digest"] = "DUMMY_CATALOG_SIGNATURE"
    recomputed = hash_waveguide_certified_artifact_catalog(c_dict)
    assert recomputed == d1


def test_catalog_counts_and_indexing():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    catalog = build_waveguide_certified_artifact_catalog(report_path)

    # 17. Distribution-ready artifact count is correct.
    # Excluding self-referential json/md which are pending or blocked because they don't exist yet.
    # 28 total files cataloged. Let's see: 26 exist, so ready = 26.
    has_json = os.path.exists(os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json"))
    has_md = os.path.exists(os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.md"))
    expected_ready = 26 + (1 if has_json else 0) + (1 if has_md else 0)
    expected_pending = 2 - (1 if has_json else 0) - (1 if has_md else 0)

    assert catalog.distribution_ready_artifact_count == expected_ready

    # 18. Blocked/pending/invalid counts are correct.
    assert catalog.blocked_artifact_count == 0
    assert catalog.pending_artifact_count == expected_pending
    assert catalog.invalid_artifact_count == 0

    # 19. RC1 artifact count is correct.
    # Manifest, Record, Verdict, bundle, resolver, audit report = 6 entries.
    assert catalog.rc1_artifact_count == 6

    # 20. RC2 artifact count is correct.
    # Manifest, Record, Verdict, bundle, resolver, audit report = 6 entries.
    assert catalog.rc2_artifact_count == 6

    # 21. Shared artifact count is correct.
    # Delta audit, release registry, compiler session registry, audit report, index, pub manifest, distribution readiness report (7 json)
    # 5 md files (bundle, validator, index, pub manifest, validator) + 2 pending catalogs (json/md) + 2 python files = 16.
    assert catalog.shared_artifact_count == 16

    # 22. Artifact types are deterministic and sorted.
    assert catalog.artifact_types_indexed == sorted(list(set(e.artifact_type for e in catalog.entries)))

    # 23. Artifact formats are deterministic and sorted.
    assert catalog.artifact_formats_indexed == ["json", "markdown", "python"]

    # 24. Package roles are deterministic and sorted.
    assert catalog.package_roles_indexed == sorted(list(set(e.package_role for e in catalog.entries)))

    # 25. RC scopes are deterministic and sorted.
    assert catalog.rc_scopes_indexed == ["RC1", "RC2", "Shared"]

    # 26. Artifact paths are deterministic and sorted.
    assert catalog.artifact_paths_indexed == sorted(e.artifact_path for e in catalog.entries)

    # 27. Artifact digests are deterministic and sorted.
    # Clean up empty digests (from pending entries)
    assert catalog.artifact_digests_indexed == sorted(list(set(filter(None, (e.artifact_digest for e in catalog.entries)))))


def test_artifact_path_classifications():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    catalog = build_waveguide_certified_artifact_catalog(report_path)

    # 28. Documentation artifact paths are deterministic and sorted.
    assert len(catalog.documentation_artifact_paths) == 7 # 5 md docs + 1 self catalog md + 1 self catalog json (which is documentation_index type)
    assert catalog.documentation_artifact_paths[0].endswith(".json") or catalog.documentation_artifact_paths[0].endswith(".md")

    # 29. Proof artifact paths are deterministic and sorted.
    # All JSON files except self catalog json
    assert len(catalog.proof_artifact_paths) == 19

    # 30. Code artifact paths are deterministic and sorted.
    assert len(catalog.code_artifact_paths) == 1
    assert catalog.code_artifact_paths[0] == "tools/sol-core/sol_waveguide_certified_artifact_catalog.py"

    # 31. Test artifact paths are deterministic and sorted.
    assert len(catalog.test_artifact_paths) == 1
    assert catalog.test_artifact_paths[0] == "tests/test_waveguide_certified_artifact_catalog.py"


def test_package_inventory():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    catalog = build_waveguide_certified_artifact_catalog(report_path)

    # 32. Distribution package inventory is deterministic.
    inv1 = build_waveguide_distribution_package_inventory(catalog.entries)
    inv2 = build_waveguide_distribution_package_inventory(catalog.entries)
    assert inv1 == inv2
    assert catalog.distribution_package_inventory == inv1

    # 33. Inventory is sorted by artifact path.
    sorted_paths = [item["artifact_path"] for item in catalog.distribution_package_inventory]
    assert sorted_paths == sorted(sorted_paths)


def test_summary_and_export(temp_dir):
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    catalog = build_waveguide_certified_artifact_catalog(report_path)

    # 34. Summary output is deterministic.
    s1 = summarize_waveguide_certified_artifact_catalog(catalog)
    s2 = summarize_waveguide_certified_artifact_catalog(catalog)
    assert s1 == s2
    assert "SOL WAVEGUIDE CERTIFIED ARTIFACT CATALOG" in s1

    # 35. JSON export is deterministic.
    out_file = os.path.join(temp_dir, "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    export_waveguide_certified_artifact_catalog(catalog, out_file)
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["artifact_catalog_digest"] == catalog.artifact_catalog_digest


def test_compare():
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json")
    c1 = build_waveguide_certified_artifact_catalog(report_path)
    c2 = build_waveguide_certified_artifact_catalog(report_path)

    diff = compare_waveguide_certified_artifact_catalogs(c1, c2)
    assert diff["all_match"] is True
