# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Hierarchical Shard Consensus
================================
Implements local shard-level consensus and global shard-group consensus gating.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

from sol_shard_topology import ShardId, ShardTopology

@dataclass
class ShardConsensusGroup:
    group_id: str
    topology: ShardTopology
    local_quorum: float = 0.67
    global_quorum: float = 0.67
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ShardConsensusProposal:
    proposal_id: str
    shard_id: ShardId
    proposed_state_hash: str
    timestamp: float = field(default_factory=time.time)
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ShardConsensusVote:
    node_id: str
    proposal_id: str
    decision: str  # "approve" | "reject" | "abstain"
    weight: float = 1.0
    signature: str = ""

@dataclass
class ShardConsensusDecision:
    proposal_id: str
    decision: str  # "commit" | "abort"
    quorum_reached: bool
    approved_ratio: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HierarchicalConsensusReport:
    report_id: str
    proposal: ShardConsensusProposal
    local_decisions: Dict[str, ShardConsensusDecision]  # shard_id -> decision
    global_decision: ShardConsensusDecision
    passed_gates: bool
    reproducibility_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_shard_consensus_group(
    topology: ShardTopology,
    local_quorum: float = 0.67,
    global_quorum: float = 0.67
) -> ShardConsensusGroup:
    """
    Constructs a ShardConsensusGroup.
    """
    group_id = f"SCGROUP_{topology.topology_id[:20]}"
    return ShardConsensusGroup(
        group_id=group_id,
        topology=topology,
        local_quorum=local_quorum,
        global_quorum=global_quorum,
        metadata={"created_at": time.time()}
    )


def propose_shard_state(
    group: ShardConsensusGroup,
    shard_id: ShardId,
    state_hash: str,
    evidence: Dict[str, Any]
) -> ShardConsensusProposal:
    """
    Creates a new ShardConsensusProposal.
    """
    proposal_id = f"SPROP_{shard_id.shard_id}_{int(time.time())}"
    return ShardConsensusProposal(
        proposal_id=proposal_id,
        shard_id=shard_id,
        proposed_state_hash=state_hash,
        timestamp=time.time(),
        evidence=evidence
    )


def collect_shard_votes(
    group: ShardConsensusGroup,
    proposal: ShardConsensusProposal,
    mock_votes: Optional[Dict[str, str]] = None
) -> List[ShardConsensusVote]:
    """
    Simulates gathering local shard votes.
    mock_votes contains node_id -> "approve"/"reject"/"abstain" mappings.
    """
    votes = []
    # Mocking 3 validators per shard domain for quorum evaluation
    shard_id = proposal.shard_id.shard_id
    for idx in range(3):
        node_id = f"{shard_id}_val_{idx}"
        decision = "approve"
        if mock_votes is not None:
            decision = mock_votes.get(node_id, mock_votes.get(shard_id, "approve"))
            
        votes.append(ShardConsensusVote(
            node_id=node_id,
            proposal_id=proposal.proposal_id,
            decision=decision,
            weight=1.0,
            signature=f"sig_{node_id}_{proposal.proposed_state_hash[:8]}"
        ))
    return votes


def evaluate_local_quorum(
    votes: List[ShardConsensusVote],
    group: ShardConsensusGroup
) -> ShardConsensusDecision:
    """
    Evaluates local validator votes to check if local quorum is reached.
    """
    total_eligible = sum(v.weight for v in votes)
    total_approved = sum(v.weight for v in votes if v.decision == "approve")
    
    ratio = total_approved / total_eligible if total_eligible > 0 else 0.0
    quorum_reached = ratio >= (group.local_quorum - 1e-5)
    decision = "commit" if quorum_reached else "abort"
    
    proposal_id = votes[0].proposal_id if votes else "unknown"
    
    return ShardConsensusDecision(
        proposal_id=proposal_id,
        decision=decision,
        quorum_reached=quorum_reached,
        approved_ratio=ratio,
        metadata={"total_votes": len(votes), "approved_votes": int(total_approved)}
    )


