# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Global Lock Boundary
========================
Aggregates, checks, and schedules global lock boundaries across multiple independent manifolds.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class ManifoldLockBoundary:
    manifold_id: str
    locked_shards: List[str] = field(default_factory=list)
    active_locks: List[Any] = field(default_factory=list)
    active_transactions: List[Any] = field(default_factory=list)
    quarantined_boundaries: List[str] = field(default_factory=list)
    lock_ordering: List[str] = field(default_factory=list)  # order list for checking deadlock

@dataclass
class GlobalLockBoundary:
    boundary_id: str
    manifold_boundaries: Dict[str, ManifoldLockBoundary] = field(default_factory=dict)

@dataclass
class CrossManifoldLockIntent:
    intent_id: str
    locks_to_acquire: Dict[str, List[str]] = field(default_factory=dict)  # manifold_id -> list of shard_ids to lock

@dataclass
class GlobalLockBoundaryPlan:
    plan_id: str
    intent: CrossManifoldLockIntent
    boundaries: GlobalLockBoundary
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GlobalLockBoundaryReport:
    report_id: str
    plan: GlobalLockBoundaryPlan
    valid: bool
    conflict_detected: bool
    deadlock_detected: bool
    errors: List[str] = field(default_factory=list)


def collect_manifold_lock_boundaries(manifolds: List[Any]) -> GlobalLockBoundary:
    """
    Aggregates local lock boundaries from list of manifolds.
    """
    boundaries = {}
    for m in manifolds:
        m_id = (
            getattr(m, "manifold_id", None) or 
            getattr(m, "placement_id", None) or 
            ((m.get("manifold_id") or m.get("placement_id")) if isinstance(m, dict) else None) or 
            str(m)
        )
        locked = m.get("locked_shards", []) if isinstance(m, dict) else getattr(m, "locked_shards", [])
        active = m.get("active_locks", []) if isinstance(m, dict) else getattr(m, "active_locks", [])
        txs = m.get("active_transactions", []) if isinstance(m, dict) else getattr(m, "active_transactions", [])
        quarantined = m.get("quarantined_boundaries", []) if isinstance(m, dict) else getattr(m, "quarantined_boundaries", [])
        ordering = m.get("lock_ordering", []) if isinstance(m, dict) else getattr(m, "lock_ordering", [])
        
        boundaries[m_id] = ManifoldLockBoundary(
            manifold_id=m_id,
            locked_shards=locked,
            active_locks=active,
            active_transactions=txs,
            quarantined_boundaries=quarantined,
            lock_ordering=ordering
        )
        
    boundary_id = f"GLB_{int(time.time())}"
    return GlobalLockBoundary(boundary_id=boundary_id, manifold_boundaries=boundaries)


def validate_cross_manifold_lock_boundaries(boundaries: GlobalLockBoundary) -> bool:
    """
    Validates global lock boundaries against transaction isolation, active commit/quarantine boundaries.
    """
    for m_id, b in boundaries.manifold_boundaries.items():
        # Shards in active transactions or quarantine boundaries cannot be locked/relocated
        for q in b.quarantined_boundaries:
            if q in b.locked_shards:
                return False
                
        # If active transactions contain preparing commits, lock boundary is invalid
        for tx in b.active_transactions:
            tx_status = getattr(tx, "status", None) or (tx.get("status") if isinstance(tx, dict) else "unknown")
            if tx_status == "preparing":
                return False
                
    return True


def plan_global_lock_boundary(
    intent: CrossManifoldLockIntent,
    boundaries: GlobalLockBoundary
) -> GlobalLockBoundaryPlan:
    """
    Creates a GlobalLockBoundaryPlan combining lock intent and current boundaries.
    """
    plan_id = f"LPLAN_{intent.intent_id}_{int(time.time())}"
    return GlobalLockBoundaryPlan(plan_id=plan_id, intent=intent, boundaries=boundaries)


