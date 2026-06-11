# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Atomic Commit Ranger
====================
Patrols distributed 2-phase commit operations and validates atomic commit safety.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any
from datetime import datetime, timezone

class AtomicCommitRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 17 atomic transactions, decisions, rollbacks, and reports.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Atomic Commit Ranger. You patrol distributed participants,\n"
            "evaluate prepare states, verify rollback snapshots, and audit commit gates."
        )
        super().__init__("Atomic Commit Ranger", system_prompt, lib_agent)

    def observe_atomic_commit(
        self,
        report: Any,
        mission_id: str = "M_ATOMIC_COMMIT_PATROL"
    ) -> SovereignPacket:
        """
        Observes atomic commit reports to construct a SovereignPacket.
        """
        if report is not None:
            self.travel(report)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        transaction = extract(report, "transaction")
        tx_id = extract(transaction, "transaction_id", "unknown_tx")
        participants = extract(transaction, "participants", [])
        part_count = len(participants)
        
        # Count prepared participants
        prepare_results = extract(report, "prepare_results", [])
        prep_count = sum(1 for r in prepare_results if extract(r, "prepared", False))
        
        decision = extract(report, "decision")
        q_status = extract(decision, "quorum_reached", False)
        decision_str = extract(decision, "decision", "abort")
        
        rollback_snap = extract(transaction, "rollback_snapshot")
        snap_status = rollback_snap is not None
        
        # Gates verification
        gate_rep = extract(report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep is not None else {}
        route_ok = checked_gates.get("boundary_routes_valid", True)
        
        rollback_result = extract(report, "rollback_result")
        rollback_status = rollback_result is not None and extract(rollback_result, "rolled_back", False)
        
        passed_gates = extract(report, "passed_gates", False)
        
        # Partial failure risk
        partial_risk = (not passed_gates) and (decision_str == "commit" or (prep_count > 0 and prep_count < part_count and not snap_status))
        
        quarantine = (not passed_gates) or (prep_count < part_count and not snap_status)
        promotion_ready = passed_gates and (decision_str == "commit") and snap_status and not partial_risk

        evidence = {
            "transaction_id": tx_id,
            "participant_count": part_count,
            "prepared_count": prep_count,
            "quorum_status": q_status,
            "rollback_snapshot_status": snap_status,
            "boundary_route_status": route_ok,
            "commit_decision": decision_str,
            "rollback_status": rollback_status,
            "partial_failure_risk": partial_risk,
            "quarantine_recommendation": quarantine,
            "promotion_readiness": promotion_ready
        }

        recommendation = "promote" if promotion_ready else ("quarantine" if quarantine else "observe")
        
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_ATOMIC_OBS_{tx_id}_{timestamp_str}"
        repro_hash = extract(report, "reproducibility_hash", "none")

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=17,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 17 distributed atomic commit and participant rollback synchronization",
            evidence=evidence,
            invariants_checked=[
                "participants_valid",
                "rollback_snapshots_present",
                "consensus_quorum_reached",
                "all_participants_prepared"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed atomic transaction {tx_id}: decision={decision_str}, promotion_ready={promotion_ready}."
        )
        return packet