def evaluate_global_quorum(
    local_decisions: Dict[str, ShardConsensusDecision],
    group: ShardConsensusGroup
) -> ShardConsensusDecision:
    """
    Evaluates global shard decisions to check if overall shard group quorum is reached.
    """
    total_shards = len(group.topology.shards)
    committed_shards = sum(1 for dec in local_decisions.values() if dec.decision == "commit")
    
    ratio = committed_shards / total_shards if total_shards > 0 else 0.0
    quorum_reached = ratio >= (group.global_quorum - 1e-5)
    decision = "commit" if quorum_reached else "abort"
    
    proposal_id = list(local_decisions.values())[0].proposal_id if local_decisions else "unknown"
    
    return ShardConsensusDecision(
        proposal_id=proposal_id,
        decision=decision,
        quorum_reached=quorum_reached,
        approved_ratio=ratio,
        metadata={"total_shards": total_shards, "committed_shards": committed_shards}
    )


def propose_transaction_commit(
    transaction: Any,
    lock_schedule: Any,
    consensus_group: ShardConsensusGroup
) -> ShardConsensusProposal:
    """
    Creates a transaction-aware consensus proposal.
    """
    tx_id_str = getattr(transaction.transaction_id, "tx_id", str(transaction.transaction_id))
    payload = f"{tx_id_str}:{transaction.intent.value}:{transaction.intent.op}"
    state_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    evidence = {
        "transaction_id": tx_id_str,
        "lock_schedule_valid": lock_schedule is not None,
        "all_locks_granted": len(getattr(lock_schedule, "waits", [])) == 0 if lock_schedule else False,
        "has_rollback_snapshot": transaction.rollback_snapshot is not None
    }
    
    shard_id_val = "shard_0"
    if transaction.participants:
        shard_id_val = transaction.participants[0].participant_id
        
    proposal_id = f"TXPROP_{tx_id_str}_{int(time.time())}"
    return ShardConsensusProposal(
        proposal_id=proposal_id,
        shard_id=ShardId(shard_id_val),
        proposed_state_hash=state_hash,
        timestamp=time.time(),
        evidence=evidence
    )


def evaluate_transaction_quorum(
    votes: List[ShardConsensusVote],
    quorum_ratio: float = 0.67
) -> ShardConsensusDecision:
    """
    Evaluates transaction consensus votes against ratio constraints.
    """
    total_weight = sum(v.weight for v in votes)
    total_approved = sum(v.weight for v in votes if v.decision == "approve")
    
    ratio = total_approved / total_weight if total_weight > 0 else 0.0
    quorum_reached = ratio >= (quorum_ratio - 1e-5)
    decision = "commit" if quorum_reached else "abort"
    
    proposal_id = votes[0].proposal_id if votes else "unknown"
    
    return ShardConsensusDecision(
        proposal_id=proposal_id,
        decision=decision,
        quorum_reached=quorum_reached,
        approved_ratio=ratio,
        metadata={"total_votes": len(votes), "approved_votes": int(total_approved)}
    )


def verify_transaction_commit_consensus(
    transaction: Any,
    lock_schedule: Any,
    deadlock_report: Any,
    local_decision: ShardConsensusDecision,
    global_decision: Optional[ShardConsensusDecision] = None
) -> bool:
    """
    Transaction commit requires:
      - local shard lock approval (all locks granted, valid order)
      - local quorum if applicable
      - global quorum if applicable
      - rollback snapshots
      - no deadlock
    """
    # 1. Local shard lock approval
    if not lock_schedule:
        return False
    if len(lock_schedule.waits) > 0 or not lock_schedule.lock_order_valid:
        return False
        
    # 2. No deadlock
    if deadlock_report and deadlock_report.deadlock_detected:
        return False
        
    # 3. Rollback snapshots
    if not getattr(transaction, "rollback_snapshot", None):
        return False
        
    # 4. Local quorum
    if local_decision.decision != "commit":
        return False
        
    # 5. Global quorum
    if global_decision and global_decision.decision != "commit":
        return False
        
    return True
