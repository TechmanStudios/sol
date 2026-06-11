# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Distributed Pipeline Optimizer
==================================
Identifies pipeline bottlenecks, workload imbalances, and suggests rebalances.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib

@dataclass
class PipelineOptimizationPolicy:
    max_rebalance_depth: int = 2
    target_core_load_threshold: float = 3.0
    allow_cross_core_migration: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineOptimizationCandidate:
    candidate_id: str
    target_task_id: str
    current_core_id: str
    recommended_core_id: str
    reducible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineOptimizationPlan:
    plan_id: str
    candidates: List[PipelineOptimizationCandidate]
    policy: PipelineOptimizationPolicy
    schedule_reference: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineOptimizationResult:
    success: bool
    optimized_schedule: Any
    optimized_report: Any
    original_report: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineOptimizationReport:
    optimization_report_id: str
    result: PipelineOptimizationResult
    performance_comparison: Dict[str, Any] = field(default_factory=dict)
    passed_gates: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


def analyze_pipeline_bottlenecks(schedule: Any, trace: Any) -> Dict[str, Any]:
    """
    Identifies cores with backpressure or high loads and returns a bottleneck map.
    """
    # Count tasks per core
    core_tasks = {}
    if hasattr(schedule, "tasks"):
        for task in schedule.tasks.values():
            if task.core_id:
                core_tasks[task.core_id] = core_tasks.get(task.core_id, 0) + 1
            
    # Count stalls per core
    core_stalls = {}
    events = getattr(trace, "events", []) or []
    for event in events:
        if event.get("event") == "task_stall":
            task_id = event.get("task_id")
            if hasattr(schedule, "tasks"):
                task = schedule.tasks.get(task_id)
                if task and task.core_id:
                    core_stalls[task.core_id] = core_stalls.get(task.core_id, 0) + 1
                
    bottlenecks = {}
    for core_id, count in core_tasks.items():
        stalls = core_stalls.get(core_id, 0)
        # Bottleneck if count > 3 or stalls > 0
        if count > 3 or stalls > 0:
            bottlenecks[core_id] = {
                "task_count": count,
                "stall_count": stalls,
                "severity": "high" if count > 4 or stalls > 1 else "medium"
            }
    return bottlenecks


def identify_rebalance_candidates(schedule: Any, trace: Any, policy: PipelineOptimizationPolicy) -> List[PipelineOptimizationCandidate]:
    """
    Finds load-rebalancing candidates for overloaded cores.
    """
    bottlenecks = analyze_pipeline_bottlenecks(schedule, trace)
    candidates = []
    
    if not bottlenecks or not policy.allow_cross_core_migration:
        return candidates
        
    # Find underloaded cores
    core_tasks = {}
    if hasattr(schedule, "tasks"):
        for task in schedule.tasks.values():
            if task.core_id:
                core_tasks[task.core_id] = core_tasks.get(task.core_id, 0) + 1
            
    all_cores = list(schedule.core_group.cores.keys()) if hasattr(schedule, "core_group") and hasattr(schedule.core_group, "cores") else []
    underloaded = [c for c in all_cores if core_tasks.get(c, 0) < policy.target_core_load_threshold]
    
    if not underloaded:
        # Fallback to any core that is not the overloaded core itself
        underloaded = all_cores
        
    if not underloaded:
        return candidates
        
    idx = 0
    candidate_idx = 0
    for core_id, info in bottlenecks.items():
        if info["severity"] in ("high", "medium"):
            # Find tasks on this overloaded core that can be moved
            if hasattr(schedule, "tasks"):
                overloaded_tasks = [t for t in schedule.tasks.values() if t.core_id == core_id]
                # Move some tasks to balance load
                for t in overloaded_tasks[2:]:
                    target_core = underloaded[idx % len(underloaded)]
                    if target_core != core_id:
                        candidates.append(PipelineOptimizationCandidate(
                            candidate_id=f"CAND_{candidate_idx}",
                            target_task_id=t.task_id,
                            current_core_id=core_id,
                            recommended_core_id=target_core,
                            reducible=True,
                            metadata={"new_core_id": target_core}
                        ))
                        candidate_idx += 1
                        idx += 1
                
    return candidates


def build_optimization_plan(candidates: List[PipelineOptimizationCandidate], policy: PipelineOptimizationPolicy) -> PipelineOptimizationPlan:
    """
    Builds a PipelineOptimizationPlan from list of candidates.
    """
    plan_id = f"PLAN_OPT_{int(time.time())}"
    return PipelineOptimizationPlan(
        plan_id=plan_id,
        candidates=candidates,
        policy=policy,
        schedule_reference=None
    )


def execute_shadow_optimization(plan: PipelineOptimizationPlan) -> PipelineOptimizationResult:
    """
    Applies the optimization plan on schedule reference and runs execute_shadow_pipeline.
    """
    from sol_multicore_pipeline import apply_shadow_optimization, execute_shadow_pipeline
    
    schedule = plan.schedule_reference
    original_report = execute_shadow_pipeline(schedule)
    
    # Apply optimizations
    optimized_schedule = apply_shadow_optimization(schedule, plan)
    
    # Run optimized schedule
    optimized_report = execute_shadow_pipeline(optimized_schedule)
    
    success = optimized_report.passed_gates
    return PipelineOptimizationResult(
        success=success,
        optimized_schedule=optimized_schedule,
        optimized_report=optimized_report,
        original_report=original_report
    )


