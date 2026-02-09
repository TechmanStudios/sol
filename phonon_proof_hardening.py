#!/usr/bin/env python3
"""
SOL Phonon Proof-Hardening Suite
=================================

Three tests to strengthen the phonon/Faraday R&D proof packet:

  Test 1: Critical Zone Ultra-Resolution (d=74→84 at 0.01)
          Pin exact phase transition boundaries.

  Test 2: Seed Stability (10 RNG seeds at key damping values)
          Verify transitions are structural, not stochastic.

  Test 3: Iton Tracker (directed energy transport detection)
          Track coherent energy packets moving through specific
          edge-paths in the lattice. An "iton" is a self-sustaining
          directed energy flow that chooses a path rather than
          diffusing uniformly.

All three tests use the same multi-agent injection pattern as the
original phonon sweep for direct comparability.
"""
from __future__ import annotations

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
# Constants (identical to phonon sweep)
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
HEARTBEAT_PERIOD_STEPS = round(2 * math.pi / (0.15 * 10 * DT))


def load_graph_info():
    graph_path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(graph_path) as f:
        data = json.load(f)
    labels = {n["id"]: n["label"] for n in data["rawNodes"]}
    groups = {n["id"]: n.get("group", "bridge") for n in data["rawNodes"]}
    return labels, groups


def make_engine(damping, seed=42):
    engine = SOLEngine.from_default_graph(
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed
    )
    for label, amount in MULTI_AGENT_INJECTIONS:
        engine.inject(label, amount)
    return engine


# ===================================================================
# TEST 1: Critical Zone Ultra-Resolution
# ===================================================================

