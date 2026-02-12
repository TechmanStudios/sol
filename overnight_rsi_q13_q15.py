#!/usr/bin/env python3
"""
SOL Overnight RSI — Q13-Q15 Deep Investigation
================================================

7-hour autonomous experiment suite targeting the three open questions
from the jeans_telekinetic proof packet.

SUITE 1 — Q13: Flickering Mechanism (estimated ~90 min)
  What structural property determines heavy flickerers at d=5?
  Probe 1A: Structural census (degree, betweenness, clustering, eigenvector centrality)
            correlated with flicker count at d=5
  Probe 1B: Basin boundary analysis — how many distinct basins exist in each
            node's 1-hop and 2-hop neighborhood
  Probe 1C: Christine Hayes [90] deep dive — full structural fingerprint
  Probe 1D: Predictive model — which metric best predicts flicker count?

SUITE 2 — Q14: Hot Frozen Basin Determinism (estimated ~60 min)
  Can d=50 basins be predicted from adjacency matrix alone?
  Probe 2A: Static conductance matrix analysis — predict basin from max-weighted
            neighbor at t=0
  Probe 2B: Phase-gated prediction — include cos(omega*t*10) gate schedule
            in the prediction
  Probe 2C: Multi-hop prediction — if 1-hop misses, check 2-hop relay
  Probe 2D: Analytical accuracy score — predicted vs actual for all 140 nodes

SUITE 3 — Q15: Identity Gap Bridging (estimated ~180 min)
  Can any intervention close the d=5-10 identity gap?
  Probe 3A: Parameter tuning — sweep c_press and dt at d=5, 7, 10
  Probe 3B: Multi-injection defense — simultaneous injection of all 5 standard nodes
  Probe 3C: Topology surgery — add strategic edges to stabilize
  Probe 3D: Injection magnitude sweep — vary injection at d=5-10
  Probe 3E: Growth + defense — Jeans growth with pre-stabilization injection

SUITE 4 — Cross-Question Synthesis (~30 min)
  Probe 4A: Does the structural predictor from Q13 also predict Q15 vulnerability?
  Probe 4B: Does the analytical model from Q14 extend to d=30, d=75?

Outputs:
  data/overnight_rsi_q13_q15/<timestamp>/
    q13_structural_census.json
    q13_basin_boundary.json
    q13_christine_hayes.json
    q13_predictive_model.json
    q14_conductance_prediction.json
    q14_phase_gated.json
    q14_multihop.json
    q14_accuracy.json
    q15_param_tuning.json
    q15_multi_inject.json
    q15_topology_surgery.json
    q15_injection_sweep.json
    q15_growth_defense.json
    q_cross_synthesis.json
    overnight_report.md
    run_log.txt

ENGINE: tools/sol-core/sol_engine.py (IMMUTABLE)
GRAPH:  tools/sol-core/default_graph.json (IMMUTABLE)
"""
from __future__ import annotations

import copy
import json
import math
import sys
import time
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SOL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))

from sol_engine import SOLPhysics, compute_metrics, create_engine, SOLEngine

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
_RUN_TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
_OUTPUT_DIR = _SOL_ROOT / "data" / "overnight_rsi_q13_q15" / _RUN_TS
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _OUTPUT_DIR / "run_log.txt"
_REPORT_FILE = _OUTPUT_DIR / "overnight_report.md"

# ---------------------------------------------------------------------------
# Constants  (match existing experiments)
# ---------------------------------------------------------------------------
DT = 0.12
C_PRESS = 0.1
STEPS = 500
SAMPLE_INTERVAL = 5
RNG_SEED = 42

STANDARD_INJECTIONS = [
    ("grail", 40.0),
    ("metatron", 35.0),
    ("pyramid", 30.0),
    ("christ", 25.0),
    ("light codes", 20.0),
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_log_buffer: list[str] = []


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    _log_buffer.append(line)


def flush_log():
    with open(_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(_log_buffer))


def save_json(name: str, data: Any):
    path = _OUTPUT_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    log(f"  Saved {name} ({path.stat().st_size / 1024:.1f} KB)")


# ---------------------------------------------------------------------------
# Graph utilities
# ---------------------------------------------------------------------------
def load_default_graph():
    path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(path) as f:
        data = json.load(f)
    return data["rawNodes"], data["rawEdges"]


def get_labels(raw_nodes):
    return {n["id"]: n["label"] for n in raw_nodes}


def get_groups(raw_nodes):
    return {n["id"]: n.get("group", "bridge") for n in raw_nodes}


def get_degrees(raw_edges):
    deg = defaultdict(int)
    for e in raw_edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1
    return dict(deg)


def get_adjacency(raw_edges):
    adj = defaultdict(set)
    for e in raw_edges:
        adj[e["from"]].add(e["to"])
        adj[e["to"]].add(e["from"])
    return adj


def get_edge_map(raw_edges):
    """Dict from (from, to) -> edge dict."""
    em = {}
    for e in raw_edges:
        em[(e["from"], e["to"])] = e
        em[(e["to"], e["from"])] = e
    return em


# ---------------------------------------------------------------------------
# Budget tracker
# ---------------------------------------------------------------------------
class BudgetTracker:
    def __init__(self, budget_hours: float):
        self.budget_seconds = budget_hours * 3600
        self.t0 = time.time()
        self.trial_count = 0
        self.suite_times: dict[str, float] = {}

    def elapsed(self) -> float:
        return time.time() - self.t0

    def remaining(self) -> float:
        return max(0.0, self.budget_seconds - self.elapsed())

    def exhausted(self) -> bool:
        return self.elapsed() >= self.budget_seconds

    def pct(self) -> float:
        return min(100.0, 100.0 * self.elapsed() / self.budget_seconds)

    def start_suite(self, name: str):
        self.suite_times[name] = time.time()

    def end_suite(self, name: str):
        if name in self.suite_times:
            self.suite_times[name] = time.time() - self.suite_times[name]


# =========================================================================
# STRUCTURAL ANALYSIS UTILITIES (for Q13 & Q14)
# =========================================================================

def compute_betweenness_centrality(adj: dict[Any, set], node_ids: list) -> dict[Any, float]:
    """
    Brandes' algorithm for betweenness centrality.
    O(V*E) — fine for 140 nodes.
    """
    bc = {n: 0.0 for n in node_ids}

    for s in node_ids:
        # BFS / shortest path
        stack = []
        pred: dict = {n: [] for n in node_ids}
        sigma = {n: 0.0 for n in node_ids}
        sigma[s] = 1.0
        dist = {n: -1 for n in node_ids}
        dist[s] = 0
        queue = [s]
        qi = 0

        while qi < len(queue):
            v = queue[qi]
            qi += 1
            stack.append(v)
            for w in adj.get(v, set()):
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        delta = {n: 0.0 for n in node_ids}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                bc[w] += delta[w]

    # Normalize
    n = len(node_ids)
    if n > 2:
        norm = 1.0 / ((n - 1) * (n - 2))
        for k in bc:
            bc[k] *= norm

    return bc


def compute_clustering_coefficient(adj: dict[Any, set]) -> dict[Any, float]:
    """Local clustering coefficient for each node."""
    cc = {}
    for n in adj:
        neighbors = list(adj[n])
        k = len(neighbors)
        if k < 2:
            cc[n] = 0.0
            continue
        links = 0
        for i in range(k):
            for j in range(i + 1, k):
                if neighbors[j] in adj.get(neighbors[i], set()):
                    links += 1
        cc[n] = 2.0 * links / (k * (k - 1))
    return cc


def compute_eigenvector_centrality(adj: dict[Any, set], node_ids: list,
                                    max_iter: int = 100, tol: float = 1e-6) -> dict[Any, float]:
    """Power-iteration eigenvector centrality."""
    n = len(node_ids)
    idx = {nid: i for i, nid in enumerate(node_ids)}
    x = np.ones(n) / n

    for _ in range(max_iter):
        x_new = np.zeros(n)
        for nid in node_ids:
            i = idx[nid]
            for nb in adj.get(nid, set()):
                j = idx.get(nb)
                if j is not None:
                    x_new[i] += x[j]
        norm = np.linalg.norm(x_new)
        if norm > 0:
            x_new /= norm
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new

    return {nid: float(x[idx[nid]]) for nid in node_ids}


# =========================================================================
# BASIN PROBING (shared)
# =========================================================================

def probe_basin_sequence(raw_nodes, raw_edges, inject_id, damping,
                         inject_amount=50.0, steps=600, sample_every=5):
    """
    Run a single-injection probe and return the full basin sequence.
    """
    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=RNG_SEED)
    target = physics.node_by_id.get(inject_id)
    if target:
        target["rho"] += inject_amount

    sequence = []
    for s in range(1, steps + 1):
        physics.step(DT, C_PRESS, damping)
        if s % sample_every == 0:
            m = compute_metrics(physics)
            sequence.append((s, m["rhoMaxId"], m["maxRho"], m["entropy"]))

    basins = [s[1] for s in sequence]
    transitions = sum(1 for i in range(1, len(basins)) if basins[i] != basins[i - 1])
    unique = len(set(basins))
    final = basins[-1] if basins else None
    dominant = Counter(basins).most_common(1)[0][0] if basins else None

    return {
        "inject_id": inject_id,
        "damping": damping,
        "n_transitions": transitions,
        "unique_basins": unique,
        "final_basin": final,
        "dominant_basin": dominant,
        "is_self": final == inject_id,
        "sequence": basins,
    }


