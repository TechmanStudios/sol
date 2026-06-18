# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Run Execution Blueprint.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_run_execution_blueprint import (
    WaveguidePackageRunBlueprintPhase,
    WaveguidePackageAssemblyRunExecutionBlueprint,
    build_waveguide_package_run_blueprint_phase,
    validate_waveguide_package_run_blueprint_phase,
    build_waveguide_package_assembly_run_execution_blueprint,
    validate_waveguide_package_assembly_run_execution_blueprint,
    summarize_waveguide_package_assembly_run_execution_blueprint,
    export_waveguide_package_assembly_run_execution_blueprint,
    compare_waveguide_package_assembly_run_execution_blueprints,
    hash_waveguide_package_run_blueprint_phase,
    hash_waveguide_package_assembly_run_execution_blueprint
)

@pytest.fixture
def clean_preflight_report() -> dict:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_PREFLIGHT_AUDIT_REPORT.json")
    assert os.path.exists(report_path), "Missing run preflight audit report JSON"
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_run_blueprint_phase_build_and_validation(clean_preflight_report):
    # 1. Run blueprint phase can be built.
    phase = build_waveguide_package_run_blueprint_phase(
        phase_index=0,
        phase_name="Run Preflight Validation",
        phase_type="run_preflight_validation",
        preflight_dict=clean_preflight_report
    )
    assert isinstance(phase, WaveguidePackageRunBlueprintPhase)
    
    # 2. Run blueprint phase validates.
    ok, reasons = validate_waveguide_package_run_blueprint_phase(phase)
    assert ok is True

def test_run_blueprint_phase_digest_determinism_and_exclusion(clean_preflight_report):
    # 3. Phase digest is deterministic.
    p1 = build_waveguide_package_run_blueprint_phase(
        phase_index=0,
        phase_name="Run Preflight Validation",
        phase_type="run_preflight_validation",
        preflight_dict=clean_preflight_report
    )
    p2 = build_waveguide_package_run_blueprint_phase(
        phase_index=0,
        phase_name="Run Preflight Validation",
        phase_type="run_preflight_validation",
        preflight_dict=clean_preflight_report
    )
    assert p1.run_blueprint_phase_digest == p2.run_blueprint_phase_digest
    assert len(p1.run_blueprint_phase_digest) == 64

    # 4. run_blueprint_phase_digest is excluded from its own digest input.
    p_dict = asdict(p1)
    p_dict["run_blueprint_phase_digest"] = "MUTATED_PHASE_SELF_DIGEST"
    recomputed = hash_waveguide_package_run_blueprint_phase(p_dict)
    assert recomputed == p1.run_blueprint_phase_digest

def test_blueprint_phase_validation_failures(clean_preflight_report):
    base_phase = build_waveguide_package_run_blueprint_phase(
        phase_index=0,
        phase_name="Run Preflight Validation",
        phase_type="run_preflight_validation",
        preflight_dict=clean_preflight_report
    )

    def assert_phase_invalid_with_mutation(field_name, value):
        p_dict = asdict(base_phase)
        p_dict[field_name] = value
        p_dict["run_blueprint_phase_digest"] = hash_waveguide_package_run_blueprint_phase(p_dict)
        ok, _ = validate_waveguide_package_run_blueprint_phase(p_dict)
        assert not ok

    # 5. Missing guard conditions blocks phase.
    assert_phase_invalid_with_mutation("required_guard_conditions", [])

    # 6. Missing abort conditions blocks phase.
    assert_phase_invalid_with_mutation("abort_conditions", [])

    # 7. Missing safety gates blocks phase.
    assert_phase_invalid_with_mutation("safety_gates", [])

    # 8. Missing no-op boundary blocks phase.
    assert_phase_invalid_with_mutation("noop_boundary", {})

    # 9. Missing rollback/no-op policy blocks phase.
    assert_phase_invalid_with_mutation("run_rollback_noop_policy", {})

    # 10. Any performed mutation flag true blocks phase.
    performed_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in performed_flags:
        assert_phase_invalid_with_mutation(flag, True)