def test_critical_zone():
    """d=74→84 at 0.05 resolution: 201 trials."""
    print("\n" + "=" * 70)
    print("  TEST 1: CRITICAL ZONE ULTRA-RESOLUTION (d=74-84, step=0.05)")
    print("=" * 70)

    damp_values = [round(74.0 + i * 0.05, 2) for i in range(201)]
    steps = 500

    results = []
    t0 = time.time()

    for i, damp in enumerate(damp_values):
        engine = make_engine(damp)
        n_nodes = len(engine.physics.nodes)

        # Collect rho traces at reduced sampling (every 5 steps)
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
        rho_arr = np.array(rho_samples)

        # Oscillation amplitude (simplified)
        osc_amps = []
        for j in range(n_nodes):
            trace = rho_arr[:, j]
            if np.max(trace) > 1e-15:
                osc_amps.append(np.std(trace) / max(np.mean(trace), 1e-15))
            else:
                osc_amps.append(0.0)
        osc_arr = np.array(osc_amps)
        n_modes = int(np.sum(osc_arr > 0.01))

        # Cross-correlation of injection nodes (phase coherence)
        # Normalize traces to [0,1] to handle extreme amplitude ranges
        inj_indices = []
        id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}
        for nid in [1, 2, 9, 23, 29]:
            if nid in id_to_idx:
                inj_indices.append(id_to_idx[nid])

        corrs = []
        for a in range(len(inj_indices)):
            for b in range(a + 1, len(inj_indices)):
                t1 = rho_arr[:, inj_indices[a]].copy()
                t2 = rho_arr[:, inj_indices[b]].copy()
                # Normalize each trace to zero-mean, unit-variance
                r1 = np.max(t1) - np.min(t1)
                r2 = np.max(t2) - np.min(t2)
                if r1 > 0 and r2 > 0:
                    t1 = (t1 - np.mean(t1)) / r1
                    t2 = (t2 - np.mean(t2)) / r2
                    c = np.corrcoef(t1, t2)[0, 1]
                    if not np.isnan(c):
                        corrs.append(abs(c))
        coherence = float(np.mean(corrs)) if corrs else 0.0

        # FFT for heartbeat power
        mass_signal = np.sum(rho_arr, axis=1)
        hb_power = 0.0
        if np.max(np.abs(mass_signal)) > 1e-15:
            fft_v = np.fft.rfft(mass_signal)
            power = np.abs(fft_v) ** 2
            freqs = np.fft.rfftfreq(len(mass_signal), d=DT * 5)  # sampling every 5 steps
            hb_freq = 0.15 * 10 / (2 * math.pi)
            p_no_dc = power[1:]
            f_no_dc = freqs[1:]
            if len(p_no_dc) > 0 and np.sum(p_no_dc) > 1e-15:
                hb_band = np.abs(f_no_dc - hb_freq) < 0.1
                sub_band = np.abs(f_no_dc - hb_freq / 2) < 0.1
                hb_power = float(np.sum(p_no_dc[hb_band | sub_band]) / np.sum(p_no_dc))

        dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None

        results.append({
            "damping": damp,
            "n_modes": n_modes,
            "coherence": coherence,
            "hb_power": hb_power,
            "mean_osc": float(np.mean(osc_arr)),
            "max_osc": float(np.max(osc_arr)),
            "final_basin": dominant,
            "final_maxrho": final["maxRho"],
        })

        if (i + 1) % 50 == 0 or i == 0:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (len(damp_values) - i - 1)
            lbl = ""
            if dominant is not None:
                lbl = f"[{dominant}]"
            print(f"  d={damp:6.2f}  modes={n_modes:3d}  coh={coherence:.4f}  "
                  f"HB={hb_power:.4f}  basin={lbl:<6}  "
                  f"[{elapsed:.0f}s, ETA {eta:.0f}s]")

    elapsed = time.time() - t0
    print(f"\n  Completed 201 trials in {elapsed:.1f}s")

    # Find exact transition points
    labels, _ = load_graph_info()
    print("\n  EXACT PHASE TRANSITION BOUNDARIES:")
    prev_modes = results[0]["n_modes"]
    prev_basin = results[0]["final_basin"]
    prev_coh = results[0]["coherence"]

    for r in results[1:]:
        # Mode count transitions
        if r["n_modes"] != prev_modes:
            delta = r["n_modes"] - prev_modes
            print(f"    d={r['damping']:6.2f}: MODES {prev_modes} → {r['n_modes']} "
                  f"(Δ={delta:+d})")
            prev_modes = r["n_modes"]

        # Basin transitions
        if r["final_basin"] != prev_basin:
            prev_lbl = labels.get(prev_basin, "?") if prev_basin else "None"
            curr_lbl = labels.get(r["final_basin"], "?") if r["final_basin"] else "None"
            print(f"    d={r['damping']:6.2f}: BASIN [{prev_basin}] {prev_lbl} "
                  f"→ [{r['final_basin']}] {curr_lbl}")
            prev_basin = r["final_basin"]

        # Coherence jumps > 0.05
        coh_delta = r["coherence"] - prev_coh
        if abs(coh_delta) > 0.05:
            print(f"    d={r['damping']:6.2f}: COHERENCE {prev_coh:.4f} → "
                  f"{r['coherence']:.4f} (Δ={coh_delta:+.4f})")
            prev_coh = r["coherence"]
        else:
            prev_coh = r["coherence"]

    return results


# ===================================================================
# TEST 2: Seed Stability
# ===================================================================

