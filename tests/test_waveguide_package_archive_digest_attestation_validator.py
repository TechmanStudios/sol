# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Digest Attestation Validator.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_signing_plan import build_waveguide_package_archive_signing_plan
from sol_waveguide_package_archive_signing_gate import build_waveguide_package_archive_signing_gate
from sol_waveguide_package_archive_digest_attestation import (
    build_waveguide_package_archive_digest_attestation,
    hash_waveguide_package_archive_digest_attestation
)
from sol_waveguide_package_archive_digest_attestation_validator import (
    build_waveguide_package_archive_digest_attestation_audit_case,
    build_waveguide_package_archive_digest_attestation_audit_report,
    validate_waveguide_package_archive_digest_attestation_audit_report,
    hash_waveguide_package_archive_digest_attestation_audit_case,
    hash_waveguide_package_archive_digest_attestation_audit_report,
    WaveguidePackageArchiveDigestAttestationAuditCase,
    WaveguidePackageArchiveDigestAttestationAuditReport,
    export_waveguide_package_archive_digest_attestation_audit_report
)


@pytest.fixture
def clean_digest_attestation() -> dict:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        idx_dict = json.load(f)
    plan = build_waveguide_package_archive_signing_plan(idx_dict)
    gate = build_waveguide_package_archive_signing_gate(plan)
    recorded_digest = gate.current_archive_candidate_digest
    att = build_waveguide_package_archive_digest_attestation(gate, archive_override_digest=recorded_digest)
    return asdict(att)


def test_audit_case_lifecycle(clean_digest_attestation):
    stmt = clean_digest_attestation["archive_digest_attestation_statements"][0]
    att_digest = clean_digest_attestation["package_archive_digest_attestation_digest"]

    # 1. Digest attestation audit case builds.
    case = build_waveguide_package_archive_digest_attestation_audit_case(
        stmt, att_digest, True, 0, stmt["archive_display_path"], archive_override_digest=stmt["archive_file_digest_recomputed"]
    )
    assert isinstance(case, WaveguidePackageArchiveDigestAttestationAuditCase)
    assert case.attestation_audit_status == "archive_digest_attestation_audit_verified"

    # 2. Digest attestation audit case validates.
    # The top-level validator check handles this, but we can verify field values.
    assert case.archive_file_digest_match is True
    assert case.archive_digest_attestation_statement_digest_match is True

    # 3. Audit case digest is deterministic.
    dig1 = hash_waveguide_package_archive_digest_attestation_audit_case(case)
    dig2 = hash_waveguide_package_archive_digest_attestation_audit_case(case)
    assert dig1 == dig2
    assert case.archive_digest_attestation_audit_case_digest == dig1

    # 4. archive_digest_attestation_audit_case_digest is excluded from its own digest input.
    c_dict = asdict(case)
    c_dict["archive_digest_attestation_audit_case_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_digest_attestation_audit_case(c_dict) == dig1


def test_audit_report_lifecycle(clean_digest_attestation):
    recorded_digest = clean_digest_attestation["archive_candidate_digest"]

    # 17. Top-level digest attestation audit report builds.
    report = build_waveguide_package_archive_digest_attestation_audit_report(
        clean_digest_attestation, archive_override_digest=recorded_digest
    )
    assert isinstance(report, WaveguidePackageArchiveDigestAttestationAuditReport)
    assert report.package_archive_digest_attestation_audit_report_status == "package_archive_digest_attestation_verified"

    # 18. Top-level digest attestation audit report validates.
    ok, errs = validate_waveguide_package_archive_digest_attestation_audit_report(report)
    assert ok is True, f"Errors: {errs}"

    # 19. Report digest is deterministic.
    dig1 = hash_waveguide_package_archive_digest_attestation_audit_report(report)
    dig2 = hash_waveguide_package_archive_digest_attestation_audit_report(report)
    assert dig1 == dig2
    assert report.package_archive_digest_attestation_audit_report_digest == dig1

    # 20. package_archive_digest_attestation_audit_report_digest is excluded from its own digest input.
    r_dict = asdict(report)
    r_dict["package_archive_digest_attestation_audit_report_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_digest_attestation_audit_report(r_dict) == dig1

    # 21. Verified attestation audit case count is 1.
    assert report.verified_archive_digest_attestation_audit_count == 1


def test_audit_failures_and_blocks(clean_digest_attestation):
    recorded_digest = clean_digest_attestation["archive_candidate_digest"]

    # 5. Digest attestation independent validation failure blocks audit.
    att_bad = dict(clean_digest_attestation)
    att_bad["package_archive_digest_attestation_id"] = "bad_id"
    att_bad["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(att_bad)
    report = build_waveguide_package_archive_digest_attestation_audit_report(att_bad, archive_override_digest=recorded_digest)
    assert report.package_archive_digest_attestation_audit_report_status == "package_archive_digest_attestation_blocked"

    # 6. Attestation statement digest mismatch blocks audit.
    att_stmt_bad = dict(clean_digest_attestation)
    stmt = dict(att_stmt_bad["archive_digest_attestation_statements"][0])
    stmt["archive_filename"] = "mutated.zip"
    att_stmt_bad["archive_digest_attestation_statements"] = [stmt]
    att_stmt_bad["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(att_stmt_bad)
    report2 = build_waveguide_package_archive_digest_attestation_audit_report(att_stmt_bad, archive_override_digest=recorded_digest)
    assert report2.package_archive_digest_attestation_audit_report_status == "package_archive_digest_attestation_blocked"

    # 7. Recomputed archive digest mismatch blocks audit.
    report3 = build_waveguide_package_archive_digest_attestation_audit_report(clean_digest_attestation, archive_override_digest="mismatch_digest")
    assert report3.package_archive_digest_attestation_audit_report_status == "package_archive_digest_attestation_invalid"

    # 10. Real signature claimed true blocks audit.
    rep_clean = build_waveguide_package_archive_digest_attestation_audit_report(clean_digest_attestation, archive_override_digest=recorded_digest)
    r_dict = asdict(rep_clean)
    r_dict["real_signature_absent_verified"] = False
    r_dict["package_archive_digest_attestation_audit_report_digest"] = hash_waveguide_package_archive_digest_attestation_audit_report(r_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation_audit_report(r_dict)
    assert ok is False
    assert any("real_signature_absent_verified" in e for e in errs)

    # 13. Private key material loaded true blocks audit.
    r_dict = asdict(rep_clean)
    r_dict["private_key_material_absent_verified"] = False
    r_dict["package_archive_digest_attestation_audit_report_digest"] = hash_waveguide_package_archive_digest_attestation_audit_report(r_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation_audit_report(r_dict)
    assert ok is False
    assert any("private_key_material_absent_verified" in e for e in errs)


def test_audit_report_artifacts(tmp_path, clean_digest_attestation):
    recorded_digest = clean_digest_attestation["archive_candidate_digest"]
    report = build_waveguide_package_archive_digest_attestation_audit_report(
        clean_digest_attestation, archive_override_digest=recorded_digest
    )
    out_json = str(tmp_path / "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION_AUDIT_REPORT.json")
    export_waveguide_package_archive_digest_attestation_audit_report(report, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["package_archive_digest_attestation_audit_report_id"] == "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-DIGEST-ATTESTATION-AUDIT-REPORT"
