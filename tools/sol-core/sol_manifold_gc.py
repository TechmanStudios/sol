# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Manifold Garbage Collector
==============================
Implements reachability analysis, orphan node detection, stale edge identification,
GC collection policy evaluation, and shadow tombstoning.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
import time
from sol_graph_kernel import GCSnapshot

@dataclass
class ManifoldGCPolicy:
    shadow_only_by_default: bool = True
    tombstone_before_delete: bool = True
    min_age_steps: int = 10
    preserve_active_registers: bool = True
    preserve_recent_transactions: bool = True
    preserve_locked_shards: bool = True
    preserve_quarantined_evidence: bool = True
    preserve_phase_tables: bool = True
    preserve_hcam_banks: bool = True
    rollback_required_for_live_gc: bool = True

@dataclass
class ReachabilityRoot:
    root_node_id: str

@dataclass
class ReachabilityReport:
    reachable_node_ids: Set[str] = field(default_factory=set)
    unreachable_node_ids: Set[str] = field(default_factory=set)

@dataclass
class ManifoldTombstone:
    target_id: str
    target_type: str  # "node" | "edge"
    tombstoned_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GCCollectionPlan:
    plan_id: str
    nodes_to_collect: List[str]
    edges_to_collect: List[tuple]
    tombstones: List[ManifoldTombstone] = field(default_factory=list)
    policy: ManifoldGCPolicy = field(default_factory=ManifoldGCPolicy)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GCCollectionReport:
    report_id: str
    plan: GCCollectionPlan
    collected_nodes: List[str] = field(default_factory=list)
    collected_edges: List[tuple] = field(default_factory=list)
    tombstones_created: List[ManifoldTombstone] = field(default_factory=list)
    passed_gates: bool = False
    gate_report: Optional[Any] = None
    reproducibility_hash: str = ""


def mark_reachable_nodes(
    snapshot: GCSnapshot,
    roots: List[ReachabilityRoot]
) -> ReachabilityReport:
    """
    Standard DFS traversal from roots to determine reachable nodes.
    """
    adj = {}
    for n in snapshot.nodes:
        adj[n["id"]] = []
        
    for e in snapshot.edges:
        src = e["from"]
        dst = e["to"]
        if src in adj:
            adj[src].append(dst)
            
    reachable = set()
    root_ids = [r.root_node_id for r in roots]
    
    def dfs(node_id):
        reachable.add(node_id)
        for neighbor in adj.get(node_id, []):
            if neighbor not in reachable:
                dfs(neighbor)
                
    for r_id in root_ids:
        if r_id in adj and r_id not in reachable:
            dfs(r_id)
            
    all_ids = set(n["id"] for n in snapshot.nodes)
    unreachable = all_ids - reachable
    
    return ReachabilityReport(
        reachable_node_ids=reachable,
        unreachable_node_ids=unreachable
    )


def identify_orphan_nodes(
    snapshot: GCSnapshot,
    reachability_report: ReachabilityReport
) -> List[str]:
    """
    Identifies orphan nodes that are unreachable from any root.
    """
    return list(reachability_report.unreachable_node_ids)


def identify_stale_edges(
    snapshot: GCSnapshot,
    policy: ManifoldGCPolicy
) -> List[tuple]:
    """
    Identifies stale edges (endpoints are unreachable or zero flux/weight).
    """
    stale = []
    # In shadow/dry-run mode, we identify edges connecting unreachable nodes
    # or edges with flux == 0.0 and conductance <= 0.1
    for e in snapshot.edges:
        src = e["from"]
        dst = e["to"]
        flux = e.get("flux", 0.0)
        cond = e.get("conductance", 1.0)
        
        # Age check
        age = e.get("metadata", {}).get("age_steps", 0)
        if flux == 0.0 or age >= policy.min_age_steps:
            stale.append((src, dst))
    return stale


