# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Live Relocation
===================
Manages token validation, snapshot captures, step execution, and rollbacks for sandbox relocations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class LiveRelocationToken:
    token_id: str
    court_authorization_id: str
    sandbox_scope: bool
    source_id: str  # source core/shard/manifold id
    target_id: str  # target core/shard/manifold id
    expiration: float
    max_relocation_steps: int
    rollback_required: bool
    ranger_observer_id: str
    active: bool = True

@dataclass
class SandboxRelocationRequest:
    request_id: str
    rebalance_plan: Any
    token: LiveRelocationToken
    timestamp: float = field(default_factory=time.time)

@dataclass
class SandboxRelocationSnapshot:
    snapshot_id: str
    request: SandboxRelocationRequest
    before_placement_map: Any  # Copy of original placement map
    manifold_states: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class SandboxRelocationStep:
    step_id: str
    manifold_id: str
    source_core: str
    target_core: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SandboxRelocationPlan:
    plan_id: str
    request: SandboxRelocationRequest
    steps: List[SandboxRelocationStep] = field(default_factory=list)

@dataclass
class SandboxRelocationResult:
    success: bool
    snapshot: SandboxRelocationSnapshot
    after_placement_map: Any
    rolled_back: bool = False
    rollback_reason: Optional[str] = None
    steps_executed: int = 0
    errors: List[str] = field(default_factory=list)

@dataclass
class SandboxRelocationReport:
    report_id: str
    result: SandboxRelocationResult
    passed_gates: bool
    timestamp: float = field(default_factory=time.time)


def build_sandbox_relocation_request(rebalance_plan: Any, token: LiveRelocationToken) -> SandboxRelocationRequest:
    """
    Builds a SandboxRelocationRequest from an accepted rebalance plan and live token.
    """
    req_id = f"REQ_RELOC_{int(time.time())}"
    return SandboxRelocationRequest(
        request_id=req_id,
        rebalance_plan=rebalance_plan,
        token=token
    )


def validate_live_relocation_token(token: LiveRelocationToken) -> bool:
    """
    Validates a live relocation token according to required fields and expiration.
    """
    if not token.active:
        return False
        
    # Expiration check
    if token.expiration < time.time():
        return False
        
    # Sandbox scope required
    if not token.sandbox_scope:
        return False
        
    # Rollback capability required
    if not token.rollback_required:
        return False
        
    # Required authorization ID and observer presence
    if not token.court_authorization_id or not token.ranger_observer_id:
        return False
        
    # Required source and target presence
    if not token.source_id or not token.target_id:
        return False
        
    # Max relocation steps bounds
    if token.max_relocation_steps <= 0:
        return False
        
    return True


def capture_sandbox_relocation_snapshot(request: SandboxRelocationRequest) -> SandboxRelocationSnapshot:
    """
    Captures a rollback snapshot of the current placements before relocation begins.
    """
    import copy
    plan = request.rebalance_plan
    # Try to extract the placement map from rebalance plan references
    original_map = None
    if plan is not None:
        if isinstance(plan, dict):
            original_map = plan.get("placement_map")
        else:
            original_map = getattr(plan, "placement_map", None) or getattr(plan, "topology_reference", None)
            
    if original_map is None and plan is not None:
        if hasattr(plan, "manifold_to_core") or (isinstance(plan, dict) and "manifold_to_core" in plan):
            original_map = plan
            
    # Cloned placement map
    copied_map = copy.deepcopy(original_map)
    snap_id = f"SNAP_RELOC_{int(time.time())}"
    
    return SandboxRelocationSnapshot(
        snapshot_id=snap_id,
        request=request,
        before_placement_map=copied_map
    )



def execute_sandbox_relocation_step(step: SandboxRelocationStep, snapshot: SandboxRelocationSnapshot) -> bool:
    """
    Executes a single relocation step on the sandbox environment copy.
    """
    token = snapshot.request.token
    if not validate_live_relocation_token(token):
        return False
        
    # In sandbox mode, apply move using placement planner helper
    from sol_manifold_placement import plan_manifold_move, apply_sandbox_relocation_move
    
    # Generate proposed move
    move = plan_manifold_move(step.manifold_id, step.source_core, step.target_core)
    
    # We update snapshot's request rebalance_plan placement_map in shadow/sandbox
    plan = snapshot.request.rebalance_plan
    if plan is not None:
        if hasattr(plan, "placement_map") and plan.placement_map is not None:
            updated_map = apply_sandbox_relocation_move(plan.placement_map, move, token)
            plan.placement_map = updated_map
            return True
        elif isinstance(plan, dict) and "placement_map" in plan:
            updated_map = apply_sandbox_relocation_move(plan["placement_map"], move, token)
            plan["placement_map"] = updated_map
            return True
            
    return False


