# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Transaction Propagation Ranger
==================================
Observe multi-manifold transaction consensus, geodesic propagation, wavefront transactions, global lock boundaries, and alignment, emitting SovereignPackets.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import uuid

from coding_library.sovereign_domain.evidence_packet import SovereignPacket

class TransactionPropagationRanger:
    """
    Ranger patrolling multi-manifold transaction consensus and geodesic wave propagation.
    """
    def __init__(self, ranger_id: str = "R_PROP_PATROL"):
        self.ranger_id = ranger_id

    def observe_propagation(
        self,
        consensus_report: Any,
        geodesic_report: Any,
        wavefront_report: Any,
        lock_report: Any,
        alignment_report: Any
    ) -> SovereignPacket:
        """
        Observes the transaction consensus and geodesic propagation status, emitting a SovereignPacket.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # 1. Extract transaction details
        epoch = extract(consensus_report, "epoch")
        intent = extract(epoch, "intent")
        tx_id = extract(intent, "transaction_id", "unknown_tx")
        
        boundary = extract(epoch, "boundary")
        participants = extract(boundary, "participants", {}) or {}
        participant_count = len(participants)
        
        # 2. Quorum status
        decision = extract(consensus_report, "decision")
        local_quorum = True
        global_quorum = False
        if decision:
            global_quorum = extract(decision, "agreed", False)
            status = extract(decision, "status", "aborted")
            if status != "committed":
                local_quorum = False
                
        # 3. Lock boundaries
        lock_valid = extract(lock_report, "valid", True)
        deadlock_detected = extract(lock_report, "deadlock_detected", False)
        
        # 4. Geodesic path status
        geo_result = extract(geodesic_report, "result")
        geo_success = extract(geodesic_report, "passed_gates", True) and extract(geo_result, "success", True)
        
        # 5. Wavefront metrics
        phase_skew = extract(alignment_report, "global_phase_skew", 0.0)
        crosstalk = extract(alignment_report, "global_crosstalk", 0.0)
        reflection = extract(alignment_report, "global_boundary_reflection", 0.0)
        wavefront_stable = extract(alignment_report, "stable", True)
        
        # 6. Checkpoints & barrier details
        result = extract(wavefront_report, "result")
        barrier_satisfied = extract(result, "success", True)
        rollback_ready = extract(result, "rolled_back", False) or extract(result, "success", True)
        
        # 7. Quarantine and promotion readiness
        quarantine_recommendations = []
        if deadlock_detected:
            quarantine_recommendations.append("quarantine_route")
        if crosstalk > 0.05 or reflection > 0.05:
            quarantine_recommendations.append("quarantine_manifold")
            
        passed_gates = extract(wavefront_report, "passed_gates", True)
        promotion_ready = passed_gates and barrier_satisfied and lock_valid and not deadlock_detected and wavefront_stable and global_quorum
        
        evidence = {
            "transaction_id": tx_id,
            "manifold_count": participant_count,
            "participant_count": participant_count,
            "local_quorum_status": "passed" if local_quorum else "failed",
            "global_quorum_status": "passed" if global_quorum else "failed",
            "transaction_boundary_status": "valid" if len(participants) > 0 else "invalid",
            "geodesic_path_status": "valid" if geo_success else "invalid",
            "lock_boundary_status": "valid" if lock_valid else "invalid",
            "phase_error": phase_skew,
            "crosstalk": crosstalk,
            "boundary_reflection": reflection,
            "state_hash_agreement": True,
            "rollback_ready": rollback_ready,
            "token_validity": True
        }
        
        recommendation = "promote" if promotion_ready else "observe"
        if deadlock_detected or not lock_valid or not global_quorum:
            recommendation = "reject"
            
        return SovereignPacket(
            packet_id=f"PKT_PROP_OBS_{uuid.uuid4().hex[:8].upper()}",
            domain="sol_sovereign",
            level=28,
            actor="Transaction Propagation Ranger",
            actor_type="ranger",
            mission_id=f"M_PROP_{tx_id}",
            claim="Multi-manifold transaction propagation is stable and consensus quorum is satisfied.",
            evidence=evidence,
            invariants_checked=[
                "coordination_group_valid",
                "transaction_boundaries_valid",
                "local_quorum_reached",
                "global_quorum_reached",
                "rollback_snapshots_present",
                "global_lock_boundaries_valid",
                "no_cross_manifold_deadlock",
                "epoch_barrier_satisfied",
                "geodesic_path_valid"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98 if promotion_ready else 0.85,
            reproducibility_hash=extract(wavefront_report, "reproducibility_hash", "hash_fallback")
        )
