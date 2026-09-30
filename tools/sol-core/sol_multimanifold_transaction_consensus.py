# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Multi-Manifold Transaction Consensus
========================================
Coordinates multi-manifold transaction boundaries, consensus quorums, and states.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

@dataclass
class MultiManifoldTransactionIntent:
    transaction_id: str
    target_manifolds: List[str] = field(default_factory=list)
    initiator_id: str = "coordinator"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ManifoldTransactionParticipant:
    manifold_id: str
    state: str  # "prepare" | "commit" | "abort"
    rollback_snapshot_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiManifoldTransactionBoundary:
    boundary_id: str
    participants: Dict[str, ManifoldTransactionParticipant] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionConsensusEpoch:
    epoch_id: str
    intent: MultiManifoldTransactionIntent
    boundary: MultiManifoldTransactionBoundary
    status: str = "active"  # "active" | "committed" | "aborted"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionConsensusVote:
    node_id: str
    vote_id: str
    decision: str  # "approve" | "reject" | "abstain"
    weight: float = 1.0
    signature: str = ""

@dataclass
class TransactionConsensusDecision:
    decision_id: str
    agreed: bool
    status: str  # "committed" | "aborted" | "undecided"
    timestamp: float = field(default_factory=time.time)

@dataclass
class TransactionConsensusReport:
    report_id: str
    epoch: TransactionConsensusEpoch
    votes: List[TransactionConsensusVote]
    decision: TransactionConsensusDecision
    passed_gates: bool
    reproducibility_hash: str

def build_transaction_consensus_epoch(intent: MultiManifoldTransactionIntent, coordination_group: Any) -> TransactionConsensusEpoch:
    from sol_multimanifold_coordinator import _get_manifold_id
    participants = {}
    for m in coordination_group.manifolds:
        m_id = _get_manifold_id(m)
        if intent.target_manifolds and m_id not in intent.target_manifolds:
            continue
        # Check if there is an existing snapshot ID in intent metadata, fallback to mock snapshot
        snapshot_id = intent.metadata.get("snapshot_ids", {}).get(m_id) or f"SNAP_{m_id}_{intent.transaction_id}"
        participants[m_id] = ManifoldTransactionParticipant(
            manifold_id=m_id,
            state="prepare",
            rollback_snapshot_id=snapshot_id
        )
    boundary = MultiManifoldTransactionBoundary(
        boundary_id=f"BND_{intent.transaction_id}",
        participants=participants
    )
    epoch_id = f"TCEPOCH_{intent.transaction_id}_{int(time.time())}"
    return TransactionConsensusEpoch(
        epoch_id=epoch_id,
        intent=intent,
        boundary=boundary,
        status="active",
        metadata=dict(intent.metadata)
    )

def validate_transaction_boundaries(epoch: TransactionConsensusEpoch) -> bool:
    # Checks if all target manifolds are registered in the boundary and have non-empty snapshot references
    if not epoch.boundary.participants:
        return False
    for p_id, participant in epoch.boundary.participants.items():
        if not participant.rollback_snapshot_id:
            return False
        if participant.state == "abort":
            return False
    return True

def collect_transaction_consensus_votes(epoch: TransactionConsensusEpoch, mock_votes: Optional[Dict[str, str]] = None) -> List[TransactionConsensusVote]:
    votes = []
    split_brain = epoch.metadata.get("split_brain_detected", False) or epoch.intent.metadata.get("split_brain_detected", False)
    
    # Each participant represents a manifold, and we collect votes from them.
    for i, (m_id, participant) in enumerate(epoch.boundary.participants.items()):
        decision = "approve"
        if mock_votes is not None:
            decision = mock_votes.get(m_id, "approve")
        elif participant.state == "abort":
            decision = "reject"
        elif split_brain and i > 0:
            # Followers vote reject in split brain condition
            decision = "reject"
            
        votes.append(TransactionConsensusVote(
            node_id=m_id,
            vote_id=f"TVOTE_{m_id}_{epoch.epoch_id[:12]}",
            decision=decision,
            weight=1.0,
            signature=f"tsig_{m_id}_{decision}"
        ))
    return votes

