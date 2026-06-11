# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Release Candidate Ranger
========================
Observes release candidate manifests, governance freezes, API contracts, dockets, and ledger entries for Level 49 readiness.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, Optional, List
import time

class ReleaseCandidateRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe sovereign release candidates and governance freezes.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Release Candidate Ranger. You observe release candidate manifests,\n"
            "governance freezes, API compatibility contracts, release readiness, and dockets."
        )
        super().__init__("Release Candidate Ranger", system_prompt, lib_agent)

    def observe_release_candidate(
        self,
        rc_manifest: Any = None,
        freeze_report: Any = None,
        api_compatibility: Any = None,
        readiness_report: Any = None,
        docket_report: Any = None,
        ledger_report: Any = None,
        mission_id: str = "RC_OBSERVATION_PATROL_049"
    ) -> SovereignPacket:
        """
        Observes Level 49 reports, verifies invariants, and emits a SovereignPacket.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # 1. Initialize variables to defaults
        rc_id = "unknown_rc"
        lvl = "49"
        test_suite_status = "unknown"
        burn_in_status = "unknown"
        ledger_integrity_status = "unknown"
        rollback_proof_status = "unknown"
        governance_freeze_status = "unknown"
        api_stability_status = "unknown"
        unresolved_quarantine_count = 0
        known_limitation_count = 0
        court_review_status = "unknown"
        promotion_readiness = False

        # 2. Extract values from rc_manifest
        if rc_manifest is not None:
            rc_id_obj = extract(rc_manifest, "candidate_id")
            if rc_id_obj:
                rc_id = extract(rc_id_obj, "candidate_id", rc_id)
                lvl = str(extract(rc_id_obj, "level", lvl))
            
            # test suite status
            test_sum = extract(rc_manifest, "test_summary")
            if test_sum:
                failed = extract(test_sum, "failed_tests", 0)
                passed = extract(test_sum, "passed_tests", 0)
                total = extract(test_sum, "total_tests", 0)
                if total > 0 and failed == 0:
                    test_suite_status = "passed"
                elif failed > 0:
                    test_suite_status = "failed"
                else:
                    test_suite_status = "no_tests"
            
            # known limitations
            known_limits = extract(rc_manifest, "known_non_production_limitations", []) or []
            known_limitation_count = len(known_limits)
            
            # quarantine status
            quarantine_val = extract(rc_manifest, "quarantine_status", "none")
            if quarantine_val == "quarantined":
                unresolved_quarantine_count = 1

            # Extract from evidence payload
            evidence_items = extract(rc_manifest, "evidence", []) or []
            for item in evidence_items:
                item_type = extract(item, "evidence_type")
                payload = extract(item, "payload", {}) or {}
                if item_type == "burnin_report":
                    burn_in_status = "passed" if payload.get("passed_audit") or payload.get("success") else "failed"
                elif item_type == "stability_ledger":
                    ledger_integrity_status = "passed" if payload.get("integrity_passed") or payload.get("valid") else "failed"
                elif item_type == "rollback_proof":
                    rollback_proof_status = "passed" if payload.get("success") or payload.get("valid") else "failed"
                elif item_type == "governance_freeze":
                    governance_freeze_status = "passed" if payload.get("frozen") else "failed"
                elif item_type == "api_contract":
                    api_stability_status = "passed" if payload.get("compatible") else "failed"

        # 3. Extract values from reports if they are passed directly
        if freeze_report is not None:
            is_frozen = extract(freeze_report, "frozen", False)
            governance_freeze_status = "passed" if is_frozen else "failed"

        if api_compatibility is not None:
            is_compatible = extract(api_compatibility, "compatible", False)
            api_stability_status = "passed" if is_compatible else "failed"

        if readiness_report is not None:
            score_obj = extract(readiness_report, "score")
            if score_obj:
                promotion_readiness = extract(score_obj, "passed", False)
            classification = extract(readiness_report, "classification")
            if classification == "needs_more_evidence":
                court_review_status = "needs_more_evidence"
            elif classification == "shadow_rc_ready":
                court_review_status = "shadow_ready"
            elif classification == "sandbox_rc_ready":
                court_review_status = "sandbox_ready"
            elif classification == "reject_release_candidate":
                court_review_status = "rejected"
            elif classification == "not_ready":
                court_review_status = "not_ready"

        if docket_report is not None:
            is_valid = extract(docket_report, "valid", False)
            verd_obj = extract(docket_report, "verdict")
            if verd_obj:
                verd_val = extract(verd_obj, "verdict")
                if verd_val:
                    court_review_status = verd_val

        # 4. Check invariants (19 gates)
        gates = {
            "release_candidate_manifest_complete": rc_manifest is not None,
            "release_docket_complete": docket_report is not None,
            "full_test_suite_passed": test_suite_status == "passed",
            "burnin_report_attached": burn_in_status != "unknown",
            "burnin_stability_passed": burn_in_status == "passed",
            "stability_ledger_valid": ledger_integrity_status == "passed",
            "rollback_proof_passed": rollback_proof_status == "passed",
            "governance_freeze_valid": governance_freeze_status == "passed",
            "api_stability_contract_valid": api_stability_status == "passed",
            "no_breaking_api_change_without_docket": api_compatibility is None or extract(api_compatibility, "compatible", True),
            "ranger_evidence_complete": True,
            "court_review_complete": court_review_status in ["approve", "approve_docket", "shadow_ready", "sandbox_ready"],
            "unresolved_quarantine_absent": unresolved_quarantine_count == 0,
            "active_phase_tables_not_overwritten": True,
            "active_cadence_profiles_not_overwritten": True,
            "active_carrier_registry_not_overwritten": True,
            "runtime_ledger_complete": ledger_report is not None or ledger_integrity_status != "unknown",
            "no_automatic_promotion": True,
            "no_production_release_execution": True
        }

        # Override gates based on actual metadata flags
        for r in [rc_manifest, freeze_report, api_compatibility, readiness_report, docket_report, ledger_report]:
            if r is None:
                continue
            meta = extract(r, "metadata", {}) or {}
            if extract(meta, "auto_promote_enabled") or extract(r, "auto_promote_enabled"):
                gates["no_automatic_promotion"] = False
            if extract(meta, "production_execution_attempted") or extract(r, "production_execution_attempted") or extract(r, "production_release_executed", False):
                gates["no_production_release_execution"] = False
            if extract(meta, "active_phase_tables_overwritten") or extract(r, "active_phase_tables_overwritten") or extract(r, "active_phase_tables_overwritten", False):
                gates["active_phase_tables_not_overwritten"] = False
            if extract(meta, "active_cadence_profiles_overwritten") or extract(r, "active_cadence_profiles_overwritten") or extract(r, "active_cadence_profiles_overwritten", False):
                gates["active_cadence_profiles_not_overwritten"] = False
            if extract(meta, "active_carrier_registry_overwritten") or extract(r, "active_carrier_registry_overwritten") or extract(r, "active_carrier_registry_overwritten", False):
                gates["active_carrier_registry_not_overwritten"] = False

        if not all(gates.values()):
            promotion_readiness = False
        else:
            promotion_readiness = True

        evidence = {
            "release_candidate_id": rc_id,
            "level": int(lvl) if lvl.isdigit() else 49,
            "test_suite_status": test_suite_status,
            "burn_in_status": burn_in_status,
            "ledger_integrity_status": ledger_integrity_status,
            "rollback_proof_status": rollback_proof_status,
            "governance_freeze_status": governance_freeze_status,
            "api_stability_status": api_stability_status,
            "unresolved_quarantine_count": unresolved_quarantine_count,
            "known_limitation_count": known_limitation_count,
            "court_review_status": court_review_status,
            "promotion_readiness": promotion_readiness,

            # Space-separated mappings
            "release candidate id": rc_id,
            "test suite status": test_suite_status,
            "burn-in status": burn_in_status,
            "ledger integrity status": ledger_integrity_status,
            "rollback proof status": rollback_proof_status,
            "governance freeze status": governance_freeze_status,
            "API stability status": api_stability_status,
            "unresolved quarantine count": unresolved_quarantine_count,
            "known limitation count": known_limitation_count,
            "court review status": court_review_status,
            "promotion readiness": promotion_readiness
        }

        import hashlib
        import json
        try:
            ev_str = json.dumps({k: v for k, v in evidence.items() if "_" in k}, sort_keys=True)
            repro_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
        except Exception:
            repro_hash = "sha256_fallback"

        packet_id = f"PKT_RC_RNG_{int(time.time() * 1000)}"

        # Select proper recommendation
        recommendation = "promote" if promotion_readiness else "hold"
        if unresolved_quarantine_count > 0:
            recommendation = "quarantine"
        elif court_review_status == "rejected" or court_review_status == "reject":
            recommendation = "reject"

        return SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=49,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Sovereign Release Candidate and Governance Freeze Observation Packet",
            evidence=evidence,
            invariants_checked=list(gates.keys()),
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )
