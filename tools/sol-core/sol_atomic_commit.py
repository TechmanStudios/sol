# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Distributed Manifold Atomic Commit
======================================
Scaffolds distributed atomic commit, rollback snapshots, and 2PC protocols
across manifold boundaries.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

@dataclass
class AtomicCommitParticipant:
    participant_id: str
    status: str  # "idle" | "preparing" | "prepared" | "committed" | "aborted"
    state_value: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AtomicCommitIntent:
    intent_id: str
    op: str  # e.g., "COMMIT_WORD"
    value: int
    width: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DistributedRollbackSnapshot:
    snapshot_id: str
    transaction_id: str
    participant_states: Dict[str, Dict[str, Any]]
    timestamp: float = field(default_factory=time.time)

@dataclass
class AtomicCommitTransaction:
    transaction_id: str
    participants: List[AtomicCommitParticipant]
    intent: AtomicCommitIntent
    sandbox: bool = True
    status: str = "pending"  # "pending" | "prepared" | "committed" | "aborted"
    rollback_snapshot: Optional[DistributedRollbackSnapshot] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AtomicPrepareResult:
    participant_id: str
    prepared: bool
    status: str
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class AtomicCommitDecision:
    transaction_id: str
    decision: str  # "commit" | "abort"
    quorum_reached: bool
    all_prepared: bool
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AtomicCommitResult:
    transaction_id: str
    committed: bool
    sandbox_executed: bool
    committed_value: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

@dataclass
class AtomicRollbackResult:
    transaction_id: str
    rolled_back: bool
    reason: str
    restored_states: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

@dataclass
class AtomicCommitReport:
    report_id: str
    transaction: AtomicCommitTransaction
    prepare_results: List[AtomicPrepareResult]
    decision: AtomicCommitDecision
    commit_result: Optional[AtomicCommitResult] = None
    rollback_result: Optional[AtomicRollbackResult] = None
    passed_gates: bool = False
    reproducibility_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_atomic_transaction(
    participants: List[AtomicCommitParticipant],
    intent: AtomicCommitIntent,
    sandbox: bool = True
) -> AtomicCommitTransaction:
    """
    Constructs a distributed atomic commit transaction.
    """
    tx_id = f"TX_{intent.intent_id}_{int(time.time())}"
    return AtomicCommitTransaction(
        transaction_id=tx_id,
        participants=participants,
        intent=intent,
        sandbox=sandbox,
        status="pending",
        metadata={"created_at": time.time()}
    )


def validate_lock_schedule(
    lock_schedule: Optional[Any],
    deadlock_report: Optional[Any],
    rollback_snapshots_present: bool,
    token: Optional[Any] = None
) -> Dict[str, bool]:
    """
    Validates lock schedule, order, deadlocks, leases, snapshots, and token permissions.
    """
    gates = {
        "all_required_locks_granted": False,
        "lock_order_valid": False,
        "no_deadlock_detected": False,
        "lock_leases_valid": False,
        "rollback_snapshots_present": rollback_snapshots_present,
        "sandbox_token_required_for_live_commit": False
    }

    if lock_schedule is not None:
        gates["all_required_locks_granted"] = len(getattr(lock_schedule, "waits", [])) == 0
        gates["lock_order_valid"] = getattr(lock_schedule, "lock_order_valid", True)
        
        # Leases are valid if we have locks and they have expires_at metadata (stub is always True if locks exist)
        gates["lock_leases_valid"] = True
    else:
        # If no locks are needed or lock schedule is not provided, default to True
        gates["all_required_locks_granted"] = True
        gates["lock_order_valid"] = True
        gates["lock_leases_valid"] = True

    if deadlock_report is not None:
        gates["no_deadlock_detected"] = not getattr(deadlock_report, "deadlock_detected", False)
    else:
        gates["no_deadlock_detected"] = True

    # Check sandbox token rules
    token_ok = False
    if token is not None:
        live_enabled = (
            getattr(token, "live_control_enabled", False) or
            getattr(token, "active", False) or
            getattr(token, "authorized_by_court", False)
        )
        if isinstance(token, dict):
            live_enabled = (
                token.get("live_control_enabled", False) or
                token.get("active", False) or
                token.get("authorized_by_court", False)
            )
        sandbox_only = getattr(token, "sandbox_only", True)
        if not sandbox_only and isinstance(token, dict):
            sandbox_only = token.get("sandbox_only", True)
        token_ok = live_enabled and sandbox_only

    gates["sandbox_token_required_for_live_commit"] = token_ok

    return gates


