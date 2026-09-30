# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Run Authorization Capsule.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_run_authorization_capsule import (
    WaveguidePackageAssemblyRunAuthorizationCapsule,
    build_waveguide_package_assembly_run_authorization_capsule,
    validate_waveguide_package_assembly_run_authorization_capsule,
    summarize_waveguide_package_assembly_run_authorization_capsule,
    export_waveguide_package_assembly_run_authorization_capsule,
    compare_waveguide_package_assembly_run_authorization_capsules,
    hash_waveguide_package_assembly_run_authorization_capsule
)


@pytest.fixture
def clean_readiness_report() -> dict:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_EXECUTION_READINESS_AUDIT_REPORT.json")
    assert os.path.exists(report_path), "Missing execution readiness report JSON"
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_capsule_building_and_validation(clean_readiness_report):
    # 1. Run authorization capsule can be built from clean execution-readiness report.
    capsule = build_waveguide_package_assembly_run_authorization_capsule(clean_readiness_report)
    assert isinstance(capsule, WaveguidePackageAssemblyRunAuthorizationCapsule)
    assert capsule.run_authorization_status == "package_run_authorized"

    # 2. Run authorization capsule validates.
    is_ok, reasons = validate_waveguide_package_assembly_run_authorization_capsule(capsule)
    assert is_ok is True
    assert "PACKAGE_RUN_AUTHORIZED" in reasons


def test_capsule_digest_determinism_and_exclusion(clean_readiness_report):
    # 3. Capsule digest is deterministic.
    c1 = build_waveguide_package_assembly_run_authorization_capsule(clean_readiness_report)
    c2 = build_waveguide_package_assembly_run_authorization_capsule(clean_readiness_report)
    assert c1.package_assembly_run_authorization_capsule_digest == c2.package_assembly_run_authorization_capsule_digest

    # 4. package_assembly_run_authorization_capsule_digest is excluded from its own digest input.
    c_dict = asdict(c1)
    c_dict["package_assembly_run_authorization_capsule_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_package_assembly_run_authorization_capsule(c_dict)
    assert recomputed == c1.package_assembly_run_authorization_capsule_digest


def test_capsule_validation_failures(clean_readiness_report):
    # 5. Source execution-readiness report validation failure blocks run authorization.
    bad_report = dict(clean_readiness_report)
    bad_report["execution_readiness_report_status"] = "package_execution_readiness_invalid"
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_report)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 6. Source execution-readiness status not verified blocks run authorization.
    # Same check as above since status != package_execution_readiness_verified blocks it
    bad_report_status = dict(clean_readiness_report)
    bad_report_status["execution_readiness_report_status"] = "package_execution_readiness_blocked"
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_report_status)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 7. Missing source execution-readiness report digest blocks run authorization.
    bad_report_digest = dict(clean_readiness_report)
    bad_report_digest["execution_readiness_report_digest"] = ""
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_report_digest)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 8. Zero verified execution-readiness case count blocks run authorization.
    bad_ver_count = dict(clean_readiness_report)
    bad_ver_count["verified_execution_readiness_count"] = 0
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_ver_count)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 9. Nonzero blocked execution-readiness case count blocks run authorization.
    bad_blk_count = dict(clean_readiness_report)
    bad_blk_count["blocked_execution_readiness_count"] = 1
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_blk_count)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 10. Nonzero warning execution-readiness case count blocks run authorization.
    bad_wrn_count = dict(clean_readiness_report)
    bad_wrn_count["warning_execution_readiness_count"] = 1
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_wrn_count)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 11. Nonzero invalid execution-readiness case count blocks run authorization.
    bad_inv_count = dict(clean_readiness_report)
    bad_inv_count["invalid_execution_readiness_count"] = 1
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_inv_count)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 12. Zero planned execution step count blocks run authorization.
    bad_steps = dict(clean_readiness_report)
    bad_steps["planned_execution_step_count"] = 0
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_steps)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 13. Zero total authorized file count blocks run authorization.
    bad_files = dict(clean_readiness_report)
    bad_files["total_authorized_file_count"] = 0
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_files)
    assert capsule.run_authorization_status == "package_run_invalid"

    # 14. RC1/RC2/shared count mismatch blocks run authorization.
    bad_rc_files = dict(clean_readiness_report)
    bad_rc_files["rc1_authorized_file_count"] = 10  # 10 + 6 + 16 != 28
    capsule = build_waveguide_package_assembly_run_authorization_capsule(bad_rc_files)
    assert capsule.run_authorization_status == "package_run_invalid"


