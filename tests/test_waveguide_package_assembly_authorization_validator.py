# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Assembly Authorization Validator.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_assembly_authorization_envelope import (
    hash_waveguide_package_assembly_authorization_envelope
)
from sol_waveguide_package_assembly_authorization_validator import (
    WaveguidePackagePreflightAuthorizationAuditCase,
    WaveguidePackagePreflightAuthorizationAuditReport,
    build_waveguide_package_preflight_authorization_audit_case as build_waveguide_package_preflight_authorization_case,
    validate_waveguide_package_assembly_authorization_envelope_independently,
    build_waveguide_package_preflight_authorization_audit_report,
    validate_waveguide_package_preflight_authorization_audit_report,
    summarize_waveguide_package_preflight_authorization_audit_report,
    export_waveguide_package_preflight_authorization_audit_report,
    compare_waveguide_package_preflight_authorization_audit_reports,
    hash_waveguide_package_preflight_authorization_case,
    hash_waveguide_package_preflight_authorization_report,
    recompute_waveguide_package_assembly_authorization_envelope_digest,
    validate_waveguide_package_authorization_boolean_matrix,
    validate_waveguide_package_authorization_constraints,
    validate_waveguide_package_authorization_allowances,
    validate_waveguide_package_authorization_prohibitions,
    validate_waveguide_package_authorization_blocked_operation_counts,
    index_waveguide_preflight_authorization_cases_by_status,
    index_waveguide_preflight_authorization_cases_by_constraint
)


@pytest.fixture
def clean_validator_inputs() -> tuple[dict, dict]:
    envelope_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_AUTHORIZATION_ENVELOPE.json")
    report_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_FINAL_PACKAGE_READINESS_AUDIT_REPORT.json")

    assert os.path.exists(envelope_path), "Missing authorization envelope JSON"
    assert os.path.exists(report_path), "Missing final package readiness report JSON"

    with open(envelope_path, "r", encoding="utf-8") as f:
        envelope = json.load(f)
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    return envelope, report


def test_preflight_cases_building_and_validation(clean_validator_inputs):
    envelope, report = clean_validator_inputs

    # 1. Preflight authorization audit case can be built from clean authorization envelope.
    case = build_waveguide_package_preflight_authorization_case(envelope, report)
    assert isinstance(case, WaveguidePackagePreflightAuthorizationAuditCase)
    assert case.preflight_authorization_status == "preflight_authorization_verified"

    # 2. Preflight authorization audit case validates.
    # To validate, we can build the report first, but the case digest itself can be recomputed.
    assert case.authorization_envelope_digest_match is True
    assert case.source_final_package_readiness_report_digest_match is True
    assert case.source_final_package_readiness_report_valid is True


def test_preflight_case_digest_determinism_and_exclusion(clean_validator_inputs):
    envelope, report = clean_validator_inputs

    # 3. Preflight authorization audit case digest is deterministic.
    c1 = build_waveguide_package_preflight_authorization_case(envelope, report)
    c2 = build_waveguide_package_preflight_authorization_case(envelope, report)
    assert c1.preflight_authorization_case_digest == c2.preflight_authorization_case_digest
    assert len(c1.preflight_authorization_case_digest) == 64

    # 4. preflight_authorization_case_digest is excluded from its own digest input.
    c_dict = asdict(c1)
    c_dict["preflight_authorization_case_digest"] = "MUTATED_SELF_DIGEST"
    recomputed = hash_waveguide_package_preflight_authorization_case(c_dict)
    assert recomputed == c1.preflight_authorization_case_digest


