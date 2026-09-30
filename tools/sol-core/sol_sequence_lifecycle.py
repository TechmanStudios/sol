# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Multi-Sequence Lifecycle
============================
Tracks sequence lifecycle states, identifies completed or abandoned sequences,
and builds lifecycle compaction reports.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class SequenceLifecycleState:
    sequence_id: str
    status: str  # "running" | "completed" | "abandoned"
    step_count: int
    age_steps: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SequenceCompactionPlan:
    plan_id: str
    sequences_to_compact: List[SequenceLifecycleState]
    tombstone_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SequenceGCReport:
    report_id: str
    plan: SequenceCompactionPlan
    compacted_sequence_ids: List[str] = field(default_factory=list)
    passed_gates: bool = False
    reproducibility_hash: str = ""


def analyze_sequence_lifecycle(
    sequences: List[Any]
) -> List[SequenceLifecycleState]:
    """
    Normalizes a list of sequences (either dicts or SequenceLifecycleState instances)
    into SequenceLifecycleState list.
    """
    normalized = []
    for seq in sequences:
        if isinstance(seq, SequenceLifecycleState):
            normalized.append(seq)
        elif isinstance(seq, dict):
            normalized.append(SequenceLifecycleState(
                sequence_id=seq.get("sequence_id", "unknown"),
                status=seq.get("status", "running"),
                step_count=seq.get("step_count", 0),
                age_steps=seq.get("age_steps", 0),
                metadata=seq.get("metadata", {})
            ))
    return normalized


def identify_completed_sequences(
    sequences: List[Any]
) -> List[SequenceLifecycleState]:
    """
    Returns sequences whose status is completed.
    """
    states = analyze_sequence_lifecycle(sequences)
    return [s for s in states if s.status == "completed"]


def identify_abandoned_sequences(
    sequences: List[Any],
    policy: Any
) -> List[SequenceLifecycleState]:
    """
    Returns sequences whose status is abandoned or who are older than min_age_steps.
    """
    states = analyze_sequence_lifecycle(sequences)
    min_age = getattr(policy, "min_age_steps", 10)
    
    abandoned = []
    for s in states:
        if s.status == "abandoned" or s.age_steps >= min_age:
            abandoned.append(s)
    return abandoned


def build_sequence_compaction_plan(
    sequences: List[Any],
    policy: Any
) -> SequenceCompactionPlan:
    """
    Plans lifecycle compaction, ensuring completed and abandoned sequences are candidate.
    """
    completed = identify_completed_sequences(sequences)
    abandoned = identify_abandoned_sequences(sequences, policy)
    
    all_candidates = []
    seen = set()
    for s in completed + abandoned:
        if s.sequence_id not in seen:
            seen.add(s.sequence_id)
            all_candidates.append(s)
            
    plan = SequenceCompactionPlan(
        plan_id=f"SEQ_COMP_{int(time.time())}",
        sequences_to_compact=all_candidates,
        tombstone_required=getattr(policy, "tombstone_before_delete", True)
    )
    return plan
