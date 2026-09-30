# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Manifest.
"""

import os
import json
import pytest
import zipfile
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_plan import build_waveguide_package_archive_plan
from sol_waveguide_package_archive_builder import execute_waveguide_package_archive_build
from sol_waveguide_package_archive_manifest import (
    build_waveguide_package_archive_manifest_entry,
    validate_waveguide_package_archive_manifest_entry,
    build_waveguide_package_archive_manifest,
    validate_waveguide_package_archive_manifest,
    hash_waveguide_package_archive_manifest_entry,
    hash_waveguide_package_archive_manifest,
    WaveguidePackageArchiveManifestEntry,
    WaveguidePackageArchiveManifest
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
def clean_build_record(clean_plan, tmp_path):
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
    return rec, output_root


def test_archive_manifest_entry_lifecycle():
    # 1. Archive manifest entry can be built.
    entry = build_waveguide_package_archive_manifest_entry(
        member_path="docs/test.md",
        zf=None,
        zinfo=None,
        expected_digest="some_digest",
        expected_size=100,
        index=0,
        missing=False
    )
    assert isinstance(entry, WaveguidePackageArchiveManifestEntry)
    
    # 2. Archive manifest entry validates if not missing.
    # Note: we need it to exist or we expect it to fail if it's missing/unexpected/mismatched.
    # Let's verify a mock clean entry.
    entry.archive_member_exists = True
    entry.archive_member_digest = "some_digest"
    entry.archive_member_digest_matches_source = True
    entry.archive_manifest_entry_digest = hash_waveguide_package_archive_manifest_entry(entry)
    ok, errs = validate_waveguide_package_archive_manifest_entry(entry)
    assert ok is True, f"Errors: {errs}"

    # 3. Entry digest is deterministic.
    dig1 = hash_waveguide_package_archive_manifest_entry(entry)
    dig2 = hash_waveguide_package_archive_manifest_entry(entry)
    assert dig1 == dig2
    assert entry.archive_manifest_entry_digest == dig1
    
    # 4. archive_manifest_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["archive_manifest_entry_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_manifest_entry(e_dict) == dig1


def test_archive_manifest_lifecycle(clean_build_record):
    rec, output_root = clean_build_record
    
    # 5. Archive manifest builds from clean archive build record.
    manifest = build_waveguide_package_archive_manifest(rec, archive_output_root_override=output_root)
    assert isinstance(manifest, WaveguidePackageArchiveManifest)
    assert manifest.package_archive_manifest_status == "package_archive_manifest_ready"
    
    # 6. Archive manifest validates.
    ok, errs = validate_waveguide_package_archive_manifest(manifest)
    assert ok is True, f"Errors: {errs}"
    
    # 7. Manifest digest is deterministic.
    dig1 = hash_waveguide_package_archive_manifest(manifest)
    dig2 = hash_waveguide_package_archive_manifest(manifest)
    assert dig1 == dig2
    assert manifest.package_archive_manifest_digest == dig1
    
    # 8. package_archive_manifest_digest is excluded from its own digest input.
    m_dict = asdict(manifest)
    m_dict["package_archive_manifest_digest"] = "MUTATED"
    m_dict["local_staging_output_manifest_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_manifest(m_dict) == dig1

    # 9. Exactly 28 archive members are found.
    assert len(manifest.archive_entries) == 28
    assert manifest.total_archive_member_count == 28


def test_archive_manifest_failures_and_boundaries(clean_build_record, tmp_path):
    rec, output_root = clean_build_record
    
    # 10. Missing archive member marks missing.
    # We mutate build record to have a member path that doesn't exist in the actual ZIP.
    rec_bad = asdict(rec)
    rec_bad["archive_member_records"][0]["archive_member_relative_path"] = "missing_path.md"
    manifest = build_waveguide_package_archive_manifest(rec_bad, archive_output_root_override=output_root)
    assert manifest.missing_archive_entry_count == 1
    assert manifest.archive_entries[0].missing_archive_member is True

    # 11. Unexpected archive member marks unexpected.
    # We build manifest on a ZIP that contains files not listed in build record.
    # Let's create a temporary zip with an unexpected file.
    bad_zip_root = str(tmp_path / "bad_zip_dir")
    os.makedirs(bad_zip_root, exist_ok=True)
    bad_zip_path = os.path.join(bad_zip_root, rec.archive_filename)
    with zipfile.ZipFile(bad_zip_path, "w") as zf:
        # copy all members
        actual_zip = os.path.join(output_root, rec.archive_filename)
        with zipfile.ZipFile(actual_zip, "r") as src_zf:
            for name in src_zf.namelist():
                zf.writestr(name, src_zf.read(name))
        # add unexpected member
        zf.writestr("unexpected.txt", b"unexpected content")
        
    manifest2 = build_waveguide_package_archive_manifest(rec, archive_output_root_override=bad_zip_root)
    assert manifest2.unexpected_archive_entry_count == 1
    assert any(e.unexpected_archive_member for e in manifest2.archive_entries)

    # 12. Digest mismatch marks mismatch.
    # We mutate the expected digest in the build record.
    rec_mismatch = asdict(rec)
    rec_mismatch["archive_member_records"][0]["archive_member_digest_expected"] = "wrong_digest"
    manifest3 = build_waveguide_package_archive_manifest(rec_mismatch, archive_output_root_override=output_root)
    assert manifest3.digest_mismatch_archive_entry_count == 1
    assert manifest3.archive_entries[0].archive_member_digest_matches_source is False

    # 13. No upload/deploy/sign/publish/production mutation occurred.
    assert manifest.upload_performed is False
    assert manifest.deployment_performed is False
    assert manifest.signing_performed is False
    assert manifest.external_publication_performed is False
    assert manifest.production_mutation_performed is False


def test_archive_manifest_artifact_existence():
    # 14. Archive manifest JSON artifact exists.
    manifest_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.json")
    assert os.path.exists(manifest_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.json"
    
    # 15. Archive manifest documentation exists.
    doc_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.md")
    assert os.path.exists(doc_file), "Missing SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.md"