def evaluate_transaction_consensus_quorum(epoch: TransactionConsensusEpoch, votes: List[TransactionConsensusVote]) -> TransactionConsensusDecision:
    total_weight = sum(v.weight for v in votes)
    total_approved = sum(v.weight for v in votes if v.decision == "approve")
    
    quorum_ratio = epoch.metadata.get("quorum_ratio", 0.67)
    global_quorum = (total_approved >= (total_weight * quorum_ratio - 0.02)) if total_weight > 0 else False
    
    # Local manifold quorum: in this scaffold, we treat each manifold participant vote as a required local quorum check.
    # If any manifold participant vote is reject, local quorum fails for that manifold.
    local_quorum = all(v.decision == "approve" for v in votes)
    
    agreed = global_quorum and local_quorum and (epoch.status != "aborted")
    
    # Check participant states: if any participant is in abort state, we cannot commit
    for participant in epoch.boundary.participants.values():
        if participant.state == "abort":
            agreed = False
            
    status = "committed" if agreed else "aborted"
    
    decision_id = f"TDEC_{epoch.epoch_id}"
    return TransactionConsensusDecision(
        decision_id=decision_id,
        agreed=agreed,
        status=status,
        timestamp=time.time()
    )

def build_transaction_consensus_report(epoch: TransactionConsensusEpoch, votes: List[TransactionConsensusVote], decision: TransactionConsensusDecision) -> TransactionConsensusReport:
    report_id = f"TRPT_{epoch.epoch_id}"
    
    try:
        ev_str = json.dumps({
            "epoch_id": epoch.epoch_id,
            "agreed": decision.agreed,
            "status": decision.status,
            "vote_count": len(votes)
        }, sort_keys=True)
        repro_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    except Exception:
        repro_hash = "sha256_fallback"
        
    return TransactionConsensusReport(
        report_id=report_id,
        epoch=epoch,
        votes=votes,
        decision=decision,
        passed_gates=decision.agreed,
        reproducibility_hash=repro_hash
    )


def export_transaction_consensus_evidence(report: Any) -> Dict[str, Any]:
    """
    Exports consensus evidence packet details.
    """
    epoch = getattr(report, "epoch", None)
    decision = getattr(report, "decision", None)
    votes = getattr(report, "votes", [])
    
    local_ok = True
    for v in votes:
        if getattr(v, "decision", "") == "reject":
            local_ok = False
            
    participants = {}
    if epoch and getattr(epoch, "boundary", None):
        for m_id, p in epoch.boundary.participants.items():
            participants[m_id] = {
                "state": getattr(p, "state", "unknown"),
                "rollback_snapshot_id": getattr(p, "rollback_snapshot_id", "")
            }
            
    return {
        "local_quorum_status": "passed" if local_ok else "failed",
        "global_quorum_status": "passed" if (decision and getattr(decision, "agreed", False)) else "failed",
        "participant_status": participants,
        "prepare_commit_abort_states": [p.get("state") for p in participants.values()] if participants else [],
        "split_brain_status": "detected" if (epoch and getattr(epoch, "metadata", {}).get("split_brain_detected")) else "clean"
    }


def validate_consensus_for_promotion(report: Any) -> bool:
    """
    Validates if consensus report is clean for level promotion.
    """
    evidence = export_transaction_consensus_evidence(report)
    if evidence["local_quorum_status"] != "passed":
        return False
    if evidence["global_quorum_status"] != "passed":
        return False
    if evidence["split_brain_status"] == "detected":
        return False
    return True


def build_cadence_aware_transaction_consensus_epoch(intent: MultiManifoldTransactionIntent, coordination_group: Any, cadence_group: Any) -> TransactionConsensusEpoch:
    """
    Builds a transaction consensus epoch that is aware of cadence synchronization.
    """
    epoch = build_transaction_consensus_epoch(intent, coordination_group)
    epoch.cadence_group = cadence_group
    epoch.metadata["cadence_sync_group_id"] = getattr(cadence_group, "sync_group_id", "MOCK_SYNC_GP")
    return epoch