def prepare_transaction(
    transaction: AtomicCommitTransaction,
    lock_schedule: Optional[Any] = None,
    deadlock_report: Optional[Any] = None
) -> List[AtomicPrepareResult]:
    """
    Executes prepare checks across all transaction participants.
    """
    # Perform lock schedule validation if provided
    lock_error = None
    if lock_schedule is not None:
        gates = validate_lock_schedule(
            lock_schedule=lock_schedule,
            deadlock_report=deadlock_report,
            rollback_snapshots_present=transaction.rollback_snapshot is not None,
            token=None
        )
        if not gates["all_required_locks_granted"]:
            lock_error = "Lock schedule preparation failed: not all locks granted."
        elif not gates["lock_order_valid"]:
            lock_error = "Lock schedule preparation failed: invalid lock ordering."
        elif not gates["no_deadlock_detected"]:
            lock_error = "Lock schedule preparation failed: deadlock detected."
        elif not gates["lock_leases_valid"]:
            lock_error = "Lock schedule preparation failed: invalid lock leases."

    results = []
    for p in transaction.participants:
        # Check metadata to simulate failures if requested
        prepared = p.metadata.get("prepare_fails", False) is False and lock_error is None
        status = "prepared" if prepared else "failed"
        p.status = status
        
        err_msg = None
        if not prepared:
            if lock_error:
                err_msg = lock_error
            else:
                err_msg = f"Participant {p.participant_id} failed prepare check."
            
        results.append(AtomicPrepareResult(
            participant_id=p.participant_id,
            prepared=prepared,
            status=status,
            error_message=err_msg
        ))
    
    if all(r.prepared for r in results):
        transaction.status = "prepared"
    else:
        transaction.status = "aborted"
        
    return results


def decide_atomic_commit(
    prepare_results: List[AtomicPrepareResult],
    quorum_ratio: float = 1.0
) -> AtomicCommitDecision:
    """
    Evaluates participant prepare results and votes commit or abort decision.
    """
    total = len(prepare_results)
    prepared_count = sum(1 for r in prepare_results if r.prepared)
    
    all_prepared = prepared_count == total
    ratio = prepared_count / total if total > 0 else 0.0
    quorum_reached = ratio >= (quorum_ratio - 1e-5)
    
    decision_str = "commit" if (all_prepared and quorum_reached) else "abort"
    tx_id = "unknown"
    if prepare_results:
        # Try to extract tx_id from participant ID format if available
        tx_id = prepare_results[0].participant_id
        
    return AtomicCommitDecision(
        transaction_id=tx_id,
        decision=decision_str,
        quorum_reached=quorum_reached,
        all_prepared=all_prepared,
        metadata={"prepared_count": prepared_count, "total_count": total}
    )


def capture_participant_snapshots(transaction: AtomicCommitTransaction) -> DistributedRollbackSnapshot:
    """
    Captures rollback state snapshots of all participants.
    """
    states = {}
    for p in transaction.participants:
        states[p.participant_id] = {
            "status": p.status,
            "state_value": p.state_value,
            "metadata": p.metadata.copy()
        }
    snap_id = f"SNAP_{transaction.transaction_id}"
    snapshot = DistributedRollbackSnapshot(
        snapshot_id=snap_id,
        transaction_id=transaction.transaction_id,
        participant_states=states
    )
    transaction.rollback_snapshot = snapshot
    return snapshot


def restore_participant_snapshots(snapshot: DistributedRollbackSnapshot, participants: List[AtomicCommitParticipant]) -> None:
    """
    Restores participants back to their saved snapshots.
    """
    for p in participants:
        if p.participant_id in snapshot.participant_states:
            state = snapshot.participant_states[p.participant_id]
            p.status = state["status"]
            p.state_value = state["state_value"]
            p.metadata = state["metadata"].copy()


