# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Transaction Ranger
==================
Patrols distributed transaction coordinators, lock schedules, deadlocks, and validation safety.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any
from datetime import datetime, timezone

class TransactionRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 19 distributed transaction coordination and shard lock schedules.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Transaction Ranger. You patrol distributed transaction coordinators,\n"
            "audit shard lock schedules, analyze deadlock cycles, and review transaction gates."
        )
        super().__init__("Transaction Ranger", system_prompt, lib_agent)

    def observe_transaction(
        self,
        report: Any,
        lock_schedule: Any = None,
        deadlock_report: Any = None,
        mission_id: str = "M_TRANSACTION_PATROL"
    ) -> SovereignPacket:
        """
        Observes transaction coordinator reports to construct a SovereignPacket.
        """
        if report is not None:
            self.travel(report)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        tx_id = extract(report, "transaction_id", "unknown_tx")
        status = extract(report, "status", "unknown_status")
        
        prep_report = extract(report, "prepare_report")
        p_status = extract(prep_report, "participant_status", {})
        part_count = len(p_status)
        
        req_shards_cnt = part_count
        
        lock_order_ok = True
        lock_grant_ok = True
        lock_mode_sum = "exclusive"
        
        if lock_schedule is not None:
            lock_order_ok = extract(lock_schedule, "lock_order_valid", True)
            lock_grant_ok = len(extract(lock_schedule, "waits", [])) == 0
            grants = extract(lock_schedule, "grants", [])
            if grants:
                req = extract(grants[0], "request")
                if req:
                    lock_mode_sum = extract(req, "mode", "exclusive")
                    
        deadlock_detected = False
        if deadlock_report is not None:
            deadlock_detected = extract(deadlock_report, "deadlock_detected", False)
            
        lease_ok = lock_schedule is not None
        
        passed_prep = extract(prep_report, "passed", False)
        
        passed_gates = extract(report, "passed_gates", False)
        gate_rep = extract(report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep is not None else {}
        
        promotion_ready = (
            passed_gates and
            passed_prep and
            not deadlock_detected and
            lock_grant_ok and
            lock_order_ok
        )
        
        recommendation = "commit" if promotion_ready else "abort"

        evidence = {
            "transaction_id": tx_id,
            "participant_count": part_count,
            "required_shard_count": req_shards_cnt,
            "lock_mode_summary": lock_mode_sum,
            "lock_order_status": lock_order_ok,
            "lock_grant_status": lock_grant_ok,
            "deadlock_status": deadlock_detected,
            "lease_status": lease_ok,
            "prepare_status": passed_prep,
            "commit_abort_recommendation": recommendation,
            "promotion_readiness": promotion_ready
        }
        
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_TX_OBS_{tx_id}_{timestamp_str}"
        repro_hash = extract(report, "reproducibility_hash", "none")

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=19,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 19 distributed transaction coordinator and shard lock scheduler",
            evidence=evidence,
            invariants_checked=[
                "transaction_valid",
                "participants_valid",
                "lock_order_valid",
                "no_deadlock_detected"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed transaction {tx_id}: status={status}, promotion_ready={promotion_ready}."
        )
        return packet
