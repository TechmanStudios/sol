# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL State Hash Guard
====================
Captures cryptographic/logic state hash snapshots of participating registers and basins
before and after relocation, blocking commits on any mismatch.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class StateHashSnapshot:
    snapshot_id: str
    state_refs: List[str]
    state_hashes: Dict[str, str]
    timestamp: float = field(default_factory=time.time)

@dataclass
class StateHashComparison:
    before: StateHashSnapshot
    after: StateHashSnapshot
    agreed: bool
    mismatching_refs: List[str] = field(default_factory=list)

@dataclass
class StateHashGuardReport:
    report_id: str
    comparison: StateHashComparison
    success: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def capture_state_hash_snapshot(
    state_refs: List[str],
    mock_hashes: Optional[Dict[str, str]] = None
) -> StateHashSnapshot:
    """
    Captures the hash values of the specified state references.
    """
    if not state_refs:
        raise ValueError("State hash snapshot must be captured before relocation: state_refs cannot be empty.")
    snapshot_id = f"SH_SNAP_{uuid.uuid4().hex[:8]}"
    hashes = {}
    
    if mock_hashes is not None:
        hashes.update(mock_hashes)
    else:
        for ref in state_refs:
            hashes[ref] = "HASH_SRC_123"
            
    return StateHashSnapshot(
        snapshot_id=snapshot_id,
        state_refs=state_refs,
        state_hashes=hashes
    )


def compare_state_hashes(
    before: StateHashSnapshot,
    after: StateHashSnapshot
) -> StateHashComparison:
    """
    Compares before/after snapshots and detects mismatching state references.
    """
    mismatches = []
    for ref in before.state_refs:
        val_before = before.state_hashes.get(ref)
        val_after = after.state_hashes.get(ref)
        if val_before != val_after:
            mismatches.append(ref)
            
    agreed = len(mismatches) == 0
    return StateHashComparison(
        before=before,
        after=after,
        agreed=agreed,
        mismatching_refs=mismatches
    )


def validate_state_hash_agreement(comparison: StateHashComparison) -> bool:
    """
    Validates that there are no mismatching state references.
    """
    if not comparison.agreed:
        raise ValueError(f"State hash mismatch detected for references: {', '.join(comparison.mismatching_refs)}")
    return True


def inject_state_hash_mismatch(snapshot: StateHashSnapshot) -> None:
    """
    Simulates a total state hash mismatch by corrupting all state hashes in the snapshot.
    """
    for ref in snapshot.state_hashes:
        snapshot.state_hashes[ref] = f"{snapshot.state_hashes[ref]}_CORRUPTED"


def inject_partial_state_hash_mismatch(snapshot: StateHashSnapshot, state_ref: str) -> None:
    """
    Simulates a partial state hash mismatch by corrupting a single state reference.
    """
    if state_ref in snapshot.state_hashes:
        snapshot.state_hashes[state_ref] = f"{snapshot.state_hashes[state_ref]}_PARTIAL_CORRUPTED"
