#!/usr/bin/env python3
"""
SOL Lattice Stress Test — Combined Three-Vector Experiment
============================================================

Combines three independent probes into a unified experiment suite
to test the lattice's computational limits and hunt for emergent phenomena:

  TEST A — Cold-Node Identity Mapping Under Damping Stress
    Inject each of 140 nodes individually at 5 damping values.
    Track which nodes are cold (never dominant), which wake up under stress,
    and whether cold-node identity is invariant or damping-dependent.
    700 trials (140 nodes × 5 damping values)

  TEST B — Weighted Conductance Channels
    Modify edge w0 weights to create "highways" (w0=3.0) and "walls" (w0=0.1).
    4 weight topologies: UNIFORM, SPIRIT_HIGHWAY, INJECTION_HIGHWAY, HUB_WALL
    Each at 4 damping values × 2 injection patterns = 32 trials.
    Tests whether conductance programming can steer basin formation.

  TEST C — Injection Protocol Variation
    6 injection protocols: STANDARD, REVERSED, SEQUENTIAL, SINGLE_MASSIVE,
    COLD_INJECT, SPREAD_UNIFORM
    Each at 6 damping values = 36 trials.
    Tests whether injection ORDER, MAGNITUDE, and TARGET selection
    produce different basin structures or reveal new phase transitions.

Total: ~768 trials

Outputs: data/lattice_stress_test.json
"""
from __future__ import annotations

import copy
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

_SOL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))

from sol_engine import SOLEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DT = 0.12
C_PRESS = 0.1
STEPS = 500
SAMPLE_INTERVAL = 5

STANDARD_INJECTIONS = [
    ("grail", 40.0),
    ("metatron", 35.0),
    ("pyramid", 30.0),
    ("christ", 25.0),
    ("light codes", 20.0),
]

# Damping values spanning all known regimes
STRESS_DAMPS = [0.2, 5.0, 20.0, 55.0, 79.5]
WEIGHT_DAMPS = [0.2, 5.0, 20.0, 79.5]
INJECT_DAMPS = [0.2, 5.0, 20.0, 55.0, 79.5, 83.0]


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


def make_engine(raw_nodes, raw_edges, damping, seed=42):
    return SOLEngine.from_graph(
        raw_nodes, raw_edges,
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed
    )


def apply_standard_injection(engine):
    for label, amount in STANDARD_INJECTIONS:
        engine.inject(label, amount)


# ---------------------------------------------------------------------------
# Shared analysis
# ---------------------------------------------------------------------------