def validate_transaction_cadence_boundaries(epoch: TransactionConsensusEpoch) -> bool:
    """
    Validates that all target manifolds in transaction boundary have associated cadence profiles.
    """
    if not validate_transaction_boundaries(epoch):
        return False
        
    cadence_group = getattr(epoch, "cadence_group", None)
    if not cadence_group:
        return False
        
    # Check that every participant manifold has a profile in the sync group
    profiles = getattr(cadence_group, "profiles", {})
    for m_id in epoch.boundary.participants.keys():
        if m_id not in profiles:
            return False
            
    return True


def evaluate_cadence_aware_quorum(epoch: TransactionConsensusEpoch, votes: List[TransactionConsensusVote], cadence_report: Any) -> TransactionConsensusDecision:
    """
    Evaluates local and global quorum, requiring both standard votes consensus and cadence timing stability.
    """
    decision = evaluate_transaction_consensus_quorum(epoch, votes)
    
    # Require cadence stability
    cadence_stable = True
    if cadence_report is not None:
        # Check standard attributes
        success = getattr(cadence_report, "passed_gates", True)
        if hasattr(cadence_report, "result"):
            success = success and getattr(cadence_report.result, "success", True)
        stable = getattr(cadence_report, "stable", True)
        if hasattr(cadence_report, "sync_group"):
            # check sync report
            success = success and (getattr(cadence_report, "global_skew", 0.0) <= 0.05)
        
        cadence_stable = success and stable
        
    if not cadence_stable:
        decision.agreed = False
        decision.status = "aborted"
        
    return decision


def build_entangled_transaction_consensus_epoch(
    intent: MultiManifoldTransactionIntent,
    propagation_paths: List[Any],
    cadence_group: Any
) -> TransactionConsensusEpoch:
    """
    Builds a transaction consensus epoch that is aware of entangled propagation.
    """
    from sol_multimanifold_coordinator import ManifoldCoordinationGroup
    # Determine target manifolds from intent or propagation paths
    target_set = set(intent.target_manifolds)
    for p in propagation_paths:
        src = getattr(p, "source_manifold_id", None)
        tgt = getattr(p, "target_manifold_id", None)
        if src: target_set.add(src)
        if tgt: target_set.add(tgt)
    
    co_group = ManifoldCoordinationGroup("CO_GP_ENTANGLED", list(target_set), set())
    epoch = build_transaction_consensus_epoch(intent, co_group)
    epoch.cadence_group = cadence_group
    epoch.propagation_paths = propagation_paths
    return epoch


def validate_entangled_transaction_boundaries(epoch: TransactionConsensusEpoch) -> bool:
    """
    Validates boundary registration and presence of active entanglement links.
    """
    if not validate_transaction_cadence_boundaries(epoch):
        return False
        
    paths = getattr(epoch, "propagation_paths", [])
    if not paths:
        return False
        
    for path in paths:
        link_id = getattr(path, "link_id", None)
        if not link_id or link_id == "MISSING":
            return False
            
    return True


def evaluate_entangled_transaction_quorum(
    epoch: TransactionConsensusEpoch,
    votes: List[TransactionConsensusVote],
    propagation_report: Any,
    cadence_report: Any
) -> TransactionConsensusDecision:
    """
    Evaluates entangled consensus quorum, checking local/global quorums,
    propagation stability, cadence stability, rollback snapshot presence, and split-brain checks.
    """
    decision = evaluate_cadence_aware_quorum(epoch, votes, cadence_report)
    
    # 1. Enforce entangled propagation stability
    propagation_stable = True
    if propagation_report is not None:
        passed = getattr(propagation_report, "passed_gates", True)
        res = getattr(propagation_report, "result", None)
        if res:
            passed = passed and getattr(res, "success", True)
        propagation_stable = passed
        
    if not propagation_stable:
        decision.agreed = False
        decision.status = "aborted"
        
    # 2. Enforce rollback readiness
    rollback_ok = (
        epoch.metadata.get("rollback_snapshots") or
        epoch.metadata.get("rollback_snapshots_present") or
        epoch.intent.metadata.get("rollback_snapshots")
    )
    if not rollback_ok:
        decision.agreed = False
        decision.status = "aborted"
        
    # 3. Enforce no split-brain state
    if epoch.metadata.get("split_brain") or epoch.metadata.get("split_brain_detected"):
        decision.agreed = False
        decision.status = "aborted"
        
    return decision
