# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Transaction Cadence Epoch
=============================
Manages transaction cadence epochs, commit barriers, and consensus checkpoints.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class CadenceConsensusCheckpoint:
    checkpoint_id: str
    manifold_id: str
    tick_index: int
    verified: bool = True

@dataclass
class CadenceCommitBarrier:
    barrier_id: str
    required_ticks: int
    satisfied: bool = False

@dataclass
class TransactionCadenceEpoch:
    epoch_id: str
    transaction_intent: Any
    cadence_group: Any
    checkpoints: List[CadenceConsensusCheckpoint] = field(default_factory=list)
    status: str = "active"  # "active" | "committed" | "aborted"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionCadenceDecision:
    decision_id: str
    status: str  # "committed" | "aborted"
    committed_tick: int
    rollback_refs: List[str] = field(default_factory=list)

@dataclass
class TransactionCadenceReport:
    report_id: str
    epoch: TransactionCadenceEpoch
    decision: TransactionCadenceDecision
    success: bool
    errors: List[str] = field(default_factory=list)


def start_transaction_cadence_epoch(transaction_intent: Any, cadence_group: Any) -> TransactionCadenceEpoch:
    """
    Starts a cadence epoch for a transaction intent.
    Ensures rollback snapshot references are present.
    """
    def extract_meta(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    metadata = extract_meta(transaction_intent, "metadata", {}) or {}
    
    # Check for rollback snapshots
    rollback_present = False
    if metadata.get("rollback_snapshots") or metadata.get("snapshot_ids") or metadata.get("rollback_snapshot_refs"):
        rollback_present = True
        
    if not rollback_present:
        raise ValueError("Cannot start transaction cadence epoch: missing rollback snapshot references.")
        
    epoch_id = f"CAD_EPOCH_{extract_meta(transaction_intent, 'transaction_id', 'unknown')}_{int(time.time() * 1000)}"
    
    return TransactionCadenceEpoch(
        epoch_id=epoch_id,
        transaction_intent=transaction_intent,
        cadence_group=cadence_group,
        metadata=dict(metadata)
    )


def register_cadence_checkpoint(epoch: TransactionCadenceEpoch, checkpoint: CadenceConsensusCheckpoint) -> None:
    """
    Registers a verification checkpoint for a manifold tick.
    """
    epoch.checkpoints.append(checkpoint)


def evaluate_cadence_commit_barrier(epoch: TransactionCadenceEpoch) -> bool:
    """
    Checks if all participating manifolds have registered verified checkpoints for the current tick index.
    """
    if epoch.metadata.get("split_brain_detected") or epoch.metadata.get("split_brain"):
        return False
        
    # Get participating manifolds from cadence sync group or intent target_manifolds
    participants = []
    if hasattr(epoch.cadence_group, "participants"):
        participants = [p.manifold_id for p in epoch.cadence_group.participants]
    elif hasattr(epoch.cadence_group, "profiles"):
        participants = list(epoch.cadence_group.profiles.keys())
        
    if not participants:
        return False
        
    # Check if there is at least one verified checkpoint for each participant
    verified_manifolds = set()
    for cp in epoch.checkpoints:
        if cp.verified:
            verified_manifolds.add(cp.manifold_id)
            
    # Commit barrier satisfied if all participants are verified
    return all(m in verified_manifolds for m in participants)


def commit_shadow_cadence_epoch(epoch: TransactionCadenceEpoch) -> TransactionCadenceReport:
    """
    Commits shadow epoch if cadence barrier is satisfied.
    """
    errors = []
    
    # Check commit barrier
    if not evaluate_cadence_commit_barrier(epoch):
        errors.append("Cannot commit before cadence barrier is satisfied (missing checkpoints or split-brain timing detected)")
        
    # Check if commit is requested outside approved cadence window
    if epoch.metadata.get("outside_cadence_window"):
        errors.append("Transaction commit rejected: outside of approved cadence window boundaries.")
        
    # High drift check
    if epoch.metadata.get("high_cadence_drift"):
        errors.append("Cannot commit: cadence drift exceeds threshold limits.")
        
    success = len(errors) == 0
    status = "committed" if success else "aborted"
    epoch.status = status
    
    committed_tick = max([cp.tick_index for cp in epoch.checkpoints]) if epoch.checkpoints else 0
    
    def extract_meta(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    rollback_snapshots = extract_meta(epoch.transaction_intent, "metadata", {}).get("snapshot_ids", {})
    rollback_refs = list(rollback_snapshots.values()) if isinstance(rollback_snapshots, dict) else []
    
    decision = TransactionCadenceDecision(
        decision_id=f"DEC_CAD_{epoch.epoch_id}",
        status=status,
        committed_tick=committed_tick,
        rollback_refs=rollback_refs
    )
    
    return TransactionCadenceReport(
        report_id=f"REP_CAD_EPOCH_{epoch.epoch_id}",
        epoch=epoch,
        decision=decision,
        success=success,
        errors=errors
    )


def abort_cadence_epoch(epoch: TransactionCadenceEpoch, reason: str) -> TransactionCadenceReport:
    """
    Aborts epoch and logs reason.
    """
    epoch.status = "aborted"
    decision = TransactionCadenceDecision(
        decision_id=f"DEC_CAD_ABORT_{epoch.epoch_id}",
        status="aborted",
        committed_tick=0,
        rollback_refs=[]
    )
    return TransactionCadenceReport(
        report_id=f"REP_CAD_EPOCH_{epoch.epoch_id}",
        epoch=epoch,
        decision=decision,
        success=False,
        errors=[reason]
    )


from sol_temporal_cadence import (
    validate_entangled_commit_cadence,
    measure_entangled_commit_cadence_error,
    validate_atomic_commit_cadence,
    measure_atomic_commit_cadence_error
)