def commit_transaction(
    transaction: AtomicCommitTransaction,
    decision: AtomicCommitDecision,
    token: Any = None,
    lock_schedule: Optional[Any] = None,
    deadlock_report: Optional[Any] = None
) -> AtomicCommitResult:
    """
    Commits the transaction to participants if gates pass and sandbox token is present.
    """
    errors = []
    sandbox_executed = False
    
    if decision.decision != "commit":
        transaction.status = "aborted"
        for p in transaction.participants:
            p.status = "aborted"
        return AtomicCommitResult(
            transaction_id=transaction.transaction_id,
            committed=False,
            sandbox_executed=False,
            errors=["Transaction decision was abort."]
        )
        
    if not transaction.rollback_snapshot:
        transaction.status = "aborted"
        for p in transaction.participants:
            p.status = "aborted"
        return AtomicCommitResult(
            transaction_id=transaction.transaction_id,
            committed=False,
            sandbox_executed=False,
            errors=["Rollback snapshot is missing. Commit blocked."]
        )
        
    # Perform lock schedule validation if provided
    if lock_schedule is not None:
        gates = validate_lock_schedule(
            lock_schedule=lock_schedule,
            deadlock_report=deadlock_report,
            rollback_snapshots_present=transaction.rollback_snapshot is not None,
            token=token
        )
        if not gates["all_required_locks_granted"]:
            errors.append("Commit blocked: not all required locks are granted.")
        if not gates["lock_order_valid"]:
            errors.append("Commit blocked: lock order is invalid.")
        if not gates["no_deadlock_detected"]:
            errors.append("Commit blocked: deadlock detected.")
        if not gates["lock_leases_valid"]:
            errors.append("Commit blocked: lock leases are invalid.")
        if not gates["rollback_snapshots_present"]:
            errors.append("Commit blocked: rollback snapshot is missing.")
            
        if errors:
            transaction.status = "aborted"
            for p in transaction.participants:
                p.status = "aborted"
            return AtomicCommitResult(
                transaction_id=transaction.transaction_id,
                committed=False,
                sandbox_executed=False,
                errors=errors
            )
        
    if transaction.sandbox:
        token_ok = False
        if token is not None:
            live_enabled = (
                getattr(token, "live_control_enabled", False) or
                getattr(token, "active", False) or
                getattr(token, "authorized_by_court", False)
            )
            if isinstance(token, dict):
                live_enabled = (
                    token.get("live_control_enabled", False) or
                    token.get("active", False) or
                    token.get("authorized_by_court", False)
                )
            sandbox_only = getattr(token, "sandbox_only", True)
            if not sandbox_only and isinstance(token, dict):
                sandbox_only = token.get("sandbox_only", True)
            
            token_ok = live_enabled and sandbox_only
            
        if token_ok:
            sandbox_executed = True
        else:
            errors.append("Valid sandbox token is required for live commit. Running in shadow/dry-run mode.")
    else:
        transaction.status = "aborted"
        for p in transaction.participants:
            p.status = "aborted"
        return AtomicCommitResult(
            transaction_id=transaction.transaction_id,
            committed=False,
            sandbox_executed=False,
            errors=["Production/default live distributed mutation is strictly forbidden."]
        )
        
    committed_val = transaction.intent.value
    transaction.status = "committed"
    for p in transaction.participants:
        p.status = "committed"
        if sandbox_executed:
            p.state_value = committed_val
            
    return AtomicCommitResult(
        transaction_id=transaction.transaction_id,
        committed=True,
        sandbox_executed=sandbox_executed,
        committed_value=committed_val if sandbox_executed else None,
        errors=errors
    )


def rollback_transaction(transaction: AtomicCommitTransaction, reason: str) -> AtomicRollbackResult:
    """
    Rolls back transaction and restores participants to snapshot.
    """
    if not transaction.rollback_snapshot:
        return AtomicRollbackResult(
            transaction_id=transaction.transaction_id,
            rolled_back=False,
            reason=f"Rollback failed: snapshot not found. {reason}",
            restored_states={}
        )
        
    restore_participant_snapshots(transaction.rollback_snapshot, transaction.participants)
    transaction.status = "aborted"
    for p in transaction.participants:
        p.status = "aborted"
        
    restored = {p.participant_id: p.state_value for p in transaction.participants}
    return AtomicRollbackResult(
        transaction_id=transaction.transaction_id,
        rolled_back=True,
        reason=reason,
        restored_states=restored
    )