def probe_basin_simple(raw_nodes, raw_edges, inject_id, damping,
                        inject_amount=50.0, steps=STEPS, sample_every=SAMPLE_INTERVAL):
    """Quick basin probe — returns just final basin and self-attraction."""
    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=RNG_SEED)
    target = physics.node_by_id.get(inject_id)
    if target:
        target["rho"] += inject_amount

    basin_visits = defaultdict(int)
    for s in range(1, steps + 1):
        physics.step(DT, C_PRESS, damping)
        if s % sample_every == 0:
            m = compute_metrics(physics)
            bid = m["rhoMaxId"]
            if bid is not None:
                basin_visits[bid] += 1

    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
    return {
        "inject_id": inject_id,
        "damping": damping,
        "dominant_basin": dominant,
        "is_self": dominant == inject_id,
    }


# =========================================================================
# SUITE 1: Q13 — Flickering Mechanism
# =========================================================================

def suite_q13(raw_nodes, raw_edges, budget: BudgetTracker):
    """
    Q13: What structural property determines heavy flickerers at d=5?
    """
    log("=" * 70)
    log("SUITE 1 — Q13: FLICKERING MECHANISM")
    log("=" * 70)
    budget.start_suite("q13")

    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)
    adj = get_adjacency(raw_edges)
    node_ids = [n["id"] for n in raw_nodes]

    # ── Probe 1A: Structural Census ──
    log("\n  Probe 1A: Computing structural metrics for all 140 nodes...")
    t0 = time.time()

    bc = compute_betweenness_centrality(adj, node_ids)
    cc = compute_clustering_coefficient(adj)
    ec = compute_eigenvector_centrality(adj, node_ids)

    log(f"    Centrality computation: {time.time() - t0:.1f}s")

    # Now run flicker probes at d=5
    log("  Probe 1A: Running d=5 flicker probes for all 140 nodes...")
    flicker_data = []
    t0 = time.time()
    for i, nid in enumerate(node_ids):
        r = probe_basin_sequence(raw_nodes, raw_edges, nid, damping=5.0)
        r["label"] = labels[nid]
        r["group"] = groups.get(nid, "bridge")
        r["degree"] = degrees.get(nid, 0)
        r["betweenness"] = bc.get(nid, 0.0)
        r["clustering"] = cc.get(nid, 0.0)
        r["eigenvector"] = ec.get(nid, 0.0)
        flicker_data.append(r)

        if (i + 1) % 20 == 0 or i == len(node_ids) - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(node_ids) - i - 1) / rate
            log(f"    [{i+1}/{len(node_ids)}] {elapsed:.1f}s, ~{eta:.0f}s remaining")

        if budget.exhausted():
            log("  [WARN] Budget exhausted during Q13 Probe 1A")
            break

    budget.trial_count += len(flicker_data)

    # Correlation analysis
    log("  Probe 1A: Computing correlations...")
    trans_arr = np.array([d["n_transitions"] for d in flicker_data])
    deg_arr = np.array([d["degree"] for d in flicker_data])
    bc_arr = np.array([d["betweenness"] for d in flicker_data])
    cc_arr = np.array([d["clustering"] for d in flicker_data])
    ec_arr = np.array([d["eigenvector"] for d in flicker_data])

    def corr_safe(a, b):
        if len(a) < 3:
            return 0.0
        c = np.corrcoef(a, b)
        r = c[0, 1]
        return float(r) if np.isfinite(r) else 0.0

    correlations = {
        "degree_vs_flicker": corr_safe(deg_arr, trans_arr),
        "betweenness_vs_flicker": corr_safe(bc_arr, trans_arr),
        "clustering_vs_flicker": corr_safe(cc_arr, trans_arr),
        "eigenvector_vs_flicker": corr_safe(ec_arr, trans_arr),
    }

    # Rank metrics by absolute correlation
    best_predictor = max(correlations, key=lambda k: abs(correlations[k]))
    log(f"  Probe 1A: Best predictor of flickering: {best_predictor} "
        f"(r={correlations[best_predictor]:.4f})")
    for k, v in sorted(correlations.items(), key=lambda x: -abs(x[1])):
        log(f"    {k}: r = {v:.4f}")

    census_result = {
        "correlations": correlations,
        "best_predictor": best_predictor,
        "node_data": [
            {
                "id": d["inject_id"], "label": d["label"], "group": d["group"],
                "degree": d["degree"], "betweenness": round(d["betweenness"], 6),
                "clustering": round(d["clustering"], 4),
                "eigenvector": round(d["eigenvector"], 6),
                "n_transitions": d["n_transitions"],
                "unique_basins": d["unique_basins"],
                "is_self": d["is_self"],
            }
            for d in flicker_data
        ],
    }
    save_json("q13_structural_census.json", census_result)

    # ── Probe 1B: Basin Boundary Analysis ──
    if not budget.exhausted():
        log("\n  Probe 1B: Basin boundary analysis...")
        log("    Computing basin membership for 1-hop and 2-hop neighborhoods...")

        # First: get the basin assignment for each node at d=5
        # (stable basin = dominant basin from probe)
        node_basins = {d["inject_id"]: d["dominant_basin"] for d in flicker_data}

        boundary_data = []
        for nid in node_ids:
            neighbors_1hop = adj.get(nid, set())
            neighbors_2hop = set()
            for nb in neighbors_1hop:
                neighbors_2hop.update(adj.get(nb, set()))
            neighbors_2hop -= neighbors_1hop
            neighbors_2hop.discard(nid)

            # Basin diversity in 1-hop neighborhood
            basins_1hop = set()
            for nb in neighbors_1hop:
                b = node_basins.get(nb)
                if b is not None:
                    basins_1hop.add(b)

            # Basin diversity in 2-hop neighborhood
            basins_2hop = set()
            for nb in neighbors_2hop:
                b = node_basins.get(nb)
                if b is not None:
                    basins_2hop.add(b)

            # Combined
            basins_all = basins_1hop | basins_2hop

            # Is this node's own basin different from majority of neighbors?
            own_basin = node_basins.get(nid)
            neighbor_basin_counts = Counter(
                node_basins.get(nb) for nb in neighbors_1hop
                if node_basins.get(nb) is not None
            )
            majority_neighbor_basin = (
                neighbor_basin_counts.most_common(1)[0][0]
                if neighbor_basin_counts else None
            )
            is_boundary = own_basin != majority_neighbor_basin

            fd = next((d for d in flicker_data if d["inject_id"] == nid), None)

            boundary_data.append({
                "id": nid,
                "label": labels[nid],
                "group": groups.get(nid, "bridge"),
                "degree": degrees.get(nid, 0),
                "n_transitions": fd["n_transitions"] if fd else 0,
                "own_basin": own_basin,
                "n_basins_1hop": len(basins_1hop),
                "n_basins_2hop": len(basins_2hop),
                "n_basins_combined": len(basins_all),
                "is_boundary_node": is_boundary,
                "majority_neighbor_basin": majority_neighbor_basin,
                "n_neighbors_1hop": len(neighbors_1hop),
                "n_neighbors_2hop": len(neighbors_2hop),
            })

        # Correlate basin boundary diversity with flicker rate
        bd_trans = np.array([d["n_transitions"] for d in boundary_data])
        bd_1hop = np.array([d["n_basins_1hop"] for d in boundary_data], dtype=float)
        bd_2hop = np.array([d["n_basins_2hop"] for d in boundary_data], dtype=float)
        bd_comb = np.array([d["n_basins_combined"] for d in boundary_data], dtype=float)
        bd_is_boundary = np.array([1.0 if d["is_boundary_node"] else 0.0 for d in boundary_data])

        boundary_correlations = {
            "basins_1hop_vs_flicker": corr_safe(bd_1hop, bd_trans),
            "basins_2hop_vs_flicker": corr_safe(bd_2hop, bd_trans),
            "basins_combined_vs_flicker": corr_safe(bd_comb, bd_trans),
            "is_boundary_vs_flicker": corr_safe(bd_is_boundary, bd_trans),
        }

        best_boundary = max(boundary_correlations, key=lambda k: abs(boundary_correlations[k]))
        log(f"  Probe 1B: Best boundary predictor: {best_boundary} "
            f"(r={boundary_correlations[best_boundary]:.4f})")

        # Boundary nodes vs non-boundary: mean flicker comparison
        boundary_nodes = [d for d in boundary_data if d["is_boundary_node"]]
        interior_nodes = [d for d in boundary_data if not d["is_boundary_node"]]
        mean_boundary_flicker = (
            np.mean([d["n_transitions"] for d in boundary_nodes]) if boundary_nodes else 0
        )
        mean_interior_flicker = (
            np.mean([d["n_transitions"] for d in interior_nodes]) if interior_nodes else 0
        )
        log(f"    Boundary nodes ({len(boundary_nodes)}): mean flicker = {mean_boundary_flicker:.2f}")
        log(f"    Interior nodes ({len(interior_nodes)}): mean flicker = {mean_interior_flicker:.2f}")

        boundary_result = {
            "correlations": boundary_correlations,
            "best_predictor": best_boundary,
            "mean_boundary_flicker": float(mean_boundary_flicker),
            "mean_interior_flicker": float(mean_interior_flicker),
            "n_boundary_nodes": len(boundary_nodes),
            "n_interior_nodes": len(interior_nodes),
            "node_data": boundary_data,
        }
        save_json("q13_basin_boundary.json", boundary_result)

    # ── Probe 1C: Christine Hayes Deep Dive ──
    if not budget.exhausted():
        log("\n  Probe 1C: Christine Hayes [90] deep dive...")
        ch_id = 90
        ch_neighbors = list(adj.get(ch_id, set()))
        ch_degree = degrees.get(ch_id, 0)
        ch_bc = bc.get(ch_id, 0.0)
        ch_cc = cc.get(ch_id, 0.0)
        ch_ec = ec.get(ch_id, 0.0)

        # Rank among all nodes
        all_bc = sorted(bc.items(), key=lambda x: -x[1])
        all_ec = sorted(ec.items(), key=lambda x: -x[1])
        all_deg = sorted(degrees.items(), key=lambda x: -x[1])
        bc_rank = next(i for i, (nid, _) in enumerate(all_bc) if nid == ch_id) + 1
        ec_rank = next(i for i, (nid, _) in enumerate(all_ec) if nid == ch_id) + 1
        deg_rank = next(i for i, (nid, _) in enumerate(all_deg) if nid == ch_id) + 1

        # Neighbor structural info
        neighbor_info = []
        for nb in ch_neighbors:
            nb_basin = next(
                (d["dominant_basin"] for d in flicker_data if d["inject_id"] == nb), None
            )
            neighbor_info.append({
                "id": nb,
                "label": labels.get(nb, "?"),
                "group": groups.get(nb, "bridge"),
                "degree": degrees.get(nb, 0),
                "basin": nb_basin,
            })

        # Basins of neighbors
        ch_neighbor_basins = set(ni["basin"] for ni in neighbor_info if ni["basin"] is not None)

        # Multi-damping flicker profile
        ch_multi_damping = []
        for d_val in [1.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0]:
            r = probe_basin_sequence(raw_nodes, raw_edges, ch_id, damping=d_val)
            ch_multi_damping.append({
                "damping": d_val,
                "n_transitions": r["n_transitions"],
                "unique_basins": r["unique_basins"],
                "final_basin": r["final_basin"],
                "is_self": r["is_self"],
            })
            budget.trial_count += 1
            if budget.exhausted():
                break

        ch_data = next((d for d in flicker_data if d["inject_id"] == ch_id), {})
        christine_result = {
            "node_id": ch_id,
            "label": labels.get(ch_id, "?"),
            "group": groups.get(ch_id, "bridge"),
            "degree": ch_degree,
            "degree_rank": f"{deg_rank}/{len(node_ids)}",
            "betweenness": round(ch_bc, 6),
            "betweenness_rank": f"{bc_rank}/{len(node_ids)}",
            "clustering": round(ch_cc, 4),
            "eigenvector": round(ch_ec, 6),
            "eigenvector_rank": f"{ec_rank}/{len(node_ids)}",
            "d5_transitions": ch_data.get("n_transitions", 0),
            "d5_unique_basins": ch_data.get("unique_basins", 0),
            "d5_is_self": ch_data.get("is_self", False),
            "n_neighbor_basins": len(ch_neighbor_basins),
            "neighbor_basins": sorted(ch_neighbor_basins),
            "neighbors": neighbor_info,
            "multi_damping_profile": ch_multi_damping,
            "is_boundary_node": any(
                d["is_boundary_node"]
                for d in boundary_data
                if d["id"] == ch_id
            ) if 'boundary_data' in dir() else None,
        }
        log(f"    Christine Hayes: degree={ch_degree} (rank {deg_rank}), "
            f"betweenness={ch_bc:.6f} (rank {bc_rank}), "
            f"neighbor basins={len(ch_neighbor_basins)}")
        save_json("q13_christine_hayes.json", christine_result)

    # ── Probe 1D: Predictive Model ──
    if not budget.exhausted():
        log("\n  Probe 1D: Building predictive model...")

        # Combine all metrics for a multi-variate ranking
        all_metrics = correlations.copy()
        if 'boundary_correlations' in dir():
            all_metrics.update(boundary_correlations)

        # Simple: for each node, compute a combined score
        # Score = weighted sum of top-2 correlating metrics
        sorted_metrics = sorted(all_metrics.items(), key=lambda x: -abs(x[1]))
        top2 = sorted_metrics[:2]
        log(f"    Top 2 predictors: {top2[0][0]} (r={top2[0][1]:.4f}), "
            f"{top2[1][0]} (r={top2[1][1]:.4f})")

        # Heavy flickerer threshold: > 10 transitions (from existing analysis)
        heavy_threshold = 10
        n_heavy = sum(1 for d in flicker_data if d["n_transitions"] > heavy_threshold)
        n_total = len(flicker_data)

        # Top/bottom flickerers
        sorted_by_flicker = sorted(flicker_data, key=lambda d: -d["n_transitions"])
        top10 = sorted_by_flicker[:10]
        bottom10 = sorted_by_flicker[-10:]

        predictive_result = {
            "all_correlations": all_metrics,
            "sorted_by_strength": sorted_metrics,
            "heavy_flickerer_threshold": heavy_threshold,
            "n_heavy": n_heavy,
            "n_total": n_total,
            "top_10_flickerers": [
                {"id": d["inject_id"], "label": d["label"],
                 "transitions": d["n_transitions"], "degree": d["degree"],
                 "betweenness": round(d["betweenness"], 6),
                 "group": d["group"]}
                for d in top10
            ],
            "bottom_10_flickerers": [
                {"id": d["inject_id"], "label": d["label"],
                 "transitions": d["n_transitions"], "degree": d["degree"],
                 "betweenness": round(d["betweenness"], 6),
                 "group": d["group"]}
                for d in bottom10
            ],
        }
        save_json("q13_predictive_model.json", predictive_result)

    budget.end_suite("q13")
    log(f"\n  Suite Q13 complete: {budget.suite_times.get('q13', 0):.1f}s, "
        f"{budget.trial_count} trials so far")


