"""Q2 Topology Analysis: christic[22] neighborhood & graph structure."""
import json
from collections import defaultdict
import numpy as np

with open("tools/sol-core/default_graph.json") as f:
    g = json.load(f)
nodes = g["rawNodes"]
edges = g["rawEdges"]

# Build adjacency + degree
adj = defaultdict(set)
deg = defaultdict(int)
edge_map = {}
for e in edges:
    s, t = e["from"], e["to"]
    adj[s].add(t)
    adj[t].add(s)
    deg[s] += 1
    deg[t] += 1
    edge_map[(s, t)] = e
    edge_map[(t, s)] = e

label_map = {n["id"]: n["label"] for n in nodes}
group_map = {n["id"]: n.get("group", "bridge") for n in nodes}

print("=" * 70)
print("  CHRISTIC[22] TOPOLOGY ANALYSIS")
print("=" * 70)

christic = [n for n in nodes if n["id"] == 22][0]
print(f"Label: {christic['label']}")
print(f"Group: {christic.get('group', 'bridge')}")
print(f"Degree: {deg[22]}")

# Neighbors
nbs = sorted(adj[22])
print(f"\nNeighbors ({len(nbs)}):")
for nb in nbs:
    e = edge_map.get((22, nb), edge_map.get((nb, 22), {}))
    w0 = e.get("w0", 1.0)
    diode = e.get("diode", 0)
    cond = e.get("conductance", 1.0)
    print(f"  [{nb:3d}] {label_map[nb]:30s} grp={group_map[nb]:8s} deg={deg[nb]:3d} w0={w0:.1f} diode={diode}")

# 2-hop neighborhood
two_hop = set()
for nb in nbs:
    two_hop.update(adj[nb])
two_hop -= set(nbs)
two_hop.discard(22)
print(f"\n1-hop: {len(nbs)} nodes, 2-hop (excl 1-hop): {len(two_hop)} nodes")
print(f"Total reachable in 2 hops: {len(nbs) + len(two_hop)}/140")

# BFS centrality
def bfs_all(start):
    visited = {start: 0}
    queue = [start]
    while queue:
        cur = queue.pop(0)
        for nb in adj[cur]:
            if nb not in visited:
                visited[nb] = visited[cur] + 1
                queue.append(nb)
    return visited

all_ids = [n["id"] for n in nodes]
centralities = {}
for nid in all_ids:
    dists = bfs_all(nid)
    centralities[nid] = np.mean(list(dists.values()))

sorted_centrality = sorted(centralities.items(), key=lambda x: x[1])
print(f"\nBFS CENTRALITY (lower = more central):")
print(f"  christic[22]: {centralities[22]:.3f}")
rank = [i for i, (nid, _) in enumerate(sorted_centrality) if nid == 22][0] + 1
print(f"  Rank: {rank}/{len(all_ids)}")
print(f"\nTop 10 most central:")
for i, (nid, c) in enumerate(sorted_centrality[:10]):
    print(f"  {i+1}. [{nid:3d}] {label_map[nid]:30s} grp={group_map[nid]:8s} deg={deg[nid]:3d} centrality={c:.3f}")

# Injection nodes
inj_labels = [("grail", 40), ("metatron", 35), ("pyramid", 30), ("christ", 25), ("light_codes", 20)]
print(f"\nINJECTION NODES:")
for lbl, amt in inj_labels:
    node = [n for n in nodes if n["label"] == lbl]
    if node:
        nid = node[0]["id"]
        dists = bfs_all(nid)
        dist_22 = dists.get(22, -1)
        shared_nbs = adj[nid] & adj[22]
        print(f"  [{nid:3d}] {lbl:20s} deg={deg[nid]:3d} grp={group_map[nid]:8s} dist_to_22={dist_22} inject={amt} shared_neighbors_with_22={len(shared_nbs)}")

# Clustering coefficient of christic[22]
def clustering_coeff(nid):
    neighbors = list(adj[nid])
    if len(neighbors) < 2:
        return 0.0
    links = 0
    for i in range(len(neighbors)):
        for j in range(i + 1, len(neighbors)):
            if neighbors[j] in adj[neighbors[i]]:
                links += 1
    return 2 * links / (len(neighbors) * (len(neighbors) - 1))

cc_22 = clustering_coeff(22)
cc_all = [clustering_coeff(nid) for nid in all_ids]
print(f"\nCLUSTERING COEFFICIENTS:")
print(f"  christic[22]: {cc_22:.4f}")
print(f"  Mean: {np.mean(cc_all):.4f}")
print(f"  Median: {np.median(cc_all):.4f}")

# Spirit group analysis
spirit_nodes = [n["id"] for n in nodes if n.get("group") == "spirit"]
print(f"\nSPIRIT GROUP ({len(spirit_nodes)} nodes):")
for nid in sorted(spirit_nodes):
    print(f"  [{nid:3d}] {label_map[nid]:30s} deg={deg[nid]:3d} centrality={centralities[nid]:.3f} cc={clustering_coeff(nid):.4f}")

# Key question: what's the LOCAL energy drainage pattern?
# Under high damping, energy dissipates fast. The node that is the
# "last to lose" its energy wins. Which node has the topology to
# accumulate and retain the most?
# Hypothesis: christic[22] is a topological SINK — its neighbors
# are high-degree hubs that funnel energy toward it

# Analyze: for each spirit node, what's the sum-of-neighbor-degrees?
print(f"\nENERGY FUNNEL ANALYSIS:")
print(f"  Sum-of-neighbor-degrees (higher = more energy inflow potential):")
for nid in sorted(spirit_nodes):
    nb_deg_sum = sum(deg[nb] for nb in adj[nid])
    nb_deg_mean = np.mean([deg[nb] for nb in adj[nid]])
    print(f"  [{nid:3d}] {label_map[nid]:30s} deg={deg[nid]:3d} sum_nb_deg={nb_deg_sum:5d} mean_nb_deg={nb_deg_mean:.1f}")

# Bridge and tech node analysis for context
tech_nodes = [n["id"] for n in nodes if n.get("group") == "tech"]
bridge_nodes = [n["id"] for n in nodes if n.get("group", "bridge") == "bridge"]
print(f"\nGROUP SUMMARY:")
print(f"  Tech: {len(tech_nodes)} nodes (IDs: {tech_nodes})")
print(f"  Spirit: {len(spirit_nodes)} nodes") 
print(f"  Bridge: {len(bridge_nodes)} nodes")
print(f"  Tech avg degree: {np.mean([deg[n] for n in tech_nodes]):.1f}")
print(f"  Spirit avg degree: {np.mean([deg[n] for n in spirit_nodes]):.1f}")
print(f"  Bridge avg degree: {np.mean([deg[n] for n in bridge_nodes]):.1f}")