def rollback_sandbox_relocation(snapshot: SandboxRelocationSnapshot, reason: str) -> SandboxRelocationResult:
    """
    Rolls back the sandbox placement maps and references to the captured snapshot state.
    """
    from sol_manifold_placement import restore_sandbox_placement
    
    # Restore original placements on the request rebalance plan reference
    restored_map = restore_sandbox_placement(snapshot)
    
    res = SandboxRelocationResult(
        success=False,
        snapshot=snapshot,
        after_placement_map=restored_map,
        rolled_back=True,
        rollback_reason=reason,
        errors=[f"Relocation rolled back: {reason}"]
    )
    return res


def summarize_sandbox_relocation(result: SandboxRelocationResult) -> Dict[str, Any]:
    """
    Provides a status overview of the relocation trial result.
    """
    return {
        "success": result.success,
        "rolled_back": result.rolled_back,
        "rollback_reason": result.rollback_reason,
        "steps_executed": result.steps_executed,
        "error_count": len(result.errors),
        "snapshot_id": result.snapshot.snapshot_id
    }


@dataclass
class MultiManifoldRelocationRequest:
    request_id: str
    coordination_plan: Any
    tokens: Dict[str, LiveRelocationToken]
    timestamp: float = field(default_factory=time.time)

@dataclass
class MultiManifoldRelocationSnapshot:
    snapshot_id: str
    request: MultiManifoldRelocationRequest
    manifold_snapshots: Dict[str, SandboxRelocationSnapshot]
    timestamp: float = field(default_factory=time.time)


def build_multi_manifold_relocation_request(
    coordination_plan: Any,
    tokens: Dict[str, LiveRelocationToken]
) -> MultiManifoldRelocationRequest:
    """
    Builds a MultiManifoldRelocationRequest from a coordination plan and a map of tokens.
    """
    req_id = f"REQ_MRELOC_{int(time.time())}"
    return MultiManifoldRelocationRequest(
        request_id=req_id,
        coordination_plan=coordination_plan,
        tokens=tokens
    )


def validate_multi_manifold_relocation_tokens(
    tokens: Dict[str, LiveRelocationToken],
    coordination_plan: Any
) -> bool:
    """
    Validates that all tokens for the manifolds participating in the coordination plan are present and authorized.
    """
    steps = getattr(coordination_plan, "steps", [])
    for step in steps:
        m_id = getattr(step, "manifold_id", None)
        if not m_id:
            continue
        token = tokens.get(m_id)
        if not token or not validate_live_relocation_token(token):
            return False
    return True


def capture_multi_manifold_snapshots(
    request: MultiManifoldRelocationRequest
) -> MultiManifoldRelocationSnapshot:
    """
    Captures snapshots for all manifolds in the relocation request.
    """
    from sol_multimanifold_coordinator import _get_manifold_id
    snapshots = {}
    plan = request.coordination_plan
    group = getattr(plan, "group", None)
    manifolds = getattr(group, "manifolds", []) if group else []
    
    for m in manifolds:
        m_id = _get_manifold_id(m)
        token = request.tokens.get(m_id) or LiveRelocationToken(

            token_id=f"T_DUMMY_{m_id}",
            court_authorization_id="AUTH_DUMMY",
            sandbox_scope=True,
            source_id="core_0",
            target_id="core_1",
            expiration=time.time() + 100,
            max_relocation_steps=5,
            rollback_required=True,
            ranger_observer_id="R_DUMMY"
        )
        dummy_req = SandboxRelocationRequest(
            request_id=f"REQ_DUMMY_{m_id}",
            rebalance_plan=m,
            token=token
        )
        snapshots[m_id] = capture_sandbox_relocation_snapshot(dummy_req)
        
    snap_id = f"MSNAP_{int(time.time())}"
    return MultiManifoldRelocationSnapshot(
        snapshot_id=snap_id,
        request=request,
        manifold_snapshots=snapshots
    )


def rollback_multi_manifold_relocation(
    snapshots: MultiManifoldRelocationSnapshot,
    reason: str
) -> Dict[str, SandboxRelocationResult]:
    """
    Rolls back all participating manifolds to their pre-relocation state.
    """
    results = {}
    for m_id, snap in snapshots.manifold_snapshots.items():
        results[m_id] = rollback_sandbox_relocation(snap, reason)
    return results

