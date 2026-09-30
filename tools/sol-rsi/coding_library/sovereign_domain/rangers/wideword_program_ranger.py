# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
WideWord Program Ranger
=======================
Observes WaveguideProgramExecutionReport, WideWordProgramTrace, and WaveguideProgramAdapterReport,
generating a SovereignPacket evidence packet.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any, Dict, List
import time

class WideWordProgramRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe WideWord Waveguide Program executions.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the WideWord Program Ranger. You inspect Waveguide Program execution reports\n"
            "and WideWord program traces to verify deterministic correctness and lack of state mutation."
        )
        super().__init__("WideWord Program Ranger", system_prompt, lib_agent)

    def observe_program_execution(
        self,
        execution_report: Any,
        program_trace: Any,
        adapter_report: Any = None,
        mission_id: str = "MOCK_WWP_MISSION"
    ) -> SovereignPacket:
        """
        Observes Waveguide Program execution reports, validates correctness,
        and returns a SovereignPacket evidence packet.
        """
        if execution_report is not None:
            self.travel(execution_report)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # Retrieve basic metrics
        width = extract(execution_report, "width") or 32
        backend_requested = extract(execution_report, "backend_requested") or "lane_fabric_vm"
        
        # Determine layers used
        layers_used = extract(execution_report, "layers_used") or {}
        backend_used = extract(execution_report, "backend_used") or backend_requested
        
        trace_steps = extract(program_trace, "steps") or []
        instruction_count = len(trace_steps)
        
        passed_instruction_count = sum(1 for step in trace_steps if extract(step, "match", False))
        failed_instruction_count = instruction_count - passed_instruction_count
        
        unavailable_layer_count = sum(1 for step in trace_steps if extract(step, "layer_used") == "unavailable")
        
        oracle_match_status = extract(execution_report, "oracle_match", False)
        active_table_mutation_status = extract(execution_report, "active_table_mutated", False)
        
        # Promotion readiness
        promotion_ready = (
            oracle_match_status and
            not active_table_mutation_status and
            failed_instruction_count == 0 and
            unavailable_layer_count == 0
        )
        
        evidence = {
            "width": width,
            "backend_requested": backend_requested,
            "backend_used": backend_used,
            "program_count": 1,
            "instruction_count": instruction_count,
            "passed_instruction_count": passed_instruction_count,
            "failed_instruction_count": failed_instruction_count,
            "unavailable_layer_count": unavailable_layer_count,
            "oracle_match_status": oracle_match_status,
            "active_table_mutation_status": active_table_mutation_status,
            "promotion_ready": promotion_ready
        }
        
        import uuid
        packet = SovereignPacket(
            packet_id=f"PKT_WWP_{uuid.uuid4().hex[:8].upper()}",
            domain="compute",
            level=37,
            actor="WideWord Program Ranger",
            actor_type="ranger",
            mission_id=mission_id,
            claim="WideWord Waveguide Program Execution verified successfully" if promotion_ready else "WideWord Waveguide Program Execution validation failed",
            evidence=evidence,
            invariants_checked=["oracle_match_status", "no_active_table_mutation"],
            artifacts=[],
            recommendation="observe" if promotion_ready else "reject",
            confidence=1.0,
            reproducibility_hash=extract(execution_report, "reproducibility_hash", "hash_placeholder")
        )
        return packet
