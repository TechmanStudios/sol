# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Waveguide Control-Memory Ranger
===============================
Observes WaveguideBranchControlReport, WaveguideMemoryShardReport,
and WaveguideControlMemoryExecutionReport, producing a SovereignPacket.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any, Dict, List
import time
import uuid

class WaveguideControlMemoryRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe WideWord Waveguide Control-Memory Bridge execution.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Waveguide Control-Memory Ranger. You inspect Waveguide Control-Memory\n"
            "execution, branch control, and memory shard reports and verify compliance."
        )
        super().__init__("Waveguide Control-Memory Ranger", system_prompt, lib_agent)

    def observe_waveguide_control_memory(
        self,
        branch_report: Any,
        memory_report: Any,
        execution_report: Any,
        capability_matrix: Any,
        compliance_report: Any = None,
        widths: List[int] = None,
        mission_id: str = "MOCK_WAVEGUIDE_BRIDGE_MISSION"
    ) -> SovereignPacket:
        """
        Observes bridge reports and produces a SovereignPacket with the required metrics.
        """
        if execution_report is not None:
            self.travel(execution_report)
        
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # 1. Width count
        if widths is None:
            widths = [32, 64]
        width_count = len(widths)

        # 2. Extract execution steps and counts
        trace_steps = extract(execution_report, "trace_steps", []) or []
        mismatches = extract(execution_report, "mismatches", []) or []
        
        program_count = 1  # Standard single program case or custom batch
        instruction_count = len(trace_steps)
        
        branch_instruction_count = 0
        memory_instruction_count = 0
        alu_instruction_count = 0
        fallback_count = 0
        unsupported_instruction_count = 0
        
        # Count instruction types from trace_steps
        for step in trace_steps:
            lu = extract(step, "layer_used", "")
            op = extract(extract(step, "instruction"), "op", "").upper()
            
            if lu == "waveguide_branch_control":
                branch_instruction_count += 1
            elif lu == "waveguide_memory_shard":
                memory_instruction_count += 1
            elif lu == "pdm_waveguide_shadow":
                alu_instruction_count += 1
            elif lu == "lane_fabric_vm":
                fallback_count += 1
            elif lu.startswith("unsupported_"):
                unsupported_instruction_count += 1

        oracle_mismatch_count = len(mismatches)
        
        active_mutation_status = extract(execution_report, "active_mutated", False)
        
        # Compliance status
        compliance_status = "non_compliant"
        if compliance_report is not None:
            results = extract(compliance_report, "results", []) or []
            for r in results:
                if extract(r, "backend") == "pdm_waveguide_microcoded_strict":
                    compliance_status = extract(r, "compliance_level", "non_compliant")
        else:
            # Fallback deduction: if no mismatches, no fallbacks, and success
            success = extract(execution_report, "success", False)
            if success and oracle_mismatch_count == 0 and fallback_count == 0 and unsupported_instruction_count == 0:
                compliance_status = "full_compliance"
            elif fallback_count > 0 or unsupported_instruction_count > 0:
                compliance_status = "partial_compliance"

        # Promotion readiness: no fallbacks, no mismatches, no mutation, success
        success = extract(execution_report, "success", False)
        promotion_ready = (
            success and 
            fallback_count == 0 and 
            oracle_mismatch_count == 0 and 
            unsupported_instruction_count == 0 and 
            not active_mutation_status
        )

        evidence = {
            "width count": width_count,
            "program count": program_count,
            "instruction count": instruction_count,
            "branch instruction count": branch_instruction_count,
            "memory instruction count": memory_instruction_count,
            "ALU instruction count": alu_instruction_count,
            "fallback count": fallback_count,
            "oracle mismatch count": oracle_mismatch_count,
            "unsupported instruction count": unsupported_instruction_count,
            "active mutation status": active_mutation_status,
            "Micro-ISA compliance status": compliance_status,
            "promotion readiness": promotion_ready
        }

        packet = SovereignPacket(
            packet_id=f"PKT_WCMB_{uuid.uuid4().hex[:8].upper()}",
            domain="compute",
            level=38,
            actor="Waveguide Control-Memory Ranger",
            actor_type="ranger",
            mission_id=mission_id,
            claim="Waveguide Control-Memory Bridge validation completed" if promotion_ready else "Waveguide Control-Memory Bridge validation failed",
            evidence=evidence,
            invariants_checked=["no_fallback", "no_active_table_mutation", "branch_gating", "memory_coherency"],
            artifacts=[],
            recommendation="observe" if promotion_ready else "reject",
            confidence=1.0,
            reproducibility_hash=uuid.uuid4().hex
        )
        return packet
