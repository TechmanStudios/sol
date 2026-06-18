# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Archive Signing Gate.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_package_archive_signing_plan import (
    build_waveguide_package_archive_signing_plan,
    hash_waveguide_package_archive_signing_plan
)
from sol_waveguide_package_archive_signing_gate import (
    build_waveguide_package_archive_signing_gate,
    validate_waveguide_package_archive_signing_gate,
    hash_waveguide_package_archive_signing_gate,
    WaveguidePackageArchiveSigningGate,
    export_waveguide_package_archive_signing_gate
)


@pytest.fixture
def clean_signing_plan() -> dict:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        idx_dict = json.load(f)
    plan = build_waveguide_package_archive_signing_plan(idx_dict)
    return asdict(plan)


def test_signing_gate_lifecycle(clean_signing_plan):
    # 1. Archive signing gate builds from clean signing plan.
    gate = build_waveguide_package_archive_signing_gate(clean_signing_plan)
    assert isinstance(gate, WaveguidePackageArchiveSigningGate)
    assert gate.package_archive_signing_gate_status == "package_archive_signing_gate_ready"
    assert gate.package_archive_signing_gate_decision == "allow_local_digest_attestation"

    # 2. Archive signing gate validates.
    ok, errs = validate_waveguide_package_archive_signing_gate(gate)
    assert ok is True, f"Errors: {errs}"

    # 3. Signing gate digest is deterministic.
    dig1 = hash_waveguide_package_archive_signing_gate(gate)
    dig2 = hash_waveguide_package_archive_signing_gate(gate)
    assert dig1 == dig2
    assert gate.package_archive_signing_gate_digest == dig1

    # 4. package_archive_signing_gate_digest is excluded from its own digest input.
    g_dict = asdict(gate)
    g_dict["package_archive_signing_gate_digest"] = "MUTATED"
    assert hash_waveguide_package_archive_signing_gate(g_dict) == dig1


def test_signing_gate_failures_and_blocks(clean_signing_plan):
    # 5. Signing plan validation failure blocks gate.
    plan_bad = dict(clean_signing_plan)
    plan_bad["package_archive_signing_plan_id"] = "bad_id"
    plan_bad["package_archive_signing_plan_digest"] = hash_waveguide_package_archive_signing_plan(plan_bad)
    gate = build_waveguide_package_archive_signing_gate(plan_bad)
    assert gate.package_archive_signing_gate_status == "package_archive_signing_gate_blocked"
    assert gate.package_archive_signing_gate_decision == "block_archive_signing"

    # 6. Signing plan status not ready blocks gate.
    plan_not_ready = dict(clean_signing_plan)
    plan_not_ready["package_archive_signing_plan_status"] = "package_archive_signing_plan_blocked"
    plan_not_ready["package_archive_signing_plan_digest"] = hash_waveguide_package_archive_signing_plan(plan_not_ready)
    gate2 = build_waveguide_package_archive_signing_gate(plan_not_ready)
    assert gate2.package_archive_signing_gate_status == "package_archive_signing_gate_blocked"

    # 7. Digest attestation allowed false blocks gate.
    gate_clean = build_waveguide_package_archive_signing_gate(clean_signing_plan)
    g_dict = asdict(gate_clean)
    g_dict["digest_attestation_allowed"] = False
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("digest_attestation_allowed" in e for e in errs)

    # 8. Local digest attestation allowed false blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["local_digest_attestation_allowed"] = False
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("local_digest_attestation_allowed" in e for e in errs)

    # 9. Real key signing allowed true blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["real_key_signing_allowed"] = True
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("real_key_signing_allowed" in e for e in errs)

    # 10. External signing allowed true blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["external_signing_allowed"] = True
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("external_signing_allowed" in e for e in errs)

    # 11. Timestamp authority allowed true blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["timestamp_authority_allowed"] = True
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("timestamp_authority_allowed" in e for e in errs)

    # 12. Missing future key-management requirement blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["requires_future_key_management_gate"] = False
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("requires_future_key_management_gate" in e for e in errs)

    # 13. Missing future signing-key gate requirement blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["requires_future_signing_key_gate"] = False
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("requires_future_signing_key_gate" in e for e in errs)

    # 14. Missing no-network-signing requirement blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["requires_no_network_signing"] = False
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("requires_no_network_signing" in e for e in errs)

    # 15. Missing no-credentials-loaded requirement blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["requires_no_credentials_loaded"] = False
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("requires_no_credentials_loaded" in e for e in errs)

    # 16. Any signing/upload/deploy/publish/mutate performed flag true blocks gate.
    g_dict = asdict(gate_clean)
    g_dict["upload_performed"] = True
    g_dict["package_archive_signing_gate_digest"] = hash_waveguide_package_archive_signing_gate(g_dict)
    ok, errs = validate_waveguide_package_archive_signing_gate(g_dict)
    assert ok is False
    assert any("upload_performed" in e for e in errs)


def test_signing_gate_artifacts(tmp_path, clean_signing_plan):
    gate = build_waveguide_package_archive_signing_gate(clean_signing_plan)
    out_json = str(tmp_path / "SOL_WAVEGUIDE_PACKAGE_ARCHIVE_SIGNING_GATE.json")
    export_waveguide_package_archive_signing_gate(gate, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["package_archive_signing_gate_id"] == "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-SIGNING-GATE"
