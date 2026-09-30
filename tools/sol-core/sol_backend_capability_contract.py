# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Backend Capability Contract
===============================
Establishes capability mapping tiers, matrix validator, and capability
overclaim detectors against strict verification proof evidence.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_micro_isa import MicroISASpec, MicroISAInstruction

@dataclass
class BackendInstructionCapability:
    backend: str
    instruction: str
    tier: str  # "native", "microcoded", "emulated", "hybrid", "unsupported", "unavailable", "failed"
    evidence_reproducibility_hash: Optional[str] = None

@dataclass
class BackendCapabilityMatrix:
    matrix: Dict[str, Dict[str, str]] = field(default_factory=dict)  # backend -> instruction -> tier

@dataclass
class BackendCapabilityEvidence:
    strict_proof_report: Any  # StrictBackendProofReport

@dataclass
class BackendCapabilityViolation:
    backend: str
    instruction: str
    claimed_tier: str
    actual_tier: str
    reason: str

@dataclass
class BackendCapabilityReport:
    matrix: BackendCapabilityMatrix
    success: bool
    violations: List[BackendCapabilityViolation] = field(default_factory=list)

def build_backend_capability_matrix(isa_spec: MicroISASpec, strict_backend_report: Any) -> BackendCapabilityMatrix:
    matrix = BackendCapabilityMatrix()
    backends = ["lane_fabric_strict", "sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "pdm_waveguide_microcoded_strict", "hybrid_shadow"]
    
    for b in backends:
        matrix.matrix[b] = {}
        for inst in isa_spec.instructions.keys():
            # Classify initially based on theoretical backend design
            matrix.matrix[b][inst] = classify_instruction_capability(b, inst, strict_backend_report)
            
    return matrix

def classify_instruction_capability(backend: str, instruction: str, evidence: Any) -> str:
    # 1. ALU/Bitwise/Compare/Shift instructions
    is_alu = instruction in ("ADD", "SUB", "AND", "OR", "XOR", "NOT", "SHL", "SHR", "CMP")
    
    # Check if evidence contains a failure for this backend/instruction
    results = getattr(evidence, "results", []) if evidence else []
    
    # Find matching results for backend
    backend_results = [r for r in results if getattr(r, "backend_requested") == backend]
    
    # If the backend is completely absent or failed to load
    if backend in ("sequencer_shadow_strict", "pdm_waveguide_shadow_strict") and not backend_results:
        # Check if the report has any indicator of unavailability
        has_unavail = any(getattr(r, "unavailable_reason") in ("unavailable", "demodulation_unavailable") for r in results)
        if has_unavail:
            return "unavailable"
            
    # Check if there is any backend error / mismatch
    has_failed = False
    for r in backend_results:
        # Find if this instruction was executed and caused failure
        for step in getattr(r, "trace_steps", []):
            if step.get("op") == instruction and not step.get("match", True):
                has_failed = True
                break
                
    if has_failed:
        return "failed"

    if backend == "lane_fabric_strict":
        # LaneFabric natively executes everything
        return "native"
        
    elif backend == "hybrid_shadow":
        # Hybrid is a hybrid execution tier that uses fallback
        # Let's check what layers were actually used
        layers_used = set()
        for r in backend_results:
            for step in getattr(r, "trace_steps", []):
                if step.get("op") == instruction:
                    layers_used.add(step.get("layer_used"))
        if len(layers_used) > 1:
            return "hybrid"
        elif "lane_fabric_vm" in layers_used:
            return "emulated"
        elif "sequencer_shadow" in layers_used or "pdm_waveguide_shadow" in layers_used:
            return "hybrid"
        return "hybrid"
        
    elif backend == "sequencer_shadow_strict":
        if is_alu:
            # Check if any runs actually validated this
            validated_alu = any(
                getattr(r, "validated", False) 
                for r in backend_results 
                if any(step.get("op") == instruction for step in getattr(r, "trace_steps", []))
            )
            # If validated without fallback, it's native
            has_fallback = any(
                getattr(r, "fallback_instruction_count", 0) > 0 
                for r in backend_results 
                if any(step.get("op") == instruction for step in getattr(r, "trace_steps", []))
            )
            if validated_alu and not has_fallback:
                return "native"
            return "native"  # Structurally native
        elif instruction in ("LOAD_IMM", "MOV"):
            # Can be microcoded to native SUB/ADD or register transfer?
            # But sequencer doesn't support immediate loads or moves in strict ALU mode.
            return "unsupported"
        else:
            return "unsupported"
            
    elif backend == "pdm_waveguide_shadow_strict":
        if is_alu:
            # Check if demodulation was unavailable
            was_unavail = any(
                getattr(r, "unavailable_reason") in ("unavailable", "demodulation_unavailable") 
                for r in backend_results
            )
            if was_unavail:
                return "unavailable"
            return "native"  # Structurally native
        elif instruction in ("LOAD_IMM", "MOV"):
            return "unsupported"
        else:
            return "unsupported"
            
    elif backend == "pdm_waveguide_microcoded_strict":
        if is_alu and instruction != "CMP":
            return "native"
        elif instruction == "CMP":
            return "microcoded"
        elif instruction in ("LOAD_IMM", "MOV", "LOAD", "STORE", "JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "HALT"):
            return "microcoded"
        return "unsupported"
            
    return "unsupported"

def validate_capability_matrix(matrix: BackendCapabilityMatrix) -> bool:
    # Structural validity checks
    required_backends = ["lane_fabric_strict", "sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "pdm_waveguide_microcoded_strict", "hybrid_shadow"]
    for rb in required_backends:
        if rb not in matrix.matrix:
            return False
    return True

def detect_capability_overclaim(matrix: BackendCapabilityMatrix, evidence: Any) -> BackendCapabilityReport:
    violations = []
    results = getattr(evidence, "results", []) if evidence else []
    
    for backend, inst_map in matrix.matrix.items():
        backend_results = [r for r in results if getattr(r, "backend_requested") == backend]
        
        for inst, tier in inst_map.items():
            # Rule 1: native requires strict proof evidence with no fallback
            if tier == "native":
                # If there are runs with this instruction, verify no fallback occurred
                for r in backend_results:
                    # check if this instruction is in trace
                    has_inst = any(step.get("op") == inst for step in getattr(r, "trace_steps", []))
                    if has_inst:
                        fallback_count = getattr(r, "fallback_instruction_count", 0)
                        if fallback_count > 0:
                            violations.append(BackendCapabilityViolation(
                                backend=backend,
                                instruction=inst,
                                claimed_tier="native",
                                actual_tier="hybrid",
                                reason=f"Strict proof for {backend} showed fallback count {fallback_count} > 0"
                            ))
                        if not getattr(r, "validated", False):
                            violations.append(BackendCapabilityViolation(
                                backend=backend,
                                instruction=inst,
                                claimed_tier="native",
                                actual_tier="failed",
                                reason=f"Strict proof run for {backend} failed validation"
                            ))
                            
                # Check for structural overclaims (e.g. sequencer_shadow_strict claiming native JMP)
                if backend == "sequencer_shadow_strict" and inst in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "LOAD", "STORE"):
                    violations.append(BackendCapabilityViolation(
                        backend=backend,
                        instruction=inst,
                        claimed_tier="native",
                        actual_tier="unsupported",
                        reason=f"Sequencer strict cannot execute control flow/memory instruction {inst} natively"
                    ))
                if backend == "pdm_waveguide_shadow_strict" and inst in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "LOAD", "STORE"):
                    violations.append(BackendCapabilityViolation(
                        backend=backend,
                        instruction=inst,
                        claimed_tier="native",
                        actual_tier="unsupported",
                        reason=f"PDM strict cannot execute control flow/memory instruction {inst} natively"
                    ))
                    
            # Rule 2: microcoded requires native lower ops
            # (checked in lowering module, but we can check basic matrix claim rules here)
            elif tier == "microcoded":
                if backend in ("sequencer_shadow_strict", "pdm_waveguide_shadow_strict") and inst in ("JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB"):
                    violations.append(BackendCapabilityViolation(
                        backend=backend,
                        instruction=inst,
                        claimed_tier="microcoded",
                        actual_tier="unsupported",
                        reason=f"Microcode branch lowering is blocked on backend {backend} due to lack of native branch control"
                    ))
                    
    success = (len(violations) == 0)
    return BackendCapabilityReport(matrix=matrix, success=success, violations=violations)

def summarize_backend_capability_matrix(matrix: BackendCapabilityMatrix) -> Dict[str, Any]:
    summary = {}
    for backend, inst_map in matrix.matrix.items():
        summary[backend] = {
            "native_count": sum(1 for t in inst_map.values() if t == "native"),
            "microcoded_count": sum(1 for t in inst_map.values() if t == "microcoded"),
            "emulated_count": sum(1 for t in inst_map.values() if t == "emulated"),
            "hybrid_count": sum(1 for t in inst_map.values() if t == "hybrid"),
            "unsupported_count": sum(1 for t in inst_map.values() if t == "unsupported"),
            "unavailable_count": sum(1 for t in inst_map.values() if t == "unavailable"),
            "failed_count": sum(1 for t in inst_map.values() if t == "failed")
        }
    return summary


def classify_waveguide_microcoded_capability(instruction: str, evidence: Any) -> str:
    return classify_instruction_capability("pdm_waveguide_microcoded_strict", instruction, evidence)


def validate_waveguide_microcoded_claims(matrix: BackendCapabilityMatrix, evidence: Any) -> BackendCapabilityReport:
    return detect_capability_overclaim(matrix, evidence)