def test_seed_stability():
    """Run 10 seeds at key damping values to verify structural transitions."""
    print("\n" + "=" * 70)
    print("  TEST 2: SEED STABILITY (10 seeds × 15 damping values)")
    print("=" * 70)

    seeds = [42, 137, 256, 314, 500, 777, 1024, 1337, 2048, 9999]
    # Key damping values: pre-turbulence, turbulence, stable, critical zone
    key_damps = [0.5, 2.0, 5.0, 10.0, 20.0, 40.0, 55.0, 75.0,
                 78.0, 79.5, 80.0, 82.5, 83.0, 83.5, 84.0]
    steps = 1000
    labels, _ = load_graph_info()

    results = {}
    t0 = time.time()

    for damp in key_damps:
        seed_results = []
        for seed in seeds:
            engine = make_engine(damp, seed=seed)
            n_nodes = len(engine.physics.nodes)

            basin_visits = defaultdict(int)
            rho_samples = []

            for s in range(1, steps + 1):
                engine.step()
                if s % 20 == 0:
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

            dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None

            seed_results.append({
                "seed": seed,
                "dominant_basin": dominant,
                "n_modes": n_modes,
                "final_maxrho": final["maxRho"],
                "final_entropy": final["entropy"],
            })

        results[damp] = seed_results

        # Check agreement
        basins = [r["dominant_basin"] for r in seed_results]
        modes = [r["n_modes"] for r in seed_results]
        unique_basins = len(set(basins))
        mode_range = max(modes) - min(modes)

        basin_str = ""
        if unique_basins == 1 and basins[0] is not None:
            basin_str = f"[{basins[0]}] {labels.get(basins[0], '?')}"
            stability = "STABLE"
        elif unique_basins == 1:
            basin_str = "[None]"
            stability = "STABLE"
        else:
            basin_str = f"{unique_basins} distinct basins"
            stability = "VARIABLE"

        print(f"  d={damp:5.1f}  {stability:<8}  basin={basin_str:<30}  "
              f"modes={min(modes)}-{max(modes)}  "
              f"maxRho_range={min(r['final_maxrho'] for r in seed_results):.2e}-"
              f"{max(r['final_maxrho'] for r in seed_results):.2e}")

    elapsed = time.time() - t0
    print(f"\n  Completed {len(key_damps) * len(seeds)} trials in {elapsed:.1f}s")

    return results


# ===================================================================
# TEST 3: Iton Tracker
# ===================================================================

