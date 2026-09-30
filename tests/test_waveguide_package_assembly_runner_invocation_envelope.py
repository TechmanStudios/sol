# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Runner Invocation Envelope.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_runner_invocation_envelope import (
    WaveguidePackageAssemblyRunnerInvocationEnvelope,
    build_waveguide_package_assembly_runner_invocation_envelope,
    validate_waveguide_package_assembly_runner_invocation_envelope,
    summarize_waveguide_package_assembly_runner_invocation_envelope,
    export_waveguide_package_assembly_runner_invocation_envelope,
    compare_waveguide_package_assembly_runner_invocation_envelopes,
    hash_waveguide_package_assembly_runner_invocation_envelope
)


@pytest.fixture
def clean_readiness_report() -> dict:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_RUNNER_READINESS_AUDIT_REPORT.json")
    assert os.path.exists(report_path), "Missing readiness report JSON"
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_runner_invocation_envelope_build_and_validation(clean_readiness_report):
    # 1. Runner invocation envelope builds.
    envelope = build_waveguide_package_assembly_runner_invocation_envelope(clean_readiness_report)
    assert isinstance(envelope, WaveguidePackageAssemblyRunnerInvocationEnvelope)
    assert envelope.runner_invocation_status == "package_runner_invocation_ready"

    # 2. Runner invocation envelope validates.
    ok, reasons = validate_waveguide_package_assembly_runner_invocation_envelope(envelope)
    assert ok is True
    assert "PACKAGE_RUNNER_INVOCATION_READY" in reasons


def test_envelope_digest_determinism_and_exclusion(clean_readiness_report):
    # 3. Envelope digest is deterministic.
    e1 = build_waveguide_package_assembly_runner_invocation_envelope(clean_readiness_report)
    e2 = build_waveguide_package_assembly_runner_invocation_envelope(clean_readiness_report)
    assert e1.package_assembly_runner_invocation_envelope_digest == e2.package_assembly_runner_invocation_envelope_digest
    assert len(e1.package_assembly_runner_invocation_envelope_digest) == 64

    # 4. package_assembly_runner_invocation_envelope_digest is excluded from its own digest input.
    e_dict = asdict(e1)
    e_dict["package_assembly_runner_invocation_envelope_digest"] = "MUTATED_ENVELOPE_SELF_DIGEST"
    recomputed = hash_waveguide_package_assembly_runner_invocation_envelope(e_dict)
    assert recomputed == e1.package_assembly_runner_invocation_envelope_digest


def test_envelope_validation_failures(clean_readiness_report):
    # Helper to build envelope with modified readiness dict
    def build_envelope_with_mutations(readiness_mod):
        rf = dict(clean_readiness_report)
        rf.update(readiness_mod)
        return build_waveguide_package_assembly_runner_invocation_envelope(rf)

    def assert_envelope_invalid_with_envelope_mutation(field_name, value):
        env = build_waveguide_package_assembly_runner_invocation_envelope(clean_readiness_report)
        e_dict = asdict(env)
        e_dict[field_name] = value
        e_dict["package_assembly_runner_invocation_envelope_digest"] = hash_waveguide_package_assembly_runner_invocation_envelope(e_dict)
        ok, _ = validate_waveguide_package_assembly_runner_invocation_envelope(e_dict)
        assert not ok

    # 5. Runner-readiness validation failure blocks invocation.
    env = build_envelope_with_mutations({"runner_readiness_report_status": "package_runner_readiness_invalid"})
    assert env.runner_invocation_status == "package_runner_invocation_invalid"

    # 6. Runner-readiness status not verified blocks invocation.
    env = build_envelope_with_mutations({"runner_readiness_report_status": "package_runner_readiness_blocked"})
    assert env.runner_invocation_status == "package_runner_invocation_invalid"

    # 7. Zero verified readiness cases blocks invocation.
    env = build_envelope_with_mutations({"verified_runner_readiness_count": 0})
    assert env.runner_invocation_status == "package_runner_invocation_invalid"

    # 8. Nonzero blocked/warning/invalid readiness count blocks invocation.
    env = build_envelope_with_mutations({"blocked_runner_readiness_count": 1})
    assert env.runner_invocation_status == "package_runner_invocation_invalid"

    # 9. No-op dry-run authorization false blocks invocation.
    # Wait, check envelope validation when specific authorization flags are mutated
    assert_envelope_invalid_with_envelope_mutation("noop_dry_run_authorized", False)

    # 10. Metadata-only invocation false blocks invocation.
    assert_envelope_invalid_with_envelope_mutation("metadata_only_runner_invocation", False)

    # 11. Physical execution authorization true blocks invocation.
    assert_envelope_invalid_with_envelope_mutation("physical_execution_authorized", True)

    # 12. Any mutation authorization true blocks invocation.
    mutation_auth_fields = [
        "archive_creation_authorized", "file_copy_authorized",
        "directory_creation_authorized", "upload_authorized", "deployment_authorized",
        "signing_authorized", "external_publication_authorized", "production_mutation_authorized"
    ]
    for field in mutation_auth_fields:
        assert_envelope_invalid_with_envelope_mutation(field, True)

    # 13. Any performed mutation flag true blocks invocation.
    mutation_perf_fields = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for field in mutation_perf_fields:
        assert_envelope_invalid_with_envelope_mutation(field, True)

    # 14. Nonzero blocked operation counter blocks invocation.
    assert_envelope_invalid_with_envelope_mutation("blocked_operation_attempt_counts", {"archive_creation": 1})

    # 15. Missing constraints/allowances/prohibitions blocks invocation.
    assert_envelope_invalid_with_envelope_mutation("runner_invocation_constraints", [])
    assert_envelope_invalid_with_envelope_mutation("runner_invocation_allowances", [])
    assert_envelope_invalid_with_envelope_mutation("runner_invocation_prohibitions", [])

    # 16. Missing guard requirements blocks invocation.
    assert_envelope_invalid_with_envelope_mutation("runner_invocation_guard_requirements", [])

    # 17. Missing no-op boundary blocks invocation.
    assert_envelope_invalid_with_envelope_mutation("runner_invocation_noop_boundary", {})

    # 18. Missing rollback/no-op policy blocks invocation.
    assert_envelope_invalid_with_envelope_mutation("runner_invocation_rollback_noop_policy", {})


def test_envelope_artifacts_exist():
    # 19. JSON artifact exists.
    json_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUNNER_INVOCATION_ENVELOPE.json")
    assert os.path.exists(json_path)

    # 20. Documentation exists.
    md_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUNNER_INVOCATION_ENVELOPE.md")
    assert os.path.exists(md_path)