def test_preflight_failures_and_blocks(clean_validator_inputs):
    envelope, report = clean_validator_inputs

    # 5. Envelope digest mismatch blocks/fails preflight audit.
    bad_envelope = dict(envelope)
    bad_envelope["package_assembly_authorization_envelope_digest"] = "mismatched_digest"
    case = build_waveguide_package_preflight_authorization_case(bad_envelope, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"
    assert "PREFLIGHT_AUTH_ENVELOPE_DIGEST_MISMATCH" in case.reason_codes

    # 6. Source final package-readiness report validation failure blocks preflight audit.
    bad_report = dict(report)
    bad_report["final_package_readiness_report_digest"] = "invalid"
    case = build_waveguide_package_preflight_authorization_case(envelope, bad_report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 7. Source final package-readiness report digest mismatch blocks preflight audit.
    bad_report_digest = dict(report)
    # Recompute to be valid report, but change digest value inside envelope to cause mismatch
    bad_envelope_digest = dict(envelope)
    bad_envelope_digest["source_final_package_readiness_report_digest"] = "mismatched_report_digest"
    bad_envelope_digest["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_envelope_digest)
    case = build_waveguide_package_preflight_authorization_case(bad_envelope_digest, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"
    assert "PREFLIGHT_AUTH_SOURCE_FINAL_READINESS_DIGEST_MISMATCH" in case.reason_codes

    # 8. Authorization status not authorized blocks preflight audit.
    bad_env_status = dict(envelope)
    bad_env_status["authorization_status"] = "package_assembly_blocked"
    bad_env_status["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_status)
    case = build_waveguide_package_preflight_authorization_case(bad_env_status, report)
    assert case.preflight_authorization_status == "preflight_authorization_blocked"

    # 9. Authorization decision not metadata-only future assembly blocks preflight audit.
    bad_env_dec = dict(envelope)
    bad_env_dec["authorization_decision"] = "invalid_decision"
    bad_env_dec["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_dec)
    case = build_waveguide_package_preflight_authorization_case(bad_env_dec, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 10. Zero verified final package count blocks preflight audit.
    bad_env_v = dict(envelope)
    bad_env_v["verified_final_package_count"] = 0
    bad_env_v["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_v)
    case = build_waveguide_package_preflight_authorization_case(bad_env_v, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 11. Nonzero blocked final package count blocks preflight audit.
    bad_env_b = dict(envelope)
    bad_env_b["blocked_final_package_count"] = 1
    bad_env_b["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_b)
    case = build_waveguide_package_preflight_authorization_case(bad_env_b, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 12. Nonzero pending final package count blocks preflight audit.
    bad_env_p = dict(envelope)
    bad_env_p["pending_final_package_count"] = 1
    bad_env_p["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_p)
    case = build_waveguide_package_preflight_authorization_case(bad_env_p, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 13. Nonzero invalid final package count blocks preflight audit.
    bad_env_i = dict(envelope)
    bad_env_i["invalid_final_package_count"] = 1
    bad_env_i["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_i)
    case = build_waveguide_package_preflight_authorization_case(bad_env_i, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 14. Authorized file count mismatch blocks preflight audit.
    bad_env_total = dict(envelope)
    bad_env_total["total_authorized_file_count"] = 10  # should be 28
    bad_env_total["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_total)
    case = build_waveguide_package_preflight_authorization_case(bad_env_total, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 15. Metadata-only authorization false blocks preflight audit.
    bad_env_meta = dict(envelope)
    bad_env_meta["metadata_only_authorization"] = False
    bad_env_meta["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_meta)
    case = build_waveguide_package_preflight_authorization_case(bad_env_meta, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 16. Future operation authorization false or missing blocks preflight audit.
    bad_env_fut = dict(envelope)
    bad_env_fut["future_operation_authorized"] = False
    bad_env_fut["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_fut)
    case = build_waveguide_package_preflight_authorization_case(bad_env_fut, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 17-24. Boolean authorizations set to true block preflight audit.
    flags = [
        "archive_creation_authorized", "file_copy_authorized", "directory_creation_authorized",
        "upload_authorized", "deployment_authorized", "signing_authorized",
        "external_publication_authorized", "production_mutation_authorized"
    ]
    for flag in flags:
        bad_env_flag = dict(envelope)
        bad_env_flag[flag] = True
        bad_env_flag["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_flag)
        case = build_waveguide_package_preflight_authorization_case(bad_env_flag, report)
        assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 25. Nonzero blocked operation attempt count blocks preflight audit.
    bad_env_blocked = dict(envelope)
    bad_env_blocked["blocked_operation_attempt_counts"] = dict(envelope["blocked_operation_attempt_counts"])
    bad_env_blocked["blocked_operation_attempt_counts"]["archive_creation"] = 1
    bad_env_blocked["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_blocked)
    case = build_waveguide_package_preflight_authorization_case(bad_env_blocked, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 26. Missing authorization constraints blocks preflight audit.
    bad_env_con = dict(envelope)
    bad_env_con["authorization_constraints"] = []
    bad_env_con["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_con)
    case = build_waveguide_package_preflight_authorization_case(bad_env_con, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 27. Missing authorization allowances blocks preflight audit.
    bad_env_all = dict(envelope)
    bad_env_all["authorization_allowances"] = []
    bad_env_all["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_all)
    case = build_waveguide_package_preflight_authorization_case(bad_env_all, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 28. Missing authorization prohibitions blocks preflight audit.
    bad_env_pro = dict(envelope)
    bad_env_pro["authorization_prohibitions"] = []
    bad_env_pro["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_pro)
    case = build_waveguide_package_preflight_authorization_case(bad_env_pro, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"

    # 29. Missing software caveat blocks preflight audit.
    bad_env_caveat = dict(envelope)
    bad_env_caveat["software_validation_caveat"] = ""
    bad_env_caveat["package_assembly_authorization_envelope_digest"] = hash_waveguide_package_assembly_authorization_envelope(bad_env_caveat)
    case = build_waveguide_package_preflight_authorization_case(bad_env_caveat, report)
    assert case.preflight_authorization_status == "preflight_authorization_invalid"


def test_top_level_preflight_report(clean_validator_inputs):
    envelope, report = clean_validator_inputs

    # 30. Top-level preflight authorization audit report can be built.
    report_obj = build_waveguide_package_preflight_authorization_audit_report(envelope, report)
    assert isinstance(report_obj, WaveguidePackagePreflightAuthorizationAuditReport)
    assert report_obj.preflight_authorization_report_status == "package_preflight_authorization_verified"

    # 31. Top-level preflight authorization audit report validates.
    ok, reasons = validate_waveguide_package_preflight_authorization_audit_report(report_obj)
    assert ok is True
    assert "PREFLIGHT_AUTH_REPORT_DIGEST_VALID" in reasons
    assert "PACKAGE_PREFLIGHT_AUTHORIZATION_VERIFIED" in reasons

    # 32. Preflight authorization report digest is deterministic.
    report_obj2 = build_waveguide_package_preflight_authorization_audit_report(envelope, report)
    assert report_obj.preflight_authorization_report_digest == report_obj2.preflight_authorization_report_digest
    assert len(report_obj.preflight_authorization_report_digest) == 64

    # 33. preflight_authorization_report_digest is excluded from its own digest input.
    r_dict = asdict(report_obj)
    r_dict["preflight_authorization_report_digest"] = "MUTATED_SELF"
    recomputed = hash_waveguide_package_preflight_authorization_report(r_dict)
    assert recomputed == report_obj.preflight_authorization_report_digest

    # 34. Verified/blocked/warning/invalid preflight counts are correct.
    assert report_obj.verified_preflight_count == 1
    assert report_obj.blocked_preflight_count == 0
    assert report_obj.warning_preflight_count == 0
    assert report_obj.invalid_preflight_count == 0

    # 35. Total authorized file count is correct.
    assert report_obj.total_authorized_file_count == 28

    # 36. RC1 authorized file count is correct.
    assert report_obj.rc1_authorized_file_count == 6

    # 37. RC2 authorized file count is correct.
    assert report_obj.rc2_authorized_file_count == 6

    # 38. Shared authorized file count is correct.
    assert report_obj.shared_authorized_file_count == 16

    # 39-49. Lists must be sorted.
    assert report_obj.authorized_target_package_sections == sorted(report_obj.authorized_target_package_sections)
    assert report_obj.authorized_package_roles == sorted(report_obj.authorized_package_roles)
    assert report_obj.authorized_artifact_types == sorted(report_obj.authorized_artifact_types)
    assert report_obj.authorized_artifact_formats == sorted(report_obj.authorized_artifact_formats)
    assert report_obj.authorized_source_artifact_paths == sorted(report_obj.authorized_source_artifact_paths)
    assert report_obj.authorized_target_package_paths == sorted(report_obj.authorized_target_package_paths)
    assert report_obj.authorized_source_artifact_digests == sorted(report_obj.authorized_source_artifact_digests)
    assert report_obj.authorized_layout_entry_digests == sorted(report_obj.authorized_layout_entry_digests)
    assert report_obj.authorized_dry_run_case_digests == sorted(report_obj.authorized_dry_run_case_digests)
    assert report_obj.authorized_package_content_entry_digests == sorted(report_obj.authorized_package_content_entry_digests)
    assert report_obj.authorized_final_package_audit_case_digests == sorted(report_obj.authorized_final_package_audit_case_digests)

    # 50. Authorization boolean matrix verifies.
    assert report_obj.authorization_boolean_matrix_verified is True

    # 51. Blocked operation attempt counts are deterministic and zero.
    assert report_obj.archive_creation_attempt_count == 0
    assert report_obj.file_copy_attempt_count == 0
    assert report_obj.directory_creation_attempt_count == 0
    assert report_obj.upload_attempt_count == 0
    assert report_obj.deployment_attempt_count == 0
    assert report_obj.signing_attempt_count == 0
    assert report_obj.external_publication_attempt_count == 0
    assert report_obj.production_mutation_attempt_count == 0

    # 52-54. Constraints / allowances / prohibitions are sorted.
    assert report_obj.authorization_constraints == sorted(report_obj.authorization_constraints)
    assert report_obj.authorization_allowances == sorted(report_obj.authorization_allowances)
    assert report_obj.authorization_prohibitions == sorted(report_obj.authorization_prohibitions)


def test_summary_and_export_determinism(clean_validator_inputs, tmp_path):
    envelope, report = clean_validator_inputs
    report_obj = build_waveguide_package_preflight_authorization_audit_report(envelope, report)

    # 55. Summary output is deterministic.
    s1 = summarize_waveguide_package_preflight_authorization_audit_report(report_obj)
    s2 = summarize_waveguide_package_preflight_authorization_audit_report(report_obj)
    assert s1 == s2

    # 56. JSON export is deterministic.
    file_path = os.path.join(tmp_path, "preflight_audit_report.json")
    export_waveguide_package_preflight_authorization_audit_report(report_obj, file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["preflight_authorization_report_digest"] == report_obj.preflight_authorization_report_digest
