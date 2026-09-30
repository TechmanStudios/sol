# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Physical Execution Gate Validator.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_physical_execution_gate_validator import (
    WaveguidePackagePhysicalGatePreflightAuditCase,
    WaveguidePackagePhysicalGatePreflightAuditReport,
    build_waveguide_package_physical_gate_preflight_audit_case,
    validate_waveguide_package_assembly_physical_execution_gate_independently,
    build_waveguide_package_physical_gate_preflight_audit_report,
    validate_waveguide_package_physical_gate_preflight_audit_report,
    summarize_waveguide_package_physical_gate_preflight_audit_report,
    export_waveguide_package_physical_gate_preflight_audit_report,
    hash_waveguide_package_physical_gate_preflight_audit_case,
    hash_waveguide_package_physical_gate_preflight_audit_report
)


@pytest.fixture
def clean_gate() -> dict:
    gate_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE.json")
    assert os.path.exists(gate_path), "Missing physical execution gate JSON"
    with open(gate_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def clean_audit_report() -> dict:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT_AUDIT_REPORT.json")
    assert os.path.exists(report_path), "Missing transcript audit report JSON"
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_preflight_case_build_and_validation(clean_gate, clean_audit_report):
    # 1. Physical gate preflight audit case builds.
    case = build_waveguide_package_physical_gate_preflight_audit_case(clean_gate, clean_audit_report)
    assert isinstance(case, WaveguidePackagePhysicalGatePreflightAuditCase)

    # 2. Physical gate preflight audit case validates.
    assert case.physical_gate_preflight_status == "physical_gate_preflight_verified"

    # 3. Physical gate preflight case digest is deterministic.
    digest1 = hash_waveguide_package_physical_gate_preflight_audit_case(case)
    digest2 = hash_waveguide_package_physical_gate_preflight_audit_case(case)
    assert digest1 == digest2
    assert case.physical_gate_preflight_case_digest == digest1

    # 4. physical_gate_preflight_case_digest is excluded from its own digest input.
    case_dict = asdict(case)
    case_dict["physical_gate_preflight_case_digest"] = "DUMMY"
    digest_with_dummy = hash_waveguide_package_physical_gate_preflight_audit_case(case_dict)
    assert digest_with_dummy == digest1


def test_preflight_audit_failures(clean_gate, clean_audit_report):
    # 5. Physical execution gate digest mismatch blocks audit.
    bad_gate = dict(clean_gate)
    bad_gate["package_assembly_physical_execution_gate_digest"] = "wrong_digest"
    case = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate, clean_audit_report)
    assert case.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 6. Transcript audit report validation failure blocks audit.
    # 7. Transcript audit report digest mismatch blocks audit.
    bad_report = dict(clean_audit_report)
    bad_report["transcript_audit_report_digest"] = "wrong_digest"
    case2 = build_waveguide_package_physical_gate_preflight_audit_case(clean_gate, bad_report)
    assert case2.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 8. Physical execution gate status not ready blocks audit.
    bad_gate2 = dict(clean_gate)
    bad_gate2["physical_execution_gate_status"] = "package_physical_execution_gate_invalid"
    from sol_waveguide_package_assembly_physical_execution_gate import hash_waveguide_package_assembly_physical_execution_gate
    bad_gate2["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate2)
    case3 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate2, clean_audit_report)
    assert case3.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 9. Physical execution gate decision mismatch blocks audit.
    bad_gate3 = dict(clean_gate)
    bad_gate3["physical_execution_gate_decision"] = "invalid_decision"
    bad_gate3["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate3)
    case4 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate3, clean_audit_report)
    assert case4.physical_gate_preflight_status == "physical_gate_preflight_blocked"


def test_gate_preflight_matrix_checks(clean_gate, clean_audit_report):
    # 10. Future physical execution request allowed false blocks/warns according to chosen semantics.
    bad_gate = dict(clean_gate)
    bad_gate["future_physical_execution_request_allowed"] = False
    from sol_waveguide_package_assembly_physical_execution_gate import hash_waveguide_package_assembly_physical_execution_gate
    bad_gate["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate)
    case = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate, clean_audit_report)
    assert case.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 11. Physical execution permitted by gate true blocks audit.
    bad_gate2 = dict(clean_gate)
    bad_gate2["physical_execution_permitted_by_gate"] = True
    bad_gate2["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate2)
    case2 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate2, clean_audit_report)
    assert case2.physical_gate_preflight_status == "physical_gate_preflight_blocked"


