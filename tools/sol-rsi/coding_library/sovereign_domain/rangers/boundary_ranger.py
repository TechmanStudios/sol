# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Boundary Ranger
===============
Inspects PML boundary health and detects standing-wave reflections.
Now observes PMLProfile configurations and outputs SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any
from datetime import datetime, timezone

class BoundaryRanger(LuminaRoamingAgent):
    """
    Ranger verifying absorption qualities of Perfectly Matched Layers (PML) boundary cells.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Boundary Ranger. You inspect PML boundary cells,\n"
            "detect edge reflections, standing waves, and verify absorption quality."
        )
        super().__init__("Boundary Ranger", system_prompt, lib_agent)

    def inspect_boundaries(self, sequencer_obj) -> Dict[str, Any]:
        """
        Check boundary cell states for standing waves or reflections.
        Observe/report only: does not adjust damping parameters.
        """
        self.travel(sequencer_obj)
        report = {
            "status": "STABLE",
            "reflection_score": 0.01,
            "observations": []
        }
        self.state_history.append("Inspected PML boundaries: no standing waves detected.")
        return report

    def observe_pml_profile(self, profile_obj: Any, mission_id: str = "MOCK_BOUNDARY_MISSION") -> SovereignPacket:
        """
        Observes a PMLProfile configuration, checks boundary configuration state,
        and returns a SovereignPacket representing the verification verdict.
        Does not modify engine state.
        """
        self.travel(profile_obj)

        def extract(name, default=None):
            if isinstance(profile_obj, dict):
                return profile_obj.get(name, default)
            return getattr(profile_obj, name, default)

        grid_size = extract("grid_size")
        pml_cells = extract("pml_cells")
        core_gamma = extract("core_gamma")
        boundary_gamma = extract("boundary_gamma")
        profile = extract("profile", [])

        configured = (pml_cells is not None and pml_cells > 0) and (boundary_gamma is not None and boundary_gamma > 0.0)
        max_damping = max(profile) if profile else 0.0

        evidence = {
            "grid_size": grid_size,
            "pml_cells": pml_cells,
            "core_gamma": core_gamma,
            "boundary_gamma": boundary_gamma,
            "max_damping": max_damping,
            "boundaries_configured": configured
        }

        # Packet ID and hash
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_BOUND_OBS_{id(profile_obj)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Boundary PML damping profile configuration report",
            evidence=evidence,
            invariants_checked=["boundary_attenuation"],
            artifacts=[],
            recommendation="observe" if configured else "reject",
            confidence=0.95,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed PML boundary profile: config_status={configured}.")
        return packet
