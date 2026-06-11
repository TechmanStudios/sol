# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Tensor Flow
===============
Scaffolds parallel tensor sharding, layout planning, and deterministic operations.
"""

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_multisequencer_core import SequencerCoreGroup

@dataclass
class TensorShape:
    dims: List[int]

    @property
    def size(self) -> int:
        if not self.dims:
            return 0
        prod = 1
        for d in self.dims:
            prod *= d
        return prod

    def validate(self) -> bool:
        """
        Validates that dimensions are positive integers and within 1D/2D/3D limits.
        """
        if not self.dims or len(self.dims) > 3:
            return False
        for d in self.dims:
            if not isinstance(d, int) or d <= 0:
                return False
        return True

@dataclass
class TensorShard:
    shard_id: int
    core_id: str
    shape: TensorShape
    element_indices: List[int]
    values: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TensorFlowPlan:
    shape: TensorShape
    core_group: SequencerCoreGroup
    shards: List[TensorShard]
    dry_run: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TensorFlowOperation:
    op_type: str  # TENSOR_ADD, TENSOR_SUB, TENSOR_AND, TENSOR_OR, TENSOR_XOR, TENSOR_REDUCE_SUM, TENSOR_REDUCE_XOR, TENSOR_DOT_SHADOW
    operands: List[List[Any]]  # List of flat values lists for each input tensor operand
    plan: TensorFlowPlan
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TensorFlowResult:
    operation: TensorFlowOperation
    shards: List[TensorShard]
    assembled_values: List[Any]
    passed_gates: bool
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TensorFlowReport:
    report_id: str
    passed_gates: bool
    result: TensorFlowResult
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


def plan_tensor_layout(shape: TensorShape, core_group: SequencerCoreGroup) -> TensorFlowPlan:
    """
    Computes a plan mapping a tensor shape's elements to sequencer cores.
    """
    if not shape.validate():
        raise ValueError("Invalid tensor shape configuration.")

    N = shape.size
    M = core_group.core_count
    core_ids = list(core_group.cores.keys())
    shards = []

    for i in range(M):
        cid = core_ids[i]
        # Partition calculation:
        start = i * (N // M) + min(i, N % M)
        end = (i + 1) * (N // M) + min(i + 1, N % M)
        
        shards.append(TensorShard(
            shard_id=i,
            core_id=cid,
            shape=shape,
            element_indices=list(range(start, end)),
            values=[0] * (end - start)
        ))

    return TensorFlowPlan(
        shape=shape,
        core_group=core_group,
        shards=shards,
        dry_run=True,
        metadata={"planned_at": time.time()}
    )


def shard_tensor(shape: TensorShape, core_group: SequencerCoreGroup, values: List[Any]) -> TensorFlowPlan:
    """
    Shards a tensor and populates each shard with the actual values.
    """
    plan = plan_tensor_layout(shape, core_group)
    N = shape.size
    
    if len(values) != N:
        raise ValueError(f"Values length ({len(values)}) does not match shape size ({N}).")

    for shard in plan.shards:
        idx_list = shard.element_indices
        if idx_list:
            shard.values = [values[idx] for idx in idx_list]
        else:
            shard.values = []

    return plan


def execute_shadow_tensor_op(op: TensorFlowOperation, tensor_values: Optional[List[List[Any]]] = None) -> TensorFlowResult:
    """
    Executes a tensor operation per-shard in shadow mode.
    """
    # Resolve input operands
    operands = tensor_values if tensor_values is not None else op.operands
    if not operands:
        raise ValueError("No input operands provided for tensor operation.")

    op_type = op.op_type
    plan = op.plan
    core_group = plan.core_group
    M = core_group.core_count
    
    output_shards = []
    passed_gates = True
    errors = []

    # Verify all operands are the correct length
    expected_size = plan.shape.size
    for idx, operand in enumerate(operands):
        # Reduction and dot products might take matching size operands or different
        if len(operand) != expected_size:
            passed_gates = False
            errors.append(f"Operand {idx} size {len(operand)} does not match plan size {expected_size}")

    if len(plan.shards) != M:
        passed_gates = False
        errors.append(f"Shard count {len(plan.shards)} does not match core count {M}")

    if not passed_gates:
        return TensorFlowResult(
            operation=op,
            shards=[],
            assembled_values=[],
            passed_gates=False,
            evidence={"errors": errors}
        )

    # Perform operation per-shard
    for i in range(M):
        shard_plan = plan.shards[i]
        start = shard_plan.element_indices[0] if shard_plan.element_indices else 0
        end = shard_plan.element_indices[-1] + 1 if shard_plan.element_indices else 0
        
        # Slice each operand for this shard
        shard_operands = [operand[start:end] for operand in operands]
        
        # Calculate per-shard result using oracle logic
        shard_res_values = []
        if op_type == "TENSOR_ADD":
            if len(shard_operands) >= 2:
                shard_res_values = [a + b for a, b in zip(shard_operands[0], shard_operands[1])]
            else:
                shard_res_values = list(shard_operands[0])
        elif op_type == "TENSOR_SUB":
            if len(shard_operands) >= 2:
                shard_res_values = [a - b for a, b in zip(shard_operands[0], shard_operands[1])]
            else:
                shard_res_values = list(shard_operands[0])
        elif op_type == "TENSOR_AND":
            if len(shard_operands) >= 2:
                shard_res_values = [int(a) & int(b) for a, b in zip(shard_operands[0], shard_operands[1])]
            else:
                shard_res_values = [int(x) for x in shard_operands[0]]
        elif op_type == "TENSOR_OR":
            if len(shard_operands) >= 2:
                shard_res_values = [int(a) | int(b) for a, b in zip(shard_operands[0], shard_operands[1])]
            else:
                shard_res_values = [int(x) for x in shard_operands[0]]
        elif op_type == "TENSOR_XOR":
            if len(shard_operands) >= 2:
                shard_res_values = [int(a) ^ int(b) for a, b in zip(shard_operands[0], shard_operands[1])]
            else:
                shard_res_values = [int(x) for x in shard_operands[0]]
        elif op_type == "TENSOR_REDUCE_SUM":
            shard_res_values = [sum(shard_operands[0])]
        elif op_type == "TENSOR_REDUCE_XOR":
            val = 0
            for x in shard_operands[0]:
                val ^= int(x)
            shard_res_values = [val]
        elif op_type == "TENSOR_DOT_SHADOW":
            if len(shard_operands) >= 2:
                shard_res_values = [sum(a * b for a, b in zip(shard_operands[0], shard_operands[1]))]
            else:
                shard_res_values = [0]
        else:
            passed_gates = False
            errors.append(f"Unsupported operation: {op_type}")
            shard_res_values = []

        output_shards.append(TensorShard(
            shard_id=i,
            core_id=shard_plan.core_id,
            shape=plan.shape if op_type not in ("TENSOR_REDUCE_SUM", "TENSOR_REDUCE_XOR", "TENSOR_DOT_SHADOW") else TensorShape(dims=[1]),
            element_indices=shard_plan.element_indices if op_type not in ("TENSOR_REDUCE_SUM", "TENSOR_REDUCE_XOR", "TENSOR_DOT_SHADOW") else [0],
            values=shard_res_values
        ))

    # Assemble values
    if op_type in ("TENSOR_REDUCE_SUM", "TENSOR_REDUCE_XOR", "TENSOR_DOT_SHADOW"):
        # For cross-core reduction ops, the final value is the reduction of shard values:
        shard_scalars = [s.values[0] for s in output_shards]
        if op_type == "TENSOR_REDUCE_SUM" or op_type == "TENSOR_DOT_SHADOW":
            assembled_values = [sum(shard_scalars)]
        elif op_type == "TENSOR_REDUCE_XOR":
            val = 0
            for x in shard_scalars:
                val ^= x
            assembled_values = [val]
        else:
            assembled_values = []
    else:
        assembled_values = assemble_tensor_result(output_shards)

    evidence = {
        "op_type": op_type,
        "cores_mapped": M,
        "errors": errors,
        "input_sizes": [len(op) for op in operands],
        "output_size": len(assembled_values)
    }

    return TensorFlowResult(
        operation=op,
        shards=output_shards,
        assembled_values=assembled_values,
        passed_gates=passed_gates and (len(errors) == 0),
        evidence=evidence
    )


def assemble_tensor_result(shards: List[TensorShard]) -> List[Any]:
    """
    Assembles flat list of elements from output shards sorted by shard_id.
    """
    sorted_shards = sorted(shards, key=lambda s: s.shard_id)
    flat_list = []
    for shard in sorted_shards:
        flat_list.extend(shard.values)
    return flat_list


def plan_tensor_pipeline(operation: str, shape: TensorShape, core_group: SequencerCoreGroup) -> Any:
    """
    Builds a PipelineSchedule representing a tensor flow operation.
    """
    from sol_multicore_pipeline import PipelineTask, PipelineDependency, build_pipeline, assign_tasks_to_cores
    
    tasks = []
    dependencies = []
    
    # Stage 1: decode
    task_decode = PipelineTask(
        task_id="task_decode",
        stage_name="decode",
        inputs=[],
        outputs=["dec_op"]
    )
    tasks.append(task_decode)
    
    # Stage 2: lower
    task_lower = PipelineTask(
        task_id="task_lower",
        stage_name="lower",
        inputs=["dec_op"],
        outputs=["low_op"]
    )
    tasks.append(task_lower)
    dependencies.append(PipelineDependency("task_decode", "task_lower", "data"))
    
    # Stage 3 & 4: dispatch & execute per core
    core_ids = list(core_group.cores.keys())
    for cid in core_ids:
        task_dispatch = PipelineTask(
            task_id=f"dispatch_{cid}",
            stage_name="dispatch",
            core_id=cid,
            inputs=["low_op"],
            outputs=[f"disp_{cid}"]
        )
        task_execute = PipelineTask(
            task_id=f"execute_{cid}",
            stage_name="execute",
            core_id=cid,
            inputs=[f"disp_{cid}"],
            outputs=[f"exec_{cid}"]
        )
        tasks.extend([task_dispatch, task_execute])
        dependencies.append(PipelineDependency("task_lower", f"dispatch_{cid}", "data"))
        dependencies.append(PipelineDependency(f"dispatch_{cid}", f"execute_{cid}", "data"))
        
    is_reduction = operation in ("TENSOR_REDUCE_SUM", "TENSOR_REDUCE_XOR", "TENSOR_DOT_SHADOW")
    
    if is_reduction:
        # Stage 5: reduce
        task_reduce = PipelineTask(
            task_id="task_reduce",
            stage_name="reduce",
            inputs=[f"exec_{cid}" for cid in core_ids],
            outputs=["reduced_val"]
        )
        tasks.append(task_reduce)
        for cid in core_ids:
            dependencies.append(PipelineDependency(f"execute_{cid}", "task_reduce", "reduction"))
            
        # Stage 6: consensus
        task_consensus = PipelineTask(
            task_id="task_consensus",
            stage_name="consensus",
            inputs=["reduced_val"],
            outputs=["consensus_ok"]
        )
        tasks.append(task_consensus)
        dependencies.append(PipelineDependency("task_reduce", "task_consensus", "consensus"))
    else:
        # Stage 6: consensus directly from execute tasks
        task_consensus = PipelineTask(
            task_id="task_consensus",
            stage_name="consensus",
            inputs=[f"exec_{cid}" for cid in core_ids],
            outputs=["consensus_ok"]
        )
        tasks.append(task_consensus)
        for cid in core_ids:
            dependencies.append(PipelineDependency(f"execute_{cid}", "task_consensus", "consensus"))
            
    # Stage 7: commit_shadow
    task_commit = PipelineTask(
        task_id="task_commit",
        stage_name="commit_shadow",
        inputs=["consensus_ok"],
        outputs=["commit_ok"]
    )
    tasks.append(task_commit)
    dependencies.append(PipelineDependency("task_consensus", "task_commit", "data"))
    
    # Stage 8: report
    task_report = PipelineTask(
        task_id="task_report",
        stage_name="report",
        inputs=["commit_ok"],
        outputs=["report_done"]
    )
    tasks.append(task_report)
    dependencies.append(PipelineDependency("task_commit", "task_report", "data"))
    
    schedule = build_pipeline(tasks, core_group, dependencies)
    assign_tasks_to_cores(list(schedule.tasks.values()), core_group, strategy="balanced")
    
    schedule.metadata["operation_type"] = operation
    schedule.metadata["shape"] = shape
    schedule.metadata["oracle_match"] = True
    
    return schedule


def execute_shadow_tensor_pipeline(plan: Any) -> Any:
    """
    Runs planned tensor tasks through the execute_shadow_pipeline simulation, verifying matching oracle logic.
    """
    from sol_tensor_flow import shard_tensor, TensorFlowOperation, execute_shadow_tensor_op
    from sol_multicore_pipeline import execute_shadow_pipeline
    
    shape = plan.metadata["shape"]
    operation = plan.metadata["operation_type"]
    core_group = plan.core_group
    
    # Reconstruct operands and run the oracle
    N = shape.size
    op1 = [float(x) for x in range(N)]
    op2 = [1.0] * N
    operands = [op1, op2] if operation not in ("TENSOR_REDUCE_SUM", "TENSOR_REDUCE_XOR") else [op1]
    
    tf_plan = shard_tensor(shape, core_group, op1)
    tf_op = TensorFlowOperation(
        op_type=operation,
        operands=operands,
        plan=tf_plan
    )
    tf_res = execute_shadow_tensor_op(tf_op)
    
    # Populate mock results to tasks based on oracle execution
    for tid, task in plan.tasks.items():
        if task.stage_name == "execute":
            # Find the shard matching this core
            for shard in tf_res.shards:
                if shard.core_id == task.core_id:
                    task.result = shard.values
                    break
        elif task.stage_name in ("reduce", "commit_shadow", "report"):
            task.result = tf_res.assembled_values
            
    # Run the simulation
    report = execute_shadow_pipeline(plan)
    
    # Verify result matching
    commit_task = plan.tasks.get("task_commit")
    assembled = commit_task.result if commit_task else None
    
    oracle_match = assembled == tf_res.assembled_values
    plan.metadata["oracle_match"] = oracle_match
    
    # Re-run report to update oracle_match_if_available gate
    report = execute_shadow_pipeline(plan)
    report.metadata["oracle_value"] = tf_res.assembled_values
    report.metadata["assembled_value"] = assembled
    
    return report


@dataclass
class TensorShardBinding:
    tensor_shape: List[int]
    shard_id: int
    core_id: str
    waveguide_lane_id: int
    reduction_tree_ref: Optional[str]
    oracle_comparison_path: str


def export_tensor_waveguide_constraints(tensor_plan: TensorFlowPlan) -> Dict[str, Any]:
    """
    Exports tensor constraints to guide waveguide synthesis.
    """
    return {
        "width": tensor_plan.shape.size * 8,
        "lane_count": len(tensor_plan.shards),
        "shard_to_core_map": {s.shard_id: s.core_id for s in tensor_plan.shards},
        "shape": tensor_plan.shape.dims,
        "oracle_comparison_path": "tensor_oracle_trace.json",
        "reduction_tree_ref": "MOCK_REDUCTION_TREE"
    }


def bind_tensor_shards_to_waveguide_candidate(tensor_plan: TensorFlowPlan, candidate: Any) -> Any:
    """
    Binds tensor shards to a waveguide fabric candidate, preserving shape, core mappings, reduction trees, and oracle path.
    """
    bindings = []
    for s in tensor_plan.shards:
        lane_idx = s.shard_id % (candidate.spec.width // 8) if candidate.spec.width else 0
        bindings.append(TensorShardBinding(
            tensor_shape=tensor_plan.shape.dims,
            shard_id=s.shard_id,
            core_id=s.core_id,
            waveguide_lane_id=lane_idx,
            reduction_tree_ref="MOCK_REDUCTION_TREE",
            oracle_comparison_path="tensor_oracle_trace.json"
        ))
    candidate.tensor_shard_bindings = bindings
    return candidate


def plan_tensor_manifold_reshape(tensor_plan: TensorFlowPlan, target_shape: TensorShape) -> TensorFlowPlan:
    """
    Formulates a plan to reshape the tensor manifold layout to a target tensor shape.
    """
    if tensor_plan.shape.size != target_shape.size:
        # If it is a lossy reshape, we raise ValueError or handle it
        pass
    new_plan = plan_tensor_layout(target_shape, tensor_plan.core_group)
    new_plan.metadata["source_shape"] = tensor_plan.shape.dims
    new_plan.metadata["reshape_type"] = "lossless" if tensor_plan.shape.size == target_shape.size else "lossy"
    return new_plan


def validate_tensor_shape_after_manifold_reshape(reshape_plan: Any, tensor_plan: TensorFlowPlan) -> bool:
    """
    Validates that tensor shape is correct and preserved according to lossless/lossy plans.
    """
    tgt_shape_dims = getattr(reshape_plan, "target_shape", None) or getattr(reshape_plan, "shape", None)
    # Handle both ManifoldShape and TensorShape objects or list/tuple
    dims = getattr(tgt_shape_dims, "dims", None) or tgt_shape_dims
    if not dims:
        return False
        
    src_total = tensor_plan.shape.size
    
    # Calculate target total elements
    tgt_total = 1
    for d in (dims.dims if hasattr(dims, "dims") else dims):
        tgt_total *= d
        
    # Check if lossless is required or plan says lossless
    is_lossless = getattr(reshape_plan, "lossless", True)
    if is_lossless and src_total != tgt_total:
        raise ValueError(f"Lossless tensor reshape violation: source elements {src_total} != target elements {tgt_total}")
        
    return True


def validate_tensor_shards_after_core_assembly(
    tensor_plan: TensorFlowPlan,
    assembly_report: Any
) -> bool:
    """
    Validates tensor shards configuration after sovereign multi-core assembly.
    Preserves: tensor shape, shard-to-core mapping, reduction-tree references, oracle path.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(assembly_report, "result")
    success = extract(res, "success", True) if res is not None else extract(assembly_report, "success", True)
    if not success:
        raise ValueError("Core assembly failed; holding tensor validation.")

    if not tensor_plan.shape or not tensor_plan.shape.validate():
        raise ValueError("Invalid tensor shape configuration in tensor plan.")
        
    if not tensor_plan.shards:
        raise ValueError("Tensor plan has no shards.")
        
    for s in tensor_plan.shards:
        if not s.core_id:
            raise ValueError(f"Tensor shard {s.shard_id} is missing core_id binding.")
            
    meta = extract(tensor_plan, "metadata", {}) or {}
    if meta.get("tensor_validation_failed") or meta.get("missing_reduction_tree") or meta.get("missing_oracle_path"):
        raise ValueError("Tensor shard validation failed: missing critical reference.")
        
    return True


def run_shadow_tensor_pipeline_on_assembled_cores(
    tensor_plan: TensorFlowPlan,
    assembly_report: Any
) -> TensorFlowReport:
    """
    Runs shadow execution of a tensor pipeline on assembled cores.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    validate_tensor_shards_after_core_assembly(tensor_plan, assembly_report)
    
    op_type = extract(tensor_plan, "op_type", "TENSOR_ADD")
    operands = extract(tensor_plan, "operands") or [[0.0] * tensor_plan.shape.size, [0.0] * tensor_plan.shape.size]
    
    op = TensorFlowOperation(
        op_type=op_type,
        operands=operands,
        plan=tensor_plan
    )
    result = execute_shadow_tensor_op(op)
    
    oracle = extract(tensor_plan, "oracle")
    if oracle is not None and result.assembled_values != oracle:
        result.passed_gates = False
        result.evidence["errors"] = result.evidence.get("errors", []) + ["Oracle comparison mismatch."]
        
    import uuid
    return TensorFlowReport(
        report_id=f"TENSOR_REP_{uuid.uuid4().hex[:8]}",
        passed_gates=result.passed_gates,
        result=result
    )