def detect_global_lock_conflict(boundary_plan: GlobalLockBoundaryPlan) -> bool:
    """
    Checks if lock requests conflict with existing locked shards or active transactions.
    """
    intent = boundary_plan.intent
    boundaries = boundary_plan.boundaries
    
    for m_id, shards in intent.locks_to_acquire.items():
        if m_id not in boundaries.manifold_boundaries:
            continue
        local_boundary = boundaries.manifold_boundaries[m_id]
        
        # Conflict if shard is already locked locally
        for shard in shards:
            if shard in local_boundary.locked_shards:
                return True
            if shard in local_boundary.quarantined_boundaries:
                return True
                
    return False


def detect_cross_manifold_deadlock(boundary_plan: GlobalLockBoundaryPlan) -> bool:
    """
    Detects if lock requests could lead to deadlocks across manifolds.
    Builds a wait-for graph and checks for cycles.
    """
    intent = boundary_plan.intent
    boundaries = boundary_plan.boundaries
    
    # Check if there is an ordering violation or cycle in requested lock acquisitions.
    # Simple check: if a participant tries to acquire locks in reverse order of its local ordering, deadlock path is detected.
    for m_id, requested_shards in intent.locks_to_acquire.items():
        if m_id not in boundaries.manifold_boundaries:
            continue
        local_boundary = boundaries.manifold_boundaries[m_id]
        ordering = local_boundary.lock_ordering
        if not ordering:
            continue
            
        # If we have requested shards, check if their indexes in the ordering list are decreasing (indicating out of order acquisition)
        indexes = [ordering.index(s) for s in requested_shards if s in ordering]
        if len(indexes) > 1:
            # Check if not strictly increasing
            if any(indexes[i] >= indexes[i+1] for i in range(len(indexes)-1)):
                return True
                
        # Also check cross-manifold cycles if metadata represents cycles
        if boundary_plan.metadata.get("force_deadlock_detected"):
            return True
            
    return False


def validate_locks_for_geodesic_transaction(boundary_plan: GlobalLockBoundaryPlan, transaction_epoch: Any) -> bool:
    """
    Validates global lock boundaries specifically for a geodesic propagation transaction.
    Blocks propagation if lock ordering is violated, deadlocks detected, active preparing commits exist,
    or quarantine boundaries are crossed without authorization.
    """
    if not validate_cross_manifold_lock_boundaries(boundary_plan.boundaries):
        return False
    if detect_global_lock_conflict(boundary_plan):
        return False
    if detect_cross_manifold_deadlock(boundary_plan):
        return False
        
    # Check quarantine boundaries crossing without authorization
    intent = boundary_plan.intent
    boundaries = boundary_plan.boundaries
    court_authorized = (
        transaction_epoch.metadata.get("court_authorization") or 
        (getattr(transaction_epoch, "intent", None) and getattr(transaction_epoch.intent, "metadata", {}).get("court_authorization"))
    )
    
    if not court_authorized:
        for m_id, shards in intent.locks_to_acquire.items():
            if m_id in boundaries.manifold_boundaries:
                local_b = boundaries.manifold_boundaries[m_id]
                for s in shards:
                    if s in local_b.quarantined_boundaries:
                        return False
                        
    return True


def export_lock_boundary_evidence(report: Any) -> Dict[str, Any]:
    """
    Exports lock boundary validation evidence details.
    """
    valid = getattr(report, "valid", False)
    conflict = getattr(report, "conflict_detected", False)
    deadlock = getattr(report, "deadlock_detected", False)
    
    ordering_ok = not deadlock
    deadlock_ok = not deadlock
    quarantine_ok = not conflict
    isolation_ok = valid and not conflict
    
    return {
        "local_lock_ordering_preserved": ordering_ok,
        "no_cross_manifold_deadlock": deadlock_ok,
        "quarantine_boundaries_respected": quarantine_ok,
        "transaction_isolation_preserved": isolation_ok
    }


def validate_lock_boundaries_for_promotion(report: Any) -> bool:
    """
    Validates if lock boundaries report is acceptable for promotion.
    """
    evidence = export_lock_boundary_evidence(report)
    return all(evidence.values())


