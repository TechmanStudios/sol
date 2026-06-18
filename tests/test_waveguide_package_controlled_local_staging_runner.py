# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Controlled Local Staging Runner.
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
    WaveguidePackageLocalStagingCopyRecord,
    WaveguidePackageControlledLocalStagingRunRecord,
    build_waveguide_package_controlled_local_staging_run_request,
    execute_waveguide_package_controlled_local_staging_run,
    validate_waveguide_package_controlled_local_staging_run_record,
    summarize_waveguide_package_controlled_local_staging_run_record,
    export_waveguide_package_controlled_local_staging_run_record,
    hash_waveguide_package_local_staging_copy_record,
    hash_waveguide_package_controlled_local_staging_run_record,
    resolve_waveguide_package_local_staging_root,
    validate_waveguide_package_local_staging_target_path
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


def test_runner_approval_guards(clean_plan, tmp_path):
    staging_root = str(tmp_path / "staged")

    # 1. Staging run request without operator approval is blocked and performs no mutation.
    record = execute_waveguide_package_controlled_local_staging_run(
        staging_plan=clean_plan,
        staging_root=staging_root,
        operator_approved=False,
        local_filesystem_scope_confirmed=True
    )
    assert record.controlled_local_staging_run_status == "package_local_staging_run_blocked"
    assert not os.path.exists(staging_root)

    # 2. Staging run request without local filesystem scope confirmation is blocked and performs no mutation.
    record2 = execute_waveguide_package_controlled_local_staging_run(
        staging_plan=clean_plan,
        staging_root=staging_root,
        operator_approved=True,
        local_filesystem_scope_confirmed=False
    )
    assert record2.controlled_local_staging_run_status == "package_local_staging_run_blocked"
    assert not os.path.exists(staging_root)


def test_runner_unsafe_roots(clean_plan):
    # 3. Unsafe staging root is blocked.
    # Staging root equals repository root
    with pytest.raises(ValueError) as excinfo:
        resolve_waveguide_package_local_staging_root(REPO_ROOT)
    assert "repository root" in str(excinfo.value)

    # Staging root equals user home directory
    with pytest.raises(ValueError) as excinfo2:
        resolve_waveguide_package_local_staging_root(os.path.expanduser("~"))
    assert "user home" in str(excinfo2.value)

    # Staging root equals filesystem root
    # Note: On Windows drive root like C:\ or filesystem root
    # We test it raised ValueError in execute run too.
    record = execute_waveguide_package_controlled_local_staging_run(
        staging_plan=clean_plan,
        staging_root=REPO_ROOT,
        operator_approved=True,
        local_filesystem_scope_confirmed=True
    )
    assert record.controlled_local_staging_run_status == "package_local_staging_run_blocked"


def test_runner_target_path_escape(clean_plan, tmp_path):
    staging_root = str(tmp_path / "staged")
    # 4. Target path escape is blocked.
    assert not validate_waveguide_package_local_staging_target_path(staging_root, "../escape.json")


def test_runner_successful_execution(clean_plan, tmp_path):
    staging_root = str(tmp_path / "staged")

    # 5. Clean approved run completes in a pytest `tmp_path` staging root.
    record = execute_waveguide_package_controlled_local_staging_run(
        staging_plan=clean_plan,
        staging_root=staging_root,
        operator_approved=True,
        local_filesystem_scope_confirmed=True
    )
    assert record.controlled_local_staging_run_status == "package_local_staging_run_completed"
    assert os.path.exists(staging_root)

    # 6. Exactly 28 files are copied.
    assert len(record.copy_records) == 28
    assert record.copied_file_count == 28

    # 7. All copied files match source digests.
    for r in record.copy_records:
        assert r.copy_status == "local_staging_copy_completed"
        assert r.target_digest_matches_source

    # 8. Copy record digest is deterministic.
    cr = record.copy_records[0]
    dig1 = hash_waveguide_package_local_staging_copy_record(cr)
    dig2 = hash_waveguide_package_local_staging_copy_record(cr)
    assert dig1 == dig2

    # 9. local_staging_copy_record_digest is excluded from its own digest input.
    cr_dict = asdict(cr)
    cr_dict["local_staging_copy_record_digest"] = "MUTATED"
    assert hash_waveguide_package_local_staging_copy_record(cr_dict) == dig1

    # 10. Run record digest is deterministic.
    dig3 = hash_waveguide_package_controlled_local_staging_run_record(record)
    dig4 = hash_waveguide_package_controlled_local_staging_run_record(record)
    assert dig3 == dig4

    # 11. controlled_local_staging_run_record_digest is excluded from its own digest input.
    rr_dict = asdict(record)
    rr_dict["controlled_local_staging_run_record_digest"] = "MUTATED"
    assert hash_waveguide_package_controlled_local_staging_run_record(rr_dict) == dig3

    # 12. No archive/upload/deploy/sign/publish/mutate occurred.
    assert record.archive_creation_performed is False
    assert record.upload_performed is False
    assert record.deployment_performed is False
    assert record.signing_performed is False
    assert record.external_publication_performed is False
    assert record.production_mutation_performed is False
    assert record.archive_created_count == 0
    assert record.upload_count == 0
    assert record.deployment_count == 0
    assert record.signing_count == 0
    assert record.external_publication_count == 0
    assert record.production_mutation_count == 0
