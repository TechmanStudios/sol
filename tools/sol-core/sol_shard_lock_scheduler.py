# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Shard-Lock Scheduler
========================
Implements local/distributed lock leases, compatibility matrices,
wait-for graphs, deadlock cycle detection, and prevention policies.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
import time

@dataclass
class ShardLock:
    shard_id: str
    mode: str  # "shared" | "exclusive" | "intent_shared" | "intent_exclusive"
    owner_transaction_id: str
    requested_at: float
    expires_at: float
    rollback_plan_ref: str

@dataclass
class ShardLockRequest:
    request_id: str
    transaction_id: str
    shard_id: str
    mode: str
    timeout: float = 1.0
    rollback_plan_ref: str = "none"

@dataclass
class ShardLockGrant:
    grant_id: str
    request: ShardLockRequest
    granted_at: float = field(default_factory=time.time)

@dataclass
class ShardLockWait:
    wait_id: str
    request: ShardLockRequest
    waiting_on_transaction_ids: List[str] = field(default_factory=list)

@dataclass
class ShardLockRelease:
    transaction_id: str
    shard_id: str
    released_at: float = field(default_factory=time.time)

@dataclass
class ShardLockSchedule:
    transaction_id: str
    grants: List[ShardLockGrant] = field(default_factory=list)
    waits: List[ShardLockWait] = field(default_factory=list)
    lock_order: List[str] = field(default_factory=list)
    lock_order_valid: bool = True

@dataclass
class DeadlockDetectionReport:
    deadlock_detected: bool
    cycle: List[str] = field(default_factory=list)
    policy_recommended: str = "ordered_locks"

@dataclass
class ShardLockSchedulerReport:
    scheduler_report_id: str
    active_locks: List[ShardLock] = field(default_factory=list)
    deadlock_report: DeadlockDetectionReport = field(default_factory=dict)


# In-memory lock registry for testing and shadow execution
_ACTIVE_LOCKS: List[ShardLock] = []

def get_active_locks() -> List[ShardLock]:
    """
    Returns the list of currently active locks.
    """
    global _ACTIVE_LOCKS
    return _ACTIVE_LOCKS

def clear_active_locks() -> None:
    """
    Clears all active locks in the registry.
    """
    global _ACTIVE_LOCKS
    _ACTIVE_LOCKS.clear()


# Lock Compatibility Matrix
# True = compatible, False = conflicts
# Modes: "shared", "exclusive", "intent_shared", "intent_exclusive"
COMPATIBILITY_MATRIX = {
    "shared": {
        "shared": True,
        "exclusive": False,
        "intent_shared": True,
        "intent_exclusive": False
    },
    "exclusive": {
        "shared": False,
        "exclusive": False,
        "intent_shared": False,
        "intent_exclusive": False
    },
    "intent_shared": {
        "shared": True,
        "exclusive": False,
        "intent_shared": True,
        "intent_exclusive": True
    },
    "intent_exclusive": {
        "shared": False,
        "exclusive": False,
        "intent_shared": True,
        "intent_exclusive": True
    }
}


def are_modes_compatible(mode1: str, mode2: str) -> bool:
    """
    Determines if two lock modes are compatible.
    """
    m1 = mode1.lower()
    m2 = mode2.lower()
    if m1 in COMPATIBILITY_MATRIX and m2 in COMPATIBILITY_MATRIX[m1]:
        return COMPATIBILITY_MATRIX[m1][m2]
    return False


