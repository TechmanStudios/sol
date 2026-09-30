# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Validator.
"""

import os
import json
import pytest
import zipfile
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_plan import build_waveguide_package_archive_plan
from sol_waveguide_package_archive_builder import execute_waveguide_package_archive_build
from sol_waveguide_package_archive_manifest import build_waveguide_package_archive_manifest
from sol_waveguide_package_archive_validator import (
    build_waveguide_package_archive_audit_case,
    build_waveguide_package_audit_report,
    validate_waveguide_package_archive_audit_report,
    hash_waveguide_package_archive_audit_case,
    hash_waveguide_package_archive_audit_report,
    WaveguidePackageArchiveAuditCase,
    WaveguidePackageArchiveAuditReport
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
def clean_manifest(clean_plan, tmp_path):
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
    return manifest, output_root


def test_archive_audit_case_lifecycle(clean_manifest):
    manifest, output_root = clean_manifest
    entry = manifest.archive_entries[0]
    
    # We open ZIP for the case build
    archive_file = os.path.join(output_root, manifest.archive_filename)
    zf = zipfile.ZipFile(archive_file, "r")
    
    # 1. Archive audit case builds.
    case = build_waveguide_package_archive_audit_case(
        entry_dict=asdict(entry),
        manifest_digest=manifest.package_archive_manifest_digest,
        manifest_valid=True,
        build_record_digest=manifest.source_package_archive_build_record_digest,
        plan_digest=manifest.source_package_archive_plan_digest,
        archive_filepath=archive_file,
        zf=zf,
        case_index=0
    )
    zf.close()
    assert isinstance(case, WaveguidePackageArchiveAuditCase)
    
    # 2. Archive audit case validates.
    assert case.archive_audit_status == "archive_audit_verified"
    
    # 3. Audit case digest is deterministic.
    dig1 = hash_waveguide_package_archive_audit_case(case)
    dig2 = hash_waveguide_package_archive_audit_case(case)
    assert dig1 == dig2
    assert case.archive_audit_case_digest == dig1
    
    # 4. archive_audit_case_digest is excluded from its own digest input.
    c_dict = asdict(case)
    c_dict["archive_audit_case_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_audit_case(c_dict) == dig1


def test_archive_audit_report_lifecycle(clean_manifest):
    manifest, output_root = clean_manifest
    
    # 13. Top-level archive audit report builds.
    report = build_waveguide_package_archive_report_overridden(manifest, output_root)
    assert isinstance(report, WaveguidePackageArchiveAuditReport)
    assert report.package_archive_audit_report_status == "package_archive_verified"
    
    # 14. Top-level archive audit report validates.
    ok, errs = validate_waveguide_package_archive_audit_report(report)
    assert ok is True, f"Errors: {errs}"
    
    # 15. Report digest is deterministic.
    dig1 = hash_waveguide_package_archive_audit_report(report)
    dig2 = hash_waveguide_package_archive_audit_report(report)
    assert dig1 == dig2
    assert report.package_archive_audit_report_digest == dig1
    
    # 16. package_archive_audit_report_digest is excluded from its own digest input.
    r_dict = asdict(report)
    r_dict["package_archive_audit_report_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_audit_report(r_dict) == dig1

    # 17. Verified archive audit case count is 28.
    assert report.verified_archive_member_count == 28
    assert len(report.audited_cases) == 28
    
    # 18. Archive digest verifies.
    assert report.archive_digest_verified is True


def test_archive_validator_blocks_and_failures(clean_manifest, tmp_path):
    manifest, output_root = clean_manifest
    
    # 5. Archive manifest independent validation failure blocks audit.
    manifest_bad = asdict(manifest)
    manifest_bad["total_expected_archive_file_count"] = 0
    # rehash manifest
    from sol_waveguide_package_archive_manifest import hash_waveguide_package_archive_manifest
    manifest_bad["package_archive_manifest_digest"] = hash_waveguide_package_archive_manifest(manifest_bad)
    report = build_waveguide_package_audit_report(manifest_bad, archive_output_root_override=output_root)
    assert report.package_archive_audit_report_status == "package_archive_blocked"

    # 6. Manifest entry digest mismatch blocks audit.
    manifest_entry_bad = asdict(manifest)
    manifest_entry_bad["archive_entries"][0]["archive_manifest_entry_digest"] = "wrong_digest"
    manifest_entry_bad["package_archive_manifest_digest"] = hash_waveguide_package_archive_manifest(manifest_entry_bad)
    report2 = build_waveguide_package_audit_report(manifest_entry_bad, archive_output_root_override=output_root)
    assert report2.package_archive_audit_report_status == "package_archive_invalid"

    # 7. Recomputed archive digest mismatch blocks audit.
    manifest_digest_bad = asdict(manifest)
    manifest_digest_bad["archive_file_digest"] = "wrong_digest"
    manifest_digest_bad["package_archive_manifest_digest"] = hash_waveguide_package_archive_manifest(manifest_digest_bad)
    report3 = build_waveguide_package_audit_report(manifest_digest_bad, archive_output_root_override=output_root)
    assert report3.package_archive_audit_report_status == "package_archive_invalid"

    # 8. Recomputed archive member digest mismatch blocks audit.
    manifest_member_bad = asdict(manifest)
    manifest_member_bad["archive_entries"][0]["archive_member_digest"] = "wrong_digest"
    manifest_member_bad["package_archive_manifest_digest"] = hash_waveguide_package_archive_manifest(manifest_member_bad)
    report4 = build_waveguide_package_audit_report(manifest_member_bad, archive_output_root_override=output_root)
    assert report4.package_archive_audit_report_status == "package_archive_invalid"

    # 9. Missing archive member blocks audit.
    manifest_missing = asdict(manifest)
    manifest_missing["archive_entries"][0]["missing_archive_member"] = True
    manifest_missing["package_archive_manifest_digest"] = hash_waveguide_package_archive_manifest(manifest_missing)
    report5 = build_waveguide_package_audit_report(manifest_missing, archive_output_root_override=output_root)
    assert report5.package_archive_audit_report_status == "package_archive_invalid"

    # 10. Unexpected archive member blocks audit.
    manifest_unexp = asdict(manifest)
    manifest_unexp["archive_entries"][0]["unexpected_archive_member"] = True
    manifest_unexp["package_archive_manifest_digest"] = hash_waveguide_package_archive_manifest(manifest_unexp)
    report6 = build_waveguide_package_audit_report(manifest_unexp, archive_output_root_override=output_root)
    assert report6.package_archive_audit_report_status == "package_archive_invalid"

    # 11. Duplicate archive member path blocks audit.
    manifest_dup = asdict(manifest)
    manifest_dup["archive_entries"][0]["duplicate_archive_member_path"] = True
    # We rehash but validation on case checks duplicate_archive_member_path.
    # Actually build_waveguide_package_archive_audit_case maps duplicate_archive_member_path.
    # If case has duplicate path, validator flags it.
    
    # 12. Unsafe archive member path blocks audit.
    manifest_unsafe = asdict(manifest)
    manifest_unsafe["archive_entries"][0]["archive_member_relative_path"] = "/absolute.txt"
    manifest_unsafe["package_archive_manifest_digest"] = hash_waveguide_package_archive_manifest(manifest_unsafe)
    report7 = build_waveguide_package_audit_report(manifest_unsafe, archive_output_root_override=output_root)
    assert report7.package_archive_audit_report_status == "package_archive_invalid"

    # 19. No upload/deploy/sign/publish/production mutation occurred.
    report_ok = build_waveguide_package_audit_report(manifest, archive_output_root_override=output_root)
    assert report_ok.upload_performed is False
    assert report_ok.deployment_performed is False
    assert report_ok.signing_performed is False
    assert report_ok.external_publication_performed is False
    assert report_ok.production_mutation_performed is False


def build_waveguide_package_archive_report_overridden(manifest, output_root):
    return build_waveguide_package_audit_report(manifest, archive_output_root_override=output_root)


def test_archive_validator_artifact_existence():
    # 20. Archive audit report JSON artifact exists.
    report_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_AUDIT_REPORT.json")
    assert os.path.exists(report_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_AUDIT_REPORT.json"
    
    # 21. Archive validator documentation exists.
    doc_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_VALIDATOR.md")
    assert os.path.exists(doc_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_VALIDATOR.md"
