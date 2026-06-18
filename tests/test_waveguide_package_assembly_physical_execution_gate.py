# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Physical Execution Gate.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_physical_execution_gate import (
    WaveguidePackageAssemblyPhysicalExecutionGate,
    build_waveguide_package_assembly_physical_execution_gate,
    validate_waveguide_package_assembly_physical_execution_gate,
    summarize_waveguide_package_assembly_physical_execution_gate,
    export_waveguide_package_assembly_physical_execution_gate,
    hash_waveguide_package_assembly_physical_execution_gate
)


@pytest.fixture
def clean_audit_report() -> dict:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT_AUDIT_REPORT.json")
    assert os.path.exists(report_path), "Missing transcript audit report JSON"
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_gate_build_and_validation(clean_audit_report):
    # 1. Physical execution gate builds from clean transcript audit report.
    gate = build_waveguide_package_assembly_physical_execution_gate(clean_audit_report)
    assert isinstance(gate, WaveguidePackageAssemblyPhysicalExecutionGate)

    # 2. Physical execution gate validates.
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate)
    assert ok is True
    assert "PACKAGE_PHYSICAL_EXECUTION_GATE_READY" in reasons

    # 3. Physical execution gate digest is deterministic.
    digest1 = hash_waveguide_package_assembly_physical_execution_gate(gate)
    digest2 = hash_waveguide_package_assembly_physical_execution_gate(gate)
    assert digest1 == digest2
    assert gate.package_assembly_physical_execution_gate_digest == digest1

    # 4. package_assembly_physical_execution_gate_digest is excluded from its own digest input.
    gate_dict = asdict(gate)
    gate_dict["package_assembly_physical_execution_gate_digest"] = "DUMMY"
    digest_with_dummy = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert digest_with_dummy == digest1


def test_upstream_failures_block_gate(clean_audit_report):
    # 5. Transcript audit validation failure blocks gate.
    bad_report = dict(clean_audit_report)
    bad_report["transcript_audit_report_digest"] = "wrong_digest"
    gate = build_waveguide_package_assembly_physical_execution_gate(bad_report)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate)
    assert ok is False
    assert "PACKAGE_PHYSICAL_EXECUTION_GATE_INVALID" in reasons

    # 6. Transcript audit status not verified blocks gate.
    bad_report2 = dict(clean_audit_report)
    bad_report2["transcript_audit_report_status"] = "package_runner_noop_transcript_audit_invalid"
    # recalculate its digest to make it valid structurally, but status is not ready
    from sol_waveguide_package_runner_noop_dry_run_transcript_validator import hash_waveguide_package_runner_transcript_audit_report
    bad_report2["transcript_audit_report_digest"] = hash_waveguide_package_runner_transcript_audit_report(bad_report2)
    gate2 = build_waveguide_package_assembly_physical_execution_gate(bad_report2)
    ok2, reasons2 = validate_waveguide_package_assembly_physical_execution_gate(gate2)
    assert ok2 is False

    # 7. Zero verified transcript audit cases blocks gate.
    bad_report3 = dict(clean_audit_report)
    bad_report3["verified_transcript_audit_count"] = 0
    bad_report3["transcript_audit_report_digest"] = hash_waveguide_package_runner_transcript_audit_report(bad_report3)
    gate3 = build_waveguide_package_assembly_physical_execution_gate(bad_report3)
    ok3, reasons3 = validate_waveguide_package_assembly_physical_execution_gate(gate3)
    assert ok3 is False


