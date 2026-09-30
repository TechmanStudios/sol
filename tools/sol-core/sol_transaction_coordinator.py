# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Distributed Transaction Coordinator
=======================================
Coordinates 2-phase commits, aborts, and rollback schedules across multiple shards.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

@dataclass
class TransactionId:
    tx_id: str

@dataclass
class TransactionParticipant:
    participant_id: str
    status: str = "idle"  # "idle" | "preparing" | "prepared" | "committed" | "aborted"
    state_value: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionIntent:
    intent_id: str
    op: str  # e.g., "COMMIT_WORD"
    value: int
    width: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DistributedTransaction:
    transaction_id: TransactionId
    participants: List[TransactionParticipant]
    intent: TransactionIntent
    sandbox: bool = True
    status: str = "pending"  # "pending" | "preparing" | "prepared" | "committed" | "aborted"
    rollback_snapshot: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionPrepareReport:
    passed: bool
    participant_status: Dict[str, str]
    errors: List[str] = field(default_factory=list)

@dataclass
class TransactionCommitReport:
    success: bool
    committed_value: Optional[int] = None
    errors: List[str] = field(default_factory=list)

@dataclass
class TransactionAbortReport:
    success: bool
    reason: str

@dataclass
class TransactionCoordinatorReport:
    report_id: str
    transaction_id: str
    status: str
    prepare_report: TransactionPrepareReport
    commit_report: Optional[TransactionCommitReport] = None
    abort_report: Optional[TransactionAbortReport] = None
    passed_gates: bool = False
    gate_report: Optional[Any] = None
    reproducibility_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


_ACTIVE_TRANSACTIONS: List[DistributedTransaction] = []

def get_active_transactions() -> List[DistributedTransaction]:
    global _ACTIVE_TRANSACTIONS
    return _ACTIVE_TRANSACTIONS

def register_transaction(transaction: DistributedTransaction) -> None:
    global _ACTIVE_TRANSACTIONS
    _ACTIVE_TRANSACTIONS.append(transaction)

def unregister_transaction(tx_id: str) -> None:
    global _ACTIVE_TRANSACTIONS
    _ACTIVE_TRANSACTIONS = [t for t in _ACTIVE_TRANSACTIONS if getattr(t.transaction_id, "tx_id", str(t.transaction_id)) != tx_id]

def clear_active_transactions() -> None:
    global _ACTIVE_TRANSACTIONS
    _ACTIVE_TRANSACTIONS.clear()


def build_transaction(
    intent: TransactionIntent,
    participants: List[TransactionParticipant],
    sandbox: bool = True
) -> DistributedTransaction:
    """
    Constructs a distributed transaction.
    """
    tx_id = TransactionId(f"TX_{intent.intent_id}_{int(time.time())}")
    tx = DistributedTransaction(
        transaction_id=tx_id,
        participants=participants,
        intent=intent,
        sandbox=sandbox,
        status="pending",
        metadata={"created_at": time.time()}
    )
    register_transaction(tx)
    return tx


def prepare_distributed_transaction(
    transaction: DistributedTransaction
) -> TransactionPrepareReport:
    """
    Prepares the distributed transaction, validating state and locks.
    """
    transaction.status = "preparing"
    for p in transaction.participants:
        p.status = "preparing"
        
    errors = []
    p_status = {}
    
    # Check if a participant is mocked to fail prepare
    for p in transaction.participants:
        prepare_fails = p.metadata.get("prepare_fails", False)
        # Lock missing checks
        locks_missing = p.metadata.get("locks_missing", False)
        
        if prepare_fails:
            p.status = "aborted"
            errors.append(f"Participant {p.participant_id} failed prepare check.")
        elif locks_missing:
            p.status = "aborted"
            errors.append(f"Participant {p.participant_id} cannot prepare due to missing locks.")
        else:
            p.status = "prepared"
            
        p_status[p.participant_id] = p.status
        
    passed = len(errors) == 0
    if passed:
        transaction.status = "prepared"
    else:
        transaction.status = "aborted"
        
    return TransactionPrepareReport(
        passed=passed,
        participant_status=p_status,
        errors=errors
    )


def commit_distributed_transaction(
    transaction: DistributedTransaction,
    token: Any = None
) -> TransactionCommitReport:
    """
    Commits the distributed transaction.
    """
    errors = []
    
    if transaction.status != "prepared":
        transaction.status = "aborted"
        for p in transaction.participants:
            p.status = "aborted"
        return TransactionCommitReport(
            success=False,
            errors=["Transaction is not in prepared status. Commit blocked."]
        )
        
    # Check sandbox live token rules
    sandbox_executed = False
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
            errors.append("Valid sandbox token is required for live commit. Dry-run/shadow execution only.")
    else:
        transaction.status = "aborted"
        for p in transaction.participants:
            p.status = "aborted"
        return TransactionCommitReport(
            success=False,
            errors=["Production/default live distributed write is strictly forbidden."]
        )
        
    # Commit value to participants
    committed_val = transaction.intent.value
    transaction.status = "committed"
    for p in transaction.participants:
        p.status = "committed"
        if sandbox_executed:
            p.state_value = committed_val
            
    return TransactionCommitReport(
        success=True,
        committed_value=committed_val if sandbox_executed else None,
        errors=errors
    )


def abort_distributed_transaction(
    transaction: DistributedTransaction,
    reason: str
) -> TransactionAbortReport:
    """
    Aborts the distributed transaction.
    """
    transaction.status = "aborted"
    for p in transaction.participants:
        p.status = "aborted"
        
    return TransactionAbortReport(
        success=True,
        reason=reason
    )


def summarize_transaction(
    transaction: DistributedTransaction
) -> Dict[str, Any]:
    """
    Provides a status summary of the distributed transaction.
    """
    return {
        "transaction_id": transaction.transaction_id.tx_id,
        "status": transaction.status,
        "participant_count": len(transaction.participants),
        "intent_op": transaction.intent.op,
        "intent_value": transaction.intent.value,
        "sandbox": transaction.sandbox
    }


def validate_bypass_for_transactions(bypass_route: Any, coordinator_report: Optional[Any] = None) -> bool:
    """
    Validates that the bypass route does not violate active transaction isolation,
    held shard locks, rollback snapshots, or atomic commit boundaries.
    """
    metadata = getattr(bypass_route, "metadata", {}) or {}
    if isinstance(bypass_route, dict):
        metadata = bypass_route.get("metadata", {})
        
    if metadata.get("isolation_violation") or metadata.get("lock_held") or metadata.get("rollback_needed") or metadata.get("atomic_violation"):
        return False
        
    source_id = getattr(bypass_route, "source_task_id", "")
    target_id = getattr(bypass_route, "target_task_id", "")
    if "commit" in source_id or "commit" in target_id:
        return False
        
    return True


def validate_rebalance_against_active_transactions(plan: Any, transactions: List[Any]) -> bool:
    """
    Validates rebalance candidates against active coordinator transactions.
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


