# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 50: Sovereign Production Gateways and System Finalization.
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
from sol_production_gateway import (
    ProductionGatewayPolicy,
    ProductionGatewayRequest,
    ProductionGatewayDecision,
    ProductionGatewayReport,
    build_production_gateway,
    validate_production_gateway_policy,
    evaluate_production_gateway_request,
    execute_shadow_production_gateway_check,
    summarize_production_gateway_report
)
from sol_final_system_manifest import (
    FinalSystemManifest,
    FinalSystemEvidenceItem,
    FinalSystemInvariantSnapshot,
    FinalSystemGateSummary,
    FinalSystemVerdict,
    FinalSystemReport,
    open_final_system_manifest,
    attach_final_system_evidence,
    attach_final_invariant_snapshot,
    attach_final_gate_summary,
    validate_final_system_manifest,
    summarize_final_system_manifest
)
from sol_final_gate_registry import (
    FinalGateDefinition,
    FinalGateRegistry,
    FinalGateEvaluation,
    FinalGateRegistryReport,
    build_final_gate_registry,
    register_final_gate,
    evaluate_final_gate_registry,
    summarize_final_gate_registry
)
from sol_production_readiness_guard import (
    ProductionReadinessGuardPolicy,
    ProductionReadinessSignal,
    ProductionReadinessDecision,
    ProductionReadinessReport,
    collect_production_readiness_signals,
    evaluate_production_readiness_guard,
    classify_production_readiness
)
from sol_system_lockdown import (
    SystemLockdownPolicy,
    SystemLockdownSnapshot,
    SystemLockdownViolation,
    SystemLockdownReport,
    capture_system_lockdown_snapshot,
    validate_system_lockdown,
    detect_system_lockdown_violation,
    summarize_system_lockdown
)
from sol_runtime_handoff_manifest import (
    RuntimeHandoffManifest,
    RuntimeHandoffEvidence,
    RuntimeHandoffChecklist,
    RuntimeHandoffReport,
    open_runtime_handoff_manifest,
    attach_runtime_handoff_evidence,
    validate_runtime_handoff_checklist,
    summarize_runtime_handoff
)
from sol_finalization_docket import (
    FinalizationDocket,
    FinalizationDocketEvidence,
    FinalizationDocketReview,
    FinalizationDocketVerdict,
    FinalizationDocketReport,
    open_finalization_docket,
    attach_finalization_evidence,
    validate_finalization_docket,
    summarize_finalization_docket
)
from sol_runtime_ledger import (
    append_final_system_manifest_entry,
    append_final_gate_registry_entry,
    append_production_gateway_entry,
    append_system_lockdown_entry,
    append_finalization_docket_entry
)
from sol_sovereign_runtime import (
    SovereignRuntimeState,
    SovereignRuntimeCommand,
    SovereignRuntimeId,
    SovereignRuntimePolicy,
    submit_system_finalization_command,
    execute_shadow_system_finalization_command,
    submit_production_gateway_check_command,
    execute_shadow_production_gateway_check_command
)
from sol_court_supervised_promotion import (
    review_production_gateway_report,
    review_final_system_manifest,
    review_final_gate_registry_report,
    review_production_readiness_guard_report,
    review_system_lockdown_report,
    review_runtime_handoff_manifest,
    review_finalization_docket
)
from coding_library.sovereign_domain.promotion_court import PromotionCourt
from coding_library.sovereign_domain.rangers.finalization_ranger import FinalizationRanger


# 1. production gateway builds default-deny
def test_production_gateway_builds_default_deny():
    policy = ProductionGatewayPolicy()
    assert validate_production_gateway_policy(policy) is True
    report = build_production_gateway(policy)
    assert report.decision.decision == "deny"


# 2. production gateway denies production mutation request
def test_production_gateway_denies_production_mutation_request():
    policy = ProductionGatewayPolicy()
    req = ProductionGatewayRequest(
        request_id="REQ_PROD",
        target_operation="mutate_state",
        payload={"production_execution": True},
        mode="production"
    )
    decision = evaluate_production_gateway_request(req, policy)
    assert decision.decision == "deny"


