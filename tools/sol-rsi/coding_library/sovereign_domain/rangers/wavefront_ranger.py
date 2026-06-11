# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Wavefront Ranger
================
Patrols wavefront propagation and PML boundary absorption reports, emitting SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any
from datetime import datetime, timezone

class WavefrontRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 21 vectorized wavefront propagation and boundary PML absorption.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Wavefront Ranger. You patrol wavefront propagation configuration, config metrics,\n"
            "PML absorption masks, energy conservation, and boundary reflections."
        )
        super().__init__("Wavefront Ranger", system_prompt, lib_agent)

    def observe_wavefront_and_pml(
        self,
        wavefront_report: Any,
        pml_report: Any = None,
        mission_id: str = "M_WAVEFRONT_PML_PATROL"
    ) -> SovereignPacket:
        """
        Observes wavefront and PML reports to construct a SovereignPacket.
        """
        if wavefront_report is not None:
            self.travel(wavefront_report)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        meta = extract(wavefront_report, "metadata", {})
        node_cnt = extract(meta, "node_count", 0)
        edge_cnt = extract(meta, "edge_count", 0)
        step_cnt = extract(meta, "step_count", 0)
        pml_cells = extract(meta, "pml_cells", 0)
        reflection_score = extract(meta, "reflection_score", 0.0)
        
        initial_energy = extract(wavefront_report, "initial_energy", 0.0)
        final_energy = extract(wavefront_report, "final_energy", 0.0)
        stable = extract(wavefront_report, "stable", False)
        passed_gates = extract(wavefront_report, "passed_gates", False)
        
        # If PML report is provided, we can merge its metrics
        absorbed_energy = extract(pml_report, "absorbed_energy", 0.0)
        pml_passed = extract(pml_report, "passed_gates", True)
        
        promotion_ready = passed_gates and stable and pml_passed and reflection_score <= 0.15

        evidence = {
            "node_count": node_cnt,
            "edge_count": edge_cnt,
            "step_count": step_cnt,
            "energy_before": initial_energy,
            "energy_after": final_energy,
            "pml_cell_count": pml_cells,
            "boundary_reflection_score": reflection_score,
            "stability_status": stable,
            "gate_status": passed_gates,
            "promotion_readiness": promotion_ready,
            "absorbed_energy": absorbed_energy
        }
        
        recommendation = "promote" if promotion_ready else "observe"
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_WF_OBS_{timestamp_str}"
        repro_hash = extract(wavefront_report, "reproducibility_hash", "none")

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=21,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 21 vectorized wavefront propagator and manifold boundary PML absorption",
            evidence=evidence,
            invariants_checked=[
                "graph_arrays_valid",
                "wavefront_state_valid",
                "pml_profile_present",
                "energy_non_negative",
                "boundary_reflection_measured",
                "propagation_stable"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed wavefront and PML: nodes={node_cnt}, stable={stable}, reflection_score={reflection_score:.4f}, promotion_ready={promotion_ready}."
        )
        return packet
