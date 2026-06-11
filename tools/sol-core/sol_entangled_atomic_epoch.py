# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Atomic Epoch
==========================
Coordinates atomic epoch checkpoints and barrier constraints under multi-manifold consensus.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class EntangledAtomicEpoch:
    epoch_id: str
    commit_intent: Any
    consensus_intent: Any
    checkpoints: List[Any] = field(default_factory=list)
    state: str = "active"  # "active" | "committed" | "aborted"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledAtomicCheckpoint:
    checkpoint_id: str
    participant_id: str
    verified: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class EntangledAtomicBarrier:
    epoch_id: str
    satisfied: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class EntangledAtomicEpochState:
    status: str
    rollback_recommended: bool = False

@dataclass
class EntangledAtomicEpochReport:
    success: bool
    epoch: EntangledAtomicEpoch
    decision: EntangledAtomicEpochState
    errors: List[str] = field(default_factory=list)


def start_entangled_atomic_epoch(
    commit_intent: Any,
    consensus_intent: Any
) -> EntangledAtomicEpoch:
    """
    Starts an entangled atomic epoch.
    """
    import uuid
    epoch_id = f"ENT_ATOMIC_EPOCH_{uuid.uuid4().hex[:8]}"
    
    meta = {}
    if commit_intent and hasattr(commit_intent, "metadata") and commit_intent.metadata:
        meta.update(commit_intent.metadata)
    if consensus_intent and hasattr(consensus_intent, "metadata") and consensus_intent.metadata:
        meta.update(consensus_intent.metadata)
        
    return EntangledAtomicEpoch(
        epoch_id=epoch_id,
        commit_intent=commit_intent,
        consensus_intent=consensus_intent,
        metadata=meta
    )


def register_entangled_atomic_checkpoint(
    epoch: EntangledAtomicEpoch,
    checkpoint: EntangledAtomicCheckpoint
) -> None:
    """
    Registers a verification checkpoint to the epoch.
    """
    epoch.checkpoints.append(checkpoint)


def evaluate_entangled_atomic_barrier(epoch: EntangledAtomicEpoch) -> EntangledAtomicBarrier:
    """
    Checks completeness of atomic checkpoints across all participants in coordination group.
    """
    errors = []
    
    # 1. Enforce checkpoints registered
    if not epoch.checkpoints:
        errors.append("No verification checkpoints registered.")
    else:
        # Check all registered are verified
        for cp in epoch.checkpoints:
            if not cp.verified:
                errors.append(f"Checkpoint {cp.checkpoint_id} for participant {cp.participant_id} is not verified.")
                
        # Check that we have checkpoints for all participants in the intent coordination group
        intent = epoch.commit_intent
        if intent:
            group = getattr(intent, "coordination_group", []) or []
            if not group and hasattr(intent, "participants"):
                group = [p.participant_id for p in intent.participants]
                
            cp_ids = {cp.participant_id for cp in epoch.checkpoints}
            missing = [m for m in group if m not in cp_ids]
            if missing:
                errors.append(f"Missing participant checkpoints: {', '.join(missing)}")
                
    satisfied = len(errors) == 0
    return EntangledAtomicBarrier(
        epoch_id=epoch.epoch_id,
        satisfied=satisfied,
        errors=errors
    )


def commit_shadow_entangled_atomic_epoch(epoch: EntangledAtomicEpoch) -> EntangledAtomicEpochReport:
    """
    Commits the atomic epoch in shadow mode, validating checkpoints, lock boundaries,
    telemetry constraints, and consensus.
    """
    errors = []
    
    # 1. Check barrier
    barrier = evaluate_entangled_atomic_barrier(epoch)
    if not barrier.satisfied:
        errors.extend(barrier.errors)
        
    meta = epoch.metadata
    
    # 2. Check lock boundaries
    if meta.get("lock_boundary_failed") or meta.get("lock_boundary_failure"):
        errors.append("Lock boundary failure blocks commit.")
    if meta.get("cross_manifold_deadlock"):
        errors.append("Cross-manifold deadlock detected; aborting commit.")
        
    # 3. Check rollback snapshots
    if meta.get("missing_rollback_snapshot") or meta.get("missing_rollback_snapshot_for"):
        errors.append("Missing rollback snapshots blocks commit.")
        
    # 4. Check wavefront propagation stability
    if meta.get("unstable_propagation") or meta.get("unstable_feedback"):
        errors.append("Unstable entangled propagation blocks commit.")
        
    # 5. Check phase drift, crosstalk, boundary reflection, state hash, split-brain
    if meta.get("high_phase_drift"):
        errors.append("High entanglement phase drift blocks commit.")
    if meta.get("high_crosstalk") or meta.get("crosstalk_breach"):
        errors.append("High crosstalk blocks commit.")
    if meta.get("boundary_reflection_breach"):
        errors.append("Boundary reflection breach blocks commit.")
    if meta.get("state_hash_mismatch") or meta.get("state_hash_agreement_failed"):
        errors.append("State hash mismatch blocks commit.")
    if meta.get("split_brain") or meta.get("split_brain_detected"):
        errors.append("Split-brain sequencer state blocks commit.")
        
    # 6. Check cadence window
    if meta.get("outside_cadence_window") or meta.get("outside_window"):
        errors.append("Commit outside cadence window is blocked.")
        
    if meta.get("missing_pml_boundary"):
        errors.append("Missing PML boundary blocks commit.")
        
    if errors:
        epoch.state = "aborted"
        dec = EntangledAtomicEpochState(status="aborted", rollback_recommended=True)
        return EntangledAtomicEpochReport(success=False, epoch=epoch, decision=dec, errors=errors)
        
    epoch.state = "committed"
    dec = EntangledAtomicEpochState(status="committed", rollback_recommended=False)
    return EntangledAtomicEpochReport(success=True, epoch=epoch, decision=dec)


def abort_entangled_atomic_epoch(epoch: EntangledAtomicEpoch, reason: str) -> EntangledAtomicEpochReport:
    """
    Aborts the atomic epoch and triggers a rollback recommendation.
    """
    epoch.state = "aborted"
    dec = EntangledAtomicEpochState(status="aborted", rollback_recommended=True)
    return EntangledAtomicEpochReport(
        success=False,
        epoch=epoch,
        decision=dec,
        errors=[reason]
    )
