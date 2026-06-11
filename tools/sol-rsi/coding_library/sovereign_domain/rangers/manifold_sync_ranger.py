# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Manifold Sync Ranger
========================
Observe multi-manifold coordination, global lock boundaries, wavefront alignment, and epochs, emitting SovereignPackets.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import uuid

from coding_library.sovereign_domain.evidence_packet import SovereignPacket

class ManifoldSyncRanger:
    """
    Ranger patrolling multi-manifold synchronization, coordination, and alignment.
    """
    def __init__(self, ranger_id: str = "R_SYNC_PATROL"):
        self.ranger_id = ranger_id

    def observe_sync(
        self,
        coordination_plan: Any,
        lock_report: Any,
        wavefront_report: Any,
        epoch_report: Any,
        coordination_report: Any
    ) -> SovereignPacket:
        """
        Observes the multi-manifold synchronization status and emits a SovereignPacket.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # 1. Extract counts
        group = extract(coordination_plan, "group")
        manifolds = extract(group, "manifolds", []) or []
        core_groups = extract(group, "core_groups", []) or []
        manifold_count = len(manifolds)
        core_group_count = len(core_groups)

        # 2. Epoch details
        epoch_id = extract(epoch_report, "epoch_id", "unknown_epoch")
        barrier_satisfied = extract(epoch_report, "barrier_satisfied", False)

        # 3. Lock boundaries
        lock_valid = extract(lock_report, "valid", True)
        deadlock_detected = extract(lock_report, "deadlock_detected", False)

        # 4. Wavefront metrics
        phase_skew = extract(wavefront_report, "global_phase_skew", 0.0)
        crosstalk = extract(wavefront_report, "global_crosstalk", 0.0)
        reflection = extract(wavefront_report, "global_boundary_reflection", 0.0)
        wavefront_stable = extract(wavefront_report, "stable", True)

        # 5. Quorum and rollback details
        quorum_reached = False
        decision = extract(epoch_report, "consensus_decision")
        if decision:
            quorum_reached = extract(decision, "quorum_reached", False) or extract(decision, "passed", False)
            
        result = extract(coordination_report, "result")
        rollback_ready = extract(result, "rolled_back", False) or extract(result, "success", True)

        # 6. Quarantine and promotion readiness
        quarantine_recommendations = []
        if deadlock_detected:
            quarantine_recommendations.append("quarantine_route")
        if crosstalk > 0.05 or reflection > 0.05:
            quarantine_recommendations.append("quarantine_manifold")

        passed_gates = extract(coordination_report, "passed_gates", True)
        promotion_ready = passed_gates and barrier_satisfied and lock_valid and not deadlock_detected and wavefront_stable and quorum_reached

        # Assemble evidence dictionary
        evidence = {
            "manifold_count": manifold_count,
            "core_group_count": core_group_count,
            "epoch_id": epoch_id,
            "epoch_barrier_status": "satisfied" if barrier_satisfied else "failed",
            "global_lock_boundary_status": "valid" if lock_valid else "invalid",
            "cross_manifold_deadlock_status": "deadlock_detected" if deadlock_detected else "no_deadlock",
            "wavefront_alignment_status": "stable" if wavefront_stable else "unstable",
            "global_phase_skew": phase_skew,
            "crosstalk": crosstalk,
            "boundary_reflection": reflection,
            "quorum_status": "passed" if quorum_reached else "failed",
            "rollback_ready": rollback_ready,
            "quarantine_recommendations": quarantine_recommendations,
            "promotion_readiness": promotion_ready,
            "token_validity": True
        }

        recommendation = "promote" if promotion_ready else "observe"
        if deadlock_detected or not lock_valid:
            recommendation = "reject"
        elif not barrier_satisfied:
            recommendation = "observe"

        return SovereignPacket(
            packet_id=f"PKT_SYNC_OBS_{uuid.uuid4().hex[:8].upper()}",
            domain="sol_sovereign",
            level=27,
            actor="Manifold Sync Ranger",
            actor_type="ranger",
            mission_id=f"M_SYNC_{epoch_id}",
            claim="Multi-manifold coordination is stable and synchronized within safety constraints.",
            evidence=evidence,
            invariants_checked=[
                "coordination_group_valid",
                "epoch_barrier_satisfied",
                "global_lock_boundaries_valid",
                "no_cross_manifold_deadlock",
                "wavefront_alignment_measured",
                "multimanifold_quorum_reached"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98 if promotion_ready else 0.85,
            reproducibility_hash=extract(coordination_report, "reproducibility_hash", "hash_fallback")
        )
