# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Run Blueprint Validator / Runner Readiness Auditor.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_run_blueprint_validator import (
    WaveguidePackageRunnerReadinessAuditCase,
    WaveguidePackageRunnerReadinessAuditReport,
    build_waveguide_package_runner_readiness_audit_case,
    validate_waveguide_package_assembly_run_execution_blueprint_independently,
    build_waveguide_package_runner_readiness_audit_report,
    validate_waveguide_package_runner_readiness_audit_report,
    summarize_waveguide_package_runner_readiness_audit_report,
    export_waveguide_package_runner_readiness_audit_report,
    compare_waveguide_package_runner_readiness_audit_reports,
    hash_waveguide_package_runner_readiness_audit_case,
    hash_waveguide_package_runner_readiness_audit_report
)


@pytest.fixture
def clean_preflight_and_blueprint() -> tuple:
    preflight_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_PREFLIGHT_AUDIT_REPORT.json")
    blueprint_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_EXECUTION_BLUEPRINT.json")
    assert os.path.exists(preflight_path), "Missing preflight JSON"
    assert os.path.exists(blueprint_path), "Missing blueprint JSON"
    
    with open(preflight_path, "r", encoding="utf-8") as f:
        preflight = json.load(f)
    with open(blueprint_path, "r", encoding="utf-8") as f:
        blueprint = json.load(f)
    return blueprint, preflight


def test_runner_readiness_case_build_and_validation(clean_preflight_and_blueprint):
    blueprint, preflight = clean_preflight_and_blueprint
    phase = blueprint["blueprint_phases"][0]

    # 1. Runner-readiness audit case can be built.
    case = build_waveguide_package_runner_readiness_audit_case(phase, blueprint, preflight)
    assert isinstance(case, WaveguidePackageRunnerReadinessAuditCase)
    assert case.runner_readiness_status == "runner_readiness_verified"

    # 2. Runner-readiness audit case validates (internal checks inside builder).
    assert case.run_blueprint_digest_match is True
    assert case.run_blueprint_phase_digest_match is True


def test_runner_readiness_case_digest_determinism_and_exclusion(clean_preflight_and_blueprint):
    blueprint, preflight = clean_preflight_and_blueprint
    phase = blueprint["blueprint_phases"][0]

    # 3. Runner-readiness case digest is deterministic.
    c1 = build_waveguide_package_runner_readiness_audit_case(phase, blueprint, preflight)
    c2 = build_waveguide_package_runner_readiness_audit_case(phase, blueprint, preflight)
    assert c1.runner_readiness_case_digest == c2.runner_readiness_case_digest
    assert len(c1.runner_readiness_case_digest) == 64

    # 4. runner_readiness_case_digest is excluded from its own digest input.
    c_dict = asdict(c1)
    c_dict["runner_readiness_case_digest"] = "MUTATED_CASE_SELF_DIGEST"
    recomputed = hash_waveguide_package_runner_readiness_audit_case(c_dict)
    assert recomputed == c1.runner_readiness_case_digest


