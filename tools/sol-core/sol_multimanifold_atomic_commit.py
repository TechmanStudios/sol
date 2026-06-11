# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Multi-Manifold Atomic Commit
================================
Implements atomic commit, rollback snapshots, and 2-phase commit barrier evaluations
across multiple independent manifold boundaries.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class AtomicCommitBoundary:
    boundary_id: str
    target_manifolds: List[str]
    locked_shards: List[str]
    pml_coverage_valid: bool = True

@dataclass
class AtomicCommitParticipantState:
    participant_id: str
    status: str  # "idle" | "preparing" | "prepared" | "committed" | "aborted"
    rollback_snapshot_present: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AtomicPrepareWavefront:
    wavefront_id: str
    coherence_stable: bool = True
    drift_within_threshold: bool = True

@dataclass
class MultiManifoldAtomicCommitIntent:
    intent_id: str
    transaction_intent: Any
    coordination_group: List[str]  # list of participating manifold_ids
    boundaries: List[AtomicCommitBoundary] = field(default_factory=list)
    participant_states: Dict[str, AtomicCommitParticipantState] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AtomicCommitBarrier:
    barrier_id: str
    satisfied: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class MultiManifoldAtomicCommitDecision:
    decision_id: str
    status: str  # "commit" | "abort"
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class MultiManifoldAtomicCommitResult:
    success: bool
    committed_value: Optional[int]
    rollback_triggered: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class MultiManifoldAtomicCommitReport:
    report_id: str
    intent: MultiManifoldAtomicCommitIntent
    decision: MultiManifoldAtomicCommitDecision
    result: MultiManifoldAtomicCommitResult
    passed_gates: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def build_multimanifold_atomic_commit_intent(
    transaction_intent: Any,
    coordination_group: List[str],
    metadata: Optional[Dict[str, Any]] = None
) -> MultiManifoldAtomicCommitIntent:
    """
    Builds the multi-manifold atomic commit intent.
    """
    import uuid
    intent_id = f"MM_COMMIT_INT_{uuid.uuid4().hex[:8]}"
    meta = dict(metadata) if metadata is not None else {}
    
    # Inherit metadata from transaction_intent
    if transaction_intent and hasattr(transaction_intent, "metadata") and transaction_intent.metadata:
        meta.update(transaction_intent.metadata)
        
    boundaries = []
    # Build default boundaries
    boundary_id = f"BOUND_{intent_id}"
    boundaries.append(AtomicCommitBoundary(
        boundary_id=boundary_id,
        target_manifolds=coordination_group,
        locked_shards=[f"SHARD_{m}" for m in coordination_group],
        pml_coverage_valid=not meta.get("missing_pml_boundary", False)
    ))
    
    participant_states = {}
    for m in coordination_group:
        # Check if participant is mocked to miss snapshot
        snapshot_present = True
        if meta.get("missing_rollback_snapshot") or meta.get("missing_rollback_snapshot_for") == m:
            snapshot_present = False
            
        participant_states[m] = AtomicCommitParticipantState(
            participant_id=m,
            status="idle",
            rollback_snapshot_present=snapshot_present,
            metadata={}
        )
        
    return MultiManifoldAtomicCommitIntent(
        intent_id=intent_id,
        transaction_intent=transaction_intent,
        coordination_group=coordination_group,
        boundaries=boundaries,
        participant_states=participant_states,
        metadata=meta
    )


def validate_atomic_commit_boundaries(intent: MultiManifoldAtomicCommitIntent) -> bool:
    """
    Validates atomic commit boundaries (e.g. PML coverage, locks).
    """
    if not intent.boundaries:
        raise ValueError("Missing atomic commit boundaries.")
        
    for b in intent.boundaries:
        if not b.pml_coverage_valid:
            raise ValueError(f"PML boundary coverage check failed for boundary {b.boundary_id}")
            
    # Check if lock boundary failure was explicitly triggered
    if intent.metadata.get("lock_boundary_failed") or intent.metadata.get("lock_boundary_failure"):
        raise ValueError("Global lock boundary validation failed; sequencer commit blocked.")
        
    # Check cross-manifold deadlock
    if intent.metadata.get("cross_manifold_deadlock"):
        raise ValueError("Cross-manifold deadlock detected; aborting commit.")
        
    return True


