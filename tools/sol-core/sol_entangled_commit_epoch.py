# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Commit Epoch
==========================
Coordinates transaction commit barriers under entangled wavefront propagation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class EntangledCommitEpoch:
    epoch_id: str
    transaction_intent: Any
    propagation_intent: Any
    cadence_group: Any
    checkpoints: List[Any] = field(default_factory=list)
    state: str = "active"  # "active" | "committed" | "aborted"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledCommitCheckpoint:
    checkpoint_id: str
    participant_id: str
    verified: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class EntangledCommitBarrier:
    epoch_id: str
    satisfied: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class EntangledCommitState:
    status: str
    rollback_recommended: bool = False

@dataclass
class EntangledCommitReport:
    success: bool
    epoch: EntangledCommitEpoch
    decision: Any
    errors: List[str] = field(default_factory=list)


def start_entangled_commit_epoch(
    transaction_intent: Any,
    propagation_intent: Any,
    cadence_group: Any
) -> EntangledCommitEpoch:
    """
    Starts an entangled commit epoch.
    """
    import uuid
    epoch_id = f"ENT_EPOCH_{uuid.uuid4().hex[:8]}"
    
    # Inherit metadata from intents
    meta = {}
    if transaction_intent and hasattr(transaction_intent, "metadata") and transaction_intent.metadata:
        meta.update(transaction_intent.metadata)
    if propagation_intent and hasattr(propagation_intent, "metadata") and propagation_intent.metadata:
        meta.update(propagation_intent.metadata)
        
    return EntangledCommitEpoch(
        epoch_id=epoch_id,
        transaction_intent=transaction_intent,
        propagation_intent=propagation_intent,
        cadence_group=cadence_group,
        metadata=meta
    )


def register_entangled_commit_checkpoint(
    epoch: EntangledCommitEpoch,
    checkpoint: EntangledCommitCheckpoint
) -> None:
    """
    Registers a participant verification checkpoint.
    """
    epoch.checkpoints.append(checkpoint)


def evaluate_entangled_commit_barrier(epoch: EntangledCommitEpoch) -> EntangledCommitBarrier:
    """
    Checks completeness of participant checkpoints.
    """
    errors = []
    
    # 1. Enforce that checkpoints exist
    if not epoch.checkpoints:
        errors.append("No verification checkpoints registered.")
    else:
        # Enforce that all registered checkpoints are verified
        for cp in epoch.checkpoints:
            if not cp.verified:
                errors.append(f"Checkpoint {cp.checkpoint_id} for participant {cp.participant_id} is not verified.")
                
        # For mock test checking of missing participant checkpoints:
        # If the cadence group lists participants, verify we have checkpoints for all of them
        if epoch.cadence_group and hasattr(epoch.cadence_group, "participants"):
            p_ids = {p.manifold_id for p in epoch.cadence_group.participants}
            cp_ids = {cp.participant_id for cp in epoch.checkpoints}
            missing = p_ids - cp_ids
            if missing:
                errors.append(f"Missing participant checkpoints: {', '.join(missing)}")
                
    satisfied = len(errors) == 0
    return EntangledCommitBarrier(
        epoch_id=epoch.epoch_id,
        satisfied=satisfied,
        errors=errors
    )


def commit_shadow_entangled_epoch(epoch: EntangledCommitEpoch) -> EntangledCommitReport:
    """
    Commits the epoch in shadow mode, validating lock, snapshot, and telemetry gates.
    """
    errors = []
    
    # 1. Verify commit barrier is satisfied
    barrier = evaluate_entangled_commit_barrier(epoch)
    if not barrier.satisfied:
        errors.extend(barrier.errors)
        
    # 2. Check lock boundaries
    if epoch.metadata.get("lock_boundary_failed"):
        errors.append("Lock boundary failure blocks commit.")
    if epoch.metadata.get("cross_manifold_deadlock"):
        errors.append("Cross-manifold deadlock detected; aborting commit.")
        
    # 3. Check rollback snapshots
    if not epoch.metadata.get("rollback_snapshots") and not epoch.metadata.get("rollback_snapshots_present"):
        errors.append("Missing rollback snapshots blocks commit.")
        
    # 4. Check wavefront propagation stability
    if epoch.metadata.get("unstable_propagation"):
        errors.append("Unstable entangled propagation blocks commit.")
        
    # 5. Check phase drift, crosstalk, boundary reflection, state hash, split-brain
    if epoch.metadata.get("high_phase_drift"):
        errors.append("High entanglement phase drift blocks commit.")
    if epoch.metadata.get("high_crosstalk"):
        errors.append("High crosstalk blocks commit.")
    if epoch.metadata.get("boundary_reflection_breach"):
        errors.append("Boundary reflection breach blocks commit.")
    if epoch.metadata.get("state_hash_mismatch"):
        errors.append("State hash mismatch blocks commit.")
    if epoch.metadata.get("split_brain"):
        errors.append("Split-brain sequencer state blocks commit.")
        
    if errors:
        epoch.state = "aborted"
        dec = EntangledCommitState(status="aborted", rollback_recommended=True)
        return EntangledCommitReport(success=False, epoch=epoch, decision=dec, errors=errors)
        
    epoch.state = "committed"
    dec = EntangledCommitState(status="committed", rollback_recommended=False)
    return EntangledCommitReport(success=True, epoch=epoch, decision=dec)


