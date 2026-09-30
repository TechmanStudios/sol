# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Execution Plan.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_execution_plan import (
    WaveguidePackageAssemblyExecutionStep,
    WaveguidePackageAssemblyExecutionPlan,
    build_waveguide_package_assembly_execution_step,
    validate_waveguide_package_assembly_execution_step,
    build_waveguide_package_assembly_execution_plan,
    validate_waveguide_package_assembly_execution_plan,
    summarize_waveguide_package_assembly_execution_plan,
    export_waveguide_package_assembly_execution_plan,
    compare_waveguide_package_assembly_execution_plans,
    hash_waveguide_package_assembly_execution_step,
    hash_waveguide_package_assembly_execution_plan,
    index_waveguide_execution_steps_by_type,
    index_waveguide_execution_steps_by_status,
    index_waveguide_execution_steps_by_phase
)


@pytest.fixture
def clean_execution_plan_inputs() -> tuple[dict, dict]:
    preflight_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_PREFLIGHT_AUTHORIZATION_AUDIT_REPORT.json")
    readiness_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_FINAL_PACKAGE_READINESS_AUDIT_REPORT.json")

    assert os.path.exists(preflight_path), "Missing preflight authorization audit report JSON"
    assert os.path.exists(readiness_path), "Missing final package readiness audit report JSON"

    with open(preflight_path, "r", encoding="utf-8") as f:
        preflight = json.load(f)
    with open(readiness_path, "r", encoding="utf-8") as f:
        readiness = json.load(f)

    return preflight, readiness


def test_execution_step_building_and_validation(clean_execution_plan_inputs):
    # 1. Package assembly execution step can be built.
    step = build_waveguide_package_assembly_execution_step(
        step_id="SOL-WAVEGUIDE-EXECUTION-STEP-TEST",
        index=99,
        name="Test Step",
        stype="prepare_metadata_instruction",
        phase="instruction_planning",
        source_digest="digest123",
        source_path="source/path.py",
        input_kind="source_artifact",
        output_ref="target/path.py",
        output_kind="target_artifact",
        section="source/",
        tpath="target/path.py",
        adigest="digest123",
        atype="python_module",
        role="implementation_source",
        scope="Shared",
        preflight_report_digest="report_digest_123"
    )
    assert isinstance(step, WaveguidePackageAssemblyExecutionStep)
    assert step.package_execution_step_id == "SOL-WAVEGUIDE-EXECUTION-STEP-TEST"

    # 2. Package assembly execution step validates.
    ok, reasons = validate_waveguide_package_assembly_execution_step(step)
    assert ok is True
    assert "PACKAGE_EXECUTION_STEP_DIGEST_VALID" in reasons


