# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Distributed Multi-Shard Topology
====================================
Defines shard IDs, shard domains, boundaries, and topologies for distributed scaling.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

@dataclass(frozen=True)
class ShardId:
    shard_id: str

@dataclass
class ShardDomain:
    shard_id: ShardId
    manifold_ids: List[str] = field(default_factory=list)
    lanes: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ShardBoundary:
    source_shard: ShardId
    target_shard: ShardId
    delay_ms: float = 0.1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ShardTopology:
    topology_id: str
    shards: Dict[str, ShardDomain] = field(default_factory=dict)
    boundaries: List[ShardBoundary] = field(default_factory=list)
    replication_factor: int = 1
    lane_mappings: Dict[int, str] = field(default_factory=dict)  # lane_id -> shard_id string
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ShardGroup:
    group_id: str
    shard_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ShardTopologyReport:
    report_id: str
    topology: ShardTopology
    passed: bool
    errors: List[str] = field(default_factory=list)
    reproducibility_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_shard_topology(
    shard_count: int,
    replication_factor: int = 1
) -> ShardTopology:
    """
    Constructs a shard topology with ring boundary connections.
    Supports shard counts of 2, 4, or 8.
    """
    topology_id = f"TOPOLOGY_{shard_count}S_R{replication_factor}_{int(time.time())}"
    shards = {}
    boundaries = []
    
    # Create ShardDomains
    for i in range(shard_count):
        s_id = f"shard_{i}"
        shards[s_id] = ShardDomain(
            shard_id=ShardId(s_id),
            manifold_ids=[],
            lanes=[],
            metadata={"index": i}
        )
        
    # Create adjacent boundaries (ring configuration: bidirectional 0 <-> 1 <-> ... <-> N-1 <-> 0)
    for i in range(shard_count):
        next_i = (i + 1) % shard_count
        s_curr = ShardId(f"shard_{i}")
        s_next = ShardId(f"shard_{next_i}")
        
        boundaries.append(ShardBoundary(source_shard=s_curr, target_shard=s_next, delay_ms=0.15))
        boundaries.append(ShardBoundary(source_shard=s_next, target_shard=s_curr, delay_ms=0.15))
        
    return ShardTopology(
        topology_id=topology_id,
        shards=shards,
        boundaries=boundaries,
        replication_factor=replication_factor,
        metadata={"created_at": time.time(), "shard_count": shard_count}
    )


def validate_shard_topology(topology: ShardTopology) -> bool:
    """
    Validates the shard topology configuration.
    """
    shard_count = len(topology.shards)
    # Supported counts: 2, 4, 8
    if shard_count not in [2, 4, 8]:
        return False
        
    if topology.replication_factor < 1:
        return False
        
    # Check that boundaries exist
    if not topology.boundaries:
        return False
        
    return True


def assign_manifold_to_shard(manifold_id: str, topology: ShardTopology) -> ShardId:
    """
    Consistently maps a manifold ID to a target ShardId.
    """
    shard_count = len(topology.shards)
    if shard_count == 0:
        return ShardId("shard_0")
        
    # Consistent hashing modulo shard_count
    h = hashlib.sha256(manifold_id.encode('utf-8')).hexdigest()
    idx = int(h, 16) % shard_count
    s_id = f"shard_{idx}"
    
    # Update manifold_ids in ShardDomain if not already present
    if s_id in topology.shards:
        if manifold_id not in topology.shards[s_id].manifold_ids:
            topology.shards[s_id].manifold_ids.append(manifold_id)
            
    return ShardId(s_id)


def map_fabric_lanes_to_shards(width: int, topology: ShardTopology) -> None:
    """
    Maps fabric waveguide lanes to shards.
    """
    num_lanes = width // 8
    shard_keys = list(topology.shards.keys())
    shard_count = len(shard_keys)
    
    if shard_count == 0:
        return
        
    topology.lane_mappings.clear()
    for lane_id in range(num_lanes):
        # Map lane to shard (round robin or modulo)
        idx = lane_id % shard_count
        s_id = shard_keys[idx]
        topology.lane_mappings[lane_id] = s_id
        
        # Also assign lane to ShardDomain
        if s_id in topology.shards:
            if lane_id not in topology.shards[s_id].lanes:
                topology.shards[s_id].lanes.append(lane_id)


def rebalance_shard_topology_shadow(topology: ShardTopology, rebalance_plan: Any) -> ShardTopology:
    """
    Returns a copy of ShardTopology with rebalance moves applied in shadow mode.
    """
    import copy
    new_topo = copy.deepcopy(topology)
    
    # Extract candidates
    candidates = getattr(rebalance_plan, "candidates", []) or []
    if isinstance(rebalance_plan, dict):
        candidates = rebalance_plan.get("candidates", [])
        
    for cand in candidates:
        item_type = getattr(cand, "item_type", "")
        item_id = getattr(cand, "item_id", "")
        target_loc = getattr(cand, "target_location", "")
        metadata = getattr(cand, "metadata", {}) or {}
        
        if isinstance(cand, dict):
            item_type = cand.get("item_type", "")
            item_id = cand.get("item_id", "")
            target_loc = cand.get("target_location", "")
            metadata = cand.get("metadata", {}) or {}
            
        if item_type == "manifold":
            # Find target shard (could be defined in metadata, target_loc, or a default)
            target_shard = metadata.get("target_shard", target_loc)
            if not target_shard or not target_shard.startswith("shard_"):
                # fallback/guess target shard if target_loc is core
                target_shard = "shard_0"
            
            if target_shard in new_topo.shards:
                # Remove manifold from any current shards
                for s_domain in new_topo.shards.values():
                    if item_id in s_domain.manifold_ids:
                        s_domain.manifold_ids.remove(item_id)
                new_topo.shards[target_shard].manifold_ids.append(item_id)
                
        elif item_type == "shard":
            # A shard itself is moved. We can update its metadata mapping or core binding
            if item_id in new_topo.shards:
                new_topo.shards[item_id].metadata["assigned_core"] = target_loc
                
    return new_topo


def validate_rebalanced_topology(topology: ShardTopology) -> bool:
    """
    Validates a rebalanced shard topology.
    """
    return validate_shard_topology(topology)


def compare_shard_topologies(before: ShardTopology, after: ShardTopology) -> Dict[str, Any]:
    """
    Compares two shard topologies and lists the difference in manifold and shard placements.
    """
    differences = {
        "moved_manifolds": {},
        "moved_shards": {},
        "identical": True
    }
    
    # Check manifold moves
    before_manifold_map = {}
    for s_id, s_domain in before.shards.items():
        for m_id in s_domain.manifold_ids:
            before_manifold_map[m_id] = s_id
            
    after_manifold_map = {}
    for s_id, s_domain in after.shards.items():
        for m_id in s_domain.manifold_ids:
            after_manifold_map[m_id] = s_id
            
    all_manifolds = set(before_manifold_map.keys()).union(after_manifold_map.keys())
    for m_id in all_manifolds:
        src = before_manifold_map.get(m_id)
        dst = after_manifold_map.get(m_id)
        if src != dst:
            differences["moved_manifolds"][m_id] = {"from": src, "to": dst}
            differences["identical"] = False
            
    # Check shard core binding moves
    for s_id in before.shards:
        src_core = before.shards[s_id].metadata.get("assigned_core")
        dst_core = after.shards[s_id].metadata.get("assigned_core")
        if src_core != dst_core:
            differences["moved_shards"][s_id] = {"from": src_core, "to": dst_core}
            differences["identical"] = False
            
    return differences
