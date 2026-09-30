# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Distributed Cross-Shard Query
=================================
Scaffolds distributed query planning, boundary-crossing hops, shadow execution,
and fan-in response reduction trees.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

from sol_shard_topology import ShardId, ShardTopology, assign_manifold_to_shard

@dataclass
class CrossShardQuery:
    query_id: str
    query_type: str  # "single" | "fan-out"
    target_manifold_ids: List[str]
    fields: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossShardQueryHop:
    hop_index: int
    source_shard: ShardId
    target_shard: ShardId
    delay_ms: float = 0.1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossShardQueryPlan:
    query: CrossShardQuery
    target_shards: List[ShardId]
    hops: List[CrossShardQueryHop] = field(default_factory=field)
    reduction: str = "merge"  # "merge" | "sum" | "concat"
    cost_estimate: Optional[Any] = None  # QueryCostEstimate
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossShardQueryResult:
    plan: CrossShardQueryPlan
    success: bool
    raw_values: Dict[str, Any] = field(default_factory=dict)  # shard_id -> raw value
    assembled_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossShardQueryReport:
    report_id: str
    query_plan: CrossShardQueryPlan
    query_result: CrossShardQueryResult
    passed_gates: bool = False
    gate_report: Optional[Any] = None  # InstructionGateReport
    reproducibility_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


def plan_cross_shard_query(
    query: CrossShardQuery,
    topology: ShardTopology
) -> CrossShardQueryPlan:
    """
    Generates a distributed query plan with hops across shards.
    """
    # 1. Map target manifolds to target shards
    target_shards_set = set()
    for manifold_id in query.target_manifold_ids:
        s_id = assign_manifold_to_shard(manifold_id, topology)
        target_shards_set.add(s_id)
        
    target_shards = list(target_shards_set)
    # Default to shard_0 if empty
    if not target_shards:
        target_shards = [ShardId("shard_0")]
        
    # Determine coordinator shard
    coord_shard = ShardId("shard_0")
    
    # 2. Build query type and hops
    q_type = "single" if len(target_shards) == 1 and target_shards[0] == coord_shard else "fan-out"
    
    hops = []
    hop_idx = 0
    
    for t_shard in target_shards:
        if t_shard == coord_shard:
            continue
            
        # Mocking route boundaries from coordinator to target
        # For simplicity, if we cross to another shard, we construct a boundary hop
        # Verify boundary exists in topology
        boundary_exists = False
        for b in topology.boundaries:
            if b.source_shard == coord_shard and b.target_shard == t_shard:
                boundary_exists = True
                break
                
        # Fallback to general crossing
        hops.append(CrossShardQueryHop(
            hop_index=hop_idx,
            source_shard=coord_shard,
            target_shard=t_shard,
            delay_ms=0.15 if boundary_exists else 0.5,
            metadata={"boundary_exists": boundary_exists}
        ))
        hop_idx += 1
        
    reduction = query.metadata.get("reduction", "merge")
    
    # Let's import QueryCostEstimate dynamically to avoid circular dependencies
    from sol_query_optimizer import estimate_query_cost
    
    plan = CrossShardQueryPlan(
        query=CrossShardQuery(query.query_id, q_type, query.target_manifold_ids, query.fields, query.metadata),
        target_shards=target_shards,
        hops=hops,
        reduction=reduction,
        metadata={"coordinator": coord_shard.shard_id}
    )
    
    plan.cost_estimate = estimate_query_cost(plan)
    return plan


def validate_cross_shard_query_plan(plan: CrossShardQueryPlan) -> bool:
    """
    Validates query plan completeness and constraints.
    """
    if not plan.target_shards:
        return False
        
    # Max hops allowed is 8 to prevent infinite loops
    if len(plan.hops) > 8:
        return False
        
    # Check that query targets are declared
    if not plan.query.target_manifold_ids:
        return False
        
    return True


def assemble_cross_shard_result(
    results: Dict[str, Any],
    reduction: str = "merge"
) -> Any:
    """
    Assembles local responses into a final reduction value.
    """
    if not results:
        return None
        
    if reduction == "sum":
        total_sum = 0
        for val in results.values():
            if isinstance(val, (int, float)):
                total_sum += val
            elif isinstance(val, dict):
                # Sum the dict values
                total_sum += sum(v for v in val.values() if isinstance(v, (int, float)))
        return total_sum
        
    elif reduction == "concat":
        total_concat = []
        for val in results.values():
            if isinstance(val, list):
                total_concat.extend(val)
            else:
                total_concat.append(val)
        return total_concat
        
    elif reduction == "first":
        keys = sorted(results.keys())
        return results[keys[0]]
        
    else:  # Default "merge"
        merged = {}
        for val in results.values():
            if isinstance(val, dict):
                merged.update(val)
            else:
                # If it's a primitive, store it under a generic key
                pass
        return merged if merged else results


def execute_shadow_cross_shard_query(
    plan: CrossShardQueryPlan,
    mock_values: Optional[Dict[str, Any]] = None
) -> CrossShardQueryResult:
    """
    Shadow executes query, collecting raw shard values and reducing them.
    """
    raw_values = {}
    
    for shard in plan.target_shards:
        s_id = shard.shard_id
        if mock_values and s_id in mock_values:
            raw_values[s_id] = mock_values[s_id]
        else:
            # Default mock values
            raw_values[s_id] = {f"val_{s_id}": 0xCAFE}
            
    assembled = assemble_cross_shard_result(raw_values, plan.reduction)
    
    validation_passed = validate_cross_shard_query_plan(plan)
    
    return CrossShardQueryResult(
        plan=plan,
        success=validation_passed,
        raw_values=raw_values,
        assembled_value=assembled,
        metadata={"executed_at": time.time()}
    )
