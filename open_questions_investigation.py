#!/usr/bin/env python3
"""
SOL Open-Questions Investigation
=================================

10 targeted probes answering every open question from the proof packet.

  Probe 1  (Q1)  Coherence Resurrection — fine sweep d=77.5..79.0, step 0.025
  Probe 2  (Q2)  Mode Pre-Collapse Anatomy — identify the 9 modes that die at d=83.30
  Probe 3  (Q3)  Iton Pathway Selection — per-edge flux from metatron at d=0.2
  Probe 4  (Q4)  COLD_WIRE Relay Chain — add orion->metatron, track new relay nodes
  Probe 5  (Q5)  Phase Coupling Hierarchy — PLV for hub pairs across damping
  Probe 6  (Q6)  SPIRIT_HIGHWAY Basin Steering — structural analysis of spirit edges
  Probe 7  (Q7)  SPREAD Coherence Invariance — systematic symmetry-breaking tests
  Probe 8  (Q8)  SEQUENTIAL Iton Persistence — wavefront hypothesis test
  Probe 9  (Q9)  COLD_INJECT Novel Basins — BFS reachability + individual cold tests
  Probe 10 (Q10) Self-Attractor Phase Transition — fine sweep d=5..35

Estimated: ~450 trials, ~15-20 min
Outputs: data/open_questions_investigation.json
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

from sol_engine import SOLEngine, SOLPhysics, compute_metrics, create_engine

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

INJECTION_IDS = [1, 2, 9, 23, 29]  # grail, christ, metatron, light_codes, pyramid


# ---------------------------------------------------------------------------
# Shared utilities
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


def build_adjacency(raw_edges):
    adj = defaultdict(set)
    for e in raw_edges:
        adj[e["from"]].add(e["to"])
        adj[e["to"]].add(e["from"])
    return dict(adj)


def bfs_distances(adj, start_id):
    dist = {start_id: 0}
    queue = [start_id]
    while queue:
        nxt = []
        for nid in queue:
            for nb in adj.get(nid, []):
                if nb not in dist:
                    dist[nb] = dist[nid] + 1
                    nxt.append(nb)
        queue = nxt
    return dist


# ===================================================================
# PROBE 1 (Q1): Coherence Resurrection at d~78.2
# ===================================================================

def probe_1_coherence_resurrection():
    """Fine sweep d=77.5..79.0 step 0.025 -- map the phase snap."""
    print("\n" + "=" * 70)
    print("  PROBE 1 (Q1): COHERENCE RESURRECTION MECHANISM")
    print("  Fine sweep d=77.50 to 79.00, step 0.025 = 61 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    id_to_idx = {}

    damp_values = [round(77.5 + i * 0.025, 3) for i in range(61)]
    results = []
    t0 = time.time()

    for damp in damp_values:
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)

        if not id_to_idx:
            id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}

        rho_samples = []
        psi_samples = []
        basin_visits = defaultdict(int)

        for s in range(1, STEPS + 1):
            engine.step()
            if s % SAMPLE_INTERVAL == 0:
                m = engine.compute_metrics()
                bid = m["rhoMaxId"]
                if bid is not None:
                    basin_visits[bid] = basin_visits.get(bid, 0) + 1
                rho_samples.append([n["rho"] for n in engine.physics.nodes])
                psi_samples.append([n["psi"] for n in engine.physics.nodes])

        # Coherence (injection-node correlations)
        rho_arr = np.array(rho_samples)
        inj_indices = [id_to_idx[nid] for nid in INJECTION_IDS if nid in id_to_idx]
        corrs = []
        for a in range(len(inj_indices)):
            for b in range(a + 1, len(inj_indices)):
                t1 = rho_arr[:, inj_indices[a]]
                t2 = rho_arr[:, inj_indices[b]]
                r1 = np.ptp(t1)
                r2 = np.ptp(t2)
                if r1 > 0 and r2 > 0:
                    t1n = (t1 - np.mean(t1)) / r1
                    t2n = (t2 - np.mean(t2)) / r2
                    c = np.corrcoef(t1n, t2n)[0, 1]
                    if not np.isnan(c):
                        corrs.append(abs(c))
        coherence = float(np.mean(corrs)) if corrs else 0.0

        # Psi analysis: mean psi of injection nodes (belief field state)
        psi_arr = np.array(psi_samples)
        inj_psi_mean = float(np.mean(psi_arr[-1, inj_indices]))
        inj_psi_std = float(np.std(psi_arr[-1, inj_indices]))

        # Conductance of injection-node edges
        inj_ids_set = set(INJECTION_IDS)
        inj_conds = []
        for e in engine.physics.edges:
            if e["from"] in inj_ids_set or e["to"] in inj_ids_set:
                inj_conds.append(e["conductance"])
        inj_cond_mean = float(np.mean(inj_conds)) if inj_conds else 0.0

        dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
        final = engine.compute_metrics()

        # Mode count
        osc_amps = []
        for j in range(len(engine.physics.nodes)):
            trace = rho_arr[:, j]
            if np.max(trace) > 1e-15:
                osc_amps.append(float(np.std(trace) / max(np.mean(trace), 1e-15)))
            else:
                osc_amps.append(0.0)
        n_modes = int(np.sum(np.array(osc_amps) > 0.01))

        print(f"  d={damp:7.3f}  coh={coherence:.4f}  modes={n_modes:3d}  "
              f"psi_mean={inj_psi_mean:+.4f}  cond={inj_cond_mean:.4f}  "
              f"basin=[{dominant}] {labels.get(dominant, '?')}")

        results.append({
            "damping": damp,
            "coherence": coherence,
            "n_modes": n_modes,
            "dominant_basin": dominant,
            "basin_label": labels.get(dominant, "?"),
            "maxRho": final["maxRho"],
            "inj_psi_mean": inj_psi_mean,
            "inj_psi_std": inj_psi_std,
            "inj_cond_mean": inj_cond_mean,
        })

    elapsed = time.time() - t0

    # Find the steepest coherence gradient
    max_grad = 0.0
    max_grad_d = 0.0
    for i in range(1, len(results)):
        grad = abs(results[i]["coherence"] - results[i-1]["coherence"])
        if grad > max_grad:
            max_grad = grad
            max_grad_d = results[i]["damping"]

    # Find basin transition point
    basin_transition_d = None
    for i in range(1, len(results)):
        if results[i]["dominant_basin"] != results[i-1]["dominant_basin"]:
            basin_transition_d = results[i]["damping"]

    print(f"\n  ANSWER Q1:")
    print(f"    Max coherence gradient: {max_grad:.4f} at d={max_grad_d:.3f}")
    print(f"    Basin transition: d={basin_transition_d}")
    print(f"    Coherence snap width determined at 0.025 resolution")

    # Does psi change precede coherence snap?
    pre_snap = [r for r in results if r["damping"] < max_grad_d]
    post_snap = [r for r in results if r["damping"] >= max_grad_d]
    if pre_snap and post_snap:
        psi_before = pre_snap[-1]["inj_psi_mean"]
        psi_after = post_snap[0]["inj_psi_mean"]
        cond_before = pre_snap[-1]["inj_cond_mean"]
        cond_after = post_snap[0]["inj_cond_mean"]
        print(f"    Psi before snap: {psi_before:+.4f}, after: {psi_after:+.4f}")
        print(f"    Conductance before: {cond_before:.4f}, after: {cond_after:.4f}")

    print(f"  [{elapsed:.1f}s, {len(results)} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": len(results),
        "results": results,
        "max_coherence_gradient": max_grad,
        "max_gradient_damping": max_grad_d,
        "basin_transition_damping": basin_transition_d,
    }


# ===================================================================
# PROBE 2 (Q2): Mode Pre-Collapse Anatomy
# ===================================================================

def probe_2_mode_precollapse():
    """Identify which 9 modes die at d=83.30 and what makes them special."""
    print("\n" + "=" * 70)
    print("  PROBE 2 (Q2): MODE PRE-COLLAPSE ANATOMY")
    print("  Fine sweep d=83.20..83.40, step 0.01 = 21 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)

    damp_values = [round(83.20 + i * 0.01, 2) for i in range(21)]
    results = []
    mode_sets_by_damp = {}
    t0 = time.time()

    for damp in damp_values:
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)

        rho_samples = []
        for s in range(1, STEPS + 1):
            engine.step()
            if s % SAMPLE_INTERVAL == 0:
                rho_samples.append([n["rho"] for n in engine.physics.nodes])

        rho_arr = np.array(rho_samples)
        active_modes = []
        for j in range(len(engine.physics.nodes)):
            trace = rho_arr[:, j]
            if np.max(trace) > 1e-15:
                cov = float(np.std(trace) / max(np.mean(trace), 1e-15))
            else:
                cov = 0.0
            if cov > 0.01:
                nid = engine.physics.nodes[j]["id"]
                active_modes.append(nid)

        mode_sets_by_damp[damp] = set(active_modes)
        final = engine.compute_metrics()

        print(f"  d={damp:.2f}  modes={len(active_modes):3d}  "
              f"maxRho={final['maxRho']:.2e}  "
              f"basin=[{final['rhoMaxId']}] {labels.get(final['rhoMaxId'], '?')}")

        results.append({
            "damping": damp,
            "n_modes": len(active_modes),
            "active_mode_ids": sorted(active_modes),
            "maxRho": final["maxRho"],
        })

    elapsed = time.time() - t0

    # Find the transition points
    print(f"\n  MODE DEATH ANALYSIS:")
    prev_set = None
    for damp in damp_values:
        cur_set = mode_sets_by_damp[damp]
        if prev_set is not None and len(cur_set) < len(prev_set):
            died = prev_set - cur_set
            print(f"\n  At d={damp:.2f}: {len(died)} modes died")
            for nid in sorted(died):
                print(f"    [{nid:3d}] {labels.get(nid, '?'):<30} "
                      f"group={groups.get(nid, '?'):<8} degree={degrees.get(nid, 0)}")

            # Structural analysis of dead modes
            dead_degrees = [degrees.get(nid, 0) for nid in died]
            dead_groups = [groups.get(nid, "?") for nid in died]
            surviving = cur_set
            surv_degrees = [degrees.get(nid, 0) for nid in surviving]

            print(f"    Dead mode avg degree: {np.mean(dead_degrees):.1f}")
            print(f"    Surviving mode avg degree: {np.mean(surv_degrees):.1f}")
            print(f"    Dead mode groups: {dict(zip(*np.unique(dead_groups, return_counts=True)))}")
        prev_set = cur_set

    # What's special about the 9 modes?
    # Find d where 9 die
    for i in range(1, len(results)):
        delta = results[i-1]["n_modes"] - results[i]["n_modes"]
        if 5 <= delta <= 15:  # near the 9-mode death
            d_before = results[i-1]["damping"]
            d_after = results[i]["damping"]
            alive_before = mode_sets_by_damp[d_before]
            alive_after = mode_sets_by_damp[d_after]
            died = alive_before - alive_after

            # Check if these modes share neighbors
            adj = build_adjacency(raw_edges)
            dead_list = sorted(died)
            shared_neighbors = set()
            for nid in dead_list:
                shared_neighbors.update(adj.get(nid, set()))
            unique_to_dead = shared_neighbors - alive_after

            print(f"\n  STRUCTURAL ANALYSIS of {len(died)}-mode death at d={d_after:.2f}:")
            print(f"    Dead mode IDs: {dead_list}")
            print(f"    Dead modes share {len(shared_neighbors)} total neighbor connections")
            print(f"    {len(unique_to_dead)} neighbors unique to dead modes (not in survivors)")

            # Are the dead modes connected to each other?
            internal_edges = 0
            for nid in dead_list:
                for nb in adj.get(nid, set()):
                    if nb in died:
                        internal_edges += 1
            internal_edges //= 2
            print(f"    Internal edges among dead modes: {internal_edges}")

            # Distance from injection nodes
            for inj_id in INJECTION_IDS:
                dists = bfs_distances(adj, inj_id)
                dead_dists = [dists.get(nid, 999) for nid in dead_list]
                surv_dists = [dists.get(nid, 999) for nid in alive_after if nid in dists]
                print(f"    Avg BFS dist from [{inj_id}] {labels.get(inj_id, '?')}: "
                      f"dead={np.mean(dead_dists):.2f} vs surv={np.mean(surv_dists):.2f}")

    print(f"\n  [{elapsed:.1f}s, {len(results)} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": len(results),
        "results": results,
        "mode_sets": {str(d): sorted(s) for d, s in mode_sets_by_damp.items()},
    }


# ===================================================================
# PROBE 3 (Q3): Iton Pathway Selection from Metatron
# ===================================================================

def probe_3_iton_pathway():
    """Track per-edge flux from metatron at d=0.2 to understand routing."""
    print("\n" + "=" * 70)
    print("  PROBE 3 (Q3): ITON PATHWAY SELECTION FROM METATRON")
    print("  1 deep-instrumented trial at d=0.2")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    degrees = get_degrees(raw_edges)
    groups = get_groups(raw_nodes)

    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=0.2, rng_seed=42)
    apply_standard_injection(engine)

    t0 = time.time()
    metatron_id = 9

    # Run 500 steps
    for s in range(1, STEPS + 1):
        engine.step()

    # Analyze edges from metatron
    metatron_edges = []
    for e in engine.physics.edges:
        if e["from"] == metatron_id or e["to"] == metatron_id:
            other_id = e["to"] if e["from"] == metatron_id else e["from"]
            other_node = engine.physics.node_by_id.get(other_id)
            flux = e.get("flux", 0.0)
            cond = e.get("conductance", 1.0)
            w0 = e.get("w0", 1.0)
            is_outflow = (flux > 0) if e["from"] == metatron_id else (flux < 0)
            metatron_edges.append({
                "other_id": other_id,
                "other_label": labels.get(other_id, "?"),
                "other_degree": degrees.get(other_id, 0),
                "other_group": groups.get(other_id, "?"),
                "other_rho": other_node["rho"] if other_node else 0.0,
                "other_psi": other_node["psi"] if other_node else 0.0,
                "flux": flux,
                "abs_flux": abs(flux),
                "conductance": cond,
                "w0": w0,
                "is_outflow": is_outflow,
            })

    # Sort by absolute flux
    metatron_edges.sort(key=lambda x: x["abs_flux"], reverse=True)

    print(f"\n  Metatron [{metatron_id}] edge analysis (degree={degrees.get(metatron_id, 0)}):")
    print(f"  {'Neighbor':<28} {'Deg':>4} {'Group':<8} {'Flux':>10} {'Dir':>4} "
          f"{'Cond':>7} {'Rho':>10} {'Psi':>6}")
    print(f"  {'-'*28} {'-'*4} {'-'*8} {'-'*10} {'-'*4} {'-'*7} {'-'*10} {'-'*6}")

    for e in metatron_edges:
        direction = "OUT" if e["is_outflow"] else "IN"
        print(f"  {e['other_label']:<28} {e['other_degree']:4d} {e['other_group']:<8} "
              f"{e['flux']:+10.6f} {direction:>4} {e['conductance']:7.4f} "
              f"{e['other_rho']:10.4f} {e['other_psi']:+6.3f}")

    # Analyze: is flux proportional to degree or to conductance?
    outflows = [e for e in metatron_edges if e["is_outflow"]]
    if len(outflows) >= 2:
        flux_vals = [e["abs_flux"] for e in outflows]
        deg_vals = [e["other_degree"] for e in outflows]
        cond_vals = [e["conductance"] for e in outflows]
        psi_vals = [e["other_psi"] for e in outflows]
        rho_vals = [e["other_rho"] for e in outflows]

        corr_deg = float(np.corrcoef(flux_vals, deg_vals)[0, 1]) if len(outflows) > 2 else 0.0
        corr_cond = float(np.corrcoef(flux_vals, cond_vals)[0, 1]) if len(outflows) > 2 else 0.0
        corr_psi = float(np.corrcoef(flux_vals, psi_vals)[0, 1]) if len(outflows) > 2 else 0.0
        corr_rho = float(np.corrcoef(flux_vals, rho_vals)[0, 1]) if len(outflows) > 2 else 0.0

        print(f"\n  OUTFLOW CORRELATIONS ({len(outflows)} outflow edges):")
        print(f"    flux vs degree:      r = {corr_deg:+.4f}")
        print(f"    flux vs conductance: r = {corr_cond:+.4f}")
        print(f"    flux vs psi:         r = {corr_psi:+.4f}")
        print(f"    flux vs rho:         r = {corr_rho:+.4f}")

        # Flux is target_flux = conductance * tension * diode_gain * delta_p
        # delta_p = p_metatron - p_neighbor
        # So flux should correlate with (conductance * delta_p)
        metatron_p = engine.physics.node_by_id[metatron_id]["p"]
        delta_p_vals = [metatron_p - engine.physics.node_by_id.get(e["other_id"], {}).get("p", 0)
                        for e in outflows]
        cond_dp = [c * dp for c, dp in zip(cond_vals, delta_p_vals)]
        corr_theory = float(np.corrcoef(flux_vals, cond_dp)[0, 1]) if len(outflows) > 2 else 0.0
        print(f"    flux vs (cond * delta_p): r = {corr_theory:+.4f}  <-- theoretical predictor")

    # Top 3 flux recipients
    print(f"\n  TOP 3 FLUX RECIPIENTS from metatron:")
    for i, e in enumerate(outflows[:3]):
        print(f"    {i+1}. [{e['other_id']}] {e['other_label']} "
              f"(degree={e['other_degree']}, flux={e['abs_flux']:.6f})")

    elapsed = time.time() - t0
    print(f"\n  [{elapsed:.1f}s, 1 trial]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": 1,
        "metatron_edges": metatron_edges,
        "correlations": {
            "flux_vs_degree": corr_deg if len(outflows) > 2 else None,
            "flux_vs_conductance": corr_cond if len(outflows) > 2 else None,
            "flux_vs_psi": corr_psi if len(outflows) > 2 else None,
            "flux_vs_cond_delta_p": corr_theory if len(outflows) > 2 else None,
        },
    }


# ===================================================================
# PROBE 4 (Q4): COLD_WIRE Relay Chain Formation
# ===================================================================

def probe_4_cold_wire_relays():
    """Add orion->metatron edge, track which specific relay nodes appear."""
    print("\n" + "=" * 70)
    print("  PROBE 4 (Q4): COLD_WIRE RELAY CHAIN FORMATION")
    print("  2 conditions (control, cold_wire) x 2 damping = 4 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    degrees = get_degrees(raw_edges)
    groups = get_groups(raw_nodes)

    # Orion [11] -> Metatron [9]
    orion_id, metatron_id = 11, 9

    results = {}
    t0 = time.time()

    for damp in [0.2, 5.0]:
        for condition in ["CONTROL", "COLD_WIRE"]:
            edges = copy.deepcopy(raw_edges)
            nodes = copy.deepcopy(raw_nodes)
            if condition == "COLD_WIRE":
                edges.append({"from": orion_id, "to": metatron_id, "w0": 1.0, "kind": "none"})

            engine = make_engine(nodes, edges, damping=damp)
            apply_standard_injection(engine)

            # Track flux history per edge over last 100 steps
            for s in range(1, STEPS + 1):
                engine.step()

            # Analyze all nodes for relay behavior
            node_edges_map = defaultdict(list)
            for ei, e in enumerate(engine.physics.edges):
                node_edges_map[e["from"]].append((ei, "from"))
                node_edges_map[e["to"]].append((ei, "to"))

            relay_nodes = []
            source_nodes = []
            sink_nodes = []
            for n in engine.physics.nodes:
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

                total = inflow + outflow
                if total > 0.001:
                    balance = abs(inflow - outflow) / total
                    if balance < 0.3:
                        relay_nodes.append(nid)
                    elif inflow > outflow:
                        sink_nodes.append(nid)
                    else:
                        source_nodes.append(nid)

            iton_score = len(relay_nodes) / max(1, len(relay_nodes) + len(source_nodes) + len(sink_nodes))
            final = engine.compute_metrics()

            key = f"{condition}_d{damp}"
            results[key] = {
                "relay_nodes": sorted(relay_nodes),
                "source_nodes": sorted(source_nodes),
                "sink_nodes": sorted(sink_nodes),
                "n_relays": len(relay_nodes),
                "n_sources": len(source_nodes),
                "n_sinks": len(sink_nodes),
                "iton_score": iton_score,
                "maxRho": final["maxRho"],
            }

            print(f"\n  {condition} d={damp}: relays={len(relay_nodes)} "
                  f"sources={len(source_nodes)} sinks={len(sink_nodes)} "
                  f"iton={iton_score:.3f}")

    # Compare: which relay nodes are NEW in COLD_WIRE?
    for damp in [0.2, 5.0]:
        ctrl_relays = set(results[f"CONTROL_d{damp}"]["relay_nodes"])
        wire_relays = set(results[f"COLD_WIRE_d{damp}"]["relay_nodes"])
        new_relays = wire_relays - ctrl_relays
        lost_relays = ctrl_relays - wire_relays

        print(f"\n  d={damp} COLD_WIRE relay changes:")
        print(f"    NEW relays ({len(new_relays)}):")
        for nid in sorted(new_relays):
            print(f"      [{nid:3d}] {labels.get(nid, '?'):<25} "
                  f"deg={degrees.get(nid, 0)} group={groups.get(nid, '?')}")
        if lost_relays:
            print(f"    LOST relays ({len(lost_relays)}):")
            for nid in sorted(lost_relays):
                print(f"      [{nid:3d}] {labels.get(nid, '?'):<25} "
                      f"deg={degrees.get(nid, 0)}")

        # Are new relays on the path from orion to metatron?
        adj = build_adjacency(raw_edges)
        orion_dists = bfs_distances(adj, orion_id)
        met_dists = bfs_distances(adj, metatron_id)

        print(f"\n    New relay distances:")
        for nid in sorted(new_relays):
            d_orion = orion_dists.get(nid, 999)
            d_met = met_dists.get(nid, 999)
            print(f"      [{nid:3d}] {labels.get(nid, '?'):<25} "
                  f"dist_orion={d_orion} dist_metatron={d_met}")

        # Degree ratio analysis
        orion_deg = degrees.get(orion_id, 0)
        met_deg = degrees.get(metatron_id, 0)
        print(f"\n    Orion degree: {orion_deg}, Metatron degree: {met_deg}, "
              f"ratio: {orion_deg / max(1, met_deg):.3f}")

    elapsed = time.time() - t0
    print(f"\n  [{elapsed:.1f}s, 4 trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": 4,
        "results": results,
    }


# ===================================================================
# PROBE 5 (Q5): Phase Coupling Hierarchy
# ===================================================================

def probe_5_phase_coupling():
    """Compute PLV for hub pairs across damping range."""
    print("\n" + "=" * 70)
    print("  PROBE 5 (Q5): PHASE COUPLING HIERARCHY")
    print("  12 damping values, track PLV for key pairs")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    degrees = get_degrees(raw_edges)
    groups = get_groups(raw_nodes)
    adj = build_adjacency(raw_edges)

    # Key pairs to analyze
    pairs = [
        (79, 82, "par-johannine_grove"),
        (2, 9, "christ-metatron"),
        (1, 29, "grail-pyramid"),
        (1, 9, "grail-metatron"),
        (1, 2, "grail-christ"),
        (23, 29, "light_codes-pyramid"),
    ]

    damp_values = [0.2, 1.0, 3.0, 5.0, 10.0, 15.0, 20.0, 40.0, 55.0, 70.0, 79.5, 83.0]
    results = []
    t0 = time.time()

    for damp in damp_values:
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)

        id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}

        # Collect rho traces at every step for PLV
        rho_traces = {nid: [] for nid, _, _ in pairs for nid in [nid]}
        all_trace_ids = set()
        for a, b, _ in pairs:
            all_trace_ids.add(a)
            all_trace_ids.add(b)

        rho_per_step = []
        for s in range(1, 2001):  # 2000 steps for good PLV
            engine.step()
            row = [engine.physics.nodes[id_to_idx[nid]]["rho"]
                   for nid in sorted(all_trace_ids)]
            rho_per_step.append(row)

        rho_per_step = np.array(rho_per_step)
        sorted_ids = sorted(all_trace_ids)
        id_to_col = {nid: i for i, nid in enumerate(sorted_ids)}

        # Compute PLV via Hilbert transform
        from scipy.signal import hilbert

        pair_results = {}
        for a, b, name in pairs:
            trace_a = rho_per_step[:, id_to_col[a]]
            trace_b = rho_per_step[:, id_to_col[b]]

            # Detrend
            trace_a = trace_a - np.mean(trace_a)
            trace_b = trace_b - np.mean(trace_b)

            if np.std(trace_a) < 1e-20 or np.std(trace_b) < 1e-20:
                plv = 0.0
            else:
                analytic_a = hilbert(trace_a)
                analytic_b = hilbert(trace_b)
                phase_a = np.angle(analytic_a)
                phase_b = np.angle(analytic_b)
                delta_phase = phase_a - phase_b
                plv = float(np.abs(np.mean(np.exp(1j * delta_phase))))

            pair_results[name] = round(plv, 4)

        print(f"  d={damp:5.1f}  ", end="")
        for name in [p[2] for p in pairs]:
            print(f"{name}={pair_results[name]:.3f}  ", end="")
        print()

        results.append({
            "damping": damp,
            "plv": pair_results,
        })

    elapsed = time.time() - t0

    # Analysis
    print(f"\n  ANSWER Q5:")
    # At what damping does christ-metatron PLV reach 1.0?
    cm_onset = None
    pj_lowest = 1.0
    for r in results:
        cm = r["plv"]["christ-metatron"]
        pj = r["plv"]["par-johannine_grove"]
        if cm >= 0.99 and cm_onset is None:
            cm_onset = r["damping"]
        pj_lowest = min(pj_lowest, pj)

    print(f"    christ-metatron PLV>=0.99 onset: d={cm_onset}")
    print(f"    par-johannine_grove minimum PLV: {pj_lowest:.3f}")

    # Are they both same group?
    print(f"    christ group: {groups.get(2, '?')}, metatron group: {groups.get(9, '?')}")
    print(f"    par group: {groups.get(79, '?')}, johannine grove group: {groups.get(82, '?')}")

    # Are they directly connected?
    print(f"    christ-metatron direct edge: {9 in adj.get(2, set())}")
    print(f"    par-johannine_grove direct edge: {82 in adj.get(79, set())}")

    # BFS distance
    d_cm = bfs_distances(adj, 2).get(9, 999)
    d_pj = bfs_distances(adj, 79).get(82, 999)
    print(f"    christ-metatron BFS distance: {d_cm}")
    print(f"    par-johannine_grove BFS distance: {d_pj}")

    print(f"\n  [{elapsed:.1f}s, {len(results)} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": len(results),
        "results": results,
    }


# ===================================================================
# PROBE 6 (Q6): SPIRIT_HIGHWAY Basin Steering
# ===================================================================

def probe_6_spirit_highway():
    """Why spirit-edge weighting steers basin but others don't."""
    print("\n" + "=" * 70)
    print("  PROBE 6 (Q6): SPIRIT_HIGHWAY BASIN STEERING")
    print("  Structural analysis + targeted verification runs")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)
    adj = build_adjacency(raw_edges)

    # Count edges by group involvement
    spirit_ids = {n["id"] for n in raw_nodes if n.get("group") == "spirit"}
    tech_ids = {n["id"] for n in raw_nodes if n.get("group") == "tech"}
    bridge_ids = {n["id"] for n in raw_nodes if n.get("group", "bridge") == "bridge"}
    inj_ids = {1, 2, 9, 23, 29}
    hub_ids = {79, 82}

    spirit_edges = [e for e in raw_edges if e["from"] in spirit_ids or e["to"] in spirit_ids]
    inj_edges = [e for e in raw_edges if e["from"] in inj_ids or e["to"] in inj_ids]
    hub_edges = [e for e in raw_edges if e["from"] in hub_ids or e["to"] in hub_ids]

    print(f"\n  STRUCTURAL CENSUS:")
    print(f"    Spirit nodes: {len(spirit_ids)}")
    print(f"    Spirit-adjacent edges: {len(spirit_edges)} / {len(raw_edges)} "
          f"({100*len(spirit_edges)/len(raw_edges):.1f}%)")
    print(f"    Injection-node edges: {len(inj_edges)} / {len(raw_edges)} "
          f"({100*len(inj_edges)/len(raw_edges):.1f}%)")
    print(f"    Hub edges: {len(hub_edges)} / {len(raw_edges)} "
          f"({100*len(hub_edges)/len(raw_edges):.1f}%)")

    # Key insight: spirit nodes are phase-gated (active when phase < 0.2)
    # Heartbeat: cos(1.5t). phase < 0.2 means cos(1.5t) < 0.2
    # cos(x) < 0.2 happens for x in (acos(0.2), 2*pi - acos(0.2))
    # acos(0.2) ~ 1.369, so spirit active for ~74% of the heartbeat cycle
    acos_02 = math.acos(0.2)
    spirit_active_frac = (2 * math.pi - 2 * acos_02) / (2 * math.pi)
    tech_active_frac = (2 * acos_02 - 2 * math.acos(-0.2) + 2 * math.pi) / (2 * math.pi)
    # Actually: tech active when phase > -0.2, i.e. cos(1.5t) > -0.2
    # cos(x) > -0.2 for x in (0, acos(-0.2)) U (2*pi - acos(-0.2), 2*pi)
    acos_neg02 = math.acos(-0.2)
    tech_active_frac = (2 * acos_neg02) / (2 * math.pi)

    # Bridge always active = 100%
    overlap = spirit_active_frac + tech_active_frac - 1.0  # both active simultaneously

    print(f"\n  PHASE GATING ANALYSIS:")
    print(f"    Spirit active fraction: {spirit_active_frac:.3f} ({100*spirit_active_frac:.1f}%)")
    print(f"    Tech active fraction: {tech_active_frac:.3f} ({100*tech_active_frac:.1f}%)")
    print(f"    Bridge active fraction: 1.000 (100%)")
    print(f"    Spirit+Tech overlap: {overlap:.3f}")

    # Which injection nodes are spirit-type?
    print(f"\n  INJECTION NODE GROUPS:")
    for nid in sorted(inj_ids):
        g = groups.get(nid, "?")
        d = degrees.get(nid, 0)
        print(f"    [{nid:3d}] {labels.get(nid, '?'):<20} group={g}  degree={d}")

    # Spirit-adjacent injection nodes
    spirit_adj_inj = []
    for nid in inj_ids:
        spirit_neighbors = adj.get(nid, set()) & spirit_ids
        if spirit_neighbors:
            spirit_adj_inj.append((nid, spirit_neighbors))
    print(f"\n  Injection nodes with spirit neighbors: {len(spirit_adj_inj)}")
    for nid, snbs in spirit_adj_inj:
        print(f"    [{nid}] {labels.get(nid, '?')}: {len(snbs)} spirit neighbors")

    # Targeted verification: run other weighting schemes at w0=3.0
    # but this time weight ONLY bridge-bridge edges, ONLY tech-adjacent, etc.
    print(f"\n  TARGETED VERIFICATION RUNS:")
    topologies = {
        "SPIRIT_3x": lambda e: 3.0 if (e["from"] in spirit_ids or e["to"] in spirit_ids) else 1.0,
        "BRIDGE_ONLY_3x": lambda e: 3.0 if (e["from"] in bridge_ids and e["to"] in bridge_ids) else 1.0,
        "SPIRIT_CONNECTED_TO_INJ_3x": lambda e: 3.0 if (
            (e["from"] in spirit_ids and e["to"] in inj_ids) or
            (e["to"] in spirit_ids and e["from"] in inj_ids)) else 1.0,
        "NON_SPIRIT_3x": lambda e: 3.0 if (e["from"] not in spirit_ids and e["to"] not in spirit_ids) else 1.0,
    }

    t0 = time.time()
    trial_count = 0

    for topo_name, w0_fn in topologies.items():
        nodes = copy.deepcopy(raw_nodes)
        edges = copy.deepcopy(raw_edges)
        n_modified = 0
        for e in edges:
            new_w0 = w0_fn(e)
            if new_w0 != 1.0:
                n_modified += 1
            e["w0"] = new_w0

        engine = make_engine(nodes, edges, damping=0.2)
        apply_standard_injection(engine)

        basin_visits = defaultdict(int)
        for s in range(1, STEPS + 1):
            engine.step()
            if s % 50 == 0:
                m = engine.compute_metrics()
                bid = m["rhoMaxId"]
                if bid is not None:
                    basin_visits[bid] = basin_visits.get(bid, 0) + 1

        dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
        print(f"    {topo_name:<30} edges_mod={n_modified:3d}  "
              f"basin=[{dominant}] {labels.get(dominant, '?')}")
        trial_count += 1

    # Why does spirit highway steer? Hypothesis: spirit nodes are on SHORT PATHS
    # between injection nodes and grail. When spirit edges are amplified,
    # flux preferentially flows through spirit-adjacent paths.
    print(f"\n  PATH ANALYSIS:")
    for inj_id in sorted(inj_ids):
        if inj_id == 1:
            continue  # grail is the target basin
        # BFS from injection node - how many hops through spirit vs non-spirit?
        dists = bfs_distances(adj, inj_id)
        d_to_grail = dists.get(1, 999)

        # Count spirit nodes on shortest path(s)
        # BFS from grail to find shortest path predecessors
        # Simple: just count spirit nodes at each distance shell
        spirit_at_dist = defaultdict(int)
        bridge_at_dist = defaultdict(int)
        for nid, d in dists.items():
            if nid in spirit_ids:
                spirit_at_dist[d] += 1
            else:
                bridge_at_dist[d] += 1

        print(f"    [{inj_id}] {labels.get(inj_id, '?')} -> grail: "
              f"BFS dist={d_to_grail}, spirit on d=1: {spirit_at_dist.get(1, 0)}")

    elapsed = time.time() - t0
    print(f"\n  [{elapsed:.1f}s, {trial_count} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": trial_count,
        "structural": {
            "spirit_edges": len(spirit_edges),
            "inj_edges": len(inj_edges),
            "hub_edges": len(hub_edges),
            "total_edges": len(raw_edges),
            "spirit_active_frac": spirit_active_frac,
            "tech_active_frac": tech_active_frac,
        },
    }