# =========================================================================
# SUITE 2: Q14 — Hot Frozen Basin Determinism
# =========================================================================

def suite_q14(raw_nodes, raw_edges, budget: BudgetTracker):
    """
    Q14: Can d=50 basin assignment be predicted analytically?
    """
    log("\n" + "=" * 70)
    log("SUITE 2 — Q14: HOT FROZEN BASIN DETERMINISM")
    log("=" * 70)
    budget.start_suite("q14")

    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)
    adj = get_adjacency(raw_edges)
    edge_map = get_edge_map(raw_edges)
    node_ids = [n["id"] for n in raw_nodes]

    # ── Probe 2A: Static Conductance Prediction ──
    log("\n  Probe 2A: Static conductance matrix analysis...")

    # Build the initial conductance for each edge
    # From sol_engine: conductance = w0 * base * exp(gamma * avg_psi)
    # At t=0: psi = psi_bias (1.0 for spirit, -1.0 for tech, 0.0 for bridge)
    conductance_base = 1.0
    conductance_gamma = 0.75

    node_psi_bias = {}
    for n in raw_nodes:
        g = n.get("group", "bridge")
        if g == "spirit":
            node_psi_bias[n["id"]] = 1.0
        elif g == "tech":
            node_psi_bias[n["id"]] = -1.0
        else:
            node_psi_bias[n["id"]] = 0.0

    # Compute initial conductance for every edge
    edge_conductances = {}
    for e in raw_edges:
        fid, tid = e["from"], e["to"]
        avg_psi = (node_psi_bias.get(fid, 0) + node_psi_bias.get(tid, 0)) / 2
        w0 = e.get("w0", 1.0)
        cond = w0 * conductance_base * math.exp(conductance_gamma * avg_psi)
        # Clamp like the engine
        cond = max(0.1, min(3.0, cond))
        edge_conductances[(fid, tid)] = cond
        edge_conductances[(tid, fid)] = cond

    # For each node, predict basin = neighbor with highest initial conductance
    static_predictions = {}
    for nid in node_ids:
        best_neighbor = None
        best_cond = -1.0
        for nb in adj.get(nid, set()):
            c = edge_conductances.get((nid, nb), 0.0)
            if c > best_cond:
                best_cond = c
                best_neighbor = nb
        static_predictions[nid] = best_neighbor

    # ── Run actual d=50 probes ──
    log("  Running d=50 basin probes for all 140 nodes...")
    actual_basins = {}
    t0 = time.time()
    for i, nid in enumerate(node_ids):
        r = probe_basin_simple(raw_nodes, raw_edges, nid, damping=50.0, steps=100)
        actual_basins[nid] = r["dominant_basin"]
        budget.trial_count += 1

        if (i + 1) % 40 == 0 or i == len(node_ids) - 1:
            elapsed = time.time() - t0
            log(f"    [{i+1}/{len(node_ids)}] {elapsed:.1f}s")

        if budget.exhausted():
            log("  [WARN] Budget exhausted during Q14 Probe 2A")
            break

    # Compare predictions vs actual
    correct = sum(1 for nid in actual_basins if static_predictions.get(nid) == actual_basins[nid])
    total = len(actual_basins)
    accuracy = 100.0 * correct / total if total > 0 else 0.0
    log(f"  Probe 2A: Static conductance prediction accuracy: {correct}/{total} = {accuracy:.1f}%")

    misses = [
        {"id": nid, "label": labels[nid], "predicted": static_predictions.get(nid),
         "actual": actual_basins[nid], "pred_label": labels.get(static_predictions.get(nid), "?"),
         "actual_label": labels.get(actual_basins[nid], "?")}
        for nid in actual_basins
        if static_predictions.get(nid) != actual_basins[nid]
    ]

    conductance_result = {
        "accuracy_pct": round(accuracy, 1),
        "correct": correct,
        "total": total,
        "n_misses": len(misses),
        "misses": misses[:30],  # Limit for readability
        "predictions": {
            str(nid): {"predicted": static_predictions.get(nid), "actual": actual_basins[nid]}
            for nid in actual_basins
        },
    }
    save_json("q14_conductance_prediction.json", conductance_result)

    # ── Probe 2B: Phase-Gated Prediction ──
    if not budget.exhausted():
        log("\n  Probe 2B: Phase-gated prediction...")

        # Phase gate at t=dt (first step): cos(omega * dt * 10)
        omega = 0.15
        t_first = DT  # 0.12
        phase_val = math.cos(omega * t_first * 10)
        is_surface_active = phase_val > -0.2
        is_deep_active = phase_val < 0.2
        log(f"    Phase at t={t_first}: cos={phase_val:.4f}, "
            f"surface_active={is_surface_active}, deep_active={is_deep_active}")

        # Phase-aware prediction: only consider edges where BOTH endpoints are awake
        phase_predictions = {}
        for nid in node_ids:
            src_group = groups.get(nid, "bridge")
            src_awake = True
            if src_group == "tech" and not is_surface_active:
                src_awake = False
            if src_group == "spirit" and not is_deep_active:
                src_awake = False

            best_neighbor = None
            best_cond = -1.0
            for nb in adj.get(nid, set()):
                dst_group = groups.get(nb, "bridge")
                dst_awake = True
                if dst_group == "tech" and not is_surface_active:
                    dst_awake = False
                if dst_group == "spirit" and not is_deep_active:
                    dst_awake = False

                if not src_awake and not dst_awake:
                    continue

                c = edge_conductances.get((nid, nb), 0.0)
                # Apply tension modifiers
                tension = 1.0
                if src_group == "tech" or dst_group == "tech":
                    tension = 1.2  # surfaceTension
                if src_group == "spirit" or dst_group == "spirit":
                    tension = 0.8  # deepViscosity
                effective_c = c * tension

                if effective_c > best_cond:
                    best_cond = effective_c
                    best_neighbor = nb
            phase_predictions[nid] = best_neighbor

        # Compare
        phase_correct = sum(
            1 for nid in actual_basins
            if phase_predictions.get(nid) == actual_basins[nid]
        )
        phase_accuracy = 100.0 * phase_correct / total if total > 0 else 0.0
        log(f"  Probe 2B: Phase-gated prediction accuracy: "
            f"{phase_correct}/{total} = {phase_accuracy:.1f}%")

        # Improvement over static
        improvement = phase_accuracy - accuracy
        log(f"    Improvement over static: {improvement:+.1f}%")

        phase_result = {
            "accuracy_pct": round(phase_accuracy, 1),
            "correct": phase_correct,
            "total": total,
            "improvement_over_static": round(improvement, 1),
            "phase_at_t0": {
                "t": t_first,
                "cos_val": round(phase_val, 4),
                "surface_active": is_surface_active,
                "deep_active": is_deep_active,
            },
        }
        save_json("q14_phase_gated.json", phase_result)

    # ── Probe 2C: Multi-Hop Prediction ──
    if not budget.exhausted():
        log("\n  Probe 2C: Multi-hop prediction (2-hop relay)...")

        # For misses: check if actual_basin is a 2-hop neighbor
        # (i.e., energy went through a relay)
        multihop_predictions = {}
        for nid in node_ids:
            # 1-hop: best conductance neighbor
            hop1 = phase_predictions.get(nid, static_predictions.get(nid))
            if hop1 is not None and hop1 == actual_basins.get(nid):
                multihop_predictions[nid] = hop1
                continue

            # 2-hop: from hop1, find THAT node's best neighbor
            if hop1 is not None:
                best2 = None
                best2_cond = -1.0
                for nb2 in adj.get(hop1, set()):
                    if nb2 == nid:
                        continue
                    c = edge_conductances.get((hop1, nb2), 0.0)
                    if c > best2_cond:
                        best2_cond = c
                        best2 = nb2
                multihop_predictions[nid] = best2
            else:
                multihop_predictions[nid] = None

        multihop_correct = sum(
            1 for nid in actual_basins
            if multihop_predictions.get(nid) == actual_basins[nid]
        )
        multihop_accuracy = 100.0 * multihop_correct / total if total > 0 else 0.0
        log(f"  Probe 2C: Multi-hop prediction accuracy: "
            f"{multihop_correct}/{total} = {multihop_accuracy:.1f}%")

        multihop_result = {
            "accuracy_pct": round(multihop_accuracy, 1),
            "correct": multihop_correct,
            "total": total,
            "improvement_over_phase": round(multihop_accuracy - phase_accuracy, 1),
            "improvement_over_static": round(multihop_accuracy - accuracy, 1),
        }
        save_json("q14_multihop.json", multihop_result)

    # ── Probe 2D: Extended dampings (d=30, d=75) ──
    if not budget.exhausted():
        log("\n  Probe 2D: Testing prediction model at d=30 and d=75...")
        extended_results = {}
        for d_test in [30.0, 75.0]:
            if budget.exhausted():
                break
            ext_basins = {}
            t0 = time.time()
            for nid in node_ids:
                r = probe_basin_simple(raw_nodes, raw_edges, nid, damping=d_test, steps=100)
                ext_basins[nid] = r["dominant_basin"]
                budget.trial_count += 1
                if budget.exhausted():
                    break

            ext_correct = sum(
                1 for nid in ext_basins
                if static_predictions.get(nid) == ext_basins[nid]
            )
            ext_total = len(ext_basins)
            ext_accuracy = 100.0 * ext_correct / ext_total if ext_total > 0 else 0.0
            log(f"    d={d_test}: static prediction accuracy = "
                f"{ext_correct}/{ext_total} = {ext_accuracy:.1f}%")

            extended_results[str(d_test)] = {
                "accuracy_pct": round(ext_accuracy, 1),
                "correct": ext_correct,
                "total": ext_total,
            }

        save_json("q14_accuracy.json", {
            "d50_static": round(accuracy, 1),
            "d50_phase_gated": round(phase_accuracy, 1) if 'phase_accuracy' in dir() else None,
            "d50_multihop": round(multihop_accuracy, 1) if 'multihop_accuracy' in dir() else None,
            "extended_dampings": extended_results,
        })

    budget.end_suite("q14")
    log(f"\n  Suite Q14 complete: {budget.suite_times.get('q14', 0):.1f}s, "
        f"{budget.trial_count} trials so far")


