# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Package Pipeline Completion Index.
"""

import os
import json
import pytest
from dataclasses import asdict

from sol_waveguide_rc_promotion_ledger import REPO_ROOT
from sol_waveguide_release_handoff_bundle import build_waveguide_release_handoff_bundle
from sol_waveguide_offline_consumer_verification_kit import build_waveguide_offline_consumer_verification_kit
from sol_waveguide_distribution_readiness_closure_report import (
    build_waveguide_distribution_readiness_closure_report,
    hash_waveguide_distribution_readiness_closure_report
)
from sol_waveguide_package_pipeline_completion_index import (
    build_waveguide_package_pipeline_completion_entry,
    validate_waveguide_package_pipeline_completion_entry,
    build_waveguide_package_pipeline_completion_index,
    validate_waveguide_package_pipeline_completion_index,
    hash_waveguide_package_pipeline_completion_entry,
    hash_waveguide_package_pipeline_completion_index,
    export_waveguide_package_pipeline_completion_index,
    WaveguidePackagePipelineCompletionEntry,
    WaveguidePackagePipelineCompletionIndex
)


@pytest.fixture
def clean_closure_report() -> dict:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        idx_dict = json.load(f)
    bundle = build_waveguide_release_handoff_bundle(idx_dict)
    kit = build_waveguide_offline_consumer_verification_kit(bundle)
    report = build_waveguide_distribution_readiness_closure_report(bundle, kit)
    return asdict(report)


def test_completion_entry_lifecycle(clean_closure_report):
    # 1. Package pipeline completion entry can be built.
    entry = build_waveguide_package_pipeline_completion_entry(
        stage_id="archive_plan",
        stage_name="Archive Plan",
        stage_status="ready",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_PLAN.json",
        kind="json",
        report_dict=clean_closure_report,
        index=0
    )
    assert isinstance(entry, WaveguidePackagePipelineCompletionEntry)
    assert entry.package_pipeline_completion_entry_status == "package_pipeline_completion_entry_verified"

    # 2. Package pipeline completion entry validates.
    ok, errs = validate_waveguide_package_pipeline_completion_entry(entry)
    assert ok is True, f"Errors: {errs}"

    # 3. Entry digest is deterministic.
    dig1 = hash_waveguide_package_pipeline_completion_entry(entry)
    dig2 = hash_waveguide_package_pipeline_completion_entry(entry)
    assert dig1 == dig2
    assert entry.package_pipeline_completion_entry_digest == dig1

    # 4. package_pipeline_completion_entry_digest is excluded from its own digest input.
    e_dict = asdict(entry)
    e_dict["package_pipeline_completion_entry_digest"] = "MUTATED"
    assert hash_waveguide_package_pipeline_completion_entry(e_dict) == dig1


def test_completion_index_lifecycle(clean_closure_report):
    # 5. Package pipeline completion index builds.
    index_obj = build_waveguide_package_pipeline_completion_index(clean_closure_report)
    assert isinstance(index_obj, WaveguidePackagePipelineCompletionIndex)
    assert index_obj.package_pipeline_completion_index_status == "package_pipeline_completion_index_valid"

    # 6. Package pipeline completion index validates.
    ok, errs = validate_waveguide_package_pipeline_completion_index(index_obj)
    assert ok is True, f"Errors: {errs}"

    # 7. Completion index digest is deterministic.
    dig1 = hash_waveguide_package_pipeline_completion_index(index_obj)
    dig2 = hash_waveguide_package_pipeline_completion_index(index_obj)
    assert dig1 == dig2
    assert index_obj.package_pipeline_completion_index_digest == dig1

    # 8. package_pipeline_completion_index_digest is excluded from its own digest input.
    i_dict = asdict(index_obj)
    i_dict["package_pipeline_completion_index_digest"] = "MUTATED"
    assert hash_waveguide_package_pipeline_completion_index(i_dict) == dig1

    # 20+ completed stages verified
    assert index_obj.completed_stage_count >= 20


def test_completion_index_failures_and_blocks(clean_closure_report):
    # 9. Distribution readiness closure validation failure blocks index.
    rep_bad = dict(clean_closure_report)
    rep_bad["distribution_readiness_closure_report_id"] = "bad_id"
    rep_bad["distribution_readiness_closure_report_digest"] = hash_waveguide_distribution_readiness_closure_report(rep_bad)
    idx_obj = build_waveguide_package_pipeline_completion_index(rep_bad)
    assert idx_obj.package_pipeline_completion_index_status == "package_pipeline_completion_index_blocked"

    # 10. Distribution readiness closure status not verified blocks index.
    rep_unverified = dict(clean_closure_report)
    rep_unverified["distribution_readiness_closure_report_status"] = "distribution_readiness_closure_blocked"
    rep_unverified["distribution_readiness_closure_report_digest"] = hash_waveguide_distribution_readiness_closure_report(rep_unverified)
    idx_obj2 = build_waveguide_package_pipeline_completion_index(rep_unverified)
    assert idx_obj2.package_pipeline_completion_index_status == "package_pipeline_completion_index_blocked"

    # 11. Package release stage closed false blocks index.
    rep_not_closed = dict(clean_closure_report)
    rep_not_closed["package_release_stage_closed"] = False
    rep_not_closed["distribution_readiness_closure_report_digest"] = hash_waveguide_distribution_readiness_closure_report(rep_not_closed)
    idx_obj3 = build_waveguide_package_pipeline_completion_index(rep_not_closed)
    assert idx_obj3.package_pipeline_completion_index_status == "package_pipeline_completion_index_blocked"

    # 12. Ready-to-pivot flag false blocks index.
    rep_not_ready = dict(clean_closure_report)
    rep_not_ready["ready_to_pivot_to_new_direction"] = False
    rep_not_ready["distribution_readiness_closure_report_digest"] = hash_waveguide_distribution_readiness_closure_report(rep_not_ready)
    idx_obj4 = build_waveguide_package_pipeline_completion_index(rep_not_ready)
    assert idx_obj4.package_pipeline_completion_index_status == "package_pipeline_completion_index_blocked"


def test_completion_index_artifacts(tmp_path, clean_closure_report):
    # 16. Package pipeline completion index JSON artifact exists.
    index_obj = build_waveguide_package_pipeline_completion_index(clean_closure_report)
    out_json = str(tmp_path / "SOL_WAVEGUIDE_PACKAGE_PIPELINE_COMPLETION_INDEX.json")
    export_waveguide_package_pipeline_completion_index(index_obj, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["package_pipeline_completion_index_id"] == "SOL-WAVEGUIDE-PACKAGE-PIPELINE-COMPLETION-INDEX"
