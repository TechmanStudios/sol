# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Lock-Free Bypass Structures
===============================
Provides fast-path direct routing channels to bypass core locks and boundaries when safe.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class BypassChannel:
    channel_id: str
    source_core_id: str
    target_core_id: str
    bandwidth_factor: float = 1.0

@dataclass
class BypassRoute:
    source_task_id: str
    target_task_id: str
    dependency_type: str = "data"
    is_safe: bool = True
    reason: str = "no hazards"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BypassEligibilityReport:
    route: BypassRoute
    eligible: bool
    reasons: List[str] = field(default_factory=list)

@dataclass
class BypassExecutionPlan:
    plan_id: str
    eligible_routes: List[BypassRoute]
    schedule_reference: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BypassExecutionReport:
    report_id: str
    passed_gates: bool
    optimized_schedule: Any
    original_report: Any
    optimized_report: Any
    bypass_routes_applied: List[BypassRoute] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def identify_bypassable_dependencies(schedule: Any) -> List[BypassRoute]:
    """
    Scans the schedule dependencies and identifies routes that are eligible for bypass.
    """
    eligible_routes = []
    
    # Simple rule check:
    # 1. Dependency must be "data" or "reduction", but not "consensus" or "lock".
    # 2. Source and target tasks must not be part of a write-after-write hazard (e.g. they don't both write same outputs).
    # 3. No unresolved transaction lock exists (we validate this with coordinate helper).
    # 4. No consensus checkpoint is bypassed.
    
    if not hasattr(schedule, "dependencies") or not hasattr(schedule, "tasks"):
        return eligible_routes
        
    for dep in schedule.dependencies:
        src_task = schedule.tasks.get(dep.source_task_id)
        dst_task = schedule.tasks.get(dep.target_task_id)
        if not src_task or not dst_task:
            continue
            
        reasons = []
        is_safe = True
        
        # Rule 1: No consensus checkpoint is bypassed (neither task can be consensus stage)
        if src_task.stage_name == "consensus" or dst_task.stage_name == "consensus":
            is_safe = False
            reasons.append("consensus_checkpoint_bypassed")
            
        # Rule 2: No write-after-write hazard exists between source and target
        overlap_outputs = set(src_task.outputs).intersection(set(dst_task.outputs))
        if overlap_outputs:
            is_safe = False
            reasons.append("write_after_write_hazard_exists")
            
        # Rule 3: No unresolved transaction lock exists
        meta = getattr(dep, "metadata", {}) or {}
        if meta.get("transaction_lock") or meta.get("unresolved_lock"):
            is_safe = False
            reasons.append("unresolved_transaction_lock")
            
        # Rule 4: Verify if oracle match can be preserved
        if meta.get("oracle_mismatch"):
            is_safe = False
            reasons.append("oracle_match_not_preserved")
            
        route = BypassRoute(
            source_task_id=dep.source_task_id,
            target_task_id=dep.target_task_id,
            dependency_type=dep.dependency_type,
            is_safe=is_safe,
            reason=", ".join(reasons) if reasons else "safe_read_only",
            metadata=meta
        )
        
        # We always return the route so eligibility checks can see why it was rejected
        eligible_routes.append(route)
            
    return eligible_routes


def validate_bypass_route(route: BypassRoute) -> bool:
    """
    Returns True if the route does not bypass a consensus checkpoint or trigger write-after-write hazards.
    """
    if not route.is_safe:
        return False
    if "consensus" in route.reason or "write" in route.reason or "lock" in route.reason:
        return False
    return True


def build_bypass_plan(schedule: Any, eligible_routes: List[BypassRoute]) -> BypassExecutionPlan:
    """
    Builds a BypassExecutionPlan from list of eligible routes.
    """
    plan_id = f"PLAN_BYPASS_{int(time.time())}"
    return BypassExecutionPlan(
        plan_id=plan_id,
        eligible_routes=eligible_routes,
        schedule_reference=schedule
    )


def execute_shadow_bypass(plan: BypassExecutionPlan) -> BypassExecutionReport:
    """
    Applies the bypass routes to schedule reference and executes shadow pipeline.
    """
    from sol_multicore_pipeline import apply_shadow_bypass, execute_shadow_pipeline
    
    schedule = plan.schedule_reference
    original_report = execute_shadow_pipeline(schedule)
    
    # Filter only validated routes
    valid_routes = [r for r in plan.eligible_routes if validate_bypass_route(r)]
    
    optimized_schedule = apply_shadow_bypass(schedule, plan)
    optimized_report = execute_shadow_pipeline(optimized_schedule)
    
    passed_gates = optimized_report.passed_gates and all(validate_bypass_route(r) for r in valid_routes)
    
    return BypassExecutionReport(
        report_id=f"RPT_BYPASS_{int(time.time())}",
        passed_gates=passed_gates,
        optimized_schedule=optimized_schedule,
        original_report=original_report,
        optimized_report=optimized_report,
        bypass_routes_applied=valid_routes
    )
