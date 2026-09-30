# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Query Tree Optimization
===========================
Calculates routing cost metrics and performs tree-pruning query optimizations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import copy
import time

@dataclass
class QueryCostEstimate:
    route_depth: int
    shard_count: int
    fanout_count: int
    boundary_crossings: int
    reduction_depth: int
    estimated_crosstalk_risk: float
    consensus_overhead: float
    total_cost: float

@dataclass
class QueryTreeOptimization:
    strategy: str  # "balanced" | "latency" | "bandwidth"
    original_cost: QueryCostEstimate
    optimized_cost: QueryCostEstimate
    improvement_ratio: float

@dataclass
class OptimizedQueryPlan:
    original_plan: Any  # CrossShardQueryPlan
    optimized_plan: Any  # CrossShardQueryPlan
    optimization: QueryTreeOptimization
    metadata: Dict[str, Any] = field(default_factory=dict)


def estimate_query_cost(plan: Any) -> QueryCostEstimate:
    """
    Computes weighted cost estimate for a cross-shard query plan.
    """
    from sol_cross_shard_query import CrossShardQueryPlan
    
    route_depth = len(plan.hops)
    shard_count = len(plan.target_shards)
    
    # Coordinator fanout is target shards - 1 (since coordinator is one target)
    fanout_count = max(0, shard_count - 1)
    
    # Boundary crossings is the number of hops crossing domains
    boundary_crossings = sum(1 for h in plan.hops if h.source_shard != h.target_shard)
    
    # Reduction tree depth log2 of shard count
    import math
    reduction_depth = math.ceil(math.log2(shard_count)) if shard_count > 0 else 0
    
    # Crosstalk risk grows with boundary crossings
    crosstalk_risk = boundary_crossings * 0.03
    
    # Consensus overhead grows with shard count
    consensus_overhead = shard_count * 2.0
    
    # Total cost formula
    total_cost = (
        (route_depth * 10) +
        (shard_count * 5) +
        (fanout_count * 5) +
        (boundary_crossings * 15) +
        (reduction_depth * 8) +
        (consensus_overhead * 12)
    )
    
    return QueryCostEstimate(
        route_depth=route_depth,
        shard_count=shard_count,
        fanout_count=fanout_count,
        boundary_crossings=boundary_crossings,
        reduction_depth=reduction_depth,
        estimated_crosstalk_risk=crosstalk_risk,
        consensus_overhead=consensus_overhead,
        total_cost=total_cost
    )


def optimize_query_tree(
    plan: Any,
    strategy: str = "balanced"
) -> OptimizedQueryPlan:
    """
    Optimizes a query tree structure by pruning redundant paths or hops.
    """
    original_cost = estimate_query_cost(plan)
    
    # Deep copy plan for optimization
    opt_plan = copy.deepcopy(plan)
    
    # Perform optimization by bundling hops or removing redundant crossings
    # Deduplicate hops targeting the same destination
    seen_targets = set()
    pruned_hops = []
    for hop in opt_plan.hops:
        if hop.target_shard.shard_id not in seen_targets:
            seen_targets.add(hop.target_shard.shard_id)
            pruned_hops.append(hop)
            
    opt_plan.hops = pruned_hops
    
    # Re-index hops
    for idx, hop in enumerate(opt_plan.hops):
        hop.hop_index = idx
        
    # Recompute cost
    optimized_cost = estimate_query_cost(opt_plan)
    
    # Calculate improvement ratio
    orig_total = original_cost.total_cost
    opt_total = optimized_cost.total_cost
    
    improvement = (orig_total - opt_total) / orig_total if orig_total > 0 else 0.0
    
    optimization = QueryTreeOptimization(
        strategy=strategy,
        original_cost=original_cost,
        optimized_cost=optimized_cost,
        improvement_ratio=improvement
    )
    
    return OptimizedQueryPlan(
        original_plan=plan,
        optimized_plan=opt_plan,
        optimization=optimization,
        metadata={"optimized_at": float(time.time() if hasattr(time, "time") else 0.0)}
    )


def compare_query_plans(original: Any, optimized: Any) -> Dict[str, Any]:
    """
    Compares original and optimized query plans.
    """
    orig_cost = estimate_query_cost(original)
    opt_cost = estimate_query_cost(optimized)
    
    return {
        "original_cost": orig_cost.total_cost,
        "optimized_cost": opt_cost.total_cost,
        "cost_delta": orig_cost.total_cost - opt_cost.total_cost,
        "depth_reduction": len(original.hops) - len(optimized.hops),
        "boundary_crossings_reduction": (
            sum(1 for h in original.hops if h.source_shard != h.target_shard) -
            sum(1 for h in optimized.hops if h.source_shard != h.target_shard)
        )
    }
