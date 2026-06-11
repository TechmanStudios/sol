# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Multi-Sequencer Core Coordination
=====================================
Manages parallel multi-core WideWord instructions, grouping sequencer cores,
and assigning lane fabrics.
"""

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_lane_fabric import LaneFabric

@dataclass
class SequencerCoreId:
    core_id: str

    def __post_init__(self):
        if not isinstance(self.core_id, str):
            self.core_id = str(self.core_id)

@dataclass
class SequencerCoreState:
    core_id: SequencerCoreId
    lane_fabric: Optional[LaneFabric] = None
    instructions: List[Any] = field(default_factory=list)
    execution_history: List[Any] = field(default_factory=list)
    status: str = "idle"
    work_queue: List[Any] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SequencerCoreGroup:
    cores: Dict[str, SequencerCoreState]
    width: int = 64
    core_count: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiSequencerExecutionPlan:
    core_group: SequencerCoreGroup
    instructions: List[Any]
    core_instruction_mapping: Dict[str, List[Any]]
    dry_run: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiSequencerExecutionResult:
    plan: MultiSequencerExecutionPlan
    core_results: Dict[str, List[Any]]
    passed_gates: bool
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiSequencerReport:
    report_id: str
    passed_gates: bool
    execution_result: MultiSequencerExecutionResult
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_sequencer_core_group(core_count: int, width: int = 64) -> SequencerCoreGroup:
    """
    Builds a group of 2, 4, or 8 sequencer cores.
    """
    if core_count not in (2, 4, 8):
        raise ValueError(f"Unsupported core count: {core_count}. Only 2, 4, and 8 cores are supported.")

    cores = {}
    for i in range(core_count):
        core_id_str = f"core_{i}"
        core_id = SequencerCoreId(core_id_str)
        # Create core state with an unassigned lane fabric initially,
        # or we can assign a default one that can be overridden.
        # Let's assign default fabric so it is ready, but allow assignment override.
        fabric = LaneFabric.for_width(width)
        cores[core_id_str] = SequencerCoreState(
            core_id=core_id,
            lane_fabric=fabric,
            status="idle"
        )

    return SequencerCoreGroup(
        cores=cores,
        width=width,
        core_count=core_count,
        metadata={"created_at": time.time()}
    )


def assign_fabric_to_core(core_id: Any, lane_fabric: Any, core_group: Optional[SequencerCoreGroup] = None) -> Any:
    """
    Binds a lane fabric to a core state. If core_group is provided, binds within the group.
    """
    target_id = core_id.core_id if hasattr(core_id, "core_id") else str(core_id)
    
    if core_group is not None:
        if target_id in core_group.cores:
            core_group.cores[target_id].lane_fabric = lane_fabric
        return core_group

    if isinstance(core_id, SequencerCoreState):
        core_id.lane_fabric = lane_fabric
        return core_id

    # Fallback return none if no context is provided
    return None


def plan_parallel_execution(instructions: List[Any], core_group: SequencerCoreGroup) -> MultiSequencerExecutionPlan:
    """
    Maps list of instructions across cores in the group in a round-robin format.
    """
    core_ids = list(core_group.cores.keys())
    mapping = {cid: [] for cid in core_ids}

    for idx, inst in enumerate(instructions):
        cid = core_ids[idx % len(core_ids)]
        mapping[cid].append(inst)

    return MultiSequencerExecutionPlan(
        core_group=core_group,
        instructions=instructions,
        core_instruction_mapping=mapping,
        dry_run=True,
        metadata={"planned_at": time.time()}
    )


def execute_shadow_parallel_plan(plan: MultiSequencerExecutionPlan) -> MultiSequencerExecutionResult:
    """
    Executes a parallel execution plan in shadow mode.
    """
    core_results = {}
    passed_gates = True
    errors = []
    
    # 1. Verification of assigned fabrics
    for cid, core in plan.core_group.cores.items():
        if core.lane_fabric is None:
            passed_gates = False
            errors.append(f"Core {cid} has no assigned lane fabric.")

    # 2. Execute instructions for each core
    for cid, insts in plan.core_instruction_mapping.items():
        core_state = plan.core_group.cores.get(cid)
        results = []
        if core_state is not None:
            core_state.status = "active"
            for inst in insts:
                # Get op and values
                op = getattr(inst, "op", "add").lower()
                a = getattr(inst, "a", 0)
                b = getattr(inst, "b", 0)
                
                # Execute in shadow mode using fabric if available
                res_val = 0
                if core_state.lane_fabric is not None:
                    try:
                        if op == "add":
                            res_obj = core_state.lane_fabric.add_word(a, b)
                            res_val = res_obj.result
                        elif op == "sub":
                            res_obj = core_state.lane_fabric.sub_word(a, b)
                            res_val = res_obj.result
                        elif op == "and":
                            res_obj = core_state.lane_fabric.and_word(a, b)
                            res_val = res_obj.result
                        elif op == "or":
                            res_obj = core_state.lane_fabric.or_word(a, b)
                            res_val = res_obj.result
                        elif op == "xor":
                            res_obj = core_state.lane_fabric.xor_word(a, b)
                            res_val = res_obj.result
                        elif op == "not":
                            res_obj = core_state.lane_fabric.not_word(a)
                            res_val = res_obj.result
                        else:
                            # Fallback if unknown op
                            res_val = a + b
                    except Exception as e:
                        errors.append(f"Core {cid} execution error: {str(e)}")
                        passed_gates = False
                else:
                    # Fallback evaluation without fabric
                    if op == "add":
                        res_val = a + b
                    elif op == "sub":
                        res_val = a - b
                    elif op == "xor":
                        res_val = a ^ b
                    
                results.append({
                    "instruction": inst,
                    "result": res_val,
                    "status": "completed",
                    "core_id": cid
                })
                core_state.execution_history.append(inst)
            core_state.status = "completed"
        core_results[cid] = results

    evidence = {
        "total_instructions": len(plan.instructions),
        "errors": errors,
        "cores_executed": list(core_results.keys()),
        "per_core_counts": {cid: len(r) for cid, r in core_results.items()}
    }

    return MultiSequencerExecutionResult(
        plan=plan,
        core_results=core_results,
        passed_gates=passed_gates and (len(errors) == 0),
        evidence=evidence
    )


def summarize_core_group(core_group: SequencerCoreGroup) -> Dict[str, Any]:
    """
    Returns a dictionary summary of the core group configuration and state.
    """
    return {
        "core_count": core_group.core_count,
        "width": core_group.width,
        "cores": {
            cid: {
                "status": core.status,
                "has_fabric": core.lane_fabric is not None,
                "history_length": len(core.execution_history)
            }
            for cid, core in core_group.cores.items()
        }
    }


def core_work_queue(core_id: str, core_group: SequencerCoreGroup) -> List[Any]:
    """
    Returns the task list in the work queue for the given core.
    """
    core_state = core_group.cores.get(core_id)
    if core_state is not None:
        if not hasattr(core_state, "work_queue"):
            core_state.work_queue = []
        return core_state.work_queue
    return []


def dispatch_pipeline_task(task: Any, core_id: str, core_group: SequencerCoreGroup, dry_run: bool = True) -> Any:
    """
    Simulates core dispatch of a pipeline task.
    """
    core_state = core_group.cores.get(core_id)
    if core_state is not None:
        core_state.status = "active"
        if not hasattr(core_state, "work_queue"):
            core_state.work_queue = []
        if not hasattr(core_state, "results"):
            core_state.results = {}
            
        task.status = "running"
        task.core_id = core_id
        
        # Simulate execution logic or store result
        # Save to history & results
        core_state.execution_history.append(task)
        core_state.results[task.task_id] = task.result
        task.status = "completed"
        core_state.status = "completed"
        return task
    return None


def collect_core_pipeline_results(core_group: SequencerCoreGroup) -> Dict[str, Any]:
    """
    Aggregates results from all cores in the group.
    """
    combined = {}
    for cid, core in core_group.cores.items():
        if hasattr(core, "results") and core.results:
            combined.update(core.results)
    return combined


def plan_core_group_rebalance(
    core_group: SequencerCoreGroup,
    placement_map: Any,
    metrics: Any
) -> Dict[str, Any]:
    """
    Creates a plan dictionary to rebalance manifolds and shards across cores in the group.
    """
    return {
        "core_group_reference": core_group,
        "placement_map": placement_map,
        "metrics": metrics,
        "timestamp": time.time()
    }


def execute_shadow_core_rebalance(plan: Any) -> SequencerCoreGroup:
    """
    Applies the placement map from the rebalance plan to a deep copy of the core group.
    """
    import copy
    
    # Extract core group and placement map
    core_group = None
    placement_map = None
    
    if isinstance(plan, dict):
        core_group = plan.get("core_group_reference") or plan.get("core_group")
        placement_map = plan.get("placement_map")
    else:
        core_group = getattr(plan, "core_group_reference", None) or getattr(plan, "core_group", None)
        placement_map = getattr(plan, "placement_map", None)
        
    if core_group is None:
        raise ValueError("Core group reference missing in rebalance plan.")
        
    new_cg = copy.deepcopy(core_group)
    if placement_map is None:
        return new_cg
        
    # Extract mappings
    m_to_c = getattr(placement_map, "manifold_to_core", {}) or {}
    s_to_c = getattr(placement_map, "shard_to_core", {}) or {}
    if isinstance(placement_map, dict):
        m_to_c = placement_map.get("manifold_to_core", {})
        s_to_c = placement_map.get("shard_to_core", {})
        
    # Apply to core states metadata
    for m_id, core_id in m_to_c.items():
        if core_id in new_cg.cores:
            core_state = new_cg.cores[core_id]
            if not hasattr(core_state, "metadata"):
                core_state.metadata = {}
            if "assigned_manifolds" not in core_state.metadata:
                core_state.metadata["assigned_manifolds"] = []
            if m_id not in core_state.metadata["assigned_manifolds"]:
                core_state.metadata["assigned_manifolds"].append(m_id)
                
    for s_id, core_id in s_to_c.items():
        if core_id in new_cg.cores:
            core_state = new_cg.cores[core_id]
            if not hasattr(core_state, "metadata"):
                core_state.metadata = {}
            if "assigned_shards" not in core_state.metadata:
                core_state.metadata["assigned_shards"] = []
            if s_id not in core_state.metadata["assigned_shards"]:
                core_state.metadata["assigned_shards"].append(s_id)
                
    return new_cg

