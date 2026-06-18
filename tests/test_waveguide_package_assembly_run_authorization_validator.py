# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Run Authorization Validator.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_run_authorization_validator import (
    WaveguidePackageRunPreflightAuditCase,
    WaveguidePackageRunPreflightAuditReport,
    build_waveguide_package_run_preflight_case,
    validate_waveguide_package_assembly_run_authorization_capsule_independently,
    build_waveguide_package_run_preflight_audit_report,
    validate_waveguide_package_run_preflight_audit_report,
    summarize_waveguide_package_run_preflight_audit_report,
    export_waveguide_package_run_preflight_audit_report,
    compare_waveguide_package_run_preflight_audit_reports,
    hash_waveguide_package_run_preflight_case,
    hash_waveguide_package_run_preflight_report
)

@pytest.fixture
def clean_capsule() -> dict:
    capsule_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_AUTHORIZATION_CAPSULE.json")
    assert os.path.exists(capsule_path), "Missing run authorization capsule JSON"
    with open(capsule_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def clean_readiness_report() -> dict:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_EXECUTION_READINESS_AUDIT_REPORT.json")
    assert os.path.exists(report_path), "Missing execution readiness report JSON"
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_run_preflight_case_build_and_validation(clean_capsule, clean_readiness_report):
    # 1. Run preflight audit case can be built.
    case = build_waveguide_package_run_preflight_case(clean_capsule, clean_readiness_report)
    assert isinstance(case, WaveguidePackageRunPreflightAuditCase)
    
    # 2. Run preflight audit case validates.
    assert case.run_preflight_status == "package_run_preflight_verified"
    assert "PACKAGE_RUN_AUTHORIZED" in case.reason_codes

def test_run_preflight_case_digest_determinism_and_exclusion(clean_capsule, clean_readiness_report):
    # 3. Run preflight case digest is deterministic.
    c1 = build_waveguide_package_run_preflight_case(clean_capsule, clean_readiness_report)
    c2 = build_waveguide_package_run_preflight_case(clean_capsule, clean_readiness_report)
    assert c1.run_preflight_case_digest == c2.run_preflight_case_digest
    assert len(c1.run_preflight_case_digest) == 64

    # 4. run_preflight_case_digest is excluded from its own digest input.
    c_dict = asdict(c1)
    c_dict["run_preflight_case_digest"] = "MUTATED_SELF_CASE_DIGEST"
    recomputed = hash_waveguide_package_run_preflight_case(c_dict)
    assert recomputed == c1.run_preflight_case_digest

def test_validator_failures(clean_capsule, clean_readiness_report):
    # Helper to validate case and verify failure
    def assert_case_invalid_with_mutation(mutation_fn):
        mutated_capsule = dict(clean_capsule)
        mutation_fn(mutated_capsule)
        case = build_waveguide_package_run_preflight_case(mutated_capsule, clean_readiness_report)
        assert case.run_preflight_status == "package_run_preflight_invalid"

    # 5. Capsule digest mismatch blocks audit.
    def mutate_capsule_digest(c):
        c["package_assembly_run_authorization_capsule_digest"] = "bad_digest"
    assert_case_invalid_with_mutation(mutate_capsule_digest)

    # 6. Execution-readiness report validation failure blocks audit.
    mutated_report = dict(clean_readiness_report)
    mutated_report["execution_readiness_report_status"] = "package_execution_readiness_invalid"
    case = build_waveguide_package_run_preflight_case(clean_capsule, mutated_report)
    assert case.run_preflight_status == "package_run_preflight_invalid"

    # 7. Execution-readiness report digest mismatch blocks audit.
    def mutate_readiness_digest_ref(c):
        c["source_execution_readiness_report_digest"] = "bad_readiness_digest"
    assert_case_invalid_with_mutation(mutate_readiness_digest_ref)

    # 8. Run authorization status not authorized blocks audit.
    def mutate_auth_status(c):
        c["run_authorization_status"] = "package_run_unauthorized"
    assert_case_invalid_with_mutation(mutate_auth_status)

    # 9. Run authorization decision mismatch blocks audit.
    def mutate_decision(c):
        c["run_authorization_decision"] = "deny_run_request"
    assert_case_invalid_with_mutation(mutate_decision)

    # 10. Specific future run authorization false blocks audit.
    def mutate_specific_future_run(c):
        c["specific_future_run_authorized"] = False
    assert_case_invalid_with_mutation(mutate_specific_future_run)

    # 11. Metadata-only run authorization false blocks audit.
    def mutate_metadata_only(c):
        c["metadata_only_run_authorization"] = False
    assert_case_invalid_with_mutation(mutate_metadata_only)

    # 12. Any physical authorization flag true blocks audit.
    auth_flags = [
        "physical_execution_authorized", "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized"
    ]
    for flag in auth_flags:
        def make_mutate_fn(f):
            return lambda c: c.update({f: True})
        assert_case_invalid_with_mutation(make_mutate_fn(flag))

    # 13. Any performed operation flag true blocks audit.
    performed_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in performed_flags:
        def make_mutate_fn(f):
            return lambda c: c.update({f: True})
        assert_case_invalid_with_mutation(make_mutate_fn(flag))

    # 14. Nonzero blocked operation counter blocks audit.
    def mutate_blocked_counts(c):
        c["blocked_operation_attempt_counts"]["archive_creation"] = 1
    assert_case_invalid_with_mutation(mutate_blocked_counts)

    # 15. Missing constraints/allowances/prohibitions blocks audit.
    def mutate_constraints(c):
        c["run_constraints"] = []
    assert_case_invalid_with_mutation(mutate_constraints)

    def mutate_allowances(c):
        c["run_allowances"] = []
    assert_case_invalid_with_mutation(mutate_allowances)

    def mutate_prohibitions(c):
        c["run_prohibitions"] = []
    assert_case_invalid_with_mutation(mutate_prohibitions)

    # 16. Missing guard requirements blocks audit.
    def mutate_guards(c):
        c["run_guard_requirements"] = []
    assert_case_invalid_with_mutation(mutate_guards)

    # 17. Missing no-op boundary blocks audit.
    def mutate_noop_boundary(c):
        c["run_noop_boundary"] = {}
    assert_case_invalid_with_mutation(mutate_noop_boundary)

    # 18. Missing rollback/no-op policy blocks audit.
    def mutate_policy(c):
        c["run_rollback_noop_policy"] = {}
    assert_case_invalid_with_mutation(mutate_policy)

def test_report_building_and_validation(clean_capsule, clean_readiness_report):
    # 19. Top-level run preflight report builds.
    report = build_waveguide_package_run_preflight_audit_report(clean_capsule, clean_readiness_report)
    assert isinstance(report, WaveguidePackageRunPreflightAuditReport)
    assert report.run_preflight_report_status == "package_run_preflight_verified"

    # 20. Top-level run preflight report validates.
    ok, reasons = validate_waveguide_package_run_preflight_audit_report(report)
    assert ok is True
    assert "PACKAGE_RUN_PREFLIGHT_VERIFIED" in reasons

def test_report_digest_determinism_and_exclusion(clean_capsule, clean_readiness_report):
    # 21. Report digest is deterministic.
    r1 = build_waveguide_package_run_preflight_audit_report(clean_capsule, clean_readiness_report)
    r2 = build_waveguide_package_run_preflight_audit_report(clean_capsule, clean_readiness_report)
    assert r1.run_preflight_report_digest == r2.run_preflight_report_digest

    # 22. run_preflight_report_digest is excluded from its own digest input.
    r_dict = asdict(r1)
    r_dict["run_preflight_report_digest"] = "MUTATED_SELF_REPORT_DIGEST"
    recomputed = hash_waveguide_package_run_preflight_report(r_dict)
    assert recomputed == r1.run_preflight_report_digest

def test_report_correctness_and_export(clean_capsule, clean_readiness_report):
    report = build_waveguide_package_run_preflight_audit_report(clean_capsule, clean_readiness_report)

    # 23. Counts and indexes are deterministic.
    assert report.verified_run_preflight_count == 1
    assert report.total_authorized_file_count == 28
    assert report.planned_execution_step_count == 31
    assert report.rc1_authorized_file_count == 6
    assert report.rc2_authorized_file_count == 6
    assert report.shared_authorized_file_count == 16

    assert report.run_constraints == sorted(report.run_constraints)
    assert report.run_allowances == sorted(report.run_allowances)
    assert report.run_prohibitions == sorted(report.run_prohibitions)
    assert report.run_guard_requirements == sorted(report.run_guard_requirements)

    assert report.authorized_target_package_sections == sorted(report.authorized_target_package_sections)
    assert report.authorized_source_reference_digests == sorted(report.authorized_source_reference_digests)

    # 24. JSON export is deterministic.
    export_path = "docs/test_run_preflight_audit_report.json"
    export_waveguide_package_run_preflight_audit_report(report, export_path)
    full_export_path = os.path.join(REPO_ROOT, export_path)
    assert os.path.exists(full_export_path)
    
    with open(full_export_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["run_preflight_report_digest"] == report.run_preflight_report_digest
    os.remove(full_export_path)

    # 25. Run preflight JSON artifact exists.
    canonical_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_PREFLIGHT_AUDIT_REPORT.json")
    assert os.path.exists(canonical_path), "Missing canonical run preflight report JSON"

    # 26. Run authorization validator documentation exists.
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_AUTHORIZATION_VALIDATOR.md")
    assert os.path.exists(doc_path), "Missing run authorization validator documentation md"
