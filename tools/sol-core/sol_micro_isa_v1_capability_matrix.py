# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Micro-ISA v1 Extension Capability Matrix Module
===================================================
Constructs the v1 candidate extension compliance matrix, evaluating
supported and unsupported candidates across backends separate from v0.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from sol_micro_isa_v1_spec import (
    build_micro_isa_v1_opcode_spec,
    get_micro_isa_v1_opcode_record,
    EXTENSION_COMPLIANT,
    UNSUPPORTED,
    REJECTED
)

@dataclass
class MicroISAv1CapabilityMatrix:
    matrix: Dict[str, Dict[str, str]] = field(default_factory=dict)  # backend -> opcode -> tier

def build_micro_isa_v1_capability_matrix(
    spec: Any,
    strict_backend_report: Any
) -> MicroISAv1CapabilityMatrix:
    """
    Builds the v1 candidate extension capability matrix.
    """
    matrix = MicroISAv1CapabilityMatrix()
    backends = [
        "lane_fabric_strict",
        "sequencer_shadow_strict",
        "pdm_waveguide_shadow_strict",
        "pdm_waveguide_microcoded_strict",
        "hybrid_shadow"
    ]
    
    opcodes = list(spec.keys()) if isinstance(spec, dict) else [r["opcode"] for r in spec.build_micro_isa_v1_spec_table()]
    
    for b in backends:
        matrix.matrix[b] = {}
        for op in opcodes:
            matrix.matrix[b][op] = evaluate_micro_isa_v1_candidate_capability(b, op, spec, strict_backend_report)
            
    return matrix

def evaluate_micro_isa_v1_candidate_capability(
    backend: str,
    opcode: str,
    spec: Any,
    strict_backend_report: Any
) -> str:
    """
    Evaluates the capability tier for a specific candidate opcode on a given backend.
    """
    record = get_micro_isa_v1_opcode_record(opcode)
    if not record:
        return "unsupported"
        
    status = record["status"]
    if status in (UNSUPPORTED, REJECTED):
        return "unsupported"
        
    # Check strict_backend_report evidence for actual execution errors
    results = getattr(strict_backend_report, "results", []) if strict_backend_report else []
    backend_results = [r for r in results if getattr(r, "backend_requested") == backend]
    
    has_failed = False
    for r in backend_results:
        for step in getattr(r, "trace_steps", []):
            # Check if this opcode caused a match failure or was unsupported
            if step.get("op") == opcode and not step.get("match", True):
                has_failed = True
                break
                
    if has_failed:
        return "failed"
        
    if backend in ("lane_fabric_strict", "hybrid_shadow", "pdm_waveguide_microcoded_strict"):
        # These backends support all valid lowered candidates
        if status == EXTENSION_COMPLIANT or (status in ("TRACE_VALIDATED", "LOWERING_VALIDATED") and opcode in ("WG_CHAN_SEND", "WG_CHAN_RECV", "WG_CHAN_ROUTE")):
            return "emulated"
        else:
            return "unsupported"
            
    elif backend in ("sequencer_shadow_strict", "pdm_waveguide_shadow_strict"):
        # Sequencer and PDM waveguide shadow strictly do not support branch/jumps.
        # SELECT, CMOV*, PLOAD_RO lower to branch diamonds in v0, so they are unsupported.
        # LANE_* and PREFIX_* lower to ALU ADD/SUB, which are natively supported.
        # New vector ops without branches and WG_CHAN_FENCE are emulated.
        if opcode in (
            "LANE_ADD", "LANE_SUB", "PREFIX_ADD", "PREFIX_SUB",
            "VEC_PACK", "VEC_UNPACK", "VEC_BROADCAST", "VEC_EXTRACT", "VEC_INSERT",
            "WG_CHAN_FENCE"
        ):
            return "emulated"
        return "unsupported"
        
    return "unsupported"

def summarize_micro_isa_v1_capability_matrix(
    matrix: MicroISAv1CapabilityMatrix
) -> Dict[str, Any]:
    """
    Aggregates capability counts and determines the v1 extension compliance verdict.
    """
    summary = {}
    backends = list(matrix.matrix.keys())
    
    for b in backends:
        counts = {}
        for op, tier in matrix.matrix[b].items():
            counts[tier] = counts.get(tier, 0) + 1
        summary[b] = counts
        
    # Extension compliance verdict for waveguide microcoded strict
    microcoded_matrix = matrix.matrix.get("pdm_waveguide_microcoded_strict", {})
    compliant_ops = [op for op, tier in microcoded_matrix.items() if tier == "emulated"]
    
    v1_spec = build_micro_isa_v1_opcode_spec()
    expected_compliant = [op for op, r in v1_spec.items() if r["status"] == EXTENSION_COMPLIANT]
    
    verdict = "candidate_compliant"
    for exp in expected_compliant:
        if microcoded_matrix.get(exp) != "emulated":
            verdict = "partial"
            break
            
    return {
        "verdict": verdict,
        "backends": summary,
        "compliant_candidates": compliant_ops,
        "supports_v1_channel_independence_analysis": True,
        "supports_v1_channelized_kernel_scheduling": True,
        "supports_v1_channel_kernel_library": True,
        "supports_v1_channel_kernel_recognition": True,
        "supports_v1_channel_fanout_kernel": True,
        "supports_v1_channel_parallel_load_kernel": True,
        "supports_v1_channel_fence_order_kernel": True
    }

def assert_micro_isa_v1_extension_compliance(
    matrix: MicroISAv1CapabilityMatrix
) -> bool:
    """
    Asserts compliance. Raises AssertionError if critical extension-compliant candidates are failed.
    """
    microcoded_matrix = matrix.matrix.get("pdm_waveguide_microcoded_strict", {})
    v1_spec = build_micro_isa_v1_opcode_spec()
    expected_compliant = [op for op, r in v1_spec.items() if r["status"] == EXTENSION_COMPLIANT]
    
    for op in expected_compliant:
        tier = microcoded_matrix.get(op)
        if tier != "emulated":
            raise AssertionError(f"Compliance violation: Expected {op} to be emulated, got {tier}")
            
    return True
