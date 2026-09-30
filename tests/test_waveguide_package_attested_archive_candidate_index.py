# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Attested Archive Candidate Index.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_signing_plan import build_waveguide_package_archive_signing_plan
from sol_waveguide_package_archive_signing_gate import build_waveguide_package_archive_signing_gate
from sol_waveguide_package_archive_digest_attestation import build_waveguide_package_archive_digest_attestation
from sol_waveguide_package_archive_digest_attestation_validator import (
    build_waveguide_package_archive_digest_attestation_audit_report,
    hash_waveguide_package_archive_digest_attestation_audit_report
)
from sol_waveguide_package_attested_archive_candidate_index import (
    build_waveguide_package_attested_archive_candidate_entry,
    validate_waveguide_package_attested_archive_candidate_entry,
    build_waveguide_package_attested_archive_candidate_index,
    validate_waveguide_package_attested_archive_candidate_index,
    hash_waveguide_package_attested_archive_candidate_entry,
    hash_waveguide_package_attested_archive_candidate_index,
    WaveguidePackageAttestedArchiveCandidateEntry,
    WaveguidePackageAttestedArchiveCandidateIndex,
    export_waveguide_package_attested_archive_candidate_index
)


@pytest.fixture
def clean_audit_report() -> dict:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        idx_dict = json.load(f)
    plan = build_waveguide_package_archive_signing_plan(idx_dict)
    gate = build_waveguide_package_archive_signing_gate(plan)
    recorded_digest = gate.current_archive_candidate_digest
    att = build_waveguide_package_archive_digest_attestation(gate, archive_override_digest=recorded_digest)
    report = build_waveguide_package_archive_digest_attestation_audit_report(att, archive_override_digest=recorded_digest)
    return asdict(report)


def test_attested_entry_lifecycle(clean_audit_report):
    # 1. Attested archive candidate entry can be built.
    entry = build_waveguide_package_attested_archive_candidate_entry(clean_audit_report, 0)
    assert isinstance(entry, WaveguidePackageAttestedArchiveCandidateEntry)
    assert entry.attested_archive_candidate_status == "attested_archive_candidate_verified"

    # 2. Attested archive candidate entry validates.
    ok, errs = validate_waveguide_package_attested_archive_candidate_entry(entry)
    assert ok is True, f"Errors: {errs}"

    # 3. Entry digest is deterministic.
    dig1 = hash_waveguide_package_attested_archive_candidate_entry(entry)
    dig2 = hash_waveguide_package_attested_archive_candidate_entry(entry)
    assert dig1 == dig2
    assert entry.attested_archive_candidate_entry_digest == dig1

    # 4. attested_archive_candidate_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["attested_archive_candidate_entry_digest"] = "MUTATED"
    assert hash_waveguide_package_attested_archive_candidate_entry(e_dict) == dig1


def test_attested_index_lifecycle(clean_audit_report):
    # 5. Attested archive candidate index builds.
    index_obj = build_waveguide_package_attested_archive_candidate_index(clean_audit_report)
    assert isinstance(index_obj, WaveguidePackageAttestedArchiveCandidateIndex)
    assert index_obj.package_attested_archive_candidate_index_status == "package_attested_archive_candidate_index_valid"

    # 6. Attested archive candidate index validates.
    ok, errs = validate_waveguide_package_attested_archive_candidate_index(index_obj)
    assert ok is True, f"Errors: {errs}"

    # 7. Index digest is deterministic.
    dig1 = hash_waveguide_package_attested_archive_candidate_index(index_obj)
    dig2 = hash_waveguide_package_attested_archive_candidate_index(index_obj)
    assert dig1 == dig2
    assert index_obj.package_attested_archive_candidate_index_digest == dig1

    # 8. package_attested_archive_candidate_index_digest is excluded from its own digest input.
    i_dict = asdict(index_obj)
    i_dict["package_attested_archive_candidate_index_digest"] = "MUTATED"
    assert hash_waveguide_package_attested_archive_candidate_index(i_dict) == dig1

    # 13. Verified attested archive candidate count is 1.
    assert index_obj.verified_attested_archive_candidate_count == 1

    # 14. Current attested archive candidate digest matches report digest.
    assert index_obj.current_attested_archive_candidate_digest == clean_audit_report["archive_file_digest_recomputed"]


def test_attested_index_failures_and_blocks(clean_audit_report):
    # 9. Audit report validation failure blocks index.
    rep_bad = dict(clean_audit_report)
    rep_bad["package_archive_digest_attestation_audit_report_id"] = "bad_id"
    rep_bad["package_archive_digest_attestation_audit_report_digest"] = hash_waveguide_package_archive_digest_attestation_audit_report(rep_bad)
    index_obj = build_waveguide_package_attested_archive_candidate_index(rep_bad)
    assert index_obj.package_attested_archive_candidate_index_status == "package_attested_archive_candidate_index_blocked"

    # 10. Audit report status not ready/verified blocks index.
    rep_unverified = dict(clean_audit_report)
    rep_unverified["package_archive_digest_attestation_audit_report_status"] = "package_archive_digest_attestation_blocked"
    rep_unverified["package_archive_digest_attestation_audit_report_digest"] = hash_waveguide_package_archive_digest_attestation_audit_report(rep_unverified)
    index_obj2 = build_waveguide_package_attested_archive_candidate_index(rep_unverified)
    assert index_obj2.package_attested_archive_candidate_index_status == "package_attested_archive_candidate_index_blocked"

    # 11. Missing archive candidate digest blocks index.
    rep_nodig = dict(clean_audit_report)
    rep_nodig["archive_file_digest_recomputed"] = ""
    rep_nodig["package_archive_digest_attestation_audit_report_digest"] = hash_waveguide_package_archive_digest_attestation_audit_report(rep_nodig)
    index_obj3 = build_waveguide_package_attested_archive_candidate_index(rep_nodig)
    # The entry building will fail due to validation or index status will be blocked because no entries build
    # If the digest is missing, the entry build fails because entry validation requires archive_file_digest
    assert index_obj3.package_attested_archive_candidate_index_status == "package_attested_archive_candidate_index_blocked" or \
           index_obj3.package_attested_archive_candidate_index_status == "package_attested_archive_candidate_index_invalid"

    # 12. Upload/deploy/publish/production mutation performed true blocks index.
    rep_mutate = dict(clean_audit_report)
    rep_mutate["upload_performed"] = True
    rep_mutate["package_archive_digest_attestation_audit_report_digest"] = hash_waveguide_package_archive_digest_attestation_audit_report(rep_mutate)
    index_obj4 = build_waveguide_package_attested_archive_candidate_index(rep_mutate)
    assert index_obj4.package_attested_archive_candidate_index_status == "package_attested_archive_candidate_index_invalid"


def test_attested_index_artifacts(tmp_path, clean_audit_report):
    index_obj = build_waveguide_package_attested_archive_candidate_index(clean_audit_report)
    out_json = str(tmp_path / "SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json")
    export_waveguide_package_attested_archive_candidate_index(index_obj, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["package_attested_archive_candidate_index_id"] == "SOL-WAVEGUIDE-PACKAGE-ATTESTED-ARCHIVE-CANDIDATE-INDEX"
