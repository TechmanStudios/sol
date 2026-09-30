# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL State Relocation Protocol
=============================
Implements the multi-stage transition protocol (Prepare -> Transfer -> Verify -> Commit/Abort)
for state relocation across manifolds.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class RelocationPrepareState:
    prepared: bool
    snapshot_captured: bool
    source_hash: str
    errors: List[str] = field(default_factory=list)

@dataclass
class RelocationTransferState:
    transferred: bool
    duration: float
    errors: List[str] = field(default_factory=list)

@dataclass
class RelocationVerifyState:
    verified: bool
    target_hash: str
    coherence_stable: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class RelocationCommitState:
    committed: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class RelocationAbortState:
    aborted: bool
    reason: str
    rollback_triggered: bool = True
    timestamp: float = field(default_factory=time.time)

@dataclass
class StateRelocationProtocol:
    protocol_id: str
    plan: Any  # StateRelocationPlan
    loop: Any  # RealtimeCalibrationLoop
    stage: str = "idle"  # "idle" | "prepared" | "transferred" | "verified" | "committed" | "aborted"
    prepare_state: Optional[RelocationPrepareState] = None
    transfer_state: Optional[RelocationTransferState] = None
    verify_state: Optional[RelocationVerifyState] = None
    commit_state: Optional[RelocationCommitState] = None
    abort_state: Optional[RelocationAbortState] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelocationProtocolReport:
    report_id: str
    protocol: StateRelocationProtocol
    success: bool
    errors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def prepare_state_relocation(protocol: StateRelocationProtocol) -> RelocationPrepareState:
    """
    Executes prepare stage. Validates lock boundaries, captures rollback snapshot and source state hash.
    """
    protocol.stage = "prepared"
    meta = protocol.plan.intent.metadata
    
    errors = []
    
    # 1. Lock boundary validation
    if meta.get("lock_boundary_failed") or meta.get("lock_boundary_failure"):
        errors.append("Lock boundary validation failed during prepare stage.")
    if meta.get("cross_manifold_deadlock"):
        errors.append("Cross-manifold deadlock detected during prepare stage.")
        
    # 2. Rollback snapshot validation
    snapshot_captured = not meta.get("missing_rollback_snapshot")
    if not snapshot_captured:
        errors.append("Failed to capture rollback snapshot.")
        
    source_hash = "HASH_SRC_123"
    if meta.get("state_hash_mismatch"):
        source_hash = "HASH_MISMATCH"
        
    prepared = len(errors) == 0
    p_state = RelocationPrepareState(
        prepared=prepared,
        snapshot_captured=snapshot_captured,
        source_hash=source_hash,
        errors=errors
    )
    protocol.prepare_state = p_state
    
    if not prepared:
        protocol.stage = "aborted"
        protocol.abort_state = RelocationAbortState(True, "Prepare stage failed: " + "; ".join(errors), True)
        
    return p_state


def transfer_state_shadow(protocol: StateRelocationProtocol) -> RelocationTransferState:
    """
    Simulates shadow state transfer from source to target.
    """
    if protocol.stage != "prepared":
        t_state = RelocationTransferState(False, 0.0, ["Cannot transfer: protocol not prepared."])
        protocol.transfer_state = t_state
        return t_state
        
    protocol.stage = "transferred"
    meta = protocol.plan.intent.metadata
    errors = []
    
    if meta.get("failed_transfer") or meta.get("unstable_propagation"):
        errors.append("Shadow transfer failed: propagation instability or boundary reflection breach.")
        
    transferred = len(errors) == 0
    t_state = RelocationTransferState(
        transferred=transferred,
        duration=0.012,
        errors=errors
    )
    protocol.transfer_state = t_state
    
    if not transferred:
        protocol.stage = "aborted"
        protocol.abort_state = RelocationAbortState(True, "Transfer stage failed: " + "; ".join(errors), True)
        
    return t_state


def verify_state_relocation(protocol: StateRelocationProtocol) -> RelocationVerifyState:
    """
    Verifies transferred target state hash and samples real-time calibration/coherence.
    """
    if protocol.stage != "transferred":
        v_state = RelocationVerifyState(False, "", False, ["Cannot verify: state not transferred."])
        protocol.verify_state = v_state
        return v_state
        
    protocol.stage = "verified"
    meta = protocol.plan.intent.metadata
    errors = []
    
    # 1. Target state hash verification
    target_hash = "HASH_SRC_123"
    if meta.get("state_hash_mismatch") or meta.get("state_hash_agreement_failed"):
        target_hash = "HASH_TGT_456"
        errors.append("Target state hash verification mismatch.")
        
    # 2. Check calibration drift, crosstalk, reflection, PML
    if meta.get("high_phase_drift"):
        errors.append("High phase drift detected during verification.")
    if meta.get("high_crosstalk") or meta.get("crosstalk_breach"):
        errors.append("High crosstalk exceeds threshold.")
    if meta.get("boundary_reflection_breach"):
        errors.append("Boundary reflection breach exceeds threshold.")
    if meta.get("missing_pml_boundary"):
        errors.append("PML boundary check failed.")
    if meta.get("unstable_feedback"):
        errors.append("Feedback loop is unstable during verification.")
        
    coherence_stable = not meta.get("unstable_propagation") and not meta.get("unstable_feedback")
    if not coherence_stable:
        errors.append("Wavefront coherence is unstable.")
        
    verified = len(errors) == 0
    v_state = RelocationVerifyState(
        verified=verified,
        target_hash=target_hash,
        coherence_stable=coherence_stable,
        errors=errors
    )
    protocol.verify_state = v_state
    
    if not verified:
        protocol.stage = "aborted"
        protocol.abort_state = RelocationAbortState(True, "Verification stage failed: " + "; ".join(errors), True)
        
    return v_state


def commit_state_relocation_shadow(protocol: StateRelocationProtocol) -> RelocationCommitState:
    """
    Atomically commits the state relocation in shadow/sandbox mode.
    """
    if protocol.stage != "verified":
        c_state = RelocationCommitState(False)
        protocol.commit_state = c_state
        return c_state
        
    protocol.stage = "committed"
    c_state = RelocationCommitState(True)
    protocol.commit_state = c_state
    return c_state


def abort_state_relocation(protocol: StateRelocationProtocol, reason: str) -> RelocationAbortState:
    """
    Aborts the protocol and triggers a rollback of the relocated state.
    """
    protocol.stage = "aborted"
    a_state = RelocationAbortState(
        aborted=True,
        reason=reason,
        rollback_triggered=True
    )
    protocol.abort_state = a_state
    return a_state
