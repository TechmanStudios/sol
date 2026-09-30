# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Focused unit tests for the SOL Waveguide Distribution Readiness Closure Report.
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
    build_waveguide_offline_consumer_verification_kit,
    hash_waveguide_offline_consumer_verification_kit
)
from sol_waveguide_distribution_readiness_closure_report import (
    build_waveguide_distribution_readiness_closure_case,
    validate_waveguide_distribution_readiness_closure_case,
    build_waveguide_distribution_readiness_closure_report,
    validate_waveguide_distribution_readiness_closure_report,
    hash_waveguide_distribution_readiness_closure_case,
    hash_waveguide_distribution_readiness_closure_report,
    export_waveguide_distribution_readiness_closure_report,
    WaveguideDistributionClosureCase,
    WaveguideDistributionReadinessClosureReport
)


@pytest.fixture
def clean_handoff_and_kit() -> tuple:
    index_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json")
    with open(index_file, "r", encoding="utf-8") as f:
        idx_dict = json.load(f)
    bundle = build_waveguide_release_handoff_bundle(idx_dict)
    kit = build_waveguide_offline_consumer_verification_kit(bundle)
    return asdict(bundle), asdict(kit)


def test_closure_case_lifecycle(clean_handoff_and_kit):
    bun, kit = clean_handoff_and_kit
    # 1. Distribution closure case can be built.
    case = build_waveguide_distribution_readiness_closure_case(
        requirement_id="archive_verification",
        kind="archive_verification",
        desc="Audit archive verification status",
        handoff_dict=bun,
        kit_dict=kit,
        index=0
    )
    assert isinstance(case, WaveguideDistributionClosureCase)
    assert case.distribution_closure_case_status == "distribution_closure_case_verified"

    # 2. Distribution closure case validates.
    ok, errs = validate_waveguide_distribution_readiness_closure_case(case)
    assert ok is True, f"Errors: {errs}"

    # 3. Closure case digest is deterministic.
    dig1 = hash_waveguide_distribution_readiness_closure_case(case)
    dig2 = hash_waveguide_distribution_readiness_closure_case(case)
    assert dig1 == dig2
    assert case.distribution_closure_case_digest == dig1

    # 4. distribution_closure_case_digest is excluded from its own digest input.
    c_dict = asdict(case)
    c_dict["distribution_closure_case_digest"] = "MUTATED"
    assert hash_waveguide_distribution_readiness_closure_case(c_dict) == dig1


def test_closure_report_lifecycle(clean_handoff_and_kit):
    bun, kit = clean_handoff_and_kit
    # 5. Distribution readiness closure report builds.
    report = build_waveguide_distribution_readiness_closure_report(bun, kit)
    assert isinstance(report, WaveguideDistributionReadinessClosureReport)
    assert report.distribution_readiness_closure_report_status == "distribution_readiness_closure_verified"

    # 6. Distribution readiness closure report validates.
    ok, errs = validate_waveguide_distribution_readiness_closure_report(report)
    assert ok is True, f"Errors: {errs}"

    # 7. Closure report digest is deterministic.
    dig1 = hash_waveguide_distribution_readiness_closure_report(report)
    dig2 = hash_waveguide_distribution_readiness_closure_report(report)
    assert dig1 == dig2
    assert report.distribution_readiness_closure_report_digest == dig1

    # 8. distribution_readiness_closure_report_digest is excluded from its own digest input.
    r_dict = asdict(report)
    r_dict["distribution_readiness_closure_report_digest"] = "MUTATED"
    assert hash_waveguide_distribution_readiness_closure_report(r_dict) == dig1

    # 19. Exit criteria verified true in clean report.
    assert report.exit_criteria_verified is True

    # 20. Package release stage closed true in clean report.
    assert report.package_release_stage_closed is True


def test_closure_report_failures_and_blocks(clean_handoff_and_kit):
    bun, kit = clean_handoff_and_kit

    # 9. Release handoff bundle validation failure blocks closure.
    bun_bad = dict(bun)
    bun_bad["release_handoff_bundle_id"] = "bad_id"
    bun_bad["release_handoff_bundle_digest"] = hash_waveguide_release_handoff_bundle(bun_bad)
    report = build_waveguide_distribution_readiness_closure_report(bun_bad, kit)
    assert report.distribution_readiness_closure_report_status == "distribution_readiness_closure_blocked"

    # 10. Offline verification kit validation failure blocks closure.
    kit_bad = dict(kit)
    kit_bad["offline_consumer_verification_kit_id"] = "bad_id"
    kit_bad["offline_consumer_verification_kit_digest"] = hash_waveguide_offline_consumer_verification_kit(kit_bad)
    report2 = build_waveguide_distribution_readiness_closure_report(bun, kit_bad)
    assert report2.distribution_readiness_closure_report_status == "distribution_readiness_closure_blocked"

    # 11. Archive not verified blocks closure.
    bun_no_arc = dict(bun)
    bun_no_arc["release_handoff_bundle_status"] = "release_handoff_bundle_blocked"
    bun_no_arc["release_handoff_bundle_digest"] = hash_waveguide_release_handoff_bundle(bun_no_arc)
    report3 = build_waveguide_distribution_readiness_closure_report(bun_no_arc, kit)
    assert report3.distribution_readiness_closure_report_status == "distribution_readiness_closure_blocked" or \
           report3.distribution_readiness_closure_report_status == "distribution_readiness_closure_invalid"


def test_closure_report_artifacts(tmp_path, clean_handoff_and_kit):
    bun, kit = clean_handoff_and_kit
    # 21. Distribution readiness closure JSON artifact exists.
    report = build_waveguide_distribution_readiness_closure_report(bun, kit)
    out_json = str(tmp_path / "SOL_WAVEGUIDE_DISTRIBUTION_READINESS_CLOSURE_REPORT.json")
    export_waveguide_distribution_readiness_closure_report(report, out_json)
    assert os.path.exists(out_json)
    with open(out_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["distribution_readiness_closure_report_id"] == "SOL-WAVEGUIDE-DISTRIBUTION-READINESS-CLOSURE-REPORT"
