#!/usr/bin/env python3
"""
SOL Logic Gate & Signal Router — Experiment 8
===============================================

Demonstrates that the SOL lattice can implement Boolean logic gates and
programmable signal routing using four primitives established in prior R&D:

  1. Addressable routing  — spirit-highway w0 programming steers basins
  2. Relay amplification   — cold-node / reverse-sequential creates 3x iton
  3. Coherence control     — SPREAD vs point injection controls phase alignment
  4. Persistent transport  — REVERSE sequential gap=100 sustains iton under stress

CONSTRUCTS BUILT:
  Gate 1: NOT GATE   — Spirit-highway ON inverts default basin (metatron -> grail)
  Gate 2: AND GATE   — Both injection AND highway required for grail basin
  Gate 3: OR GATE    — Either input A or input B pushes energy above threshold
  Gate 4: SIGNAL ROUTER  — w0 weight vectors steer to 4+ distinct basin targets
  Gate 5: RELAY CHAIN    — REVERSE sequential builds persistent relay network
  Gate 6: 2-BIT MUX  — Combines routing + injection to address 4 output states

ENGINE: tools/sol-core/sol_engine.py (IMMUTABLE)
GRAPH:  tools/sol-core/default_graph.json (IMMUTABLE — modified copies only)

Outputs: data/logic_gate_router.json
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

from sol_engine import SOLEngine, SOLPhysics, create_engine

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

# Known node IDs from the graph
NODE_IDS = {
    "grail": 1, "christ": 2, "metatron": 9, "light codes": 23,
    "pyramid": 29, "par": 79, "johannine grove": 82,
    "mystery school": 89, "christine hayes": 90,
    "numis'om": 80, "orion": 5, "thothhorra": 31,
}


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
    """Build adjacency list from edges."""
    adj = defaultdict(set)
    for e in raw_edges:
        adj[e["from"]].add(e["to"])
        adj[e["to"]].add(e["from"])
    return adj


def make_engine_from_modified(raw_nodes, raw_edges, damping, seed=42):
    """Create engine from (potentially modified) graph data."""
    return SOLEngine.from_graph(
        raw_nodes, raw_edges,
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed
    )


def apply_standard_injection(engine):
    for label, amount in STANDARD_INJECTIONS:
        engine.inject(label, amount)


def set_spirit_highway(raw_edges, w0_spirit=3.0, raw_nodes=None):
    """Set w0 for all spirit-adjacent edges. Returns modified edge list."""
    groups = {}
    if raw_nodes:
        groups = {n["id"]: n.get("group", "bridge") for n in raw_nodes}
    edges = copy.deepcopy(raw_edges)
    count = 0
    for e in edges:
        sg = groups.get(e["from"], "bridge")
        dg = groups.get(e["to"], "bridge")
        if sg == "spirit" or dg == "spirit":
            e["w0"] = w0_spirit
            count += 1
    return edges, count


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def analyze_trial(engine, rho_samples):
    """Compute mode count, coherence, iton score, dominant basin."""
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

    return {
        "n_modes": n_modes,
        "coherence": coherence,
        "iton_score": iton_score,
        "n_sources": n_sources,
        "n_pass": n_pass,
        "n_sinks": n_sinks,
    }


def run_and_analyze(engine, steps=STEPS, sample_every=SAMPLE_INTERVAL):
    """Step, collect rho samples, compute metrics."""
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
    analysis["dominant_basin"] = dominant
    analysis["dominant_basin_frac"] = basin_visits.get(dominant, 0) / max(1, sum(basin_visits.values())) if dominant else 0.0
    analysis["final_maxrho"] = final["maxRho"]
    analysis["final_entropy"] = final["entropy"]
    analysis["final_mass"] = final["mass"]
    analysis["basin_visits"] = dict(basin_visits)
    analysis["top5_rho"] = sorted(
        [(n["id"], n["rho"]) for n in engine.physics.nodes],
        key=lambda x: x[1], reverse=True
    )[:5]

    return analysis


def format_basin(nid, labels):
    """Format a basin ID for printing."""
    return f"{labels.get(nid, '?')}[{nid}]"


# ===================================================================
# GATE 1: NOT GATE
# ===================================================================
# Input:  SPIRIT_HIGHWAY = ON (w0=3.0) or OFF (w0=1.0)
# Output: Basin destination
#   OFF -> metatron (default basin)
#   ON  -> grail (inverted via spirit-highway steering)
# ===================================================================

def gate_1_not():
    """NOT gate via spirit-highway inversion."""
    print("\n" + "=" * 70)
    print("  GATE 1: NOT GATE (spirit-highway inversion)")
    print("  Input: SPIRIT_HIGHWAY = {OFF, ON}")
    print("  Output: basin destination")
    print("  Expected: OFF->metatron, ON->grail")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results = {}

    test_damps = [0.2, 5.0, 20.0]

    for damp in test_damps:
        print(f"\n  Damping d={damp}:")

        # --- Input = OFF (default w0) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)
        off_result = run_and_analyze(engine, steps=STEPS)
        off_basin = off_result["dominant_basin"]
        print(f"    HIGHWAY OFF: basin = {format_basin(off_basin, labels)}, "
              f"iton={off_result['iton_score']:.3f}, coh={off_result['coherence']:.4f}")

        # --- Input = ON (spirit highway w0=3.0) ---
        mod_edges, n_mod = set_spirit_highway(raw_edges, w0_spirit=3.0, raw_nodes=raw_nodes)
        engine = make_engine_from_modified(raw_nodes, mod_edges, damping=damp, seed=42)
        apply_standard_injection(engine)
        on_result = run_and_analyze(engine, steps=STEPS)
        on_basin = on_result["dominant_basin"]
        print(f"    HIGHWAY ON:  basin = {format_basin(on_basin, labels)}, "
              f"iton={on_result['iton_score']:.3f}, coh={on_result['coherence']:.4f}")

        # Gate correctness
        inversion = (off_basin != on_basin)
        print(f"    NOT gate {'PASS' if inversion else 'FAIL'}: "
              f"OFF={format_basin(off_basin, labels)} -> ON={format_basin(on_basin, labels)}")

        results[damp] = {
            "off": {"basin": off_basin, "iton": off_result["iton_score"],
                    "coherence": off_result["coherence"]},
            "on": {"basin": on_basin, "iton": on_result["iton_score"],
                   "coherence": on_result["coherence"]},
            "inverted": inversion,
        }

    passed = sum(1 for r in results.values() if r["inverted"])
    total = len(results)
    print(f"\n  NOT GATE SUMMARY: {passed}/{total} damping values show inversion")

    return {"gate": "NOT", "results": results, "pass_rate": passed / total}


# ===================================================================
# GATE 2: AND GATE
# ===================================================================
# Input A: INJECTION = ON (standard 5-agent) or OFF (no injection)
# Input B: SPIRIT_HIGHWAY = ON (w0=3.0) or OFF (w0=1.0)
# Output: Basin = grail ONLY when BOTH inputs are ON
#   A=0 B=0 -> no energy (trivially not grail)
#   A=1 B=0 -> metatron (injection but no highway)
#   A=0 B=1 -> no energy (highway but no injection)
#   A=1 B=1 -> grail (injection + highway together)
# ===================================================================

def gate_2_and():
    """AND gate: injection AND highway both required for grail basin."""
    print("\n" + "=" * 70)
    print("  GATE 2: AND GATE (injection AND spirit-highway)")
    print("  Input A: INJECTION = {OFF, ON}")
    print("  Input B: SPIRIT_HIGHWAY = {OFF, ON}")
    print("  Output: grail ONLY when A=1 AND B=1")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results = {}

    test_damps = [0.2, 5.0, 20.0]

    for damp in test_damps:
        print(f"\n  Damping d={damp}:")
        gate_states = {}

        # --- A=0, B=0 (no injection, no highway) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        # No injection
        r00 = run_and_analyze(engine, steps=STEPS)
        b00 = r00["dominant_basin"]
        mass00 = r00["final_mass"]
        print(f"    A=0 B=0: basin={format_basin(b00, labels)}, mass={mass00:.2f}")
        gate_states["00"] = {"basin": b00, "mass": mass00, "is_grail": b00 == 1}

        # --- A=1, B=0 (injection, no highway) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)
        r10 = run_and_analyze(engine, steps=STEPS)
        b10 = r10["dominant_basin"]
        print(f"    A=1 B=0: basin={format_basin(b10, labels)}, "
              f"iton={r10['iton_score']:.3f}")
        gate_states["10"] = {"basin": b10, "is_grail": b10 == 1,
                             "iton": r10["iton_score"]}

        # --- A=0, B=1 (no injection, highway ON) ---
        mod_edges, _ = set_spirit_highway(raw_edges, w0_spirit=3.0, raw_nodes=raw_nodes)
        engine = make_engine_from_modified(raw_nodes, mod_edges, damping=damp, seed=42)
        # No injection
        r01 = run_and_analyze(engine, steps=STEPS)
        b01 = r01["dominant_basin"]
        mass01 = r01["final_mass"]
        print(f"    A=0 B=1: basin={format_basin(b01, labels)}, mass={mass01:.2f}")
        gate_states["01"] = {"basin": b01, "mass": mass01, "is_grail": b01 == 1}

        # --- A=1, B=1 (injection + highway) ---
        engine = make_engine_from_modified(raw_nodes, mod_edges, damping=damp, seed=42)
        apply_standard_injection(engine)
        r11 = run_and_analyze(engine, steps=STEPS)
        b11 = r11["dominant_basin"]
        print(f"    A=1 B=1: basin={format_basin(b11, labels)}, "
              f"iton={r11['iton_score']:.3f}")
        gate_states["11"] = {"basin": b11, "is_grail": b11 == 1,
                             "iton": r11["iton_score"]}

        # Verify AND truth table: grail ONLY at 11
        grail_id = 1
        correct = (
            gate_states["00"]["basin"] != grail_id and
            gate_states["10"]["basin"] != grail_id and
            gate_states["01"]["basin"] != grail_id and
            gate_states["11"]["basin"] == grail_id
        )
        # More relaxed: grail at 11, NOT grail at 10
        relaxed = (
            gate_states["10"]["basin"] != grail_id and
            gate_states["11"]["basin"] == grail_id
        )
        print(f"    AND gate strict={'PASS' if correct else 'FAIL'}, "
              f"relaxed={'PASS' if relaxed else 'FAIL'}")

        results[damp] = {
            "states": gate_states,
            "strict_pass": correct,
            "relaxed_pass": relaxed,
        }

    passed_strict = sum(1 for r in results.values() if r["strict_pass"])
    passed_relaxed = sum(1 for r in results.values() if r["relaxed_pass"])
    total = len(results)
    print(f"\n  AND GATE SUMMARY: strict={passed_strict}/{total}, "
          f"relaxed={passed_relaxed}/{total}")

    return {"gate": "AND", "results": results,
            "strict_pass_rate": passed_strict / total,
            "relaxed_pass_rate": passed_relaxed / total}


# ===================================================================
# GATE 3: OR GATE
# ===================================================================
# Input A: Standard injection (grail 40)
# Input B: Cold-node injection (cold nodes, 40 total)
# Output: HIGH energy (mass > threshold) if EITHER input is ON
#   A=0 B=0 -> LOW (no energy)
#   A=1 B=0 -> HIGH
#   A=0 B=1 -> HIGH
#   A=1 B=1 -> HIGH
# ===================================================================

def gate_3_or():
    """OR gate: either input raises energy above threshold."""
    print("\n" + "=" * 70)
    print("  GATE 3: OR GATE (multiple injection sources)")
    print("  Input A: Standard injection (grail, 40)")
    print("  Input B: Cold-node injection (christine hayes, 40)")
    print("  Output: energy above threshold")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results = {}

    # Christine hayes (90) is a known cold node with degree=70, spirit group
    cold_node_id = 90
    cold_label = "christine hayes"

    test_damps = [0.2, 5.0, 20.0]

    for damp in test_damps:
        print(f"\n  Damping d={damp}:")
        gate_states = {}

        # --- A=0, B=0 (no injection) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        r00 = run_and_analyze(engine, steps=STEPS)
        mass00 = r00["final_mass"]
        max_rho_00 = r00["final_maxrho"]
        print(f"    A=0 B=0: mass={mass00:.4f}, maxRho={max_rho_00:.4f}")
        gate_states["00"] = {"mass": mass00, "maxRho": max_rho_00}

        # --- A=1, B=0 (standard grail injection only) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        engine.inject("grail", 40.0)
        r10 = run_and_analyze(engine, steps=STEPS)
        mass10 = r10["final_mass"]
        max_rho_10 = r10["final_maxrho"]
        b10 = r10["dominant_basin"]
        print(f"    A=1 B=0: mass={mass10:.4f}, maxRho={max_rho_10:.4f}, "
              f"basin={format_basin(b10, labels)}")
        gate_states["10"] = {"mass": mass10, "maxRho": max_rho_10, "basin": b10}

        # --- A=0, B=1 (cold-node injection only) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        engine.inject_by_id(cold_node_id, 40.0)
        r01 = run_and_analyze(engine, steps=STEPS)
        mass01 = r01["final_mass"]
        max_rho_01 = r01["final_maxrho"]
        b01 = r01["dominant_basin"]
        print(f"    A=0 B=1: mass={mass01:.4f}, maxRho={max_rho_01:.4f}, "
              f"basin={format_basin(b01, labels)}")
        gate_states["01"] = {"mass": mass01, "maxRho": max_rho_01, "basin": b01}

        # --- A=1, B=1 (both injections) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        engine.inject("grail", 40.0)
        engine.inject_by_id(cold_node_id, 40.0)
        r11 = run_and_analyze(engine, steps=STEPS)
        mass11 = r11["final_mass"]
        max_rho_11 = r11["final_maxrho"]
        b11 = r11["dominant_basin"]
        print(f"    A=1 B=1: mass={mass11:.4f}, maxRho={max_rho_11:.4f}, "
              f"basin={format_basin(b11, labels)}")
        gate_states["11"] = {"mass": mass11, "maxRho": max_rho_11, "basin": b11}

        # Determine threshold: midpoint between 00 and minimum of {10, 01}
        min_active = min(mass10, mass01)
        threshold = (mass00 + min_active) / 2.0

        or_correct = (
            mass00 < threshold and
            mass10 > threshold and
            mass01 > threshold and
            mass11 > threshold
        )
        print(f"    Threshold={threshold:.4f}")
        print(f"    OR gate {'PASS' if or_correct else 'FAIL'}: "
              f"00={'LO' if mass00 < threshold else 'HI'}, "
              f"10={'HI' if mass10 > threshold else 'LO'}, "
              f"01={'HI' if mass01 > threshold else 'LO'}, "
              f"11={'HI' if mass11 > threshold else 'LO'}")

        results[damp] = {
            "states": gate_states,
            "threshold": threshold,
            "correct": or_correct,
        }

    passed = sum(1 for r in results.values() if r["correct"])
    total = len(results)
    print(f"\n  OR GATE SUMMARY: {passed}/{total} damping values correct")

    return {"gate": "OR", "results": results, "pass_rate": passed / total}


# ===================================================================
# GATE 4: SIGNAL ROUTER (4-way address decoder)
# ===================================================================
# Uses w0 weight programming to steer energy to distinct basins.
# 4 weight vectors -> 4 different basin destinations.
# ===================================================================

def gate_4_signal_router():
    """4-way signal router via w0 weight vectors."""
    print("\n" + "=" * 70)
    print("  GATE 4: SIGNAL ROUTER (4-way address decoder)")
    print("  4 weight vectors -> 4 distinct basin targets")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    adj = get_adjacency(raw_edges)

    # Find edges touching specific node groups for targeted routing
    # We define 4 routing configs that weight different subgraphs

    # Identify edge indices by connected node properties
    edge_info = []
    for ei, e in enumerate(raw_edges):
        edge_info.append({
            "idx": ei,
            "from": e["from"], "to": e["to"],
            "from_group": groups.get(e["from"], "bridge"),
            "to_group": groups.get(e["to"], "bridge"),
        })

    results = {}
    damp = 0.2  # Low damping shows routing most clearly

    ROUTE_CONFIGS = {
        "UNIFORM": {
            "description": "Default weights (w0=1.0 everywhere)",
            "rule": lambda e, nodes, groups: 1.0,
        },
        "SPIRIT_3x": {
            "description": "Spirit-adjacent edges w0=3.0",
            "rule": lambda e, nodes, groups: 3.0 if (
                groups.get(e["from"], "bridge") == "spirit" or
                groups.get(e["to"], "bridge") == "spirit"
            ) else 1.0,
        },
        "GRAIL_ATTRACT": {
            "description": "Edges touching grail neighbors w0=3.0, others w0=0.5",
            "rule": lambda e, nodes, groups: 3.0 if (
                e["from"] == 1 or e["to"] == 1 or
                e["from"] in adj.get(1, set()) or e["to"] in adj.get(1, set())
            ) else 0.5,
        },
        "HUB_SUPPRESS": {
            "description": "Mega-hub (par,jg) edges w0=0.1, others w0=2.0",
            "rule": lambda e, nodes, groups: 0.1 if (
                e["from"] in (79, 82) or e["to"] in (79, 82)
            ) else 2.0,
        },
        "PYRAMID_FOCUS": {
            "description": "Pyramid neighborhood w0=3.0, spirit w0=0.3",
            "rule": lambda e, nodes, groups: 3.0 if (
                e["from"] == 29 or e["to"] == 29 or
                e["from"] in adj.get(29, set()) or e["to"] in adj.get(29, set())
            ) else (0.3 if (
                groups.get(e["from"], "bridge") == "spirit" or
                groups.get(e["to"], "bridge") == "spirit"
            ) else 1.0),
        },
    }

    print(f"\n  Damping d={damp}:")

    basins_seen = set()
    for name, config in ROUTE_CONFIGS.items():
        mod_edges = copy.deepcopy(raw_edges)
        for e in mod_edges:
            e["w0"] = config["rule"](e, raw_nodes, groups)
        engine = make_engine_from_modified(raw_nodes, mod_edges, damping=damp, seed=42)
        apply_standard_injection(engine)
        analysis = run_and_analyze(engine, steps=STEPS)
        basin = analysis["dominant_basin"]
        basins_seen.add(basin)

        print(f"    {name:20s}: basin={format_basin(basin, labels):25s} "
              f"frac={analysis['dominant_basin_frac']:.3f} "
              f"iton={analysis['iton_score']:.3f} "
              f"coh={analysis['coherence']:.4f}")

        results[name] = {
            "basin": basin,
            "basin_label": labels.get(basin, "?"),
            "basin_frac": analysis["dominant_basin_frac"],
            "iton": analysis["iton_score"],
            "coherence": analysis["coherence"],
            "top5": analysis["top5_rho"],
            "description": config["description"],
        }

    n_distinct = len(basins_seen)
    print(f"\n  ROUTER SUMMARY: {n_distinct} distinct basins reached from {len(ROUTE_CONFIGS)} configs")
    print(f"  Basins: {[format_basin(b, labels) for b in sorted(basins_seen)]}")

    # Test at higher damping too
    for damp2 in [5.0, 20.0]:
        hi_basins = set()
        for name, config in ROUTE_CONFIGS.items():
            mod_edges = copy.deepcopy(raw_edges)
            for e in mod_edges:
                e["w0"] = config["rule"](e, raw_nodes, groups)
            engine = make_engine_from_modified(raw_nodes, mod_edges, damping=damp2, seed=42)
            apply_standard_injection(engine)
            analysis = run_and_analyze(engine, steps=STEPS)
            basin = analysis["dominant_basin"]
            hi_basins.add(basin)
        print(f"  d={damp2}: {len(hi_basins)} distinct basins: "
              f"{[format_basin(b, labels) for b in sorted(hi_basins)]}")
        results[f"d{damp2}_distinct"] = len(hi_basins)
        results[f"d{damp2}_basins"] = sorted(hi_basins)

    return {"gate": "ROUTER", "results": results, "distinct_basins_d02": n_distinct}


# ===================================================================
# GATE 5: RELAY CHAIN (persistent directional transport)
# ===================================================================
# Uses REVERSE sequential gap=100 to build maximum relay network.
# Compares with forward, simultaneous, and spread.
# Shows that ordering controls relay persistence under damping.
# ===================================================================

def gate_5_relay_chain():
    """Relay chain via reverse sequential injection."""
    print("\n" + "=" * 70)
    print("  GATE 5: RELAY CHAIN (persistent directional transport)")
    print("  Compares 4 injection orderings at d=20 (stress)")
    print("  Expected: REVERSE gap=100 >> others for iton")
    print("=" * 70)

    labels = get_labels(load_default_graph()[0])
    damp = 20.0
    gap = 100
    results = {}

    # --- SIMULTANEOUS (standard) ---
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    apply_standard_injection(engine)
    r = run_and_analyze(engine, steps=STEPS)
    print(f"\n  SIMULTANEOUS: basin={format_basin(r['dominant_basin'], labels)}, "
          f"iton={r['iton_score']:.3f}, n_pass={r['n_pass']}")
    results["SIMULTANEOUS"] = {
        "basin": r["dominant_basin"], "iton": r["iton_score"],
        "n_pass": r["n_pass"], "n_sources": r["n_sources"], "n_sinks": r["n_sinks"],
    }

    # --- FORWARD SEQUENTIAL gap=100 ---
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    for label, amount in STANDARD_INJECTIONS:
        engine.inject(label, amount)
        engine.run(gap)
    r = run_and_analyze(engine, steps=STEPS)
    print(f"  FORWARD seq gap={gap}: basin={format_basin(r['dominant_basin'], labels)}, "
          f"iton={r['iton_score']:.3f}, n_pass={r['n_pass']}")
    results["FORWARD"] = {
        "basin": r["dominant_basin"], "iton": r["iton_score"],
        "n_pass": r["n_pass"], "n_sources": r["n_sources"], "n_sinks": r["n_sinks"],
    }

    # --- REVERSE SEQUENTIAL gap=100 ---
    reverse_inj = list(reversed(STANDARD_INJECTIONS))
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    for label, amount in reverse_inj:
        engine.inject(label, amount)
        engine.run(gap)
    r = run_and_analyze(engine, steps=STEPS)
    print(f"  REVERSE  seq gap={gap}: basin={format_basin(r['dominant_basin'], labels)}, "
          f"iton={r['iton_score']:.3f}, n_pass={r['n_pass']}")
    results["REVERSE"] = {
        "basin": r["dominant_basin"], "iton": r["iton_score"],
        "n_pass": r["n_pass"], "n_sources": r["n_sources"], "n_sinks": r["n_sinks"],
    }

    # --- SPREAD (uniform across all 140) ---
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    per_node = 150.0 / 140.0
    for n in engine.physics.nodes:
        engine.inject_by_id(n["id"], per_node)
    r = run_and_analyze(engine, steps=STEPS)
    print(f"  SPREAD uniform:    basin={format_basin(r['dominant_basin'], labels)}, "
          f"iton={r['iton_score']:.3f}, n_pass={r['n_pass']}")
    results["SPREAD"] = {
        "basin": r["dominant_basin"], "iton": r["iton_score"],
        "n_pass": r["n_pass"], "n_sources": r["n_sources"], "n_sinks": r["n_sinks"],
    }

    # --- REVERSE with additional gap values to find sweet spot ---
    print(f"\n  REVERSE ordering gap sweep at d={damp}:")
    gap_sweep = {}
    for g in [25, 50, 75, 100, 125, 150, 200]:
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        for label, amount in reverse_inj:
            engine.inject(label, amount)
            engine.run(g)
        r = run_and_analyze(engine, steps=STEPS)
        gap_sweep[g] = {
            "basin": r["dominant_basin"], "iton": r["iton_score"],
            "n_pass": r["n_pass"],
        }
        print(f"    gap={g:4d}: iton={r['iton_score']:.3f}, "
              f"n_pass={r['n_pass']}, basin={format_basin(r['dominant_basin'], labels)}")

    results["gap_sweep"] = gap_sweep
    best_gap = max(gap_sweep, key=lambda g: gap_sweep[g]["iton"])
    print(f"  Best gap: {best_gap} (iton={gap_sweep[best_gap]['iton']:.3f})")

    # Compare REVERSE at different damping values
    print(f"\n  REVERSE gap=100 across damping sweep:")
    damp_sweep = {}
    for d in [0.2, 1.0, 5.0, 10.0, 20.0, 40.0, 55.0]:
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=d, rng_seed=42)
        for label, amount in reverse_inj:
            engine.inject(label, amount)
            engine.run(100)
        r = run_and_analyze(engine, steps=STEPS)
        damp_sweep[d] = {
            "basin": r["dominant_basin"], "iton": r["iton_score"],
            "n_pass": r["n_pass"],
        }
        print(f"    d={d:5.1f}: iton={r['iton_score']:.3f}, "
              f"n_pass={r['n_pass']}, basin={format_basin(r['dominant_basin'], labels)}")

    results["damp_sweep"] = damp_sweep

    return {"gate": "RELAY_CHAIN", "results": results}


# ===================================================================
# GATE 6: 2-BIT MUX (injection protocol x routing = 4 outputs)
# ===================================================================
# Bit 0: Injection ordering (FORWARD=0, REVERSE=1)
# Bit 1: Routing config (UNIFORM=0, SPIRIT_3x=1)
# Output: 4 distinct {basin, iton} states
# ===================================================================

def gate_6_mux():
    """2-bit multiplexer combining injection order and routing."""
    print("\n" + "=" * 70)
    print("  GATE 6: 2-BIT MUX (injection x routing = 4 outputs)")
    print("  Bit 0: Injection ordering (FORWARD=0, REVERSE=1)")
    print("  Bit 1: Routing (UNIFORM=0, SPIRIT_3x=1)")
    print("  Expected: 4 distinct {basin, iton} states")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)

    gap = 100
    damp = 20.0
    results = {}

    forward_inj = STANDARD_INJECTIONS
    reverse_inj = list(reversed(STANDARD_INJECTIONS))

    # Build spirit highway edges
    spirit_edges, _ = set_spirit_highway(raw_edges, w0_spirit=3.0, raw_nodes=raw_nodes)

    configs = {
        "00_fwd_uniform": {"inj": forward_inj, "edges": raw_edges, "desc": "FORWARD + UNIFORM"},
        "01_fwd_spirit":  {"inj": forward_inj, "edges": spirit_edges, "desc": "FORWARD + SPIRIT_3x"},
        "10_rev_uniform": {"inj": reverse_inj, "edges": raw_edges, "desc": "REVERSE + UNIFORM"},
        "11_rev_spirit":  {"inj": reverse_inj, "edges": spirit_edges, "desc": "REVERSE + SPIRIT_3x"},
    }

    print(f"\n  Damping d={damp}, gap={gap}:")

    mux_basins = set()
    mux_states = {}
    for name, cfg in configs.items():
        engine = make_engine_from_modified(raw_nodes, cfg["edges"], damping=damp, seed=42)
        for label, amount in cfg["inj"]:
            engine.inject(label, amount)
            engine.run(gap)
        analysis = run_and_analyze(engine, steps=STEPS)
        basin = analysis["dominant_basin"]
        mux_basins.add(basin)

        state_key = (basin, round(analysis["iton_score"], 3))
        print(f"    {name}: basin={format_basin(basin, labels):25s} "
              f"iton={analysis['iton_score']:.3f} coh={analysis['coherence']:.4f}")

        mux_states[name] = {
            "basin": basin,
            "basin_label": labels.get(basin, "?"),
            "iton": analysis["iton_score"],
            "coherence": analysis["coherence"],
            "n_pass": analysis["n_pass"],
            "top5": analysis["top5_rho"],
        }

    # Check how many distinct outputs
    output_signatures = set()
    for name, state in mux_states.items():
        sig = (state["basin"], round(state["iton"], 2))
        output_signatures.add(sig)

    n_distinct = len(output_signatures)
    n_distinct_basins = len(mux_basins)
    print(f"\n  MUX SUMMARY at d={damp}:")
    print(f"    Distinct basins: {n_distinct_basins}")
    print(f"    Distinct (basin, iton) signatures: {n_distinct}")
    print(f"    Basins: {[format_basin(b, labels) for b in sorted(mux_basins)]}")

    results["d20"] = {
        "states": mux_states,
        "n_distinct_basins": n_distinct_basins,
        "n_distinct_signatures": n_distinct,
    }

    # Test at d=0.2 for comparison
    damp2 = 0.2
    print(f"\n  Damping d={damp2}, gap={gap}:")
    mux_basins2 = set()
    mux_states2 = {}
    for name, cfg in configs.items():
        engine = make_engine_from_modified(raw_nodes, cfg["edges"], damping=damp2, seed=42)
        for label, amount in cfg["inj"]:
            engine.inject(label, amount)
            engine.run(gap)
        analysis = run_and_analyze(engine, steps=STEPS)
        basin = analysis["dominant_basin"]
        mux_basins2.add(basin)
        print(f"    {name}: basin={format_basin(basin, labels):25s} "
              f"iton={analysis['iton_score']:.3f} coh={analysis['coherence']:.4f}")
        mux_states2[name] = {
            "basin": basin,
            "basin_label": labels.get(basin, "?"),
            "iton": analysis["iton_score"],
            "coherence": analysis["coherence"],
        }

    results["d02"] = {
        "states": mux_states2,
        "n_distinct_basins": len(mux_basins2),
    }

    return {"gate": "MUX_2BIT", "results": results}


# ===================================================================
# GATE 7: COHERENCE SWITCH
# ===================================================================
# Input: Injection completeness (5 nodes vs 140 nodes)
# Output: Coherence = LOW (point injection) or HIGH (spread injection)
# This is a clean on/off switch for phase alignment control.
# ===================================================================

def gate_7_coherence_switch():
    """Coherence switch via injection completeness."""
    print("\n" + "=" * 70)
    print("  GATE 7: COHERENCE SWITCH")
    print("  Input: Injection completeness (5 vs 140 nodes)")
    print("  Output: LOW coherence (5-node) vs HIGH coherence (140-node)")
    print("=" * 70)

    labels = get_labels(load_default_graph()[0])
    results = {}

    test_damps = [0.2, 5.0, 20.0, 55.0]

    for damp in test_damps:
        print(f"\n  Damping d={damp}:")

        # --- 5-node injection (standard) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)
        r_point = run_and_analyze(engine, steps=STEPS)

        # --- 140-node injection (spread, same total energy) ---
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        per_node = 150.0 / 140.0
        for n in engine.physics.nodes:
            engine.inject_by_id(n["id"], per_node)
        r_spread = run_and_analyze(engine, steps=STEPS)

        delta_coh = r_spread["coherence"] - r_point["coherence"]
        switched = (r_spread["coherence"] > 0.99 and r_point["coherence"] < 0.99)

        print(f"    POINT  (5 nodes):   coh={r_point['coherence']:.4f}, "
              f"basin={format_basin(r_point['dominant_basin'], labels)}")
        print(f"    SPREAD (140 nodes): coh={r_spread['coherence']:.4f}, "
              f"basin={format_basin(r_spread['dominant_basin'], labels)}")
        print(f"    Delta coherence: {delta_coh:+.4f}  "
              f"Switch {'ON' if switched else 'OFF'}")

        results[damp] = {
            "point_coherence": r_point["coherence"],
            "spread_coherence": r_spread["coherence"],
            "delta": delta_coh,
            "switched": switched,
            "point_basin": r_point["dominant_basin"],
            "spread_basin": r_spread["dominant_basin"],
        }

    passed = sum(1 for r in results.values() if r["switched"])
    total = len(results)
    print(f"\n  COHERENCE SWITCH SUMMARY: {passed}/{total} damping values have clean switch")

    return {"gate": "COHERENCE_SWITCH", "results": results, "pass_rate": passed / total}


# ===================================================================
# INTEGRATION TEST: Full Logic Chain
# ===================================================================
# NOT(highway) -> routes to basin A
# AND(injection, highway) -> routes to basin B
# Uses the outputs to verify composability of primitives
# ===================================================================

def integration_test():
    """Verify gates compose: NOT + AND + routing in sequence."""
    print("\n" + "=" * 70)
    print("  INTEGRATION TEST: Composable Logic Chain")
    print("  Verifies that NOT/AND/routing primitives compose")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    damp = 0.2
    results = {}

    # Step 1: Run NOT gate (OFF -> metatron, ON -> grail)
    print("\n  Step 1: NOT gate checks")
    engine_off = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    apply_standard_injection(engine_off)
    r_off = run_and_analyze(engine_off, steps=STEPS)

    mod_edges, _ = set_spirit_highway(raw_edges, w0_spirit=3.0, raw_nodes=raw_nodes)
    engine_on = make_engine_from_modified(raw_nodes, mod_edges, damping=damp, seed=42)
    apply_standard_injection(engine_on)
    r_on = run_and_analyze(engine_on, steps=STEPS)

    not_ok = (r_off["dominant_basin"] != r_on["dominant_basin"])
    print(f"  NOT: OFF={format_basin(r_off['dominant_basin'], labels)}, "
          f"ON={format_basin(r_on['dominant_basin'], labels)}, {'PASS' if not_ok else 'FAIL'}")

    # Step 2: Verify AND (need both injection + highway for grail)
    print("  Step 2: AND gate checks")
    engine_no_inj = make_engine_from_modified(raw_nodes, mod_edges, damping=damp, seed=42)
    # No injection
    r_no_inj = run_and_analyze(engine_no_inj, steps=STEPS)
    and_ok = (r_on["dominant_basin"] == 1 and r_no_inj["dominant_basin"] != 1)
    print(f"  AND: inj+hwy={format_basin(r_on['dominant_basin'], labels)}, "
          f"hwy_only={format_basin(r_no_inj['dominant_basin'], labels)}, "
          f"{'PASS' if and_ok else 'FAIL'}")

    # Step 3: Routing orthogonality (do different w0 configs give different basins?)
    print("  Step 3: Routing orthogonality")
    basins_set = set()
    configs_tested = 0
    for w0_spirit in [0.3, 1.0, 3.0]:
        me, _ = set_spirit_highway(raw_edges, w0_spirit=w0_spirit, raw_nodes=raw_nodes)
        eng = make_engine_from_modified(raw_nodes, me, damping=damp, seed=42)
        apply_standard_injection(eng)
        r = run_and_analyze(eng, steps=STEPS)
        basins_set.add(r["dominant_basin"])
        configs_tested += 1
        print(f"    spirit_w0={w0_spirit:.1f}: basin={format_basin(r['dominant_basin'], labels)}")

    routing_ok = len(basins_set) >= 2
    print(f"  ROUTING: {len(basins_set)} distinct basins from {configs_tested} configs "
          f"{'PASS' if routing_ok else 'FAIL'}")

    # Step 4: Coherence switch independence
    print("  Step 4: Coherence switch")
    engine_point = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    apply_standard_injection(engine_point)
    r_point = run_and_analyze(engine_point, steps=STEPS)

    engine_spread = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    for n in engine_spread.physics.nodes:
        engine_spread.inject_by_id(n["id"], 150.0 / 140.0)
    r_spread = run_and_analyze(engine_spread, steps=STEPS)
    coh_ok = (r_spread["coherence"] > 0.99 and r_point["coherence"] < 0.99)
    print(f"  COHERENCE: point={r_point['coherence']:.4f}, "
          f"spread={r_spread['coherence']:.4f}, "
          f"{'PASS' if coh_ok else 'FAIL'}")

    all_pass = not_ok and and_ok and routing_ok and coh_ok
    print(f"\n  INTEGRATION: {'ALL PASS' if all_pass else 'PARTIAL FAIL'} "
          f"({'4/4' if all_pass else f'{sum([not_ok, and_ok, routing_ok, coh_ok])}/4'})")

    results = {
        "not_gate": not_ok,
        "and_gate": and_ok,
        "routing_orthogonality": routing_ok,
        "coherence_switch": coh_ok,
        "all_pass": all_pass,
        "basins_off": r_off["dominant_basin"],
        "basins_on": r_on["dominant_basin"],
        "n_routing_basins": len(basins_set),
    }

    return {"test": "INTEGRATION", "results": results}


# ===================================================================
# MAIN — Run all gates and store results
# ===================================================================

def main():
    print("=" * 70)
    print("  SOL LOGIC GATE & SIGNAL ROUTER -- EXPERIMENT 8")
    print("  7 constructs + integration test")
    print("=" * 70)

    t0_global = time.time()
    all_results = {}
    trial_count = 0

    # Gate 1: NOT
    g1 = gate_1_not()
    all_results["gate_1_not"] = g1
    # 2 trials per damping x 3 dampings = 6
    trial_count += 6

    # Gate 2: AND
    g2 = gate_2_and()
    all_results["gate_2_and"] = g2
    # 4 trials per damping x 3 dampings = 12
    trial_count += 12

    # Gate 3: OR
    g3 = gate_3_or()
    all_results["gate_3_or"] = g3
    # 4 trials x 3 dampings = 12
    trial_count += 12

    # Gate 4: Signal Router
    g4 = gate_4_signal_router()
    all_results["gate_4_router"] = g4
    # 5 configs x 1 primary + 5x2 secondary = 15
    trial_count += 15

    # Gate 5: Relay Chain
    g5 = gate_5_relay_chain()
    all_results["gate_5_relay"] = g5
    # 4 orderings + 7 gap sweep + 7 damp sweep = 18
    trial_count += 18

    # Gate 6: 2-bit MUX
    g6 = gate_6_mux()
    all_results["gate_6_mux"] = g6
    # 4 configs x 2 dampings = 8
    trial_count += 8

    # Gate 7: Coherence Switch
    g7 = gate_7_coherence_switch()
    all_results["gate_7_coherence"] = g7
    # 2 trials x 4 dampings = 8
    trial_count += 8

    # Integration test
    ig = integration_test()
    all_results["integration"] = ig
    # ~8 trials
    trial_count += 8

    elapsed = time.time() - t0_global

    # ---- Summary ----
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    print(f"  Total trials: ~{trial_count}")
    print(f"  Total time:   {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print()

    # Gate results summary
    summary_lines = [
        f"  Gate 1 NOT:       pass_rate={g1['pass_rate']:.0%}",
        f"  Gate 2 AND:       strict={g2['strict_pass_rate']:.0%}, relaxed={g2['relaxed_pass_rate']:.0%}",
        f"  Gate 3 OR:        pass_rate={g3['pass_rate']:.0%}",
        f"  Gate 4 ROUTER:    {g4['distinct_basins_d02']} distinct basins",
        f"  Gate 5 RELAY:     best_iton={max(r['iton'] for r in g5['results'].values() if isinstance(r, dict) and 'iton' in r):.3f}",
        f"  Gate 6 MUX:       {g6['results']['d20']['n_distinct_signatures']} distinct signatures",
        f"  Gate 7 COHERENCE: pass_rate={g7['pass_rate']:.0%}",
        f"  Integration:      {'ALL PASS' if ig['results']['all_pass'] else 'PARTIAL FAIL'}",
    ]
    for line in summary_lines:
        print(line)

    # ---- Save ----
    out_path = _SOL_ROOT / "data" / "logic_gate_router.json"
    out_path.parent.mkdir(exist_ok=True)

    # Convert numpy types for JSON serialization
    def convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, set):
            return sorted(obj)
        return obj

    def sanitize(d):
        if isinstance(d, dict):
            return {str(k): sanitize(v) for k, v in d.items()}
        if isinstance(d, list):
            return [sanitize(v) for v in d]
        return convert(d)

    payload = sanitize({
        "experiment": "Logic Gate & Signal Router (Experiment 8)",
        "engine_sha256": "5316e4fd6713b2d5e2dd4999780b5f7871c0a7b1c90e8f151698805653562eef",
        "graph_sha256": "b9800d5313886818c7c1980829e1ca5da7d63d9e2218e36c020df80db19b06fb",
        "total_trials": trial_count,
        "total_seconds": elapsed,
        "gates": all_results,
    })

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  Data saved to {out_path}")
    print(f"  File size: {out_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
