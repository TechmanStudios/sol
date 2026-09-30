# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Distributed State Relocation
================================
Defines models and routines for relocating distributed state across manifolds, shards,
and lane boundaries, ensuring safety metrics and state identity are preserved.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class StateRelocationParticipant:
    manifold_id: str
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateRelocationSource:
    manifold_id: str
    shard_id: str
    lane_id: Optional[int] = None
    sequencer_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateRelocationTarget:
    manifold_id: str
    shard_id: str
    lane_id: Optional[int] = None
    sequencer_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateRelocationIntent:
    intent_id: str
    source: StateRelocationSource
    target: StateRelocationTarget
    state_refs: List[str]
    policy: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateRelocationStep:
    step_id: str
    action: str  # "prepare" | "transfer" | "verify" | "commit"
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateRelocationPlan:
    plan_id: str
    intent: StateRelocationIntent
    steps: List[StateRelocationStep]
    coordination_group: List[str]
    created_at: float = field(default_factory=time.time)

@dataclass
class StateRelocationResult:
    success: bool
    relocated_refs: List[str]
    rollback_snapshot_ref: Optional[str] = None
    evidence_packet_ref: Optional[str] = None
    errors: List[str] = field(default_factory=list)

@dataclass
class StateRelocationReport:
    report_id: str
    plan: StateRelocationPlan
    result: StateRelocationResult
    passed_gates: bool
    timestamp: float = field(default_factory=time.time)


def build_state_relocation_intent(
    source: StateRelocationSource,
    target: StateRelocationTarget,
    state_refs: List[str],
    policy: str,
    metadata: Optional[Dict[str, Any]] = None
) -> StateRelocationIntent:
    """
    Builds a distributed state relocation intent.
    """
    intent_id = f"SR_INT_{uuid.uuid4().hex[:8]}"
    meta = dict(metadata) if metadata is not None else {}
    return StateRelocationIntent(
        intent_id=intent_id,
        source=source,
        target=target,
        state_refs=state_refs,
        policy=policy,
        metadata=meta
    )


def validate_state_relocation_intent(intent: StateRelocationIntent) -> bool:
    """
    Validates a state relocation intent.
    """
    if not intent.state_refs:
        raise ValueError("Relocation intent must specify at least one state reference.")
    
    # Check if mock tells us to reject
    if intent.metadata.get("missing_source_state") or intent.metadata.get("missing_source"):
        raise ValueError("Source state is missing or invalid; relocation rejected.")
        
    if intent.metadata.get("missing_target_state") or intent.metadata.get("missing_target"):
        raise ValueError("Target state is missing or invalid; relocation rejected.")

    return True


def build_state_relocation_plan(
    intent: StateRelocationIntent,
    coordination_group: List[str]
) -> StateRelocationPlan:
    """
    Builds the state relocation plan steps.
    """
    plan_id = f"SR_PLAN_{uuid.uuid4().hex[:8]}"
    
    # Generate standard protocol steps
    steps = [
        StateRelocationStep(f"STEP_{plan_id}_PREP", "prepare", {"desc": "Lock resources & verify hashes"}),
        StateRelocationStep(f"STEP_{plan_id}_XFER", "transfer", {"desc": "Shadow state transfer"}),
        StateRelocationStep(f"STEP_{plan_id}_VERIFY", "verify", {"desc": "Check coherence & parity"}),
        StateRelocationStep(f"STEP_{plan_id}_COMMIT", "commit", {"desc": "Atomically seal relocated keys"})
    ]
    
    return StateRelocationPlan(
        plan_id=plan_id,
        intent=intent,
        steps=steps,
        coordination_group=coordination_group
    )


def execute_shadow_state_relocation(plan: StateRelocationPlan) -> StateRelocationResult:
    """
    Simulates shadow execution of a state relocation plan.
    """
    meta = plan.intent.metadata
    
    # Check failures simulated via metadata
    errors = []
    if meta.get("failed_prepare") or meta.get("failed_prep"):
        errors.append("Prepare state phase failed during locks or snapshots.")
    if meta.get("failed_transfer"):
        errors.append("State transfer failed due to packet loss or connection drop.")
    if meta.get("failed_verification") or meta.get("failed_verify"):
        errors.append("Target state hash verification failed.")
    if meta.get("failed_consensus"):
        errors.append("State relocation consensus agreement was rejected.")
    if meta.get("failed_commit"):
        errors.append("Atomic commit phase failed in sandbox mode.")

    success = len(errors) == 0
    
    snap_ref = f"SNAP_SR_{plan.plan_id}" if not meta.get("missing_rollback_snapshot") else None
    ev_ref = f"EV_SR_{plan.plan_id}"
    
    return StateRelocationResult(
        success=success,
        relocated_refs=plan.intent.state_refs if success else [],
        rollback_snapshot_ref=snap_ref,
        evidence_packet_ref=ev_ref,
        errors=errors
    )


def compare_state_relocation_before_after(before: Dict[str, Any], after: Dict[str, Any]) -> bool:
    """
    Ensures that relocated state matches before/after comparisons exactly.
    """
    # Simply verify state identity and structure match
    if before.get("state_refs") != after.get("state_refs"):
        return False
    if before.get("state_hash") != after.get("state_hash"):
        return False
    return True


