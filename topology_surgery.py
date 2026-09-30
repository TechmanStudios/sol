#!/usr/bin/env python3
"""
SOL Topology Surgery Suite
============================

Controlled graph modifications to prove "the graph is the program."
Each surgery modifies a COPY of the default graph (sol-core is IMMUTABLE)
and runs the same multi-agent injection + phonon analysis protocol.

Surgeries:
  1. CONTROL    — Unmodified graph (baseline for comparison)
  2. HUB_SEVER  — Cut metatron's 3 hub edges (par, johannine grove, mystery school)
  3. BRIDGE_ADD — Add direct grail↔pyramid edge (no direct link in default graph)
  4. COLD_WIRE  — Wire peripheral node "orion" [11] directly to metatron [9]
  5. HUB_REMOVE — Remove ALL edges involving par [79] (degree 108 mega-hub)
  6. SPIRIT_CUT — Remove all spirit-to-spirit edges, isolate the spirit layer

Each surgery is tested at key damping values across the full regime:
  d = [0.2, 5.0, 20.0, 55.0, 79.5, 83.0, 83.35, 84.0]

Measurements per trial:
  - Dominant basin, mode count, coherence, heartbeat power
  - Iton score (pass-through nodes / active nodes)
  - Catastrophic collapse threshold (scan d=80→84 at 0.1)
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
MULTI_AGENT_INJECTIONS = [
    ("grail", 40.0),
    ("metatron", 35.0),
    ("pyramid", 30.0),
    ("christ", 25.0),
    ("light codes", 20.0),
]

PROBE_DAMPS = [0.2, 5.0, 20.0, 55.0, 79.5, 83.0, 83.35, 84.0]
COLLAPSE_SCAN_RANGE = [round(80.0 + i * 0.1, 1) for i in range(45)]  # 80.0→84.4
STEPS = 500


def load_default_graph():
    path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(path) as f:
        data = json.load(f)
    return data["rawNodes"], data["rawEdges"]


def make_label_map(raw_nodes):
    return {n["label"]: n["id"] for n in raw_nodes}


def make_engine_from_graph(raw_nodes, raw_edges, damping, seed=42):
    engine = SOLEngine.from_graph(
        raw_nodes, raw_edges,
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed
    )
    for label, amount in MULTI_AGENT_INJECTIONS:
        engine.inject(label, amount)
    return engine


# ===================================================================
# Surgery Definitions
# ===================================================================

def surgery_control(raw_nodes, raw_edges):
    """No modification — baseline."""
    return copy.deepcopy(raw_nodes), copy.deepcopy(raw_edges)


def surgery_hub_sever(raw_nodes, raw_edges):
    """Cut metatron [9] from par [79], johannine grove [82], mystery school [89]."""
    nodes = copy.deepcopy(raw_nodes)
    cut_pairs = {(9, 79), (79, 9), (9, 82), (82, 9), (9, 89), (89, 9)}
    edges = [e for e in copy.deepcopy(raw_edges)
             if (e["from"], e["to"]) not in cut_pairs]
    return nodes, edges


def surgery_bridge_add(raw_nodes, raw_edges):
    """Add direct grail [1] ↔ pyramid [29] edge."""
    nodes = copy.deepcopy(raw_nodes)
    edges = copy.deepcopy(raw_edges)
    edges.append({"from": 1, "to": 29})
    return nodes, edges


def surgery_cold_wire(raw_nodes, raw_edges):
    """Wire orion [11] directly to metatron [9]."""
    nodes = copy.deepcopy(raw_nodes)
    edges = copy.deepcopy(raw_edges)
    # Check if edge already exists
    exists = any((e["from"] == 9 and e["to"] == 11) or
                 (e["from"] == 11 and e["to"] == 9)
                 for e in edges)
    if not exists:
        edges.append({"from": 9, "to": 11})
    return nodes, edges


def surgery_hub_remove(raw_nodes, raw_edges):
    """Remove ALL edges involving par [79]."""
    nodes = copy.deepcopy(raw_nodes)
    edges = [e for e in copy.deepcopy(raw_edges)
             if e["from"] != 79 and e["to"] != 79]
    return nodes, edges


def surgery_spirit_cut(raw_nodes, raw_edges):
    """Remove all edges between spirit-group nodes."""
    nodes = copy.deepcopy(raw_nodes)
    id_to_group = {n["id"]: n.get("group", "bridge") for n in nodes}
    edges = []
    for e in copy.deepcopy(raw_edges):
        g_from = id_to_group.get(e["from"], "bridge")
        g_to = id_to_group.get(e["to"], "bridge")
        if g_from == "spirit" and g_to == "spirit":
            continue  # cut spirit↔spirit edges
        edges.append(e)
    return nodes, edges


SURGERIES = {
    "CONTROL":     ("Unmodified baseline", surgery_control),
    "HUB_SEVER":   ("Cut metatron from 3 hubs", surgery_hub_sever),
    "BRIDGE_ADD":  ("Add grail↔pyramid link", surgery_bridge_add),
    "COLD_WIRE":   ("Wire orion→metatron", surgery_cold_wire),
    "HUB_REMOVE":  ("Remove par (degree-108 hub)", surgery_hub_remove),
    "SPIRIT_CUT":  ("Sever spirit↔spirit edges", surgery_spirit_cut),
}


# ===================================================================
# Analysis Functions
# ===================================================================

def run_trial(raw_nodes, raw_edges, damping, steps=STEPS, seed=42):
    """Run a single trial and return metrics."""
    engine = make_engine_from_graph(raw_nodes, raw_edges, damping, seed)
    n_nodes = len(engine.physics.nodes)

    rho_samples = []
    basin_visits = defaultdict(int)

    for s in range(1, steps + 1):
        engine.step()
        if s % 5 == 0:
            m = engine.compute_metrics()
            bid = m["rhoMaxId"]
            if bid is not None:
                basin_visits[bid] = basin_visits.get(bid, 0) + 1
            rho_samples.append([n["rho"] for n in engine.physics.nodes])

    final = engine.compute_metrics()
    rho_arr = np.array(rho_samples) if rho_samples else np.zeros((1, n_nodes))

    # Mode count
    osc_amps = []
    for j in range(n_nodes):
        trace = rho_arr[:, j]
        if np.max(trace) > 1e-15:
            osc_amps.append(np.std(trace) / max(np.mean(trace), 1e-15))
        else:
            osc_amps.append(0.0)
    n_modes = int(np.sum(np.array(osc_amps) > 0.01))

    # Coherence (normalized)
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

    # Heartbeat power
    mass_signal = np.sum(rho_arr, axis=1)
    hb_power = 0.0
    if np.max(np.abs(mass_signal)) > 1e-15:
        fft_v = np.fft.rfft(mass_signal)
        power = np.abs(fft_v) ** 2
        freqs = np.fft.rfftfreq(len(mass_signal), d=DT * 5)
        hb_freq = 0.15 * 10 / (2 * math.pi)
        p_no_dc = power[1:]
        f_no_dc = freqs[1:]
        if len(p_no_dc) > 0 and np.sum(p_no_dc) > 1e-15:
            hb_band = np.abs(f_no_dc - hb_freq) < 0.1
            sub_band = np.abs(f_no_dc - hb_freq / 2) < 0.1
            hb_power = float(np.sum(p_no_dc[hb_band | sub_band]) / np.sum(p_no_dc))

    # Iton score: count pass-through nodes
    # A node is pass-through if it has both significant inflow and outflow
    node_edges_map = defaultdict(list)
    for ei, e in enumerate(engine.physics.edges):
        node_edges_map[e["from"]].append((ei, "from"))
        node_edges_map[e["to"]].append((ei, "to"))

    n_sources = 0
    n_pass = 0
    n_sinks = 0
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

    iton_score = n_pass / total_active if total_active > 0 else 0.0

    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None

    return {
        "damping": damping,
        "dominant_basin": dominant,
        "n_modes": n_modes,
        "coherence": coherence,
        "hb_power": hb_power,
        "iton_score": iton_score,
        "n_sources": n_sources,
        "n_pass": n_pass,
        "n_sinks": n_sinks,
        "final_maxrho": final["maxRho"],
        "final_entropy": final["entropy"],
        "edge_count": len(engine.physics.edges),
    }


def find_collapse_threshold(raw_nodes, raw_edges):
    """Scan d=80→84.4 at 0.1 resolution to find the catastrophic collapse boundary."""
    for damp in COLLAPSE_SCAN_RANGE:
        r = run_trial(raw_nodes, raw_edges, damp, steps=300)
        if r["n_modes"] <= 10:
            return damp, r["n_modes"]
    return None, None


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  SOL TOPOLOGY SURGERY SUITE")
    print("  6 surgeries × 8 damping values + collapse threshold scan")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = {n["id"]: n["label"] for n in raw_nodes}
    t_total = time.time()

    all_results = {}

    for sname, (desc, surgery_fn) in SURGERIES.items():
        print(f"\n{'─' * 70}")
        print(f"  SURGERY: {sname} — {desc}")
        print(f"{'─' * 70}")

        s_nodes, s_edges = surgery_fn(raw_nodes, raw_edges)
        n_edges = len(s_edges)
        n_edges_diff = n_edges - len(raw_edges)
        print(f"  Edges: {n_edges} ({n_edges_diff:+d} vs control)")

        t0 = time.time()

        # Probe at key damping values
        probe_results = []
        for damp in PROBE_DAMPS:
            r = run_trial(s_nodes, s_edges, damp)
            probe_results.append(r)
            basin_lbl = labels.get(r["dominant_basin"], "?") if r["dominant_basin"] else "None"
            print(f"    d={damp:5.1f}  modes={r['n_modes']:3d}  "
                  f"coh={r['coherence']:.4f}  HB={r['hb_power']:.4f}  "
                  f"iton={r['iton_score']:.3f}  "
                  f"basin=[{r['dominant_basin']}] {basin_lbl}")

        # Find collapse threshold
        print(f"    Scanning collapse threshold (d=80→84.4)...")
        collapse_d, collapse_modes = find_collapse_threshold(s_nodes, s_edges)
        if collapse_d is not None:
            print(f"    COLLAPSE at d={collapse_d:.1f} (modes → {collapse_modes})")
        else:
            print(f"    NO COLLAPSE in range d=80→84.4")

        elapsed = time.time() - t0
        print(f"    [{elapsed:.1f}s]")

        all_results[sname] = {
            "description": desc,
            "edge_count": n_edges,
            "edge_delta": n_edges_diff,
            "probe_results": probe_results,
            "collapse_threshold": collapse_d,
            "collapse_modes": collapse_modes,
        }

    total_time = time.time() - t_total

    # ===================================================================
    # Comparison Report
    # ===================================================================
    print(f"\n{'=' * 70}")
    print(f"  TOPOLOGY SURGERY — COMPARATIVE RESULTS")
    print(f"{'=' * 70}")

    # Collapse threshold comparison
    print(f"\n  CATASTROPHIC COLLAPSE THRESHOLDS:")
    control_collapse = all_results["CONTROL"]["collapse_threshold"]
    for sname, sr in all_results.items():
        ct = sr["collapse_threshold"]
        if ct is not None and control_collapse is not None:
            shift = ct - control_collapse
            print(f"    {sname:<14} d={ct:5.1f}  (Δ={shift:+.1f} vs control)")
        elif ct is None:
            print(f"    {sname:<14} NO COLLAPSE (immune!)")
        else:
            print(f"    {sname:<14} d={ct:5.1f}")

    # Mode count comparison at d=83.35
    print(f"\n  MODE COUNT AT d=83.35 (post-collapse in control):")
    for sname, sr in all_results.items():
        for r in sr["probe_results"]:
            if abs(r["damping"] - 83.35) < 0.01:
                print(f"    {sname:<14} modes={r['n_modes']:3d}")

    # Iton score comparison at d=0.2
    print(f"\n  ITON SCORE AT d=0.2 (peak transport):")
    for sname, sr in all_results.items():
        for r in sr["probe_results"]:
            if abs(r["damping"] - 0.2) < 0.01:
                print(f"    {sname:<14} iton={r['iton_score']:.3f}  "
                      f"pass={r['n_pass']:2d}  sources={r['n_sources']:2d}  "
                      f"sinks={r['n_sinks']:3d}")

    # Basin comparison across damping
    print(f"\n  BASIN SUCCESSION:")
    for sname, sr in all_results.items():
        basins = []
        for r in sr["probe_results"]:
            b = r["dominant_basin"]
            lbl = labels.get(b, "?") if b else "None"
            basins.append(f"d={r['damping']}: {lbl}")
        print(f"    {sname:<14}", end="")
        prev_basin = None
        for r in sr["probe_results"]:
            b = r["dominant_basin"]
            if b != prev_basin:
                lbl = labels.get(b, "?") if b else "None"
                print(f"  d={r['damping']}→{lbl}", end="")
                prev_basin = b
        print()

    # Coherence at d=79.5 (resurrection point)
    print(f"\n  COHERENCE AT d=79.5 (resurrection point in control):")
    for sname, sr in all_results.items():
        for r in sr["probe_results"]:
            if abs(r["damping"] - 79.5) < 0.01:
                print(f"    {sname:<14} coh={r['coherence']:.4f}  "
                      f"modes={r['n_modes']:3d}")

    print(f"\n  Total runtime: {total_time:.1f}s")

    # Save
    out_path = _SOL_ROOT / "data" / "topology_surgery.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Serialize
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_sec": round(total_time, 2),
        "surgeries": {
            sname: {
                "description": sr["description"],
                "edge_count": sr["edge_count"],
                "edge_delta": sr["edge_delta"],
                "collapse_threshold": sr["collapse_threshold"],
                "collapse_modes": sr["collapse_modes"],
                "probe_results": sr["probe_results"],
            }
            for sname, sr in all_results.items()
        }
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()
