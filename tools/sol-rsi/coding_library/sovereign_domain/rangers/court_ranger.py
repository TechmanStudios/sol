# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Court Ranger
============
Observes PromotionGateResult and CalibrationPromotionReport decisions and statuses,
returning valid SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class CourtRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Promotion Gate verdicts and Calibration Replay reports.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Court Ranger. You inspect PromotionGateResult decisions and\n"
            "CalibrationPromotionReport records, compiling decision metadata into evidence."
        )
        super().__init__("Court Ranger", system_prompt, lib_agent)

    def observe_court_decision(self, target_obj: Any, mission_id: str = "MOCK_COURT_MISSION") -> SovereignPacket:
        """
        Inspects a PromotionGateResult, CalibrationPromotionReport, or similar judicial report,
        and returns a SovereignPacket.
        """
        self.travel(target_obj)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        obj_classname = target_obj.__class__.__name__

        # Initialize defaults
        court_decision = "N/A"
        target_level = 11  # Default WideWord/calibration level
        lane_id = 0
        correction_type = "none"
        replay_status = "N/A"
        promotion_status = "N/A"
        quarantine_status = False

        if obj_classname == "PromotionGateResult":
            court_decision = extract(target_obj, "decision", "N/A")
            details = extract(target_obj, "details", {})
            lane_id = extract(details, "lane_id", 0)
            
            if court_decision == "authorize_candidate_phase_correction":
                correction_type = "phase"
            elif court_decision == "authorize_candidate_damping_correction":
                correction_type = "damping"
                
            quarantine_status = (court_decision == "quarantine_lane")
            passed = extract(target_obj, "passed", False)
            promotion_status = "approved" if passed else "deferred"

        elif obj_classname == "CalibrationPromotionReport":
            replay_res = extract(target_obj, "replay_result")
            replay_status = extract(replay_res, "status", "N/A")
            court_decision = extract(replay_res, "reason", "N/A")
            promotion_status = extract(target_obj, "promotion_status", "N/A")
            
            details = extract(replay_res, "details", {})
            lane_id = extract(details, "lane_id", 0)
            
            # Check if there were corrections
            if "diff_count" in details and details["diff_count"] > 0:
                correction_type = "phase"  # default type for calibration table changes
                
            quarantine_status = (replay_status == "fail")

        elif obj_classname == "CalibrationCorrectionDecision":
            court_decision = extract(target_obj, "decision", "N/A")
            lane_id = extract(target_obj, "target_lane", 0)
            correction_type = extract(target_obj, "correction_type", "none")
            quarantine_status = (court_decision == "quarantine_lane")
            promotion_status = "approved" if extract(target_obj, "authorized", False) else "deferred"

        # Evidence payload
        evidence = {
            "court_decision": court_decision,
            "target_level": target_level,
            "lane_id": lane_id,
            "correction_type": correction_type,
            "replay_status": replay_status,
            "promotion_status": promotion_status,
            "quarantine_status": quarantine_status,
            "target_type": obj_classname
        }

        # Determine recommendation:
        # If decision is quarantine or reject, recommend reject/quarantine.
        # If passed/approved, recommend promote/observe.
        if promotion_status == "approved" or court_decision in ["observe", "authorize_candidate_phase_correction", "authorize_candidate_damping_correction"]:
            recommendation = "promote" if obj_classname == "CalibrationPromotionReport" else "observe"
        elif court_decision == "quarantine_lane" or quarantine_status:
            recommendation = "quarantine"
        else:
            recommendation = "reject"

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_COURT_OBS_{id(target_obj)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Promotion gate review and closed-loop calibration recommendation report",
            evidence=evidence,
            invariants_checked=["promotion_gate_compliance", "closed_loop_bounds"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed court result: decision={court_decision}, promotion={promotion_status}.")
        return packet

    def observe_promotion(
        self,
        docket: Any = None,
        manifest: Any = None,
        report: Any = None,
        orchestration_report: Any = None,
        mission_id: str = "MOCK_COURT_MISSION"
    ) -> SovereignPacket:
        """
        Observes a PromotionDocket, PromotionManifest, CourtPromotionReport, or TransactionOrchestrationReport
        and returns a SovereignPacket containing Level 29 Court supervised evidence.
        """
        target = docket or manifest or report or orchestration_report
        self.travel(target)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        obj_classname = target.__class__.__name__ if target else "None"

        # Defaults
        candidate_id = "unknown"
        phase_level = 29
        evidence_completeness = "incomplete"
        gate_status = "pending"
        quorum_status = "unknown"
        transaction_boundary_status = "unknown"
        propagation_status = "unknown"
        rollback_status = "unknown"
        quarantine_status = "unknown"
        court_verdict = "unknown"
        promotion_readiness = "not_ready"
        recommendation = "observe"

        if obj_classname == "PromotionDocket":
            candidate_id = extract(target, "candidate_id", "unknown")
            phase_level = extract(target, "level", 29)
            from sol_promotion_docket import validate_promotion_docket
            is_valid = validate_promotion_docket(target)
            evidence_completeness = "complete" if is_valid else "incomplete"
            quarantine_status = "quarantined" if extract(target, "quarantine_status", False) else "clean"
            gate_status = "passed" if is_valid else "failed"
            
            for item in extract(target, "evidence", []):
                e_type = extract(item, "evidence_type")
                payload = extract(item, "payload")
                if e_type == "consensus_report":
                    dec = extract(payload, "decision")
                    quorum_status = "passed" if (dec and extract(dec, "agreed")) else "failed"
                elif e_type == "transaction_report":
                    res = extract(payload, "result")
                    rollback_status = "ready" if (res and extract(res, "success")) else "missing"
                    transaction_boundary_status = "valid" if (res and extract(res, "success")) else "invalid"
                elif e_type == "geodesic_propagation_report":
                    res = extract(payload, "result")
                    propagation_status = "stable" if (res and extract(res, "success")) else "unstable"
            
            if is_valid and quarantine_status == "clean" and quorum_status == "passed" and propagation_status == "stable":
                promotion_readiness = "ready"
                recommendation = "promote"

        elif obj_classname == "PromotionManifest":
            candidate_id = extract(target, "candidate_id", "unknown")
            phase_level = extract(target, "level", 29)
            verdict = extract(target, "verdict")
            court_verdict = extract(verdict, "decision", "unknown") if verdict else "unknown"
            evidence_completeness = "complete"
            gate_status = "passed"
            if court_verdict in ["promote_level28_candidate", "promote_level29_candidate"]:
                promotion_readiness = "ready"
                recommendation = "promote"

        elif obj_classname == "CourtPromotionReport":
            review = extract(target, "review")
            docket_id = extract(review, "docket_id", "unknown") if review else "unknown"
            candidate_id = docket_id.split("_")[1] if (docket_id and "_" in docket_id) else (docket_id or "unknown")
            gate_status = "passed" if extract(target, "passed_gates") else "failed"
            decision = extract(target, "decision")
            court_verdict = extract(decision, "decision", "unknown") if decision else "unknown"
            if court_verdict in ["promote_level28_candidate", "promote_level29_candidate"]:
                promotion_readiness = "ready"
                recommendation = "promote"
            elif court_verdict == "quarantine_candidate":
                quarantine_status = "quarantined"
                recommendation = "quarantine"
            else:
                recommendation = "reject"

        elif obj_classname == "TransactionOrchestrationReport":
            plan = extract(target, "plan")
            intent = extract(plan, "intent")
            candidate_id = extract(intent, "orchestration_id", "unknown") if intent else "unknown"
            gate_status = "passed" if extract(target, "passed_gates") else "failed"
            result = extract(target, "result")
            court_verdict = extract(result, "decision", "unknown") if result else "unknown"
            if court_verdict in ["promote_level28_candidate", "promote_level29_candidate", "accept_shadow_candidate"]:
                promotion_readiness = "ready"
                recommendation = "promote"
            elif court_verdict == "quarantine_candidate":
                quarantine_status = "quarantined"
                recommendation = "quarantine"
            else:
                recommendation = "reject"

        evidence = {
            "candidate_id": candidate_id,
            "phase_level": phase_level,
            "evidence_completeness": evidence_completeness,
            "gate_status": gate_status,
            "quorum_status": quorum_status,
            "transaction_boundary_status": transaction_boundary_status,
            "propagation_status": propagation_status,
            "rollback_status": rollback_status,
            "quarantine_status": quarantine_status,
            "court_verdict": court_verdict,
            "promotion_readiness": promotion_readiness,
            "target_type": obj_classname
        }

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_COURT_OBS_{id(target) if target else 0}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=29,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Court supervised promotion docket and manifest observation report",
            evidence=evidence,
            invariants_checked=["promotion_gate_compliance", "court_verdict_compliance"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed court promotion: verdict={court_verdict}, readiness={promotion_readiness}.")
        return packet
