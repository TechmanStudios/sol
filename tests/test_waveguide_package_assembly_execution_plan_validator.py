# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Execution Plan Validator.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_execution_plan import (
    hash_waveguide_package_assembly_execution_plan,
    hash_waveguide_package_assembly_execution_step
)
from sol_waveguide_package_assembly_execution_plan_validator import (
    WaveguidePackageExecutionReadinessAuditCase,
    WaveguidePackageExecutionReadinessAuditReport,
    build_waveguide_package_execution_readiness_audit_case,
    validate_waveguide_package_assembly_execution_plan_independently,
    build_waveguide_package_execution_readiness_audit_report,
    validate_waveguide_package_execution_readiness_audit_report,
    summarize_waveguide_package_execution_readiness_audit_report,
    export_waveguide_package_execution_readiness_audit_report,
    compare_waveguide_package_execution_readiness_audit_reports,
    hash_waveguide_package_execution_readiness_audit_case,
    hash_waveguide_package_execution_readiness_audit_report,
    recompute_waveguide_package_assembly_execution_plan_digest,
    recompute_waveguide_package_execution_step_digest,
    validate_waveguide_package_execution_step_sequence,
    validate_waveguide_package_execution_guard_matrix,
    validate_waveguide_package_execution_input_reference_index,
    validate_waveguide_package_execution_output_reference_index,
    validate_waveguide_package_execution_noop_boundary,
    validate_waveguide_package_execution_rollback_noop_policy,
    index_waveguide_execution_readiness_cases_by_status,
    index_waveguide_execution_readiness_cases_by_step_type,
    index_waveguide_execution_readiness_cases_by_phase
)


@pytest.fixture
def clean_validator_inputs() -> tuple[dict, dict]:
    plan_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_EXECUTION_PLAN.json")
    preflight_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_PREFLIGHT_AUTHORIZATION_AUDIT_REPORT.json")

    assert os.path.exists(plan_path), "Missing execution plan JSON"
    assert os.path.exists(preflight_path), "Missing preflight authorization report JSON"

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    with open(preflight_path, "r", encoding="utf-8") as f:
        preflight = json.load(f)

    return plan, preflight


def test_readiness_case_building_and_validation(clean_validator_inputs):
    plan, preflight = clean_validator_inputs
    step = plan["execution_steps"][0]

    # 1. Execution-readiness audit case can be built from clean execution step.
    case = build_waveguide_package_execution_readiness_audit_case(step, plan, preflight)
    assert isinstance(case, WaveguidePackageExecutionReadinessAuditCase)
    assert case.execution_readiness_status == "execution_step_readiness_verified"

    # 2. Execution-readiness audit case validates.
    # We validate via report case digest checks
    assert case.execution_plan_digest_match is True
    assert case.package_execution_step_digest_match is True
    assert case.source_preflight_authorization_report_digest_match is True
    assert case.guard_conditions_verified is True
    assert case.prohibited_operations_verified is True


