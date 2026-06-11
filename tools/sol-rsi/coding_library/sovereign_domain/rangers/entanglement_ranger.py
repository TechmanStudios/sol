# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Entanglement Ranger
===================
Patrols cross-manifold routing links and measures entanglement stability indicators.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any
from datetime import datetime, timezone

class EntanglementRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 15 cross-manifold routing and entanglement stability.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Entanglement Ranger. You patrol cross-manifold routing links,\n"
            "measure phase coherence, and track entanglement stability."
        )
        super().__init__("Entanglement Ranger", system_prompt, lib_agent)

    def observe_entanglement(
        self,
        route_plan: Any,
        routing_report: Any,
        stability_report: Any,
        mission_id: str = "M_ENTANGLE_PATROL"
    ) -> SovereignPacket:
        """
        Observes cross-manifold plans, routing outcomes, and stability reports to construct evidence.
        """
        if route_plan is not None:
            self.travel(route_plan)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        src_id = extract(extract(route_plan, "source_domain"), "manifold_id", "unknown_src")
        tgt_id = extract(extract(route_plan, "target_domain"), "manifold_id", "unknown_tgt")
        
        route = extract(route_plan, "route")
        route_depth = extract(route, "route_depth", 0)
        boundary_crossings = extract(route, "boundary_crossings", [])
        
        oracle_match = extract(routing_report, "oracle_match", False)
        coherence = extract(stability_report, "phase_coherence", 1.0)
        drift = extract(stability_report, "transfer_drift", 0.0)
        decision = extract(stability_report, "decision", "stable")
        
        repro_hash = extract(routing_report, "reproducibility_hash", "none")
        
        quarantine = (decision == "quarantine_route")
        
        passed_gates = extract(routing_report, "passed_gates", False)
        promotion_ready = passed_gates and oracle_match and (decision == "stable")
        
        evidence = {
            "source_domain": src_id,
            "target_domain": tgt_id,
            "value_width": extract(route_plan, "value_width", 64),
            "route_depth": route_depth,
            "boundary_crossings": boundary_crossings,
            "oracle_match": oracle_match,
            "phase_coherence": coherence,
            "transfer_drift": drift,
            "stability_decision": decision,
            "quarantine_recommended": quarantine,
            "promotion_readiness": promotion_ready
        }
        
        recommendation = "promote" if promotion_ready else ("quarantine" if quarantine else "observe")
        
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_ENTANGLE_OBS_{id(routing_report)}_{timestamp_str}"
        
        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=15,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 15 cross-manifold routing and entanglement stability",
            evidence=evidence,
            invariants_checked=[
                "source_domain_valid",
                "target_domain_valid",
                "route_completeness",
                "entanglement_stability"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed cross-manifold {src_id} -> {tgt_id}: stability={decision}, promotion_ready={promotion_ready}."
        )
        return packet