def request_locks(
    transaction_id: str,
    shard_ids: List[str],
    mode: str = "exclusive",
    rollback_plan_ref: str = "default_rollback_plan"
) -> ShardLockSchedule:
    """
    Constructs lock requests, verifying deterministic alphabetical shard sorting.
    """
    # Enforce deterministic locking by sorting shard IDs
    sorted_shards = sorted(shard_ids)
    lock_order_valid = (shard_ids == sorted_shards)
    
    grants = []
    waits = []
    
    # Process requests
    for idx, s_id in enumerate(shard_ids):
        req = ShardLockRequest(
            request_id=f"LREQ_{transaction_id}_{s_id}_{idx}",
            transaction_id=transaction_id,
            shard_id=s_id,
            mode=mode,
            timeout=1.0,
            rollback_plan_ref=rollback_plan_ref
        )
        
        # Check conflicts with other active locks in registry
        conflicting_txs = []
        for lock in _ACTIVE_LOCKS:
            if lock.shard_id == s_id and lock.owner_transaction_id != transaction_id:
                if not are_modes_compatible(lock.mode, mode):
                    conflicting_txs.append(lock.owner_transaction_id)
                    
        if conflicting_txs:
            # Place in wait queue
            waits.append(ShardLockWait(
                wait_id=f"LWAIT_{transaction_id}_{s_id}_{idx}",
                request=req,
                waiting_on_transaction_ids=list(set(conflicting_txs))
            ))
        else:
            # Grant lock and add to registry
            grants.append(ShardLockGrant(
                grant_id=f"LGRANT_{transaction_id}_{s_id}_{idx}",
                request=req,
                granted_at=time.time()
            ))
            _ACTIVE_LOCKS.append(ShardLock(
                shard_id=s_id,
                mode=mode,
                owner_transaction_id=transaction_id,
                requested_at=time.time(),
                expires_at=time.time() + 10.0,
                rollback_plan_ref=rollback_plan_ref
            ))
            
    return ShardLockSchedule(
        transaction_id=transaction_id,
        grants=grants,
        waits=waits,
        lock_order=shard_ids,
        lock_order_valid=lock_order_valid
    )


def grant_locks_if_available(
    requests: List[ShardLockRequest]
) -> ShardLockSchedule:
    """
    Processes a list of lock requests against active locks and grants if compatible.
    """
    if not requests:
        return ShardLockSchedule(transaction_id="unknown")
        
    tx_id = requests[0].transaction_id
    grants = []
    waits = []
    shard_ids = []
    
    for idx, req in enumerate(requests):
        s_id = req.shard_id
        shard_ids.append(s_id)
        
        conflicting_txs = []
        for lock in _ACTIVE_LOCKS:
            if lock.shard_id == s_id and lock.owner_transaction_id != tx_id:
                if not are_modes_compatible(lock.mode, req.mode):
                    conflicting_txs.append(lock.owner_transaction_id)
                    
        if conflicting_txs:
            waits.append(ShardLockWait(
                wait_id=f"LWAIT_{tx_id}_{s_id}_{idx}",
                request=req,
                waiting_on_transaction_ids=list(set(conflicting_txs))
            ))
        else:
            grants.append(ShardLockGrant(
                grant_id=f"LGRANT_{tx_id}_{s_id}_{idx}",
                request=req,
                granted_at=time.time()
            ))
            _ACTIVE_LOCKS.append(ShardLock(
                shard_id=s_id,
                mode=req.mode,
                owner_transaction_id=tx_id,
                requested_at=time.time(),
                expires_at=time.time() + req.timeout,
                rollback_plan_ref=req.rollback_plan_ref
            ))
            
    # Check lock order valid (must be sorted alphabetically)
    sorted_shards = sorted(shard_ids)
    lock_order_valid = (shard_ids == sorted_shards)
    
    return ShardLockSchedule(
        transaction_id=tx_id,
        grants=grants,
        waits=waits,
        lock_order=shard_ids,
        lock_order_valid=lock_order_valid
    )


def release_locks(transaction_id: str) -> List[ShardLockRelease]:
    """
    Releases all locks currently held by a transaction.
    """
    global _ACTIVE_LOCKS
    released = []
    remaining = []
    
    for lock in _ACTIVE_LOCKS:
        if lock.owner_transaction_id == transaction_id:
            released.append(ShardLockRelease(
                transaction_id=transaction_id,
                shard_id=lock.shard_id
            ))
        else:
            remaining.append(lock)
            
    _ACTIVE_LOCKS = remaining
    return released


def build_wait_for_graph(
    lock_schedule: ShardLockSchedule
) -> Dict[str, List[str]]:
    """
    Constructs a wait-for adjacency list mapping transaction_id to dependencies.
    """
    graph = {}
    tx_id = lock_schedule.transaction_id
    
    # Owner transaction waits for the transactions listed in waits
    waiting_on = set()
    for wait in lock_schedule.waits:
        for other_tx in wait.waiting_on_transaction_ids:
            waiting_on.add(other_tx)
            
    if waiting_on:
        graph[tx_id] = list(waiting_on)
    else:
        graph[tx_id] = []
        
    return graph


