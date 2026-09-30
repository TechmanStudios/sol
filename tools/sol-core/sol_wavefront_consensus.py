# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Wavefront Consensus
=======================
Scaffolds distributed multi-sequencer synchronization and coherent wavefront consensus logic.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

@dataclass
class WavefrontConsensusNode:
    node_id: str
    role: str  # "leader" | "follower" | "observer"
    weight: float = 1.0

@dataclass
class WavefrontConsensusGroup:
    group_id: str
    nodes: List[WavefrontConsensusNode]
    quorum_ratio: float = 0.67
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConsensusProposal:
    proposal_id: str
    proposer_id: str
    proposed_state_hash: str
    timestamp: float = field(default_factory=time.time)
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConsensusVote:
    node_id: str
    vote_id: str
    proposal_id: str
    decision: str  # "approve" | "reject" | "abstain"
    weight: float = 1.0
    signature: str = ""

@dataclass
class ConsensusQuorum:
    total_eligible_weight: float
    total_voted_weight: float
    total_approved_weight: float
    quorum_reached: bool

@dataclass
class ConsensusDecision:
    proposal_id: str
    agreed_state_hash: Optional[str]
    committed: bool
    status: str  # "committed" | "rejected" | "undecided"
    timestamp: float = field(default_factory=time.time)

@dataclass
class WavefrontConsensusReport:
    report_id: str
    proposal: ConsensusProposal
    votes: List[ConsensusVote]
    quorum: ConsensusQuorum
    decision: ConsensusDecision
    passed_gates: bool
    reproducibility_hash: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_consensus_group(
    sequencer_ids: List[str],
    quorum_ratio: float = 0.67
) -> WavefrontConsensusGroup:
    """
    Constructs a wavefront consensus group from list of sequencer IDs.
    """
    nodes = []
    # Make the first sequencer the leader, others followers
    for i, seq_id in enumerate(sequencer_ids):
        role = "leader" if i == 0 else "follower"
        nodes.append(WavefrontConsensusNode(
            node_id=seq_id,
            role=role,
            weight=1.0
        ))
        
    group_id = f"CGROUP_{'_'.join(sequencer_ids)[:30]}"
    return WavefrontConsensusGroup(
        group_id=group_id,
        nodes=nodes,
        quorum_ratio=quorum_ratio,
        metadata={"created_at": time.time()}
    )


def propose_wavefront_state(
    group: WavefrontConsensusGroup,
    state_hash: str,
    evidence: Dict[str, Any]
) -> ConsensusProposal:
    """
    Creates a new ConsensusProposal on behalf of the group's leader node.
    """
    leader_node = next((n for n in group.nodes if n.role == "leader"), group.nodes[0] if group.nodes else None)
    proposer_id = leader_node.node_id if leader_node else "unknown_proposer"
    proposal_id = f"PROP_{group.group_id}_{int(time.time())}"
    
    return ConsensusProposal(
        proposal_id=proposal_id,
        proposer_id=proposer_id,
        proposed_state_hash=state_hash,
        timestamp=time.time(),
        evidence=evidence
    )


def collect_consensus_votes(
    group: WavefrontConsensusGroup,
    proposal: ConsensusProposal,
    mock_votes: Optional[Dict[str, str]] = None
) -> List[ConsensusVote]:
    """
    Collects votes from all nodes in the group. Uses mock_votes dictionary if supplied.
    """
    votes = []
    for node in group.nodes:
        # Default decision is "approve"
        decision = "approve"
        if mock_votes is not None:
            decision = mock_votes.get(node.node_id, "approve")
            
        votes.append(ConsensusVote(
            node_id=node.node_id,
            vote_id=f"VOTE_{node.node_id}_{proposal.proposal_id[:12]}",
            proposal_id=proposal.proposal_id,
            decision=decision,
            weight=node.weight,
            signature=f"sig_{node.node_id}_{proposal.proposed_state_hash[:8]}"
        ))
    return votes


def evaluate_quorum(
    votes: List[ConsensusVote],
    quorum_ratio: float = 0.67
) -> ConsensusQuorum:
    """
    Evaluates votes to check if the quorum requirements are met.
    """
    total_weight = sum(v.weight for v in votes)
    total_voted = sum(v.weight for v in votes if v.decision != "abstain")
    total_approved = sum(v.weight for v in votes if v.decision == "approve")
    
    threshold = total_weight * quorum_ratio
    quorum_reached = total_approved >= (threshold - 0.02)
    
    return ConsensusQuorum(
        total_eligible_weight=total_weight,
        total_voted_weight=total_voted,
        total_approved_weight=total_approved,
        quorum_reached=quorum_reached
    )


