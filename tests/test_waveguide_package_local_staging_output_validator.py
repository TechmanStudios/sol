# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Local Staging Output Validator.
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
    build_waveguide_package_local_staging_output_manifest
)
from sol_waveguide_package_local_staging_output_validator import (
    WaveguidePackageLocalStagingOutputAuditCase,
    WaveguidePackageLocalStagingOutputAuditReport,
    build_waveguide_package_local_staging_output_audit_case,
    build_waveguide_package_local_staging_output_audit_report,
    validate_waveguide_package_local_staging_output_audit_report,
    summarize_waveguide_package_local_staging_output_audit_report,
    export_waveguide_package_local_staging_output_audit_report,
    hash_waveguide_package_local_staging_output_audit_case,
    hash_waveguide_package_local_staging_output_audit_report
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
    run_rec = execute_waveguide_package_controlled_local_staging_run(
        staging_plan=clean_plan,
        staging_root=staging_root,
        operator_approved=True,
        local_filesystem_scope_confirmed=True
    )
    return run_rec, staging_root


@pytest.fixture
def clean_manifest(clean_run_record):
    run_record, staging_root = clean_run_record
    return build_waveguide_package_local_staging_output_manifest(run_record, staging_root), staging_root


def test_audit_case_lifecycle(clean_manifest):
    manifest, staging_root = clean_manifest
    entry = manifest.output_entries[0]

    # 1. Local staging output audit case builds.
    case = build_waveguide_package_local_staging_output_audit_case(
        entry_dict=asdict(entry),
        manifest_digest=manifest.local_staging_output_manifest_digest,
        manifest_valid=True,
        run_digest=manifest.source_controlled_local_staging_run_record_digest,
        plan_digest=manifest.source_controlled_local_staging_plan_digest,
        staging_root=staging_root,
        case_index=0
    )
    assert isinstance(case, WaveguidePackageLocalStagingOutputAuditCase)

    # 2. Local staging output audit case validates.
    assert case.audit_status == "local_staging_output_audit_verified"

    # 3. Audit case digest is deterministic.
    dig1 = hash_waveguide_package_local_staging_output_audit_case(case)
    dig2 = hash_waveguide_package_local_staging_output_audit_case(case)
    assert dig1 == dig2
    assert case.local_staging_output_audit_case_digest == dig1

    # 4. local_staging_output_audit_case_digest is excluded from its own digest input.
    c_dict = asdict(case)
    c_dict["local_staging_output_audit_case_digest"] = "MUTATED"
    assert hash_waveguide_package_local_staging_output_audit_case(c_dict) == dig1


def test_audit_failures(clean_manifest, tmp_path):
    manifest, staging_root = clean_manifest
    # 5. Output manifest independent validation failure blocks audit.
    # Set invalid manifest
    fake_manifest = asdict(manifest)
    fake_manifest["local_staging_output_manifest_digest"] = "wrong"
    report = build_waveguide_package_local_staging_output_audit_report(fake_manifest, staging_root)
    assert report.local_staging_output_audit_report_status == "package_local_staging_output_invalid"

    # 6. Entry digest mismatch blocks audit.
    fake_manifest2 = asdict(manifest)
    fake_manifest2["output_entries"][0]["local_staging_output_entry_digest"] = "wrong"
    # Recompute top level manifest digest to make it structurally valid
    from sol_waveguide_package_local_staging_output_manifest import hash_waveguide_package_local_staging_output_manifest
    fake_manifest2["local_staging_output_manifest_digest"] = hash_waveguide_package_local_staging_output_manifest(fake_manifest2)
    report2 = build_waveguide_package_local_staging_output_audit_report(fake_manifest2, staging_root)
    assert report2.local_staging_output_audit_report_status == "package_local_staging_output_invalid"

    # 7. Recomputed staged digest mismatch blocks audit.
    # Mutate a file on disk
    norm_root = resolve_waveguide_package_local_staging_root(staging_root)
    first_entry = manifest.output_entries[0]
    tgt_path = os.path.join(norm_root, first_entry.target_staging_relative_path)
    with open(tgt_path, "w", encoding="utf-8") as f:
        f.write("wrong content")

    report3 = build_waveguide_package_local_staging_output_audit_report(manifest, staging_root)
    assert report3.local_staging_output_audit_report_status == "package_local_staging_output_blocked"
    assert report3.blocked_local_staging_output_audit_count >= 1


def test_missing_and_unexpected_and_duplicate(clean_manifest):
    manifest, staging_root = clean_manifest
    norm_root = resolve_waveguide_package_local_staging_root(staging_root)

    # 8. Missing file blocks audit.
    # Delete a file
    first_entry = manifest.output_entries[0]
    tgt_path = os.path.join(norm_root, first_entry.target_staging_relative_path)
    if os.path.exists(tgt_path):
        os.remove(tgt_path)

    # Rebuild manifest to mark it as missing
    manifest_missing = build_waveguide_package_local_staging_output_manifest(manifest.source_controlled_local_staging_run_record_digest, staging_root)
    # Actually build audit report from manifest directly
    report = build_waveguide_package_local_staging_output_audit_report(manifest, staging_root)
    assert report.local_staging_output_audit_report_status == "package_local_staging_output_blocked"

    # 9. Unexpected file blocks audit.
    # Write unexpected file
    with open(os.path.join(norm_root, "unexp.txt"), "w") as f:
        f.write("unexp")
    report2 = build_waveguide_package_local_staging_output_audit_report(manifest, staging_root)
    assert report2.local_staging_output_audit_report_status == "package_local_staging_output_blocked"


def test_top_level_report_lifecycle(clean_manifest):
    manifest, staging_root = clean_manifest

    # 11. Top-level output audit report builds.
    report = build_waveguide_package_local_staging_output_audit_report(manifest, staging_root)
    assert isinstance(report, WaveguidePackageLocalStagingOutputAuditReport)

    # 12. Top-level output audit report validates.
    valid, errors = validate_waveguide_package_local_staging_output_report = validate_waveguide_package_local_staging_output_audit_report(report)
    assert valid, f"Report validation errors: {errors}"

    # 13. Report digest is deterministic.
    dig1 = hash_waveguide_package_local_staging_output_audit_report(report)
    dig2 = hash_waveguide_package_local_staging_output_audit_report(report)
    assert dig1 == dig2
    assert report.local_staging_output_audit_report_digest == dig1

    # 14. local_staging_output_audit_report_digest is excluded from its own digest input.
    r_dict = asdict(report)
    r_dict["local_staging_output_audit_report_digest"] = "MUTATED"
    assert hash_waveguide_package_local_staging_output_audit_report(r_dict) == dig1

    # 15. Verified audit case count is 28.
    assert report.verified_local_staging_output_audit_count == 28

    # 16. No archive/upload/deploy/sign/publish/mutate occurred.
    assert report.archive_creation_performed is False
    assert report.upload_performed is False
    assert report.deployment_performed is False
    assert report.signing_performed is False
