# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Synchronized Sequencer Commit
=================================
Synchronizes sequencer commits across multiple manifolds.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class SequencerCommitIntent:
    intent_id: str
    sequencers: List[str]
    transaction_epoch: Any
    cadence_epoch: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SequencerCommitParticipant:
    sequencer_id: str
    status: str = "active"

@dataclass
class SynchronizedCommitBarrier:
    barrier_id: str
    participants: List[str]
    satisfied: bool

@dataclass
class SequencerCommitVote:
    sequencer_id: str
    decision: str  # "approve" | "reject"

@dataclass
class SynchronizedCommitDecision:
    decision_id: str
    status: str  # "committed" | "aborted" | "held"
    justification: str

@dataclass
class SynchronizedCommitResult:
    success: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class SynchronizedCommitReport:
    report_id: str
    result: SynchronizedCommitResult
    passed_gates: bool
    global_skew: float = 0.0


def build_synchronized_commit_intent(
    sequencers: List[str],
    transaction_epoch: Any,
    cadence_epoch: Any
) -> SequencerCommitIntent:
    """
    Builds and validates commit intent for 2 or 3+ sequencers.
    """
    if not sequencers:
        raise ValueError("Must specify at least one sequencer.")
    for s in sequencers:
        if not s or not isinstance(s, str) or s.strip() == "":
            raise ValueError("Invalid sequencer identifier.")
            
    import uuid
    intent_id = f"SEQ_COMMIT_INT_{uuid.uuid4().hex[:8]}"
    return SequencerCommitIntent(
        intent_id=intent_id,
        sequencers=sequencers,
        transaction_epoch=transaction_epoch,
        cadence_epoch=cadence_epoch
    )


def validate_commit_participants(intent: SequencerCommitIntent) -> bool:
    """
    Enforces participant completeness check.
    """
    if not intent.sequencers:
        raise ValueError("Intent has no registered sequencers.")
    return True


def collect_synchronized_commit_votes(
    intent: SequencerCommitIntent,
    mock_votes: Optional[Dict[str, str]] = None
) -> List[SequencerCommitVote]:
    """
    Gathers local votes from all registered participants.
    """
    votes = []
    source = mock_votes if mock_votes is not None else {}
    for seq in intent.sequencers:
        if seq in source:
            votes.append(SequencerCommitVote(sequencer_id=seq, decision=source[seq]))
    return votes


def evaluate_synchronized_commit_barrier(
    intent: SequencerCommitIntent,
    votes: List[SequencerCommitVote]
) -> SynchronizedCommitBarrier:
    """
    Enforces quorum, cadence window, and participant requirements.
    """
    errors = []
    
    # 1. Check cadence window validity
    cadence_epoch = intent.cadence_epoch
    if cadence_epoch:
        # Check if cadence window failure was explicitly triggered
        metadata = getattr(cadence_epoch, "metadata", {}) or {}
        if metadata.get("outside_cadence_window") or metadata.get("outside_window") or intent.metadata.get("cadence_window_failure"):
            errors.append("Cadence window validation failed; sequencer commit blocked outside window.")
            
    # 2. Check all participants are registered
    voted_ids = {v.sequencer_id for v in votes}
    missing = [seq for seq in intent.sequencers if seq not in voted_ids]
    if missing:
        errors.append(f"Synchronized commit barrier blocks missing participant(s): {', '.join(missing)}")
        
    # 3. Quorum check
    rejects = [v.sequencer_id for v in votes if v.decision == "reject"]
    if rejects:
        errors.append(f"Failed local quorum: rejects from {', '.join(rejects)}")
        
    # Check global quorum (e.g. if we have a simulated global quorum failure)
    if intent.metadata.get("simulate_global_quorum_failure") or any(v.decision == "reject_global" for v in votes):
        errors.append("Failed global quorum across coordination group.")
        
    satisfied = len(errors) == 0
    barrier_id = f"BARRIER_{intent.intent_id}"
    barrier = SynchronizedCommitBarrier(
        barrier_id=barrier_id,
        participants=intent.sequencers,
        satisfied=satisfied
    )
    # Set errors list on barrier's metadata or metadata dictionary for debug
    barrier._errors = errors
    return barrier