def prepare_multimanifold_atomic_commit(intent: MultiManifoldAtomicCommitIntent) -> List[AtomicCommitParticipantState]:
    """
    Executes prepare step. Updates participant state statuses.
    """
    results = []
    
    # Check prepare failures
    failed_prepare = intent.metadata.get("failed_prepare") or intent.metadata.get("failed_prepare_for")
    
    for m, state in intent.participant_states.items():
        if failed_prepare == m or intent.metadata.get("failed_prepare", False):
            state.status = "aborted"
        else:
            state.status = "prepared"
        results.append(state)
        
    return results


def evaluate_atomic_commit_barrier(
    intent: MultiManifoldAtomicCommitIntent,
    consensus_report: Any
) -> AtomicCommitBarrier:
    """
    Evaluates whether the atomic commit barrier is satisfied.
    Consensus report must be passed/successful. All participants must be prepared and have snapshots.
    """
    errors = []
    barrier_id = f"BARRIER_{intent.intent_id}"
    
    # 1. Consensus report success check
    if not consensus_report:
        errors.append("Wavefront consensus report is missing.")
    else:
        success = getattr(consensus_report, "success", False)
        if not success:
            errors.append(f"Wavefront consensus failed: {getattr(consensus_report, 'errors', ['consensus unapproved'])}")
            
    # 2. Check participant states
    for m, state in intent.participant_states.items():
        if state.status != "prepared":
            errors.append(f"Participant {m} is in status {state.status}, not prepared.")
        if not state.rollback_snapshot_present:
            errors.append(f"Participant {m} is missing rollback snapshot.")
            
    # 3. Check wavefront state hash agreement in consensus report
    if consensus_report:
        dec = getattr(consensus_report, "decision", None)
        if dec:
            hash_agreement = getattr(dec, "state_hash_agreement", None)
            if hash_agreement and not getattr(hash_agreement, "agreement", True):
                errors.append("State hash mismatch across participating manifolds.")
                
    satisfied = len(errors) == 0
    return AtomicCommitBarrier(barrier_id=barrier_id, satisfied=satisfied, errors=errors)


def commit_shadow_multimanifold_atomic(
    intent: MultiManifoldAtomicCommitIntent,
    decision: MultiManifoldAtomicCommitDecision
) -> MultiManifoldAtomicCommitReport:
    """
    Executes commit or abort in shadow mode.
    """
    import uuid
    report_id = f"MM_COMMIT_REP_{uuid.uuid4().hex[:8]}"
    
    success = decision.status == "commit"
    errors = []
    if not success:
        errors.append(decision.justification)
        
    val = None
    if success:
        for m, state in intent.participant_states.items():
            state.status = "committed"
        # Extract intent value if present
        tx_intent = intent.transaction_intent
        val = getattr(tx_intent, "value", None) or (tx_intent.get("value") if isinstance(tx_intent, dict) else None)
    else:
        for m, state in intent.participant_states.items():
            state.status = "aborted"
            
    res = MultiManifoldAtomicCommitResult(
        success=success,
        committed_value=val if success else None,
        rollback_triggered=not success,
        errors=errors
    )
    
    return MultiManifoldAtomicCommitReport(
        report_id=report_id,
        intent=intent,
        decision=decision,
        result=res,
        passed_gates=success,
        errors=errors
    )


def abort_multimanifold_atomic_commit(
    intent: MultiManifoldAtomicCommitIntent,
    reason: str
) -> MultiManifoldAtomicCommitReport:
    """
    Aborts atomic commit and triggers rollback status for all participants.
    """
    import uuid
    report_id = f"MM_ABORT_REP_{uuid.uuid4().hex[:8]}"
    
    for m, state in intent.participant_states.items():
        state.status = "aborted"
        
    dec = MultiManifoldAtomicCommitDecision(
        decision_id=f"DEC_ABORT_{intent.intent_id}",
        status="abort",
        justification=reason
    )
    
    res = MultiManifoldAtomicCommitResult(
        success=False,
        committed_value=None,
        rollback_triggered=True,
        errors=[reason]
    )
    
    return MultiManifoldAtomicCommitReport(
        report_id=report_id,
        intent=intent,
        decision=dec,
        result=res,
        passed_gates=False,
        errors=[reason]
    )


