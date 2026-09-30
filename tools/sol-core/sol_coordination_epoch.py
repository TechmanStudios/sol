# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Coordination Epoch
======================
Manages coordination epochs, participant registrations, and barrier synchronization checks.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class EpochParticipant:
    participant_id: str
    registered: bool = False
    registered_at: Optional[float] = None

@dataclass
class EpochBarrier:
    barrier_id: str
    required_participants: List[str] = field(default_factory=list)
    satisfied: bool = False

@dataclass
class CoordinationEpoch:
    epoch_id: str
    group: Any  # ManifoldCoordinationGroup
    purpose: str
    participants: Dict[str, EpochParticipant] = field(default_factory=dict)
    barrier: Optional[EpochBarrier] = None
    status: str = "active"  # "active" | "committed" | "aborted"
    reason: Optional[str] = None

@dataclass
class EpochConsensusDecision:
    decision_id: str
    epoch_id: str
    passed: bool
    votes: Dict[str, bool] = field(default_factory=dict)
    quorum_reached: bool = False

@dataclass
class EpochSynchronizationReport:
    report_id: str
    epoch_id: str
    status: str
    barrier_satisfied: bool
    consensus_decision: Optional[EpochConsensusDecision] = None
    timestamp: float = field(default_factory=time.time)


def start_coordination_epoch(group: Any, purpose: str) -> CoordinationEpoch:
    """
    Initializes a new CoordinationEpoch for the given group.
    """
    epoch_id = f"EPOCH_{int(time.time())}"
    
    # Extract expected participant IDs from the coordination group
    required = []
    if hasattr(group, "registered_manifold_ids"):
        required = list(group.registered_manifold_ids)
    elif isinstance(group, dict):
        required = group.get("registered_manifold_ids") or group.get("manifolds") or []
        
    required_str = [str(r) for r in required]
    
    # Pre-populate participants list
    participants = {}
    for p in required_str:
        participants[p] = EpochParticipant(participant_id=p)
        
    barrier = EpochBarrier(
        barrier_id=f"BARR_{epoch_id}",
        required_participants=required_str
    )
    
    return CoordinationEpoch(
        epoch_id=epoch_id,
        group=group,
        purpose=purpose,
        participants=participants,
        barrier=barrier
    )


def register_epoch_participant(epoch: CoordinationEpoch, participant: str) -> None:
    """
    Registers a participant to an active CoordinationEpoch.
    """
    if epoch.status != "active":
        return
        
    if participant in epoch.participants:
        p = epoch.participants[participant]
        p.registered = True
        p.registered_at = time.time()
    else:
        # Dynamic participant registration
        epoch.participants[participant] = EpochParticipant(
            participant_id=participant,
            registered=True,
            registered_at=time.time()
        )


def evaluate_epoch_barrier(epoch: CoordinationEpoch) -> bool:
    """
    Evaluates whether the epoch barrier has been satisfied.
    Epochs prevent split-brain coordination; no participant can proceed
    unless all required participants are accounted for.
    """
    if not epoch.barrier:
        return True
        
    for p in epoch.barrier.required_participants:
        p_state = epoch.participants.get(p)
        if not p_state or not p_state.registered:
            epoch.barrier.satisfied = False
            return False
            
    epoch.barrier.satisfied = True
    return True


def commit_shadow_epoch(epoch: CoordinationEpoch) -> EpochSynchronizationReport:
    """
    Commits an active epoch, setting status to committed.
    """
    barrier_ok = evaluate_epoch_barrier(epoch)
    if not barrier_ok:
        epoch.status = "aborted"
        epoch.reason = "Barrier verification failed: missing registered participant(s)."
    else:
        epoch.status = "committed"
        
    report_id = f"ERPT_{epoch.epoch_id}_{int(time.time())}"
    return EpochSynchronizationReport(
        report_id=report_id,
        epoch_id=epoch.epoch_id,
        status=epoch.status,
        barrier_satisfied=barrier_ok
    )


def abort_epoch(epoch: CoordinationEpoch, reason: str) -> None:
    """
    Aborts a coordination epoch with a specified reason.
    """
    epoch.status = "aborted"
    epoch.reason = reason