def test_missing_requirements_block_audit(clean_gate, clean_audit_report):
    from sol_waveguide_package_assembly_physical_execution_gate import hash_waveguide_package_assembly_physical_execution_gate
    
    # 12. Missing explicit operator approval requirement blocks audit.
    bad_gate = dict(clean_gate)
    bad_gate["requires_explicit_operator_approval"] = False
    bad_gate["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate)
    case = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate, clean_audit_report)
    assert case.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 13. Missing separate physical runner requirement blocks audit.
    bad_gate2 = dict(clean_gate)
    bad_gate2["requires_separate_physical_runner"] = False
    bad_gate2["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate2)
    case2 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate2, clean_audit_report)
    assert case2.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 14. Missing gate preflight audit requirement blocks audit.
    bad_gate3 = dict(clean_gate)
    bad_gate3["requires_gate_preflight_audit"] = False
    bad_gate3["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate3)
    case3 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate3, clean_audit_report)
    assert case3.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 15. Missing local filesystem scope confirmation requirement blocks audit.
    bad_gate4 = dict(clean_gate)
    bad_gate4["requires_local_filesystem_scope_confirmation"] = False
    bad_gate4["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate4)
    case4 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate4, clean_audit_report)
    assert case4.physical_gate_preflight_status == "physical_gate_preflight_blocked"


def test_performed_mutations_and_blocked_attempts_block_audit(clean_gate, clean_audit_report):
    from sol_waveguide_package_assembly_physical_execution_gate import hash_waveguide_package_assembly_physical_execution_gate

    # 16. Any performed mutation flag true blocks audit.
    bad_gate = dict(clean_gate)
    bad_gate["physical_execution_performed"] = True
    bad_gate["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate)
    case = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate, clean_audit_report)
    assert case.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 17. Nonzero blocked operation count blocks audit.
    bad_gate2 = dict(clean_gate)
    bad_gate2["blocked_operation_attempt_counts"] = {"archive_creation": 1}
    bad_gate2["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate2)
    case2 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate2, clean_audit_report)
    assert case2.physical_gate_preflight_status == "physical_gate_preflight_blocked"


def test_missing_structural_blocks_block_audit(clean_gate, clean_audit_report):
    from sol_waveguide_package_assembly_physical_execution_gate import hash_waveguide_package_assembly_physical_execution_gate

    # 18. Missing constraints/allowances/prohibitions blocks audit.
    bad_gate = dict(clean_gate)
    bad_gate["gate_constraints"] = []
    bad_gate["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate)
    case = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate, clean_audit_report)
    assert case.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 19. Missing guard requirements blocks audit.
    bad_gate2 = dict(clean_gate)
    bad_gate2["gate_guard_requirements"] = []
    bad_gate2["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate2)
    case2 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate2, clean_audit_report)
    assert case2.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 20. Missing no-op boundary blocks audit.
    bad_gate3 = dict(clean_gate)
    bad_gate3["gate_noop_boundary"] = {}
    bad_gate3["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate3)
    case3 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate3, clean_audit_report)
    assert case3.physical_gate_preflight_status == "physical_gate_preflight_blocked"

    # 21. Missing rollback/no-op policy blocks audit.
    bad_gate4 = dict(clean_gate)
    bad_gate4["gate_rollback_noop_policy"] = {}
    bad_gate4["package_assembly_physical_execution_gate_digest"] = hash_waveguide_package_assembly_physical_execution_gate(bad_gate4)
    case4 = build_waveguide_package_physical_gate_preflight_audit_case(bad_gate4, clean_audit_report)
    assert case4.physical_gate_preflight_status == "physical_gate_preflight_blocked"


def test_top_level_preflight_report(clean_gate, clean_audit_report):
    # 22. Top-level physical gate preflight audit report builds.
    report = build_waveguide_package_physical_gate_preflight_audit_report(clean_gate, clean_audit_report)
    assert isinstance(report, WaveguidePackagePhysicalGatePreflightAuditReport)

    # 23. Top-level physical gate preflight audit report validates.
    ok, reasons = validate_waveguide_package_physical_gate_preflight_audit_report(report)
    assert ok is True
    assert "PACKAGE_PHYSICAL_EXECUTION_GATE_AUDIT_VERIFIED" in reasons

    # 24. Physical gate preflight report digest is deterministic.
    digest1 = hash_waveguide_package_physical_gate_preflight_audit_report(report)
    digest2 = hash_waveguide_package_physical_gate_preflight_audit_report(report)
    assert digest1 == digest2
    assert report.physical_gate_preflight_report_digest == digest1

    # 25. physical_gate_preflight_report_digest is excluded from its own digest input.
    rep_dict = asdict(report)
    rep_dict["physical_gate_preflight_report_digest"] = "DUMMY"
    digest_with_dummy = hash_waveguide_package_physical_gate_preflight_audit_report(rep_dict)
    assert digest_with_dummy == digest1


def test_gate_audit_artifacts_exist():
    # 26. Physical execution gate audit JSON artifact exists.
    json_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE_AUDIT_REPORT.json")
    assert os.path.exists(json_path)

    # 27. Physical execution gate validator documentation exists.
    md_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE_VALIDATOR.md")
    assert os.path.exists(md_path)