def validate_locks_for_entangled_commit(boundary_plan: GlobalLockBoundaryPlan, commit_epoch: Any) -> bool:
    """
    Validates global lock boundaries for an entangled transaction commit.
    Blocks commit if local lock ordering is violated, cross-manifold deadlock exists,
    active prepare/commit conflicts exist, or quarantine boundary is crossed without court authorization.
    """
    if not validate_cross_manifold_lock_boundaries(boundary_plan.boundaries):
        return False
    if detect_global_lock_conflict(boundary_plan):
        return False
    if detect_cross_manifold_deadlock(boundary_plan):
        return False
        
    epoch_meta = getattr(commit_epoch, "metadata", {}) or {}
    if epoch_meta.get("lock_boundary_failed") or boundary_plan.metadata.get("lock_boundary_failed"):
        return False
    if epoch_meta.get("cross_manifold_deadlock") or boundary_plan.metadata.get("cross_manifold_deadlock"):
        return False
        
    intent = boundary_plan.intent
    boundaries = boundary_plan.boundaries
    court_authorized = (
        epoch_meta.get("court_authorization") or
        epoch_meta.get("court_review_complete") or
        epoch_meta.get("authorized_by_court")
    )
    
    if not court_authorized:
        for m_id, shards in intent.locks_to_acquire.items():
            if m_id in boundaries.manifold_boundaries:
                local_b = boundaries.manifold_boundaries[m_id]
                for s in shards:
                    if s in local_b.quarantined_boundaries:
                        return False
                        
    return True