# =========================================================================
# SUITE 3: Q15 — Identity Gap Bridging
# =========================================================================

def suite_q15(raw_nodes, raw_edges, budget: BudgetTracker):
    """
    Q15: Can any intervention close the d=5-10 identity gap?
    """
    log("\n" + "=" * 70)
    log("SUITE 3 — Q15: IDENTITY GAP BRIDGING")
    log("=" * 70)
    budget.start_suite("q15")

    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)
    adj = get_adjacency(raw_edges)
    node_ids = [n["id"] for n in raw_nodes]

    # Sample 40 representative nodes for faster sweeps
    sorted_by_deg = sorted(node_ids, key=lambda x: degrees.get(x, 0), reverse=True)
    sample_ids = (
        sorted_by_deg[:14]          # top 14 by degree
        + sorted_by_deg[-14:]       # bottom 14
        + sorted_by_deg[56:68]      # middle 12
    )
    sample_ids = list(dict.fromkeys(sample_ids))[:40]

    GAP_DAMPINGS = [5.0, 7.0, 10.0]

    # ── Baseline: measure identity at gap dampings ──
    log("\n  Baseline: measuring identity at d=5, 7, 10 for 40 sample nodes...")
    baseline = {}
    t0 = time.time()
    for d_val in GAP_DAMPINGS:
        results = []
        for nid in sample_ids:
            r = probe_basin_simple(raw_nodes, raw_edges, nid, damping=d_val)
            results.append(r)
            budget.trial_count += 1
        self_pct = 100.0 * sum(1 for r in results if r["is_self"]) / len(results)
        baseline[str(d_val)] = {
            "self_attract_pct": round(self_pct, 1),
            "n_probes": len(results),
        }
        log(f"    d={d_val}: self-attraction = {self_pct:.1f}%")

    # ── Probe 3A: Parameter Tuning ──
    if not budget.exhausted():
        log("\n  Probe 3A: Parameter tuning sweep (c_press, dt)...")

        c_press_values = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
        dt_values = [0.06, 0.12, 0.24, 0.48]

        param_results = []

        # c_press sweep at fixed dt=0.12
        log("    Sweeping c_press...")
        for cp in c_press_values:
            if budget.exhausted():
                break
            for d_val in GAP_DAMPINGS:
                if budget.exhausted():
                    break
                self_count = 0
                for nid in sample_ids:
                    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=RNG_SEED)
                    target = physics.node_by_id.get(nid)
                    if target:
                        target["rho"] += 50.0
                    basin_visits = defaultdict(int)
                    for s in range(1, STEPS + 1):
                        physics.step(DT, cp, d_val)
                        if s % SAMPLE_INTERVAL == 0:
                            m = compute_metrics(physics)
                            bid = m["rhoMaxId"]
                            if bid is not None:
                                basin_visits[bid] += 1
                    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
                    if dominant == nid:
                        self_count += 1
                    budget.trial_count += 1

                self_pct = 100.0 * self_count / len(sample_ids)
                param_results.append({
                    "param": "c_press",
                    "c_press": cp,
                    "dt": DT,
                    "damping": d_val,
                    "self_attract_pct": round(self_pct, 1),
                    "baseline_self_pct": baseline[str(d_val)]["self_attract_pct"],
                    "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
                })
                log(f"      c_press={cp}, d={d_val}: self={self_pct:.1f}% "
                    f"(delta={self_pct - baseline[str(d_val)]['self_attract_pct']:+.1f}%)")

        # dt sweep at fixed c_press=0.1
        log("    Sweeping dt...")
        for dt_val in dt_values:
            if budget.exhausted():
                break
            for d_val in GAP_DAMPINGS:
                if budget.exhausted():
                    break
                self_count = 0
                for nid in sample_ids:
                    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=RNG_SEED)
                    target = physics.node_by_id.get(nid)
                    if target:
                        target["rho"] += 50.0
                    basin_visits = defaultdict(int)
                    for s in range(1, STEPS + 1):
                        physics.step(dt_val, C_PRESS, d_val)
                        if s % SAMPLE_INTERVAL == 0:
                            m = compute_metrics(physics)
                            bid = m["rhoMaxId"]
                            if bid is not None:
                                basin_visits[bid] += 1
                    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
                    if dominant == nid:
                        self_count += 1
                    budget.trial_count += 1

                self_pct = 100.0 * self_count / len(sample_ids)
                param_results.append({
                    "param": "dt",
                    "c_press": C_PRESS,
                    "dt": dt_val,
                    "damping": d_val,
                    "self_attract_pct": round(self_pct, 1),
                    "baseline_self_pct": baseline[str(d_val)]["self_attract_pct"],
                    "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
                })
                log(f"      dt={dt_val}, d={d_val}: self={self_pct:.1f}% "
                    f"(delta={self_pct - baseline[str(d_val)]['self_attract_pct']:+.1f}%)")

        # Best intervention
        best_param = max(param_results, key=lambda r: r["delta"]) if param_results else None
        if best_param:
            log(f"    Best parameter intervention: {best_param['param']}="
                f"{best_param.get(best_param['param'], '?')}, d={best_param['damping']} "
                f"-> delta={best_param['delta']:+.1f}%")

        save_json("q15_param_tuning.json", {
            "baseline": baseline,
            "results": param_results,
            "best_intervention": best_param,
        })

    # ── Probe 3B: Multi-Injection Defense ──
    if not budget.exhausted():
        log("\n  Probe 3B: Multi-injection defense...")

        multi_inj_results = []
        for d_val in GAP_DAMPINGS:
            if budget.exhausted():
                break
            self_count = 0
            for nid in sample_ids:
                if budget.exhausted():
                    break
                physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=RNG_SEED)

                # Inject target node
                target = physics.node_by_id.get(nid)
                if target:
                    target["rho"] += 50.0

                # ALSO inject the 5 standard nodes for "shielding"
                for lbl, amt in STANDARD_INJECTIONS:
                    for n in physics.nodes:
                        if n["label"].lower() == lbl.lower() and n["id"] != nid:
                            n["rho"] += amt
                            break

                basin_visits = defaultdict(int)
                for s in range(1, STEPS + 1):
                    physics.step(DT, C_PRESS, d_val)
                    if s % SAMPLE_INTERVAL == 0:
                        m = compute_metrics(physics)
                        bid = m["rhoMaxId"]
                        if bid is not None:
                            basin_visits[bid] += 1

                dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
                if dominant == nid:
                    self_count += 1
                budget.trial_count += 1

            self_pct = 100.0 * self_count / len(sample_ids)
            multi_inj_results.append({
                "damping": d_val,
                "self_attract_pct": round(self_pct, 1),
                "baseline_self_pct": baseline[str(d_val)]["self_attract_pct"],
                "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
            })
            log(f"    d={d_val}: multi-inject self={self_pct:.1f}% "
                f"(delta={self_pct - baseline[str(d_val)]['self_attract_pct']:+.1f}%)")

        save_json("q15_multi_inject.json", {
            "strategy": "Inject target + 5 standard hubs simultaneously",
            "results": multi_inj_results,
        })

    # ── Probe 3C: Topology Surgery ──
    if not budget.exhausted():
        log("\n  Probe 3C: Topology surgery...")

        surgery_results = []

        # Strategy 1: Add self-loops (w0=2.0) to every node
        log("    Strategy: self-loop reinforcement (w0=2.0)...")
        modified_edges_selfloop = copy.deepcopy(raw_edges)
        for n in raw_nodes:
            modified_edges_selfloop.append({
                "from": n["id"], "to": n["id"], "w0": 2.0,
            })

        for d_val in GAP_DAMPINGS:
            if budget.exhausted():
                break
            self_count = 0
            for nid in sample_ids:
                r = probe_basin_simple(raw_nodes, modified_edges_selfloop, nid, damping=d_val)
                if r["is_self"]:
                    self_count += 1
                budget.trial_count += 1

            self_pct = 100.0 * self_count / len(sample_ids)
            surgery_results.append({
                "strategy": "self_loop_w2",
                "damping": d_val,
                "self_attract_pct": round(self_pct, 1),
                "baseline_self_pct": baseline[str(d_val)]["self_attract_pct"],
                "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
            })
            log(f"      d={d_val}: self-loop self={self_pct:.1f}% "
                f"(delta={self_pct - baseline[str(d_val)]['self_attract_pct']:+.1f}%)")

        # Strategy 2: Boost edge weights for low-degree nodes
        log("    Strategy: low-degree edge boosting (w0 *= 3.0 for deg<=3)...")
        modified_edges_boost = copy.deepcopy(raw_edges)
        low_deg_ids = {nid for nid, d in degrees.items() if d <= 3}
        for e in modified_edges_boost:
            if e["from"] in low_deg_ids or e["to"] in low_deg_ids:
                e["w0"] = e.get("w0", 1.0) * 3.0

        for d_val in GAP_DAMPINGS:
            if budget.exhausted():
                break
            self_count = 0
            for nid in sample_ids:
                r = probe_basin_simple(raw_nodes, modified_edges_boost, nid, damping=d_val)
                if r["is_self"]:
                    self_count += 1
                budget.trial_count += 1

            self_pct = 100.0 * self_count / len(sample_ids)
            surgery_results.append({
                "strategy": "low_deg_boost_3x",
                "damping": d_val,
                "self_attract_pct": round(self_pct, 1),
                "baseline_self_pct": baseline[str(d_val)]["self_attract_pct"],
                "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
            })
            log(f"      d={d_val}: low-deg boost self={self_pct:.1f}% "
                f"(delta={self_pct - baseline[str(d_val)]['self_attract_pct']:+.1f}%)")

        # Strategy 3: Double all edge weights
        log("    Strategy: global w0 doubling...")
        modified_edges_double = copy.deepcopy(raw_edges)
        for e in modified_edges_double:
            e["w0"] = e.get("w0", 1.0) * 2.0

        for d_val in GAP_DAMPINGS:
            if budget.exhausted():
                break
            self_count = 0
            for nid in sample_ids:
                r = probe_basin_simple(raw_nodes, modified_edges_double, nid, damping=d_val)
                if r["is_self"]:
                    self_count += 1
                budget.trial_count += 1

            self_pct = 100.0 * self_count / len(sample_ids)
            surgery_results.append({
                "strategy": "global_w0_double",
                "damping": d_val,
                "self_attract_pct": round(self_pct, 1),
                "baseline_self_pct": baseline[str(d_val)]["self_attract_pct"],
                "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
            })
            log(f"      d={d_val}: global w0 2x self={self_pct:.1f}% "
                f"(delta={self_pct - baseline[str(d_val)]['self_attract_pct']:+.1f}%)")

        # Strategy 4: Halve all edge weights (reduce transport)
        log("    Strategy: global w0 halving (reduce transport)...")
        modified_edges_half = copy.deepcopy(raw_edges)
        for e in modified_edges_half:
            e["w0"] = e.get("w0", 1.0) * 0.5

        for d_val in GAP_DAMPINGS:
            if budget.exhausted():
                break
            self_count = 0
            for nid in sample_ids:
                r = probe_basin_simple(raw_nodes, modified_edges_half, nid, damping=d_val)
                if r["is_self"]:
                    self_count += 1
                budget.trial_count += 1

            self_pct = 100.0 * self_count / len(sample_ids)
            surgery_results.append({
                "strategy": "global_w0_half",
                "damping": d_val,
                "self_attract_pct": round(self_pct, 1),
                "baseline_self_pct": baseline[str(d_val)]["self_attract_pct"],
                "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
            })
            log(f"      d={d_val}: global w0 0.5x self={self_pct:.1f}% "
                f"(delta={self_pct - baseline[str(d_val)]['self_attract_pct']:+.1f}%)")

        best_surgery = max(surgery_results, key=lambda r: r["delta"]) if surgery_results else None
        if best_surgery:
            log(f"    Best surgery: {best_surgery['strategy']} at d={best_surgery['damping']} "
                f"-> delta={best_surgery['delta']:+.1f}%")

        save_json("q15_topology_surgery.json", {
            "baseline": baseline,
            "results": surgery_results,
            "best_intervention": best_surgery,
        })

    # ── Probe 3D: Injection Magnitude Sweep ──
    if not budget.exhausted():
        log("\n  Probe 3D: Injection magnitude sweep at d=5-10...")

        inj_amounts = [10.0, 25.0, 50.0, 100.0, 200.0, 500.0, 1000.0]
        inj_results = []

        for inj_amt in inj_amounts:
            if budget.exhausted():
                break
            for d_val in GAP_DAMPINGS:
                if budget.exhausted():
                    break
                self_count = 0
                for nid in sample_ids:
                    r = probe_basin_simple(raw_nodes, raw_edges, nid, damping=d_val,
                                            inject_amount=inj_amt)
                    if r["is_self"]:
                        self_count += 1
                    budget.trial_count += 1

                self_pct = 100.0 * self_count / len(sample_ids)
                inj_results.append({
                    "injection": inj_amt,
                    "damping": d_val,
                    "self_attract_pct": round(self_pct, 1),
                    "delta": round(self_pct - baseline[str(d_val)]["self_attract_pct"], 1),
                })
                log(f"      inj={inj_amt}, d={d_val}: self={self_pct:.1f}%")

        save_json("q15_injection_sweep.json", {
            "baseline": baseline,
            "results": inj_results,
        })

    # ── Probe 3E: Growth + Defense ──
    if not budget.exhausted():
        log("\n  Probe 3E: Jeans growth with pre-stabilization...")

        # Test: at d=5, does pre-injecting hubs BEFORE growth help stability?
        growth_results = []

        try:
            from jeans_cosmology_experiment import (
                SynthSpawner, apply_tractor_beam, _build_adjacency,
                INJECTION_STRATEGIES,
            )

            for defense in ["none", "pre_inject", "double_w0"]:
                if budget.exhausted():
                    break

                for d_val in GAP_DAMPINGS:
                    if budget.exhausted():
                        break

                    # Prepare graph
                    test_edges = copy.deepcopy(raw_edges)
                    if defense == "double_w0":
                        for e in test_edges:
                            e["w0"] = e.get("w0", 1.0) * 2.0

                    # Run growth phase
                    physics, _ = create_engine(raw_nodes, test_edges, rng_seed=RNG_SEED)

                    if defense == "pre_inject":
                        for lbl, amt in STANDARD_INJECTIONS:
                            physics.inject(lbl, amt)

                    # Run 200 steps at low damping to trigger Jeans
                    for s in range(200):
                        physics.step(DT, C_PRESS, 0.2)

                    # Count synth nodes
                    n_synths = sum(1 for n in physics.nodes if n.get("isStellar"))

                    # Now re-probe at gap damping with grown graph
                    grown_nodes = [
                        {"id": n["id"], "label": n["label"],
                         "group": n.get("group", "bridge"),
                         "semanticMass": n.get("semanticMass", 1.0)}
                        for n in physics.nodes
                    ]
                    grown_edges = [
                        {"from": e["from"], "to": e["to"], "w0": e.get("w0", 1.0)}
                        for e in physics.edges
                    ]

                    # Get original node ids
                    orig_in_grown = [nid for nid in sample_ids
                                      if any(n["id"] == nid for n in grown_nodes)]

                    self_count = 0
                    for nid in orig_in_grown[:20]:  # Limit for speed
                        r = probe_basin_simple(grown_nodes, grown_edges, nid, damping=d_val)
                        if r["is_self"]:
                            self_count += 1
                        budget.trial_count += 1

                    n_tested = min(20, len(orig_in_grown))
                    self_pct = 100.0 * self_count / n_tested if n_tested > 0 else 0.0

                    growth_results.append({
                        "defense": defense,
                        "damping": d_val,
                        "n_synths": n_synths,
                        "n_tested": n_tested,
                        "self_attract_pct": round(self_pct, 1),
                    })
                    log(f"      defense={defense}, d={d_val}: "
                        f"synths={n_synths}, self={self_pct:.1f}%")

        except ImportError:
            log("    [WARN] jeans_cosmology_experiment not available, skipping growth test")
            growth_results = [{"error": "jeans import failed"}]

        save_json("q15_growth_defense.json", {
            "baseline": baseline,
            "results": growth_results,
        })

    budget.end_suite("q15")
    log(f"\n  Suite Q15 complete: {budget.suite_times.get('q15', 0):.1f}s, "
        f"{budget.trial_count} trials so far")