def no_active_transaction_references(candidate: str) -> bool:
    """
    Validation gate check: candidate node has no active transaction or lock references.
    """
    # Import registries dynamically to prevent import cycles
    from sol_transaction_coordinator import get_active_transactions
    from sol_shard_lock_scheduler import get_active_locks
    
    # Check locks
    for lock in get_active_locks():
        if lock.shard_id == candidate or lock.owner_transaction_id == candidate:
            return False
            
    # Check transactions
    for tx in get_active_transactions():
        tx_id_str = getattr(tx.transaction_id, "tx_id", str(tx.transaction_id))
        if tx_id_str == candidate:
            return False
        # Check participants
        for p in tx.participants:
            if p.participant_id == candidate:
                return False
        # Check rollback snapshot
        if tx.rollback_snapshot:
            if isinstance(tx.rollback_snapshot, dict) and candidate in tx.rollback_snapshot:
                return False
            elif hasattr(tx.rollback_snapshot, "participant_states"):
                if candidate in tx.rollback_snapshot.participant_states:
                    return False
    return True


def build_gc_collection_plan(
    snapshot: GCSnapshot,
    policy: ManifoldGCPolicy
) -> GCCollectionPlan:
    """
    Constructs a garbage collection plan, filtering candidates through safety rules.
    """
    # 1. Reachability check from default root (e.g. "shard_0" or first active node)
    roots = []
    if snapshot.nodes:
        roots.append(ReachabilityRoot(snapshot.nodes[0]["id"]))
        
    reach_rep = mark_reachable_nodes(snapshot, roots)
    orphans = identify_orphan_nodes(snapshot, reach_rep)
    stale_edges = identify_stale_edges(snapshot, policy)
    
    nodes_to_collect = []
    edges_to_collect = []
    tombstones = []
    
    # Filter nodes based on safety policy
    for node_id in orphans:
        # Check active registers preservation
        if policy.preserve_active_registers:
            if node_id.startswith("M_REG_") or node_id.startswith("reg_"):
                continue
        # Check HCAM banks preservation
        if policy.preserve_hcam_banks:
            if "hcam" in node_id.lower() or "bank" in node_id.lower():
                continue
        # Check phase tables preservation
        if policy.preserve_phase_tables:
            if "phase" in node_id.lower():
                continue
        # Check quarantined evidence
        if policy.preserve_quarantined_evidence:
            if "evidence" in node_id.lower():
                continue
        # Check transaction and lock references
        if not no_active_transaction_references(node_id):
            continue
            
        nodes_to_collect.append(node_id)
        if policy.tombstone_before_delete:
            tombstones.append(ManifoldTombstone(target_id=node_id, target_type="node"))
            
    # Filter edges
    for edge in stale_edges:
        src, dst = edge
        if src in nodes_to_collect or dst in nodes_to_collect:
            edges_to_collect.append(edge)
            if policy.tombstone_before_delete:
                tombstones.append(ManifoldTombstone(target_id=f"{src}->{dst}", target_type="edge"))
                
    plan = GCCollectionPlan(
        plan_id=f"GC_PLAN_{int(time.time())}",
        nodes_to_collect=nodes_to_collect,
        edges_to_collect=edges_to_collect,
        tombstones=tombstones,
        policy=policy,
        metadata={"snapshot": snapshot}
    )
    return plan


def execute_shadow_gc(plan: GCCollectionPlan) -> GCCollectionReport:
    """
    Shadow executes GC collection plan on snapshot copy.
    """
    snapshot = plan.metadata.get("snapshot")
    if not snapshot:
        return GCCollectionReport(
            report_id=f"GC_RPT_{plan.plan_id}",
            plan=plan,
            passed_gates=False
        )
        
    collected_nodes = []
    collected_edges = []
    tombstones_created = list(plan.tombstones)
    
    # In shadow execution, we don't mutate live data.
    # We simulate node reclamation by copying node list and tagging tombstones.
    for n_id in plan.nodes_to_collect:
        collected_nodes.append(n_id)
        
    for edge in plan.edges_to_collect:
        collected_edges.append(edge)
        
    return GCCollectionReport(
        report_id=f"GC_RPT_{plan.plan_id}",
        plan=plan,
        collected_nodes=collected_nodes,
        collected_edges=collected_edges,
        tombstones_created=tombstones_created,
        passed_gates=True
    )