def test_execution_step_digest_determinism_and_exclusion():
    step1 = build_waveguide_package_assembly_execution_step(
        step_id="SOL-WAVEGUIDE-EXECUTION-STEP-TEST",
        index=99,
        name="Test Step",
        stype="prepare_metadata_instruction",
        phase="instruction_planning",
        source_digest="digest123",
        source_path="source/path.py",
        input_kind="source_artifact",
        output_ref="target/path.py",
        output_kind="target_artifact",
        section="source/",
        tpath="target/path.py",
        adigest="digest123",
        atype="python_module",
        role="implementation_source",
        scope="Shared",
        preflight_report_digest="report_digest_123"
    )

    step2 = build_waveguide_package_assembly_execution_step(
        step_id="SOL-WAVEGUIDE-EXECUTION-STEP-TEST",
        index=99,
        name="Test Step",
        stype="prepare_metadata_instruction",
        phase="instruction_planning",
        source_digest="digest123",
        source_path="source/path.py",
        input_kind="source_artifact",
        output_ref="target/path.py",
        output_kind="target_artifact",
        section="source/",
        tpath="target/path.py",
        adigest="digest123",
        atype="python_module",
        role="implementation_source",
        scope="Shared",
        preflight_report_digest="report_digest_123"
    )

    # 3. Execution step digest is deterministic.
    assert step1.package_execution_step_digest == step2.package_execution_step_digest

    # 4. package_execution_step_digest is excluded from its own digest input.
    step_dict = asdict(step1)
    step_dict["package_execution_step_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_package_assembly_execution_step(step_dict)
    assert recomputed == step1.package_execution_step_digest


def test_execution_step_validation_failures():
    step = build_waveguide_package_assembly_execution_step(
        step_id="SOL-WAVEGUIDE-EXECUTION-STEP-TEST",
        index=99,
        name="Test Step",
        stype="prepare_metadata_instruction",
        phase="instruction_planning",
        source_digest="digest123",
        source_path="source/path.py",
        input_kind="source_artifact",
        output_ref="target/path.py",
        output_kind="target_artifact",
        section="source/",
        tpath="target/path.py",
        adigest="digest123",
        atype="python_module",
        role="implementation_source",
        scope="Shared",
        preflight_report_digest="report_digest_123"
    )

    # 5. Physical execution performed true blocks step validation.
    bad_step = asdict(step)
    bad_step["physical_execution_performed"] = True
    bad_step["package_execution_step_digest"] = hash_waveguide_package_assembly_execution_step(bad_step)
    ok, reasons = validate_waveguide_package_assembly_execution_step(bad_step)
    assert ok is False
    assert any("MUTATION" in r for r in reasons)

    # 6-13. Various physical mutation flags true block step validation.
    mutation_flags = [
        "archive_created", "file_copied", "directory_created",
        "upload_performed", "deployment_performed", "signing_performed",
        "external_publication_performed", "production_mutation_performed"
    ]
    for flag in mutation_flags:
        bad_step = asdict(step)
        bad_step[flag] = True
        bad_step["package_execution_step_digest"] = hash_waveguide_package_assembly_execution_step(bad_step)
        ok, reasons = validate_waveguide_package_assembly_execution_step(bad_step)
        assert ok is False
        assert any("MUTATION" in r for r in reasons)

    # 14. Missing guard conditions blocks step validation.
    bad_step = asdict(step)
    bad_step["guard_conditions"] = []
    bad_step["package_execution_step_digest"] = hash_waveguide_package_assembly_execution_step(bad_step)
    ok, reasons = validate_waveguide_package_assembly_execution_step(bad_step)
    assert ok is False

    # 15. Missing prohibited operations blocks step validation.
    bad_step = asdict(step)
    bad_step["prohibited_operations"] = []
    bad_step["package_execution_step_digest"] = hash_waveguide_package_assembly_execution_step(bad_step)
    ok, reasons = validate_waveguide_package_assembly_execution_step(bad_step)
    assert ok is False

    # 16. Missing no-op boundary blocks step validation.
    bad_step = asdict(step)
    bad_step["no_op_boundary"] = False
    bad_step["package_execution_step_digest"] = hash_waveguide_package_assembly_execution_step(bad_step)
    ok, reasons = validate_waveguide_package_assembly_execution_step(bad_step)
    assert ok is False


def test_execution_plan_building_and_validation(clean_execution_plan_inputs):
    preflight, readiness = clean_execution_plan_inputs

    # 17. Package assembly execution plan can be built.
    plan = build_waveguide_package_assembly_execution_plan(preflight, readiness)
    assert isinstance(plan, WaveguidePackageAssemblyExecutionPlan)
    assert plan.package_assembly_execution_plan_status == "package_execution_plan_ready"

    # 18. Package assembly execution plan validates.
    ok, reasons = validate_waveguide_package_assembly_execution_plan(plan)
    assert ok is True
    assert "PACKAGE_EXECUTION_PLAN_READY" in reasons


def test_execution_plan_digest_determinism_and_exclusion(clean_execution_plan_inputs):
    preflight, readiness = clean_execution_plan_inputs

    # 19. Execution plan digest is deterministic.
    plan1 = build_waveguide_package_assembly_execution_plan(preflight, readiness)
    plan2 = build_waveguide_package_assembly_execution_plan(preflight, readiness)
    assert plan1.package_assembly_execution_plan_digest == plan2.package_assembly_execution_plan_digest

    # 20. package_assembly_execution_plan_digest is excluded from its own digest input.
    plan_dict = asdict(plan1)
    plan_dict["package_assembly_execution_plan_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_package_assembly_execution_plan(plan_dict)
    assert recomputed == plan1.package_assembly_execution_plan_digest


def test_execution_plan_failures(clean_execution_plan_inputs):
    preflight, readiness = clean_execution_plan_inputs

    # 21. Source preflight authorization report validation failure blocks plan.
    bad_preflight = dict(preflight)
    bad_preflight["preflight_authorization_report_digest"] = "invalid"
    plan = build_waveguide_package_assembly_execution_plan(bad_preflight, readiness)
    assert plan.package_assembly_execution_plan_status == "package_execution_plan_invalid"
    assert "PACKAGE_EXECUTION_SOURCE_PREFLIGHT_INVALID" in plan.reason_codes

    # 22. Source preflight authorization report status not verified blocks plan.
    bad_preflight_status = dict(preflight)
    bad_preflight_status["preflight_authorization_report_status"] = "package_preflight_authorization_blocked"
    # Ensure it validates but has blocked status
    bad_preflight_status["preflight_authorization_report_digest"] = hash_waveguide_package_assembly_execution_plan(bad_preflight_status)
    plan = build_waveguide_package_assembly_execution_plan(bad_preflight_status, readiness)
    assert plan.package_assembly_execution_plan_status == "package_execution_plan_invalid"


def test_execution_plan_structural_properties(clean_execution_plan_inputs):
    preflight, readiness = clean_execution_plan_inputs
    plan = build_waveguide_package_assembly_execution_plan(preflight, readiness)

    # 25. Planned/blocked/warning/invalid step counts are correct.
    assert plan.planned_execution_step_count == 31  # 28 file steps + 1 setup + 1 boundary + 1 blueprint
    assert plan.blocked_execution_step_count == 0
    assert plan.warning_execution_step_count == 0
    assert plan.invalid_execution_step_count == 0

    # 26-27. Input/Output reference counts correct.
    assert plan.planned_input_reference_count == 28
    assert plan.planned_output_reference_count == 28

    # 28-37. Sorting and determinism.
    assert plan.target_package_sections == sorted(plan.target_package_sections)
    assert plan.execution_step_types_indexed == sorted(plan.execution_step_types_indexed)
    assert plan.execution_step_phases_indexed == sorted(plan.execution_step_phases_indexed)
    assert plan.package_roles_indexed == sorted(plan.package_roles_indexed)
    assert plan.artifact_types_indexed == sorted(plan.artifact_types_indexed)
    assert plan.rc_scopes_indexed == sorted(plan.rc_scopes_indexed)
    assert plan.source_reference_digests == sorted(plan.source_reference_digests)
    assert plan.source_reference_paths == sorted(plan.source_reference_paths)
    assert plan.target_package_paths == sorted(plan.target_package_paths)
    assert plan.planned_output_references == sorted(plan.planned_output_references)

    # 38-40. Execution guard matrix and indexes complete.
    assert len(plan.execution_guard_matrix) > 0
    assert plan.execution_guard_matrix == sorted(plan.execution_guard_matrix)
    assert len(plan.execution_input_reference_index) == 28
    assert len(plan.execution_output_reference_index) == 28

    # 41-45. Flags and policy blocks
    assert plan.noop_sandbox_boundary["physical_execution_performed"] is False
    assert plan.noop_sandbox_boundary["archive_creation_performed"] is False
    assert plan.rollback_noop_policy["rollback_required"] is False
    assert all(v == 0 for v in plan.blocked_operation_attempt_counts.values())
    assert plan.physical_execution_performed is False
    assert plan.archive_creation_performed is False
    assert plan.file_copy_performed is False

    # 46. Summary output.
    summary = summarize_waveguide_package_assembly_execution_plan(plan)
    assert "SOL Waveguide Package Assembly Execution Plan Summary" in summary

    # 47. JSON export.
    export_path = "docs/test_execution_plan.json"
    export_waveguide_package_assembly_execution_plan(plan, export_path)
    full_export_path = os.path.join(REPO_ROOT, export_path)
    assert os.path.exists(full_export_path)
    with open(full_export_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["package_assembly_execution_plan_digest"] == plan.package_assembly_execution_plan_digest
    os.remove(full_export_path)