def abort_entangled_epoch(epoch: EntangledCommitEpoch, reason: str) -> EntangledCommitReport:
    """
    Aborts the epoch and triggers a rollback recommendation.
    """
    epoch.state = "aborted"
    dec = EntangledCommitState(status="aborted", rollback_recommended=True)
    return EntangledCommitReport(
        success=False,
        epoch=epoch,
        decision=dec,
        errors=[reason]
    )


def register_entangled_calibration_checkpoint(
    epoch: EntangledCommitEpoch,
    calibration_report: Any
) -> None:
    """
    Registers a calibration checkpoint to the epoch.
    """
    if "calibration_checkpoints" not in epoch.metadata:
        epoch.metadata["calibration_checkpoints"] = []
    epoch.metadata["calibration_checkpoints"].append(calibration_report)
    epoch.metadata["calibration_report_present"] = True


def evaluate_entangled_calibration_barrier(epoch: EntangledCommitEpoch) -> EntangledCommitBarrier:
    """
    Evaluates gates required for the calibration barrier.
    """
    errors = []
    meta = epoch.metadata or {}
    
    # 1. Calibration baseline exists
    if not meta.get("calibration_baseline_present") and not meta.get("calibration_baseline"):
        errors.append("Calibration baseline is missing.")
        
    # 2. Feedback loop has completed or held safely
    loop_status = meta.get("feedback_loop_status", "incomplete")
    if not meta.get("feedback_loop_completed") and loop_status not in ["completed", "held"]:
        errors.append("Feedback loop is incomplete or unstable.")
        
    # 3. Stability report is attached
    if not meta.get("stability_report_attached") and not meta.get("stability_report"):
        errors.append("Stability report is not attached.")
        
    # 4. Rollback path is available
    if not meta.get("rollback_path_available") and not meta.get("rollback_ready") and not meta.get("rollback_snapshots_present"):
        errors.append("Rollback path is unavailable.")
        
    # 5. Ranger evidence exists
    if not meta.get("ranger_evidence_complete") and not meta.get("ranger_evidence"):
        errors.append("Ranger evidence is missing.")
        
    satisfied = len(errors) == 0
    return EntangledCommitBarrier(
        epoch_id=epoch.epoch_id,
        satisfied=satisfied,
        errors=errors
    )


def register_atomic_prepare_checkpoint(epoch: EntangledCommitEpoch, prepare_report: Any) -> None:
    """
    Registers an atomic prepare checkpoint to the commit epoch.
    """
    if "atomic_prepare_checkpoints" not in epoch.metadata:
        epoch.metadata["atomic_prepare_checkpoints"] = []
    epoch.metadata["atomic_prepare_checkpoints"].append(prepare_report)
    epoch.metadata["atomic_prepare_present"] = True


def register_atomic_consensus_checkpoint(epoch: EntangledCommitEpoch, consensus_report: Any) -> None:
    """
    Registers an atomic consensus checkpoint to the commit epoch.
    """
    if "atomic_consensus_checkpoints" not in epoch.metadata:
        epoch.metadata["atomic_consensus_checkpoints"] = []
    epoch.metadata["atomic_consensus_checkpoints"].append(consensus_report)
    epoch.metadata["atomic_consensus_present"] = True


def register_atomic_rollback_checkpoint(epoch: EntangledCommitEpoch, rollback_report: Any) -> None:
    """
    Registers an atomic rollback checkpoint to the commit epoch.
    """
    if "atomic_rollback_checkpoints" not in epoch.metadata:
        epoch.metadata["atomic_rollback_checkpoints"] = []
    epoch.metadata["atomic_rollback_checkpoints"].append(rollback_report)
    epoch.metadata["atomic_rollback_present"] = True
