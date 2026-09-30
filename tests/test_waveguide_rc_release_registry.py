# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Release Registry and Promotion Index
"""

import os
import json
import pytest

from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_promotion_ledger import build_waveguide_rc_promotion_record
from sol_waveguide_rc_promotion_court import (
    build_waveguide_rc_promotion_case,
    build_waveguide_rc_court_panel,
    build_waveguide_rc_court_verdict
)
from sol_waveguide_rc_release_registry import (
    build_waveguide_rc_registry_entry,
    validate_waveguide_rc_registry_entry,
    build_waveguide_rc_release_registry,
    validate_waveguide_rc_release_registry,
    hash_waveguide_rc_registry_entry,
    hash_waveguide_rc_release_registry,
    summarize_waveguide_rc_release_registry,
    export_waveguide_rc_release_registry,
    compare_waveguide_rc_release_registries
)


def test_registry_entries_build_successfully():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)

    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)

    assert entry1 is not None
    assert entry1.rc_id == "SOL-WAVEGUIDE-RC1"
    assert entry1.release_status == "release_registered"


def test_registry_entry_validation_works():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)
    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)

    ok, reasons = validate_waveguide_rc_registry_entry(entry1)
    assert ok is True
    assert "RC_REGISTRY_ENTRY_DIGEST_VALID" in reasons
    assert "RC_REGISTRY_COURT_VERDICT_APPROVED" in reasons


def test_rejected_verdict_blocks_entry():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc1["optimization_profiles"].append("COST_MODEL_DEBUG")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)

    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)
    assert entry1.release_status == "release_blocked"

    ok, reasons = validate_waveguide_rc_registry_entry(entry1)
    assert ok is False
    assert "RC_REGISTRY_COURT_VERDICT_NOT_APPROVED" in reasons


def test_missing_quorum_blocks_entry():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    panel1 = [att for att in panel1 if att.ranger_id != "ReleaseGateRanger"]
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)

    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)
    assert entry1.release_status == "release_blocked"


def test_digests_are_deterministic_and_exclude_self():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)
    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)

    entry_dict = entry1.__dict__.copy()
    entry_dict["registry_entry_digest"] = "different_entry_digest"

    h1 = hash_waveguide_rc_registry_entry(entry1)
    h2 = hash_waveguide_rc_registry_entry(entry_dict)
    assert h1 == h2


def test_top_level_registry_builds_and_validates():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)
    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)

    rc2 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
    rec2 = build_waveguide_rc_promotion_record(rc2)
    case2 = build_waveguide_rc_promotion_case(rec2)
    panel2 = build_waveguide_rc_court_panel(rec2)
    verd2 = build_waveguide_rc_court_verdict(case2, panel2)
    entry2 = build_waveguide_rc_registry_entry(verd2, rec2)

    reg = build_waveguide_rc_release_registry([entry1, entry2])

    assert reg.registry_status == "registry_valid"
    assert "SOL-WAVEGUIDE-RC1" in reg.approved_rc_ids
    assert "SOL-WAVEGUIDE-RC2" in reg.approved_rc_ids
    assert reg.latest_foundation_rc == "SOL-WAVEGUIDE-RC1"
    assert reg.latest_governed_stack_rc == "SOL-WAVEGUIDE-RC2"

    ok, reasons = validate_waveguide_rc_release_registry(reg)
    assert ok is True
    assert "RC_REGISTRY_DIGEST_VALID" in reasons
    assert "RC_REGISTRY_APPROVED_RC_INDEXED" in reasons


def test_top_level_digest_excludes_self():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)
    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)

    reg = build_waveguide_rc_release_registry([entry1])
    reg_dict = reg.__dict__.copy()
    reg_dict["registry_digest"] = "different_registry_digest"

    h1 = hash_waveguide_rc_release_registry(reg)
    h2 = hash_waveguide_rc_release_registry(reg_dict)
    assert h1 == h2


def test_registry_summary_and_compare_are_deterministic():
    rc1 = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rec1 = build_waveguide_rc_promotion_record(rc1)
    case1 = build_waveguide_rc_promotion_case(rec1)
    panel1 = build_waveguide_rc_court_panel(rec1)
    verd1 = build_waveguide_rc_court_verdict(case1, panel1)
    entry1 = build_waveguide_rc_registry_entry(verd1, rec1)

    reg1 = build_waveguide_rc_release_registry([entry1])
    reg2 = build_waveguide_rc_release_registry([entry1])

    s1 = summarize_waveguide_rc_release_registry(reg1)
    s2 = summarize_waveguide_rc_release_registry(reg2)
    assert s1 == s2

    diff = compare_waveguide_rc_release_registries(reg1, reg2)
    assert len(diff) == 0


def test_registry_files_exist_on_disk():
    from sol_waveguide_rc_release_registry import REPO_ROOT

    registry_json = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    doc_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.md")

    assert os.path.exists(registry_json)
    assert os.path.exists(doc_path)
