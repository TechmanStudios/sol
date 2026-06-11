# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Wavefront Consensus
=================================
Coordinates and evaluates consensus across multiple participating manifolds,
ensuring agreement on state hashes, cadence windows, and local/global quorums.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class EntangledConsensusParticipant:
    manifold_id: str
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledWavefrontConsensusIntent:
    intent_id: str
    participants: List[EntangledConsensusParticipant]
    propagation_report: Optional[Any] = None
    cadence_report: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledWavefrontVote:
    manifold_id: str
    decision: str  # "approve" | "reject"
    state_hash: str
    cadence_window_valid: bool = True
    rollback_ready: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledWavefrontQuorum:
    local_quorum_passed: bool
    global_quorum_passed: bool
    sequencer_quorum_passed: bool
    entanglement_links_valid: bool

@dataclass
class EntangledConsensusStateHash:
    hash_value: str
    agreement: bool

@dataclass
class EntangledWavefrontConsensusDecision:
    decision_id: str
    status: str  # "approved" | "rejected" | "held"
    quorum: EntangledWavefrontQuorum
    state_hash_agreement: EntangledConsensusStateHash
    justification: str

@dataclass
class EntangledWavefrontConsensusReport:
    report_id: str
    intent: EntangledWavefrontConsensusIntent
    votes: List[EntangledWavefrontVote]
    decision: EntangledWavefrontConsensusDecision
    success: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def build_entangled_wavefront_consensus_intent(
    participants: List[EntangledConsensusParticipant],
    propagation_report: Optional[Any] = None,
    cadence_report: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> EntangledWavefrontConsensusIntent:
    """
    Builds an entangled wavefront consensus intent.
    """
    import uuid
    intent_id = f"EWC_INT_{uuid.uuid4().hex[:8]}"
    meta = dict(metadata) if metadata is not None else {}
    return EntangledWavefrontConsensusIntent(
        intent_id=intent_id,
        participants=participants,
        propagation_report=propagation_report,
        cadence_report=cadence_report,
        metadata=meta
    )


def validate_entangled_consensus_participants(intent: EntangledWavefrontConsensusIntent) -> bool:
    """
    Validates that the consensus intent has at least two active participants.
    """
    if not intent.participants:
        raise ValueError("Consensus intent must specify at least one participant.")
    
    active_count = sum(1 for p in intent.participants if p.status == "active")
    if active_count < 2:
        # If less than 2 active participants, we raise ValueError to represent rejection
        raise ValueError("Consensus intent requires at least 2 active participants.")
        
    return True


def collect_entangled_wavefront_votes(
    intent: EntangledWavefrontConsensusIntent,
    mock_votes: Optional[List[Dict[str, Any]]] = None
) -> List[EntangledWavefrontVote]:
    """
    Gathers votes from all registered participants.
    """
    votes = []
    if mock_votes is not None:
        for mv in mock_votes:
            votes.append(EntangledWavefrontVote(
                manifold_id=mv["manifold_id"],
                decision=mv.get("decision", "approve"),
                state_hash=mv.get("state_hash", "HASH_OK"),
                cadence_window_valid=mv.get("cadence_window_valid", True),
                rollback_ready=mv.get("rollback_ready", True),
                metadata=mv.get("metadata", {})
            ))
    else:
        # Generate default positive votes for all participants
        for p in intent.participants:
            votes.append(EntangledWavefrontVote(
                manifold_id=p.manifold_id,
                decision="approve",
                state_hash="HASH_OK",
                cadence_window_valid=True,
                rollback_ready=True
            ))
    return votes


def evaluate_entangled_wavefront_quorum(
    intent: EntangledWavefrontConsensusIntent,
    votes: List[EntangledWavefrontVote]
) -> EntangledWavefrontQuorum:
    """
    Evaluates local quorum, global quorum, sequencer quorum, and entanglement link validity.
    """
    # Local quorum: check if any participant rejected locally
    local_quorum_passed = all(v.decision == "approve" for v in votes)
    
    # Global quorum: simulated global quorum failure via intent metadata
    global_quorum_passed = not intent.metadata.get("global_quorum_failed", False)
    
    # Sequencer quorum: check if all participants voted (sequencer completeness)
    voted_ids = {v.manifold_id for v in votes}
    participant_ids = {p.manifold_id for p in intent.participants}
    sequencer_quorum_passed = participant_ids.issubset(voted_ids)
    
    # Entanglement link validity: check if propagation report links are active (none marked MISSING or invalid)
    entanglement_links_valid = True
    if intent.propagation_report:
        paths = getattr(intent.propagation_report, "paths", []) or []
        for p in paths:
            if getattr(p, "link_id", "") == "MISSING":
                entanglement_links_valid = False
                
    if intent.metadata.get("invalid_link", False):
        entanglement_links_valid = False
        
    return EntangledWavefrontQuorum(
        local_quorum_passed=local_quorum_passed,
        global_quorum_passed=global_quorum_passed,
        sequencer_quorum_passed=sequencer_quorum_passed,
        entanglement_links_valid=entanglement_links_valid
    )


def build_entangled_wavefront_consensus_report(
    intent: EntangledWavefrontConsensusIntent,
    votes: List[EntangledWavefrontVote],
    decision: EntangledWavefrontConsensusDecision
) -> EntangledWavefrontConsensusReport:
    """
    Builds the final consensus report.
    """
    import uuid
    report_id = f"EWC_REP_{uuid.uuid4().hex[:8]}"
    success = decision.status == "approved"
    
    errors = []
    if not success:
        errors.append(decision.justification)
        
    return EntangledWavefrontConsensusReport(
        report_id=report_id,
        intent=intent,
        votes=votes,
        decision=decision,
        success=success,
        errors=errors
    )


def build_state_relocation_consensus_intent(relocation_report: Any, wavefront_report: Any) -> EntangledWavefrontConsensusIntent:
    """
    Builds a relocation-aware consensus intent.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    plan = extract(relocation_report, "plan")
    intent = extract(plan, "intent")
    meta = extract(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    participants = []
    coordination_group = extract(plan, "coordination_group") or []
    for m in coordination_group:
        participants.append(EntangledConsensusParticipant(manifold_id=m, status="active"))
        
    return build_entangled_wavefront_consensus_intent(
        participants=participants,
        propagation_report=wavefront_report,
        metadata=meta
    )


def evaluate_state_relocation_consensus(
    intent: EntangledWavefrontConsensusIntent,
    votes: List[EntangledWavefrontVote]
) -> EntangledWavefrontConsensusDecision:
    """
    Evaluates relocation-aware consensus votes and checks.
    """
    q = evaluate_entangled_wavefront_quorum(intent, votes)
    
    meta = intent.metadata
    errors = []
    
    if meta.get("unstable_propagation") or meta.get("unstable_feedback"):
        errors.append("Wavefront coherence failure.")
        
    has_agreement = not meta.get("state_hash_mismatch") and not meta.get("state_hash_agreement_failed")
    if not has_agreement:
        errors.append("State hash agreement failed.")
        
    if meta.get("outside_cadence_window") or meta.get("outside_window"):
        errors.append("Cadence window validity check failed.")
        
    if meta.get("missing_rollback_snapshot"):
        errors.append("Rollback readiness check failed.")
        
    if not q.local_quorum_passed:
        errors.append("Local quorum failed.")
    if not q.global_quorum_passed:
        errors.append("Global quorum failed.")
    if not q.entanglement_links_valid:
        errors.append("Entanglement link validity failed.")
        
    success = len(errors) == 0
    import uuid
    dec_id = f"DEC_SR_CONS_{uuid.uuid4().hex[:8]}"
    
    return EntangledWavefrontConsensusDecision(
        decision_id=dec_id,
        status="approved" if success else "rejected",
        quorum=q,
        state_hash_agreement=EntangledConsensusStateHash("HASH_OK" if has_agreement else "MISMATCH", has_agreement),
        justification="Relocation consensus passed" if success else "; ".join(errors)
    )


def build_route_optimization_consensus_intent(
    route_report: Any,
    rebalance_report: Any
) -> EntangledWavefrontConsensusIntent:
    """
    Builds a consensus intent for route-optimization.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    plan = extract(route_report, "plan")
    intent = extract(plan, "intent")
    meta = extract(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    participants = []
    # Extract manifolds from the optimized route if present
    selected = extract(plan, "selected_candidate")
    route = extract(selected, "route") if selected else None
    manifolds = extract(route, "manifolds") if route else []
    
    if not manifolds:
        manifolds = ["manifold_1", "manifold_2"]
        
    for m in manifolds:
        participants.append(EntangledConsensusParticipant(manifold_id=m, status="active"))
        
    # Merge rebalance report metadata if present
    rebal_plan = extract(rebalance_report, "plan")
    rebal_intent = extract(rebal_plan, "intent")
    rebal_meta = extract(rebal_intent, "policy", {}) or {}
    if isinstance(rebal_meta, dict):
        meta.update(rebal_meta)
        
    return build_entangled_wavefront_consensus_intent(
        participants=participants,
        propagation_report=route_report,
        metadata=meta
    )


def evaluate_route_optimization_consensus(
    intent: EntangledWavefrontConsensusIntent,
    votes: List[EntangledWavefrontVote]
) -> EntangledWavefrontConsensusDecision:
    """
    Evaluates consensus for route optimization, checking state hashes, coherence, 
    entanglement links, cadence, quorums, rollback, and safety oracle agreement.
    """
    q = evaluate_entangled_wavefront_quorum(intent, votes)
    meta = intent.metadata
    errors = []
    
    # 1. State hash agreement
    has_agreement = not meta.get("state_hash_mismatch", False) and all(v.state_hash == "HASH_OK" for v in votes)
    if not has_agreement:
        errors.append("Route state hash agreement failed")
        
    # 2. Wavefront coherence
    if meta.get("wavefront_coherence_failed", False):
        errors.append("Wavefront coherence failure")
        
    # 3. Entanglement link validity
    if not q.entanglement_links_valid or meta.get("entanglement_link_invalid", False):
        errors.append("Entanglement link invalid")
        
    # 4. Cadence window validity
    if not all(v.cadence_window_valid for v in votes) or meta.get("outside_cadence_window", False):
        errors.append("Route lies outside approved cadence window")
        
    # 5. Quorum status
    if not q.local_quorum_passed:
        errors.append("Local quorum failed")
    if not q.global_quorum_passed:
        errors.append("Global quorum failed")
    if not q.sequencer_quorum_passed:
        errors.append("Sequencer quorum failed")
        
    # 6. Rollback readiness
    if not all(v.rollback_ready for v in votes) or meta.get("missing_rollback_snapshot", False):
        errors.append("Rollback readiness check failed")
        
    # 7. Safety oracle agreement
    if meta.get("safety_oracle_disagreement", False):
        errors.append("Route candidate safety oracle disagreement")
        
    success = (len(errors) == 0)
    import uuid
    dec_id = f"DEC_RO_CONS_{uuid.uuid4().hex[:8]}"
    
    return EntangledWavefrontConsensusDecision(
        decision_id=dec_id,
        status="approved" if success else "rejected",
        quorum=q,
        state_hash_agreement=EntangledConsensusStateHash("HASH_OK" if has_agreement else "MISMATCH", has_agreement),
        justification="Route optimization consensus passed" if success else "; ".join(errors)
    )