def detect_deadlock(
    wait_for_graph: Dict[str, List[str]]
) -> DeadlockDetectionReport:
    """
    Performs Depth-First Search cycle detection to detect deadlocks.
    """
    visited = {}
    path = []
    cycle = []
    
    def dfs(node):
        nonlocal cycle
        visited[node] = 1  # visiting
        path.append(node)
        
        for neighbor in wait_for_graph.get(node, []):
            if neighbor in visited:
                if visited[neighbor] == 1:
                    # Cycle detected
                    idx = path.index(neighbor)
                    cycle = path[idx:] + [neighbor]
                    return True
            else:
                if dfs(neighbor):
                    return True
                    
        path.pop()
        visited[node] = 2  # fully visited
        return False
        
    deadlock_detected = False
    for node in wait_for_graph:
        if node not in visited:
            if dfs(node):
                deadlock_detected = True
                break
                
    return DeadlockDetectionReport(
        deadlock_detected=deadlock_detected,
        cycle=cycle,
        policy_recommended="ordered_locks"
    )


def prevent_deadlock(
    strategy: str = "ordered_locks"
) -> Dict[str, Any]:
    """
    Deadlock prevention details placeholder.
    """
    return {
        "strategy": strategy,
        "enforced": True,
        "alternative_strategies": ["wound_wait", "wait_die", "timeout_abort"]
    }


@dataclass
class LockBoundary:
    boundary_id: str
    core_id: str
    shard_id: str
    locked_tasks: List[str]
    lock_mode: str  # "shared" | "exclusive"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LockBoundaryOptimization:
    optimization_id: str
    target_boundary_id: str
    reducible: bool
    reason: str
    original_wait_duration: float
    optimized_wait_duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LockBoundaryReport:
    boundaries: List[LockBoundary] = field(default_factory=list)
    optimizations: List[LockBoundaryOptimization] = field(default_factory=list)
    is_safe: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


def analyze_cross_core_lock_boundaries(schedule: Any, lock_schedule: Any) -> LockBoundaryReport:
    """
    Analyzes locks in the schedule and lock_schedule to find boundaries.
    """
    boundaries = []
    
    lock_deps = []
    if hasattr(schedule, "dependencies"):
        for dep in schedule.dependencies:
            if getattr(dep, "dependency_type", "data") == "lock":
                lock_deps.append(dep)

    if hasattr(schedule, "tasks"):
        for idx, dep in enumerate(lock_deps):
            target_task = schedule.tasks.get(dep.target_task_id)
            source_task = schedule.tasks.get(dep.source_task_id)
            if target_task and source_task:
                is_exclusive = (
                    any(target_task.outputs) or
                    any(source_task.outputs) or
                    "write" in target_task.task_id.lower() or
                    "write" in source_task.task_id.lower()
                )
                
                dep_meta = getattr(dep, "metadata", {}) or {}
                if dep_meta.get("lock_mode") == "exclusive":
                    is_exclusive = True
                elif dep_meta.get("lock_mode") == "shared":
                    is_exclusive = False
                    
                boundaries.append(LockBoundary(
                    boundary_id=f"BND_{idx}",
                    core_id=getattr(target_task, "core_id", "default_core"),
                    shard_id=getattr(target_task, "metadata", {}).get("shard_id", "shard_0"),
                    locked_tasks=[source_task.task_id, target_task.task_id],
                    lock_mode="exclusive" if is_exclusive else "shared",
                    metadata=dep_meta
                ))
            
    report = LockBoundaryReport(
        boundaries=boundaries,
        optimizations=[],
        is_safe=True
    )
    report.optimizations = suggest_lock_boundary_reduction(report)
    return report

def suggest_lock_boundary_reduction(report: LockBoundaryReport) -> List[LockBoundaryOptimization]:
    """
    Suggests reducing lock boundaries that are read-only and have no write dependencies.
    """
    optimizations = []
    for b in report.boundaries:
        if b.lock_mode == "shared":
            optimizations.append(LockBoundaryOptimization(
                optimization_id=f"OPT_{b.boundary_id}",
                target_boundary_id=b.boundary_id,
                reducible=True,
                reason="Read-only shared lock boundary wait can be safely bypassed or reduced.",
                original_wait_duration=0.5,
                optimized_wait_duration=0.0,
                metadata={"bypassed": True}
            ))
        else:
            optimizations.append(LockBoundaryOptimization(
                optimization_id=f"OPT_{b.boundary_id}",
                target_boundary_id=b.boundary_id,
                reducible=False,
                reason="Required exclusive lock must be maintained for write safety.",
                original_wait_duration=0.5,
                optimized_wait_duration=0.5,
                metadata={"bypassed": False}
            ))
    return optimizations