def test_runner_readiness_case_validation_failures(clean_preflight_and_blueprint):
    blueprint, preflight = clean_preflight_and_blueprint
    phase = blueprint["blueprint_phases"][0]

    # Helper to build case with modified blueprints or preflight dicts
    def build_case_with_mutations(blueprint_mod=None, preflight_mod=None, phase_mod=None):
        bp = dict(blueprint)
        pf = dict(preflight)
        ph = dict(phase)
        if blueprint_mod:
            bp.update(blueprint_mod)
        if preflight_mod:
            pf.update(preflight_mod)
        if phase_mod:
            ph.update(phase_mod)
        return build_waveguide_package_runner_readiness_audit_case(ph, bp, pf)

    # 5. Blueprint digest mismatch blocks readiness.
    c = build_case_with_mutations(blueprint_mod={"package_assembly_run_execution_blueprint_digest": "INVALID_BLUEPRINT_DIGEST"})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 6. Phase digest mismatch blocks readiness.
    c = build_case_with_mutations(phase_mod={"run_blueprint_phase_digest": "INVALID_PHASE_DIGEST"})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 7. Run-preflight report validation failure blocks readiness.
    c = build_case_with_mutations(preflight_mod={"run_preflight_report_status": "package_run_preflight_invalid"})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 8. Run-preflight digest mismatch blocks readiness.
    c = build_case_with_mutations(preflight_mod={"run_preflight_report_digest": "INVALID_PREFLIGHT_DIGEST"})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 9. Blueprint status not ready blocks readiness.
    c = build_case_with_mutations(blueprint_mod={"run_blueprint_status": "package_run_blueprint_invalid"})
    # Wait, building is independent, let's verify if that is validated in report or case
    report = build_waveguide_package_runner_readiness_audit_report(
        dict(blueprint, run_blueprint_status="package_run_blueprint_invalid"), preflight
    )
    assert report.runner_readiness_report_status == "package_runner_readiness_invalid"

    # 10. Phase status not ready blocks readiness.
    mutated_phase = dict(phase, phase_status="run_blueprint_phase_invalid")
    mutated_phases = list(blueprint["blueprint_phases"])
    mutated_phases[0] = mutated_phase
    report = build_waveguide_package_runner_readiness_audit_report(
        dict(blueprint, blueprint_phases=mutated_phases), preflight
    )
    assert report.runner_readiness_report_status == "package_runner_readiness_invalid"

    # 11. Missing guard conditions blocks readiness.
    c = build_case_with_mutations(phase_mod={"required_guard_conditions": ["missing_guard"]})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 12. Missing abort conditions blocks readiness.
    c = build_case_with_mutations(phase_mod={"abort_conditions": []})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 13. Missing safety gates blocks readiness.
    c = build_case_with_mutations(phase_mod={"safety_gates": []})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 14. Missing expected input/output blocks readiness.
    # Check if a step planning phase has invalid input/output paths.
    planning_phase = [p for p in blueprint["blueprint_phases"] if p["phase_type"] == "artifact_instruction_planning"][0]
    c = build_waveguide_package_runner_readiness_audit_case(
        dict(planning_phase, expected_input_reference="unauthorized_path"), blueprint, preflight
    )
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 15. Missing no-op boundary blocks readiness.
    c = build_case_with_mutations(phase_mod={"noop_boundary": {}})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 16. Missing rollback/no-op policy blocks readiness.
    c = build_case_with_mutations(phase_mod={"run_rollback_noop_policy": {}})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 17. Any performed mutation flag true blocks readiness.
    c = build_case_with_mutations(phase_mod={"physical_execution_performed": True})
    assert c.runner_readiness_status == "runner_readiness_blocked"

    # 18. Nonzero blocked operation counter blocks readiness.
    c = build_case_with_mutations(blueprint_mod={"blocked_operation_attempt_counts": {"archive_creation": 1}})
    assert c.runner_readiness_status == "runner_readiness_blocked"


def test_top_level_report_building_and_validation(clean_preflight_and_blueprint):
    blueprint, preflight = clean_preflight_and_blueprint

    # 19. Top-level runner-readiness report builds.
    report = build_waveguide_package_runner_readiness_audit_report(blueprint, preflight)
    assert isinstance(report, WaveguidePackageRunnerReadinessAuditReport)
    assert report.runner_readiness_report_status == "package_runner_readiness_verified"

    # 20. Top-level runner-readiness report validates.
    ok, reasons = validate_waveguide_package_runner_readiness_audit_report(report)
    assert ok is True
    assert "PACKAGE_RUNNER_READINESS_VERIFIED" in reasons


def test_report_digest_determinism_and_exclusion(clean_preflight_and_blueprint):
    blueprint, preflight = clean_preflight_and_blueprint

    # 21. Report digest is deterministic.
    r1 = build_waveguide_package_runner_readiness_audit_report(blueprint, preflight)
    r2 = build_waveguide_package_runner_readiness_audit_report(blueprint, preflight)
    assert r1.runner_readiness_report_digest == r2.runner_readiness_report_digest

    # 22. runner_readiness_report_digest is excluded from its own digest input.
    r_dict = asdict(r1)
    r_dict["runner_readiness_report_digest"] = "MUTATED_REPORT_SELF_DIGEST"
    recomputed = hash_waveguide_package_runner_readiness_audit_report(r_dict)
    assert recomputed == r1.runner_readiness_report_digest


def test_report_phase_sequence_properties(clean_preflight_and_blueprint):
    blueprint, preflight = clean_preflight_and_blueprint
    report = build_waveguide_package_runner_readiness_audit_report(blueprint, preflight)

    # 23. Phase sequence is contiguous.
    # (Checked during validation inside validator.py, returns True for Clean sequence)
    # Let's verify here manually:
    for idx, c in enumerate(report.audited_cases):
        assert c.phase_index == idx

    # 24. Phase count is 34.
    assert report.blueprint_phase_count == 34
    assert len(report.audited_cases) == 34


def test_report_artifacts_exist():
    # 25. Runner readiness JSON artifact exists.
    json_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_READINESS_AUDIT_REPORT.json")
    assert os.path.exists(json_path)

    # 26. Runner readiness documentation exists.
    md_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_BLUEPRINT_VALIDATOR.md")
    assert os.path.exists(md_path)