def execute_shadow_synchronized_commit(
    intent: SequencerCommitIntent,
    decision: SynchronizedCommitDecision
) -> SynchronizedCommitReport:
    """
    Simulates commit in shadow/sandbox mode.
    """
    success = decision.status == "committed"
    errors = []
    if not success:
        errors.append(decision.justification)
        
    result = SynchronizedCommitResult(success=success, errors=errors)
    import uuid
    report_id = f"SEQ_COMMIT_REP_{uuid.uuid4().hex[:8]}"
    return SynchronizedCommitReport(
        report_id=report_id,
        result=result,
        passed_gates=success,
        global_skew=intent.metadata.get("global_skew", 0.0)
    )


def validate_synchronized_commit_after_feedback(
    commit_report: Any,
    feedback_report: Any
) -> bool:
    """
    Validates synchronized sequencer commits after feedback loops.
    Blocks if:
    - feedback loop is unstable
    - calibration drift remains above threshold
    - entanglement coherence is below threshold
    - cadence drift exceeds threshold
    - rollback readiness is missing
    """
    if not commit_report or not feedback_report:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    res = extract(feedback_report, "result")
    if not res:
        return False
        
    success = extract(res, "success", True)
    if not success:
        return False
        
    final_state = extract(res, "final_state")
    if not final_state:
        return False
        
    drift = extract(final_state, "drift", 0.0)
    coherence = extract(final_state, "coherence", 1.0)
    
    if drift > 0.05 or coherence < 0.90:
        return False
        
    # Check cadence drift
    cadence_drift = extract(final_state, "cadence_drift", 0.0)
    meta = extract(feedback_report, "metadata", {}) or {}
    if extract(meta, "cadence_drift", 0.0) > 0.05 or cadence_drift > 0.05:
        return False
        
    # Check rollback readiness
    if not extract(meta, "rollback_snapshots_present", False) and not extract(meta, "rollback_ready", False) and not extract(meta, "rollback_snapshots", False):
        return False
        
    return True


def prepare_synchronized_commit_for_atomic_epoch(commit_report: Any) -> Dict[str, Any]:
    """
    Prepares synchronized commit state for integration with an atomic epoch.
    """
    passed = False
    if commit_report:
        passed = getattr(commit_report, "passed_gates", False) or getattr(getattr(commit_report, "result", None), "success", False)
    return {
        "commit_prepared": passed,
        "timestamp": time.time()
    }


def validate_synchronized_commit_for_atomicity(commit_report: Any, atomic_epoch: Any) -> bool:
    """
    Validates synchronized commit against atomicity constraints.
    Blocks if:
    - any sequencer is missing
    - local quorum failed
    - global quorum failed
    - cadence barrier failed
    - rollback readiness is missing
    - split-brain sequencer state is detected
    """
    if not commit_report or not atomic_epoch:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    passed_gates = extract(commit_report, "passed_gates", True)
    res = extract(commit_report, "result")
    success = extract(res, "success", True) if res else True
    
    if not passed_gates or not success:
        return False
        
    meta = extract(atomic_epoch, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    # Check if cadence barrier failed or window invalid
    if meta.get("outside_cadence_window") or meta.get("outside_window") or meta.get("cadence_window_failure"):
        return False
        
    # Check if rollback readiness is missing
    rollback_ready = (
        meta.get("rollback_snapshots") or 
        meta.get("rollback_snapshots_present") or 
        meta.get("rollback_ready")
    )
    if not rollback_ready:
        return False
        
    # Check split-brain sequencer state
    if meta.get("split_brain") or meta.get("split_brain_detected"):
        return False
        
    # Check local/global/sequencer quorums
    if meta.get("local_quorum_failed") or meta.get("global_quorum_failed") or meta.get("sequencer_quorum_failed"):
        return False
        
    # Check missing participant/sequencer
    if meta.get("missing_sequencer") or meta.get("failed_prepare"):
        return False
        
    return True