# =========================================================================
# SUITE 4: Cross-Question Synthesis
# =========================================================================

def suite_cross(raw_nodes, raw_edges, budget: BudgetTracker):
    """
    Cross-question synthesis: connect Q13 -> Q14 -> Q15 findings.
    """
    log("\n" + "=" * 70)
    log("SUITE 4 — CROSS-QUESTION SYNTHESIS")
    log("=" * 70)
    budget.start_suite("cross")

    labels = get_labels(raw_nodes)
    node_ids = [n["id"] for n in raw_nodes]
    adj = get_adjacency(raw_edges)
    degrees = get_degrees(raw_edges)

    # Load Q13 results if available
    q13_census_path = _OUTPUT_DIR / "q13_structural_census.json"
    q14_accuracy_path = _OUTPUT_DIR / "q14_accuracy.json"

    synthesis = {"probes": []}

    # ── Probe 4A: Structural predictors vs vulnerability ──
    if q13_census_path.exists() and not budget.exhausted():
        log("\n  Probe 4A: Structural predictors vs identity vulnerability...")

        with open(q13_census_path) as f:
            census = json.load(f)

        node_data = {d["id"]: d for d in census.get("node_data", [])}

        # Run identity test at border dampings (d=5,7,10)
        vulnerability_data = []
        for nid in node_ids:
            if budget.exhausted():
                break
            nd = node_data.get(nid, {})
            results_by_d = {}
            for d_val in [5.0, 7.0, 10.0]:
                r = probe_basin_simple(raw_nodes, raw_edges, nid, damping=d_val)
                results_by_d[str(d_val)] = r["is_self"]
                budget.trial_count += 1

            # Vulnerability = fraction of gap dampings where identity is lost
            n_lost = sum(1 for v in results_by_d.values() if not v)
            vulnerability = n_lost / len(results_by_d)

            vulnerability_data.append({
                "id": nid,
                "label": labels[nid],
                "degree": nd.get("degree", 0),
                "betweenness": nd.get("betweenness", 0.0),
                "clustering": nd.get("clustering", 0.0),
                "eigenvector": nd.get("eigenvector", 0.0),
                "n_transitions_d5": nd.get("n_transitions", 0),
                "vulnerability": vulnerability,
                "self_d5": results_by_d.get("5.0", False),
                "self_d7": results_by_d.get("7.0", False),
                "self_d10": results_by_d.get("10.0", False),
            })

        # Correlate structural metrics with vulnerability
        if vulnerability_data:
            vuln_arr = np.array([d["vulnerability"] for d in vulnerability_data])
            deg_arr = np.array([d["degree"] for d in vulnerability_data], dtype=float)
            bc_arr = np.array([d["betweenness"] for d in vulnerability_data])
            trans_arr = np.array([d["n_transitions_d5"] for d in vulnerability_data], dtype=float)

            def corr_safe(a, b):
                if len(a) < 3:
                    return 0.0
                c = np.corrcoef(a, b)
                r = c[0, 1]
                return float(r) if np.isfinite(r) else 0.0

            vuln_correlations = {
                "degree_vs_vulnerability": corr_safe(deg_arr, vuln_arr),
                "betweenness_vs_vulnerability": corr_safe(bc_arr, vuln_arr),
                "d5_flicker_vs_vulnerability": corr_safe(trans_arr, vuln_arr),
            }

            log(f"    Correlations with identity vulnerability:")
            for k, v in sorted(vuln_correlations.items(), key=lambda x: -abs(x[1])):
                log(f"      {k}: r = {v:.4f}")

            synthesis["probes"].append({
                "probe": "4A",
                "question": "Do Q13 structural predictors predict Q15 vulnerability?",
                "correlations": vuln_correlations,
                "n_nodes": len(vulnerability_data),
                "mean_vulnerability": float(np.mean(vuln_arr)),
                "node_data": vulnerability_data[:10],  # Top 10 for readability
            })

    # ── Probe 4B: Q14 model extension ──
    if q14_accuracy_path.exists() and not budget.exhausted():
        log("\n  Probe 4B: Q14 analytical model extension...")
        with open(q14_accuracy_path) as f:
            q14_data = json.load(f)

        synthesis["probes"].append({
            "probe": "4B",
            "question": "Does Q14 analytical model extend to other dampings?",
            "q14_results": q14_data,
        })

    save_json("q_cross_synthesis.json", synthesis)

    budget.end_suite("cross")
    log(f"\n  Suite Cross complete: {budget.suite_times.get('cross', 0):.1f}s, "
        f"{budget.trial_count} trials so far")