# ===================================================================
# PROBE 7 (Q7): SPREAD Coherence Invariance
# ===================================================================

def probe_7_spread_coherence():
    """Test if SPREAD's perfect coherence comes from injection symmetry."""
    print("\n" + "=" * 70)
    print("  PROBE 7 (Q7): SPREAD COHERENCE INVARIANCE MECHANISM")
    print("  6 spread variants x 2 damping values = 12 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    all_ids = sorted(labels.keys())
    total_energy = 150.0  # Same as standard

    variants = {
        "SPREAD_UNIFORM": lambda ids: {nid: total_energy / len(ids) for nid in ids},
        "SPREAD_NOISY_5pct": lambda ids: {
            nid: (total_energy / len(ids)) * (1 + 0.05 * (2 * (hash(nid) % 1000) / 1000 - 1))
            for nid in ids
        },
        "SPREAD_NOISY_20pct": lambda ids: {
            nid: (total_energy / len(ids)) * (1 + 0.20 * (2 * (hash(nid) % 1000) / 1000 - 1))
            for nid in ids
        },
        "SPREAD_NOISY_50pct": lambda ids: {
            nid: (total_energy / len(ids)) * (1 + 0.50 * (2 * (hash(nid) % 1000) / 1000 - 1))
            for nid in ids
        },
        "SPREAD_INJ5_ONLY": lambda ids: {nid: 30.0 for nid in INJECTION_IDS},
        "SPREAD_RANDOM_10": lambda ids: {
            nid: total_energy / 10.0
            for nid in sorted(ids, key=lambda x: hash(x * 7919))[:10]
        },
    }

    damp_values = [0.2, 55.0]
    results = []
    t0 = time.time()

    for damp in damp_values:
        for var_name, inj_fn in variants.items():
            engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
            injections = inj_fn(all_ids)
            for nid, amount in injections.items():
                engine.inject_by_id(nid, amount)

            rho_samples = []
            basin_visits = defaultdict(int)
            for s in range(1, STEPS + 1):
                engine.step()
                if s % SAMPLE_INTERVAL == 0:
                    m = engine.compute_metrics()
                    bid = m["rhoMaxId"]
                    if bid is not None:
                        basin_visits[bid] = basin_visits.get(bid, 0) + 1
                    rho_samples.append([n["rho"] for n in engine.physics.nodes])

            # Coherence
            rho_arr = np.array(rho_samples)
            id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}
            inj_indices = [id_to_idx[nid] for nid in INJECTION_IDS if nid in id_to_idx]
            corrs = []
            for a in range(len(inj_indices)):
                for b in range(a + 1, len(inj_indices)):
                    t1 = rho_arr[:, inj_indices[a]]
                    t2 = rho_arr[:, inj_indices[b]]
                    r1 = np.ptp(t1)
                    r2 = np.ptp(t2)
                    if r1 > 0 and r2 > 0:
                        t1n = (t1 - np.mean(t1)) / r1
                        t2n = (t2 - np.mean(t2)) / r2
                        c = np.corrcoef(t1n, t2n)[0, 1]
                        if not np.isnan(c):
                            corrs.append(abs(c))
            coherence = float(np.mean(corrs)) if corrs else 0.0

            # Entropy of initial injection
            inj_vals = list(injections.values())
            inj_total = sum(inj_vals)
            inj_entropy = 0.0
            if inj_total > 0:
                for v in inj_vals:
                    p = v / inj_total
                    if p > 0:
                        inj_entropy -= p * math.log(p)
                inj_entropy /= math.log(max(2, len(inj_vals)))

            dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None

            print(f"  d={damp:5.1f} {var_name:<22} coh={coherence:.4f}  "
                  f"n_inject={len(injections):3d}  inj_entropy={inj_entropy:.4f}  "
                  f"basin=[{dominant}] {labels.get(dominant, '?')}")

            results.append({
                "damping": damp,
                "variant": var_name,
                "coherence": coherence,
                "n_injected_nodes": len(injections),
                "injection_entropy": inj_entropy,
                "dominant_basin": dominant,
                "basin_label": labels.get(dominant, "?"),
            })

    elapsed = time.time() - t0

    print(f"\n  ANSWER Q7:")
    print(f"    If coherence drops with noise -> symmetry hypothesis confirmed")
    print(f"    If coherence stays 1.0 with noise -> something deeper at play")

    # Check sensitivity
    for damp in damp_values:
        uniform_coh = None
        for r in results:
            if r["damping"] == damp and r["variant"] == "SPREAD_UNIFORM":
                uniform_coh = r["coherence"]
        for r in results:
            if r["damping"] == damp and r["variant"] != "SPREAD_UNIFORM":
                delta = r["coherence"] - (uniform_coh or 0)
                print(f"    d={damp}: {r['variant']}: coh delta = {delta:+.4f}")

    print(f"\n  [{elapsed:.1f}s, {len(results)} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": len(results),
        "results": results,
    }