# 3. production gateway can approve shadow-only check
def test_production_gateway_can_approve_shadow_only_check():
    policy = ProductionGatewayPolicy()
    req = ProductionGatewayRequest(
        request_id="REQ_SHADOW",
        target_operation="read_only_check",
        payload={},
        mode="shadow"
    )
    decision = evaluate_production_gateway_request(req, policy)
    assert decision.decision == "shadow_only_approved"


# 4. final system manifest opens and validates
def test_final_system_manifest_opens_and_validates():
    manifest = open_final_system_manifest("SYS-50.0.1")
    assert manifest.system_id == "SYS-50.0.1"
    
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    
    assert validate_final_system_manifest(manifest) is True


# 5. final system manifest rejects missing release candidate evidence
def test_final_system_manifest_rejects_missing_rc_evidence():
    manifest = open_final_system_manifest("SYS-50.0.1")
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    assert validate_final_system_manifest(manifest) is False


# 6. final system manifest rejects missing rollback proof
def test_final_system_manifest_rejects_missing_rollback_proof():
    manifest = open_final_system_manifest("SYS-50.0.1")
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    assert validate_final_system_manifest(manifest) is False


# 7. final gate registry aggregates required gates
def test_final_gate_registry_aggregates_required_gates():
    registry = build_final_gate_registry([50])
    assert "runtime_governance" in registry.gates
    assert "production_gateway" in registry.gates
    assert "system_lockdown" in registry.gates or "governance_freeze" in registry.gates


# 8. finalized gate registry is immutable
def test_finalized_gate_registry_is_immutable():
    registry = build_final_gate_registry([50])
    evaluate_final_gate_registry(registry, {"all_passed": True})
    assert registry.finalized is True
    with pytest.raises(ValueError, match="Gate registry is immutable once finalized"):
        register_final_gate(registry, FinalGateDefinition("extra", 50, "test"))


