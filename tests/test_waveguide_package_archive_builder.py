# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Builder.
"""

import os
import json
import pytest
import zipfile
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_plan import build_waveguide_package_archive_plan
from sol_waveguide_package_archive_builder import (
    build_waveguide_package_archive_build_request,
    execute_waveguide_package_archive_build,
    validate_waveguide_package_archive_build_record,
    hash_waveguide_package_archive_build_record,
    hash_waveguide_package_archive_member_build_record,
    resolve_waveguide_package_archive_output_root,
    validate_waveguide_package_archive_output_path,
    WaveguidePackageArchiveBuildRecord
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


def test_archive_builder_safety_guards(clean_plan, tmp_path):
    output_root = str(tmp_path / "archive_out")
    
    # 1. Archive build request without operator approval is blocked and creates no archive.
    rec = execute_waveguide_package_archive_build(
        archive_plan=clean_plan,
        archive_output_root=output_root,
        operator_approved=False,
        local_archive_scope_confirmed=True
    )
    assert rec.package_archive_build_status == "package_archive_build_blocked"
    assert rec.archive_creation_performed is False
    assert not os.path.exists(os.path.join(output_root, clean_plan.archive_filename))
    
    # 2. Archive build request without local archive scope confirmation is blocked and creates no archive.
    rec2 = execute_waveguide_package_archive_build(
        archive_plan=clean_plan,
        archive_output_root=output_root,
        operator_approved=True,
        local_archive_scope_confirmed=False
    )
    assert rec2.package_archive_build_status == "package_archive_build_blocked"
    assert rec2.archive_creation_performed is False
    
    # 3. Unsafe archive output root is blocked.
    with pytest.raises(ValueError):
        resolve_waveguide_package_archive_output_root(REPO_ROOT)
    with pytest.raises(ValueError):
        resolve_waveguide_package_archive_output_root(os.path.expanduser("~"))

    # 4. Archive output path escape is blocked.
    escape_ok = validate_waveguide_package_archive_output_path(output_root, "../escaped.zip")
    assert escape_ok is False


def test_archive_builder_successful_build(clean_plan, tmp_path):
    # Set up staging override for testing
    staging_override = os.path.join(REPO_ROOT, "docs", "staged_temp")
    
    # 5. Clean approved ZIP build completes in a pytest tmp_path archive output root.
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
    assert rec.package_archive_build_status == "package_archive_build_completed"
    assert rec.archive_creation_performed is True
    
    archive_file = os.path.join(output_root, clean_plan.archive_filename)
    assert os.path.exists(archive_file)
    
    # 6. Exactly 28 members are written.
    with zipfile.ZipFile(archive_file, "r") as zf:
        members = zf.namelist()
    assert len(members) == 28
    
    # 7. Archive member paths are deterministic and safe.
    for m in members:
        assert not m.startswith("/")
        assert ".." not in m
        assert "\\" not in m

    # 8. Archive digest is deterministic for identical inputs.
    rec2 = execute_waveguide_package_archive_build(
        archive_plan=clean_plan,
        archive_output_root=output_root,
        operator_approved=True,
        local_archive_scope_confirmed=True,
        clean_existing_archive_output=True,
        allow_overwrite=True,
        staging_root_override=staging_override
    )
    assert rec.archive_file_digest == rec2.archive_file_digest
    assert len(rec.archive_file_digest) == 64


def test_archive_builder_record_digests(clean_plan, tmp_path):
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
    
    # 9. Member build record digest is deterministic.
    member = rec.archive_member_records[0]
    dig1 = hash_waveguide_package_archive_member_build_record(member)
    dig2 = hash_waveguide_package_archive_member_build_record(member)
    assert dig1 == dig2
    assert member.archive_member_build_record_digest == dig1
    
    # 10. archive_member_build_record_digest is excluded from its own digest input.
    m_dict = asdict(member)
    m_dict["archive_member_build_record_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_member_build_record(m_dict) == dig1
    
    # 11. Build record digest is deterministic.
    br_dig1 = hash_waveguide_package_archive_build_record(rec)
    br_dig2 = hash_waveguide_package_archive_build_record(rec)
    assert br_dig1 == br_dig2
    assert rec.package_archive_build_record_digest == br_dig1
    
    # 12. package_archive_build_record_digest is excluded from its own digest input.
    br_dict = asdict(rec)
    br_dict["package_archive_build_record_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_build_record(br_dict) == br_dig1

    # 13. No upload/deploy/sign/publish/production mutation occurred.
    assert rec.upload_performed is False
    assert rec.deployment_performed is False
    assert rec.signing_performed is False
    assert rec.external_publication_performed is False
    assert rec.production_mutation_performed is False


def test_archive_builder_artifact_existence():
    # 14. Archive build record JSON artifact exists.
    record_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_BUILD_RECORD.json")
    assert os.path.exists(record_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_BUILD_RECORD.json"
    
    # 15. Archive builder documentation exists.
    doc_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_BUILDER.md")
    assert os.path.exists(doc_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_BUILDER.md"
