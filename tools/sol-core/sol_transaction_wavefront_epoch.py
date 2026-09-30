# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Transaction Wavefront Epoch
===============================
Coordinates transaction wavefront checkpoints, commit barriers, and epoch status.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class WavefrontPropagationCheckpoint:
    checkpoint_id: str
    manifold_id: str
    completed: bool
    state_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WavefrontCommitBarrier:
    barrier_id: str
    required_checkpoints: List[str] = field(default_factory=list)
    satisfied: bool = False

@dataclass
class TransactionWavefrontEpoch:
    epoch_id: str
    transaction_intent: Any  # MultiManifoldTransactionIntent
    propagation_intent: Any  # GeodesicPropagationIntent
    checkpoints: Dict[str, WavefrontPropagationCheckpoint] = field(default_factory=dict)
    barrier: WavefrontCommitBarrier = field(default_factory=WavefrontCommitBarrier)
    status: str = "active"  # "active" | "committed" | "aborted"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WavefrontTransactionResult:
    success: bool
    epoch_id: str
    committed: bool
    rolled_back: bool
    rollback_reason: Optional[str]
    errors: List[str] = field(default_factory=list)

@dataclass
class WavefrontTransactionReport:
    report_id: str
    result: WavefrontTransactionResult
    passed_gates: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

def start_wavefront_transaction_epoch(transaction_intent: Any, propagation_intent: Any) -> TransactionWavefrontEpoch:
    epoch_id = f"TWEPOCH_{transaction_intent.transaction_id}_{int(time.time())}"
    
    required = list(transaction_intent.target_manifolds)
    barrier = WavefrontCommitBarrier(
        barrier_id=f"BAR_{epoch_id}",
        required_checkpoints=required,
        satisfied=False
    )
    
    return TransactionWavefrontEpoch(
        epoch_id=epoch_id,
        transaction_intent=transaction_intent,
        propagation_intent=propagation_intent,
        checkpoints={},
        barrier=barrier,
        status="active",
        metadata=dict(transaction_intent.metadata)
    )

def register_wavefront_checkpoint(epoch: TransactionWavefrontEpoch, checkpoint: WavefrontPropagationCheckpoint) -> None:
    epoch.checkpoints[checkpoint.manifold_id] = checkpoint
    # Re-evaluate barrier
    epoch.barrier.satisfied = evaluate_wavefront_commit_barrier(epoch)

def evaluate_wavefront_commit_barrier(epoch: TransactionWavefrontEpoch) -> bool:
    if not epoch.barrier.required_checkpoints:
        return False
    for req_m in epoch.barrier.required_checkpoints:
        checkpoint = epoch.checkpoints.get(req_m)
        if checkpoint is None or not checkpoint.completed:
            return False
    return True

def commit_shadow_wavefront_transaction(epoch: TransactionWavefrontEpoch) -> WavefrontTransactionReport:
    errors = []
    satisfied = evaluate_wavefront_commit_barrier(epoch)
    
    if not satisfied:
        errors.append("Commit barrier not satisfied: missing or incomplete checkpoints.")
        epoch.status = "aborted"
        result = WavefrontTransactionResult(
            success=False,
            epoch_id=epoch.epoch_id,
            committed=False,
            rolled_back=True,
            rollback_reason="Commit barrier not satisfied.",
            errors=errors
        )
    else:
        epoch.status = "committed"
        result = WavefrontTransactionResult(
            success=True,
            epoch_id=epoch.epoch_id,
            committed=True,
            rolled_back=False,
            rollback_reason=None,
            errors=[]
        )
        
    return WavefrontTransactionReport(
        report_id=f"TWRPT_{epoch.epoch_id}",
        result=result,
        passed_gates=result.success,
        metadata={"status": epoch.status}
    )

def abort_wavefront_transaction(epoch: TransactionWavefrontEpoch, reason: str) -> WavefrontTransactionReport:
    epoch.status = "aborted"
    result = WavefrontTransactionResult(
        success=False,
        epoch_id=epoch.epoch_id,
        committed=False,
        rolled_back=True,
        rollback_reason=reason,
        errors=[reason]
    )
    return WavefrontTransactionReport(
        report_id=f"TWRPT_{epoch.epoch_id}",
        result=result,
        passed_gates=False,
        metadata={"status": epoch.status}
    )


def export_wavefront_epoch_evidence(report: Any) -> Dict[str, Any]:
    """
    Exports wavefront transaction epoch evidence details.
    """
    result = getattr(report, "result", None)
    committed = getattr(result, "committed", False) if result else False
    rolled_back = getattr(result, "rolled_back", False) if result else False
    
    checkpoints_ok = committed and not rolled_back
    barrier_ok = committed and not rolled_back
    rollback_present = True
    partial_prop = rolled_back or not committed
    
    metadata = getattr(report, "metadata", {}) or {}
    split_brain = metadata.get("split_brain_detected", False)
    
    return {
        "checkpoints_complete": checkpoints_ok,
        "commit_barrier_satisfied": barrier_ok,
        "rollback_path_present": rollback_present,
        "no_partial_propagation": not partial_prop,
        "no_split_brain_epoch": not split_brain
    }


def validate_wavefront_epoch_for_promotion(report: Any) -> bool:
    """
    Validates if wavefront epoch report is acceptable for promotion.
    """
    evidence = export_wavefront_epoch_evidence(report)
    return all(evidence.values())