def export_state_relocation_fault_targets(plan: StateRelocationPlan) -> Dict[str, Any]:
    """
    Exports potential target structures (source, target, state references) for fault injection.
    """
    intent = plan.intent
    return {
        "plan_id": plan.plan_id,
        "source_manifold": intent.source.manifold_id,
        "target_manifold": intent.target.manifold_id,
        "state_refs": intent.state_refs,
        "coordination_group": plan.coordination_group
    }


def validate_relocation_result_against_fault_matrix(report: StateRelocationReport, matrix_report: Any) -> bool:
    """
    Validates that a relocation report outcome complies with any active fault matrix triggers.
    If any fault was injected and failed the matrix run, the relocation must not show success.
    """
    if not getattr(matrix_report, "success", True):
        # If any fault was flagged as failed, relocation report must show passed_gates = False
        if getattr(report, "passed_gates", False) or getattr(report.result, "success", False):
            return False
    return True


def validate_state_relocation_after_route_optimization(
    relocation_report: Any,
    route_report: Any
) -> bool:
    """
    Validates state relocation after route optimization.
    Relocation must be blocked (raises ValueError) if the optimized route invalidates
    source state, target state, state hashes, rollback snapshots, locks, or cadence windows.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not route_report:
        return True

    route_success = extract(route_report, "success", False)
    if not route_success:
        raise ValueError("Route optimization failed; state relocation blocked.")

    # Extract plans
    plan = extract(route_report, "plan")
    intent = extract(plan, "intent")
    tx_context = extract(intent, "transaction_report", {}) or {}

    # Check invalidations
    # 1. Source state references
    if extract(tx_context, "missing_source_state", False) or extract(tx_context, "missing_source", False):
        raise ValueError("Route optimization invalidates source state reference; state relocation blocked.")

    # 2. Target state references
    if extract(tx_context, "missing_target_state", False) or extract(tx_context, "missing_target", False):
        raise ValueError("Route optimization invalidates target state reference; state relocation blocked.")

    # 3. State hash agreement
    if extract(tx_context, "state_hash_mismatch", False):
        raise ValueError("Route optimization invalidates state hash agreement; state relocation blocked.")

    # 4. Rollback references
    rollback_snapshots = extract(plan, "rollback_snapshots", [])
    if not rollback_snapshots or extract(tx_context, "missing_rollback_snapshot", False):
        raise ValueError("Route optimization invalidates rollback snapshot references; state relocation blocked.")

    # 5. Lock boundaries
    lock_boundaries = extract(plan, "global_lock_boundaries", [])
    if "lock_boundary_violation" in lock_boundaries or extract(tx_context, "lock_boundary_violation", False):
        raise ValueError("Route optimization invalidates lock boundaries; state relocation blocked.")

    # 6. Cadence boundaries
    cadence_windows = extract(plan, "cadence_windows", [])
    if "outside_cadence_window" in cadence_windows or extract(tx_context, "outside_cadence_window", False):
        raise ValueError("Route optimization invalidates cadence window boundaries; state relocation blocked.")

    return True


def validate_state_refs_after_topology_relocation(
    relocation_report: Any,
    topology_report: Any
) -> bool:
    """
    Validates state references after a topology relocation.
    Raises ValueError if the topology relocation invalidates source, target, state hashes,
    rollback, lane, or carrier bindings.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not topology_report:
        return True

    # Check for topology mismatch failures
    result = extract(topology_report, "result", {})
    success = extract(result, "success", True)
    errors = extract(result, "errors", [])
    
    if not success or errors:
        raise ValueError(f"Topology relocation failed; state relocation blocked. Errors: {errors}")

    plan = extract(topology_report, "plan", {})
    intent = extract(plan, "intent", {})
    topology_refs = extract(intent, "topology_refs", {})

    if topology_refs.get("source_refs_invalid") or topology_refs.get("missing_source"):
        raise ValueError("Topology relocation invalidates source references; state relocation blocked.")
    if topology_refs.get("target_refs_invalid") or topology_refs.get("missing_target"):
        raise ValueError("Topology relocation invalidates target references; state relocation blocked.")
    if topology_refs.get("state_hash_invalid") or topology_refs.get("state_hash_mismatch"):
        raise ValueError("Topology relocation invalidates state hashes; state relocation blocked.")
    if topology_refs.get("rollback_refs_invalid") or topology_refs.get("missing_rollback_snapshot"):
        raise ValueError("Topology relocation invalidates rollback references; state relocation blocked.")
    if topology_refs.get("lane_bindings_invalid") or topology_refs.get("lane_bindings_violated"):
        raise ValueError("Topology relocation invalidates lane bindings; state relocation blocked.")
    if topology_refs.get("carrier_bindings_invalid") or topology_refs.get("carrier_bindings_violated"):
        raise ValueError("Topology relocation invalidates carrier bindings; state relocation blocked.")

    return True


def block_state_relocation_on_topology_mismatch(report: Any) -> bool:
    """
    Blocks state relocation if there is a topology mismatch or failure in the report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    result = extract(report, "result", {})
    success = extract(result, "success", True)
    errors = extract(result, "errors", [])
    if not success or errors:
        raise ValueError(f"State relocation blocked due to topology mismatch: {errors}")
    return True


