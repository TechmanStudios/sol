# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Manifold Placement Planner
==============================
Manages placement maps, moves, cost estimates, and relocation constraint validation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import copy

@dataclass
class PlacementPolicy:
    max_rebalance_moves: int = 3
    min_improvement: float = 0.05
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlacementConstraint:
    constraint_type: str  # e.g., "preserve_locks", "preserve_transactions", "preserve_hcam_locality", "preserve_phase_tables"
    target_id: str
    satisfied: bool = True
    reason: str = "satisfied"

@dataclass
class PlacementCostEstimate:
    cost_id: str
    estimated_cost: float
    breakdown: Dict[str, float] = field(default_factory=dict)

@dataclass
class PlacementMove:
    move_id: str
    manifold_id: str
    source_core: str
    target_core: str
    constraints: List[PlacementConstraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlacementMap:
    placement_id: str
    manifold_to_core: Dict[str, str] = field(default_factory=dict)
    shard_to_core: Dict[str, str] = field(default_factory=dict)


def estimate_placement_cost(placement_map: PlacementMap) -> PlacementCostEstimate:
    """
    Estimates the latency and alignment cost of a placement configuration map.
    """
    cost = float(len(placement_map.manifold_to_core) * 0.15 + len(placement_map.shard_to_core) * 0.25)
    return PlacementCostEstimate(
        cost_id=f"EST_{placement_map.placement_id}",
        estimated_cost=cost,
        breakdown={"manifold_cost": len(placement_map.manifold_to_core) * 0.15, "shard_cost": len(placement_map.shard_to_core) * 0.25}
    )


def plan_manifold_move(
    manifold_id: str,
    source_core: str,
    target_core: str,
    constraints: Optional[List[PlacementConstraint]] = None
) -> PlacementMove:
    """
    Constructs a PlacementMove.
    """
    c_list = constraints or [
        PlacementConstraint("preserve_transactions", manifold_id, True),
        PlacementConstraint("preserve_locks", manifold_id, True),
        PlacementConstraint("preserve_rollback_snapshots", manifold_id, True),
        PlacementConstraint("preserve_hcam_locality", manifold_id, True),
        PlacementConstraint("preserve_phase_tables", manifold_id, True),
        PlacementConstraint("preserve_evidence_packets", manifold_id, True)
    ]
    return PlacementMove(
        move_id=f"MOVE_{manifold_id}_{source_core}_to_{target_core}",
        manifold_id=manifold_id,
        source_core=source_core,
        target_core=target_core,
        constraints=c_list
    )


def validate_placement_constraints(move: PlacementMove) -> bool:
    """
    Validates that all constraints in the move are satisfied.
    Checks:
    - preserve active transactions
    - preserve held locks
    - preserve rollback snapshots
    - preserve H-CAM bank locality
    - preserve phase table references
    - preserve evidence packet references
    - avoid moving quarantined shards unless court-authorized
    """
    # 1. Check constraints list satisfaction
    for c in move.constraints:
        if not c.satisfied:
            return False
            
    # 2. Check metadata flags representing violations
    meta = getattr(move, "metadata", {}) or {}
    
    # Active transaction check
    if meta.get("transaction_active") or meta.get("active_transaction_present"):
        return False
        
    # Held lock check
    if meta.get("exclusive_lock_held") or meta.get("lock_held"):
        return False
        
    # Rollback snapshots check
    if meta.get("rollback_broken") or meta.get("rollback_snapshots_not_preserved"):
        return False
        
    # H-CAM bank locality check
    if meta.get("hcam_locality_broken"):
        return False
        
    # Phase table references check
    if meta.get("phase_tables_broken"):
        return False
        
    # Evidence packet references check
    if meta.get("evidence_packets_broken"):
        return False
        
    # Quarantined shard unless court-authorized check
    if meta.get("quarantined") and not meta.get("court_authorized"):
        return False
        
    # Consensus check
    if meta.get("consensus_broken"):
        return False
        
    return True


def apply_shadow_placement_move(placement_map: PlacementMap, move: PlacementMove) -> PlacementMap:
    """
    Returns a new copy of the placement map with the move applied.
    """
    new_map = copy.deepcopy(placement_map)
    if validate_placement_constraints(move):
        new_map.manifold_to_core[move.manifold_id] = move.target_core
    return new_map


def apply_sandbox_relocation_move(
    placement_map: PlacementMap,
    move: PlacementMove,
    token: Any
) -> PlacementMap:
    """
    Applies a sandbox-only relocation move if authorized by a token and constraints pass.
    Strictly preserves the original/default placement map immutably.
    """
    from sol_live_relocation import validate_live_relocation_token
    if not validate_live_relocation_token(token):
        raise ValueError("Invalid live relocation token for sandbox relocation.")

    # Core rule:
    # "This phase may perform closed-loop sandbox relocation trials using authorized live control tokens ...
    # It must not enable production/default live relocation. All live relocation remains sandbox-only ..."
    # So we reject if the token's scope is not sandbox_scope.
    if not getattr(token, "sandbox_scope", False):
        raise ValueError("Non-sandbox relocation scope is strictly rejected.")

    # Validate placement constraints
    if not validate_placement_constraints(move):
        raise ValueError("Placement constraints violated for sandbox relocation.")

    # Prevent production modifications
    if "production" in getattr(placement_map, "placement_id", "").lower() or "default" in getattr(placement_map, "placement_id", "").lower():
        raise ValueError("Production/default placement maps are immutable and cannot be mutated.")

    new_map = copy.deepcopy(placement_map)
    new_map.manifold_to_core[move.manifold_id] = move.target_core

    # Record before/after and remap tables
    if not hasattr(new_map, "metadata") or new_map.metadata is None:
        new_map.metadata = {}
    new_map.metadata["before_placement_map"] = copy.deepcopy(placement_map)
    new_map.metadata["after_placement_map"] = copy.deepcopy(new_map)
    new_map.metadata["remap_table"] = {move.manifold_id: move.target_core}

    return new_map


def restore_sandbox_placement(snapshot: Any) -> PlacementMap:
    """
    Restores the sandbox placement map from a rollback snapshot.
    """
    before_map = getattr(snapshot, "before_placement_map", None)
    if before_map is None:
        raise ValueError("Missing rollback snapshot placement map.")
    return copy.deepcopy(before_map)

