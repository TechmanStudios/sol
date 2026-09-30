# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Release Candidate Index.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_plan import build_waveguide_package_archive_plan
from sol_waveguide_package_archive_builder import execute_waveguide_package_archive_build
from sol_waveguide_package_archive_manifest import build_waveguide_package_archive_manifest
from sol_waveguide_package_archive_validator import build_waveguide_package_audit_report
from sol_waveguide_package_archive_release_candidate_index import (
    build_waveguide_package_archive_candidate_entry,
    validate_waveguide_package_archive_candidate_entry,
    build_waveguide_package_archive_release_candidate_index,
    validate_waveguide_package_archive_release_candidate_index,
    hash_waveguide_package_archive_candidate_entry,
    hash_waveguide_package_archive_release_candidate_index,
    WaveguidePackageArchiveCandidateEntry,
    WaveguidePackageArchiveReleaseCandidateIndex
)


@pytest.fixture
def staging_audit_report_path() -> str:
    return os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_LOCAL_STAGING_OUTPUT_AUDIT_REPORT.json")


@pytest.fixture
def staging_plan_path() -> str:
    return os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_PLAN.json")


@pytest.fixture
def clean_plan(staging_audit_report_path, staging_plan_path):
    return build_waveguide_package_archive_plan(staging_audit_report_path, staging_plan_path)


@pytest.fixture
def clean_audit_report(clean_plan, tmp_path):
    staging_override = os.path.join(REPO_ROOT, "docs", "staged_temp")
    output_root = str(tmp_path / "archive_out")
    rec = execute_waveguide_package_archive_build(
        archive_plan=clean_plan,
        archive_output_root=output_root,
        operator_approved=True,
        local_archive_scope_confirmed=True,
        clean_existing_archive_output=True,
        allow_overwrite=True,
        staging_root_override=staging_override
    )
    manifest = build_waveguide_package_archive_manifest(rec, archive_output_root_override=output_root)
    report = build_waveguide_package_audit_report(manifest, archive_output_root_override=output_root)
    return report


def test_archive_candidate_entry_lifecycle(clean_plan, clean_audit_report):
    report_dict = asdict(clean_audit_report)
    
    # 1. Archive candidate entry builds.
    entry = build_waveguide_package_archive_candidate_entry(report_dict, 0)
    assert isinstance(entry, WaveguidePackageArchiveCandidateEntry)
    
    # 2. Archive candidate entry validates.
    ok, errs = validate_waveguide_package_archive_candidate_entry(entry)
    assert ok is True, f"Errors: {errs}"
    
    # 3. Entry digest is deterministic.
    dig1 = hash_waveguide_package_archive_candidate_entry(entry)
    dig2 = hash_waveguide_package_archive_candidate_entry(entry)
    assert dig1 == dig2
    assert entry.archive_candidate_entry_digest == dig1
    
    # 4. archive_candidate_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["archive_candidate_entry_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_candidate_entry(e_dict) == dig1


def test_archive_release_candidate_index_lifecycle(clean_audit_report):
    # 5. Archive release candidate index builds.
    index_obj = build_waveguide_package_archive_release_candidate_index(clean_audit_report)
    assert isinstance(index_obj, WaveguidePackageArchiveReleaseCandidateIndex)
    assert index_obj.package_archive_release_candidate_index_status == "package_archive_candidate_index_valid"
    
    # 6. Archive release candidate index validates.
    ok, errs = validate_waveguide_package_archive_release_candidate_index(index_obj)
    assert ok is True, f"Errors: {errs}"
    
    # 7. Index digest is deterministic.
    dig1 = hash_waveguide_package_archive_release_candidate_index(index_obj)
    dig2 = hash_waveguide_package_archive_release_candidate_index(index_obj)
    assert dig1 == dig2
    assert index_obj.package_archive_release_candidate_index_digest == dig1
    
    # 8. package_archive_release_candidate_index_digest is excluded from its own digest input.
    i_dict = asdict(index_obj)
    i_dict["package_archive_release_candidate_index_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_release_candidate_index(i_dict) == dig1

    # 13. Verified archive candidate count is 1.
    assert index_obj.verified_archive_candidate_count == 1
    
    # 14. Current archive candidate digest matches archive audit report.
    assert index_obj.current_archive_candidate_digest == clean_audit_report.archive_file_digest_recomputed


def test_archive_index_failures_and_blocks(clean_audit_report):
    # 9. Archive audit report validation failure blocks index.
    report_bad = asdict(clean_audit_report)
    report_bad["package_archive_audit_report_id"] = "bad_id"
    # rehash report
    from sol_waveguide_package_archive_validator import hash_waveguide_package_archive_audit_report
    report_bad["package_archive_audit_report_digest"] = hash_waveguide_package_archive_audit_report(report_bad)
    index_obj = build_waveguide_package_archive_release_candidate_index(report_bad)
    assert index_obj.package_archive_release_candidate_index_status == "package_archive_candidate_index_blocked"

    # 10. Archive audit status not verified blocks index.
    report_unverified = asdict(clean_audit_report)
    report_unverified["package_archive_audit_report_status"] = "package_archive_invalid"
    report_unverified["package_archive_audit_report_digest"] = hash_waveguide_package_archive_audit_report(report_unverified)
    index_obj2 = build_waveguide_package_archive_release_candidate_index(report_unverified)
    assert index_obj2.package_archive_release_candidate_index_status == "package_archive_candidate_index_blocked"

    # 11. Missing archive digest blocks index.
    report_nodig = asdict(clean_audit_report)
    report_nodig["archive_file_digest_recomputed"] = ""
    report_nodig["package_archive_audit_report_digest"] = hash_waveguide_package_archive_audit_report(report_nodig)
    index_obj3 = build_waveguide_package_archive_release_candidate_index(report_nodig)
    assert index_obj3.archive_candidates[0].archive_candidate_status == "archive_candidate_invalid"

    # 12. Signing/upload/publish/deploy/production mutation performed blocks index.
    report_mutate = asdict(clean_audit_report)
    report_mutate["upload_performed"] = True
    report_mutate["package_archive_audit_report_digest"] = hash_waveguide_package_archive_audit_report(report_mutate)
    index_obj4 = build_waveguide_package_archive_release_candidate_index(report_mutate)
    assert index_obj4.archive_candidates[0].archive_candidate_status == "archive_candidate_invalid"


def test_archive_index_artifact_existence():
    # 15. Archive candidate index JSON artifact exists.
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json")
    assert os.path.exists(index_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json"
    
    # 16. Archive candidate index documentation exists.
    doc_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.md")
    assert os.path.exists(doc_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.md"
