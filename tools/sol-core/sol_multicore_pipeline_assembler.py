# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Multi-Core Pipeline Assembler
=================================
Binds logical execution pipeline stages, lanes, and waveguides to physical core assemblies.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class PipelineAssemblyIntent:
    intent_id: str
    sequence: Any
    runtime: Any
    core_assembly: Any
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineAssemblyStageBinding:
    stage_name: str
    core_id: str
    active: bool = True

@dataclass
class PipelineAssemblyLaneBinding:
    lane_id: int
    waveguide_segment_id: str

@dataclass
class PipelineAssemblyCoreBinding:
    core_id: str
    cluster_id: str

@dataclass
class PipelineAssemblyPlan:
    plan_id: str
    intent: PipelineAssemblyIntent
    stage_bindings: List[PipelineAssemblyStageBinding]
    lane_bindings: List[PipelineAssemblyLaneBinding]
    core_bindings: List[PipelineAssemblyCoreBinding]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineAssemblyResult:
    success: bool
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineAssemblyReport:
    report_id: str
    plan: PipelineAssemblyPlan
    result: PipelineAssemblyResult
    timestamp: float = field(default_factory=time.time)


def build_pipeline_assembly_intent(
    sequence: Any,
    runtime: Any,
    core_assembly: Any
) -> PipelineAssemblyIntent:
    """
    Constructs a pipeline assembly intent.
    """
    return PipelineAssemblyIntent(
        intent_id=f"INT_ASM_{uuid.uuid4().hex[:8]}",
        sequence=sequence,
        runtime=runtime,
        core_assembly=core_assembly
    )


def bind_pipeline_stages_to_cores(
    intent: PipelineAssemblyIntent
) -> List[PipelineAssemblyStageBinding]:
    """
    Maps pipeline stages to core units.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    cores = []
    plan = extract(intent, "core_assembly", {})
    if plan:
        clusters = extract(plan, "clusters", [])
        for c in clusters:
            for u in extract(c, "cores", []):
                cores.append(extract(u, "core_id"))

    if not cores:
        cores = ["core_0", "core_1"]

    required_stages = [
        "decode", "lower", "dispatch", "execute",
        "reduce", "consensus", "commit_shadow", "report"
    ]
    
    # Check if simulate missing stage binding is requested
    meta = extract(intent, "metadata", {}) or {}
    simulate_missing = meta.get("simulate_missing_stage") or (isinstance(intent.sequence, dict) and intent.sequence.get("simulate_missing_stage"))
    if simulate_missing:
        # omit "consensus" stage to simulate missing stage binding failure
        required_stages.remove("consensus")

    bindings = []
    for idx, stage in enumerate(required_stages):
        core_id = cores[idx % len(cores)]
        bindings.append(PipelineAssemblyStageBinding(
            stage_name=stage,
            core_id=core_id
        ))
    return bindings


def bind_pipeline_lanes_to_waveguides(
    intent: PipelineAssemblyIntent
) -> List[PipelineAssemblyLaneBinding]:
    """
    Binds data lanes to waveguide segments.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    bindings = []
    # Fetch waveguide candidate lanes
    fabric = extract(intent, "core_assembly", {})
    metadata = extract(fabric, "metadata", {}) or {}
    
    num_lanes = metadata.get("lane_count", 8) or 8
    for i in range(num_lanes):
        bindings.append(PipelineAssemblyLaneBinding(
            lane_id=i,
            waveguide_segment_id=f"WG_SEG_{i}"
        ))
    return bindings


def validate_pipeline_assembly_plan(
    plan: PipelineAssemblyPlan
) -> bool:
    """
    Ensures all 8 required stages are bound and valid.
    """
    required_stages = {
        "decode", "lower", "dispatch", "execute",
        "reduce", "consensus", "commit_shadow", "report"
    }
    
    bound_stages = {b.stage_name for b in plan.stage_bindings}
    missing = required_stages - bound_stages
    if missing:
        raise ValueError(f"Missing stage binding rejects pipeline assembly: {missing}")

    # Check lane coverage
    if not plan.lane_bindings:
        raise ValueError("Lane bindings cannot be empty.")

    return True


def execute_shadow_pipeline_assembly(
    plan: PipelineAssemblyPlan
) -> PipelineAssemblyReport:
    """
    Executes multi-core pipeline assembly mapping in shadow mode.
    """
    errors = []
    try:
        validate_pipeline_assembly_plan(plan)
    except ValueError as e:
        errors.append(str(e))

    success = len(errors) == 0
    result = PipelineAssemblyResult(
        success=success,
        errors=errors
    )
    return PipelineAssemblyReport(
        report_id=f"ASM_REP_{uuid.uuid4().hex[:8]}",
        plan=plan,
        result=result
    )