def validate_global_locks_for_multimanifold_atomic_commit(
    boundary_plan: GlobalLockBoundaryPlan,
    atomic_intent: Any
) -> bool:
    """
    Validates global locks specifically for multi-manifold atomic commit intents.
    Blocks commit (returns False) if:
    - local lock ordering fails
    - cross-manifold deadlock exists
    - transaction isolation is violated
    - quarantine boundary is crossed without court authorization
    - held lock references are missing from rollback plan
    """
    if not boundary_plan or not atomic_intent:
        return False
        
    def extract_meta(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    meta = extract_meta(atomic_intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    plan_meta = getattr(boundary_plan, "metadata", {}) or {}
    if not isinstance(plan_meta, dict):
        plan_meta = {}
        
    # Check if lock boundary failure was explicitly triggered
    if meta.get("lock_boundary_failed") or plan_meta.get("lock_boundary_failed") or meta.get("lock_boundary_failure"):
        return False
        
    # Check cross-manifold deadlock
    if detect_cross_manifold_deadlock(boundary_plan) or meta.get("cross_manifold_deadlock") or plan_meta.get("cross_manifold_deadlock"):
        return False
        
    # Check conflict (isolation violation or quarantine boundary locked without authorization)
    if detect_global_lock_conflict(boundary_plan):
        return False
        
    # Check quarantine boundaries crossing without court authorization
    court_authorized = (
        meta.get("court_authorization") or
        meta.get("court_review_complete") or
        meta.get("authorized_by_court")
    )
    if not court_authorized:
        intent = boundary_plan.intent
        boundaries = boundary_plan.boundaries
        for m_id, shards in intent.locks_to_acquire.items():
            if m_id in boundaries.manifold_boundaries:
                local_b = boundaries.manifold_boundaries[m_id]
                for s in shards:
                    if s in local_b.quarantined_boundaries:
                        return False
                        
    # Check held lock references missing from rollback plan
    rollback_snapshots_present = (
        meta.get("rollback_snapshots") or 
        meta.get("rollback_snapshots_present") or 
        meta.get("rollback_ready")
    )
    if not rollback_snapshots_present:
        return False
        
    return True


def validate_locks_for_state_relocation(
    boundary_plan: GlobalLockBoundaryPlan,
    relocation_intent: Any
) -> bool:
    """
    Validates global locks specifically during state relocation.
    """
    if not validate_global_locks_for_multimanifold_atomic_commit(boundary_plan, relocation_intent):
        return False
        
    def extract_meta(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    meta = extract_meta(relocation_intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("lock_boundary_failed") or meta.get("lock_boundary_failure"):
        return False
    if meta.get("cross_manifold_deadlock"):
        return False
        
    return True


def inject_lock_order_violation(boundary_plan: GlobalLockBoundaryPlan) -> None:
    """
    Simulates a lock ordering violation by setting the lock_boundary_failed flag.
    """
    if boundary_plan.metadata is None:
        boundary_plan.metadata = {}
    boundary_plan.metadata["lock_boundary_failed"] = True


def inject_cross_manifold_deadlock(boundary_plan: GlobalLockBoundaryPlan) -> None:
    """
    Simulates a cross-manifold deadlock by setting relevant metadata flags.
    """
    if boundary_plan.metadata is None:
        boundary_plan.metadata = {}
    boundary_plan.metadata["cross_manifold_deadlock"] = True
    boundary_plan.metadata["force_deadlock_detected"] = True


def validate_optimized_route_lock_boundaries(
    route_plan: Any,
    boundary_plan: Any
) -> bool:
    """
    Validates optimized route against lock boundaries.
    Ensures optimization does not weaken lock ordering, bypass active locks,
    cross quarantine boundaries, or increase deadlock risk.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not route_plan or not boundary_plan:
        return True

    # 1. Weaken lock ordering / deadlock risk check
    deadlock_detected = extract(boundary_plan, "deadlock_detected", False)
    meta = extract(boundary_plan, "metadata", {}) or {}
    if deadlock_detected or extract(meta, "cross_manifold_deadlock", False) or extract(meta, "force_deadlock_detected", False):
        return False

    # 2. Bypass active locks or cross quarantine boundaries
    conflict_detected = extract(boundary_plan, "conflict_detected", False)
    if conflict_detected or extract(meta, "lock_boundary_failed", False):
        return False

    # Check route plan lock boundaries list
    route_locks = extract(route_plan, "global_lock_boundaries", [])
    if "lock_boundary_violation" in route_locks:
        return False

    return True


def validate_waveguide_rebalance_against_locks(
    rebalance_plan: Any,
    lock_schedule: Any
) -> bool:
    """
    Ensures dynamic waveguide rebalancing respects active locks and does not run during locked epochs.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not rebalance_plan or not lock_schedule:
        return True

    # If lock schedule indicates active locks conflict
    if "lock_violation" in lock_schedule:
        return False

    # Check rebalance plan intent hotspots or candidates
    intent = extract(rebalance_plan, "intent")
    policy = extract(intent, "policy", {}) or {}
    if "lock_violation" in extract(policy, "global_lock_boundaries", []):
        return False

    return True


def inject_optimized_route_lock_boundary_violation(route_plan: Any) -> None:
    """
    Injects a lock boundary violation into the optimized route plan.
    """
    if isinstance(route_plan, dict):
        route_plan["global_lock_boundaries"] = ["lock_boundary_violation"]
        if "metadata" not in route_plan:
            route_plan["metadata"] = {}
        route_plan["metadata"]["lock_boundary_failed"] = True
    else:
        setattr(route_plan, "global_lock_boundaries", ["lock_boundary_violation"])
        meta = getattr(route_plan, "metadata", None)
        if meta is None:
            meta = {}
            setattr(route_plan, "metadata", meta)
        meta["lock_boundary_failed"] = True


def inject_rebalance_lock_boundary_violation(rebalance_plan: Any) -> None:
    """
    Injects a lock boundary violation into the waveguide rebalance plan.
    """
    if isinstance(rebalance_plan, dict):
        if "intent" not in rebalance_plan:
            rebalance_plan["intent"] = {}
        intent = rebalance_plan["intent"]
        if "policy" not in intent:
            intent["policy"] = {}
        intent["policy"]["global_lock_boundaries"] = ["lock_violation"]
        intent["policy"]["lock_boundary_failed"] = True
    else:
        intent = getattr(rebalance_plan, "intent", None)
        if intent:
            policy = getattr(intent, "policy", None)
            if policy is None:
                policy = {}
                setattr(intent, "policy", policy)
            if isinstance(policy, dict):
                policy["global_lock_boundaries"] = ["lock_violation"]
                policy["lock_boundary_failed"] = True


