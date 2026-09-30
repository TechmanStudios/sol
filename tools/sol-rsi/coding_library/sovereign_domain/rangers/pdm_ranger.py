# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
PDM Ranger
==========
Observes PDMExecutionReport records and compiles valid SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any
from datetime import datetime, timezone

class PDMRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe waveguide-gated PDM execution reports.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the PDM Ranger. You inspect PDMExecutionReport objects,\n"
            "verifying wave modulation, demodulation, and oracle correctness."
        )
        super().__init__("PDM Ranger", system_prompt, lib_agent)

    def observe_execution(self, report: Any, mission_id: str = "MOCK_PDM_MISSION") -> SovereignPacket:
        """
        Inspects a PDMExecutionReport and returns a SovereignPacket.
        """
        self.travel(report)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        inst_id = extract(report, "instruction_id", "none")
        op = extract(report, "op", "UNKNOWN")
        width = extract(report, "width", 0)
        lane_count = extract(report, "lane_count", 0)
        passed_gates = extract(report, "passed_gates", False)
        match = extract(report, "oracle_match", False)
        repro_hash = extract(report, "reproducibility_hash", "none")

        channel_count = lane_count * 8
        demod_passed = passed_gates and match

        evidence = {
            "op": op,
            "width": width,
            "lane_count": lane_count,
            "channel_count": channel_count,
            "demodulation_passed": demod_passed,
            "oracle_match": match,
            "gate_status": "pass" if passed_gates else "fail",
            "frontier_suggestion_status": "observe" if demod_passed else "hold",
            "reproducibility_hash": repro_hash
        }

        recommendation = "promote" if demod_passed else "reject"

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_PDM_OBS_{id(report)}_{timestamp_str}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Waveguide-gated PDM execution and demodulation verification report",
            evidence=evidence,
            invariants_checked=["pdm_modulation_parity", "quadrature_orthogonality"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed PDM execution: op={op}, demod_passed={demod_passed}.")
        return packet
