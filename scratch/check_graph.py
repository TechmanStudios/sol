import sys
from pathlib import Path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_final import (
    MHRALevel11ProcessingManifold, Level11ManifoldGroup, SemanticManifold, UniversalManifold
)

# Build semantic basins
nodes = []
edges = []
basins = []
for i in range(16):
    n_val, e_val, b_val = UniversalManifold.build_semantic_basin(f"Basin_Val{i}", num_nodes=10, start_idx=i*10)
    nodes.extend(n_val)
    edges.extend(e_val)
    basins.append(b_val)
n_q, e_q, b_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=160)
nodes.extend(n_q)
edges.extend(e_q)
basins.append(b_q)

semantic = SemanticManifold(nodes, edges, basins)
processing = MHRALevel11ProcessingManifold(baseline_rho=15.0)
group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)

print("Nodes in group:", len(group.raw_nodes))
print("Edges in group:", len(group.raw_edges))

# Look for any edge connecting Lane 0 nodes to Lane 1 nodes
lane0_nodes = set()
lane1_nodes = set()

# Lane 0 processing nodes:
for n in group.raw_nodes:
    nid = n["id"]
    if "0" in nid and ("S_R" in nid or "GATE" in nid or "P_Bus" in nid or "Gate_Match" in nid or "Basin_Val" in nid):
        lane0_nodes.add(nid)
    elif "1" in nid and ("S_R" in nid or "GATE" in nid or "P_Bus" in nid or "Gate_Match" in nid or "Basin_Val" in nid):
        lane1_nodes.add(nid)

# Also add the internal basin nodes to the respective lane sets
for i in range(8):
    lane0_nodes.update(semantic.basins[f"Basin_Val{i}"].node_ids)
for i in range(8, 16):
    lane1_nodes.update(semantic.basins[f"Basin_Val{i}"].node_ids)

print(f"Lane 0 node count: {len(lane0_nodes)}")
print(f"Lane 1 node count: {len(lane1_nodes)}")

print("\nInter-lane edges (connecting Lane 0 to Lane 1):")
for e in group.raw_edges:
    f, t = e["from"], e["to"]
    if (f in lane0_nodes and t in lane1_nodes) or (f in lane1_nodes and t in lane0_nodes):
        print(f"  {f} -> {t} (w0={e.get('w0')}, kind={e.get('kind')})")

print("\nAll edges connected to P_Bus0:")
for e in group.raw_edges:
    if e["from"] == "P_Bus0" or e["to"] == "P_Bus0":
        print(f"  {e['from']} -> {e['to']} (w0={e.get('w0')})")

print("\nAll edges connected to P_Bus1:")
for e in group.raw_edges:
    if e["from"] == "P_Bus1" or e["to"] == "P_Bus1":
        print(f"  {e['from']} -> {e['to']} (w0={e.get('w0')})")
