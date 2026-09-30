# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for SOL Waveguide Package Assembly Authorization Envelope.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_authorization_envelope import (
    WaveguidePackageAssemblyAuthorizationEnvelope,
    build_waveguide_package_assembly_authorization_envelope,
    validate_waveguide_package_assembly_authorization_envelope,
    summarize_waveguide_package_assembly_authorization_envelope,
    export_waveguide_package_assembly_authorization_envelope,
    compare_waveguide_package_assembly_authorization_envelopes,
    hash_waveguide_package_assembly_authorization_envelope,
    index_waveguide_package_authorization_references_by_source
)


@pytest.fixture
def clean_readiness_report() -> dict:
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_FINAL_PACKAGE_READINESS_AUDIT_REPORT.json")
    assert os.path.exists(report_path), "Missing final package readiness report JSON"
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_authorization_envelope_building_and_validation(clean_readiness_report):
    report = clean_readiness_report

    # 1. Authorization envelope can be built from clean final package-readiness report.
    envelope = build_waveguide_package_assembly_authorization_envelope(report)
    assert isinstance(envelope, WaveguidePackageAssemblyAuthorizationEnvelope)
    assert envelope.authorization_status == "package_assembly_authorized"
    assert envelope.authorization_decision == "authorize_metadata_only_future_assembly"

    # 2. Authorization envelope validates.
    ok, reasons = validate_waveguide_package_assembly_authorization_envelope(envelope)
    assert ok is True
    assert "PACKAGE_AUTHORIZATION_ENVELOPE_DIGEST_VALID" in reasons
    assert "PACKAGE_ASSEMBLY_AUTHORIZED" in reasons


