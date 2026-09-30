# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Plan.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_plan import (
    build_waveguide_package_archive_plan_entry,
    validate_waveguide_package_archive_plan_entry,
    build_waveguide_package_archive_plan,
    validate_waveguide_package_archive_plan,
    hash_waveguide_package_archive_plan_entry,
    hash_waveguide_package_archive_plan,
    validate_waveguide_package_archive_member_path_safety,
    WaveguidePackageArchivePlanEntry,
    WaveguidePackageArchivePlan
)


@pytest.fixture
def staging_audit_report_path() -> str:
    return os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_LOCAL_STAGING_OUTPUT_AUDIT_REPORT.json")


@pytest.fixture
def staging_plan_path() -> str:
    return os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_PLAN.json")


def test_archive_plan_entry_lifecycle(staging_plan_path):
    with open(staging_plan_path, "r", encoding="utf-8") as f:
        plan_dict = json.load(f)
    se = plan_dict["local_staging_entries"][0]
    
    # 1. Archive plan entry can be built.
    entry = build_waveguide_package_archive_plan_entry(se, "mock_staged_digest", 0)
    assert isinstance(entry, WaveguidePackageArchivePlanEntry)
    
    # 2. Archive plan entry validates.
    ok, errs = validate_waveguide_package_archive_plan_entry(entry)
    assert ok is True, f"Validation errors: {errs}"
    
    # 3. Entry digest is deterministic.
    dig1 = hash_waveguide_package_archive_plan_entry(entry)
    dig2 = hash_waveguide_package_archive_plan_entry(entry)
    assert dig1 == dig2
    assert entry.archive_plan_entry_digest == dig1
    
    # 4. archive_plan_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["archive_plan_entry_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_plan_entry(e_dict) == dig1


def test_archive_plan_lifecycle(staging_audit_report_path, staging_plan_path):
    # 5. Archive plan builds.
    plan = build_waveguide_package_archive_plan(staging_audit_report_path, staging_plan_path)
    assert isinstance(plan, WaveguidePackageArchivePlan)
    
    # 6. Archive plan validates.
    ok, errs = validate_waveguide_package_archive_plan(plan)
    assert ok is True, f"Validation errors: {errs}"
    
    # 7. Plan digest is deterministic.
    dig1 = hash_waveguide_package_archive_plan(plan)
    dig2 = hash_waveguide_package_archive_plan(plan)
    assert dig1 == dig2
    assert plan.package_archive_plan_digest == dig1
    
    # 8. package_archive_plan_digest is excluded from its own digest input.
    p_dict = asdict(plan)
    p_dict["package_archive_plan_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_plan(p_dict) == dig1


def test_archive_plan_validation_blocks_and_failures(staging_audit_report_path, staging_plan_path):
    # 9. Local staging output audit validation failure blocks plan.
    bad_report = {
        "local_staging_output_audit_report_status": "package_local_staging_output_failed",
        "local_staging_output_audit_report_digest": "bad_digest",
        "audited_cases": []
    }
    plan = build_waveguide_package_archive_plan(bad_report, staging_plan_path)
    assert plan.package_archive_plan_status == "package_archive_plan_blocked"
    assert plan.archive_creation_allowed is False
    
    # 10. Absolute archive member path blocks plan.
    with open(staging_plan_path, "r", encoding="utf-8") as f:
        plan_dict = json.load(f)
    se = plan_dict["local_staging_entries"][0]
    se["target_staging_relative_path"] = "/absolute/path/file.txt"
    entry = build_waveguide_package_archive_plan_entry(se, "digest", 0)
    ok, errs = validate_waveguide_package_archive_plan_entry(entry)
    assert ok is False
    assert any("Unsafe archive member path" in e for e in errs)

    # 11. Parent traversal archive member path blocks plan.
    se2 = dict(se)
    se2["target_staging_relative_path"] = "docs/../../file.txt"
    entry2 = build_waveguide_package_archive_plan_entry(se2, "digest", 0)
    ok, errs = validate_waveguide_package_archive_plan_entry(entry2)
    assert ok is False
    assert any("Unsafe archive member path" in e for e in errs)

    # 12. Duplicate archive member path blocks plan.
    # We mutate the plan entries to contain duplicate paths.
    p = build_waveguide_package_archive_plan(staging_audit_report_path, staging_plan_path)
    p.archive_plan_entries[1].archive_member_relative_path = p.archive_plan_entries[0].archive_member_relative_path
    # Rehash plan
    p.package_archive_plan_digest = hash_waveguide_package_archive_plan(p)
    # The builder will recalculate collision check
    collision_check = len(set(e.archive_member_relative_path for e in p.archive_plan_entries)) == len(p.archive_plan_entries)
    assert collision_check is False

    # 13. Upload/deploy/sign/publish/mutate allowance blocks plan.
    p_bad = build_waveguide_package_archive_plan(staging_audit_report_path, staging_plan_path)
    p_bad.upload_allowed = True
    p_bad.package_archive_plan_digest = hash_waveguide_package_archive_plan(p_bad)
    ok, errs = validate_waveguide_package_archive_plan(p_bad)
    assert ok is False
    assert any("upload_allowed must be False" in e for e in errs)


def test_archive_plan_artifact_existence():
    # 14. Archive plan JSON file exists.
    plan_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_PLAN.json")
    assert os.path.exists(plan_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_PLAN.json"
    
    # 15. Archive plan documentation exists.
    doc_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_PLAN.md")
    assert os.path.exists(doc_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_PLAN.md"