def build_consensus_report(
    proposal: ConsensusProposal,
    votes: List[ConsensusVote],
    decision: ConsensusDecision
) -> WavefrontConsensusReport:
    """
    Assembles a comprehensive WavefrontConsensusReport.
    """
    # Recalculate quorum
    total_weight = sum(v.weight for v in votes)
    total_voted = sum(v.weight for v in votes if v.decision != "abstain")
    total_approved = sum(v.weight for v in votes if v.decision == "approve")
    
    # We can assume a default quorum ratio of 0.67 for the check
    threshold = total_weight * 0.67
    quorum_reached = total_approved >= (threshold - 0.02)
    
    quorum = ConsensusQuorum(
        total_eligible_weight=total_weight,
        total_voted_weight=total_voted,
        total_approved_weight=total_approved,
        quorum_reached=quorum_reached
    )
    
    report_id = f"RPT_CONSENSUS_{proposal.proposal_id}"
    
    # Create reproducibility hash
    try:
        ev_str = json.dumps({
            "proposal_id": proposal.proposal_id,
            "state_hash": proposal.proposed_state_hash,
            "quorum_reached": quorum_reached,
            "status": decision.status
        }, sort_keys=True)
        repro_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    except Exception:
        repro_hash = "sha256_fallback"
        
    return WavefrontConsensusReport(
        report_id=report_id,
        proposal=proposal,
        votes=votes,
        quorum=quorum,
        decision=decision,
        passed_gates=quorum_reached and decision.committed,
        reproducibility_hash=repro_hash,
        timestamp=time.time()
    )


def propose_atomic_commit_state(
    transaction: Any,
    consensus_group: WavefrontConsensusGroup
) -> ConsensusProposal:
    """
    Proposes an atomic commit state hash based on a transaction's intent.
    """
    import hashlib
    tx_id = getattr(transaction, "transaction_id", "unknown_tx")
    intent_val = 0
    if hasattr(transaction, "intent") and transaction.intent is not None:
        intent_val = getattr(transaction.intent, "value", 0)
    
    ev_str = f"ATOMIC_{tx_id}_{intent_val}"
    state_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    
    return propose_wavefront_state(
        consensus_group,
        state_hash,
        {"transaction_id": tx_id, "intent_value": intent_val}
    )


def collect_atomic_commit_votes(
    consensus_group: WavefrontConsensusGroup,
    proposal: ConsensusProposal,
    mock_votes: Optional[Dict[str, str]] = None
) -> List[ConsensusVote]:
    """
    Collects consensus votes for an atomic commit proposal.
    """
    return collect_consensus_votes(consensus_group, proposal, mock_votes=mock_votes)


def evaluate_atomic_commit_quorum(
    votes: List[ConsensusVote],
    quorum_ratio: float = 1.0
) -> ConsensusQuorum:
    """
    Evaluates atomic commit votes to verify quorum is reached.
    """
    return evaluate_quorum(votes, quorum_ratio=quorum_ratio)


def propose_multicore_execution_state(
    plan: Any,
    core_group: WavefrontConsensusGroup
) -> ConsensusProposal:
    """
    Proposes a multicore execution state hash based on the parallel plan.
    """
    plan_id = getattr(plan, "plan_id", "plan_multicore")
    if hasattr(plan, "metadata") and isinstance(plan.metadata, dict):
        plan_id = plan.metadata.get("plan_id", plan_id)
        
    instr_count = len(getattr(plan, "instructions", []))
    ev_str = f"MULTICORE_{plan_id}_{instr_count}_{core_group.group_id}"
    state_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    
    return propose_wavefront_state(
        core_group,
        state_hash,
        {"plan_id": plan_id, "instruction_count": instr_count}
    )


def collect_multicore_votes(
    consensus_group: WavefrontConsensusGroup,
    proposal: ConsensusProposal,
    mock_votes: Optional[Dict[str, str]] = None
) -> List[ConsensusVote]:
    """
    Collects votes from all nodes in the multicore consensus group.
    """
    return collect_consensus_votes(consensus_group, proposal, mock_votes=mock_votes)