def compare_pipeline_performance(before: Any, after: Any) -> Dict[str, Any]:
    """
    Compares the original and optimized pipeline execution reports.
    """
    before_dur = getattr(before.trace, "task_durations", {}) or {}
    after_dur = getattr(after.trace, "task_durations", {}) or {}
    
    total_before = sum(before_dur.values())
    total_after = sum(after_dur.values())
    
    before_stalls = len([e for e in getattr(before.trace, "events", []) if e.get("event") == "task_stall"])
    after_stalls = len([e for e in getattr(after.trace, "events", []) if e.get("event") == "task_stall"])
    
    return {
        "original_duration": total_before,
        "optimized_duration": total_after,
        "original_stalls": before_stalls,
        "optimized_stalls": after_stalls,
        "speedup": total_before - total_after,
        "improvement_pct": ((total_before - total_after) / total_before * 100.0) if total_before > 0 else 0.0
    }


def recommend_rebalance_from_optimization_report(report: Any) -> List[Any]:
    """
    Analyzes optimization reports to recommend rebalance candidates based on bottlenecks, stalls, etc.
    """
    from sol_shard_rebalancer import RebalanceCandidate
    candidates = []
    
    # Extract performance comparison, trace events, etc.
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    comp = extract(report, "performance_comparison", {}) or {}
    stalls = comp.get("original_stalls", 0)
    
    # If there are stalls or duration improvement indicates hot spots, we recommend rebalancing
    # Let's inspect report results or traces
    res = extract(report, "result")
    if res:
        orig = extract(res, "original_report")
        if orig:
            # Look for tasks and cores with high queue counts or stalls
            trace = extract(orig, "trace")
            events = extract(trace, "events", []) or []
            
            # Count stalls per core
            stalls_per_core = {}
            for e in events:
                if e.get("event") == "task_stall":
                    core = e.get("core_id", "core_0")
                    stalls_per_core[core] = stalls_per_core.get(core, 0) + 1
                    
            for core, count in stalls_per_core.items():
                if count > 0:
                    # Recommend moving some manifold/shard off this core
                    candidates.append(RebalanceCandidate(
                        candidate_id=f"REB_REC_{core}",
                        item_type="manifold",
                        item_id="manifold_0", # default manifold recommendation
                        source_location=core,
                        target_location="core_1" if core == "core_0" else "core_0",
                        estimated_cost=0.4,
                        reducible=True,
                        metadata={"reason": f"Repeated stalls ({count}) detected on core {core}", "source_core": core}
                    ))
                    
    # If no candidates recommended yet but there were stalls, make a default recommendation
    if not candidates and stalls > 0:
        candidates.append(RebalanceCandidate(
            candidate_id="REB_REC_DEFAULT",
            item_type="manifold",
            item_id="manifold_0",
            source_location="core_0",
            target_location="core_1",
            estimated_cost=0.5,
            reducible=True,
            metadata={"reason": "Pipeline stalls detected in optimization report."}
        ))
        
    return candidates


def recommend_pipeline_calibration_from_bottlenecks(report: Any) -> List[Any]:
    """
    Analyzes optimization reports or pipeline reports to recommend calibration.
    """
    from sol_pipeline_calibration import PipelineCalibrationTarget
    import uuid
    
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    targets = []
    
    res = extract(report, "result")
    orig = extract(res, "original_report") or report
    trace = extract(orig, "trace")
    
    events = extract(trace, "events", []) or []
    stalls = len([e for e in events if e.get("event") == "task_stall"])
    
    metadata = extract(report, "metadata", {}) or {}
    if stalls > 0 or metadata.get("high_backpressure") or metadata.get("backpressure_breach"):
        targets.append(PipelineCalibrationTarget(
            target_id=f"TGT_CAL_{uuid.uuid4().hex[:4]}",
            core_id="core_0",
            stage_name="execute",
            expected_latency=0.005
        ))
        
    return targets


def validate_optimization_after_pipeline_calibration(
    optimization_report: Any,
    calibration_report: Any
) -> bool:
    """
    Ensures that optimization does not mutate active state and validates it against calibration report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    cal_res = extract(calibration_report, "result")
    cal_success = extract(cal_res, "success", True) if cal_res is not None else extract(calibration_report, "success", True)
    
    if not cal_success:
        raise ValueError("Pipeline optimization validation failed: calibration report indicates failure.")
        
    opt_meta = extract(optimization_report, "metadata", {}) or {}
    if opt_meta.get("overwrite_active_cadence") or opt_meta.get("overwrite_active_phase_table") or opt_meta.get("overwrite_active_carrier"):
        raise ValueError("Active profile/table overwrite is prohibited.")
        
    if opt_meta.get("stage_latency_breach") or opt_meta.get("backpressure_breach") or opt_meta.get("stall_breach"):
        raise ValueError("Pipeline calibration constraint violated: timing metrics breached.")
        
    # Check for court token sandbox execution
    is_sandbox = opt_meta.get("sandbox_trial") or opt_meta.get("court_token") is not None
    if opt_meta.get("live_execution") and not is_sandbox:
        raise ValueError("Live execution requires court-tokened sandbox authorization.")
        
    return True

