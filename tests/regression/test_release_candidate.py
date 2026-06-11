# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 49: Sovereign Runtime Release Candidate and Governance Freeze.
"""

import sys
from pathlib import Path
import pytest
import time
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List

# Setup path injection to guarantee local tools importing
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Import new modules
from sol_release_candidate_manifest import (
    open_release_candidate_manifest,
    attach_release_evidence,
    attach_test_summary,
    attach_gate_snapshot,
    validate_release_candidate_manifest,
    summarize_release_candidate_manifest,
    ReleaseCandidateId,
    ReleaseCandidateEvidenceItem,
    ReleaseCandidateTestSummary,
    ReleaseCandidateGateSnapshot,
    ReleaseCandidateVerdict,
    ReleaseCandidateManifest,
    ReleaseCandidateReport
)
from sol_governance_freeze import (
    GovernanceFreezePolicy,
    GovernanceInvariant,
    GovernanceFreezeSnapshot,
    GovernanceFreezeViolation,
    GovernanceFreezeReport,
    build_governance_freeze,
    capture_governance_freeze_snapshot,
    validate_governance_invariants,
    detect_governance_freeze_violation,
    summarize_governance_freeze
)
from sol_api_stability_contract import (
    APIStabilityContract,
    FrozenAPISymbol,
    APICompatibilityReport,
    APIBreakageReport,
    capture_public_api_surface,
    build_api_stability_contract,
    validate_api_compatibility,
    detect_breaking_api_changes
)
from sol_release_readiness_score import (
    ReleaseReadinessPolicy,
    ReleaseReadinessMetric,
    ReleaseReadinessScore,
    ReleaseReadinessReport,
    collect_release_readiness_metrics,
    evaluate_release_readiness,
    classify_release_readiness
)
from sol_release_packager import (
    ReleasePackagePolicy,
    ReleasePackageArtifact,
    ReleasePackageManifest,
    ReleasePackageReport,
    build_release_package_manifest,
    validate_release_package_manifest,
    generate_shadow_release_package
)
from sol_release_docket import (
    ReleaseDocket,
    ReleaseDocketEvidence,
    ReleaseDocketReview,
    ReleaseDocketVerdict,
    ReleaseDocketReport,
    open_release_docket,
    attach_release_docket_evidence,
    validate_release_docket,
    summarize_release_docket
)
from sol_runtime_ledger import (
    append_release_candidate_entry,
    append_governance_freeze_entry,
    append_api_contract_entry,
    append_release_docket_entry
)
from sol_sovereign_runtime import (
    SovereignRuntimeState,
    SovereignRuntimeCommand,
    submit_release_candidate_command,
    execute_shadow_release_candidate_command
)
from sol_court_supervised_promotion import (
    review_release_candidate_manifest,
    review_governance_freeze_report,
    review_api_stability_contract,
    review_release_readiness_report,
    review_release_docket
)
from coding_library.sovereign_domain.promotion_court import PromotionCourt
from coding_library.sovereign_domain.rangers.release_candidate_ranger import ReleaseCandidateRanger


# 1. opens and validates
def test_manifest_opens_and_validates():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    assert manifest.candidate_id.candidate_id == "RC-49.0.1"
    
    # Needs test summary, burnin, and rollback proof to validate
    test_sum = ReleaseCandidateTestSummary(total_tests=100, passed_tests=100, failed_tests=0, duration=10.0)
    attach_test_summary(manifest, test_sum)
    
    ev_burnin = ReleaseCandidateEvidenceItem(
        evidence_id="ev_burnin",
        evidence_type="burnin_report",
        payload={"passed_audit": True}
    )
    ev_rollback = ReleaseCandidateEvidenceItem(
        evidence_id="ev_rollback",
        evidence_type="rollback_proof",
        payload={"success": True}
    )
    attach_release_evidence(manifest, ev_burnin)
    attach_release_evidence(manifest, ev_rollback)
    
    assert validate_release_candidate_manifest(manifest) is True
    
    report = summarize_release_candidate_manifest(manifest)
    assert report.valid is True
    assert report.verdict.verdict == "approve"


# 2. rejects missing test summary
def test_manifest_rejects_missing_test_summary():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    ev_burnin = ReleaseCandidateEvidenceItem(
        evidence_id="ev_burnin",
        evidence_type="burnin_report",
        payload={"passed_audit": True}
    )
    ev_rollback = ReleaseCandidateEvidenceItem(
        evidence_id="ev_rollback",
        evidence_type="rollback_proof",
        payload={"success": True}
    )
    attach_release_evidence(manifest, ev_burnin)
    attach_release_evidence(manifest, ev_rollback)
    
    assert validate_release_candidate_manifest(manifest) is False


# 3. rejects missing burn-in evidence
def test_manifest_rejects_missing_burnin_evidence():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    test_sum = ReleaseCandidateTestSummary(total_tests=100, passed_tests=100, failed_tests=0, duration=10.0)
    attach_test_summary(manifest, test_sum)
    
    ev_rollback = ReleaseCandidateEvidenceItem(
        evidence_id="ev_rollback",
        evidence_type="rollback_proof",
        payload={"success": True}
    )
    attach_release_evidence(manifest, ev_rollback)
    
    assert validate_release_candidate_manifest(manifest) is False


# 4. rejects missing rollback proof
def test_manifest_rejects_missing_rollback_proof():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    test_sum = ReleaseCandidateTestSummary(total_tests=100, passed_tests=100, failed_tests=0, duration=10.0)
    attach_test_summary(manifest, test_sum)
    
    ev_burnin = ReleaseCandidateEvidenceItem(
        evidence_id="ev_burnin",
        evidence_type="burnin_report",
        payload={"passed_audit": True}
    )
    attach_release_evidence(manifest, ev_burnin)
    
    assert validate_release_candidate_manifest(manifest) is False


# 5. captures required invariants
def test_governance_freeze_captures_required_invariants():
    # Mock runtime and registries objects
    @dataclass
    class MockRuntime:
        allow_automatic_promotion: bool = False
        allow_production_execution: bool = False
        bypass_court: bool = False
        bypass_ranger: bool = False
        bypass_rollback: bool = False
        bypass_ledger: bool = False
        ignore_quarantine: bool = False

    @dataclass
    class MockRegistries:
        active_phase_tables_overwritten: bool = False
        active_cadence_profiles_overwritten: bool = False
        active_carrier_registry_overwritten: bool = False

    runtime = MockRuntime()
    registries = MockRegistries()
    
    snapshot = capture_governance_freeze_snapshot(runtime, registries)
    
    policy = GovernanceFreezePolicy()
    report = validate_governance_invariants(snapshot, policy)
    assert report.frozen is True
    assert len(report.violations) == 0


# 6. detects automatic promotion violation
def test_governance_freeze_detects_automatic_promotion_violation():
    @dataclass
    class MockRuntime:
        allow_automatic_promotion: bool = True  # Violation!
        allow_production_execution: bool = False
        bypass_court: bool = False
        bypass_ranger: bool = False
        bypass_rollback: bool = False
        bypass_ledger: bool = False
        ignore_quarantine: bool = False

    @dataclass
    class MockRegistries:
        active_phase_tables_overwritten: bool = False
        active_cadence_profiles_overwritten: bool = False
        active_carrier_registry_overwritten: bool = False

    runtime = MockRuntime()
    registries = MockRegistries()
    
    snapshot = capture_governance_freeze_snapshot(runtime, registries)
    policy = GovernanceFreezePolicy()
    report = validate_governance_invariants(snapshot, policy)
    assert report.frozen is False
    assert len(report.violations) == 1
    assert report.violations[0].invariant_name == "no_automatic_promotion"


# 7. detects production mutation permission
def test_governance_freeze_detects_production_mutation_permission():
    @dataclass
    class MockRuntime:
        allow_automatic_promotion: bool = False
        allow_production_execution: bool = True  # Violation!
        bypass_court: bool = False
        bypass_ranger: bool = False
        bypass_rollback: bool = False
        bypass_ledger: bool = False
        ignore_quarantine: bool = False

    @dataclass
    class MockRegistries:
        active_phase_tables_overwritten: bool = False
        active_cadence_profiles_overwritten: bool = False
        active_carrier_registry_overwritten: bool = False

    runtime = MockRuntime()
    registries = MockRegistries()
    
    snapshot = capture_governance_freeze_snapshot(runtime, registries)
    policy = GovernanceFreezePolicy()
    report = validate_governance_invariants(snapshot, policy)
    assert report.frozen is False
    assert len(report.violations) == 1
    assert report.violations[0].invariant_name == "no_production_mutation"


# 8. captures public API surface
def test_api_stability_contract_captures_public_api_surface():
    surface = capture_public_api_surface(["sol_sovereign_runtime", "promotion_court"])
    assert "sol_sovereign_runtime" in surface
    assert "promotion_court" in surface
    
    contract = build_api_stability_contract(surface)
    assert len(contract.frozen_symbols["sol_sovereign_runtime"]) > 0


# 9. detects removed public symbol
def test_api_compatibility_detects_removed_public_symbol():
    before_surface = {
        "sol_sovereign_runtime": [
            FrozenAPISymbol("submit_runtime_command", "function", "runtime, command", ["runtime", "command"]),
            FrozenAPISymbol("execute_shadow_runtime_command", "function", "runtime, command", ["runtime", "command"])
        ]
    }
    after_surface = {
        "sol_sovereign_runtime": [
            # submit_runtime_command is missing!
            FrozenAPISymbol("execute_shadow_runtime_command", "function", "runtime, command", ["runtime", "command"])
        ]
    }
    before = build_api_stability_contract(before_surface)
    after = build_api_stability_contract(after_surface)
    
    report = validate_api_compatibility(before, after)
    assert report.compatible is False
    assert "sol_sovereign_runtime.submit_runtime_command" in report.removed_symbols


# 10. detects changed required field
def test_api_compatibility_detects_changed_required_field():
    before_surface = {
        "sol_sovereign_runtime": [
            FrozenAPISymbol("submit_runtime_command", "function", "runtime, command", ["runtime", "command"])
        ]
    }
    after_surface = {
        "sol_sovereign_runtime": [
            # required_fields list has changed!
            FrozenAPISymbol("submit_runtime_command", "function", "runtime, command, extra", ["runtime", "command", "extra"])
        ]
    }
    before = build_api_stability_contract(before_surface)
    after = build_api_stability_contract(after_surface)
    
    report = validate_api_compatibility(before, after)
    assert report.compatible is False
    assert any("submit_runtime_command" in chg for chg in report.changed_signatures)


# 11. classifies complete candidate as shadow_rc_ready
def test_release_readiness_classifies_complete_candidate_as_shadow_rc_ready():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    manifest.test_summary = ReleaseCandidateTestSummary(total_tests=100, passed_tests=100, failed_tests=0, duration=5.0)
    
    # Attach all successful evidence
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("1", "burnin_report", {"passed_audit": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("2", "stability_ledger", {"integrity_passed": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("3", "rollback_proof", {"success": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("4", "api_contract", {"compatible": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("5", "governance_freeze", {"frozen": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("6", "active_table_protection", {"protected": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("7", "ranger_packet", {"complete": True}))
    
    # We do NOT attach court_verdict "complete" yet, so it classifies as shadow_rc_ready
    policy = ReleaseReadinessPolicy()
    report = evaluate_release_readiness(manifest, policy)
    assert report.score.passed is True
    assert report.classification == "shadow_rc_ready"


# 12. rejects unresolved quarantine
def test_release_readiness_rejects_unresolved_quarantine():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    manifest.quarantine_status = "quarantined"  # Unresolved quarantine!
    manifest.test_summary = ReleaseCandidateTestSummary(total_tests=100, passed_tests=100, failed_tests=0, duration=5.0)
    
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("1", "burnin_report", {"passed_audit": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("2", "stability_ledger", {"integrity_passed": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("3", "rollback_proof", {"success": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("4", "api_contract", {"compatible": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("5", "governance_freeze", {"frozen": True}))
    
    policy = ReleaseReadinessPolicy()
    report = evaluate_release_readiness(manifest, policy)
    assert report.score.passed is False
    # Since it's failed due to unresolved quarantine, classify_release_readiness returns "needs_more_evidence"
    assert report.classification == "needs_more_evidence"


# 13. rejects failed burn-in
def test_release_readiness_rejects_failed_burnin():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    manifest.test_summary = ReleaseCandidateTestSummary(total_tests=100, passed_tests=100, failed_tests=0, duration=5.0)
    
    # burnin_report failed!
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("1", "burnin_report", {"passed_audit": False}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("2", "stability_ledger", {"integrity_passed": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("3", "rollback_proof", {"success": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("4", "api_contract", {"compatible": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("5", "governance_freeze", {"frozen": True}))
    
    policy = ReleaseReadinessPolicy()
    report = evaluate_release_readiness(manifest, policy)
    assert report.score.passed is False
    assert report.classification == "reject_release_candidate"


# 14. validates complete evidence
def test_release_docket_validates_complete_evidence():
    docket = open_release_docket("RC-49.0.1")
    
    required_types = [
        "rc_manifest", "governance_freeze_report", "api_stability_contract", 
        "release_readiness_report", "package_report", "burn_in_report", 
        "test_summary", "ranger_packet"
    ]
    for r_type in required_types:
        attach_release_docket_evidence(docket, ReleaseDocketEvidence(r_type, r_type, {}))
        
    # Attach court verdict with approved status
    attach_release_docket_evidence(docket, ReleaseDocketEvidence("court_verdict", "court_verdict", {"verdict": "approve"}))
    
    assert validate_release_docket(docket) is True
    report = summarize_release_docket(docket)
    assert report.valid is True
    assert report.verdict.verdict == "approve"


# 15. rejects missing court verdict
def test_release_docket_rejects_missing_court_verdict():
    docket = open_release_docket("RC-49.0.1")
    required_types = [
        "rc_manifest", "governance_freeze_report", "api_stability_contract", 
        "release_readiness_report", "package_report", "burn_in_report", 
        "test_summary", "ranger_packet"
    ]
    for r_type in required_types:
        attach_release_docket_evidence(docket, ReleaseDocketEvidence(r_type, r_type, {}))
        
    assert validate_release_docket(docket) is False
    report = summarize_release_docket(docket)
    assert report.valid is False
    assert report.verdict.verdict == "hold"


# 16. validates metadata-only package
def test_release_package_manifest_validates_metadata_only_package():
    manifest = open_release_candidate_manifest("RC-49.0.1")
    policy = GovernanceFreezePolicy()
    snapshot = capture_governance_freeze_snapshot({}, {})
    freeze_report = validate_governance_invariants(snapshot, policy)
    api_surface = capture_public_api_surface(["sol_sovereign_runtime"])
    api_contract = build_api_stability_contract(api_surface)
    
    package = build_release_package_manifest(manifest, freeze_report, api_contract)
    assert validate_release_package_manifest(package) is True
    
    # Try injecting a production switch
    package.artifacts[0].payload["enable_production"] = True
    assert validate_release_package_manifest(package) is False


# 17. runtime ledger records release candidate event
def test_runtime_ledger_records_release_candidate_event():
    ledger = {"entries": []}
    manifest = open_release_candidate_manifest("RC-49.0.1")
    
    append_release_candidate_entry(ledger, manifest)
    assert len(ledger["entries"]) == 1
    assert ledger["entries"][0].entry_type == "release_candidate"
    assert ledger["entries"][0].payload["candidate_id"] == "RC-49.0.1"


# 18. runtime rejects production release command
def test_runtime_rejects_production_release_command():
    from sol_sovereign_runtime import SovereignRuntimePolicy, SovereignRuntimeId
    policy = SovereignRuntimePolicy(allowed_modes=["shadow", "sandbox"])
    r_id = SovereignRuntimeId(runtime_id="test_runtime_49")
    state = SovereignRuntimeState(
        runtime_id=r_id,
        policy=policy,
        mode="shadow",
        active_level=48
    )
    cmd = SovereignRuntimeCommand(
        command_id="CMD_PROD",
        operation="release_candidate_step",
        mode="production",  # Blocked!
        target_level="49",
        payload={}
    )
    with pytest.raises(ValueError, match="Production mode execution is blocked"):
        submit_release_candidate_command(state, cmd)
    assert state.mode == "hold"


# 19. court can accept shadow release candidate
def test_court_can_accept_shadow_release_candidate():
    court = PromotionCourt()
    manifest = open_release_candidate_manifest("RC-49.0.1")
    manifest.test_summary = ReleaseCandidateTestSummary(total_tests=10, passed_tests=10, failed_tests=0, duration=1.0)
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("1", "burnin_report", {"passed_audit": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("2", "rollback_proof", {"success": True}))
    
    decision = court.review_release_candidate_manifest(manifest)
    assert decision.decision == "accept_shadow_release_candidate"
    assert decision.passed is True


# 20. court can hold candidate for missing evidence
def test_court_can_hold_candidate_for_missing_evidence():
    court = PromotionCourt()
    # pass a dict/object with valid=False
    decision = court.review_release_candidate_manifest({"valid": False})
    assert decision.decision == "hold_release_candidate"
    assert decision.passed is False


# 21. court can reject candidate for failed governance freeze
def test_court_can_reject_candidate_for_failed_governance_freeze():
    court = PromotionCourt()
    report = GovernanceFreezeReport(
        report_id="rpt_fail",
        snapshot=GovernanceFreezeSnapshot("snap_fail", {}),
        violations=[GovernanceFreezeViolation("v", "e", "a", "desc")],
        frozen=False
    )
    decision = court.review_governance_freeze_report(report)
    assert decision.decision == "reject_release_candidate"
    assert decision.passed is False


# 22. ReleaseCandidateRanger emits JSON-serializable SovereignPacket
def test_release_candidate_ranger_emits_json_serializable_sovereign_packet():
    ranger = ReleaseCandidateRanger()
    manifest = open_release_candidate_manifest("RC-49.0.1")
    manifest.test_summary = ReleaseCandidateTestSummary(total_tests=10, passed_tests=10, failed_tests=0, duration=1.0)
    
    packet = ranger.observe_release_candidate(rc_manifest=manifest)
    assert packet.level == 49
    assert packet.domain == "sol_sovereign"
    assert packet.recommendation in ["promote", "hold"]
    
    # Try serializing to JSON to ensure it is JSON-serializable
    packet_dict = packet.to_dict()
    packet_json = json.dumps(packet_dict)
    assert isinstance(packet_json, str)


# 23. Promotion Court can review release manifest, governance freeze, API contract, release readiness, docket, and ranger reports
def test_promotion_court_can_review_release_manifest_governance_freeze_api_contract_readiness_docket_and_ranger_reports():
    court = PromotionCourt()
    
    # Manifest review
    manifest = open_release_candidate_manifest("RC-49.0.1")
    manifest.test_summary = ReleaseCandidateTestSummary(total_tests=10, passed_tests=10, failed_tests=0, duration=1.0)
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("1", "burnin_report", {"passed_audit": True}))
    attach_release_evidence(manifest, ReleaseCandidateEvidenceItem("2", "rollback_proof", {"success": True}))
    res_manifest = court.review_release_candidate_manifest(manifest)
    assert res_manifest.decision == "accept_shadow_release_candidate"
    
    # Governance freeze review
    freeze_report = GovernanceFreezeReport("frz_rpt", GovernanceFreezeSnapshot("snap", {}), [], True)
    res_freeze = court.review_governance_freeze_report(freeze_report)
    assert res_freeze.decision == "accept_shadow_release_candidate"
    
    # API contract review
    api_contract = APIBreakageReport(broken=False, breakages=[])
    res_api = court.review_api_stability_contract(api_contract)
    assert res_api.decision == "accept_shadow_release_candidate"
    
    # Release readiness review
    readiness_report = ReleaseReadinessReport(
        report_id="rdy_rpt",
        score=ReleaseReadinessScore(readiness_value=1.0, metrics={}, passed=True),
        classification="shadow_rc_ready"
    )
    res_readiness = court.review_release_readiness_report(readiness_report)
    assert res_readiness.decision == "accept_shadow_release_candidate"
    
    # Docket review
    docket = open_release_docket("RC-49.0.1")
    required_types = [
        "rc_manifest", "governance_freeze_report", "api_stability_contract", 
        "release_readiness_report", "package_report", "burn_in_report", 
        "test_summary", "ranger_packet"
    ]
    for r_type in required_types:
        attach_release_docket_evidence(docket, ReleaseDocketEvidence(r_type, r_type, {}))
    attach_release_docket_evidence(docket, ReleaseDocketEvidence("court_verdict", "court_verdict", {"verdict": "approve"}))
    res_docket = court.review_release_docket(docket)
    assert res_docket.decision == "promote_level49_candidate"
    
    # Ranger packet review
    ranger = ReleaseCandidateRanger()
    packet = ranger.observe_release_candidate(rc_manifest=manifest)
    res_ranger = court.review_release_candidate_ranger_packet(packet)
    assert res_ranger.decision in ["promote_level49_candidate", "hold_release_candidate"]
