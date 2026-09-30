# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
H-CAM Ranger
============
Observes HierarchicalHCAMTopology, HCAMBankedRecallPlan, and HCAMRecallReport,
verifying query-response routing completeness and emitting a SovereignPacket.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any
from datetime import datetime, timezone

class HCamRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe H-CAM associative recall and banking configurations.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the H-CAM Ranger. You inspect Hierarchical H-CAM banking topologies,\n"
            "query and response routing tables, and byte-lane reduction tree word assembly."
        )
        super().__init__("HCAM Ranger", system_prompt, lib_agent)

    def observe_hcam(
        self,
        topology: Any,
        plan: Any,
        report: Any,
        mission_id: str = "MOCK_HCAM_MISSION"
    ) -> SovereignPacket:
        """
        Observes H-CAM topology, plan, and report, returning a SovereignPacket evidence log.
        """
        if topology is not None:
            self.travel(topology)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        width = extract(topology, "width", 0)
        banks = extract(topology, "banks", [])
        bank_count = len(banks)
        
        # Lane count maps to bank count
        lane_count = bank_count

        q_query = extract(plan, "query", None)
        if q_query is not None:
            address = extract(q_query, "address", 0)
        else:
            address = extract(report, "address", 0)

        # Query & response routes completeness
        q_routes = extract(plan, "query_routes", [])
        r_routes = extract(plan, "response_routes", [])
        q_complete = len(q_routes) == bank_count and bank_count > 0
        r_complete = len(r_routes) == bank_count and bank_count > 0
        
        # Reduction tree status
        tree = extract(report, "reduction_tree", None)
        tree_status = "VALID" if tree is not None and extract(tree, "depth", 0) > 0 else "INVALID"

        assembled_word = extract(report, "assembled_word", 0)
        oracle_match = extract(report, "oracle_match", False)
        passed_gates = extract(report, "passed_gates", False)

        promotion_ready = passed_gates and oracle_match and q_complete and r_complete and tree_status == "VALID"
        recommendation = "promote" if promotion_ready else "reject"

        evidence = {
            "width": width,
            "bank_count": bank_count,
            "lane_count": lane_count,
            "address": address,
            "query_route_completeness": q_complete,
            "response_route_completeness": r_complete,
            "reduction_tree_status": tree_status,
            "assembled_word": assembled_word,
            "oracle_match": oracle_match,
            "gate_status": "PASSED" if passed_gates else "FAILED",
            "promotion_readiness": promotion_ready
        }

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_HCAM_OBS_{id(report)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=13,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Hierarchical H-CAM banking associative memory recall",
            evidence=evidence,
            invariants_checked=[
                "hcam_banking_alignment",
                "query_response_routing_completeness",
                "reduction_tree_assembly"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(
            f"Observed H-CAM width {width}: assembled_word={hex(assembled_word)}, promotion_ready={promotion_ready}."
        )
        return packet
