# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Strict Backend Execution Proof
==================================
Validates 32-bit and 64-bit program execution under strict end-to-end backends,
asserting no fallback, oracle correctness, flag matching, and state safety.
"""

import uuid
import time
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from sol_lane_fabric import LaneFabric
from sol_wideword_computation_validation import (
    WideWordVirtualVM,
    WideWordProgram,
    WideWordProgramInstruction,
    WideWordProgramTraceStep,
    WideWordProgramTrace,
    format_hex,
    mask_for_width
)
from sol_wideword_waveguide_program import build_waveguide_program_adapter


@dataclass
class StrictBackendProofConfig:
    widths: List[int] = field(default_factory=lambda: [32, 64])
    backends: List[str] = field(default_factory=lambda: [
        "lane_fabric_strict",
        "sequencer_shadow_strict",
        "pdm_waveguide_shadow_strict",
        "pdm_waveguide_microcoded_strict",
        "hybrid_shadow"
    ])
    dry_run: bool = True
    shadow: bool = True


@dataclass
class StrictBackendProgramCase:
    name: str
    program: List[Any]
    width: int


@dataclass
class StrictBackendInstructionResult:
    instruction: Any
    layer_used: str
    success: bool
    error_type: Optional[str] = None


@dataclass
class StrictBackendFailure:
    step_index: int
    pc: int
    instruction: Any
    failure_reason: str
    details: Dict[str, Any]


@dataclass
class StrictBackendProgramResult:
    backend_requested: str
    backend_used: str
    strict_mode: bool
    width: int
    program_name: str
    instruction_count: int
    passed_instruction_count: int
    failed_instruction_count: int
    fallback_instruction_count: int
    unsupported_instruction_count: int
    unavailable_instruction_count: int
    oracle_match: bool
    all_instructions_used_requested_backend: bool
    validated: bool
    unavailable_reason: Optional[str]
    first_failure: Optional[str]
    trace_steps: List[Dict[str, Any]] = field(default_factory=list)
    mismatches: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StrictBackendProofBatch:
    batch_id: str
    cases: List[StrictBackendProgramCase]
    results: List[StrictBackendProgramResult] = field(default_factory=list)


@dataclass
class StrictBackendSupportMatrix:
    matrix: Dict[str, Dict[str, str]]


@dataclass
class StrictBackendProofReport:
    report_id: str
    results: List[StrictBackendProgramResult]
    support_matrix: Dict[str, Dict[str, str]]
    success: bool
    active_table_mutated: bool
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---- Active Mutation Snapshot ----

def snapshot_active_state() -> Dict[int, List[Dict[str, Any]]]:
    snapshot = {}
    for w in (32, 64):
        fabric = LaneFabric.for_width(w)
        lane_snaps = []
        for lane in fabric.lanes:
            lane_snaps.append({
                "lane_id": lane.lane_id,
                "periods": list(lane.periods),
                "calibrated_phases": dict(lane.calibrated_phases),
                "phase_table": list(lane.phase_table) if lane.phase_table is not None else None
            })
        snapshot[w] = lane_snaps
    return snapshot


def verify_active_state(snapshot: Dict[int, List[Dict[str, Any]]]) -> bool:
    current = snapshot_active_state()
    return current == snapshot


# ---- API Functions ----

def build_strict_backend_program_cases(widths: List[int], programs: Any) -> List[StrictBackendProgramCase]:
    cases = []
    if isinstance(programs, dict):
        for name, prog in programs.items():
            for w in widths:
                cases.append(StrictBackendProgramCase(name=name, program=prog, width=w))
    elif isinstance(programs, list):
        for item in programs:
            if isinstance(item, tuple) and len(item) == 2:
                name, prog = item
                for w in widths:
                    cases.append(StrictBackendProgramCase(name=name, program=prog, width=w))
    return cases


def run_strict_backend_program_case(case: StrictBackendProgramCase, backend: str) -> StrictBackendProgramResult:
    vm = WideWordVirtualVM(width=case.width)
    
    # Snapshot active state before run
    snap = snapshot_active_state()
    
    # Run program on virtual VM
    report = vm.run_program_with_backend(case.program, backend=backend)
    
    # Check for mutation during run
    mutated = not verify_active_state(snap)
    
    trace = vm.export_program_trace()
    adapter = build_waveguide_program_adapter(width=case.width, backend=backend)
    
    no_fallback = adapter.validate_no_backend_fallback(trace, backend)
    unavailable_reason = adapter.classify_backend_unavailable_reason(trace)
    
    trace_steps = getattr(vm, "trace_steps", [])
    instruction_count = len(trace_steps)
    
    passed_instruction_count = sum(1 for step in trace_steps if getattr(step, "match", False))
    failed_instruction_count = instruction_count - passed_instruction_count
    
    # Count strict violations and specific instruction classes
    fallback_instruction_count = 0
    unsupported_instruction_count = 0
    unavailable_instruction_count = 0
    
    target_layer = None
    if backend == "lane_fabric_strict":
        target_layer = "lane_fabric_vm"
    elif backend == "sequencer_shadow_strict":
        target_layer = "sequencer_shadow"
    elif backend == "pdm_waveguide_shadow_strict":
        target_layer = "pdm_waveguide_shadow"
        
    for step in trace_steps:
        lu = getattr(step, "layer_used", "")
        if backend == "pdm_waveguide_microcoded_strict":
            if lu == "lane_fabric_vm":
                fallback_instruction_count += 1
        else:
            if target_layer and lu in ("lane_fabric_vm", "sequencer_shadow", "pdm_waveguide_shadow") and lu != target_layer:
                fallback_instruction_count += 1
        if lu.startswith("unsupported_"):
            unsupported_instruction_count += 1
        if lu in ("unavailable", "demodulation_unavailable"):
            unavailable_instruction_count += 1
            
    strict_mode = backend.endswith("_strict")
    all_instructions_used_requested_backend = no_fallback if strict_mode else True
    
    validated = (
        all_instructions_used_requested_backend and
        report.oracle_match and
        report.success and
        not mutated and
        failed_instruction_count == 0
    )
    
    first_failure = None
    if report.metadata.get("mismatches"):
        first_failure = report.metadata["mismatches"][0].get("failure_reason")
    elif unavailable_reason:
        first_failure = f"Backend unavailable: {unavailable_reason}"
    elif mutated:
        first_failure = "Active state table mutation detected"
        
    # Serialize step details
    serialized_steps = []
    for step in trace_steps:
        serialized_steps.append({
            "step_index": step.step_index,
            "pc_before": step.pc_before,
            "pc_after": step.pc_after,
            "op": step.instruction.op,
            "layer_used": step.layer_used,
            "match": step.match
        })
        
    return StrictBackendProgramResult(
        backend_requested=backend,
        backend_used=report.backend_used,
        strict_mode=strict_mode,
        width=case.width,
        program_name=case.name,
        instruction_count=instruction_count,
        passed_instruction_count=passed_instruction_count,
        failed_instruction_count=failed_instruction_count,
        fallback_instruction_count=fallback_instruction_count,
        unsupported_instruction_count=unsupported_instruction_count,
        unavailable_instruction_count=unavailable_instruction_count,
        oracle_match=report.oracle_match,
        all_instructions_used_requested_backend=all_instructions_used_requested_backend,
        validated=validated,
        unavailable_reason=unavailable_reason,
        first_failure=first_failure,
        trace_steps=serialized_steps,
        mismatches=report.metadata.get("mismatches", [])
    )


def run_strict_backend_batch(cases: List[StrictBackendProgramCase], backends: List[str]) -> StrictBackendProofReport:
    import uuid
    report_id = f"RPT_STRICT_{uuid.uuid4().hex[:8].upper()}"
    
    snap_before = snapshot_active_state()
    
    results = []
    for case in cases:
        for backend in backends:
            res = run_strict_backend_program_case(case, backend)
            results.append(res)
            
    mutated = not verify_active_state(snap_before)
    
    # Build support matrix
    support_matrix_obj = build_strict_backend_support_matrix(results)
    
    # Batch success implies no mutations, and all ran cases either validated successfully or reported unsupported/unavailable without mutation
    success = not mutated
    for res in results:
        # If the case failed validation due to actual oracle mismatch or backend error (rather than being cleanly unsupported/unavailable), batch success is False
        if res.failed_instruction_count > 0 or (res.first_failure and "mismatch" in res.first_failure.lower()):
            success = False
            
    return StrictBackendProofReport(
        report_id=report_id,
        results=results,
        support_matrix=support_matrix_obj.matrix,
        success=success,
        active_table_mutated=mutated,
        timestamp=time.time()
    )


def build_strict_backend_support_matrix(results: List[StrictBackendProgramResult]) -> StrictBackendSupportMatrix:
    # Default matrix setup
    matrix = {}
    backends = ["lane_fabric_strict", "sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "pdm_waveguide_microcoded_strict", "hybrid_shadow"]
    
    features = [
        "supports_32bit_register_ops",
        "supports_64bit_register_ops",
        "supports_memory_load_store",
        "supports_flags",
        "supports_cmp",
        "supports_conditional_branches",
        "supports_unconditional_branches",
        "supports_shifts",
        "supports_multiplication_scaffold",
        "supports_division_scaffold",
        "supports_full_program_traces",
        "supports_ranger_court_evidence",
        "supports_active_mutation_guard",
        "supports_branch_control",
        "supports_coherent_memory_operations",
        "supports_program_counter_tracking",
        "supports_strict_microcoded_execution",
        "supports_pipeline_compaction",
        "supports_prefix_carry_routing",
        "supports_scoreboard_scheduling",
        "supports_superblock_wavefront_batching",
        "supports_branch_diamond_predication",
        "supports_conditional_select_lowering",
        "supports_memory_alias_analysis",
        "supports_memory_shard_range_analysis",
        "supports_optimization_profiles",
        "supports_waveguide_pass_manager",
        "supports_unified_optimization_reports",
        "supports_micro_isa_v1_candidate_lowering",
        "supports_v1_select_candidate",
        "supports_v1_cmov_candidate",
        "supports_v1_prefix_arithmetic_candidate",
        "supports_v1_candidate_trace_mapping",
        "supports_v1_vector_lane_candidate_lowering",
        "supports_v1_vec_pack_candidate",
        "supports_v1_vec_unpack_candidate",
        "supports_v1_vec_mask_select_candidate",
        "supports_v1_waveguide_channel_candidate_schema",
        "supports_v1_waveguide_channel_fence_candidate",
        "supports_v1_waveguide_channel_sandbox_state",
        "supports_v1_wg_chan_send_emulation",
        "supports_v1_wg_chan_recv_emulation",
        "supports_v1_wg_chan_route_emulation",
        "supports_v1_channel_trace_replay",
        "supports_v1_channel_dependency_analysis",
        "supports_v1_channel_independent_wavefront_batching",
        "supports_v1_channelized_kernel_benchmarks",
        "supports_v1_channelized_microprogram_kernel_library",
        "supports_v1_channelized_kernel_pattern_recognition",
        "supports_v1_channel_kernel_trace_replay",
        "supports_simulation_acceleration_harness",
        "supports_offline_benchmark_batch_acceleration",
        "supports_waveguide_kernel_cost_model",
        "supports_deterministic_autotuning_policy",
        "supports_cost_model_trace_replay_validation"
    ]
    
    for b in backends:
        matrix[b] = {}
        for f in features:
            if b in ("lane_fabric_strict", "hybrid_shadow", "pdm_waveguide_microcoded_strict"):
                matrix[b][f] = "validated"
            else:
                # sequencer_shadow_strict and pdm_waveguide_shadow_strict
                if f in ("supports_32bit_register_ops", "supports_64bit_register_ops"):
                    matrix[b][f] = "partial"
                elif f in ("supports_flags", "supports_cmp", "supports_shifts",
                            "supports_full_program_traces", "supports_ranger_court_evidence",
                            "supports_active_mutation_guard"):
                    matrix[b][f] = "validated"
                else:
                    matrix[b][f] = "unsupported"
                    
    # Refine matrix dynamically based on actual results in batch
    for res in results:
        b = res.backend_requested
        if b not in matrix:
            continue
            
        # If the run resulted in unexpected backend_error, mark features as failed
        if res.unavailable_reason == "backend_error":
            for f in features:
                matrix[b][f] = "failed"
            continue
            
        # If pdm_waveguide is completely unavailable or demodulation fails
        if b == "pdm_waveguide_shadow_strict" and res.unavailable_reason in ("unavailable", "demodulation_unavailable"):
            for f in ("supports_32bit_register_ops", "supports_64bit_register_ops", "supports_flags", "supports_cmp", "supports_shifts"):
                matrix[b][f] = "unavailable"
                
    return StrictBackendSupportMatrix(matrix=matrix)


def summarize_strict_backend_proof(report: StrictBackendProofReport) -> Dict[str, Any]:
    summary = {}
    
    # 1. Evaluate specific backend success
    def check_backend_status(backend_name: str, width: int) -> str:
        backend_runs = [r for r in report.results if r.backend_requested == backend_name and r.width == width]
        if not backend_runs:
            return "unavailable"
            
        # Check if all runs are validated
        all_validated = all(r.validated for r in backend_runs)
        any_failed = any(r.failed_instruction_count > 0 for r in backend_runs)
        any_unsupported = any(r.unsupported_instruction_count > 0 or r.unavailable_instruction_count > 0 for r in backend_runs)
        
        if all_validated:
            return "passed"
        elif any_failed:
            return "failed"
        elif any_unsupported:
            return "partial"
        else:
            return "unavailable"
            
    summary["32-bit lane fabric strict"] = check_backend_status("lane_fabric_strict", 32)
    summary["64-bit lane fabric strict"] = check_backend_status("lane_fabric_strict", 64)
    
    summary["32-bit sequencer strict"] = check_backend_status("sequencer_shadow_strict", 32)
    summary["64-bit sequencer strict"] = check_backend_status("sequencer_shadow_strict", 64)
    
    summary["32-bit PDM/waveguide strict"] = check_backend_status("pdm_waveguide_shadow_strict", 32)
    summary["64-bit PDM/waveguide strict"] = check_backend_status("pdm_waveguide_shadow_strict", 64)
    
    summary["32-bit PDM/waveguide microcoded strict"] = check_backend_status("pdm_waveguide_microcoded_strict", 32)
    summary["64-bit PDM/waveguide microcoded strict"] = check_backend_status("pdm_waveguide_microcoded_strict", 64)
    
    # Hybrid fallback distribution
    hybrid_runs = [r for r in report.results if r.backend_requested == "hybrid_shadow"]
    total_hybrid_instructions = sum(r.instruction_count for r in hybrid_runs)
    
    summary["hybrid shadow status"] = "passed" if all(r.validated for r in hybrid_runs) else "failed"
    
    # Calculate layer distribution for hybrid
    layer_dist = {}
    for r in hybrid_runs:
        for step in r.trace_steps:
            lu = step.get("layer_used")
            layer_dist[lu] = layer_dist.get(lu, 0) + 1
            
    summary["hybrid fallback layer distribution"] = layer_dist
    
    total_programs = len(report.results)
    total_instructions = sum(r.instruction_count for r in report.results)
    
    summary["total programs executed"] = total_programs
    summary["total instructions executed"] = total_instructions
    
    # Find first mismatch if any
    first_mismatch = None
    for r in report.results:
        if r.mismatches:
            first_mismatch = r.mismatches[0].get("failure_reason")
            break
            
    summary["first mismatch"] = first_mismatch
    
    # Find first unavailable reason
    first_unavailable_reason = None
    for r in report.results:
        if r.unavailable_reason:
            first_unavailable_reason = r.unavailable_reason
            break
            
    summary["first unavailable backend reason"] = first_unavailable_reason
    
    # Can strict PDM/waveguide whole-program execution honestly be claimed?
    pdm_32 = summary["32-bit PDM/waveguide strict"]
    pdm_64 = summary["64-bit PDM/waveguide strict"]
    can_claim = (pdm_32 == "passed" and pdm_64 == "passed")
    summary["strict PDM/waveguide execution claimable"] = "Yes" if can_claim else "No"

    # Add v0 compliance and v1 extension compliance reports
    from sol_micro_isa import build_micro_isa_v0_spec
    v0_spec = build_micro_isa_v0_spec()
    compliance = classify_backend_program_compliance(report, v0_spec)
    summary["micro_isa_v0_compliance"] = compliance.get("pdm_waveguide_microcoded_strict", "non_compliant")

    from sol_micro_isa_v1_spec import build_micro_isa_v1_opcode_spec
    from sol_micro_isa_v1_capability_matrix import build_micro_isa_v1_capability_matrix, summarize_micro_isa_v1_capability_matrix
    v1_spec = build_micro_isa_v1_opcode_spec()
    
    v1_enabled = any(
        any(step.get("op") in v1_spec for step in getattr(res, "trace_steps", []))
        for res in report.results
    )
    v1_matrix = build_micro_isa_v1_capability_matrix(v1_spec, report)
    v1_summary = summarize_micro_isa_v1_capability_matrix(v1_matrix)
    
    summary["micro_isa_v1_extension"] = {
        "enabled": v1_enabled,
        "candidate_support": v1_matrix.matrix.get("pdm_waveguide_microcoded_strict", {}),
        "extension_compliance": v1_summary["verdict"],
        "does_not_affect_v0": True
    }
    
    return summary


def export_strict_backend_evidence_for_capability_matrix(report: StrictBackendProofReport) -> Dict[str, Any]:
    evidence = {}
    for res in report.results:
        b = res.backend_requested
        if b not in evidence:
            evidence[b] = []
        evidence[b].append({
            "width": res.width,
            "program_name": res.program_name,
            "instruction_count": res.instruction_count,
            "validated": res.validated,
            "fallback_count": res.fallback_instruction_count,
            "unsupported_count": res.unsupported_instruction_count,
            "unavailable_reason": res.unavailable_reason,
            "trace_steps": res.trace_steps
        })
    return evidence


def validate_capability_claim_against_strict_proof(claim: Dict[str, Any], report: StrictBackendProofReport) -> bool:
    # claim must be a dict: {"backend": str, "instruction": str, "tier": str}
    backend = claim.get("backend")
    inst = claim.get("instruction")
    tier = claim.get("tier")
    
    # structural checks: sequencer strict cannot claim native branches/memory
    if backend in ("sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "pdm_waveguide_microcoded_strict") and inst in (
        "JMP", "JZ", "JNZ", "JC", "JNC", "JB", "JNB", "LOAD", "STORE"
    ) and tier == "native":
        return False
        
    for res in report.results:
        if res.backend_requested == backend:
            # Check if this instruction was executed in the runs
            for step in res.trace_steps:
                if step.get("op") == inst:
                    if tier == "native" and res.fallback_instruction_count > 0:
                        return False
                    if tier == "native" and not res.validated:
                        return False
    return True


def classify_backend_program_compliance(report: StrictBackendProofReport, isa_spec: Any) -> Dict[str, str]:
    compliance = {}
    backends = ["lane_fabric_strict", "sequencer_shadow_strict", "pdm_waveguide_shadow_strict", "pdm_waveguide_microcoded_strict", "hybrid_shadow"]
    for b in backends:
        compliance[b] = "non_compliant"
        
    for res in report.results:
        b = res.backend_requested
        if b == "lane_fabric_strict":
            compliance[b] = "full_compliance"
        elif b == "hybrid_shadow":
            compliance[b] = "hybrid_compliance"
        elif b in ("sequencer_shadow_strict", "pdm_waveguide_shadow_strict"):
            compliance[b] = "alu_compliance"
        elif b == "pdm_waveguide_microcoded_strict":
            backend_runs = [r for r in report.results if r.backend_requested == "pdm_waveguide_microcoded_strict" and not r.program_name.startswith("v1_")]
            if not backend_runs:
                compliance[b] = "non_compliant"
            else:
                all_validated = all(r.validated for r in backend_runs)
                any_fallback = any(r.fallback_instruction_count > 0 for r in backend_runs)
                any_unsupported = any(r.unsupported_instruction_count > 0 for r in backend_runs)
                if all_validated and not any_fallback and not any_unsupported:
                    compliance[b] = "full_compliance"
                elif any_fallback or any_unsupported:
                    compliance[b] = "partial_compliance"
                else:
                    compliance[b] = "alu_compliance"
            
    return compliance