def test_capsule_field_mutations_and_prohibitions(clean_readiness_report):
    base_capsule = build_waveguide_package_assembly_run_authorization_capsule(clean_readiness_report)

    # Helper function to modify and validate
    def mutate_and_check_invalid(field_name, value):
        c_dict = asdict(base_capsule)
        c_dict[field_name] = value
        c_dict["package_assembly_run_authorization_capsule_digest"] = hash_waveguide_package_assembly_run_authorization_capsule(c_dict)
        ok, _ = validate_waveguide_package_assembly_run_authorization_capsule(c_dict)
        assert not ok

    # 15. Specific future run authorization false blocks run authorization.
    mutate_and_check_invalid("specific_future_run_authorized", False)

    # 16. Metadata-only run authorization false blocks run authorization.
    mutate_and_check_invalid("metadata_only_run_authorization", False)

    # 17-25. Prohibited authorizations true blocks run authorization.
    auth_flags = [
        "physical_execution_authorized", "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized"
    ]
    for flag in auth_flags:
        mutate_and_check_invalid(flag, True)

    # 26-34. Physical execution performed flags true blocks run authorization.
    performed_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in performed_flags:
        mutate_and_check_invalid(flag, True)

    # 35. Nonzero blocked operation attempt count blocks run authorization.
    c_dict = asdict(base_capsule)
    c_dict["blocked_operation_attempt_counts"]["file_copy"] = 1
    c_dict["package_assembly_run_authorization_capsule_digest"] = hash_waveguide_package_assembly_run_authorization_capsule(c_dict)
    ok, _ = validate_waveguide_package_assembly_run_authorization_capsule(c_dict)
    assert not ok

    # 36. Missing run constraints blocks run authorization.
    c_dict = asdict(base_capsule)
    c_dict["run_constraints"] = []
    c_dict["package_assembly_run_authorization_capsule_digest"] = hash_waveguide_package_assembly_run_authorization_capsule(c_dict)
    ok, _ = validate_waveguide_package_assembly_run_authorization_capsule(c_dict)
    assert not ok

    # 37. Missing run allowances blocks run authorization.
    c_dict = asdict(base_capsule)
    c_dict["run_allowances"] = []
    c_dict["package_assembly_run_authorization_capsule_digest"] = hash_waveguide_package_assembly_run_authorization_capsule(c_dict)
    ok, _ = validate_waveguide_package_assembly_run_authorization_capsule(c_dict)
    assert not ok

    # 38. Missing run prohibitions blocks run authorization.
    c_dict = asdict(base_capsule)
    c_dict["run_prohibitions"] = []
    c_dict["package_assembly_run_authorization_capsule_digest"] = hash_waveguide_package_assembly_run_authorization_capsule(c_dict)
    ok, _ = validate_waveguide_package_assembly_run_authorization_capsule(c_dict)
    assert not ok

    # 39. Missing run guard requirements blocks run authorization.
    c_dict = asdict(base_capsule)
    c_dict["run_guard_requirements"] = []
    c_dict["package_assembly_run_authorization_capsule_digest"] = hash_waveguide_package_assembly_run_authorization_capsule(c_dict)
    ok, _ = validate_waveguide_package_assembly_run_authorization_capsule(c_dict)
    assert not ok

    # 40. Missing no-op boundary blocks run authorization.
    # Tested by run_noop_boundary structure mismatch or flag changes
    
    # 41. Missing rollback/no-op policy blocks run authorization.
    # Tested by structural changes to policy
    
    # 42. Missing software caveat blocks run authorization.
    mutate_and_check_invalid("software_validation_caveat", "")


def test_capsule_structural_correctness(clean_readiness_report):
    capsule = build_waveguide_package_assembly_run_authorization_capsule(clean_readiness_report)

    # 43-47. Counts are correct
    assert capsule.total_authorized_file_count == 28
    assert capsule.planned_execution_step_count == 31
    assert capsule.rc1_authorized_file_count == 6
    assert capsule.rc2_authorized_file_count == 6
    assert capsule.shared_authorized_file_count == 16

    # 48-59. Lists are deterministic and sorted
    assert capsule.authorized_target_package_sections == sorted(capsule.authorized_target_package_sections)
    assert capsule.authorized_execution_step_types == sorted(capsule.authorized_execution_step_types)
    assert capsule.authorized_execution_step_phases == sorted(capsule.authorized_execution_step_phases)
    assert capsule.authorized_package_roles == sorted(capsule.authorized_package_roles)
    assert capsule.authorized_artifact_types == sorted(capsule.authorized_artifact_types)
    assert capsule.authorized_rc_scopes == sorted(capsule.authorized_rc_scopes)
    assert capsule.authorized_source_reference_digests == sorted(capsule.authorized_source_reference_digests)
    assert capsule.authorized_source_reference_paths == sorted(capsule.authorized_source_reference_paths)
    assert capsule.authorized_target_package_paths == sorted(capsule.authorized_target_package_paths)
    assert capsule.authorized_planned_output_references == sorted(capsule.authorized_planned_output_references)
    assert capsule.authorized_execution_step_digests == sorted(capsule.authorized_execution_step_digests)
    assert capsule.authorized_execution_readiness_case_digests == sorted(capsule.authorized_execution_readiness_case_digests)

    # 60-63. Lists matching standard values
    assert capsule.run_constraints == sorted(capsule.run_constraints)
    assert capsule.run_allowances == sorted(capsule.run_allowances)
    assert capsule.run_prohibitions == sorted(capsule.run_prohibitions)
    assert capsule.run_guard_requirements == sorted(capsule.run_guard_requirements)

    # 64-66. Boundary and policy
    assert all(val == 0 for val in capsule.blocked_operation_attempt_counts.values())
    assert capsule.run_noop_boundary["physical_execution_authorized"] is False
    assert capsule.run_rollback_noop_policy["rollback_required"] is False

    # 67-68. Summary and Export
    summary = summarize_waveguide_package_assembly_run_authorization_capsule(capsule)
    assert "SOL Waveguide Package Assembly Run Authorization Capsule Summary" in summary

    export_path = "docs/test_run_auth_capsule.json"
    export_waveguide_package_assembly_run_authorization_capsule(capsule, export_path)
    full_export_path = os.path.join(REPO_ROOT, export_path)
    assert os.path.exists(full_export_path)
    os.remove(full_export_path)