# ===================================================================
# PROBE 8 (Q8): SEQUENTIAL Iton Persistence
# ===================================================================

def probe_8_sequential_wavefront():
    """Test wavefront hypothesis: vary gap size and injection order."""
    print("\n" + "=" * 70)
    print("  PROBE 8 (Q8): SEQUENTIAL INJECTION WAVEFRONT HYPOTHESIS")
    print("  3 gap sizes x 3 orderings x 2 damping = 18 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)

    gap_sizes = [50, 100, 200]  # Steps between each injection
    orderings = {
        "FORWARD": STANDARD_INJECTIONS,
        "REVERSE": list(reversed(STANDARD_INJECTIONS)),
        "SINGLE_THEN_REST": [
            ("grail", 150.0),  # All energy in first shot, rest are empty
        ],
    }

    # Actually for SINGLE_THEN_REST, inject all into grail then nothing else
    # Better: test actual orderings
    orderings = {
        "FORWARD": STANDARD_INJECTIONS,
        "REVERSE": list(reversed(STANDARD_INJECTIONS)),
        "HIGHEST_FIRST": [("grail", 40.0), ("metatron", 35.0), ("pyramid", 30.0),
                          ("christ", 25.0), ("light codes", 20.0)],
        # Already is forward, so use a different ordering:
    }
    # Actually redefine with meaningfully different orderings
    orderings = {
        "FORWARD_std": [("grail", 40.0), ("metatron", 35.0), ("pyramid", 30.0),
                        ("christ", 25.0), ("light codes", 20.0)],
        "REVERSE_order": [("light codes", 20.0), ("christ", 25.0), ("pyramid", 30.0),
                          ("metatron", 35.0), ("grail", 40.0)],
        "SCATTERED": [("pyramid", 30.0), ("grail", 40.0), ("light codes", 20.0),
                      ("metatron", 35.0), ("christ", 25.0)],
    }

    damp_values = [0.2, 20.0]
    results = []
    t0 = time.time()

    for damp in damp_values:
        for gap in gap_sizes:
            for ord_name, inj_list in orderings.items():
                engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)

                rho_samples = []
                basin_visits = defaultdict(int)

                for i, (label, amount) in enumerate(inj_list):
                    engine.inject(label, amount)
                    for s in range(gap):
                        engine.step()
                        step_global = i * gap + s
                        if step_global % SAMPLE_INTERVAL == 0:
                            m = engine.compute_metrics()
                            bid = m["rhoMaxId"]
                            if bid is not None:
                                basin_visits[bid] = basin_visits.get(bid, 0) + 1
                            rho_samples.append([n["rho"] for n in engine.physics.nodes])

                # Compute iton score
                node_edges_map = defaultdict(list)
                for ei, e in enumerate(engine.physics.edges):
                    node_edges_map[e["from"]].append((ei, "from"))
                    node_edges_map[e["to"]].append((ei, "to"))

                n_pass = 0
                n_active = 0
                for n in engine.physics.nodes:
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
                        n_active += 1
                        if abs(inflow - outflow) < 0.3 * (inflow + outflow):
                            n_pass += 1

                iton_score = n_pass / n_active if n_active > 0 else 0.0

                # Coherence
                rho_arr = np.array(rho_samples) if rho_samples else np.zeros((1, 140))
                id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}
                inj_indices = [id_to_idx[nid] for nid in INJECTION_IDS if nid in id_to_idx]
                corrs = []
                for a_i in range(len(inj_indices)):
                    for b_i in range(a_i + 1, len(inj_indices)):
                        t1 = rho_arr[:, inj_indices[a_i]]
                        t2 = rho_arr[:, inj_indices[b_i]]
                        r1 = np.ptp(t1)
                        r2 = np.ptp(t2)
                        if r1 > 0 and r2 > 0:
                            t1n = (t1 - np.mean(t1)) / r1
                            t2n = (t2 - np.mean(t2)) / r2
                            c = np.corrcoef(t1n, t2n)[0, 1]
                            if not np.isnan(c):
                                corrs.append(abs(c))
                coherence = float(np.mean(corrs)) if corrs else 0.0

                dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
                final = engine.compute_metrics()

                print(f"  d={damp:5.1f} gap={gap:3d} {ord_name:<16} "
                      f"iton={iton_score:.3f} coh={coherence:.3f} "
                      f"pass={n_pass:3d} basin=[{dominant}]")

                results.append({
                    "damping": damp,
                    "gap_size": gap,
                    "ordering": ord_name,
                    "iton_score": iton_score,
                    "coherence": coherence,
                    "n_pass": n_pass,
                    "dominant_basin": dominant,
                    "basin_label": labels.get(dominant, "?"),
                })

    elapsed = time.time() - t0

    print(f"\n  ANSWER Q8:")
    print(f"    If larger gaps -> more iton persistence: wavefront hypothesis supported")
    print(f"    If ordering matters: initial node position creates directional bias")

    # Check gap effect at d=20
    for ord_name in orderings:
        gaps_iton = [(r["gap_size"], r["iton_score"])
                     for r in results if r["damping"] == 20.0 and r["ordering"] == ord_name]
        gaps_iton.sort()
        print(f"    d=20, {ord_name}: ", end="")
        for gap, iton in gaps_iton:
            print(f"gap={gap}->iton={iton:.3f}  ", end="")
        print()

    print(f"\n  [{elapsed:.1f}s, {len(results)} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": len(results),
        "results": results,
    }


