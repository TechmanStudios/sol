# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Offline Consumer Verification Kit.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_release_handoff_bundle import (
    build_waveguide_release_handoff_bundle,
    hash_waveguide_release_handoff_bundle
)
from sol_waveguide_offline_consumer_verification_kit import (
    build_waveguide_offline_consumer_verification_step,
    validate_waveguide_offline_consumer_verification_step,
    build_waveguide_offline_consumer_verification_kit,
    validate_waveguide_offline_consumer_verification_kit,
    hash_waveguide_offline_verification_step,
    hash_waveguide_offline_consumer_verification_kit,
    export_waveguide_offline_consumer_verification_kit,
    WaveguideOfflineVerificationStep,
    WaveguideOfflineConsumerVerificationKit
)


@pytest.fixture
def clean_handoff_bundle() -> dict:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        idx_dict = json.load(f)
    bundle = build_waveguide_release_handoff_bundle(idx_dict)
    return asdict(bundle)


def test_offline_verification_step_lifecycle():
    # 1. Offline verification step can be built.
    step = build_waveguide_offline_consumer_verification_step(
        kind="verify_archive_sha256",
        title="Verify Archive SHA256",
        desc="Verifies archive digest",
        cmd="sha256sum docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip",
        expected="b00628c0435b36035c4552d70b4b9a451d869cb2828b1afccaa5ac467054621d",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip",
        digest="b00628c0435b36035c4552d70b4b9a451d869cb2828b1afccaa5ac467054621d",
        artifact_kind="archive_zip",
        index=0
    )
    assert isinstance(step, WaveguideOfflineVerificationStep)
    assert step.offline_verification_step_status == "offline_verification_step_ready"

    # 2. Offline verification step validates.
    ok, errs = validate_waveguide_offline_consumer_verification_step(step)
    assert ok is True, f"Errors: {errs}"

    # 3. Step digest is deterministic.
    dig1 = hash_waveguide_offline_verification_step(step)
    dig2 = hash_waveguide_offline_verification_step(step)
    assert dig1 == dig2
    assert step.offline_verification_step_digest == dig1

    # 4. offline_verification_step_digest is excluded from its own digest input.
    s_dict = asdict(step)
    s_dict["offline_verification_step_digest"] = "MUTATED"
    assert hash_waveguide_offline_verification_step(s_dict) == dig1


def test_offline_verification_kit_lifecycle(clean_handoff_bundle):
    # 5. Offline consumer verification kit builds.
    kit = build_waveguide_offline_consumer_verification_kit(clean_handoff_bundle)
    assert isinstance(kit, WaveguideOfflineConsumerVerificationKit)
    assert kit.offline_consumer_verification_kit_status == "offline_consumer_verification_kit_ready"

    # 6. Offline consumer verification kit validates.
    ok, errs = validate_waveguide_offline_consumer_verification_kit(kit)
    assert ok is True, f"Errors: {errs}"

    # 7. Kit digest is deterministic.
    dig1 = hash_waveguide_offline_consumer_verification_kit(kit)
    dig2 = hash_waveguide_offline_consumer_verification_kit(kit)
    assert dig1 == dig2
    assert kit.offline_consumer_verification_kit_digest == dig1

    # 8. offline_consumer_verification_kit_digest is excluded from its own digest input.
    k_dict = asdict(kit)
    k_dict["offline_consumer_verification_kit_digest"] = "MUTATED"
    assert hash_waveguide_offline_consumer_verification_kit(k_dict) == dig1

    # 16. Consumer verification ready true in clean kit.
    assert kit.consumer_verification_ready is True


def test_offline_verification_kit_failures_and_blocks(clean_handoff_bundle):
    # 9. Release handoff bundle validation failure blocks kit.
    bun_bad = dict(clean_handoff_bundle)
    bun_bad["release_handoff_bundle_id"] = "bad_id"
    bun_bad["release_handoff_bundle_digest"] = hash_waveguide_release_handoff_bundle(bun_bad)
    kit = build_waveguide_offline_consumer_verification_kit(bun_bad)
    assert kit.offline_consumer_verification_kit_status == "offline_consumer_verification_kit_blocked"

    # 10. Release handoff bundle status not ready blocks kit.
    bun_not_ready = dict(clean_handoff_bundle)
    bun_not_ready["release_handoff_bundle_status"] = "release_handoff_bundle_blocked"
    bun_not_ready["release_handoff_bundle_digest"] = hash_waveguide_release_handoff_bundle(bun_not_ready)
    kit2 = build_waveguide_offline_consumer_verification_kit(bun_not_ready)
    assert kit2.offline_consumer_verification_kit_status == "offline_consumer_verification_kit_blocked"

    # 11. Any verification step requiring network blocks kit.
    # We test building a step requiring network
    step = build_waveguide_offline_consumer_verification_step(
        kind="verify_archive_sha256", title="Network Step", desc="Requires network",
        cmd="curl example.com", expected="ok", path="some_path", digest="some_digest",
        artifact_kind="json", index=0, requires_network=True
    )
    assert step.offline_verification_step_status == "offline_verification_step_blocked"

    # 12. Any verification step requiring credentials blocks kit.
    step2 = build_waveguide_offline_consumer_verification_step(
        kind="verify_archive_sha256", title="Creds Step", desc="Requires credentials",
        cmd="command", expected="ok", path="some_path", digest="some_digest",
        artifact_kind="json", index=0, requires_credentials=True
    )
    assert step2.offline_verification_step_status == "offline_verification_step_blocked"

    # 13. Any verification step requiring private key blocks kit.
    step3 = build_waveguide_offline_consumer_verification_step(
        kind="verify_archive_sha256", title="Key Step", desc="Requires private key",
        cmd="command", expected="ok", path="some_path", digest="some_digest",
        artifact_kind="json", index=0, requires_private_key=True
    )
    assert step3.offline_verification_step_status == "offline_verification_step_blocked"


def test_offline_verification_kit_artifacts(tmp_path, clean_handoff_bundle):
    # 17. Offline verification kit JSON artifact exists.
    kit = build_waveguide_offline_consumer_verification_kit(clean_handoff_bundle)
    out_json = str(tmp_path / "SOL_WAVEGUIDE_OFFLINE_CONSUMER_VERIFICATION_KIT.json")
    export_waveguide_offline_consumer_verification_kit(kit, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["offline_consumer_verification_kit_id"] == "SOL-WAVEGUIDE-OFFLINE-CONSUMER-VERIFICATION-KIT"