# =========================================================================
# REPORT GENERATOR
# =========================================================================

def generate_report(budget: BudgetTracker):
    """Generate the overnight report markdown."""
    log("\n" + "=" * 70)
    log("GENERATING REPORT")
    log("=" * 70)

    lines = [
        "# SOL Overnight RSI — Q13-Q15 Investigation Report",
        "",
        f"**Run timestamp:** {_RUN_TS}",
        f"**Total runtime:** {budget.elapsed():.1f}s ({budget.elapsed()/3600:.2f}h)",
        f"**Total trials:** {budget.trial_count}",
        f"**Budget used:** {budget.pct():.1f}%",
        "",
        "## Suite Runtimes",
        "",
        "| Suite | Runtime |",
        "|-------|--------:|",
    ]

    for suite, secs in budget.suite_times.items():
        lines.append(f"| {suite} | {secs:.1f}s ({secs/60:.1f}m) |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Load and summarize each result file
    result_files = sorted(_OUTPUT_DIR.glob("q*.json"))
    for rf in result_files:
        try:
            with open(rf) as f:
                data = json.load(f)

            lines.append(f"## {rf.stem}")
            lines.append("")

            if "correlations" in data:
                lines.append("### Correlations")
                lines.append("")
                lines.append("| Metric | r |")
                lines.append("|--------|--:|")
                for k, v in sorted(data["correlations"].items(), key=lambda x: -abs(x[1])):
                    lines.append(f"| {k} | {v:.4f} |")
                lines.append("")

            if "accuracy_pct" in data:
                lines.append(f"**Accuracy:** {data['accuracy_pct']}%")
                lines.append("")

            if "best_intervention" in data and data["best_intervention"]:
                bi = data["best_intervention"]
                lines.append(f"**Best intervention:** {bi}")
                lines.append("")

            if "results" in data and isinstance(data["results"], list):
                # Summarize first few results
                lines.append(f"**Results:** {len(data['results'])} entries")
                lines.append("")

            lines.append("---")
            lines.append("")

        except Exception as e:
            lines.append(f"## {rf.stem}")
            lines.append(f"*Error reading: {e}*")
            lines.append("")

    # Answers to open questions
    lines.extend([
        "## Provisional Answers",
        "",
        "### Q13: What structural property determines heavy flickerers?",
        "",
        "_See q13_structural_census.json and q13_basin_boundary.json for full data._",
        "_Check the `best_predictor` field in each result for the winning metric._",
        "",
        "### Q14: Can d=50 basins be predicted analytically?",
        "",
        "_See q14_accuracy.json for prediction accuracy across methods._",
        "_Compare static, phase-gated, and multi-hop prediction strategies._",
        "",
        "### Q15: Can any intervention close the identity gap?",
        "",
        "_See q15_param_tuning.json, q15_topology_surgery.json, etc._",
        "_Look for the largest positive delta in self-attraction %._",
        "",
        "---",
        "",
        f"*Report generated at {datetime.now(timezone.utc).isoformat()}*",
    ])

    with open(_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log(f"  Report saved: {_REPORT_FILE}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SOL Overnight RSI — Q13-Q15")
    parser.add_argument("--budget-hours", type=float, default=7.0,
                        help="Maximum runtime in hours (default: 7)")
    parser.add_argument("--suite", type=int, nargs="+", default=None,
                        help="Run only these suites (e.g. --suite 3 4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Plan only, don't run experiments")
    parser.add_argument("--smoke", action="store_true",
                        help="Quick smoke test (~2 min)")
    args = parser.parse_args()

    budget_hours = args.budget_hours
    if args.smoke:
        budget_hours = 0.05  # ~3 minutes

    log("=" * 70)
    log("SOL OVERNIGHT RSI — Q13-Q15 DEEP INVESTIGATION")
    log("=" * 70)
    log(f"Budget: {budget_hours:.1f}h ({budget_hours * 3600:.0f}s)")
    log(f"Output: {_OUTPUT_DIR}")
    log(f"Start:  {datetime.now(timezone.utc).isoformat()}")
    log("")

    if args.dry_run:
        log("DRY RUN — planning only, no experiments will execute")
        log("")
        log("Suite 1 (Q13): Structural census + basin boundary + Christine Hayes + predictive model")
        log("Suite 2 (Q14): Static conductance + phase-gated + multi-hop prediction")
        log("Suite 3 (Q15): Parameter tuning + multi-inject + topology surgery + injection sweep + growth")
        log("Suite 4 (Cross): Structural predictors vs vulnerability + model extension")
        flush_log()
        return

    budget = BudgetTracker(budget_hours)
    raw_nodes, raw_edges = load_default_graph()

    log(f"Graph loaded: {len(raw_nodes)} nodes, {len(raw_edges)} edges")
    log("")

    suites = [
        (1, "Q13: Flickering Mechanism", suite_q13),
        (2, "Q14: Hot Frozen Determinism", suite_q14),
        (3, "Q15: Identity Gap Bridging", suite_q15),
        (4, "Cross-Question Synthesis", suite_cross),
    ]

    for suite_num, suite_name, suite_fn in suites:
        if args.suite and suite_num not in args.suite:
            continue
        if budget.exhausted():
            log(f"\n[WARN] Budget exhausted before Suite {suite_num}: {suite_name}")
            break
        try:
            suite_fn(raw_nodes, raw_edges, budget)
        except Exception as e:
            log(f"\n[ERROR] Suite {suite_num} failed: {e}")
            log(traceback.format_exc())
        flush_log()

    # Generate report
    generate_report(budget)

    log("")
    log("=" * 70)
    log("OVERNIGHT RSI COMPLETE")
    log("=" * 70)
    log(f"Total runtime: {budget.elapsed():.1f}s ({budget.elapsed()/3600:.2f}h)")
    log(f"Total trials:  {budget.trial_count}")
    log(f"Budget used:   {budget.pct():.1f}%")
    log(f"Output:        {_OUTPUT_DIR}")
    log(f"End:           {datetime.now(timezone.utc).isoformat()}")

    flush_log()


if __name__ == "__main__":
    main()