def evaluate_multicore_quorum(
    votes: List[ConsensusVote],
    quorum_ratio: float = 0.67
) -> ConsensusQuorum:
    """
    Evaluates multicore votes to verify quorum.
    """
    return evaluate_quorum(votes, quorum_ratio=quorum_ratio)


def propose_pipeline_stage_completion(
    stage: Any,
    core_group: WavefrontConsensusGroup
) -> ConsensusProposal:
    """
    Proposes a state hash representing pipeline stage completion.
    """
    stage_name = getattr(stage, "name", str(stage))
    ev_str = f"STAGE_COMPLETE_{stage_name}_{core_group.group_id}"
    state_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    
    return propose_wavefront_state(
        core_group,
        state_hash,
        {"stage_name": stage_name, "group_id": core_group.group_id}
    )


def evaluate_pipeline_stage_quorum(
    stage_report: Any,
    quorum_ratio: float = 0.67
) -> ConsensusQuorum:
    """
    Evaluates vote consensus for stage verification.
    """
    votes = getattr(stage_report, "votes", [])
    if isinstance(stage_report, dict):
        votes = stage_report.get("votes", [])
    return evaluate_quorum(votes, quorum_ratio=quorum_ratio)


def propose_coordination_epoch_state(
    epoch: Any,
    coordination_group: Any
) -> ConsensusProposal:
    """
    Proposes a state hash representing coordination epoch state.
    """
    epoch_id = getattr(epoch, "epoch_id", "epoch_coordination")
    group_id = getattr(coordination_group, "group_id", "group_coordination")
    
    # We check if split_brain is detected
    split_brain = getattr(epoch, "reason", "") == "split_brain_detected"
    
    ev_str = f"COORD_EPOCH_{epoch_id}_{group_id}"
    if split_brain:
        ev_str += "_SPLIT_BRAIN"
        
    state_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    
    if not hasattr(coordination_group, "nodes"):
        from sol_multimanifold_coordinator import _get_manifold_id
        manifold_ids = []
        if hasattr(coordination_group, "manifolds"):
            manifold_ids = [_get_manifold_id(m) for m in coordination_group.manifolds]
        elif hasattr(coordination_group, "registered_manifold_ids"):
            manifold_ids = list(coordination_group.registered_manifold_ids)
        
        if not manifold_ids:
            manifold_ids = ["manifold_mock"]
            
        consensus_group = build_consensus_group(manifold_ids)
        consensus_group.group_id = group_id
    else:
        consensus_group = coordination_group
        
    return propose_wavefront_state(
        consensus_group,
        state_hash,
        {"epoch_id": epoch_id, "group_id": group_id, "split_brain_detected": split_brain}
    )


def collect_multimanifold_coordination_votes(
    epoch: Any,
    coordination_group: Any,
    proposal: ConsensusProposal,
    mock_votes: Optional[Dict[str, str]] = None
) -> List[ConsensusVote]:
    """
    Collects votes from participants for multi-manifold coordination epoch.
    If split-brain is simulated or detected in epoch reason, follower nodes vote reject.
    """
    votes = []
    nodes = getattr(coordination_group, "nodes", [])
    
    # If coordination group nodes are not initialized, build them dynamically
    if not nodes:
        # Check registered participant IDs
        participants = getattr(epoch, "participants", {})
        nodes = []
        for i, p_id in enumerate(participants.keys()):
            role = "leader" if i == 0 else "follower"
            nodes.append(WavefrontConsensusNode(node_id=p_id, role=role))
            
    split_brain = getattr(epoch, "reason", "") == "split_brain_detected"
    
    for node in nodes:
        decision = "approve"
        if mock_votes is not None:
            decision = mock_votes.get(node.node_id, "approve")
        elif split_brain:
            # Under split brain, only leader approves, others reject or abstain
            decision = "approve" if node.role == "leader" else "reject"
            
        votes.append(ConsensusVote(
            node_id=node.node_id,
            vote_id=f"VOTE_{node.node_id}_{proposal.proposal_id[:12]}",
            proposal_id=proposal.proposal_id,
            decision=decision,
            weight=node.weight,
            signature=f"sig_{node.node_id}_{proposal.proposed_state_hash[:8]}"
        ))
    return votes


def evaluate_multimanifold_quorum(
    votes: List[ConsensusVote],
    quorum_ratio: float = 0.67
) -> ConsensusQuorum:
    """
    Evaluates multimanifold consensus votes to verify quorum.
    """
    return evaluate_quorum(votes, quorum_ratio=quorum_ratio)




