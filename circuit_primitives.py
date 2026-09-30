#!/usr/bin/env python3
"""
SOL Circuit Primitives — Experiment 9
=======================================

Answers the 4 remaining open questions from Experiment 8 and validates
the hardware-analog mapping suggested by mixed-signal circuit analysis.

PROBES:
  Probe 1 (Q1): MULTI-BASIN ROUTER — Combine w0 + injection protocol + cold
                 nodes to achieve 4+ independently addressable basins.
  Probe 2 (Q2): CLOCK SIGNAL RELAY — Periodic re-injection ("clock") to
                 sustain relay transport at d > 1.0.
  Probe 3 (Q3): GATE CASCADING — Read basin from stage 1, feed as control
                 signal into stage 2 (Schmitt trigger / threshold logic).
  Probe 4 (Q4): REGIME EXPANSION — Aggressive w0 asymmetry + spirit-layer
                 amplification to push gate operation above d=10.
  Probe 5:      SOL ISA VALIDATION — Test inject/hold/settle/readTick as
                 an instruction set (inspired by mixed-signal circuit ISA).
  Probe 6:      ANALOG FIDELITY — Measure how precisely conductance * delta_p
                 predicts actual flux (validates hardware-analog mapping:
                 I_ij = g_ij * h(psi) * (V_i - V_j)).

ENGINE: tools/sol-core/sol_engine.py (IMMUTABLE)
GRAPH:  tools/sol-core/default_graph.json (IMMUTABLE — modified copies only)

Outputs: data/circuit_primitives.json
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

from sol_engine import SOLEngine, snapshot_state, restore_state

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

TOTAL_ENERGY = 150.0

NODE_IDS = {
    "grail": 1, "christ": 2, "orion": 5, "numis'om": 7,
    "metatron": 9, "maia nartoomid": 14, "christic": 22,
    "light codes": 23, "pyramid": 29, "thothhorra": 31,
    "par": 79, "numis'om_80": 80, "johannine grove": 82,
    "mystery school": 89, "christine hayes": 90,
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
    adj = defaultdict(set)
    for e in raw_edges:
        adj[e["from"]].add(e["to"])
        adj[e["to"]].add(e["from"])
    return adj


def make_engine(raw_nodes, raw_edges, damping, seed=42):
    return SOLEngine.from_graph(
        raw_nodes, raw_edges,
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed
    )


def apply_standard_injection(engine):
    for label, amount in STANDARD_INJECTIONS:
        engine.inject(label, amount)


def set_edge_weights(raw_edges, raw_nodes, rule_fn):
    """Apply a weight rule to all edges. Returns modified copy + count."""
    groups = get_groups(raw_nodes)
    edges = copy.deepcopy(raw_edges)
    count = 0
    for e in edges:
        new_w0 = rule_fn(e, groups)
        if new_w0 != 1.0:
            count += 1
        e["w0"] = new_w0
    return edges, count


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def analyze_trial(engine, rho_samples):
    """Compute mode count, coherence, iton score."""
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
    analysis["dominant_basin_frac"] = (
        basin_visits.get(dominant, 0) / max(1, sum(basin_visits.values()))
        if dominant else 0.0
    )
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
    return f"{labels.get(nid, '?')}[{nid}]"


# ===================================================================
# PROBE 1 (Q1): MULTI-BASIN ROUTER
# ===================================================================
# Combine 3 independent control dimensions:
#   Dim 1: w0 weight vector (UNIFORM vs SPIRIT_3x)
#   Dim 2: injection protocol (STANDARD vs REVERSE_SEQ)
#   Dim 3: injection target (standard 5 vs cold nodes)
# 2 x 2 x 2 = 8 configurations -> goal: 4+ distinct basins
#
# Hardware analog: programmable crossbar (w0) + pulse generator
#   (injection protocol) + address bus (injection target)
# ===================================================================

def probe_1_multi_basin_router():
    """Combine 3 control dimensions for maximal basin addressability."""
    print("\n" + "=" * 70)
    print("  PROBE 1 (Q1): MULTI-BASIN ROUTER")
    print("  3 control dimensions x 2 states each = 8 configs")
    print("  Goal: 4+ distinct basin addresses")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    adj = get_adjacency(raw_edges)

    # Select 5 peripheral nodes by lowest degree as cold injection targets
    degrees = get_degrees(raw_edges)
    degree_sorted = sorted(degrees.items(), key=lambda x: x[1])
    # Filter out standard injection nodes and take lowest-degree 5
    standard_ids = {1, 2, 9, 23, 29}
    cold_5 = [nid for nid, deg in degree_sorted if nid not in standard_ids][:5]
    if not cold_5:
        cold_5 = [nid for nid, deg in degree_sorted][:5]
    cold_labels = [labels.get(nid, "?") for nid in cold_5]
    print(f"  Cold nodes (low-degree): {list(zip(cold_5, cold_labels))}")

    # Weight configs
    def spirit_3x(e, grps):
        if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
            return 3.0
        return 1.0

    def pyramid_suppress(e, grps):
        # Suppress pyramid neighborhood, amplify grail
        target_29 = adj.get(29, set())
        if e["from"] == 29 or e["to"] == 29 or e["from"] in target_29 or e["to"] in target_29:
            return 0.3
        target_1 = adj.get(1, set())
        if e["from"] == 1 or e["to"] == 1 or e["from"] in target_1 or e["to"] in target_1:
            return 3.0
        return 1.0

    def hub_wall(e, grps):
        if e["from"] in (79, 82) or e["to"] in (79, 82):
            return 0.1
        return 2.0

    weight_configs = {
        "UNIFORM": lambda e, g: 1.0,
        "SPIRIT_3x": spirit_3x,
        "PYRAMID_SUP": pyramid_suppress,
        "HUB_WALL": hub_wall,
    }

    # Injection configs
    def inj_standard(engine):
        apply_standard_injection(engine)

    def inj_reverse_seq(engine, gap=100):
        for label, amount in reversed(STANDARD_INJECTIONS):
            engine.inject(label, amount)
            engine.run(gap)

    def inj_cold(engine):
        per_cold = TOTAL_ENERGY / 5.0
        for nid in cold_5:
            engine.inject_by_id(nid, per_cold)

    def inj_cold_seq(engine, gap=100):
        per_cold = TOTAL_ENERGY / 5.0
        for nid in cold_5:
            engine.inject_by_id(nid, per_cold)
            engine.run(gap)

    inj_configs = {
        "STANDARD": inj_standard,
        "REV_SEQ": inj_reverse_seq,
        "COLD": inj_cold,
        "COLD_SEQ": inj_cold_seq,
    }

    damp = 0.2
    results = {}
    all_basins = set()
    trial_count = 0

    print(f"\n  Damping d={damp}, {len(weight_configs)}x{len(inj_configs)}="
          f"{len(weight_configs)*len(inj_configs)} configs:")

    for w_name, w_fn in weight_configs.items():
        mod_edges, n_mod = set_edge_weights(raw_edges, raw_nodes, w_fn)
        for i_name, i_fn in inj_configs.items():
            config_name = f"{w_name}+{i_name}"
            engine = make_engine(raw_nodes, mod_edges, damping=damp, seed=42)
            i_fn(engine)
            analysis = run_and_analyze(engine, steps=STEPS)
            basin = analysis["dominant_basin"]
            all_basins.add(basin)
            trial_count += 1

            print(f"    {config_name:30s}: basin={format_basin(basin, labels):25s} "
                  f"iton={analysis['iton_score']:.3f} coh={analysis['coherence']:.4f}")

            results[config_name] = {
                "basin": basin,
                "basin_label": labels.get(basin, "?"),
                "iton": analysis["iton_score"],
                "coherence": analysis["coherence"],
            }

    n_distinct = len(all_basins)
    print(f"\n  MULTI-BASIN SUMMARY: {n_distinct} distinct basins from "
          f"{trial_count} configs")
    print(f"  Basins: {sorted([format_basin(b, labels) for b in all_basins])}")

    # Extra: test at d=5.0 to see if basin count holds
    print(f"\n  Checking at d=5.0...")
    basins_d5 = set()
    for w_name, w_fn in weight_configs.items():
        mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, w_fn)
        for i_name, i_fn in inj_configs.items():
            engine = make_engine(raw_nodes, mod_edges, damping=5.0, seed=42)
            i_fn(engine)
            analysis = run_and_analyze(engine, steps=STEPS)
            basins_d5.add(analysis["dominant_basin"])
            trial_count += 1
    print(f"  d=5.0: {len(basins_d5)} distinct basins: "
          f"{sorted([format_basin(b, labels) for b in basins_d5])}")

    return {
        "probe": "MULTI_BASIN_ROUTER",
        "results": results,
        "n_distinct_d02": n_distinct,
        "basins_d02": sorted([b for b in all_basins if b is not None]),
        "n_distinct_d5": len(basins_d5),
        "basins_d5": sorted([b for b in basins_d5 if b is not None]),
        "cold_nodes": cold_5,
        "trial_count": trial_count,
    }


# ===================================================================
# PROBE 2 (Q2): CLOCK SIGNAL RELAY
# ===================================================================
# Test whether periodic re-injection ("clock signal") sustains relay
# transport at d > 1.0 where single-injection relays dissipate.
#
# Hardware analog: the "synth + sequencer" concept — analog state
# evolution with digital temporal control. The clock is the sequencer.
#
# Protocol: inject standard, then every N steps re-inject a small
# "maintenance pulse." Measure iton score at steady state.
# ===================================================================

def probe_2_clock_signal():
    """Periodic re-injection to sustain relay transport."""
    print("\n" + "=" * 70)
    print("  PROBE 2 (Q2): CLOCK SIGNAL RELAY")
    print("  Periodic re-injection sustains transport at d > 1.0?")
    print("  Clock periods: 25, 35, 50, 70, 100 steps")
    print("  Pulse sizes: 5%, 10%, 20% of original")
    print("=" * 70)

    labels = get_labels(load_default_graph()[0])
    results = {}
    trial_count = 0

    test_damps = [5.0, 10.0, 20.0]
    clock_periods = [25, 35, 50, 70, 100]
    pulse_fracs = [0.05, 0.10, 0.20]
    total_steps = 2000  # Run longer to test sustainability

    for damp in test_damps:
        print(f"\n  Damping d={damp}:")

        # Baseline: single injection, no clock
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)
        # Measure iton at different time windows
        baseline_itons = []
        for window in range(4):
            rho_samples = []
            for s in range(500):
                engine.step()
                if s % SAMPLE_INTERVAL == 0:
                    rho_samples.append([n["rho"] for n in engine.physics.nodes])
            if rho_samples:
                analysis = analyze_trial(engine, rho_samples)
                baseline_itons.append(analysis["iton_score"])
        print(f"  BASELINE (no clock): itons by window = "
              f"{[f'{x:.3f}' for x in baseline_itons]}")
        results[f"d{damp}_baseline"] = baseline_itons
        trial_count += 1

        # Clock signal tests
        best_iton = 0.0
        best_config = None

        for period in clock_periods:
            for pulse_frac in pulse_fracs:
                engine = SOLEngine.from_default_graph(
                    dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42
                )
                apply_standard_injection(engine)
                pulse_amount = TOTAL_ENERGY * pulse_frac

                # Run with clock
                iton_windows = []
                for window in range(4):
                    rho_samples = []
                    for s in range(500):
                        engine.step()
                        # Re-inject on clock tick
                        if s > 0 and s % period == 0:
                            for label, amount in STANDARD_INJECTIONS:
                                engine.inject(label, amount * pulse_frac)
                        if s % SAMPLE_INTERVAL == 0:
                            rho_samples.append([n["rho"] for n in engine.physics.nodes])
                    if rho_samples:
                        analysis = analyze_trial(engine, rho_samples)
                        iton_windows.append(analysis["iton_score"])

                # Use last window as steady-state
                steady_iton = iton_windows[-1] if iton_windows else 0.0
                avg_iton = float(np.mean(iton_windows)) if iton_windows else 0.0
                trial_count += 1

                if steady_iton > best_iton:
                    best_iton = steady_iton
                    best_config = (period, pulse_frac)

                config_key = f"d{damp}_p{period}_f{int(pulse_frac*100)}"
                results[config_key] = {
                    "iton_windows": iton_windows,
                    "steady_iton": steady_iton,
                    "avg_iton": avg_iton,
                }

        # Print best results per damping
        print(f"  BEST CLOCK at d={damp}: period={best_config[0] if best_config else '?'}, "
              f"pulse={best_config[1]*100 if best_config else '?'}%, "
              f"steady_iton={best_iton:.3f}")

        # Print details for best and for heartbeat-aligned (period=35)
        if best_config:
            key = f"d{damp}_p{best_config[0]}_f{int(best_config[1]*100)}"
            r = results[key]
            print(f"    Windows: {[f'{x:.3f}' for x in r['iton_windows']]}")

        # Heartbeat-aligned results
        for pf in pulse_fracs:
            key = f"d{damp}_p35_f{int(pf*100)}"
            r = results.get(key, {})
            if r:
                print(f"    HEARTBEAT(35) {int(pf*100)}%: "
                      f"itons={[f'{x:.3f}' for x in r.get('iton_windows', [])]}")

    return {
        "probe": "CLOCK_SIGNAL",
        "results": results,
        "trial_count": trial_count,
    }


# ===================================================================
# PROBE 3 (Q3): GATE CASCADING
# ===================================================================
# Test: can basin identity from gate 1 serve as control signal for gate 2?
#
# Stage 1: Run NOT gate (spirit highway ON/OFF) -> read basin
# Stage 2: Based on basin, select injection target for second engine run
#   If basin = grail -> inject pyramid
#   If basin = metatron -> inject christ
# Output: cascaded basin should differ from direct single-stage
#
# Hardware analog: Schmitt trigger / comparator with hysteresis.
#   Stage 1 output crosses threshold -> digital event -> configures stage 2
# ===================================================================

def probe_3_gate_cascading():
    """Test whether gate outputs can drive subsequent gate inputs."""
    print("\n" + "=" * 70)
    print("  PROBE 3 (Q3): GATE CASCADING")
    print("  Stage 1: NOT gate -> read basin")
    print("  Stage 2: basin-dependent injection -> read output")
    print("  Tests multi-stage logic circuits")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)

    results = {}
    trial_count = 0
    damp = 0.2

    # --- Architecture 1: Sequential two-stage ---
    # Stage 1 output (basin ID) -> Stage 2 input (injection target)
    print(f"\n  Architecture 1: Sequential two-stage at d={damp}")
    print("  Stage 1: highway {OFF, ON} -> basin A or B")
    print("  Stage 2: if basin=grail, inject pyramid(50); if basin=metatron, inject christ(50)")

    arch1_results = {}

    for highway_label, highway_on in [("OFF", False), ("ON", True)]:
        # Stage 1
        if highway_on:
            mod_edges = copy.deepcopy(raw_edges)
            for e in mod_edges:
                sg = groups.get(e["from"], "bridge")
                dg = groups.get(e["to"], "bridge")
                if sg == "spirit" or dg == "spirit":
                    e["w0"] = 3.0
            eng1 = make_engine(raw_nodes, mod_edges, damping=damp, seed=42)
        else:
            eng1 = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)

        apply_standard_injection(eng1)
        r1 = run_and_analyze(eng1, steps=STEPS)
        stage1_basin = r1["dominant_basin"]
        trial_count += 1

        # Stage 2: basin-dependent injection
        eng2 = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        if stage1_basin == 1:  # grail -> inject pyramid
            eng2.inject("pyramid", 50.0)
            stage2_input = "pyramid(50)"
        else:  # metatron or other -> inject christ
            eng2.inject("christ", 50.0)
            stage2_input = "christ(50)"

        r2 = run_and_analyze(eng2, steps=STEPS)
        stage2_basin = r2["dominant_basin"]
        trial_count += 1

        print(f"    Highway={highway_label}: "
              f"Stage1={format_basin(stage1_basin, labels)} -> "
              f"inject {stage2_input} -> "
              f"Stage2={format_basin(stage2_basin, labels)}")

        arch1_results[highway_label] = {
            "stage1_basin": stage1_basin,
            "stage2_input": stage2_input,
            "stage2_basin": stage2_basin,
            "different_outputs": None,  # filled below
        }

    # Check if cascading produces different outputs
    off_out = arch1_results["OFF"]["stage2_basin"]
    on_out = arch1_results["ON"]["stage2_basin"]
    cascades = (off_out != on_out)
    arch1_results["OFF"]["different_outputs"] = cascades
    arch1_results["ON"]["different_outputs"] = cascades
    print(f"    Cascading {'PASS' if cascades else 'FAIL'}: "
          f"OFF->{format_basin(off_out, labels)}, ON->{format_basin(on_out, labels)}")

    results["arch1_sequential"] = arch1_results

    # --- Architecture 2: Continuous cascade (shared state) ---
    # Run stage 1, then at step 500 read basin, modify w0 in-place, continue
    print(f"\n  Architecture 2: Continuous cascade (shared state)")
    print("  Run 500 steps, read basin, modify w0, run 500 more")

    arch2_results = {}

    for highway_label, highway_on in [("OFF", False), ("ON", True)]:
        # Build engine
        if highway_on:
            mod_edges = copy.deepcopy(raw_edges)
            for e in mod_edges:
                sg = groups.get(e["from"], "bridge")
                dg = groups.get(e["to"], "bridge")
                if sg == "spirit" or dg == "spirit":
                    e["w0"] = 3.0
            eng = make_engine(raw_nodes, mod_edges, damping=damp, seed=42)
        else:
            eng = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)

        apply_standard_injection(eng)

        # Stage 1: run 500 steps
        rho_samples_1 = []
        basin_visits_1 = defaultdict(int)
        for s in range(1, 501):
            eng.step()
            if s % SAMPLE_INTERVAL == 0:
                m = eng.compute_metrics()
                bid = m["rhoMaxId"]
                if bid is not None:
                    basin_visits_1[bid] = basin_visits_1.get(bid, 0) + 1
                rho_samples_1.append([n["rho"] for n in eng.physics.nodes])

        stage1_basin = max(basin_visits_1, key=basin_visits_1.get) if basin_visits_1 else None

        # Threshold decision (Schmitt trigger analog):
        # If basin is grail -> set pyramid-attract w0
        # If basin is anything else -> set hub-wall w0
        if stage1_basin == 1:  # grail
            for e in eng.physics.edges:
                adj_set = get_adjacency(raw_edges).get(29, set())
                if e["from"] == 29 or e["to"] == 29 or e["from"] in adj_set or e["to"] in adj_set:
                    e["w0"] = 3.0
                else:
                    e["w0"] = 0.5
            reconfigure = "PYRAMID_ATTRACT"
        else:  # metatron or other
            for e in eng.physics.edges:
                if e["from"] in (79, 82) or e["to"] in (79, 82):
                    e["w0"] = 0.1
                else:
                    e["w0"] = 2.0
            reconfigure = "HUB_WALL"

        # Recalculate conductance after w0 change
        eng.physics.update_conductance()

        # Stage 2: run 500 more steps
        rho_samples_2 = []
        basin_visits_2 = defaultdict(int)
        for s in range(1, 501):
            eng.step()
            if s % SAMPLE_INTERVAL == 0:
                m = eng.compute_metrics()
                bid = m["rhoMaxId"]
                if bid is not None:
                    basin_visits_2[bid] = basin_visits_2.get(bid, 0) + 1
                rho_samples_2.append([n["rho"] for n in eng.physics.nodes])

        stage2_basin = max(basin_visits_2, key=basin_visits_2.get) if basin_visits_2 else None
        trial_count += 1

        print(f"    Highway={highway_label}: "
              f"Stage1={format_basin(stage1_basin, labels)} -> "
              f"reconfigure={reconfigure} -> "
              f"Stage2={format_basin(stage2_basin, labels)}")

        arch2_results[highway_label] = {
            "stage1_basin": stage1_basin,
            "reconfigure": reconfigure,
            "stage2_basin": stage2_basin,
        }

    off_out2 = arch2_results["OFF"]["stage2_basin"]
    on_out2 = arch2_results["ON"]["stage2_basin"]
    cascades2 = (off_out2 != on_out2)
    print(f"    Continuous cascade {'PASS' if cascades2 else 'FAIL'}: "
          f"OFF->{format_basin(off_out2, labels)}, ON->{format_basin(on_out2, labels)}")

    results["arch2_continuous"] = arch2_results

    # --- Architecture 3: Three-stage pipeline ---
    print(f"\n  Architecture 3: Three-stage pipeline")
    print("  Stage 1: highway -> basin")
    print("  Stage 2: basin -> injection choice -> basin")
    print("  Stage 3: basin -> w0 choice -> final basin")

    arch3_results = {}

    for highway_label, highway_on in [("OFF", False), ("ON", True)]:
        # Stage 1
        if highway_on:
            mod_edges = copy.deepcopy(raw_edges)
            for e in mod_edges:
                sg = groups.get(e["from"], "bridge")
                dg = groups.get(e["to"], "bridge")
                if sg == "spirit" or dg == "spirit":
                    e["w0"] = 3.0
            eng1 = make_engine(raw_nodes, mod_edges, damping=damp, seed=42)
        else:
            eng1 = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(eng1)
        r1 = run_and_analyze(eng1, steps=300)
        s1_basin = r1["dominant_basin"]
        trial_count += 1

        # Stage 2: basin -> injection
        eng2 = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        if s1_basin == 1:
            eng2.inject("pyramid", 50.0)
            eng2.inject("orion", 30.0)
            s2_input = "pyramid+orion"
        else:
            eng2.inject("christ", 50.0)
            eng2.inject("light codes", 30.0)
            s2_input = "christ+light_codes"
        r2 = run_and_analyze(eng2, steps=300)
        s2_basin = r2["dominant_basin"]
        trial_count += 1

        # Stage 3: basin -> w0
        if s2_basin in (1, 29):  # grail or pyramid related
            w0_rule = lambda e, g: 0.3 if (
                g.get(e["from"], "bridge") == "spirit" or g.get(e["to"], "bridge") == "spirit"
            ) else 1.5
            s3_config = "SPIRIT_SUPPRESS"
        else:
            w0_rule = lambda e, g: 3.0 if (
                g.get(e["from"], "bridge") == "spirit" or g.get(e["to"], "bridge") == "spirit"
            ) else 1.0
            s3_config = "SPIRIT_BOOST"

        mod_edges3, _ = set_edge_weights(raw_edges, raw_nodes, w0_rule)
        eng3 = make_engine(raw_nodes, mod_edges3, damping=damp, seed=42)
        apply_standard_injection(eng3)
        r3 = run_and_analyze(eng3, steps=300)
        s3_basin = r3["dominant_basin"]
        trial_count += 1

        print(f"    Highway={highway_label}: "
              f"S1={format_basin(s1_basin, labels)} -> "
              f"S2({s2_input})={format_basin(s2_basin, labels)} -> "
              f"S3({s3_config})={format_basin(s3_basin, labels)}")

        arch3_results[highway_label] = {
            "stage1": s1_basin,
            "stage2_input": s2_input,
            "stage2": s2_basin,
            "stage3_config": s3_config,
            "stage3": s3_basin,
        }

    off_out3 = arch3_results["OFF"]["stage3"]
    on_out3 = arch3_results["ON"]["stage3"]
    cascades3 = (off_out3 != on_out3)
    print(f"    Three-stage cascade {'PASS' if cascades3 else 'FAIL'}: "
          f"OFF->{format_basin(off_out3, labels)}, ON->{format_basin(on_out3, labels)}")

    results["arch3_pipeline"] = arch3_results
    results["trial_count"] = trial_count

    # Summary
    any_pass = cascades or cascades2 or cascades3
    print(f"\n  CASCADE SUMMARY: arch1={'PASS' if cascades else 'FAIL'}, "
          f"arch2={'PASS' if cascades2 else 'FAIL'}, "
          f"arch3={'PASS' if cascades3 else 'FAIL'}")

    return {
        "probe": "GATE_CASCADING",
        "results": results,
        "cascades_arch1": cascades,
        "cascades_arch2": cascades2,
        "cascades_arch3": cascades3,
    }


# ===================================================================
# PROBE 4 (Q4): REGIME EXPANSION
# ===================================================================
# Can we extend gate operation above d=10 with aggressive w0 asymmetry?
#
# Strategy: compensate for damping by amplifying spirit-highway w0
# progressively (w0=3, 5, 10, 20, 50) to see if the NOT gate can
# push above d=10.
#
# Hardware analog: amplifier gain compensation — as the medium
# attenuates signal, increase amplifier gain to maintain signal integrity.
# ===================================================================

def probe_4_regime_expansion():
    """Push gate operation above d=10 via aggressive w0 amplification."""
    print("\n" + "=" * 70)
    print("  PROBE 4 (Q4): REGIME EXPANSION")
    print("  Test NOT gate with escalating spirit-highway w0")
    print("  Goal: extend gate operation above d=10")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)

    results = {}
    trial_count = 0

    test_damps = [0.2, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 55.0]
    w0_values = [3.0, 5.0, 10.0, 20.0, 50.0, 100.0]

    print(f"\n  NOT gate inversion test across damping x w0:")
    print(f"  {'d':>5s} | {'w0=1 (OFF)':>15s} | " +
          " | ".join(f"w0={w:.0f}" for w in w0_values))
    print("  " + "-" * (25 + 10 * len(w0_values)))

    for damp in test_damps:
        row = f"  {damp:5.1f} |"

        # Baseline (w0=1.0 everywhere = highway OFF)
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)
        r_off = run_and_analyze(engine, steps=STEPS)
        off_basin = r_off["dominant_basin"]
        row += f" {labels.get(off_basin, '?')[:13]:>15s} |"
        trial_count += 1

        damp_results = {"off_basin": off_basin}

        for w0 in w0_values:
            mod_edges = copy.deepcopy(raw_edges)
            for e in mod_edges:
                sg = groups.get(e["from"], "bridge")
                dg = groups.get(e["to"], "bridge")
                if sg == "spirit" or dg == "spirit":
                    e["w0"] = w0
            engine = make_engine(raw_nodes, mod_edges, damping=damp, seed=42)
            apply_standard_injection(engine)
            r_on = run_and_analyze(engine, steps=STEPS)
            on_basin = r_on["dominant_basin"]
            inverted = (on_basin != off_basin)
            marker = "*" if inverted else " "
            row += f" {labels.get(on_basin, '?')[:7]+marker:>9s} |"
            trial_count += 1

            damp_results[f"w0_{w0}"] = {
                "basin": on_basin,
                "inverted": inverted,
                "iton": r_on["iton_score"],
            }

        print(row)
        results[damp] = damp_results

    # Find maximum damping where inversion works for each w0
    print(f"\n  Maximum damping with inversion per w0:")
    for w0 in w0_values:
        max_d = 0
        for damp in test_damps:
            key = f"w0_{w0}"
            if results.get(damp, {}).get(key, {}).get("inverted", False):
                max_d = damp
        print(f"    w0={w0:5.0f}: max inversion damping = {max_d}")

    results["trial_count"] = trial_count

    return {
        "probe": "REGIME_EXPANSION",
        "results": results,
        "trial_count": trial_count,
    }


# ===================================================================
# PROBE 5: SOL ISA VALIDATION
# ===================================================================
# Test the "instruction set" concept from the hardware analysis:
#   INJECT -> HOLD -> SETTLE -> READTICK -> RESET
#
# Validate that these 5 operations compose into reproducible programs.
#
# Hardware analog: digital controller issuing commands to analog fabric.
# The ISA defines the interface between digital control and analog compute.
# ===================================================================

def probe_5_sol_isa():
    """Validate inject/hold/settle/readTick/reset as instruction primitives."""
    print("\n" + "=" * 70)
    print("  PROBE 5: SOL ISA VALIDATION")
    print("  Test: inject -> hold -> settle -> readTick -> reset")
    print("  Validates instruction-level composability")
    print("=" * 70)

    labels = get_labels(load_default_graph()[0])
    results = {}
    trial_count = 0
    damp = 0.2

    # Define ISA operations
    def ISA_INJECT(engine, target, amount):
        """INJECT: add energy to target node."""
        engine.inject(target, amount)
        return {"op": "INJECT", "target": target, "amount": amount}

    def ISA_HOLD(engine, steps):
        """HOLD: run N steps without injection (let dynamics evolve)."""
        engine.run(steps)
        return {"op": "HOLD", "steps": steps}

    def ISA_SETTLE(engine, settle_steps=200):
        """SETTLE: run until energy stabilizes (fixed window)."""
        engine.run(settle_steps)
        return {"op": "SETTLE", "steps": settle_steps}

    def ISA_READTICK(engine):
        """READTICK: sample current state as output."""
        m = engine.compute_metrics()
        states = sorted(
            [(n["id"], n["rho"]) for n in engine.physics.nodes],
            key=lambda x: x[1], reverse=True
        )[:5]
        return {
            "op": "READTICK",
            "basin": m["rhoMaxId"],
            "maxRho": m["maxRho"],
            "mass": m["mass"],
            "entropy": m["entropy"],
            "top5": states,
        }

    def ISA_RESET(engine):
        """RESET: zero out all node rho (cold reset)."""
        for n in engine.physics.nodes:
            n["rho"] = 0.0
            n["p"] = 0.0
        for e in engine.physics.edges:
            e["flux"] = 0.0
        return {"op": "RESET"}

    def ISA_GATE(engine, edges, w0_rule, groups_map):
        """GATE: reprogram w0 weights (psi waveform control)."""
        for e in engine.physics.edges:
            e["w0"] = w0_rule(e, groups_map)
        engine.physics.update_conductance()
        return {"op": "GATE", "rule": "applied"}

    groups_map = get_groups(load_default_graph()[0])

    # --- Program 1: Simple inject-settle-read ---
    print(f"\n  PROGRAM 1: inject -> settle -> readTick")
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    log1 = []
    log1.append(ISA_INJECT(engine, "grail", 40.0))
    log1.append(ISA_INJECT(engine, "metatron", 35.0))
    log1.append(ISA_SETTLE(engine, 500))
    tick1 = ISA_READTICK(engine)
    log1.append(tick1)
    trial_count += 1
    print(f"    basin={format_basin(tick1['basin'], labels)}, "
          f"mass={tick1['mass']:.4f}")
    results["prog1"] = {"log": log1, "output": tick1}

    # --- Program 2: inject -> hold -> inject -> settle -> read ---
    print(f"\n  PROGRAM 2: inject -> hold(100) -> inject -> settle -> readTick")
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    log2 = []
    log2.append(ISA_INJECT(engine, "grail", 40.0))
    log2.append(ISA_HOLD(engine, 100))
    log2.append(ISA_INJECT(engine, "pyramid", 30.0))
    log2.append(ISA_SETTLE(engine, 400))
    tick2 = ISA_READTICK(engine)
    log2.append(tick2)
    trial_count += 1
    print(f"    basin={format_basin(tick2['basin'], labels)}, "
          f"mass={tick2['mass']:.4f}")
    results["prog2"] = {"log": log2, "output": tick2}

    # --- Program 3: inject -> settle -> reset -> inject -> settle -> read ---
    print(f"\n  PROGRAM 3: inject -> settle -> RESET -> inject -> settle -> readTick")
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    log3 = []
    log3.append(ISA_INJECT(engine, "grail", 40.0))
    log3.append(ISA_SETTLE(engine, 300))
    tick3a = ISA_READTICK(engine)
    log3.append(tick3a)
    log3.append(ISA_RESET(engine))
    tick3b = ISA_READTICK(engine)
    log3.append({"reset_check": tick3b})
    log3.append(ISA_INJECT(engine, "christ", 50.0))
    log3.append(ISA_SETTLE(engine, 300))
    tick3c = ISA_READTICK(engine)
    log3.append(tick3c)
    trial_count += 1
    print(f"    Pre-reset: basin={format_basin(tick3a['basin'], labels)}")
    print(f"    Post-reset mass: {tick3b['mass']:.6f}")
    print(f"    Post-inject: basin={format_basin(tick3c['basin'], labels)}")
    results["prog3"] = {
        "pre_reset": tick3a,
        "reset_mass": tick3b["mass"],
        "post_inject": tick3c,
    }

    # --- Program 4: inject -> settle -> GATE -> settle -> read (reprogramming) ---
    print(f"\n  PROGRAM 4: inject -> settle -> GATE(spirit_3x) -> settle -> readTick")
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    log4 = []
    log4.append(ISA_INJECT(engine, "grail", 40.0))
    log4.append(ISA_INJECT(engine, "metatron", 35.0))
    log4.append(ISA_SETTLE(engine, 250))
    tick4a = ISA_READTICK(engine)
    log4.append(tick4a)

    spirit_rule = lambda e, g: 3.0 if (
        g.get(e["from"], "bridge") == "spirit" or g.get(e["to"], "bridge") == "spirit"
    ) else 1.0
    log4.append(ISA_GATE(engine, None, spirit_rule, groups_map))
    log4.append(ISA_SETTLE(engine, 250))
    tick4b = ISA_READTICK(engine)
    log4.append(tick4b)
    trial_count += 1

    basin_shifted = (tick4a["basin"] != tick4b["basin"])
    print(f"    Pre-GATE:  basin={format_basin(tick4a['basin'], labels)}")
    print(f"    Post-GATE: basin={format_basin(tick4b['basin'], labels)} "
          f"{'(SHIFTED!)' if basin_shifted else '(same)'}")
    results["prog4"] = {
        "pre_gate": tick4a,
        "post_gate": tick4b,
        "basin_shifted": basin_shifted,
    }

    # --- Program 5: Full cycle (inject -> hold -> gate -> settle -> read -> reset) x2 ---
    print(f"\n  PROGRAM 5: Full ISA cycle x2 (determinism test)")
    outputs = []
    for run_idx in range(2):
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        ISA_INJECT(engine, "grail", 40.0)
        ISA_INJECT(engine, "metatron", 35.0)
        ISA_HOLD(engine, 100)
        ISA_INJECT(engine, "pyramid", 30.0)
        ISA_GATE(engine, None, spirit_rule, groups_map)
        ISA_SETTLE(engine, 400)
        tick = ISA_READTICK(engine)
        outputs.append(tick)
        trial_count += 1
        print(f"    Run {run_idx+1}: basin={format_basin(tick['basin'], labels)}, "
              f"maxRho={tick['maxRho']:.6f}")

    deterministic = (
        outputs[0]["basin"] == outputs[1]["basin"] and
        abs(outputs[0]["maxRho"] - outputs[1]["maxRho"]) < 1e-10
    )
    print(f"    Determinism: {'PASS' if deterministic else 'FAIL'}")
    results["prog5_determinism"] = deterministic

    # --- Program 6: Clock-driven program (inject every 35 steps = 1 heartbeat) ---
    print(f"\n  PROGRAM 6: Clock program (inject every heartbeat, 10 ticks)")
    engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
    clock_log = []
    for tick_num in range(10):
        ISA_INJECT(engine, "grail", 5.0)  # Small maintenance pulse
        ISA_HOLD(engine, 35)  # One heartbeat period
        tick = ISA_READTICK(engine)
        clock_log.append({
            "tick": tick_num,
            "basin": tick["basin"],
            "mass": tick["mass"],
        })
    trial_count += 1

    basins_visited = set(t["basin"] for t in clock_log)
    print(f"    Basins over 10 ticks: {[format_basin(b, labels) for b in sorted(basins_visited)]}")
    print(f"    Final mass: {clock_log[-1]['mass']:.4f}")
    results["prog6_clock"] = clock_log

    print(f"\n  ISA SUMMARY: {trial_count} programs executed")
    results["trial_count"] = trial_count

    return {
        "probe": "SOL_ISA",
        "results": results,
        "trial_count": trial_count,
    }


# ===================================================================
# PROBE 6: ANALOG FIDELITY
# ===================================================================
# Validate: I_ij = g_ij * h(psi) * (V_i - V_j)
# where engine computes: target_flux = conductance * tension * diode_gain * delta_p
#
# Measure per-edge:
#   predicted = conductance * delta_p  (ignoring tension/diode for simplicity)
#   actual    = e["flux"]
# Compute correlation across all edges at multiple time snapshots.
#
# Hardware analog: validates that SOL is a linear conductance network
# (at each time step), confirming the mixed-signal circuit mapping.
# ===================================================================

def probe_6_analog_fidelity():
    """Validate the conductance * delta_p = flux relationship."""
    print("\n" + "=" * 70)
    print("  PROBE 6: ANALOG FIDELITY")
    print("  Validates: flux ~ conductance * delta_p (hardware mapping)")
    print("  I_ij = g_ij * h(psi) * (V_i - V_j)")
    print("=" * 70)

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)

    results = {}
    trial_count = 0

    test_damps = [0.2, 5.0, 20.0, 55.0]
    snapshot_steps = [10, 50, 100, 200, 500]

    for damp in test_damps:
        print(f"\n  Damping d={damp}:")
        engine = SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damp, rng_seed=42)
        apply_standard_injection(engine)
        trial_count += 1

        damp_results = {}

        for target_step in snapshot_steps:
            # Run to target step
            while engine.step_count < target_step:
                engine.step()

            # Snapshot per-edge: predicted vs actual flux
            predicted = []
            actual = []
            predicted_full = []  # Include tension/diode

            phase = math.cos(engine.physics.phase_cfg["omega"] * engine.physics._t * 10)
            is_surface = phase > -0.2
            is_deep = phase < 0.2

            for e in engine.physics.edges:
                src = engine.physics.node_by_id.get(e["from"])
                dst = engine.physics.node_by_id.get(e["to"])
                if not src or not dst:
                    continue

                # Check awake status
                sg = src.get("group", "bridge")
                dg = dst.get("group", "bridge")
                src_awake = True
                dst_awake = True
                if sg == "tech" and not is_surface:
                    src_awake = False
                if sg == "spirit" and not is_deep:
                    src_awake = False
                if dg == "tech" and not is_surface:
                    dst_awake = False
                if dg == "spirit" and not is_deep:
                    dst_awake = False

                if not src_awake and not dst_awake:
                    continue

                delta_p = src["p"] - dst["p"]
                cond = e.get("conductance", 1.0)

                # Tension
                tension = 1.0
                if sg == "tech" or dg == "tech":
                    tension = 1.2
                if sg == "spirit" or dg == "spirit":
                    tension = 0.8

                # Simple prediction: cond * delta_p
                pred_simple = cond * delta_p
                # Full prediction: cond * tension * delta_p (ignoring diode for non-battery)
                pred_full = cond * tension * delta_p

                actual_flux = e.get("flux", 0.0)

                predicted.append(pred_simple)
                predicted_full.append(pred_full)
                actual.append(actual_flux)

            # Compute correlation
            predicted = np.array(predicted)
            predicted_full = np.array(predicted_full)
            actual = np.array(actual)

            if len(predicted) > 2 and np.std(predicted) > 1e-15 and np.std(actual) > 1e-15:
                r_simple = float(np.corrcoef(predicted, actual)[0, 1])
                r_full = float(np.corrcoef(predicted_full, actual)[0, 1])
            else:
                r_simple = 0.0
                r_full = 0.0

            # Also compute R-squared (explained variance)
            if np.var(actual) > 1e-15:
                ss_res_simple = float(np.sum((actual - predicted) ** 2))
                ss_res_full = float(np.sum((actual - predicted_full) ** 2))
                ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
                r2_simple = 1 - ss_res_simple / ss_tot
                r2_full = 1 - ss_res_full / ss_tot
            else:
                r2_simple = 0.0
                r2_full = 0.0

            print(f"    Step {target_step:4d}: r(simple)={r_simple:+.4f}, "
                  f"r(full)={r_full:+.4f}, "
                  f"R2(simple)={r2_simple:.4f}, R2(full)={r2_full:.4f}, "
                  f"n_edges={len(actual)}")

            damp_results[target_step] = {
                "r_simple": r_simple,
                "r_full": r_full,
                "r2_simple": r2_simple,
                "r2_full": r2_full,
                "n_edges": int(len(actual)),
            }

        results[damp] = damp_results

    # Summary: what fraction of variance does the linear model explain?
    print(f"\n  ANALOG FIDELITY SUMMARY:")
    print(f"  The hardware mapping I_ij = g_ij * h(psi) * (V_i - V_j)")
    print(f"  corresponds to: target_flux = conductance * tension * delta_p")
    all_r2 = []
    for damp, damp_r in results.items():
        for step, step_r in damp_r.items():
            if isinstance(step_r, dict):
                all_r2.append(step_r["r_full"])
    if all_r2:
        print(f"  Mean R2(full): {np.mean(all_r2):.4f}")
        print(f"  Min  R2(full): {np.min(all_r2):.4f}")
        print(f"  Max  R2(full): {np.max(all_r2):.4f}")

    results["trial_count"] = trial_count

    return {
        "probe": "ANALOG_FIDELITY",
        "results": results,
        "trial_count": trial_count,
    }


# ===================================================================
# MAIN
# ===================================================================

def main():
    print("=" * 70)
    print("  SOL CIRCUIT PRIMITIVES -- EXPERIMENT 9")
    print("  6 probes (4 open questions + 2 hardware-analog validations)")
    print("=" * 70)

    t0_global = time.time()
    all_results = {}
    total_trials = 0

    # Probe 1: Multi-basin router
    p1 = probe_1_multi_basin_router()
    all_results["probe_1_multi_basin"] = p1
    total_trials += p1["trial_count"]

    # Probe 2: Clock signal relay
    p2 = probe_2_clock_signal()
    all_results["probe_2_clock"] = p2
    total_trials += p2["trial_count"]

    # Probe 3: Gate cascading
    p3 = probe_3_gate_cascading()
    all_results["probe_3_cascade"] = p3
    total_trials += p3["results"]["trial_count"]

    # Probe 4: Regime expansion
    p4 = probe_4_regime_expansion()
    all_results["probe_4_regime"] = p4
    total_trials += p4["trial_count"]

    # Probe 5: SOL ISA
    p5 = probe_5_sol_isa()
    all_results["probe_5_isa"] = p5
    total_trials += p5["trial_count"]

    # Probe 6: Analog fidelity
    p6 = probe_6_analog_fidelity()
    all_results["probe_6_fidelity"] = p6
    total_trials += p6["trial_count"]

    elapsed = time.time() - t0_global

    # ---- Final Summary ----
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    print(f"  Total trials: ~{total_trials}")
    print(f"  Total time:   {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print()
    print(f"  Probe 1 MULTI-BASIN:  {p1['n_distinct_d02']} basins at d=0.2, "
          f"{p1['n_distinct_d5']} at d=5.0")
    print(f"  Probe 2 CLOCK:        See per-damping results above")
    print(f"  Probe 3 CASCADE:      arch1={'PASS' if p3['cascades_arch1'] else 'FAIL'}, "
          f"arch2={'PASS' if p3['cascades_arch2'] else 'FAIL'}, "
          f"arch3={'PASS' if p3['cascades_arch3'] else 'FAIL'}")
    print(f"  Probe 4 REGIME:       See damping x w0 table above")
    print(f"  Probe 5 ISA:          6 programs, "
          f"determinism={'PASS' if p5['results']['prog5_determinism'] else 'FAIL'}")
    r2_vals = []
    for damp, damp_r in p6["results"].items():
        if isinstance(damp_r, dict):
            for step, step_r in damp_r.items():
                if isinstance(step_r, dict) and "r_full" in step_r:
                    r2_vals.append(step_r["r2_full"])
    if r2_vals:
        print(f"  Probe 6 FIDELITY:     mean R2={np.mean(r2_vals):.4f}")

    # ---- Save ----
    out_path = _SOL_ROOT / "data" / "circuit_primitives.json"
    out_path.parent.mkdir(exist_ok=True)

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
        "experiment": "Circuit Primitives (Experiment 9)",
        "engine_sha256": "5316e4fd6713b2d5e2dd4999780b5f7871c0a7b1c90e8f151698805653562eef",
        "graph_sha256": "b9800d5313886818c7c1980829e1ca5da7d63d9e2218e36c020df80db19b06fb",
        "total_trials": total_trials,
        "total_seconds": elapsed,
        "probes": all_results,
    })

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  Data saved to {out_path}")
    print(f"  File size: {out_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