# ===================================================================
# PROBE 9 (Q9): COLD_INJECT Novel Basin Discovery
# ===================================================================

def probe_9_cold_inject_reachability():
    """BFS reachability + individual cold-node injection tests."""
    print("\n" + "=" * 70)
    print("  PROBE 9 (Q9): COLD_INJECT NOVEL BASIN DISCOVERY")
    print("  BFS analysis + 5 individual cold nodes x 3 damping = 15 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)
    adj = build_adjacency(raw_edges)

    cold_5 = [64, 79, 82, 89, 90]  # john, par, johannine grove, mystery school, christine hayes
    novel_basins = [87, 94]  # crystals, christos

    # BFS analysis from standard injection nodes and cold nodes
    print(f"\n  BFS DISTANCES TO NOVEL BASINS:")
    print(f"  {'Source':<30} {'crystals[87]':>14} {'christos[94]':>14}")
    print(f"  {'-'*30} {'-'*14} {'-'*14}")

    source_nodes = list(INJECTION_IDS) + cold_5
    for src in source_nodes:
        dists = bfs_distances(adj, src)
        d87 = dists.get(87, 999)
        d94 = dists.get(94, 999)
        tag = "(inj)" if src in INJECTION_IDS else "(cold)"
        print(f"  [{src:3d}] {labels.get(src, '?'):<22} {tag}  {d87:>8}         {d94:>8}")

    # Are novel basins in a structural cluster?
    for nb_id in novel_basins:
        neighbors = adj.get(nb_id, set())
        nb_groups = [groups.get(nid, "?") for nid in neighbors]
        nb_degrees = [degrees.get(nid, 0) for nid in neighbors]
        print(f"\n  Novel basin [{nb_id}] {labels.get(nb_id, '?')}:")
        print(f"    Degree: {degrees.get(nb_id, 0)}")
        print(f"    Group: {groups.get(nb_id, '?')}")
        print(f"    Neighbor count: {len(neighbors)}")
        print(f"    Neighbor groups: {dict(zip(*np.unique(nb_groups, return_counts=True)))}")
        print(f"    Neighbor avg degree: {np.mean(nb_degrees):.1f}")

    # Individual cold-node injection tests
    print(f"\n  INDIVIDUAL COLD-NODE INJECTION TESTS:")
    damp_values = [5.0, 55.0, 79.5]
    results = []
    t0 = time.time()

    for damp in damp_values:
        for cold_id in cold_5:
            engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
            engine.inject_by_id(cold_id, 150.0)  # Full energy into single cold node

            basin_visits = defaultdict(int)
            for s in range(1, STEPS + 1):
                engine.step()
                if s % 50 == 0:
                    m = engine.compute_metrics()
                    bid = m["rhoMaxId"]
                    if bid is not None:
                        basin_visits[bid] = basin_visits.get(bid, 0) + 1

            dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
            is_novel = dominant in novel_basins

            print(f"  d={damp:5.1f} inject [{cold_id:3d}] {labels.get(cold_id, '?'):<22} "
                  f"-> basin=[{dominant}] {labels.get(dominant, '?'):<20} "
                  f"{'** NOVEL **' if is_novel else ''}")

            results.append({
                "damping": damp,
                "cold_id": cold_id,
                "cold_label": labels.get(cold_id, "?"),
                "dominant_basin": dominant,
                "basin_label": labels.get(dominant, "?"),
                "is_novel": is_novel,
                "basin_visits": dict(basin_visits),
            })

    # Also test: inject into standard nodes - can they EVER reach novel basins?
    print(f"\n  STANDARD NODE INJECTION TESTS (can they reach novel basins?):")
    for damp in [55.0, 79.5]:
        for inj_id in INJECTION_IDS:
            engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
            engine.inject_by_id(inj_id, 150.0)

            basin_visits = defaultdict(int)
            for s in range(1, STEPS + 1):
                engine.step()
                if s % 50 == 0:
                    m = engine.compute_metrics()
                    bid = m["rhoMaxId"]
                    if bid is not None:
                        basin_visits[bid] = basin_visits.get(bid, 0) + 1

            dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
            is_novel = dominant in novel_basins

            print(f"  d={damp:5.1f} inject [{inj_id:3d}] {labels.get(inj_id, '?'):<22} "
                  f"-> basin=[{dominant}] {labels.get(dominant, '?'):<20} "
                  f"{'** NOVEL **' if is_novel else ''}")

            results.append({
                "damping": damp,
                "cold_id": inj_id,
                "cold_label": labels.get(inj_id, "?"),
                "dominant_basin": dominant,
                "basin_label": labels.get(dominant, "?"),
                "is_novel": is_novel,
                "is_standard_injection": True,
            })

    elapsed = time.time() - t0
    novel_count = sum(1 for r in results if r.get("is_novel"))
    cold_novel = sum(1 for r in results if r.get("is_novel") and r["cold_id"] in cold_5)

    print(f"\n  ANSWER Q9:")
    print(f"    Novel basin discoveries: {novel_count} total, {cold_novel} from cold nodes")
    print(f"    If only cold nodes reach novel basins -> structurally isolated")

    print(f"\n  [{elapsed:.1f}s, {len(results)} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": len(results),
        "results": results,
    }


# ===================================================================
# PROBE 10 (Q10): Self-Attractor Phase Transition
# ===================================================================

def probe_10_self_attractor_transition():
    """Fine sweep d=5..35 to map self-attractor fraction."""
    print("\n" + "=" * 70)
    print("  PROBE 10 (Q10): SELF-ATTRACTOR PHASE TRANSITION")
    print("  30 representative nodes x 13 damping values = 390 trials")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)
    all_ids = sorted(labels.keys())

    # Select 30 representative nodes spanning degree distribution
    sorted_by_deg = sorted(all_ids, key=lambda x: degrees.get(x, 0))
    step = len(sorted_by_deg) // 30
    rep_nodes = [sorted_by_deg[i * step] for i in range(30)]
    # Make sure we include some known cold and known hot nodes
    rep_nodes = list(set(rep_nodes) | {1, 2, 9, 23, 29, 79, 82, 11, 64, 89})
    rep_nodes = sorted(rep_nodes)

    print(f"  Using {len(rep_nodes)} representative nodes")

    damp_values = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 35]
    results = []
    t0 = time.time()
    trial_count = 0

    for damp in damp_values:
        n_self = 0
        n_tested = 0
        self_attractors = []
        non_self = []

        for nid in rep_nodes:
            engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
            engine.inject_by_id(nid, 50.0)

            basin_visits = defaultdict(int)
            for s in range(1, 301):  # 300 steps (shorter, sufficient for basin detection)
                engine.step()
                if s % 50 == 0:
                    m = engine.compute_metrics()
                    bid = m["rhoMaxId"]
                    if bid is not None:
                        basin_visits[bid] = basin_visits.get(bid, 0) + 1

            dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
            n_tested += 1
            trial_count += 1
            if dominant == nid:
                n_self += 1
                self_attractors.append(nid)
            else:
                non_self.append((nid, dominant))

        frac = n_self / n_tested if n_tested > 0 else 0.0
        print(f"  d={damp:5.1f}  self_attractors={n_self:3d}/{n_tested}  "
              f"fraction={frac:.3f}")

        results.append({
            "damping": damp,
            "n_self_attractors": n_self,
            "n_tested": n_tested,
            "fraction": frac,
            "self_attractor_ids": self_attractors,
        })

    elapsed = time.time() - t0

    # Fit sigmoid to detect phase transition
    fracs = np.array([r["fraction"] for r in results])
    damps = np.array([r["damping"] for r in results])

    # Find steepest drop
    max_drop = 0.0
    max_drop_d = 0.0
    for i in range(1, len(fracs)):
        drop = fracs[i-1] - fracs[i]
        if drop > max_drop:
            max_drop = drop
            max_drop_d = (damps[i-1] + damps[i]) / 2

    # Check for sharp vs smooth: is there a single step where >50% of the total drop occurs?
    total_drop = fracs[0] - fracs[-1]
    single_step_fraction = max_drop / total_drop if total_drop > 0 else 0.0

    print(f"\n  ANSWER Q10:")
    print(f"    Total self-attractor drop: {fracs[0]:.3f} -> {fracs[-1]:.3f}")
    print(f"    Steepest single drop: {max_drop:.3f} at d~{max_drop_d:.1f}")
    print(f"    Single-step fraction of total: {single_step_fraction:.3f}")
    if single_step_fraction > 0.5:
        print(f"    -> PHASE TRANSITION: >50% of drop in one step (sharp)")
    elif single_step_fraction > 0.3:
        print(f"    -> STEEP CROSSOVER: 30-50% in one step (semi-sharp)")
    else:
        print(f"    -> SMOOTH CROSSOVER: distributed decline")

    # Check width of transition
    # Find d where fraction crosses 0.5
    d_half = None
    for i in range(1, len(fracs)):
        if fracs[i-1] >= 0.5 and fracs[i] < 0.5:
            # Linear interpolation
            d_half = damps[i-1] + (damps[i] - damps[i-1]) * (fracs[i-1] - 0.5) / (fracs[i-1] - fracs[i])
    if d_half is not None:
        print(f"    Half-point: d = {d_half:.1f}")

        # Width defined as d(0.9) to d(0.1):
        d_90 = d_10 = None
        for i in range(1, len(fracs)):
            if fracs[i-1] >= 0.9 * fracs[0] and fracs[i] < 0.9 * fracs[0] and d_90 is None:
                d_90 = damps[i]
            if fracs[i-1] >= 0.1 * fracs[0] and fracs[i] < 0.1 * fracs[0] and d_10 is None:
                d_10 = damps[i]
        if d_90 is not None and d_10 is not None:
            print(f"    Transition width (90%->10%): d={d_90} to d={d_10} (width={d_10-d_90})")

    print(f"\n  [{elapsed:.1f}s, {trial_count} trials]")

    return {
        "runtime_sec": round(elapsed, 2),
        "trials": trial_count,
        "results": results,
        "max_drop": max_drop,
        "max_drop_damping": max_drop_d,
        "single_step_fraction": single_step_fraction,
    }


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  SOL OPEN-QUESTIONS INVESTIGATION")
    print("  10 Targeted Probes")
    print("=" * 70)

    t_start = time.time()

    p1 = probe_1_coherence_resurrection()
    p2 = probe_2_mode_precollapse()
    p3 = probe_3_iton_pathway()
    p4 = probe_4_cold_wire_relays()
    p5 = probe_5_phase_coupling()
    p6 = probe_6_spirit_highway()
    p7 = probe_7_spread_coherence()
    p8 = probe_8_sequential_wavefront()
    p9 = probe_9_cold_inject_reachability()
    p10 = probe_10_self_attractor_transition()

    total_time = time.time() - t_start
    total_trials = sum(p["trials"] for p in [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10])

    print(f"\n{'=' * 70}")
    print(f"  INVESTIGATION COMPLETE")
    print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Total trials: {total_trials}")
    print(f"{'=' * 70}")

    # Save
    out_path = _SOL_ROOT / "data" / "open_questions_investigation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_sec": round(total_time, 2),
        "total_trials": total_trials,
        "probe_1_coherence_resurrection": p1,
        "probe_2_mode_precollapse": p2,
        "probe_3_iton_pathway": p3,
        "probe_4_cold_wire_relays": p4,
        "probe_5_phase_coupling": p5,
        "probe_6_spirit_highway": p6,
        "probe_7_spread_coherence": p7,
        "probe_8_sequential_wavefront": p8,
        "probe_9_cold_inject_reachability": p9,
        "probe_10_self_attractor_transition": p10,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()
