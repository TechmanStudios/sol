# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Distribution Package Assembly Plan.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_certified_artifact_catalog import build_waveguide_certified_artifact_catalog_entry
from sol_waveguide_distribution_package_assembly_plan import (
    build_waveguide_distribution_package_layout_entry,
    validate_waveguide_distribution_package_layout_entry,
    build_waveguide_distribution_package_assembly_plan,
    validate_waveguide_distribution_package_assembly_plan,
    summarize_waveguide_distribution_package_assembly_plan,
    export_waveguide_distribution_package_assembly_plan,
    compare_waveguide_distribution_package_assembly_plans,
    hash_waveguide_distribution_package_layout_entry,
    hash_waveguide_distribution_package_assembly_plan,
    map_waveguide_artifact_to_package_path,
    index_waveguide_package_layout_entries_by_rc,
    index_waveguide_package_layout_entries_by_section,
    index_waveguide_package_layout_entries_by_role,
    build_waveguide_package_file_map,
    build_waveguide_package_section_index,
    WaveguideDistributionPackageLayoutEntry,
    WaveguideDistributionPackageAssemblyPlan
)


@pytest.fixture
def temp_dir():
    path = os.path.join(REPO_ROOT, "docs", "test_plan_temp")
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


def test_layout_entry_building_and_validation():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    assert os.path.exists(catalog_path)
    
    with open(catalog_path, "r", encoding="utf-8") as f:
        cat_dict = json.load(f)
    catalog_digest = cat_dict.get("artifact_catalog_digest", "")

    # 1. JSON proof layout entry can be built.
    cat_entry_json = next(e for e in cat_dict["entries"] if e["artifact_path"] == "docs/SOL_WAVEGUIDE_RC1_MANIFEST.json")
    entry_json = build_waveguide_distribution_package_layout_entry(cat_entry_json, catalog_digest)
    assert isinstance(entry_json, WaveguideDistributionPackageLayoutEntry)
    assert entry_json.target_package_section == "proof/"
    assert entry_json.target_package_path == "proof/json/SOL_WAVEGUIDE_RC1_MANIFEST.json"
    ok1, r1 = validate_waveguide_distribution_package_layout_entry(entry_json)
    assert ok1 is True

    # 2. Markdown documentation layout entry can be built.
    cat_entry_md = next(e for e in cat_dict["entries"] if e["artifact_path"] == "docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE.md")
    entry_md = build_waveguide_distribution_package_layout_entry(cat_entry_md, catalog_digest)
    assert isinstance(entry_md, WaveguideDistributionPackageLayoutEntry)
    assert entry_md.target_package_section == "docs/"
    assert entry_md.target_package_path == "docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE.md"
    ok2, r2 = validate_waveguide_distribution_package_layout_entry(entry_md)
    assert ok2 is True

    # 3. Source module layout entry can be built.
    cat_entry_src = next(e for e in cat_dict["entries"] if e["artifact_path"] == "tools/sol-core/sol_waveguide_certified_artifact_catalog.py")
    entry_src = build_waveguide_distribution_package_layout_entry(cat_entry_src, catalog_digest)
    assert isinstance(entry_src, WaveguideDistributionPackageLayoutEntry)
    assert entry_src.target_package_section == "source/"
    assert entry_src.target_package_path == "source/tools/sol-core/sol_waveguide_certified_artifact_catalog.py"
    ok3, r3 = validate_waveguide_distribution_package_layout_entry(entry_src)
    assert ok3 is True

    # 4. Test source layout entry can be built.
    cat_entry_test = next(e for e in cat_dict["entries"] if e["artifact_path"] == "tests/test_waveguide_certified_artifact_catalog.py")
    entry_test = build_waveguide_distribution_package_layout_entry(cat_entry_test, catalog_digest)
    assert isinstance(entry_test, WaveguideDistributionPackageLayoutEntry)
    assert entry_test.target_package_section == "tests/"
    assert entry_test.target_package_path == "tests/test_waveguide_certified_artifact_catalog.py"
    ok4, r4 = validate_waveguide_distribution_package_layout_entry(entry_test)
    assert ok4 is True


def test_layout_entry_digest_determinism_and_exclusion():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        cat_dict = json.load(f)
    catalog_digest = cat_dict.get("artifact_catalog_digest", "")
    cat_entry = cat_dict["entries"][0]
    entry = build_waveguide_distribution_package_layout_entry(cat_entry, catalog_digest)

    # 5. Layout entry digest is deterministic.
    d1 = hash_waveguide_distribution_package_layout_entry(entry)
    d2 = hash_waveguide_distribution_package_layout_entry(entry)
    assert d1 == d2
    assert entry.package_layout_entry_digest == d1

    # 6. package_layout_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["package_layout_entry_digest"] = "DUMMY_DIGEST"
    recomputed = hash_waveguide_distribution_package_layout_entry(e_dict)
    assert recomputed == d1