def analyze_trial(engine, rho_samples):
    """Compute mode count, coherence, iton score, dominant basin from rho samples."""
    n_nodes = len(engine.physics.nodes)
    rho_arr = np.array(rho_samples) if rho_samples else np.zeros((1, n_nodes))

    # Mode count (CoV > 0.01)
    osc_amps = []
    for j in range(n_nodes):
        trace = rho_arr[:, j]
        if np.max(trace) > 1e-15:
            osc_amps.append(np.std(trace) / max(np.mean(trace), 1e-15))
        else:
            osc_amps.append(0.0)
    n_modes = int(np.sum(np.array(osc_amps) > 0.01))

    # Active mode identities (which node IDs are phonon-active)
    active_mode_ids = []
    for j in range(n_nodes):
        if osc_amps[j] > 0.01:
            active_mode_ids.append(engine.physics.nodes[j]["id"])

    # Coherence (injection nodes)
    id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}
    inj_indices = [id_to_idx.get(nid) for nid in [1, 2, 9, 23, 29]]
    inj_indices = [i for i in inj_indices if i is not None]

    corrs = []
    for a in range(len(inj_indices)):
        for b in range(a + 1, len(inj_indices)):
            t1 = rho_arr[:, inj_indices[a]].copy()
            t2 = rho_arr[:, inj_indices[b]].copy()
            r1 = np.max(t1) - np.min(t1)
            r2 = np.max(t2) - np.min(t2)
            if r1 > 0 and r2 > 0:
                t1n = (t1 - np.mean(t1)) / r1
                t2n = (t2 - np.mean(t2)) / r2
                c = np.corrcoef(t1n, t2n)[0, 1]
                if not np.isnan(c):
                    corrs.append(abs(c))
    coherence = float(np.mean(corrs)) if corrs else 0.0

    # Iton score
    node_edges_map = defaultdict(list)
    for ei, e in enumerate(engine.physics.edges):
        node_edges_map[e["from"]].append((ei, "from"))
        node_edges_map[e["to"]].append((ei, "to"))

    n_sources = 0
    n_pass = 0
    n_sinks = 0
    n_directional = 0
    total_active = 0

    for ni, n in enumerate(engine.physics.nodes):
        nid = n["id"]
        inflow = 0.0
        outflow = 0.0
        for ei, role in node_edges_map[nid]:
            flux = engine.physics.edges[ei].get("flux", 0.0)
            if role == "from":
                if flux > 0:
                    outflow += flux
                else:
                    inflow += abs(flux)
            else:
                if flux > 0:
                    inflow += flux
                else:
                    outflow += abs(flux)
        if inflow + outflow > 0.001:
            total_active += 1
            if abs(inflow - outflow) < 0.3 * (inflow + outflow):
                n_pass += 1
            elif inflow > outflow:
                n_sinks += 1
            else:
                n_sources += 1

    # Count directional edges (>80% one-way)
    for e in engine.physics.edges:
        flux = abs(e.get("flux", 0.0))
        if flux > 0.001:
            n_directional += 1

    iton_score = n_pass / total_active if total_active > 0 else 0.0

    # Conductance statistics
    conductances = [e.get("conductance", 1.0) for e in engine.physics.edges]
    cond_mean = float(np.mean(conductances))
    cond_std = float(np.std(conductances))
    cond_max = float(np.max(conductances))
    cond_min = float(np.min(conductances))

    return {
        "n_modes": n_modes,
        "active_mode_ids": active_mode_ids,
        "coherence": coherence,
        "iton_score": iton_score,
        "n_sources": n_sources,
        "n_pass": n_pass,
        "n_sinks": n_sinks,
        "n_directional": n_directional,
        "conductance_mean": cond_mean,
        "conductance_std": cond_std,
        "conductance_max": cond_max,
        "conductance_min": cond_min,
    }


def run_and_analyze(engine, steps=STEPS, sample_every=SAMPLE_INTERVAL):
    """Step the engine, collect rho samples, compute metrics."""
    basin_visits = defaultdict(int)
    rho_samples = []

    for s in range(1, steps + 1):
        engine.step()
        if s % sample_every == 0:
            m = engine.compute_metrics()
            bid = m["rhoMaxId"]
            if bid is not None:
                basin_visits[bid] = basin_visits.get(bid, 0) + 1
            rho_samples.append([n["rho"] for n in engine.physics.nodes])

    final = engine.compute_metrics()
    analysis = analyze_trial(engine, rho_samples)

    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
    node_rho_final = {n["id"]: n["rho"] for n in engine.physics.nodes}

    analysis["dominant_basin"] = dominant
    analysis["final_maxrho"] = final["maxRho"]
    analysis["final_entropy"] = final["entropy"]
    analysis["final_mass"] = final["mass"]
    analysis["basin_visits"] = dict(basin_visits)
    analysis["node_rho_final_top10"] = sorted(
        node_rho_final.items(), key=lambda x: x[1], reverse=True
    )[:10]

    return analysis


# ===================================================================
# TEST A — Cold-Node Identity Mapping Under Damping Stress
# ===================================================================

