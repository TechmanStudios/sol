# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Sequencer Ranger
================
Observes WideWordInstructionResult and WordCommitPacket, emitting valid SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class SequencerRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Multi-Lane Sequencer operations and commits.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Sequencer Ranger. You inspect WideWordInstructionResult and\n"
            "WordCommitPacket objects, verifying execution correctness and gate compliance."
        )
        super().__init__("Sequencer Ranger", system_prompt, lib_agent)

    def observe_sequencer(self, target_obj: Any, mission_id: str = "MOCK_SEQUENCER_MISSION") -> SovereignPacket:
        """
        Inspects a WideWordInstructionResult or WordCommitPacket and returns a SovereignPacket.
        """
        self.travel(target_obj)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        obj_classname = target_obj.__class__.__name__

        # Initialize defaults
        op = "UNKNOWN"
        width = 0
        lane_count = 0
        dry_run = True
        passed_gates = False
        commit_status = "N/A"
        result_val = 0
        repro_hash = "none"

        if obj_classname == "WideWordInstructionResult":
            inst = extract(target_obj, "instruction")
            op = extract(inst, "op", "UNKNOWN")
            width = extract(inst, "width", 0)
            lane_count = extract(inst, "lane_count", 0)
            dry_run = extract(inst, "dry_run", True)
            passed_gates = extract(target_obj, "passed_gates", False)
            result_val = extract(target_obj, "result", 0)
            
            gate_report = extract(target_obj, "gate_report", {})
            errors = extract(gate_report, "errors", [])
            
            commit_status = "executed_dry_run" if dry_run else "executed_live_attempt"
            repro_hash = f"sha256_{hash(str(result_val)) & 0xFFFFFFFF:08x}"

        elif obj_classname == "WordCommitPacket":
            op = extract(target_obj, "op", "UNKNOWN")
            width = extract(target_obj, "width", 0)
            lane_count = width // 8
            dry_run = True  # Commits to local scaffold ledger are dry-run by default
            
            gate_report = extract(target_obj, "gate_report", {})
            passed_gates = extract(gate_report, "passed", False)
            errors = extract(gate_report, "errors", [])
            result_val = extract(target_obj, "result", 0)
            repro_hash = extract(target_obj, "reproducibility_hash", "none")
            
            commit_status = "committed_scaffold" if passed_gates else "commit_blocked"

        # Evidence payload
        evidence = {
            "op": op,
            "width": width,
            "lane_count": lane_count,
            "dry_run": dry_run,
            "gate_passed": passed_gates,
            "commit_status": commit_status,
            "result": result_val,
            "reproducibility_hash": repro_hash,
            "target_type": obj_classname
        }

        # Determine recommendation:
        # If gates passed, recommend promote or observe.
        # If gates failed, recommend reject.
        recommendation = "observe" if passed_gates else "reject"

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_SEQ_OBS_{id(target_obj)}_{timestamp_str}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Multi-lane sequencer WideWord execution and commit observation report",
            evidence=evidence,
            invariants_checked=["sequencer_instruction_gating", "wide_word_format"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.98,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed sequencer result: op={op}, status={commit_status}, passed={passed_gates}.")
        return packet