def test_readiness_case_digest_determinism_and_exclusion(clean_validator_inputs):
    plan, preflight = clean_validator_inputs
    step = plan["execution_steps"][0]

    # 3. Execution-readiness audit case digest is deterministic.
    c1 = build_waveguide_package_execution_readiness_audit_case(step, plan, preflight)
    c2 = build_waveguide_package_execution_readiness_audit_case(step, plan, preflight)
    assert c1.execution_readiness_case_digest == c2.execution_readiness_case_digest

    # 4. execution_readiness_case_digest is excluded from its own digest input.
    c_dict = asdict(c1)
    c_dict["execution_readiness_case_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_package_execution_readiness_audit_case(c_dict)
    assert recomputed == c1.execution_readiness_case_digest


def test_readiness_case_failures(clean_validator_inputs):
    plan, preflight = clean_validator_inputs
    step = plan["execution_steps"][0]

    # 5. Execution plan digest mismatch blocks/fails readiness audit.
    bad_plan = dict(plan)
    bad_plan["package_assembly_execution_plan_digest"] = "mismatched"
    case = build_waveguide_package_execution_readiness_audit_case(step, bad_plan, preflight)
    assert case.execution_readiness_status == "execution_step_readiness_invalid"

    # 6. Execution step digest mismatch blocks/fails readiness audit.
    bad_step = dict(step)
    bad_step["package_execution_step_digest"] = "mismatched"
    case = build_waveguide_package_execution_readiness_audit_case(bad_step, plan, preflight)
    assert case.execution_readiness_status == "execution_step_readiness_invalid"

    # 7. Source preflight authorization report validation failure blocks readiness audit.
    # We can test this by mutating preflight report values
    bad_pf = dict(preflight)
    bad_pf["preflight_authorization_report_status"] = "package_preflight_authorization_invalid"
    case = build_waveguide_package_execution_readiness_audit_case(step, plan, bad_pf)
    assert case.execution_readiness_status == "execution_step_readiness_invalid"

    # 9. Execution plan status not ready blocks readiness audit.
    bad_plan_status = dict(plan)
    bad_plan_status["package_assembly_execution_plan_status"] = "package_execution_plan_invalid"
    case = build_waveguide_package_execution_readiness_audit_case(step, bad_plan_status, preflight)
    assert case.execution_readiness_status == "execution_step_readiness_invalid"

    # 10. Execution step status not planned blocks readiness audit.
    bad_step_status = dict(step)
    bad_step_status["step_status"] = "execution_step_blocked"
    bad_step_status["package_execution_step_digest"] = hash_waveguide_package_assembly_execution_step(bad_step_status)
    case = build_waveguide_package_execution_readiness_audit_case(bad_step_status, plan, preflight)
    assert case.execution_readiness_status == "execution_step_readiness_blocked"

    # 11. Missing guard conditions blocks readiness audit.
    bad_step_guards = dict(step)
    bad_step_guards["guard_conditions"] = []
    case = build_waveguide_package_execution_readiness_audit_case(bad_step_guards, plan, preflight)
    assert case.execution_readiness_status == "execution_step_readiness_invalid"

    # 12. Missing prohibited operations blocks readiness audit.
    bad_step_prohibits = dict(step)
    bad_step_prohibits["prohibited_operations"] = []
    case = build_waveguide_package_execution_readiness_audit_case(bad_step_prohibits, plan, preflight)
    assert case.execution_readiness_status == "execution_step_readiness_invalid"

    # 15. Physical execution true blocks readiness audit.
    mutations = [
        "physical_execution_performed", "archive_created", "file_copied", "directory_created",
        "upload_performed", "deployment_performed", "signing_performed",
        "external_publication_performed", "production_mutation_performed"
    ]
    for m in mutations:
        bad_step_mut = dict(step)
        bad_step_mut[m] = True
        case = build_waveguide_package_execution_readiness_audit_case(bad_step_mut, plan, preflight)
        assert case.execution_readiness_status == "execution_step_readiness_invalid"


def test_readiness_report_building_and_validation(clean_validator_inputs):
    plan, preflight = clean_validator_inputs

    # 26. Top-level execution-readiness audit report can be built.
    report = build_waveguide_package_execution_readiness_audit_report(plan, preflight)
    assert isinstance(report, WaveguidePackageExecutionReadinessAuditReport)
    assert report.execution_readiness_report_status == "package_execution_readiness_verified"

    # 27. Top-level execution-readiness audit report validates.
    ok, reasons = validate_waveguide_package_execution_readiness_audit_report(report)
    assert ok is True
    assert "PACKAGE_EXECUTION_READINESS_VERIFIED" in reasons


def test_readiness_report_digest_determinism_and_exclusion(clean_validator_inputs):
    plan, preflight = clean_validator_inputs

    # 28. Execution-readiness report digest is deterministic.
    rep1 = build_waveguide_package_execution_readiness_audit_report(plan, preflight)
    rep2 = build_waveguide_package_execution_readiness_audit_report(plan, preflight)
    assert rep1.execution_readiness_report_digest == rep2.execution_readiness_report_digest

    # 29. execution_readiness_report_digest is excluded from its own digest input.
    r_dict = asdict(rep1)
    r_dict["execution_readiness_report_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_package_execution_readiness_audit_report(r_dict)
    assert recomputed == rep1.execution_readiness_report_digest


def test_readiness_report_structural_properties(clean_validator_inputs):
    plan, preflight = clean_validator_inputs
    report = build_waveguide_package_execution_readiness_audit_report(plan, preflight)

    # 30-31. Counts are correct
    assert report.verified_execution_readiness_count == 31
    assert report.planned_execution_step_count == 31
    assert report.total_authorized_file_count == 28
    assert report.rc1_authorized_file_count == 6
    assert report.rc2_authorized_file_count == 6
    assert report.shared_authorized_file_count == 16
    assert report.planned_input_reference_count == 28
    assert report.planned_output_reference_count == 28

    # 38-49. Sorting and indexes
    assert report.target_package_sections == sorted(report.target_package_sections)
    assert report.execution_step_types_indexed == sorted(report.execution_step_types_indexed)
    assert report.execution_step_phases_indexed == sorted(report.execution_step_phases_indexed)
    assert report.package_roles_indexed == sorted(report.package_roles_indexed)
    assert report.artifact_types_indexed == sorted(report.artifact_types_indexed)
    assert report.rc_scopes_indexed == sorted(report.rc_scopes_indexed)
    assert report.source_reference_digests == sorted(report.source_reference_digests)
    assert report.source_reference_paths == sorted(report.source_reference_paths)
    assert report.target_package_paths == sorted(report.target_package_paths)
    assert report.planned_output_references == sorted(report.planned_output_references)
    assert report.execution_step_digests == sorted(report.execution_step_digests)
    assert report.execution_readiness_case_digests == sorted(report.execution_readiness_case_digests)

    # 50. Step sequence verification
    assert report.execution_guard_matrix_verified is True
    assert report.execution_input_reference_index_verified is True
    assert report.execution_output_reference_index_verified is True
    assert report.noop_sandbox_boundary_verified is True
    assert report.rollback_noop_policy_verified is True
    assert all(v == 0 for v in report.blocked_operation_attempt_counts.values())
    assert report.physical_execution_performed is False

    # Summary and Export
    summary = summarize_waveguide_package_execution_readiness_audit_report(report)
    assert "SOL Waveguide Package Execution Readiness Audit Report Summary" in summary

    export_path = "docs/test_readiness_report.json"
    export_waveguide_package_execution_readiness_audit_report(report, export_path)
    full_export_path = os.path.join(REPO_ROOT, export_path)
    assert os.path.exists(full_export_path)
    os.remove(full_export_path)
