# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Digest Attestation.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_signing_plan import build_waveguide_package_archive_signing_plan
from sol_waveguide_package_archive_signing_gate import (
    build_waveguide_package_archive_signing_gate,
    hash_waveguide_package_archive_signing_gate
)
from sol_waveguide_package_archive_digest_attestation import (
    build_waveguide_package_archive_digest_attestation_statement,
    validate_waveguide_package_archive_digest_attestation_statement,
    build_waveguide_package_archive_digest_attestation,
    validate_waveguide_package_archive_digest_attestation,
    hash_waveguide_package_archive_digest_attestation_statement,
    hash_waveguide_package_archive_digest_attestation,
    WaveguidePackageArchiveDigestAttestationStatement,
    WaveguidePackageArchiveDigestAttestation,
    export_waveguide_package_archive_digest_attestation
)


@pytest.fixture
def clean_signing_gate() -> dict:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        idx_dict = json.load(f)
    plan = build_waveguide_package_archive_signing_plan(idx_dict)
    gate = build_waveguide_package_archive_signing_gate(plan)
    return asdict(gate)


def test_digest_attestation_statement_lifecycle(clean_signing_gate):
    recorded_digest = clean_signing_gate["current_archive_candidate_digest"]
    archive_filepath = clean_signing_gate["current_archive_candidate_display_path"]

    # 1. Digest attestation statement can be built.
    statement = build_waveguide_package_archive_digest_attestation_statement(
        clean_signing_gate, 0, archive_filepath, archive_override_digest=recorded_digest
    )
    assert isinstance(statement, WaveguidePackageArchiveDigestAttestationStatement)
    assert statement.archive_digest_attestation_statement_status == "archive_digest_attestation_statement_ready"

    # 2. Digest attestation statement validates.
    ok, errs = validate_waveguide_package_archive_digest_attestation_statement(statement)
    assert ok is True, f"Errors: {errs}"

    # 3. Statement digest is deterministic.
    dig1 = hash_waveguide_package_archive_digest_attestation_statement(statement)
    dig2 = hash_waveguide_package_archive_digest_attestation_statement(statement)
    assert dig1 == dig2
    assert statement.archive_digest_attestation_statement_digest == dig1

    # 4. archive_digest_attestation_statement_digest is excluded from its own digest input.
    s_dict = asdict(statement)
    s_dict["archive_digest_attestation_statement_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_digest_attestation_statement(s_dict) == dig1


def test_digest_attestation_lifecycle(clean_signing_gate):
    recorded_digest = clean_signing_gate["current_archive_candidate_digest"]

    # 5. Digest attestation builds from clean signing gate.
    att = build_waveguide_package_archive_digest_attestation(
        clean_signing_gate, archive_override_digest=recorded_digest
    )
    assert isinstance(att, WaveguidePackageArchiveDigestAttestation)
    assert att.package_archive_digest_attestation_status == "package_archive_digest_attested"

    # 6. Digest attestation validates.
    ok, errs = validate_waveguide_package_archive_digest_attestation(att)
    assert ok is True, f"Errors: {errs}"

    # 7. Attestation digest is deterministic.
    dig1 = hash_waveguide_package_archive_digest_attestation(att)
    dig2 = hash_waveguide_package_archive_digest_attestation(att)
    assert dig1 == dig2
    assert att.package_archive_digest_attestation_digest == dig1

    # 8. package_archive_digest_attestation_digest is excluded from its own digest input.
    a_dict = asdict(att)
    a_dict["package_archive_digest_attestation_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_digest_attestation(a_dict) == dig1


def test_digest_attestation_failures_and_blocks(clean_signing_gate):
    recorded_digest = clean_signing_gate["current_archive_candidate_digest"]

    # 9. Signing gate validation failure blocks attestation.
    gate_bad = dict(clean_signing_gate)
    gate_bad["package_archive_signing_gate_id"] = "bad_id"
    gate_bad["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(gate_bad)
    att = build_waveguide_package_archive_digest_attestation(gate_bad, archive_override_digest=recorded_digest)
    assert att.package_archive_digest_attestation_status == "package_archive_digest_attestation_blocked"

    # 10. Signing gate status not ready blocks attestation.
    gate_not_ready = dict(clean_signing_gate)
    gate_not_ready["package_archive_signing_gate_status"] = "package_archive_signing_gate_blocked"
    gate_not_ready["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(gate_not_ready)
    att2 = build_waveguide_package_archive_digest_attestation(gate_not_ready, archive_override_digest=recorded_digest)
    assert att2.package_archive_digest_attestation_status == "package_archive_digest_attestation_blocked"

    # 11. Archive file digest recomputation matches recorded digest.
    # 12. Archive digest mismatch blocks attestation.
    att3 = build_waveguide_package_archive_digest_attestation(clean_signing_gate, archive_override_digest="mismatch_digest_value")
    assert att3.package_archive_digest_attestation_status == "package_archive_digest_attestation_invalid"

    # 13. Real signature claimed true blocks attestation.
    att_clean = build_waveguide_package_archive_digest_attestation(clean_signing_gate, archive_override_digest=recorded_digest)
    a_dict = asdict(att_clean)
    a_dict["real_signature_claimed"] = True
    a_dict["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(a_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation(a_dict)
    assert ok is False
    assert any("real_signature_claimed" in e for e in errs)

    # 14. Real key signing used true blocks attestation.
    a_dict = asdict(att_clean)
    a_dict["real_key_signing_used"] = True
    a_dict["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(a_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation(a_dict)
    assert ok is False
    assert any("real_key_signing_used" in e for e in errs)

    # 15. Private key material loaded true blocks attestation.
    a_dict = asdict(att_clean)
    a_dict["private_key_material_loaded"] = True
    a_dict["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(a_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation(a_dict)
    assert ok is False
    assert any("private_key_material_loaded" in e for e in errs)

    # 16. Credentials loaded true blocks attestation.
    a_dict = asdict(att_clean)
    a_dict["credentials_loaded"] = True
    a_dict["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(a_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation(a_dict)
    assert ok is False
    assert any("credentials_loaded" in e for e in errs)

    # 17. Network access used true blocks attestation.
    a_dict = asdict(att_clean)
    a_dict["network_access_used"] = True
    a_dict["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(a_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation(a_dict)
    assert ok is False
    assert any("network_access_used" in e for e in errs)

    # 18. External signing/timestamp authority used true blocks attestation.
    a_dict = asdict(att_clean)
    a_dict["external_signing_used"] = True
    a_dict["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(a_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation(a_dict)
    assert ok is False
    assert any("external_signing_used" in e for e in errs)

    # 19. Upload/deploy/publish/production mutation performed true blocks attestation.
    a_dict = asdict(att_clean)
    a_dict["upload_performed"] = True
    a_dict["package_archive_digest_attestation_digest"] = hash_waveguide_package_archive_digest_attestation(a_dict)
    ok, errs = validate_waveguide_package_archive_digest_attestation(a_dict)
    assert ok is False
    assert any("upload_performed" in e for e in errs)


def test_digest_attestation_artifacts(tmp_path, clean_signing_gate):
    recorded_digest = clean_signing_gate["current_archive_candidate_digest"]
    att = build_waveguide_package_archive_digest_attestation(
        clean_signing_gate, archive_override_digest=recorded_digest
    )
    out_json = str(tmp_path / "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json")
    export_waveguide_package_archive_digest_attestation(att, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["package_archive_digest_attestation_id"] == "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-DIGEST-ATTESTATION"
