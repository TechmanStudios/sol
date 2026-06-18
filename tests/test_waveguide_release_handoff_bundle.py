# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Release Handoff Bundle.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_release_handoff_bundle import (
    build_waveguide_release_handoff_entry,
    validate_waveguide_release_handoff_entry,
    build_waveguide_release_handoff_bundle,
    validate_waveguide_release_handoff_bundle,
    hash_waveguide_release_handoff_entry,
    hash_waveguide_release_handoff_bundle,
    export_waveguide_release_handoff_bundle,
    WaveguideReleaseHandoffEntry,
    WaveguideReleaseHandoffBundle
)


@pytest.fixture
def clean_attested_index() -> dict:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        return json.load(f)


def test_release_handoff_entry_lifecycle():
    # 1. Release handoff entry can be built.
    entry = build_waveguide_release_handoff_entry(
        kind="archive_zip",
        role="archive_zip",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip",
        digest="b00628c0435b36035c4552d70b4b9a451d869cb2828b1afccaa5ac467054621d",
        size=70162,
        fmt="zip",
        src_digest="b00628c0435b36035c4552d70b4b9a451d869cb2828b1afccaa5ac467054621d",
        src_status="verified",
        index=0
    )
    assert isinstance(entry, WaveguideReleaseHandoffEntry)
    assert entry.release_handoff_entry_status == "release_handoff_entry_ready"

    # 2. Release handoff entry validates.
    ok, errs = validate_waveguide_release_handoff_entry(entry)
    assert ok is True, f"Errors: {errs}"

    # 3. Entry digest is deterministic.
    dig1 = hash_waveguide_release_handoff_entry(entry)
    dig2 = hash_waveguide_release_handoff_entry(entry)
    assert dig1 == dig2
    assert entry.release_handoff_entry_digest == dig1

    # 4. release_handoff_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["release_handoff_entry_digest"] = "MUTATED"
    assert hash_waveguide_release_handoff_entry(e_dict) == dig1


def test_release_handoff_bundle_lifecycle(clean_attested_index):
    # 5. Release handoff bundle builds.
    bundle = build_waveguide_release_handoff_bundle(clean_attested_index)
    assert isinstance(bundle, WaveguideReleaseHandoffBundle)
    assert bundle.release_handoff_bundle_status == "release_handoff_bundle_ready"

    # 6. Release handoff bundle validates.
    ok, errs = validate_waveguide_release_handoff_bundle(bundle)
    assert ok is True, f"Errors: {errs}"

    # 7. Bundle digest is deterministic.
    dig1 = hash_waveguide_release_handoff_bundle(bundle)
    dig2 = hash_waveguide_release_handoff_bundle(bundle)
    assert dig1 == dig2
    assert bundle.release_handoff_bundle_digest == dig1

    # 8. release_handoff_bundle_digest is excluded from its own digest input.
    b_dict = asdict(bundle)
    b_dict["release_handoff_bundle_digest"] = "MUTATED"
    assert hash_waveguide_release_handoff_bundle(b_dict) == dig1


def test_release_handoff_bundle_failures_and_blocks(clean_attested_index):
    # 9. Attested archive candidate index validation failure blocks bundle.
    idx_bad = dict(clean_attested_index)
    idx_bad["package_attested_archive_candidate_index_id"] = "bad_id"
    from sol_waveguide_package_attested_archive_candidate_index import hash_waveguide_package_attested_archive_candidate_index
    idx_bad["package_attested_archive_candidate_index_digest"] = hash_waveguide_package_attested_archive_candidate_index(idx_bad)
    bundle = build_waveguide_release_handoff_bundle(idx_bad)
    assert bundle.release_handoff_bundle_status in ("release_handoff_bundle_blocked", "release_handoff_bundle_invalid")

    # 10. Attested archive candidate index status not valid blocks bundle.
    idx_unverified = dict(clean_attested_index)
    idx_unverified["package_attested_archive_candidate_index_status"] = "package_attested_archive_candidate_index_blocked"
    idx_unverified["package_attested_archive_candidate_index_digest"] = hash_waveguide_package_attested_archive_candidate_index(idx_unverified)
    bundle2 = build_waveguide_release_handoff_bundle(idx_unverified)
    assert bundle2.release_handoff_bundle_status in ("release_handoff_bundle_blocked", "release_handoff_bundle_invalid")

    # 11. Missing archive candidate digest blocks bundle.
    idx_nodig = dict(clean_attested_index)
    idx_nodig["current_attested_archive_candidate_digest"] = ""
    idx_nodig["package_attested_archive_candidate_index_digest"] = hash_waveguide_package_attested_archive_candidate_index(idx_nodig)
    bundle3 = build_waveguide_release_handoff_bundle(idx_nodig)
    # The entry or index status becomes invalid/blocked
    assert bundle3.release_handoff_bundle_status in ("release_handoff_bundle_invalid", "release_handoff_bundle_blocked")

    # 13. Real signature status other than not_performed blocks or warns according to chosen semantics.
    # We choose to block by returning invalid status
    idx_sign = dict(clean_attested_index)
    idx_sign["real_signature_status"] = "signed"
    idx_sign["package_attested_archive_candidate_index_digest"] = hash_waveguide_package_attested_archive_candidate_index(idx_sign)
    bundle4 = build_waveguide_release_handoff_bundle(idx_sign)
    assert bundle4.release_handoff_bundle_status in ("release_handoff_bundle_blocked", "release_handoff_bundle_invalid")

    # 14. Upload/deploy/publish/production mutation performed true blocks bundle.
    idx_upload = dict(clean_attested_index)
    idx_upload["upload_performed"] = True
    # Mutate a candidate to trigger entry validation failure
    cands = list(idx_upload["attested_archive_candidates"])
    cand = dict(cands[0])
    cand["upload_performed"] = True
    from sol_waveguide_package_attested_archive_candidate_index import hash_waveguide_package_attested_archive_candidate_entry
    cand["attested_archive_candidate_entry_digest"] = hash_waveguide_package_attested_archive_candidate_entry(cand)
    idx_upload["attested_archive_candidates"] = [cand]
    idx_upload["package_attested_archive_candidate_index_digest"] = hash_waveguide_package_attested_archive_candidate_index(idx_upload)
    bundle5 = build_waveguide_release_handoff_bundle(idx_upload)
    assert bundle5.release_handoff_bundle_status in ("release_handoff_bundle_blocked", "release_handoff_bundle_invalid")


def test_release_handoff_bundle_artifacts(tmp_path, clean_attested_index):
    # 15. Handoff bundle JSON artifact exists.
    bundle = build_waveguide_release_handoff_bundle(clean_attested_index)
    out_json = str(tmp_path / "SOL_WAVEGUIDE_RELEASE_HANDOFF_BUNDLE.json")
    export_waveguide_release_handoff_bundle(bundle, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["release_handoff_bundle_id"] == "SOL-WAVEGUIDE-RELEASE-HANDOFF-BUNDLE"
