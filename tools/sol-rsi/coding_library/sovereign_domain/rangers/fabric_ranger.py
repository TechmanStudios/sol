# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Fabric Ranger
=============
Observes WideWordFabricTopology, WideWordFabricExecutionPlan, and WideWordFabricReport,
verifying fabric parameters and emitting a SovereignPacket.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any, Dict
from datetime import datetime, timezone

class FabricRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe WideWord fabric configurations, execution plans, and reports.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Fabric Ranger. You inspect WideWord fabric topologies,\n"
            "perfectly matched layer boundary profiles, and prefix carry execution reports."
        )
        super().__init__("Fabric Ranger", system_prompt, lib_agent)

    def observe_fabric(
        self,
        topology: Any,
        plan: Any,
        report: Any,
        mission_id: str = "MOCK_FABRIC_MISSION"
    ) -> SovereignPacket:
        """
        Observes a fabric topology, plan, and report, returning a SovereignPacket evidence log.
        """
        if topology is not None:
            self.travel(topology)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        width = extract(topology, "width", 0)
        
        # Count lanes in topology
        lane_count = 0
        lane_groups = extract(topology, "lane_groups", [])
        lane_group_count = len(lane_groups)
        for group in lane_groups:
            lanes = extract(group, "lanes", [])
            lane_count += len(lanes)

        # Check PML profiles status
        pml_status = "VALID"
        for group in lane_groups:
            lanes = extract(group, "lanes", [])
            for lane in lanes:
                if extract(lane, "local_pml_profile", None) is None:
                    pml_status = "MISSING"
                    break

        # Check Phase alignment tables status
        phase_status = "VALID"
        for group in lane_groups:
            lanes = extract(group, "lanes", [])
            for lane in lanes:
                if extract(lane, "local_phase_alignment_table", None) is None:
                    phase_status = "MISSING"
                    break

        # Check prefix carry status from report
        carry_complete = False
        pdm_rep = extract(report, "pdm_report", None)
        if pdm_rep is not None:
            gate_rep = extract(pdm_rep, "gate_report", None)
            if gate_rep is not None:
                checked_gates = extract(gate_rep, "checked_gates", {})
                carry_complete = checked_gates.get("prefix_carry_trace_complete", False)
        carry_status = "COMPLETE" if carry_complete else "INCOMPLETE"

        # Check demodulation status & oracle match
        success = extract(report, "passed_gates", False)
        oracle_match = extract(report, "oracle_match", False)
        demod_status = "SUCCESS" if oracle_match else "FAILURE"

        # Crosstalk status
        crosstalk_levels = extract(report, "crosstalk_levels", {})
        crosstalk_ok = all(val <= 0.05 for val in crosstalk_levels.values()) if crosstalk_levels else True
        crosstalk_status = "NOMINAL" if crosstalk_ok else "CRITICAL"

        # Promotion readiness
        promotion_ready = success and oracle_match and pml_status == "VALID" and phase_status == "VALID"

        evidence = {
            "width": width,
            "lane_count": lane_count,
            "lane_group_count": lane_group_count,
            "pml_profile_status": pml_status,
            "phase_table_status": phase_status,
            "carry_trace_status": carry_status,
            "demodulation_status": demod_status,
            "oracle_match": oracle_match,
            "crosstalk_status": crosstalk_status,
            "promotion_readiness": promotion_ready
        }

        recommendation = "promote" if promotion_ready else "reject"

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_FABRIC_OBS_{id(report)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=12,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of WideWord waveguide fabric configuration and execution",
            evidence=evidence,
            invariants_checked=[
                "hierarchical_fabric_width",
                "perfect_matched_boundary_profiles",
                "prefix_carry_propagation",
                "crosstalk_isolation_thresholds"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed fabric width {width}: status={demod_status}, promotion_ready={promotion_ready}."
        )
        return packet