# 9. production readiness guard classifies complete candidate as shadow_finalized
def test_production_readiness_guard_classifies_shadow_finalized():
    manifest = open_final_system_manifest("SYS-50.0.1")
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("3", "ranger_packet", {"complete": True}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("4", "runtime_ledger", {"valid": True}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("5", "burnin_report", {"passed_audit": True}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("6", "api_contract", {"compatible": True}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("7", "governance_freeze", {"frozen": True}))
    manifest.court_verdicts.append({"complete": True})
    
    signals = collect_production_readiness_signals(manifest)
    policy = ProductionReadinessGuardPolicy(block_production=False)
    report = evaluate_production_readiness_guard(signals, policy)
    assert report.decision.decision == "shadow_finalized"


# 10. production readiness guard blocks unresolved quarantine
def test_production_readiness_guard_blocks_unresolved_quarantine():
    manifest = open_final_system_manifest("SYS-50.0.1")
    manifest.quarantine_status = "quarantined"  # quarantined!
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    
    signals = collect_production_readiness_signals(manifest)
    policy = ProductionReadinessGuardPolicy()
    report = evaluate_production_readiness_guard(signals, policy)
    assert report.decision.decision in ["production_blocked", "needs_more_evidence"]


# 11. production readiness guard blocks production mutation request
def test_production_readiness_guard_blocks_production_mutation():
    manifest = open_final_system_manifest("SYS-50.0.1")
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    # policy permits production mutation?
    manifest.final_gateway_policy = ProductionGatewayPolicy(allow_production_mutation=True)
    
    signals = collect_production_readiness_signals(manifest)
    policy = ProductionReadinessGuardPolicy(block_production=True)
    report = evaluate_production_readiness_guard(signals, policy)
    assert report.decision.decision == "production_blocked"


# 12. system lockdown captures required registries
def test_system_lockdown_captures_required_registries():
    @dataclass
    class MockRuntime:
        allow_automatic_promotion: bool = False
        allow_production_execution: bool = False
        allow_default_mutation: bool = False
        live_gateway_enabled: bool = False
        quarantine_corrupted: bool = False

    @dataclass
    class MockRegistries:
        active_phase_tables_overwritten: bool = False
        active_cadence_profiles_overwritten: bool = False
        active_carrier_registry_overwritten: bool = False
        ranger_registry_corrupted: bool = False
        court_registry_corrupted: bool = False
        rollback_registry_corrupted: bool = False
        ledger_registry_corrupted: bool = False

    snapshot = capture_system_lockdown_snapshot(MockRuntime(), MockRegistries())
    assert snapshot.settings["auto_promote_enabled"] is False
    assert snapshot.settings["active_phase_tables_protected"] is True


# 13. system lockdown detects automatic promotion violation
def test_system_lockdown_detects_automatic_promotion_violation():
    @dataclass
    class MockRuntime:
        allow_automatic_promotion: bool = True  # Violation!
        allow_production_execution: bool = False
        allow_default_mutation: bool = False
        live_gateway_enabled: bool = False
        quarantine_corrupted: bool = False

    @dataclass
    class MockRegistries:
        active_phase_tables_overwritten: bool = False
        active_cadence_profiles_overwritten: bool = False
        active_carrier_registry_overwritten: bool = False
        ranger_registry_corrupted: bool = False
        court_registry_corrupted: bool = False
        rollback_registry_corrupted: bool = False
        ledger_registry_corrupted: bool = False

    snapshot = capture_system_lockdown_snapshot(MockRuntime(), MockRegistries())
    policy = SystemLockdownPolicy()
    report = validate_system_lockdown(snapshot, policy)
    assert report.locked is False
    assert report.violations[0].invariant_name == "auto_promote_enabled"


# 14. system lockdown detects production execution violation
def test_system_lockdown_detects_production_execution_violation():
    @dataclass
    class MockRuntime:
        allow_automatic_promotion: bool = False
        allow_production_execution: bool = True  # Violation!
        allow_default_mutation: bool = False
        live_gateway_enabled: bool = False
        quarantine_corrupted: bool = False

    @dataclass
    class MockRegistries:
        active_phase_tables_overwritten: bool = False
        active_cadence_profiles_overwritten: bool = False
        active_carrier_registry_overwritten: bool = False
        ranger_registry_corrupted: bool = False
        court_registry_corrupted: bool = False
        rollback_registry_corrupted: bool = False
        ledger_registry_corrupted: bool = False

    snapshot = capture_system_lockdown_snapshot(MockRuntime(), MockRegistries())
    policy = SystemLockdownPolicy()
    report = validate_system_lockdown(snapshot, policy)
    assert report.locked is False
    assert report.violations[0].invariant_name == "production_execution_enabled"


# 15. runtime handoff manifest validates checklist
def test_runtime_handoff_manifest_validates_checklist():
    manifest = open_runtime_handoff_manifest("SYS-50")
    assert validate_runtime_handoff_checklist(manifest) is True
    
    manifest.production_status = "allow_prod"  # Violation!
    assert validate_runtime_handoff_checklist(manifest) is False


# 16. finalization docket rejects missing court verdict
def test_finalization_docket_rejects_missing_court_verdict():
    docket = open_finalization_docket("SYS-50")
    required = [
        "final_system_manifest", "final_gate_registry_report", "production_readiness_guard_report",
        "system_lockdown_report", "runtime_handoff_manifest", "release_candidate_manifest",
        "release_docket", "runtime_ledger", "ranger_packet"
    ]
    for r in required:
        attach_finalization_evidence(docket, FinalizationDocketEvidence(r, r, {}))
        
    assert validate_finalization_docket(docket) is False


# 17. runtime rejects production finalization command
def test_runtime_rejects_production_finalization_command():
    policy = SovereignRuntimePolicy(allowed_modes=["shadow", "sandbox"])
    r_id = SovereignRuntimeId("run_id")
    runtime = SovereignRuntimeState(runtime_id=r_id, policy=policy, mode="shadow")
    
    cmd = SovereignRuntimeCommand(
        command_id="cmd_id",
        operation="finalize_system",
        target_level=50,
        mode="production"  # Violation!
    )
    with pytest.raises(ValueError, match="Production mode execution is blocked"):
        submit_system_finalization_command(runtime, cmd)


# 18. runtime records gateway denial in ledger
def test_runtime_records_gateway_denial_in_ledger():
    ledger = {"entries": []}
    report = ProductionGatewayReport(
        report_id="rpt_id",
        request=ProductionGatewayRequest("req_id", "mutate", {}, "production"),
        policy=ProductionGatewayPolicy(),
        decision=ProductionGatewayDecision("deny", "Production mutation request blocked.")
    )
    append_production_gateway_entry(ledger, report)
    assert len(ledger["entries"]) == 1
    assert ledger["entries"][0].entry_type == "production_gateway"
    assert ledger["entries"][0].payload["decision"] == "deny"


# 19. court can deny production gateway
def test_court_can_deny_production_gateway():
    court = PromotionCourt()
    report = ProductionGatewayReport(
        report_id="rpt_id",
        request=ProductionGatewayRequest("req_id", "mutate", {}, "production"),
        policy=ProductionGatewayPolicy(),
        decision=ProductionGatewayDecision("deny", "Production mutation request blocked.")
    )
    gate_res = court.review_production_gateway_report(report)
    assert gate_res.decision == "deny_production_gateway"
    assert gate_res.passed is False


# 20. court can accept shadow finalization
def test_court_can_accept_shadow_finalization():
    court = PromotionCourt()
    manifest = open_final_system_manifest("SYS-50")
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    
    gate_res = court.review_final_system_manifest(manifest)
    assert gate_res.decision == "accept_shadow_finalization"
    assert gate_res.passed is True


# 21. court can hold finalization for missing evidence
def test_court_can_hold_finalization_for_missing_evidence():
    court = PromotionCourt()
    # Invalid manifest
    gate_res = court.review_final_system_manifest({"valid": False})
    assert gate_res.decision == "hold_finalization"
    assert gate_res.passed is False


# 22. FinalizationRanger emits JSON-serializable SovereignPacket
def test_finalization_ranger_emits_json_packet():
    ranger = FinalizationRanger()
    manifest = open_final_system_manifest("SYS-50")
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    
    packet = ranger.observe_finalization(final_manifest=manifest)
    assert packet.level == 50
    assert packet.domain == "sol_sovereign"
    assert packet.recommendation in ["promote", "hold"]
    
    packet_json = json.dumps(packet.to_dict())
    assert isinstance(packet_json, str)


# 23. Promotion Court can review all finalization elements
def test_promotion_court_can_review_all_elements():
    court = PromotionCourt()
    
    # 1. Gateway
    gate_rpt = ProductionGatewayReport(
        report_id="rpt_id",
        request=ProductionGatewayRequest("req_id", "op", {}, "shadow"),
        policy=ProductionGatewayPolicy(),
        decision=ProductionGatewayDecision("shadow_only_approved", "Shadow approved")
    )
    assert court.review_production_gateway_report(gate_rpt).passed is True
    
    # 2. Final Manifest
    manifest = open_final_system_manifest("SYS-50")
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("1", "release_candidate_manifest", {}))
    attach_final_system_evidence(manifest, FinalSystemEvidenceItem("2", "rollback_proof", {"success": True}))
    assert court.review_final_system_manifest(manifest).passed is True
    
    # 3. Final Gate Registry
    gate_reg_rpt = FinalGateRegistryReport("reg_rpt", [], True)
    assert court.review_final_gate_registry_report(gate_reg_rpt).passed is True
    
    # 4. Readiness Guard
    readiness_rpt = ProductionReadinessReport("rdy_rpt", ProductionReadinessDecision("shadow_finalized", "Justification"))
    assert court.review_production_readiness_guard_report(readiness_rpt).passed is True
    
    # 5. Lockdown
    lock_rpt = SystemLockdownReport("lock_rpt", SystemLockdownSnapshot("snap", {}), [], True)
    assert court.review_system_lockdown_report(lock_rpt).passed is True
    
    # 6. Handoff
    handoff = open_runtime_handoff_manifest("SYS-50")
    assert court.review_runtime_handoff_manifest(handoff).passed is True
    
    # 7. Finalization Docket
    docket = open_finalization_docket("SYS-50")
    required = [
        "final_system_manifest", "final_gate_registry_report", "production_readiness_guard_report",
        "system_lockdown_report", "runtime_handoff_manifest", "release_candidate_manifest",
        "release_docket", "runtime_ledger", "ranger_packet"
    ]
    for r in required:
        attach_finalization_evidence(docket, FinalizationDocketEvidence(r, r, {}))
    attach_finalization_evidence(docket, FinalizationDocketEvidence("court_verdict", "court_verdict", {"verdict": "approve"}))
    assert court.review_finalization_docket(docket).passed is True
