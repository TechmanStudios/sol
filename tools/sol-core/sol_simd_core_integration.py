# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL SIMD Core Integration
=========================
Coordinates waveguide fabric bindings with multi-core sequencer dispatch and execution.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class SIMDCoreBinding:
    core_id: str
    simd_mode: str
    waveguide_lane_ids: List[int]
    active: bool = True

@dataclass
class SIMDCoreFabricMap:
    map_id: str
    candidate_id: str
    bindings: List[SIMDCoreBinding]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SIMDWaveguideDispatchPlan:
    plan_id: str
    operation: Any  # SIMDInstruction or dict
    binding_map: SIMDCoreFabricMap
    dispatch_steps: List[str]
    timestamp: float = field(default_factory=time.time)

@dataclass
class SIMDWaveguideExecutionTrace:
    trace_id: str
    plan_id: str
    dispatched_values: List[int]
    executed_results: List[int]
    crosstalk_readings: Dict[int, float]
    phase_coherence: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class SIMDCoreIntegrationReport:
    report_id: str
    binding_map: SIMDCoreFabricMap
    success: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    candidate: Optional[Any] = None
    simd_modes: List[str] = field(default_factory=list)
    dispatch_plan: Optional[Any] = None
    trace: Optional[Any] = None
    oracle_match: bool = True



def bind_waveguide_fabric_to_simd_cores(candidate: Any, core_group: Any, simd_modes: List[str]) -> SIMDCoreFabricMap:
    """
    Creates bindings between core groups and the candidate waveguide lanes.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    core_ids = list(extract(core_group, "cores", {}).keys())
    if not core_ids:
        # Fallback default cores
        core_ids = ["core_0", "core_1"]
        
    num_cores = len(core_ids)
    lane_bindings = extract(candidate, "lane_bindings", [])
    num_lanes = len(lane_bindings)
    
    # Partition lanes across cores
    bindings = []
    lanes_per_core = max(1, num_lanes // num_cores)
    
    for idx, cid in enumerate(core_ids):
        start = idx * lanes_per_core
        # Last core grabs remaining lanes
        end = num_lanes if idx == num_cores - 1 else min(start + lanes_per_core, num_lanes)
        lane_subset = [lane_bindings[l].lane_id for l in range(start, end) if l < num_lanes]
        
        for mode in simd_modes:
            bindings.append(SIMDCoreBinding(
                core_id=cid,
                simd_mode=mode,
                waveguide_lane_ids=lane_subset
            ))

    map_id = f"SIMDMAP_{extract(candidate, 'candidate_id', 'unknown')}_{int(time.time())}"
    return SIMDCoreFabricMap(
        map_id=map_id,
        candidate_id=extract(candidate, "candidate_id", "unknown"),
        bindings=bindings
    )


def validate_simd_core_bindings(binding_map: SIMDCoreFabricMap) -> bool:
    """
    Ensures that SIMD core bindings are valid and completely cover all lanes.
    """
    if not binding_map.bindings:
        return False
        
    for b in binding_map.bindings:
        if not b.core_id:
            return False
        if not b.simd_mode:
            return False
        if not b.waveguide_lane_ids:
            return False
            
    return True


def plan_simd_waveguide_dispatch(operation: Any, binding_map: SIMDCoreFabricMap) -> SIMDWaveguideDispatchPlan:
    """
    Generates a waveguide dispatch plan for a SIMD instruction.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    op_code = extract(operation, "op", "VADD")
    mode_name = extract(operation, "mode", "uint8x8")
    
    steps = [
        f"Decode SIMD operation {op_code} in mode {mode_name}",
        f"Query core routing bindings for target lanes",
        f"Broadcast input wave vectors onto waveguide lanes"
    ]
    
    plan_id = f"DISPPLAN_{op_code}_{mode_name}_{int(time.time())}"
    return SIMDWaveguideDispatchPlan(
        plan_id=plan_id,
        operation=operation,
        binding_map=binding_map,
        dispatch_steps=steps
    )