def validate_lock_boundary_optimization(optimization: LockBoundaryOptimization) -> bool:
    """
    Validates if a lock boundary optimization is safe.
    Must return False if it weakens an exclusive lock.
    """
    if optimization.reducible:
        reason_lower = optimization.reason.lower()
        if "exclusive" in reason_lower or "write" in reason_lower or "required" in reason_lower:
            return False
        return True
    return False


def validate_rebalance_against_locks(plan: Any, lock_schedule: Any) -> bool:
    """
    Validates rebalance candidates against active shard locks and schedules.
    Blocks rebalance if a shard has an active exclusive lock, is part of an active
    transaction, violates lock ordering, or increases deadlock risk.
    """
    # Extract candidates
    candidates = getattr(plan, "candidates", []) or []
    if isinstance(plan, dict):
        candidates = plan.get("candidates", [])
        
    # Get active locks in the system
    active_locks = get_active_locks() or []
    
    # Also inspect lock_schedule
    grants = []
    waits = []
    if lock_schedule is not None:
        grants = getattr(lock_schedule, "grants", []) or []
        waits = getattr(lock_schedule, "waits", []) or []
        
    for cand in candidates:
        item_type = getattr(cand, "item_type", "")
        item_id = getattr(cand, "item_id", "")
        
        if isinstance(cand, dict):
            item_type = cand.get("item_type", "")
            item_id = cand.get("item_id", "")
            
        # We only care about shards in this lock-scheduler context
        target_shard = item_id if item_type == "shard" else None
        if item_type == "manifold":
            # Manifold is mapped to shard. If metadata contains shard, use it
            metadata = getattr(cand, "metadata", {}) or {}
            target_shard = metadata.get("source_shard") or metadata.get("target_shard") or "shard_0"
            
        if not target_shard:
            continue
            
        # 1. Shard has active exclusive lock
        for lock in active_locks:
            if lock.shard_id == target_shard and lock.mode.lower() == "exclusive":
                return False
                
        for grant in grants:
            req = getattr(grant, "request", None)
            if req and getattr(req, "shard_id", "") == target_shard and getattr(req, "mode", "").lower() == "exclusive":
                return False
                
        # 2. Shard is part of an active transaction
        # Check if there are active locks or waits for this shard
        for lock in active_locks:
            if lock.shard_id == target_shard:
                return False
                
        for grant in grants:
            req = getattr(grant, "request", None)
            if req and getattr(req, "shard_id", "") == target_shard:
                return False
                
        for wait in waits:
            req = getattr(wait, "request", None)
            if req and getattr(req, "shard_id", "") == target_shard:
                return False
                
        # 3. Lock ordering violation
        # (e.g. if the policy requires lock ordering, or if lock_schedule indicates ordering is invalid)
        if lock_schedule is not None and not getattr(lock_schedule, "lock_order_valid", True):
            return False
            
        # 4. Deadlock risk increase
        if waits:
            # If there are active waiters, deadlock risk increases, so we block rebalance
            return False
            
    return True


_QUIESCED_SANDBOX_SHARDS: Set[str] = set()

def quiesce_sandbox_shard_for_relocation(shard_id: str, token: Any) -> bool:
    """
    Quiesces a sandbox shard for relocation if token is valid and scoped to sandbox.
    Production/default shards must be rejected.
    """
    from sol_live_relocation import validate_live_relocation_token
    if not token or not validate_live_relocation_token(token):
        return False

    if not getattr(token, "sandbox_scope", False):
        return False

    # Production/default shard quiesce must be rejected.
    if "production" in shard_id.lower() or "default" in shard_id.lower():
        return False

    _QUIESCED_SANDBOX_SHARDS.add(shard_id)
    return True


def release_sandbox_relocation_quiesce(shard_id: str, token: Any) -> bool:
    """
    Releases the quiesced state for a sandbox shard.
    """
    from sol_live_relocation import validate_live_relocation_token
    if not token or not validate_live_relocation_token(token):
        return False

    if shard_id in _QUIESCED_SANDBOX_SHARDS:
        _QUIESCED_SANDBOX_SHARDS.remove(shard_id)
        return True
    return False


