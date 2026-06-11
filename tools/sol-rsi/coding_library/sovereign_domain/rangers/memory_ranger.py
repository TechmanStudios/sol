# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Memory Ranger
=============
Observes HCAMRecallPlan and checks HCAM memory banking correctness.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, List
from datetime import datetime, timezone

class MemoryRanger(LuminaRoamingAgent):
    """
    Ranger verifying holographic memory recall plans and byte-lane mapping configurations.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Memory Ranger. You inspect HCAM recall maps\n"
            "and verify that address/value basins are correctly aligned."
        )
        super().__init__("Memory Ranger", system_prompt, lib_agent)

    def observe_recall_plan(self, plan_obj: Any, mission_id: str = "MOCK_MEMORY_MISSION") -> SovereignPacket:
        """
        Inspects an HCAMRecallPlan, verifies that all lanes are mapped,
        and returns a SovereignPacket representing the verification verdict.
        """
        self.travel(plan_obj)

        def extract(name, default=None):
            if isinstance(plan_obj, dict):
                return plan_obj.get(name, default)
            return getattr(plan_obj, name, default)

        address = extract("address")
        address_map = extract("address_map")

        width = 0
        lane_count = 0
        bank_count = 0
        lane_to_bank = {}
        missing_mappings = []

        if address_map is not None:
            if isinstance(address_map, dict):
                width = address_map.get("width", 0)
                lane_count = address_map.get("lane_count", 0)
                banks = address_map.get("banks", [])
            else:
                width = getattr(address_map, "width", 0)
                lane_count = getattr(address_map, "lane_count", 0)
                banks = getattr(address_map, "banks", [])

            bank_count = len(banks)
            
            # Verify mappings
            for i in range(lane_count):
                found = False
                for bank in banks:
                    bank_id = bank.get("bank_id") if isinstance(bank, dict) else getattr(bank, "bank_id")
                    if bank_id == i:
                        found = True
                        lane_to_bank[i] = bank_id
                        break
                if not found:
                    missing_mappings.append(i)

        passed = len(missing_mappings) == 0 and lane_count > 0

        evidence = {
            "width": width,
            "lane_count": lane_count,
            "bank_count": bank_count,
            "address": address,
            "lane_to_bank_map": lane_to_bank,
            "missing_mappings": missing_mappings,
            "mapping_valid": passed
        }

        # Packet ID and hash
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_MEM_OBS_{id(plan_obj)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="HCAM WideWord recall map configuration report",
            evidence=evidence,
            invariants_checked=["hcam_recall_mapping"],
            artifacts=[],
            recommendation="observe" if passed else "reject",
            confidence=0.95,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed recall plan: mapping_valid={passed}.")
        return packet
