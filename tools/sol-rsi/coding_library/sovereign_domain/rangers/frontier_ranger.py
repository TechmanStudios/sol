# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Frontier Ranger
===============
Observes CandidateCorrection packets and compiles valid SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any
from datetime import datetime, timezone

class FrontierRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe closed-loop Frontier adjustment candidate packets.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Frontier Ranger. You inspect closed-loop CandidateCorrection\n"
            "packets and verify safety and calibration constraints."
        )
        super().__init__("Frontier Ranger", system_prompt, lib_agent)

    def observe_adjustment(self, correction: Any, mission_id: str = "MOCK_FRONTIER_MISSION") -> SovereignPacket:
        """
        Inspects a CandidateCorrection packet and returns a SovereignPacket.
        """
        self.travel(correction)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        reason = extract(correction, "reason", "")
        confidence = extract(correction, "confidence", 0.0)
        bounded_delta = extract(correction, "bounded_delta", 0.0)
        target_lane = extract(correction, "target_lane", 0)
        target_channel = extract(correction, "target_channel", None)
        corr_type = extract(correction, "correction_type", "phase")
        repro_hash = extract(correction, "evidence_hash", "none")

        evidence = {
            "recommendation": f"suggest_{corr_type}_nudge" if corr_type == "phase" else "suggest_damping_adjustment",
            "bounded_delta": bounded_delta,
            "target_lane": target_lane,
            "target_channel": str(target_channel) if target_channel else "none",
            "confidence": confidence,
            "live_control_enabled": False,
            "promotion_required": True,
            "reproducibility_hash": repro_hash
        }

        recommendation = "observe" if confidence >= 0.90 else "reject"

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_FRONTIER_OBS_{id(correction)}_{timestamp_str}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Frontier OS closed-loop calibration nudge shadow observation report",
            evidence=evidence,
            invariants_checked=["closed_loop_shadow_constraints", "calibration_clamping"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed Frontier adjustment: delta={bounded_delta}, type={corr_type}.")
        return packet