def test_a_cold_node_mapping():
    """Inject each of 140 nodes individually at 5 damping values.
    
    Returns per-damping cold-node sets and cross-damping comparison.
    """
    print("\n" + "=" * 70)
    print("  TEST A - COLD-NODE IDENTITY MAPPING UNDER DAMPING STRESS")
    print("  140 nodes x 5 damping values = 700 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    all_ids = sorted(labels.keys())

    results_by_damp = {}
    t0 = time.time()
    trial_count = 0

    for damp in STRESS_DAMPS:
        print(f"\n  Damping d={damp}:")
        basin_freq = defaultdict(int)
        injection_results = {}
        self_attractors = []
        cold_nodes = []

        t_d = time.time()
        for nid in all_ids:
            engine = make_engine(
                copy.deepcopy(raw_nodes), copy.deepcopy(raw_edges),
                damping=damp, seed=42
            )
            engine.inject_by_id(nid, 50.0)

            basin_visits = defaultdict(int)
            for s in range(1, STEPS + 1):
                engine.step()
                if s % 50 == 0:
                    m = engine.compute_metrics()
                    bid = m["rhoMaxId"]
                    if bid is not None:
                        basin_visits[bid] = basin_visits.get(bid, 0) + 1

            dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
            basin_freq[dominant] = basin_freq.get(dominant, 0) + 1
            final = engine.compute_metrics()

            injection_results[nid] = {
                "dominant_basin": dominant,
                "final_maxRho": final["maxRho"],
            }
            if dominant == nid:
                self_attractors.append(nid)
            trial_count += 1

        # Cold nodes: never appear as dominant
        all_dominant = set(v["dominant_basin"] for v in injection_results.values())
        cold_nodes = [nid for nid in all_ids if nid not in all_dominant]

        elapsed = time.time() - t_d

        # Where cold nodes redirect to
        cold_redirect = {}
        for nid in cold_nodes:
            dest = injection_results[nid]["dominant_basin"]
            cold_redirect[nid] = dest

        print(f"    Self-attractors: {len(self_attractors)}")
        print(f"    Cold nodes: {len(cold_nodes)}")
        print(f"    Basin families: {len(set(basin_freq.keys()))}")
        print(f"    [{elapsed:.1f}s]")

        results_by_damp[damp] = {
            "self_attractors": self_attractors,
            "cold_nodes": cold_nodes,
            "cold_redirect": cold_redirect,
            "basin_freq": {str(k): v for k, v in basin_freq.items()},
            "n_self_attractors": len(self_attractors),
            "n_cold": len(cold_nodes),
            "n_basin_families": len(set(basin_freq.keys())),
        }

    total_time = time.time() - t0

    # Cross-damping analysis
    print(f"\n  CROSS-DAMPING COMPARISON:")
    all_cold_sets = {d: set(r["cold_nodes"]) for d, r in results_by_damp.items()}

    # Invariant cold nodes (cold at ALL damping values)
    invariant_cold = set.intersection(*all_cold_sets.values()) if all_cold_sets else set()
    print(f"    Invariant cold nodes (cold at ALL {len(STRESS_DAMPS)} damping values): "
          f"{len(invariant_cold)}")
    for nid in sorted(invariant_cold):
        print(f"      [{nid:3d}] {labels.get(nid, '?'):<25} group={groups.get(nid, '?')}")

    # Stress-activated nodes (cold at d=0.2 but NOT cold at high damping)
    cold_at_low = all_cold_sets.get(0.2, set())
    stress_activated = []
    for nid in sorted(cold_at_low):
        wakes_at = [d for d in STRESS_DAMPS if d > 0.2 and nid not in all_cold_sets.get(d, set())]
        if wakes_at:
            stress_activated.append((nid, wakes_at))

    print(f"\n    Stress-activated nodes (cold at d=0.2, wake under higher damping): "
          f"{len(stress_activated)}")
    for nid, wakes in stress_activated[:20]:
        print(f"      [{nid:3d}] {labels.get(nid, '?'):<25} "
              f"wakes at d={wakes}")

    # Stress-killed nodes (self-attractor at d=0.2 but cold at high damping)
    self_at_low = set(results_by_damp[0.2]["self_attractors"])
    stress_killed = []
    for nid in sorted(self_at_low):
        dies_at = [d for d in STRESS_DAMPS if d > 0.2 and nid in all_cold_sets.get(d, set())]
        if dies_at:
            stress_killed.append((nid, dies_at))

    print(f"\n    Stress-killed nodes (self-attractor at d=0.2, cold at higher damping): "
          f"{len(stress_killed)}")
    for nid, dies in stress_killed[:20]:
        print(f"      [{nid:3d}] {labels.get(nid, '?'):<25} "
              f"dies at d={dies}")

    # Cold-node redirect stability
    redirect_changes = 0
    redirect_stable = 0
    for nid in invariant_cold:
        dests = set()
        for d in STRESS_DAMPS:
            dest = results_by_damp[d]["cold_redirect"].get(nid)
            if dest is not None:
                dests.add(dest)
        if len(dests) == 1:
            redirect_stable += 1
        else:
            redirect_changes += 1

    print(f"\n    Invariant cold nodes with STABLE redirect: {redirect_stable}")
    print(f"    Invariant cold nodes with CHANGING redirect: {redirect_changes}")

    print(f"\n  Total: {trial_count} trials in {total_time:.1f}s")

    return {
        "runtime_sec": round(total_time, 2),
        "trials": trial_count,
        "results_by_damp": {str(d): r for d, r in results_by_damp.items()},
        "invariant_cold": sorted(invariant_cold),
        "stress_activated": [(nid, wakes) for nid, wakes in stress_activated],
        "stress_killed": [(nid, dies) for nid, dies in stress_killed],
    }


# ===================================================================
# TEST B — Weighted Conductance Channels
# ===================================================================

def make_weighted_graph(raw_nodes, raw_edges, topology_name, labels, groups):
    """Apply weight topology to a copy of the graph.
    
    Modifies w0 on edges to create conductance highways and walls.
    Returns (nodes, edges, description).
    """
    nodes = copy.deepcopy(raw_nodes)
    edges = copy.deepcopy(raw_edges)

    if topology_name == "UNIFORM":
        # Control: all w0 = 1.0 (default)
        for e in edges:
            e["w0"] = 1.0
        desc = "All edges w0=1.0 (control)"

    elif topology_name == "SPIRIT_HIGHWAY":
        # Edges touching spirit nodes get w0=3.0, all others w0=1.0
        spirit_ids = {n["id"] for n in nodes if n.get("group") == "spirit"}
        for e in edges:
            if e["from"] in spirit_ids or e["to"] in spirit_ids:
                e["w0"] = 3.0
            else:
                e["w0"] = 1.0
        desc = f"Spirit-adjacent edges w0=3.0 ({len(spirit_ids)} spirit nodes)"

    elif topology_name == "INJECTION_HIGHWAY":
        # Edges between injection nodes and their immediate neighbors get w0=3.0
        inj_ids = {1, 2, 9, 23, 29}
        for e in edges:
            if e["from"] in inj_ids or e["to"] in inj_ids:
                e["w0"] = 3.0
            else:
                e["w0"] = 1.0
        desc = "Injection-node edges w0=3.0"

    elif topology_name == "HUB_WALL":
        # Mega-hub edges (par [79], johannine grove [82]) get w0=0.1
        # Everything else w0=1.0 — creates bottleneck at hubs
        hub_ids = {79, 82}
        for e in edges:
            if e["from"] in hub_ids or e["to"] in hub_ids:
                e["w0"] = 0.1
            else:
                e["w0"] = 1.0
        desc = "Hub edges (par, johannine grove) w0=0.1 (bottleneck)"

    elif topology_name == "GRADIENT":
        # Weight edges by distance from grail [1]: closer edges = higher w0
        # Build BFS distance from grail
        adj = defaultdict(set)
        for e in edges:
            adj[e["from"]].add(e["to"])
            adj[e["to"]].add(e["from"])

        dist = {1: 0}
        queue = [1]
        while queue:
            nxt = []
            for nid in queue:
                for nb in adj[nid]:
                    if nb not in dist:
                        dist[nb] = dist[nid] + 1
                        nxt.append(nb)
            queue = nxt

        max_dist = max(dist.values()) if dist else 1
        for e in edges:
            d_from = dist.get(e["from"], max_dist)
            d_to = dist.get(e["to"], max_dist)
            avg_d = (d_from + d_to) / 2.0
            # Close to grail = w0=3.0, far = w0=0.3
            e["w0"] = 3.0 - (2.7 * avg_d / max_dist)
        desc = "Distance gradient from grail: close=3.0, far=0.3"

    elif topology_name == "COLD_SUPERHIGHWAY":
        # Wire cold nodes to each other with w0=3.0
        # (Cold nodes from original survey: we'll identify them here)
        # Use high w0 on ALL edges touching cold nodes
        # First identify cold nodes via quick survey
        cold_ids = set()
        for nid in [n["id"] for n in nodes]:
            eng = SOLEngine.from_graph(
                copy.deepcopy(nodes), copy.deepcopy(edges),
                dt=DT, c_press=C_PRESS, damping=0.2, rng_seed=42
            )
            eng.inject_by_id(nid, 50.0)
            basin_v = defaultdict(int)
            for s in range(1, 301):
                eng.step()
                if s % 50 == 0:
                    m = eng.compute_metrics()
                    bid = m["rhoMaxId"]
                    if bid is not None:
                        basin_v[bid] = basin_v.get(bid, 0) + 1
            dom = max(basin_v, key=basin_v.get) if basin_v else None
            if dom != nid:
                cold_ids.add(nid)

        for e in edges:
            if e["from"] in cold_ids or e["to"] in cold_ids:
                e["w0"] = 3.0
            else:
                e["w0"] = 1.0
        desc = f"Cold-node edges w0=3.0 ({len(cold_ids)} cold nodes identified)"

    return nodes, edges, desc


def test_b_weighted_conductance():
    """Test whether edge weight programming can steer basin formation."""
    print("\n" + "=" * 70)
    print("  TEST B - WEIGHTED CONDUCTANCE CHANNELS")
    print("  6 weight topologies x 4 damping x 2 injection patterns = 48 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)

    weight_topologies = [
        "UNIFORM", "SPIRIT_HIGHWAY", "INJECTION_HIGHWAY",
        "HUB_WALL", "GRADIENT", "COLD_SUPERHIGHWAY",
    ]

    injection_patterns = {
        "STANDARD": STANDARD_INJECTIONS,
        "REVERSED": [  # Reverse the energy hierarchy
            ("grail", 20.0),
            ("metatron", 25.0),
            ("pyramid", 30.0),
            ("christ", 35.0),
            ("light codes", 40.0),
        ],
    }

    results = {}
    t0 = time.time()
    trial_count = 0

    for wt_name in weight_topologies:
        print(f"\n  Weight topology: {wt_name}")
        wt_nodes, wt_edges, wt_desc = make_weighted_graph(
            raw_nodes, raw_edges, wt_name, labels, groups
        )
        print(f"    {wt_desc}")

        wt_results = {"description": wt_desc, "trials": []}

        for inj_name, inj_pattern in injection_patterns.items():
            for damp in WEIGHT_DAMPS:
                engine = make_engine(wt_nodes, wt_edges, damping=damp)
                for label, amount in inj_pattern:
                    engine.inject(label, amount)

                analysis = run_and_analyze(engine, steps=STEPS)

                basin_lbl = labels.get(analysis["dominant_basin"], "?")
                print(f"    d={damp:5.1f} inj={inj_name:<10} "
                      f"modes={analysis['n_modes']:3d} "
                      f"coh={analysis['coherence']:.3f} "
                      f"iton={analysis['iton_score']:.3f} "
                      f"cond_u={analysis['conductance_mean']:.3f} "
                      f"basin=[{analysis['dominant_basin']}] {basin_lbl}")

                trial_data = {
                    "weight_topology": wt_name,
                    "injection_pattern": inj_name,
                    "damping": damp,
                    "dominant_basin": analysis["dominant_basin"],
                    "basin_label": basin_lbl,
                    "n_modes": analysis["n_modes"],
                    "coherence": analysis["coherence"],
                    "iton_score": analysis["iton_score"],
                    "n_pass": analysis["n_pass"],
                    "n_directional": analysis["n_directional"],
                    "conductance_mean": analysis["conductance_mean"],
                    "conductance_std": analysis["conductance_std"],
                    "conductance_max": analysis["conductance_max"],
                    "final_maxrho": analysis["final_maxrho"],
                    "final_entropy": analysis["final_entropy"],
                }
                wt_results["trials"].append(trial_data)
                trial_count += 1

        results[wt_name] = wt_results

    total_time = time.time() - t0

    # Cross-topology comparison
    print(f"\n  CROSS-TOPOLOGY COMPARISON:")
    print(f"\n    Basin steering effect (d=0.2, STANDARD injection):")
    for wt_name in weight_topologies:
        for trial in results[wt_name]["trials"]:
            if trial["damping"] == 0.2 and trial["injection_pattern"] == "STANDARD":
                print(f"      {wt_name:<22} basin=[{trial['dominant_basin']}] "
                      f"{trial['basin_label']:<20} "
                      f"iton={trial['iton_score']:.3f} "
                      f"cond_u={trial['conductance_mean']:.3f}")

    print(f"\n    Injection reversal effect (STANDARD vs REVERSED at d=0.2):")
    for wt_name in weight_topologies:
        std_basin = rev_basin = None
        for trial in results[wt_name]["trials"]:
            if trial["damping"] == 0.2:
                if trial["injection_pattern"] == "STANDARD":
                    std_basin = trial["basin_label"]
                elif trial["injection_pattern"] == "REVERSED":
                    rev_basin = trial["basin_label"]
        changed = "CHANGED" if std_basin != rev_basin else "same"
        print(f"      {wt_name:<22} std>{std_basin:<15} rev>{rev_basin:<15} {changed}")

    print(f"\n  Total: {trial_count} trials in {total_time:.1f}s")

    return {
        "runtime_sec": round(total_time, 2),
        "trials": trial_count,
        "results": {k: v for k, v in results.items()},
    }


# ===================================================================
# TEST C — Injection Protocol Variation
# ===================================================================

def test_c_injection_protocols():
    """Test 6 injection protocols at 6 damping values.
    
    Protocols:
      STANDARD    — grail(40), metatron(35), pyramid(30), christ(25), light_codes(20)
      REVERSED    — Flip the energy hierarchy
      SEQUENTIAL  — Inject one at a time with 100 steps between each
      SINGLE_MAX  — All 150 units into grail only
      COLD_INJECT — Inject 5 cold nodes instead of the standard 5
      SPREAD      — 1.07 units each into all 140 nodes (same total energy)
    """
    print("\n" + "=" * 70)
    print("  TEST C - INJECTION PROTOCOL VARIATION")
    print("  6 protocols x 6 damping values = 36 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    total_standard_energy = sum(a for _, a in STANDARD_INJECTIONS)  # 150.0

    # Identify 5 cold nodes to use for COLD_INJECT
    # Pick diverse cold nodes (different degrees/groups)
    # From original survey: cold nodes exist. Let's pick them dynamically.
    print("  Identifying cold nodes for COLD_INJECT protocol...")
    cold_candidates = []
    for nid in sorted(labels.keys()):
        eng = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=0.2, rng_seed=42)
        eng.inject_by_id(nid, 50.0)
        bv = defaultdict(int)
        for s in range(1, 301):
            eng.step()
            if s % 50 == 0:
                m = eng.compute_metrics()
                bid = m["rhoMaxId"]
                if bid is not None:
                    bv[bid] = bv.get(bid, 0) + 1
        dom = max(bv, key=bv.get) if bv else None
        if dom != nid:
            cold_candidates.append(nid)

    # Pick 5 cold nodes with diverse groups
    cold_5 = cold_candidates[:5]
    cold_labels = [labels.get(nid, "?") for nid in cold_5]
    print(f"  Selected cold nodes: {list(zip(cold_5, cold_labels))}")

    results = {}
    t0 = time.time()
    trial_count = 0

    for damp in INJECT_DAMPS:
        print(f"\n  Damping d={damp}:")
        damp_results = {}

        # --- STANDARD ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)
        analysis = run_and_analyze(engine, steps=STEPS)
        damp_results["STANDARD"] = analysis
        trial_count += 1

        # --- REVERSED ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        for label, amount in [("grail", 20.0), ("metatron", 25.0), ("pyramid", 30.0),
                              ("christ", 35.0), ("light codes", 40.0)]:
            engine.inject(label, amount)
        analysis = run_and_analyze(engine, steps=STEPS)
        damp_results["REVERSED"] = analysis
        trial_count += 1

        # --- SEQUENTIAL (inject one at a time with 100-step gaps) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        rho_samples = []
        basin_visits = defaultdict(int)
        for i, (label, amount) in enumerate(STANDARD_INJECTIONS):
            engine.inject(label, amount)
            for s in range(100):
                engine.step()
                if (i * 100 + s) % SAMPLE_INTERVAL == 0:
                    m = engine.compute_metrics()
                    bid = m["rhoMaxId"]
                    if bid is not None:
                        basin_visits[bid] = basin_visits.get(bid, 0) + 1
                    rho_samples.append([n["rho"] for n in engine.physics.nodes])
        seq_analysis = analyze_trial(engine, rho_samples)
        seq_analysis["dominant_basin"] = max(basin_visits, key=basin_visits.get) if basin_visits else None
        final = engine.compute_metrics()
        seq_analysis["final_maxrho"] = final["maxRho"]
        seq_analysis["final_entropy"] = final["entropy"]
        seq_analysis["final_mass"] = final["mass"]
        seq_analysis["basin_visits"] = dict(basin_visits)
        damp_results["SEQUENTIAL"] = seq_analysis
        trial_count += 1

        # --- SINGLE_MAX (all 150 into grail) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        engine.inject("grail", total_standard_energy)
        analysis = run_and_analyze(engine, steps=STEPS)
        damp_results["SINGLE_MAX"] = analysis
        trial_count += 1

        # --- COLD_INJECT (inject 5 cold nodes) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        per_cold = total_standard_energy / 5.0  # 30 each
        for nid in cold_5:
            engine.inject_by_id(nid, per_cold)
        analysis = run_and_analyze(engine, steps=STEPS)
        damp_results["COLD_INJECT"] = analysis
        trial_count += 1

        # --- SPREAD (uniform across all 140 nodes) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        per_node = total_standard_energy / 140.0  # ~1.07 each
        for nid in sorted(labels.keys()):
            engine.inject_by_id(nid, per_node)
        analysis = run_and_analyze(engine, steps=STEPS)
        damp_results["SPREAD"] = analysis
        trial_count += 1

        # Print summary
        for proto_name in ["STANDARD", "REVERSED", "SEQUENTIAL", "SINGLE_MAX",
                           "COLD_INJECT", "SPREAD"]:
            r = damp_results[proto_name]
            basin_lbl = labels.get(r["dominant_basin"], "?")
            print(f"    {proto_name:<14} modes={r['n_modes']:3d} "
                  f"coh={r['coherence']:.3f} "
                  f"iton={r['iton_score']:.3f} "
                  f"basin=[{r['dominant_basin']}] {basin_lbl}")

        results[str(damp)] = {
            proto: {k: v for k, v in r.items()
                    if k not in ("active_mode_ids", "node_rho_final_top10")}
            for proto, r in damp_results.items()
        }

    total_time = time.time() - t0

    # Cross-protocol comparison
    print(f"\n  CROSS-PROTOCOL COMPARISON:")

    # Basin divergence: which protocols produce DIFFERENT basins at each damping?
    print(f"\n    Basin divergence by damping:")
    for damp in INJECT_DAMPS:
        basins = {}
        for proto in ["STANDARD", "REVERSED", "SEQUENTIAL", "SINGLE_MAX",
                       "COLD_INJECT", "SPREAD"]:
            r = results[str(damp)][proto]
            b = r["dominant_basin"]
            basins[proto] = labels.get(b, "?") if b else "None"
        unique = len(set(basins.values()))
        print(f"    d={damp:5.1f}: {unique} distinct basins -- ", end="")
        for proto, lbl in basins.items():
            print(f"{proto[:4]}>{lbl} ", end="")
        print()

    # Mode count sensitivity
    print(f"\n    Mode count sensitivity (non-STANDARD protocols vs STANDARD):")
    for damp in INJECT_DAMPS:
        std_modes = results[str(damp)]["STANDARD"]["n_modes"]
        diffs = {}
        for proto in ["REVERSED", "SEQUENTIAL", "SINGLE_MAX", "COLD_INJECT", "SPREAD"]:
            m = results[str(damp)][proto]["n_modes"]
            diffs[proto] = m - std_modes
        print(f"    d={damp:5.1f}: std={std_modes:3d}  ", end="")
        for proto, d in diffs.items():
            print(f"{proto[:4]}={d:+d} ", end="")
        print()

    # Coherence comparison
    print(f"\n    Coherence comparison:")
    for damp in INJECT_DAMPS:
        print(f"    d={damp:5.1f}: ", end="")
        for proto in ["STANDARD", "REVERSED", "SEQUENTIAL", "SINGLE_MAX",
                       "COLD_INJECT", "SPREAD"]:
            c = results[str(damp)][proto]["coherence"]
            print(f"{proto[:4]}={c:.3f} ", end="")
        print()

    # Iton transport
    print(f"\n    Iton score comparison:")
    for damp in INJECT_DAMPS:
        print(f"    d={damp:5.1f}: ", end="")
        for proto in ["STANDARD", "REVERSED", "SEQUENTIAL", "SINGLE_MAX",
                       "COLD_INJECT", "SPREAD"]:
            it = results[str(damp)][proto]["iton_score"]
            print(f"{proto[:4]}={it:.3f} ", end="")
        print()

    print(f"\n  Total: {trial_count} trials in {total_time:.1f}s")

    return {
        "runtime_sec": round(total_time, 2),
        "trials": trial_count,
        "cold_nodes_used": cold_5,
        "cold_labels": cold_labels,
        "total_energy": total_standard_energy,
        "results": results,
    }


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  SOL LATTICE STRESS TEST")
    print("  Three-Vector Combined Experiment")
    print("  ~768 trials | Hunting emergent computation")
    print("=" * 70)

    t_start = time.time()

    result_a = test_a_cold_node_mapping()
    result_b = test_b_weighted_conductance()
    result_c = test_c_injection_protocols()

    total_time = time.time() - t_start

    # ===================================================================
    # SYNTHESIS
    # ===================================================================
    print(f"\n{'=' * 70}")
    print(f"  SYNTHESIS - EMERGENT PHENOMENA SCAN")
    print(f"{'=' * 70}")

    # 1. Cold node identity stability
    n_invariant = len(result_a["invariant_cold"])
    n_stress_act = len(result_a["stress_activated"])
    n_stress_kill = len(result_a["stress_killed"])
    print(f"\n  Cold-Node Dynamics:")
    print(f"    Invariant cold nodes: {n_invariant}")
    print(f"    Stress-activated: {n_stress_act} (cold>hot under damping)")
    print(f"    Stress-killed: {n_stress_kill} (hot>cold under damping)")

    if n_stress_act > 0:
        print(f"    ** EMERGENT: {n_stress_act} nodes change computational role under stress")
    if n_stress_kill > 0:
        print(f"    ** EMERGENT: {n_stress_kill} nodes lose self-attraction under stress")

    # 2. Weight-steerable basins
    uniform_basins = set()
    steered_basins = {}
    for wt_name, wr in result_b["results"].items():
        for trial in wr["trials"]:
            if trial["damping"] == 0.2 and trial["injection_pattern"] == "STANDARD":
                if wt_name == "UNIFORM":
                    uniform_basins.add(trial["dominant_basin"])
                else:
                    steered_basins[wt_name] = trial["dominant_basin"]

    n_steered = sum(1 for b in steered_basins.values()
                    if b not in uniform_basins)
    print(f"\n  Conductance Programming:")
    print(f"    Uniform control basin(s): {uniform_basins}")
    print(f"    Weight topologies that CHANGED the basin: {n_steered}/{len(steered_basins)}")
    if n_steered > 0:
        print(f"    ** EMERGENT: Basin is programmable via edge weights -- "
              f"this is addressable routing!")

    # 3. Injection protocol effects
    print(f"\n  Injection Protocol Effects:")
    for damp in INJECT_DAMPS:
        std_b = result_c["results"][str(damp)]["STANDARD"]["dominant_basin"]
        diff_protos = []
        for proto in ["REVERSED", "SEQUENTIAL", "SINGLE_MAX", "COLD_INJECT", "SPREAD"]:
            p_b = result_c["results"][str(damp)][proto]["dominant_basin"]
            if p_b != std_b:
                diff_protos.append(proto)
        if diff_protos:
            print(f"    d={damp}: {len(diff_protos)} protocols produce different basins: "
                  f"{diff_protos}")
        else:
            print(f"    d={damp}: All protocols converge to same basin")

    # 4. Novel iton patterns
    best_iton = 0
    best_iton_config = ""
    for wt_name, wr in result_b["results"].items():
        for trial in wr["trials"]:
            if trial["iton_score"] > best_iton:
                best_iton = trial["iton_score"]
                best_iton_config = (f"{wt_name} / {trial['injection_pattern']} "
                                    f"/ d={trial['damping']}")
    print(f"\n  Peak Iton Transport:")
    print(f"    Best iton score: {best_iton:.3f} at {best_iton_config}")

    for damp_str, damp_data in result_c["results"].items():
        for proto, r in damp_data.items():
            if r["iton_score"] > best_iton:
                best_iton = r["iton_score"]
                best_iton_config = f"{proto} / d={damp_str}"
    print(f"    Overall best: {best_iton:.3f} at {best_iton_config}")

    print(f"\n  Total runtime: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Total trials: "
          f"{result_a['trials'] + result_b['trials'] + result_c['trials']}")

    # Save
    out_path = _SOL_ROOT / "data" / "lattice_stress_test.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_sec": round(total_time, 2),
        "total_trials": result_a["trials"] + result_b["trials"] + result_c["trials"],
        "test_a_cold_node_mapping": result_a,
        "test_b_weighted_conductance": result_b,
        "test_c_injection_protocols": result_c,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()