def test_authorization_envelope_digest_determinism_and_exclusion(clean_readiness_report):
    report = clean_readiness_report

    # 3. Envelope digest is deterministic.
    env1 = build_waveguide_package_assembly_authorization_envelope(report)
    env2 = build_waveguide_package_assembly_authorization_envelope(report)
    assert env1.package_assembly_authorization_envelope_digest == env2.package_assembly_authorization_envelope_digest
    assert len(env1.package_assembly_authorization_envelope_digest) == 64

    # 4. package_assembly_authorization_envelope_digest is excluded from its own digest input.
    e_dict = asdict(env1)
    e_dict["package_assembly_authorization_envelope_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_package_assembly_authorization_envelope(e_dict)
    assert recomputed == env1.package_assembly_authorization_envelope_digest


def test_authorization_rejections_and_failures(clean_readiness_report):
    report = clean_readiness_report

    # 5. Source final package-readiness report validation failure blocks authorization.
    bad_report = dict(report)
    bad_report["final_package_readiness_report_digest"] = "mismatched"
    envelope = build_waveguide_package_assembly_authorization_envelope(bad_report)
    assert envelope.authorization_status == "package_assembly_blocked"
    assert envelope.future_operation_authorized is False
    assert "PACKAGE_ASSEMBLY_BLOCKED" in envelope.reason_codes

    # 6. Source final package-readiness status not verified blocks authorization.
    bad_status_report = dict(report)
    bad_status_report["final_package_readiness_report_status"] = "final_package_readiness_invalid"
    envelope = build_waveguide_package_assembly_authorization_envelope(bad_status_report)
    assert envelope.authorization_status == "package_assembly_blocked"

    # 7. Missing source final package-readiness report digest blocks authorization.
    missing_digest_report = dict(report)
    missing_digest_report["final_package_readiness_report_digest"] = ""
    envelope = build_waveguide_package_assembly_authorization_envelope(missing_digest_report)
    assert envelope.authorization_status == "package_assembly_blocked"

    # 8. Zero verified final package count blocks authorization.
    zero_count_report = dict(report)
    zero_count_report["verified_final_package_count"] = 0
    envelope = build_waveguide_package_assembly_authorization_envelope(zero_count_report)
    assert envelope.authorization_status == "package_assembly_blocked"

    # 9. Nonzero blocked final package count blocks authorization.
    blocked_count_report = dict(report)
    blocked_count_report["blocked_final_package_count"] = 1
    envelope = build_waveguide_package_assembly_authorization_envelope(blocked_count_report)
    assert envelope.authorization_status == "package_assembly_blocked"

    # 10. Nonzero pending final package count blocks authorization.
    pending_count_report = dict(report)
    pending_count_report["pending_final_package_count"] = 1
    envelope = build_waveguide_package_assembly_authorization_envelope(pending_count_report)
    assert envelope.authorization_status == "package_assembly_blocked"

    # 11. Nonzero invalid final package count blocks authorization.
    invalid_count_report = dict(report)
    invalid_count_report["invalid_final_package_count"] = 1
    envelope = build_waveguide_package_assembly_authorization_envelope(invalid_count_report)
    assert envelope.authorization_status == "package_assembly_blocked"

    # 12-19. Nonzero blocked operations counts block authorization.
    ops = [
        "archive_creation", "file_copy", "directory_creation",
        "upload", "deployment", "external_signing", "external_publication", "production_mutation"
    ]
    for op in ops:
        bad_ops_report = dict(report)
        bad_ops_report["blocked_operation_attempt_counts"] = dict(report["blocked_operation_attempt_counts"])
        # Handle "external_signing" fallback/mapping
        key = op
        if op == "external_signing" and "external_signing" not in bad_ops_report["blocked_operation_attempt_counts"]:
            key = "signing"
        bad_ops_report["blocked_operation_attempt_counts"][key] = 1
        envelope = build_waveguide_package_assembly_authorization_envelope(bad_ops_report)
        assert envelope.authorization_status == "package_assembly_blocked"


def test_authorization_boolean_and_metadata_only_rules(clean_readiness_report):
    report = clean_readiness_report
    envelope = build_waveguide_package_assembly_authorization_envelope(report)

    # 20. Metadata-only authorization must be true.
    assert envelope.metadata_only_authorization is True

    # 21-28. Mutation permissions must be false.
    assert envelope.archive_creation_authorized is False
    assert envelope.file_copy_authorized is False
    assert envelope.directory_creation_authorized is False
    assert envelope.upload_authorized is False
    assert envelope.deployment_authorized is False
    assert envelope.signing_authorized is False
    assert envelope.external_publication_authorized is False
    assert envelope.production_mutation_authorized is False


def test_authorized_counts_and_sorting(clean_readiness_report):
    report = clean_readiness_report
    envelope = build_waveguide_package_assembly_authorization_envelope(report)

    # 29. Total authorized file count matches verified final package count.
    assert envelope.total_authorized_file_count == report["verified_final_package_count"]

    # 30. RC1/RC2/shared authorized counts match source report.
    assert envelope.rc1_authorized_file_count == report["rc1_final_package_count"]
    assert envelope.rc2_authorized_file_count == report["rc2_final_package_count"]
    assert envelope.shared_authorized_file_count == report["shared_final_package_count"]

    # 31-41. Lists must be sorted.
    assert envelope.authorized_target_package_sections == sorted(envelope.authorized_target_package_sections)
    assert envelope.authorized_package_roles == sorted(envelope.authorized_package_roles)
    assert envelope.authorized_artifact_types == sorted(envelope.authorized_artifact_types)
    assert envelope.authorized_artifact_formats == sorted(envelope.authorized_artifact_formats)
    assert envelope.authorized_source_artifact_paths == sorted(envelope.authorized_source_artifact_paths)
    assert envelope.authorized_target_package_paths == sorted(envelope.authorized_target_package_paths)
    assert envelope.authorized_source_artifact_digests == sorted(envelope.authorized_source_artifact_digests)
    assert envelope.authorized_layout_entry_digests == sorted(envelope.authorized_layout_entry_digests)
    assert envelope.authorized_dry_run_case_digests == sorted(envelope.authorized_dry_run_case_digests)
    assert envelope.authorized_package_content_entry_digests == sorted(envelope.authorized_package_content_entry_digests)
    assert envelope.authorized_final_package_audit_case_digests == sorted(envelope.authorized_final_package_audit_case_digests)

    # 42-44. Constraints, allowances, prohibitions are sorted.
    assert envelope.authorization_constraints == sorted(envelope.authorization_constraints)
    assert envelope.authorization_allowances == sorted(envelope.authorization_allowances)
    assert envelope.authorization_prohibitions == sorted(envelope.authorization_prohibitions)


def test_summary_and_export_determinism(clean_readiness_report, tmp_path):
    report = clean_readiness_report
    envelope = build_waveguide_package_assembly_authorization_envelope(report)

    # 45. Summary output is deterministic.
    s1 = summarize_waveguide_package_assembly_authorization_envelope(envelope)
    s2 = summarize_waveguide_package_assembly_authorization_envelope(envelope)
    assert s1 == s2

    # 46. JSON export is deterministic.
    file_path = os.path.join(tmp_path, "authorization_envelope.json")
    export_waveguide_package_assembly_authorization_envelope(envelope, file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["package_assembly_authorization_envelope_digest"] == envelope.package_assembly_authorization_envelope_digest