def validate_rebalance_against_active_transactions(plan: Any, transactions: List[Any]) -> bool:
    """
    Validates rebalance candidates against active atomic commit transactions.
    Rebalancing must not move participants during active prepare/commit.
    Returns False if any active transaction is associated with an item being rebalanced.
    """
    # Extract candidates
    candidates = getattr(plan, "candidates", []) or []
    if isinstance(plan, dict):
        candidates = plan.get("candidates", [])
        
    for tx in transactions:
        status = getattr(tx, "status", "pending")
        if isinstance(tx, dict):
            status = tx.get("status", "pending")
            
        # If transaction is active (not committed or aborted)
        if status.lower() not in ("committed", "aborted"):
            # Check participants
            participants = getattr(tx, "participants", []) or []
            if isinstance(tx, dict):
                participants = tx.get("participants", [])
                
            for p in participants:
                p_id = getattr(p, "participant_id", "")
                if isinstance(p, dict):
                    p_id = p.get("participant_id", "")
                    
                # Check if this participant is being moved by any candidate
                for cand in candidates:
                    item_id = getattr(cand, "item_id", "")
                    if isinstance(cand, dict):
                        item_id = cand.get("item_id", "")
                        
                    # Match if item_id is in p_id or vice versa
                    if item_id and (item_id in p_id or p_id in item_id):
                        return False
                        
    return True


def validate_no_active_commit_during_relocation(plan: Any, transactions: List[Any]) -> bool:
    """
    Checks if there are any active commit/prepare phases in transactions that would block the relocation plan.
    If so, returns False (blocking relocation).
    """
    for tx in transactions:
        status = getattr(tx, "status", "pending")
        if isinstance(tx, dict):
            status = tx.get("status", "pending")
        if status.lower() in ("preparing", "prepared"):
            return False
    return True


def block_relocation_during_prepare_commit(transaction: Any) -> bool:
    """
    Returns True if the transaction is in prepare/commit phase, signaling that relocation is blocked.
    """
    status = getattr(transaction, "status", "pending")
    if isinstance(transaction, dict):
        status = transaction.get("status", "pending")
    return status.lower() in ("preparing", "prepared")


def validate_transaction_before_geodesic_propagation(transaction: Any, propagation_plan: Any) -> bool:
    """
    Validates that a transaction is ready to be propagated.
    Ensures that it contains registered participants, snapshots, and is sandboxed.
    """
    if not getattr(transaction, "participants", []):
        return False
    if not getattr(transaction, "sandbox", True):
        return False
    if getattr(transaction, "rollback_snapshot", None) is None:
        return False
    return True


def block_commit_on_unstable_propagation(report: Any) -> bool:
    """
    Returns True if geodesic propagation is unstable or safety gates fail.
    """
    stable = getattr(report, "stable", True)
    passed_gates = getattr(report, "passed_gates", True)
    if isinstance(report, dict):
        stable = report.get("stable", True)
        passed_gates = report.get("passed_gates", True)
        
    if not stable or not passed_gates:
        return True
    return False


def export_atomic_participant_state(transaction: Any) -> Dict[str, Dict[str, Any]]:
    """
    Exports participant states for atomic validation.
    """
    states = {}
    participants = getattr(transaction, "participants", []) or []
    if isinstance(transaction, dict):
        participants = transaction.get("participants", [])
        
    for p in participants:
        p_id = getattr(p, "participant_id", "") or (p.get("participant_id") if isinstance(p, dict) else "")
        status = getattr(p, "status", "idle") or (p.get("status") if isinstance(p, dict) else "idle")
        metadata = getattr(p, "metadata", {}) or (p.get("metadata") if isinstance(p, dict) else {})
        states[p_id] = {
            "status": status,
            "metadata": dict(metadata) if isinstance(metadata, dict) else {}
        }
    return states


def validate_atomic_participant_prepare_state(participant_state: Dict[str, Any]) -> bool:
    """
    Validates that a participant state is prepared and has no failures.
    """
    status = participant_state.get("status", "idle")
    if status != "prepared":
        return False
    meta = participant_state.get("metadata", {}) or {}
    if meta.get("prepare_fails") or meta.get("locks_missing"):
        return False
    return True


def block_partial_commit_risk(report: Any) -> bool:
    """
    Blocks commit if partial commit risk is detected.
    Returns True if any participant failed prepare, or is missing rollback snapshot,
    or if the commit success status is False.
    """
    if not report:
        return True
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    passed = extract(report, "passed_gates") or extract(report, "success")
    if not passed:
        return True
        
    tx = extract(report, "transaction")
    if tx:
        participants = extract(tx, "participants") or []
        for p in participants:
            status = extract(p, "status")
            if status == "aborted" or status == "failed":
                return True
        # Check snapshot
        snapshot = extract(tx, "rollback_snapshot")
        if not snapshot:
            meta = extract(tx, "metadata", {}) or {}
            if not meta.get("rollback_snapshots") and not meta.get("rollback_snapshots_present"):
                return True
                
    return False

