# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Graph Compaction
====================
Implements linear chain compaction, candidate analysis, compaction planning, and node/edge remapping.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sol_graph_kernel import GCSnapshot

@dataclass
class GraphCompactionCandidate:
    candidate_node_id: str
    predecessor_id: str
    successor_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NodeRemapTable:
    mapping: Dict[str, str] = field(default_factory=dict)

@dataclass
class EdgeRemapTable:
    mapping: Dict[Any, Any] = field(default_factory=dict)

@dataclass
class GraphCompactionPlan:
    plan_id: str
    candidates: List[GraphCompactionCandidate]
    node_remap: NodeRemapTable = field(default_factory=NodeRemapTable)
    edge_remap: EdgeRemapTable = field(default_factory=EdgeRemapTable)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphCompactionResult:
    success: bool
    compacted_snapshot: GCSnapshot
    node_remap: NodeRemapTable
    edge_remap: EdgeRemapTable
    errors: List[str] = field(default_factory=list)

@dataclass
class GraphCompactionReport:
    report_id: str
    plan: GraphCompactionPlan
    result: Optional[GraphCompactionResult] = None
    passed_gates: bool = False
    gate_report: Optional[Any] = None
    reproducibility_hash: str = ""


def analyze_compaction_candidates(graph_snapshot: GCSnapshot) -> List[GraphCompactionCandidate]:
    """
    Identifies linear chains of nodes (indegree == 1 and outdegree == 1) for compaction.
    Active registers (starting with 'M_REG_' or 'reg_') and HCAM banks are not considered.
    """
    incoming = {}
    outgoing = {}
    
    for n in graph_snapshot.nodes:
        n_id = n["id"]
        incoming[n_id] = []
        outgoing[n_id] = []
        
    for e in graph_snapshot.edges:
        src = e["from"]
        dst = e["to"]
        if src in outgoing:
            outgoing[src].append(dst)
        if dst in incoming:
            incoming[dst].append(src)
            
    candidates = []
    for n in graph_snapshot.nodes:
        n_id = n["id"]
        # Skip active registers/HCAM banks
        if n_id.startswith("M_REG_") or n_id.startswith("reg_") or "hcam" in n_id.lower() or "bank" in n_id.lower():
            continue
            
        if len(incoming.get(n_id, [])) == 1 and len(outgoing.get(n_id, [])) == 1:
            pred = incoming[n_id][0]
            succ = outgoing[n_id][0]
            
            # Avoid self-loops or two-node cycles
            if pred != n_id and succ != n_id and pred != succ:
                candidates.append(GraphCompactionCandidate(
                    candidate_node_id=n_id,
                    predecessor_id=pred,
                    successor_id=succ,
                    metadata={"incoming_flux": 1.0}
                ))
    return candidates


def build_compaction_plan(
    candidates: List[GraphCompactionCandidate],
    policy: Any = None
) -> GraphCompactionPlan:
    """
    Constructs a compaction plan from candidates.
    """
    node_mapping = {}
    edge_mapping = {}
    
    # Process linear merges
    for cand in candidates:
        # Map the candidate node to its predecessor
        node_mapping[cand.candidate_node_id] = cand.predecessor_id
        # Map the edges: (pred, cand) and (cand, succ) -> (pred, succ)
        edge_mapping[(cand.predecessor_id, cand.candidate_node_id)] = (cand.predecessor_id, cand.successor_id)
        edge_mapping[(cand.candidate_node_id, cand.successor_id)] = (cand.predecessor_id, cand.successor_id)
        
    plan = GraphCompactionPlan(
        plan_id=f"COMP_PLAN_{len(candidates)}",
        candidates=candidates,
        node_remap=NodeRemapTable(mapping=node_mapping),
        edge_remap=EdgeRemapTable(mapping=edge_mapping)
    )
    return plan


def build_remap_tables(plan: GraphCompactionPlan) -> tuple:
    """
    Returns (NodeRemapTable, EdgeRemapTable).
    """
    return plan.node_remap, plan.edge_remap


def validate_compaction_plan(plan: GraphCompactionPlan) -> bool:
    """
    Verifies plan validity (no cyclic remapping, registers preserved).
    """
    node_map = plan.node_remap.mapping
    for old_id, new_id in node_map.items():
        if old_id.startswith("M_REG_") or old_id.startswith("reg_"):
            return False  # Cannot remap registers
        # Check cyclic mapping
        visited = {old_id}
        curr = new_id
        while curr in node_map:
            if curr in visited:
                return False  # Cycle detected
            visited.add(curr)
            curr = node_map[curr]
    return True


def execute_shadow_compaction(plan: GraphCompactionPlan) -> GraphCompactionResult:
    """
    Shadow executes the compaction plan on a mock graph snapshot, producing a remapped GCSnapshot.
    Does not modify any live engine state.
    """
    errors = []
    if not validate_compaction_plan(plan):
        errors.append("Compaction plan validation failed.")
        return GraphCompactionResult(
            success=False,
            compacted_snapshot=GCSnapshot(nodes=[], edges=[]),
            node_remap=plan.node_remap,
            edge_remap=plan.edge_remap,
            errors=errors
        )
        
    # We will build a dummy snapshot to apply the mapping to
    # Since we operate on shadow, we create a remapped snapshot
    node_map = plan.node_remap.mapping
    
    # Mock nodes: let's build remapped nodes list
    remapped_nodes = []
    # Deduplicate merged nodes
    merged_ids = set(node_map.keys())
    
    # We can reconstruct node list by filtering out merged nodes
    # For testing, we mock execution by copying nodes/edges and applying map
    # We will use candidates to figure out nodes to keep
    # In a real run, we would map the plan to an input snapshot in plan.metadata
    original_snapshot = plan.metadata.get("snapshot")
    if not original_snapshot:
        # Build dummy nodes based on candidates
        all_ids = set()
        for c in plan.candidates:
            all_ids.add(c.candidate_node_id)
            all_ids.add(c.predecessor_id)
            all_ids.add(c.successor_id)
        original_snapshot = GCSnapshot(
            nodes=[{"id": idx, "rho": 1.0} for idx in all_ids],
            edges=[{"from": c.predecessor_id, "to": c.candidate_node_id} for c in plan.candidates] + \
                  [{"from": c.candidate_node_id, "to": c.successor_id} for c in plan.candidates]
        )
        
    for n in original_snapshot.nodes:
        n_id = n["id"]
        if n_id not in merged_ids:
            remapped_nodes.append(dict(n))
            
    remapped_edges = []
    seen_edges = set()
    for e in original_snapshot.edges:
        src = e["from"]
        dst = e["to"]
        
        # Apply node remaps
        new_src = node_map.get(src, src)
        new_dst = node_map.get(dst, dst)
        
        # Skip self-loops after merge
        if new_src == new_dst:
            continue
            
        edge_key = (new_src, new_dst)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            remapped_edges.append({
                "from": new_src,
                "to": new_dst,
                "w0": e.get("w0", 1.0),
                "conductance": e.get("conductance", 1.0),
                "flux": e.get("flux", 0.0)
            })
            
    compacted = GCSnapshot(nodes=remapped_nodes, edges=remapped_edges)
    return GraphCompactionResult(
        success=True,
        compacted_snapshot=compacted,
        node_remap=plan.node_remap,
        edge_remap=plan.edge_remap,
        errors=[]
    )