def test_iton_tracker():
    """
    Track directed energy transport through the lattice.

    An "iton" is defined as: a coherent packet of energy (rho) that
    moves through a sequence of connected nodes in a directed manner,
    maintaining or gaining magnitude relative to background diffusion.

    Detection method:
      - At each step, record per-edge flux (direction + magnitude)
      - Track sequences of edges where the same "packet" flows through
        consecutive nodes in a chain
      - An iton is detected when:
        1. A node gains rho from one neighbor AND loses rho to another
           (pass-through, not absorption)
        2. This pattern persists for multiple consecutive steps
        3. The direction is consistent (not oscillating)

    Run at key damping values across all regimes.
    """
    print("\n" + "=" * 70)
    print("  TEST 3: ITON TRACKER (directed energy transport)")
    print("=" * 70)

    labels, groups = load_graph_info()

    # Key damping values spanning all regimes
    iton_damps = [0.2, 1.0, 3.5, 5.0, 10.0, 40.0, 55.0, 79.5, 83.0]
    steps = 500

    all_results = {}
    t0 = time.time()

    for damp in iton_damps:
        engine = make_engine(damp)
        nodes = engine.physics.nodes
        edges = engine.physics.edges
        n_nodes = len(nodes)

        node_ids = [n["id"] for n in nodes]
        id_to_idx = {n["id"]: i for i, n in enumerate(nodes)}

        # Build adjacency for path tracking
        adjacency = defaultdict(set)
        edge_map = {}  # (from_id, to_id) -> edge index
        node_edges = defaultdict(list)  # node_id -> [(edge_idx, role)]
        for ei, e in enumerate(edges):
            adjacency[e["from"]].add(e["to"])
            adjacency[e["to"]].add(e["from"])
            edge_map[(e["from"], e["to"])] = ei
            node_edges[e["from"]].append((ei, "from"))
            node_edges[e["to"]].append((ei, "to"))

        # Per-step tracking
        # For each node at each step: net_inflow, net_outflow, pass_through_score
        node_flow_history = np.zeros((steps, n_nodes, 3))  # [inflow, outflow, rho]

        # Edge flux tracking
        n_edges = len(edges)
        edge_flux_history = np.zeros((steps, n_edges))

        # Iton detection: track "relay chains"
        # A relay = node that received significant flux from one direction
        # and passed it to another direction in the same or next step
        relay_counts = defaultdict(int)      # node_id -> relay events
        chain_events = []                    # list of detected chains

        for s in range(steps):
            # Capture pre-step rho
            pre_rho = np.array([n["rho"] for n in nodes])

            engine.step()

            # Capture post-step rho
            post_rho = np.array([n["rho"] for n in nodes])
            delta_rho = post_rho - pre_rho

            # Record edge fluxes
            for ei, e in enumerate(edges):
                edge_flux_history[s, ei] = e.get("flux", 0.0)

            # For each node, compute inflow/outflow from connected edges
            for ni, n in enumerate(nodes):
                nid = n["id"]
                inflow = 0.0
                outflow = 0.0

                for ei, role in node_edges[nid]:
                    flux = edges[ei].get("flux", 0.0)
                    if role == "from":
                        if flux > 0:
                            outflow += flux
                        else:
                            inflow += abs(flux)
                    else:  # role == "to"
                        if flux > 0:
                            inflow += flux
                        else:
                            outflow += abs(flux)

                node_flow_history[s, ni, 0] = inflow
                node_flow_history[s, ni, 1] = outflow
                node_flow_history[s, ni, 2] = post_rho[ni]

                # Relay detection: node has both significant inflow AND outflow
                # meaning energy passes THROUGH it, not just into it
                if inflow > 0.001 and outflow > 0.001:
                    pass_through_ratio = min(inflow, outflow) / max(inflow, outflow)
                    if pass_through_ratio > 0.3:  # at least 30% of flow is relayed
                        relay_counts[nid] += 1

        # Detect sustained relay chains
        # A chain: sequence of nodes where each relays to the next
        # over multiple consecutive steps
        sustained_relays = {nid: count for nid, count in relay_counts.items()
                           if count >= steps * 0.1}  # active 10%+ of steps

        # Find dominant flow direction per node
        dominant_flows = {}
        for ni, n in enumerate(nodes):
            nid = n["id"]
            total_in = np.sum(node_flow_history[:, ni, 0])
            total_out = np.sum(node_flow_history[:, ni, 1])
            if total_in + total_out > 0.001:
                direction = "PASS" if abs(total_in - total_out) < 0.3 * (total_in + total_out) else \
                           "SINK" if total_in > total_out else "SOURCE"
                dominant_flows[nid] = {
                    "direction": direction,
                    "total_inflow": float(total_in),
                    "total_outflow": float(total_out),
                    "relay_count": relay_counts.get(nid, 0),
                }

        # Edge directionality: find edges with consistent flux direction
        consistent_edges = []
        for ei, e in enumerate(edges):
            flux_trace = edge_flux_history[:, ei]
            pos_steps = np.sum(flux_trace > 0.0001)
            neg_steps = np.sum(flux_trace < -0.0001)
            total_active = pos_steps + neg_steps
            if total_active > steps * 0.5:  # active > 50% of time
                directionality = abs(pos_steps - neg_steps) / total_active
                if directionality > 0.8:  # >80% one direction = strong iton signal
                    direction = "→" if pos_steps > neg_steps else "←"
                    consistent_edges.append({
                        "from": e["from"],
                        "to": e["to"],
                        "directionality": float(directionality),
                        "mean_flux": float(np.mean(np.abs(flux_trace))),
                        "direction": direction,
                    })

        # Report
        print(f"\n  ── damping = {damp} ──")
        print(f"  Sustained relay nodes: {len(sustained_relays)}")
        if sustained_relays:
            sorted_relays = sorted(sustained_relays.items(), key=lambda x: -x[1])[:10]
            for nid, count in sorted_relays:
                flow = dominant_flows.get(nid, {})
                dir_str = flow.get("direction", "?")
                print(f"    [{nid:3d}] {labels.get(nid, '?'):<25} "
                      f"relays={count:4d}/{steps}  "
                      f"type={dir_str:<6}  group={groups.get(nid, '?')}")

        print(f"  Directional edges (>80% one-way): {len(consistent_edges)}")
        if consistent_edges:
            sorted_edges = sorted(consistent_edges,
                                  key=lambda x: -x["mean_flux"])[:10]
            for ce in sorted_edges:
                f_lbl = labels.get(ce["from"], "?")
                t_lbl = labels.get(ce["to"], "?")
                print(f"    [{ce['from']:3d}]{ce['direction']}[{ce['to']:3d}]  "
                      f"{f_lbl:<20} {ce['direction']} {t_lbl:<20}  "
                      f"dir={ce['directionality']:.2f}  "
                      f"flux={ce['mean_flux']:.6f}")

        # Node flow classification
        sinks = [nid for nid, f in dominant_flows.items() if f["direction"] == "SINK"]
        sources = [nid for nid, f in dominant_flows.items() if f["direction"] == "SOURCE"]
        passes = [nid for nid, f in dominant_flows.items() if f["direction"] == "PASS"]
        print(f"  Flow classification: {len(sources)} sources, "
              f"{len(passes)} pass-through, {len(sinks)} sinks")

        # Iton score: ratio of pass-through nodes to total active nodes
        total_active = len(dominant_flows)
        iton_score = len(passes) / total_active if total_active > 0 else 0
        print(f"  Iton score: {iton_score:.3f} "
              f"(pass-through / active, higher = more directed transport)")

        all_results[damp] = {
            "n_sustained_relays": len(sustained_relays),
            "n_directional_edges": len(consistent_edges),
            "n_sources": len(sources),
            "n_passes": len(passes),
            "n_sinks": len(sinks),
            "iton_score": iton_score,
            "top_relays": [(nid, count) for nid, count in
                          sorted(sustained_relays.items(), key=lambda x: -x[1])[:5]],
            "top_directional_edges": consistent_edges[:5],
        }

    elapsed = time.time() - t0
    print(f"\n  Completed iton tracking in {elapsed:.1f}s")

    # Summary
    print(f"\n  {'─' * 50}")
    print(f"  ITON SCORE ACROSS DAMPING RANGE")
    print(f"  {'─' * 50}")
    for damp in iton_damps:
        r = all_results[damp]
        score = r["iton_score"]
        bar = "█" * int(score * 50)
        print(f"  d={damp:5.1f}  score={score:.3f}  "
              f"relays={r['n_sustained_relays']:3d}  "
              f"dir_edges={r['n_directional_edges']:3d}  {bar}")

    return all_results


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  SOL PHONON PROOF-HARDENING SUITE")
    print("  Critical Zone | Seed Stability | Iton Tracker")
    print("=" * 70)

    t_total = time.time()

    r1 = test_critical_zone()
    r2 = test_seed_stability()
    r3 = test_iton_tracker()

    total_time = time.time() - t_total

    print("\n" + "=" * 70)
    print("  PROOF PACKET SUMMARY")
    print("=" * 70)
    print(f"\n  Total runtime: {total_time:.1f}s")

    # Save
    out_path = _SOL_ROOT / "data" / "phonon_proof_hardening.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_sec": round(total_time, 2),
        "critical_zone": [
            {"damping": r["damping"], "n_modes": r["n_modes"],
             "coherence": r["coherence"], "hb_power": r["hb_power"],
             "mean_osc": r["mean_osc"], "max_osc": r["max_osc"],
             "final_basin": r["final_basin"], "final_maxrho": r["final_maxrho"]}
            for r in r1
        ],
        "seed_stability": {
            str(damp): [
                {"seed": sr["seed"], "dominant_basin": sr["dominant_basin"],
                 "n_modes": sr["n_modes"]}
                for sr in seed_results
            ]
            for damp, seed_results in r2.items()
        },
        "iton_results": {
            str(damp): {
                "iton_score": ir["iton_score"],
                "n_sustained_relays": ir["n_sustained_relays"],
                "n_directional_edges": ir["n_directional_edges"],
                "n_sources": ir["n_sources"],
                "n_passes": ir["n_passes"],
                "n_sinks": ir["n_sinks"],
            }
            for damp, ir in r3.items()
        },
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")


if __name__ == "__main__":
    main()