def test_target_paths_constraints():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        cat_dict = json.load(f)
    catalog_digest = cat_dict.get("artifact_catalog_digest", "")
    cat_entry = cat_dict["entries"][0]
    entry = build_waveguide_distribution_package_layout_entry(cat_entry, catalog_digest)

    # 7. Target package paths are relative.
    # 8. Target package paths use /.
    # Test valid target paths
    assert not entry.target_package_path.startswith("/")
    assert "\\" not in entry.target_package_path

    # 9. Target package paths reject ..
    e_bad1 = asdict(entry)
    e_bad1["target_package_path"] = "proof/json/../../test.json"
    e_bad1["package_layout_entry_digest"] = hash_waveguide_distribution_package_layout_entry(e_bad1)
    ok1, _ = validate_waveguide_distribution_package_layout_entry(e_bad1)
    assert ok1 is False

    # 10. Target package paths reject absolute paths.
    e_bad2 = asdict(entry)
    if os.name == 'nt':
        e_bad2["target_package_path"] = "C:/proof/test.json"
    else:
        e_bad2["target_package_path"] = "/proof/test.json"
    e_bad2["package_layout_entry_digest"] = hash_waveguide_distribution_package_layout_entry(e_bad2)
    ok2, _ = validate_waveguide_distribution_package_layout_entry(e_bad2)
    assert ok2 is False


def test_deployment_and_signing_blocks():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        cat_dict = json.load(f)
    catalog_digest = cat_dict.get("artifact_catalog_digest", "")
    
    # Mock a deployment artifact
    cat_entry_dep = dict(cat_dict["entries"][0])
    cat_entry_dep["is_deployment_artifact"] = True
    cat_entry_dep["artifact_name"] = "deploy_script.py"
    
    entry_dep = build_waveguide_distribution_package_layout_entry(cat_entry_dep, catalog_digest)
    # 12. Deployment artifact is blocked.
    assert entry_dep.assembly_status == "package_layout_blocked"
    assert entry_dep.include_in_package_plan is False
    assert "PACKAGE_PLAN_DEPLOYMENT_BLOCKED" in entry_dep.reason_codes

    # Mock a signing artifact
    cat_entry_sign = dict(cat_dict["entries"][0])
    cat_entry_sign["is_signing_artifact"] = True
    cat_entry_sign["artifact_name"] = "signing_keys.key"

    entry_sign = build_waveguide_distribution_package_layout_entry(cat_entry_sign, catalog_digest)
    # 13. External signing artifact is blocked.
    assert entry_sign.assembly_status == "package_layout_blocked"
    assert entry_sign.include_in_package_plan is False
    assert "PACKAGE_PLAN_EXTERNAL_SIGNING_BLOCKED" in entry_sign.reason_codes


def test_package_plan_boundaries():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        cat_dict = json.load(f)
    catalog_digest = cat_dict.get("artifact_catalog_digest", "")
    cat_entry = cat_dict["entries"][0]
    entry = build_waveguide_distribution_package_layout_entry(cat_entry, catalog_digest)

    # 14. No archive creation is represented.
    # 15. No upload is represented.
    # 16. No deployment is represented.
    # 17. No signing is represented.
    assert "PACKAGE_PLAN_NO_ARCHIVE_CREATED" in entry.reason_codes
    assert "PACKAGE_PLAN_NO_UPLOAD_PERFORMED" in entry.reason_codes
    assert "PACKAGE_PLAN_NO_DEPLOYMENT_PERFORMED" in entry.reason_codes
    assert "PACKAGE_PLAN_NO_SIGNING_PERFORMED" in entry.reason_codes


def test_top_level_package_assembly_plan():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    
    # 18. Top-level package assembly plan can be built.
    plan = build_waveguide_distribution_package_assembly_plan(catalog_path)
    assert isinstance(plan, WaveguideDistributionPackageAssemblyPlan)

    # 19. Top-level package assembly plan validates.
    ok, reasons = validate_waveguide_distribution_package_assembly_plan(plan)
    assert ok is True
    assert plan.package_assembly_plan_status == "package_plan_ready"
    assert "PACKAGE_PLAN_READY" in plan.reason_codes


def test_plan_digest_determinism_and_exclusion():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    plan = build_waveguide_distribution_package_assembly_plan(catalog_path)

    # 20. Plan digest is deterministic.
    d1 = hash_waveguide_distribution_package_assembly_plan(plan)
    d2 = hash_waveguide_distribution_package_assembly_plan(plan)
    assert d1 == d2
    assert plan.package_assembly_plan_digest == d1

    # 21. package_assembly_plan_digest is excluded from its own digest input.
    p_dict = asdict(plan)
    p_dict["package_assembly_plan_digest"] = "DUMMY_DIGEST"
    recomputed = hash_waveguide_distribution_package_assembly_plan(p_dict)
    assert recomputed == d1


