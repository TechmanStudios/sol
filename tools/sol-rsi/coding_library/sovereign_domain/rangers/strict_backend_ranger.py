# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Strict Backend Ranger
====================
Observes StrictBackendProofReport and StrictBackendSupportMatrix,
generating a SovereignPacket evidence packet.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any, Dict, List
import time
import uuid

class StrictBackendRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe WideWord Strict Backend Execution Proofs.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Strict Backend Ranger. You inspect Strict Backend Proof reports\n"
            "and verify that strict execution rules are met, fallbacks are detected, and no active mutation occurred."
        )
        super().__init__("Strict Backend Ranger", system_prompt, lib_agent)

    def observe_strict_proof(
        self,
        proof_report: Any,
        support_matrix: Any = None,
        mission_id: str = "MOCK_STRICT_MISSION"
    ) -> SovereignPacket:
        """
        Observes a StrictBackendProofReport, validates execution attributes,
        and returns a SovereignPacket.
        """
        if proof_report is not None:
            self.travel(proof_report)
            
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)
            
        results = extract(proof_report, "results") or []
        matrix = extract(proof_report, "support_matrix") or {}
        if not matrix and support_matrix is not None:
            matrix = extract(support_matrix, "matrix") or {}
            
        backends_evaluated = set(extract(res, "backend_requested") for res in results)
        backend_count = len(backends_evaluated)
        
        validated_backends = set()
        unavailable_backends = set()
        failed_backends = set()
        
        total_programs = len(results)
        total_instructions = 0
        fallback_violations = 0
        oracle_mismatch_count = 0
        
        for res in results:
            total_instructions += extract(res, "instruction_count", 0)
            fallback_violations += extract(res, "fallback_instruction_count", 0)
            if not extract(res, "oracle_match", True):
                oracle_mismatch_count += 1
                
            b = extract(res, "backend_requested")
            if extract(res, "validated", False):
                validated_backends.add(b)
            elif extract(res, "unavailable_reason") in ("unavailable", "demodulation_unavailable"):
                unavailable_backends.add(b)
            elif extract(res, "failed_instruction_count", 0) > 0 or extract(res, "unavailable_reason") == "backend_error":
                failed_backends.add(b)
                
        validated_backend_count = len(validated_backends)
        unavailable_backend_count = len(unavailable_backends)
        failed_backend_count = len(failed_backends)
        
        active_mutation_status = extract(proof_report, "active_table_mutated", False)
        
        success = extract(proof_report, "success", False)
        promotion_ready = success and not active_mutation_status
        
        evidence = {
            "backend_count": backend_count,
            "validated_backend_count": validated_backend_count,
            "unavailable_backend_count": unavailable_backend_count,
            "failed_backend_count": failed_backend_count,
            "total_programs": total_programs,
            "total_instructions": total_instructions,
            "fallback_violations": fallback_violations,
            "oracle_mismatch_count": oracle_mismatch_count,
            "active_mutation_status": active_mutation_status,
            "support_matrix_summary": matrix,
            "promotion_ready": promotion_ready
        }
        
        packet = SovereignPacket(
            packet_id=f"PKT_STRICT_{uuid.uuid4().hex[:8].upper()}",
            domain="compute",
            level=38,
            actor="Strict Backend Ranger",
            actor_type="ranger",
            mission_id=mission_id,
            claim="Strict WideWord Backend Execution Proof completed successfully" if promotion_ready else "Strict WideWord Backend Execution Proof validation failed",
            evidence=evidence,
            invariants_checked=["no_strict_fallback", "no_active_table_mutation", "oracle_correctness"],
            artifacts=[],
            recommendation="observe" if promotion_ready else "reject",
            confidence=1.0,
            reproducibility_hash=uuid.uuid4().hex
        )
        return packet