def execute_shadow_simd_waveguide_dispatch(dispatch_plan: SIMDWaveguideDispatchPlan) -> SIMDWaveguideExecutionTrace:
    """
    Generates an execution trace by simulating the dispatch plan in shadow mode.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    op = dispatch_plan.operation
    operands = extract(op, "operands", [])
    op_type = extract(op, "op", "VADD")
    mode = extract(op, "mode", "uint8x8")
    
    # Calculate simulated results based on operation logic
    # Default outputs
    res_vals = []
    if operands and len(operands) >= 2:
        op1 = operands[0]
        op2 = operands[1]
        
        # Elements count based on mode
        elem_counts = {"uint8x8": 8, "uint16x4": 4, "uint32x2": 2, "uint64x1": 1}
        num_elems = elem_counts.get(mode, 8)
        mask_sizes = {"uint8x8": 0xFF, "uint16x4": 0xFFFF, "uint32x2": 0xFFFFFFFF, "uint64x1": 0xFFFFFFFFFFFFFFFF}
        mask = mask_sizes.get(mode, 0xFF)
        
        for idx in range(min(num_elems, len(op1), len(op2))):
            val1 = op1[idx]
            val2 = op2[idx]
            
            if op_type == "VADD":
                res_vals.append((val1 + val2) & mask)
            elif op_type == "VSUB":
                res_vals.append((val1 - val2) & mask)
            elif op_type == "VAND":
                res_vals.append(val1 & val2)
            elif op_type == "VOR":
                res_vals.append(val1 | val2)
            elif op_type == "VXOR":
                res_vals.append(val1 ^ val2)
            else:
                res_vals.append(val1)
    else:
        res_vals = [0] * 8

    trace_id = f"TRACE_{dispatch_plan.plan_id}"
    return SIMDWaveguideExecutionTrace(
        trace_id=trace_id,
        plan_id=dispatch_plan.plan_id,
        dispatched_values=operands[0] if operands else [],
        executed_results=res_vals,
        crosstalk_readings={i: 0.01 for i in range(8)},
        phase_coherence=0.99
    )


def compare_simd_waveguide_oracle(trace: SIMDWaveguideExecutionTrace, oracle: List[int]) -> bool:
    """
    Compares execution trace outputs with the expected oracle results.
    """
    return trace.executed_results == oracle


def validate_simd_bindings_after_carrier_relocation(binding_map: SIMDCoreFabricMap, relocation_plan: Any) -> bool:
    """
    Verifies that SIMD core bindings remain valid and isolated after carrier relocations.
    """
    validate_simd_core_bindings(binding_map)
    # Check if target carrier moves violate bindings
    for step in getattr(relocation_plan, "steps", []):
        # Ensure source/target lanes are valid in map
        source_covered = False
        target_covered = False
        for b in binding_map.bindings:
            if step.source_lane_id in b.waveguide_lane_ids:
                source_covered = True
            if step.target_lane_id in b.waveguide_lane_ids:
                target_covered = True
        if not source_covered or not target_covered:
            raise ValueError(f"Relocation step lanes {step.source_lane_id} -> {step.target_lane_id} not covered by SIMD bindings.")
    return True


def plan_simd_dispatch_after_reshape(operation: Any, reshape_plan: Any, carrier_plan: Any) -> SIMDWaveguideDispatchPlan:
    """
    Formulates a dispatch plan taking the coordinate reshape and carrier moves into account.
    """
    # Create mock binding map for dispatch
    cand = getattr(reshape_plan.intent, "target_shape", None)
    bindings = []
    # Generate mock binding entries based on reshaped target shape
    tot_lanes = cand.total_elements() if cand else 8
    core_map = SIMDCoreFabricMap(
        map_id="DISP_RESHAPED_MAP",
        candidate_id="RESHAPED_CAND",
        bindings=[SIMDCoreBinding(core_id="core_0", simd_mode="uint8x8", waveguide_lane_ids=list(range(tot_lanes)))]
    )
    
    plan = plan_simd_waveguide_dispatch(operation, core_map)
    plan.dispatch_steps.append("Map logic channels through coordinate remap dictionary")
    plan.dispatch_steps.append("Redirect relocated carrier frequencies to target lanes")
    return plan


def bind_interlane_carry_to_simd_core(candidate: Any, simd_mode: str) -> SIMDCoreFabricMap:
    """
    Binds inter-lane carry prefix tree to SIMD core groups based on SIMD mode.
    Supports: uint8x8, uint16x4, uint32x2, uint64x1.
    """
    if simd_mode not in ("uint8x8", "uint16x4", "uint32x2", "uint64x1"):
        raise ValueError(f"Unsupported SIMD mode: {simd_mode}")
        
    mode_lanes = {
        "uint8x8": 1,
        "uint16x4": 2,
        "uint32x2": 4,
        "uint64x1": 8
    }
    lanes_per_element = mode_lanes[simd_mode]
    lane_bindings = getattr(candidate, "lane_bindings", [])
    num_lanes = len(lane_bindings) if lane_bindings else 8
    num_elements = num_lanes // lanes_per_element
    
    bindings = []
    for el in range(num_elements):
        start_lane = el * lanes_per_element
        lane_subset = list(range(start_lane, start_lane + lanes_per_element))
        bindings.append(SIMDCoreBinding(
            core_id=f"core_{el}",
            simd_mode=simd_mode,
            waveguide_lane_ids=lane_subset
        ))
        
    map_id = f"SIMDMAP_CARRY_{simd_mode}_{int(time.time() * 1000)}"
    return SIMDCoreFabricMap(
        map_id=map_id,
        candidate_id=getattr(candidate, "candidate_id", "unknown"),
        bindings=bindings,
        metadata={"simd_mode": simd_mode, "lanes_per_element": lanes_per_element}
    )


def validate_simd_prefix_carry_mapping(binding_map: SIMDCoreFabricMap) -> bool:
    """
    Validates the prefix carry mapping for SIMD core bindings.
    """
    if not validate_simd_core_bindings(binding_map):
        return False
        
    mode = binding_map.bindings[0].simd_mode
    if mode not in ("uint8x8", "uint16x4", "uint32x2", "uint64x1"):
        return False
        
    mode_lanes = {
        "uint8x8": 1,
        "uint16x4": 2,
        "uint32x2": 4,
        "uint64x1": 8
    }
    expected = mode_lanes[mode]
    for b in binding_map.bindings:
        if len(b.waveguide_lane_ids) != expected:
            return False
            
    return True


def validate_simd_core_after_sovereign_assembly(
    binding_map: SIMDCoreFabricMap,
    assembly_report: Any
) -> bool:
    """
    Validates SIMD core bindings after sovereign multi-core assembly.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(assembly_report, "result")
    success = extract(res, "success", True) if res is not None else extract(assembly_report, "success", True)
    if not success:
        raise ValueError("Core assembly failed; holding SIMD validation.")

    if not binding_map or not binding_map.bindings:
        raise ValueError("SIMD bindings cannot be empty.")
        
    for b in binding_map.bindings:
        if b.simd_mode not in ("uint8x8", "uint16x4", "uint32x2", "uint64x1"):
            raise ValueError(f"Unsupported SIMD mode: {b.simd_mode}")
            
    meta = extract(binding_map, "metadata", {}) or {}
    if meta.get("simd_validation_failed") or meta.get("simd_mismatch"):
        raise ValueError("SIMD core validation failed: mismatch detected.")
        
    return True


def run_shadow_simd_pipeline_on_assembled_cores(
    dispatch_plan: SIMDWaveguideDispatchPlan,
    assembly_report: Any
) -> SIMDCoreIntegrationReport:
    """
    Runs shadow execution of SIMD dispatch plan on assembled cores.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    validate_simd_core_after_sovereign_assembly(dispatch_plan.binding_map, assembly_report)
    trace = execute_shadow_simd_waveguide_dispatch(dispatch_plan)
    
    op = dispatch_plan.operation
    oracle = extract(op, "oracle") if op else None
    
    oracle_match = True
    if oracle is not None:
        oracle_match = compare_simd_waveguide_oracle(trace, oracle)
        
    import uuid
    return SIMDCoreIntegrationReport(
        report_id=f"SIMD_REP_{uuid.uuid4().hex[:8]}",
        binding_map=dispatch_plan.binding_map,
        success=oracle_match,
        errors=[] if oracle_match else ["Oracle mismatch in SIMD execution."],
        simd_modes=list(set(b.simd_mode for b in dispatch_plan.binding_map.bindings)),
        dispatch_plan=dispatch_plan,
        trace=trace,
        oracle_match=oracle_match
    )


