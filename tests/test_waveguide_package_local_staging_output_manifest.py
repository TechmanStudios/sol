# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Local Staging Output Manifest.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_controlled_local_staging_plan import (
    build_waveguide_package_controlled_local_staging_plan
)
from sol_waveguide_package_controlled_local_staging_runner import (
    execute_waveguide_package_controlled_local_staging_run,
    resolve_waveguide_package_local_staging_root
)
from sol_waveguide_package_local_staging_output_manifest import (
    WaveguidePackageLocalStagingOutputEntry,
    WaveguidePackageLocalStagingOutputManifest,
    build_waveguide_package_local_staging_output_entry,
    validate_waveguide_package_local_staging_output_entry,
    build_waveguide_package_local_staging_output_manifest,
    validate_waveguide_package_local_staging_output_manifest,
    summarize_waveguide_package_local_staging_output_manifest,
    export_waveguide_package_local_staging_output_manifest,
    hash_waveguide_package_local_staging_output_entry,
    hash_waveguide_package_local_staging_output_manifest,
    scan_waveguide_package_local_staging_directory
)


@pytest.fixture
def preflight_report_path() -> str:
    return os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE_AUDIT_REPORT.json")


@pytest.fixture
def assembly_plan_path() -> str:
    return os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_ASSEMBLY_PLAN.json")


@pytest.fixture
def clean_plan(preflight_report_path, assembly_plan_path):
    return build_waveguide_package_controlled_local_staging_plan(preflight_report_path, assembly_plan_path)


@pytest.fixture
def clean_run_record(clean_plan, tmp_path):
    staging_root = str(tmp_path / "staged")
    return execute_waveguide_package_controlled_local_staging_run(
        staging_plan=clean_plan,
        staging_root=staging_root,
        operator_approved=True,
        local_filesystem_scope_confirmed=True
    ), staging_root


def test_output_entry_lifecycle():
    # 1. Local staging output entry can be built.
    entry = build_waveguide_package_local_staging_output_entry(
        output_index=0,
        output_status="local_staging_output_verified",
        source_copy_record_digest="cr_digest",
        source_artifact_path="docs/catalog.json",
        source_artifact_digest_expected="exp_digest",
        target_staging_relative_path="docs/catalog.json",
        target_staged_file_exists=True,
        target_staged_file_digest="exp_digest",
        target_staged_file_size_bytes=100,
        target_digest_matches_source=True,
        target_size_matches_source=True,
        target_path_inside_staging_root=True,
        unexpected_file=False,
        missing_file=False,
        duplicate_target_path=False,
        reason_codes=["VERIFIED"]
    )
    assert isinstance(entry, WaveguidePackageLocalStagingOutputEntry)

    # 2. Local staging output entry validates.
    valid, errors = validate_waveguide_package_local_staging_output_entry(entry)
    assert valid, f"Validation errors: {errors}"

    # 3. Entry digest is deterministic.
    dig1 = hash_waveguide_package_local_staging_output_entry(entry)
    dig2 = hash_waveguide_package_local_staging_output_entry(entry)
    assert dig1 == dig2
    assert entry.local_staging_output_entry_digest == dig1

    # 4. local_staging_output_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["local_staging_output_entry_digest"] = "MUTATED"
    assert hash_waveguide_package_local_staging_output_entry(e_dict) == dig1


def test_output_manifest_lifecycle(clean_run_record):
    run_record, staging_root = clean_run_record

    # 5. Output manifest builds from clean run record.
    manifest = build_waveguide_package_local_staging_output_manifest(run_record, staging_root)
    assert isinstance(manifest, WaveguidePackageLocalStagingOutputManifest)
    assert manifest.local_staging_output_manifest_status == "package_local_staging_manifest_ready"

    # 6. Output manifest validates.
    valid, errors = validate_waveguide_package_local_staging_output_manifest(manifest)
    assert valid, f"Manifest validation failed: {errors}"

    # 7. Manifest digest is deterministic.
    dig1 = hash_waveguide_package_local_staging_output_manifest(manifest)
    dig2 = hash_waveguide_package_local_staging_output_manifest(manifest)
    assert dig1 == dig2
    assert manifest.local_staging_output_manifest_digest == dig1

    # 8. local_staging_output_manifest_digest is excluded from its own digest input.
    m_dict = asdict(manifest)
    m_dict["local_staging_output_manifest_digest"] = "MUTATED"
    assert hash_waveguide_package_local_staging_output_manifest(m_dict) == dig1

    # 9. Exactly 28 staged files are found.
    assert manifest.verified_output_count == 28
    assert manifest.total_staged_file_count == 28


def test_manifest_discrepancies(clean_run_record):
    run_record, staging_root = clean_run_record

    # 10. Missing staged file marks missing.
    # Delete one file from staging root
    norm_root = resolve_waveguide_package_local_staging_root(staging_root)
    first_copy = run_record.copy_records[0]
    file_path = os.path.join(norm_root, first_copy.target_staging_relative_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    manifest_missing = build_waveguide_package_local_staging_output_manifest(run_record, staging_root)
    assert manifest_missing.local_staging_output_manifest_status == "package_local_staging_manifest_blocked"
    assert manifest_missing.missing_output_count == 1

    # 11. Unexpected staged file marks unexpected.
    unexpected_path = os.path.join(norm_root, "unexpected_file.txt")
    with open(unexpected_path, "w", encoding="utf-8") as f:
        f.write("unexpected contents")

    manifest_unexp = build_waveguide_package_local_staging_output_manifest(run_record, staging_root)
    assert manifest_unexp.local_staging_output_manifest_status == "package_local_staging_manifest_blocked"
    assert manifest_unexp.unexpected_output_count == 1

    # 12. Digest mismatch marks mismatch.
    # Mutate a file
    second_copy = run_record.copy_records[1]
    mutate_path = os.path.join(norm_root, second_copy.target_staging_relative_path)
    with open(mutate_path, "w", encoding="utf-8") as f:
        f.write("mutated contents")

    manifest_mismatch = build_waveguide_package_local_staging_output_manifest(run_record, staging_root)
    assert manifest_mismatch.local_staging_output_manifest_status == "package_local_staging_manifest_blocked"
    assert manifest_mismatch.digest_mismatch_output_count == 1

    # 13. No archive/upload/deploy/sign/publish/mutate occurred.
    assert manifest_missing.archive_creation_performed is False
    assert manifest_missing.upload_performed is False
    assert manifest_missing.deployment_performed is False
    assert manifest_missing.signing_performed is False