def test_plan_counts_and_indexing():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    plan = build_waveguide_distribution_package_assembly_plan(catalog_path)

    # 22. Ready layout count is correct.
    assert plan.ready_layout_count == 28

    # 23. Blocked/pending/invalid counts are correct.
    assert plan.blocked_layout_count == 0
    assert plan.pending_layout_count == 0
    assert plan.invalid_layout_count == 0

    # 24. Total planned file count matches ready layout entries.
    assert plan.total_planned_file_count == plan.ready_layout_count

    # 25. RC1 layout count is correct.
    # 26. RC2 layout count is correct.
    # 27. Shared layout count is correct.
    assert plan.rc1_layout_count == 6
    assert plan.rc2_layout_count == 6
    assert plan.shared_layout_count == 16

    # 28. Target package sections are deterministic and sorted.
    assert plan.target_package_sections == ["docs/", "proof/", "source/", "tests/"]

    # 29. Package roles are deterministic and sorted.
    # 30. Artifact types are deterministic and sorted.
    # 31. Artifact formats are deterministic and sorted.
    # 32. Source artifact paths are deterministic and sorted.
    # 33. Target package paths are deterministic and sorted.
    # 34. Source artifact digests are deterministic and sorted.
    assert plan.package_roles_indexed == sorted(list(set(e.source_package_role for e in plan.layout_entries)))
    assert plan.artifact_types_indexed == sorted(list(set(e.source_artifact_type for e in plan.layout_entries)))
    assert plan.artifact_formats_indexed == sorted(list(set(e.source_artifact_format for e in plan.layout_entries)))
    assert plan.source_artifact_paths == sorted(list(set(e.source_artifact_path for e in plan.layout_entries)))
    assert plan.target_package_paths == sorted(list(set(e.target_package_path for e in plan.layout_entries)))
    assert plan.source_artifact_digests == sorted(list(set(e.source_artifact_digest for e in plan.layout_entries if e.source_artifact_digest)))


def test_artifact_layouts_and_indexes():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    plan = build_waveguide_distribution_package_assembly_plan(catalog_path)

    # 35. Proof artifact layout is deterministic.
    # 36. Documentation artifact layout is deterministic.
    # 37. Source module layout is deterministic.
    # 38. Test source layout is deterministic.
    assert len(plan.proof_artifact_layout) == 19
    assert len(plan.documentation_artifact_layout) == 7
    assert len(plan.source_module_layout) == 1
    assert len(plan.test_source_layout) == 1

    # 39. Package file map is deterministic.
    # 40. File map is sorted by target package path.
    inv_paths = [e["target_package_path"] for e in plan.package_file_map]
    assert inv_paths == sorted(inv_paths)

    # 41. Package section index is deterministic.
    # 42. Section index lists are sorted.
    for sect, paths in plan.package_section_index.items():
        assert paths == sorted(paths)


def test_collision_detection():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    plan = build_waveguide_distribution_package_assembly_plan(catalog_path)

    # 11. Target package path collision is detected.
    # Inject a duplicate target path
    p_dict = asdict(plan)
    p_dict["layout_entries"][1]["target_package_path"] = p_dict["layout_entries"][0]["target_package_path"]
    p_dict["package_assembly_plan_digest"] = hash_waveguide_distribution_package_assembly_plan(p_dict)
    
    ok, reasons = validate_waveguide_distribution_package_assembly_plan(p_dict)
    assert ok is False


def test_summary_and_export(temp_dir):
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    plan = build_waveguide_distribution_package_assembly_plan(catalog_path)

    # 43. Summary output is deterministic.
    s1 = summarize_waveguide_distribution_package_assembly_plan(plan)
    s2 = summarize_waveguide_distribution_package_assembly_plan(plan)
    assert s1 == s2
    assert "SOL WAVEGUIDE DISTRIBUTION PACKAGE ASSEMBLY PLAN" in s1

    # 44. JSON export is deterministic.
    out_file = os.path.join(temp_dir, "SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_ASSEMBLY_PLAN.json")
    export_waveguide_distribution_package_assembly_plan(plan, out_file)
    assert os.path.exists(out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["package_assembly_plan_digest"] == plan.package_assembly_plan_digest


def test_compare():
    catalog_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json")
    p1 = build_waveguide_distribution_package_assembly_plan(catalog_path)
    p2 = build_waveguide_distribution_package_assembly_plan(catalog_path)

    diff = compare_waveguide_distribution_package_assembly_plans(p1, p2)
    assert diff["all_match"] is True