def test_transcript_checks_must_be_verified_for_gate(clean_audit_report):
    # 8. Event sequence not verified blocks gate.
    bad_report = dict(clean_audit_report)
    bad_report["event_sequence_verified"] = False
    from sol_waveguide_package_runner_noop_dry_run_transcript_validator import hash_waveguide_package_runner_transcript_audit_report
    bad_report["transcript_audit_report_digest"] = hash_waveguide_package_runner_transcript_audit_report(bad_report)
    gate = build_waveguide_package_assembly_physical_execution_gate(bad_report)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate)
    assert ok is False

    # 9. Event counts not verified blocks gate.
    bad_report2 = dict(clean_audit_report)
    bad_report2["event_counts_verified"] = False
    bad_report2["transcript_audit_report_digest"] = hash_waveguide_package_runner_transcript_audit_report(bad_report2)
    gate2 = build_waveguide_package_assembly_physical_execution_gate(bad_report2)
    ok2, reasons2 = validate_waveguide_package_assembly_physical_execution_gate(gate2)
    assert ok2 is False

    # 10. Skipped operation matrix not verified blocks gate.
    bad_report3 = dict(clean_audit_report)
    bad_report3["skipped_operation_matrix_verified"] = False
    bad_report3["transcript_audit_report_digest"] = hash_waveguide_package_runner_transcript_audit_report(bad_report3)
    gate3 = build_waveguide_package_assembly_physical_execution_gate(bad_report3)
    ok3, reasons3 = validate_waveguide_package_assembly_physical_execution_gate(gate3)
    assert ok3 is False


def test_gate_allowance_prohibition_safety_violations(clean_audit_report):
    # 11. Future physical execution request allowed false blocks or warns (blocks in our validation).
    gate = build_waveguide_package_assembly_physical_execution_gate(clean_audit_report)
    gate_dict = asdict(gate)
    gate_dict["future_physical_execution_request_allowed"] = False
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 12. Physical execution permitted by gate true blocks gate.
    gate_dict = asdict(gate)
    gate_dict["physical_execution_permitted_by_gate"] = True
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False


def test_gate_missing_requirements_blocks_gate(clean_audit_report):
    gate = build_waveguide_package_assembly_physical_execution_gate(clean_audit_report)
    
    # 13. Missing explicit operator approval requirement blocks gate.
    gate_dict = asdict(gate)
    gate_dict["requires_explicit_operator_approval"] = False
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 14. Missing separate physical runner requirement blocks gate.
    gate_dict = asdict(gate)
    gate_dict["requires_separate_physical_runner"] = False
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 15. Missing gate preflight audit requirement blocks gate.
    gate_dict = asdict(gate)
    gate_dict["requires_gate_preflight_audit"] = False
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 16. Missing local filesystem scope confirmation requirement blocks gate.
    gate_dict = asdict(gate)
    gate_dict["requires_local_filesystem_scope_confirmation"] = False
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False


def test_gate_mutation_flags_and_blocked_attempts(clean_audit_report):
    gate = build_waveguide_package_assembly_physical_execution_gate(clean_audit_report)

    # 17. Any performed mutation flag true blocks gate.
    gate_dict = asdict(gate)
    gate_dict["physical_execution_performed"] = True
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 18. Nonzero blocked operation count blocks gate.
    gate_dict = asdict(gate)
    gate_dict["blocked_operation_attempt_counts"] = {"archive_creation": 1}
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False


def test_gate_missing_structural_blocks(clean_audit_report):
    gate = build_waveguide_package_assembly_physical_execution_gate(clean_audit_report)

    # 19. Missing constraints/allowances/prohibitions blocks gate.
    gate_dict = asdict(gate)
    gate_dict["gate_constraints"] = []
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 20. Missing guard requirements blocks gate.
    gate_dict = asdict(gate)
    gate_dict["gate_guard_requirements"] = []
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 21. Missing no-op boundary blocks gate.
    gate_dict = asdict(gate)
    gate_dict["gate_noop_boundary"] = {}
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False

    # 22. Missing rollback/no-op policy blocks gate.
    gate_dict = asdict(gate)
    gate_dict["gate_rollback_noop_policy"] = {}
    gate_dict["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(gate_dict)
    ok, reasons = validate_waveguide_package_assembly_physical_execution_gate(gate_dict)
    assert ok is False


def test_gate_artifacts_exist():
    # 23. Physical execution gate JSON artifact exists.
    json_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE.json")
    assert os.path.exists(json_path)

    # 24. Physical execution gate documentation exists.
    md_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE.md")
    assert os.path.exists(md_path)