def test_blueprint_building_and_validation(clean_preflight_report):
    # 11. Top-level run execution blueprint builds.
    blueprint = build_waveguide_package_assembly_run_execution_blueprint(clean_preflight_report)
    assert isinstance(blueprint, WaveguidePackageAssemblyRunExecutionBlueprint)
    assert blueprint.run_blueprint_status == "package_run_blueprint_ready"

    # 12. Top-level run execution blueprint validates.
    ok, reasons = validate_waveguide_package_assembly_run_execution_blueprint(blueprint)
    assert ok is True
    assert "PACKAGE_RUN_BLUEPRINT_READY" in reasons

def test_blueprint_digest_determinism_and_exclusion(clean_preflight_report):
    # 13. Blueprint digest is deterministic.
    b1 = build_waveguide_package_assembly_run_execution_blueprint(clean_preflight_report)
    b2 = build_waveguide_package_assembly_run_execution_blueprint(clean_preflight_report)
    assert b1.package_assembly_run_execution_blueprint_digest == b2.package_assembly_run_execution_blueprint_digest

    # 14. package_assembly_run_execution_blueprint_digest is excluded from its own digest input.
    b_dict = asdict(b1)
    b_dict["package_assembly_run_execution_blueprint_digest"] = "MUTATED_BLUEPRINT_SELF_DIGEST"
    recomputed = hash_waveguide_package_assembly_run_execution_blueprint(b_dict)
    assert recomputed == b1.package_assembly_run_execution_blueprint_digest

def test_blueprint_phase_properties(clean_preflight_report):
    blueprint = build_waveguide_package_assembly_run_execution_blueprint(clean_preflight_report)
    phases = blueprint.blueprint_phases

    # 15. Phase sequence is contiguous.
    for idx, p in enumerate(phases):
        assert p.phase_index == idx

    # 16. Phase count is 34 for clean state.
    assert len(phases) == 34

    # 17. Artifact instruction phases equal authorized file count.
    art_phases = [p for p in phases if p.phase_type == "artifact_instruction_planning"]
    assert len(art_phases) == blueprint.total_authorized_file_count
    assert len(art_phases) == 28

def test_blueprint_matrices_and_boundaries(clean_preflight_report):
    blueprint = build_waveguide_package_assembly_run_execution_blueprint(clean_preflight_report)

    # 18. Abort condition matrix is deterministic.
    assert len(blueprint.abort_condition_matrix) == 10
    assert blueprint.abort_condition_matrix == sorted(blueprint.abort_condition_matrix)

    # 19. Safety gate matrix is deterministic.
    assert len(blueprint.safety_gate_matrix) == 7
    assert blueprint.safety_gate_matrix == sorted(blueprint.safety_gate_matrix)

    # 20. Expected input/output indexes are deterministic.
    assert len(blueprint.expected_input_index) == 28
    assert len(blueprint.expected_output_index) == 28

    # 21. No-op boundary is false-valued.
    for k, v in blueprint.noop_boundary.items():
        assert v is False

    # 22. Rollback/no-op policy is metadata-only.
    assert blueprint.rollback_noop_policy["rollback_required"] is False
    assert blueprint.rollback_noop_policy["rollback_scope"] == "metadata_only"

    # 23. Blocked operation counters are zero.
    for k, v in blueprint.blocked_operation_attempt_counts.items():
        assert v == 0

def test_blueprint_export_and_artifacts(clean_preflight_report):
    blueprint = build_waveguide_package_assembly_run_execution_blueprint(clean_preflight_report)

    # 24. JSON export is deterministic.
    export_path = "docs/test_run_execution_blueprint.json"
    export_waveguide_package_assembly_run_execution_blueprint(blueprint, export_path)
    full_export_path = os.path.join(REPO_ROOT, export_path)
    assert os.path.exists(full_export_path)
    
    with open(full_export_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["package_assembly_run_execution_blueprint_digest"] == blueprint.package_assembly_run_execution_blueprint_digest
    os.remove(full_export_path)

    # 25. Run execution blueprint JSON artifact exists.
    canonical_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_EXECUTION_BLUEPRINT.json")
    assert os.path.exists(canonical_path), "Missing canonical run execution blueprint JSON"

    # 26. Run execution blueprint documentation exists.
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_EXECUTION_BLUEPRINT.md")
    assert os.path.exists(doc_path), "Missing run execution blueprint documentation md"