def prepare_atomic_state_relocation(intent: Any, atomic_epoch: Any) -> Any:
    """
    Prepares atomic state relocation, linking it with atomic epoch checkpoint registry.
    """
    meta = getattr(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("failed_prepare") or meta.get("failed_prep"):
        raise ValueError("Failed to prepare state relocation in atomic context.")
    return True


def validate_state_relocation_for_atomic_commit(report: Any, atomic_report: Any) -> bool:
    """
    Validates state relocation report for atomic commit integration.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    result = extract(report, "result")
    success = extract(result, "success", False) if result else extract(report, "success", False)
    
    if not success:
        raise ValueError("State relocation was not successful; atomic commit blocked.")
        
    snap = extract(result, "rollback_snapshot_ref")
    if not snap:
        raise ValueError("Rollback snapshot is missing for relocated state; atomic commit blocked.")
        
    plan = extract(report, "plan")
    intent = extract(plan, "intent")
    meta = extract(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("failed_consensus"):
        raise ValueError("Consensus check failed for relocation; atomic commit blocked.")
        
    if meta.get("missing_rollback_snapshot"):
        raise ValueError("Rollback snapshot missing; atomic commit blocked.")
        
    return True


def validate_optimized_route_for_atomic_commit(
    route_report: Any,
    atomic_commit_report: Optional[Any] = None
) -> bool:
    """
    Validates optimized route before atomic commit. Raises ValueError if boundaries or locks fail.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(route_report, "success", False)
    if not success:
        raise ValueError("Route optimization failed; atomic commit blocked.")

    plan = extract(route_report, "plan")
    if not plan:
        raise ValueError("Missing route plan; atomic commit blocked.")

    intent = extract(plan, "intent")
    tx_context = extract(intent, "transaction_report", {}) or {}
    
    # 1. Transaction boundaries
    if extract(tx_context, "break_transaction_boundaries", False):
        raise ValueError("Route optimization breaks transaction boundaries; atomic commit blocked.")
        
    # 2. Atomic commit boundaries
    if extract(tx_context, "break_atomic_commit_boundaries", False):
        raise ValueError("Route optimization breaks atomic commit boundaries; atomic commit blocked.")

    # 3. Rollback snapshots missing
    rollback_snapshots = extract(plan, "rollback_snapshots", [])
    if not rollback_snapshots:
        raise ValueError("Rollback snapshots are missing; atomic commit blocked.")

    # 4. State hash mismatch
    state_hashes = extract(plan, "state_hash_references", [])
    if not state_hashes or extract(tx_context, "state_hash_mismatch", False):
        raise ValueError("Route state hashes mismatch or missing; atomic commit blocked.")

    # 5. Lock boundary violation
    lock_boundaries = extract(plan, "global_lock_boundaries", [])
    if "lock_boundary_violation" in lock_boundaries or extract(tx_context, "lock_boundary_violation", False):
        raise ValueError("Lock boundaries validation failed; atomic commit blocked.")

    # 6. Cadence windows fail
    cadence_windows = extract(plan, "cadence_windows", [])
    if "outside_cadence_window" in cadence_windows or extract(tx_context, "outside_cadence_window", False):
        raise ValueError("Cadence windows validation failed; route outside cadence window; atomic commit blocked.")

    # 7. Wavefront coherence fails
    if extract(tx_context, "wavefront_coherence_failed", False):
        raise ValueError("Wavefront coherence validation failed; atomic commit blocked.")

    # 8. Partial commit risk
    if extract(tx_context, "partial_commit_risk", False):
        raise ValueError("Partial commit risk detected; atomic commit blocked.")

    return True


def block_atomic_commit_on_unsafe_route_optimization(
    route_report: Any
) -> None:
    """
    Blocks atomic commit explicitly by raising ValueError if the route optimization is unsafe.
    """
    validate_optimized_route_for_atomic_commit(route_report, None)

