#!/usr/bin/env python3
"""
Damping Phase Map — Mapping the Third Hidden Knob
====================================================
Explores damping as the hidden control parameter governing SOL's
computational identity regime.

From basin_jeans_stability we know:
  d=0.2  → 94-96% basin stability (physics-dominated)
  d=5.0  → 90-92% basin stability (physics-dominated)
  d=20.0 → 0-19%  basin stability (topology-dominated)

This experiment maps the transition with high resolution to find:
  1. The critical damping (d_crit) where the phase transition occurs
  2. Whether the transition is sharp (first-order) or gradual (second-order)
  3. Emergent phenomena: bifurcations, hysteresis, critical slowing
  4. How damping interacts with growth magnitude (2D phase map)

Design:
  Sweep 1 — HIGH-RESOLUTION BASELINE:
    16 damping values × 140 probes on the original graph.
    Maps basin count, entropy, dominant attractor share, self-attraction %.

  Sweep 2 — DAMPING × GROWTH (2D PHASE MAP):
    16 damping values × 3 growth conditions × 140 probes.
    For each (damping, condition): measure stability%, Jaccard, synth capture.

  Sweep 3 — CRITICAL SLOWING DOWN:
    Near the transition, measure how long basins take to stabilize.
    Critical slowing is a signature of second-order phase transitions.

Outputs:
  data/damping_phase_map/baseline_sweep.csv
  data/damping_phase_map/phase_map.csv
  data/damping_phase_map/convergence_sweep.csv
  data/damping_phase_map/damping_phase_map_run_bundle.md
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "tools" / "sol-core"))

from sol_engine import (
    SOLEngine, SOLPhysics, compute_metrics, create_engine,
    DEFAULT_GRAPH_PATH, snapshot_state, restore_state,
)
from jeans_cosmology_experiment import (
    SynthSpawner, apply_tractor_beam, _build_adjacency,
    INJECTION_STRATEGIES,
)

# =====================================================================
# Configuration
# =====================================================================

# 16-point damping sweep: dense near suspected transition (d=5-20),
# sparse at extremes
DAMPING_SWEEP = [
    0.1, 0.5, 1.0, 2.0, 3.0, 5.0,       # low regime
    7.0, 8.0, 9.0, 10.0, 12.0, 15.0,     # transition zone
    20.0, 30.0, 50.0, 100.0,              # high regime
]

PROBE_INJECTION_AMOUNT = 50.0
PROBE_STEPS = 200
PROBE_SAMPLE_INTERVAL = 20
PROBE_C_PRESS = 0.1
PROBE_DT = 0.12
PROBE_RNG_SEED = 42

# Growth conditions (reused from basin_jeans_stability)
GROWTH_STEPS = 200
GROWTH_DT = 0.12
GROWTH_C_PRESS = 0.1
GROWTH_DAMPING = 0.2
GROWTH_RNG_SEED = 42
GROWTH_TRACTOR_RATE = 0.05

GROWTH_CONDITIONS = [
    ("mild",    18.0, "blast",         False),
    ("medium",  18.0, "cluster_spray", False),
    ("extreme",  8.0, "blast",         False),
]

# Convergence test: extra dampings near the transition
CONVERGENCE_DAMPINGS = [5.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0]
CONVERGENCE_MAX_STEPS = 500
CONVERGENCE_SAMPLE_INTERVAL = 10

OUT_DIR = _HERE / "data" / "damping_phase_map"


# =====================================================================
# Core probe function
# =====================================================================

def probe_basin(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    inject_id: Any,
    inject_amount: float,
    damping: float,
    steps: int = PROBE_STEPS,
    c_press: float = PROBE_C_PRESS,
    dt: float = PROBE_DT,
    rng_seed: int = PROBE_RNG_SEED,
    sample_interval: int = PROBE_SAMPLE_INTERVAL,
) -> dict:
    """
    Build a fresh engine, inject into one node, run, return dominant basin.
    """
    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=rng_seed)

    target = physics.node_by_id.get(inject_id)
    if target:
        target["rho"] += inject_amount

    basin_visits: dict[Any, int] = {}
    for s in range(1, steps + 1):
        physics.step(dt, c_press, damping)
        if s % sample_interval == 0 or s == steps:
            m = compute_metrics(physics)
            bid = m["rhoMaxId"]
            if bid is not None:
                basin_visits[bid] = basin_visits.get(bid, 0) + 1

    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
    final_m = compute_metrics(physics)

    return {
        "inject_id": inject_id,
        "damping": damping,
        "dominant_basin": dominant,
        "basin_visits": basin_visits,
        "final_maxRho": final_m["maxRho"],
        "final_entropy": final_m["entropy"],
        "final_mass": final_m["mass"],
    }


def probe_basin_with_convergence(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    inject_id: Any,
    inject_amount: float,
    damping: float,
    max_steps: int = CONVERGENCE_MAX_STEPS,
    c_press: float = PROBE_C_PRESS,
    dt: float = PROBE_DT,
    rng_seed: int = PROBE_RNG_SEED,
    sample_interval: int = CONVERGENCE_SAMPLE_INTERVAL,
) -> dict:
    """
    Like probe_basin but tracks when the dominant basin FIRST stabilizes.
    Returns the step at which the basin "locked in" and didn't change again.
    This detects critical slowing down near phase transitions.
    """
    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=rng_seed)

    target = physics.node_by_id.get(inject_id)
    if target:
        target["rho"] += inject_amount

    basin_sequence: list[tuple[int, Any]] = []

    for s in range(1, max_steps + 1):
        physics.step(dt, c_press, damping)
        if s % sample_interval == 0 or s == max_steps:
            m = compute_metrics(physics)
            bid = m["rhoMaxId"]
            basin_sequence.append((s, bid))

    # Find convergence: the earliest step after which the basin never changes
    if not basin_sequence:
        return {"inject_id": inject_id, "damping": damping,
                "converge_step": max_steps, "final_basin": None,
                "n_transitions": 0, "basin_sequence_len": 0}

    final_basin = basin_sequence[-1][1]

    # Walk backwards to find where it first became the final value
    converge_step = basin_sequence[-1][0]
    for step, bid in reversed(basin_sequence):
        if bid == final_basin:
            converge_step = step
        else:
            break

    # Count transitions
    n_transitions = 0
    for i in range(1, len(basin_sequence)):
        if basin_sequence[i][1] != basin_sequence[i - 1][1]:
            n_transitions += 1

    return {
        "inject_id": inject_id,
        "damping": damping,
        "converge_step": converge_step,
        "final_basin": final_basin,
        "n_transitions": n_transitions,
        "basin_sequence_len": len(basin_sequence),
    }


# =====================================================================
# Growth function (identical to basin_jeans_stability)
# =====================================================================

def grow_graph(
    jcrit: float,
    strategy_name: str,
    steps: int = GROWTH_STEPS,
    normalize_synth_mass: bool = False,
) -> tuple[list[dict], list[dict], dict]:
    """Run Jeans collapse, extract grown topology with dynamics reset."""
    with open(DEFAULT_GRAPH_PATH, "r") as f:
        data = json.load(f)
    physics, _ = create_engine(data["rawNodes"], data["rawEdges"],
                                rng_seed=GROWTH_RNG_SEED)
    physics.jeans_cfg["Jcrit"] = jcrit

    spawner = SynthSpawner(physics)
    strategy = INJECTION_STRATEGIES[strategy_name]
    injections = strategy["injections"]
    inj_by_step: dict[int, list[dict]] = {}
    for inj in injections:
        step_num = inj.get("at_step", 0)
        inj_by_step.setdefault(step_num, []).append(inj)

    adj = _build_adjacency(physics)

    for tick in range(steps):
        if tick in inj_by_step:
            for inj in inj_by_step[tick]:
                for n in physics.nodes:
                    if n["label"].lower() == inj["label"].lower():
                        n["rho"] += inj["amount"]
                        break
        physics.step(GROWTH_DT, GROWTH_C_PRESS, GROWTH_DAMPING)
        apply_tractor_beam(physics, GROWTH_TRACTOR_RATE, adj)
        new_births = spawner.check_and_spawn(tick)
        if new_births:
            adj = _build_adjacency(physics)

    star_count = sum(1 for n in physics.nodes if n.get("isStellar"))
    synth_count = sum(1 for n in physics.nodes if n.get("isSynth"))
    total_nodes = len(physics.nodes)
    total_edges = len(physics.edges)

    growth_stats = {
        "jcrit": jcrit, "strategy": strategy_name,
        "growth_steps": steps, "star_count": star_count,
        "synth_count": synth_count, "total_nodes": total_nodes,
        "total_edges": total_edges, "synth_events": len(spawner.events),
        "normalize_synth_mass": normalize_synth_mass,
    }

    raw_nodes = []
    for n in physics.nodes:
        raw_node = {
            "id": n["id"], "label": n["label"],
            "group": n.get("group", "bridge"),
            "rho": 0.0, "p": 0.0, "psi": 0.0, "psi_bias": 0.0,
            "semanticMass": n.get("semanticMass0", 1.0),
            "semanticMass0": n.get("semanticMass0", 1.0),
            "lastInteractionTime": 0.0, "isSingularity": False,
        }
        if n.get("isBattery"):
            raw_node["isBattery"] = True
            raw_node["b_q"] = n.get("b_q", 0)
            raw_node["b_charge"] = n.get("b_charge", 0)
            raw_node["b_state"] = n.get("b_state", "idle")
        if normalize_synth_mass and n.get("isSynth"):
            raw_node["semanticMass"] = 1.0
            raw_node["semanticMass0"] = 1.0
        raw_nodes.append(raw_node)

    raw_edges = []
    for e in physics.edges:
        raw_edge = {
            "from": e["from"], "to": e["to"],
            "w0": e.get("w0", 0.70),
            "background": e.get("background", False),
            "kind": e.get("kind", "?"),
        }
        raw_edges.append(raw_edge)

    return raw_nodes, raw_edges, growth_stats


# =====================================================================
# Sweep 1: Baseline damping sweep
# =====================================================================

def run_baseline_sweep(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    original_ids: list[Any],
    labels: dict[Any, str],
) -> list[dict]:
    """
    Sweep all dampings × all nodes on the original graph.
    For each damping, computes aggregate stats: basin count,
    self-attraction rate, top attractor share, entropy spread.
    """
    results = []
    total = len(DAMPING_SWEEP) * len(original_ids)
    done = 0
    t0 = time.time()

    for damping in DAMPING_SWEEP:
        for nid in original_ids:
            r = probe_basin(raw_nodes, raw_edges, nid,
                            PROBE_INJECTION_AMOUNT, damping)
            r["label"] = labels.get(nid, "?")
            results.append(r)
            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"  [baseline sweep] {done}/{total} "
                      f"({elapsed:.1f}s, ~{eta:.0f}s remaining)")

    return results


def aggregate_baseline(
    results: list[dict],
    n_nodes: int,
) -> list[dict]:
    """
    From per-probe results, compute per-damping aggregate statistics.
    """
    by_damping: dict[float, list[dict]] = defaultdict(list)
    for r in results:
        by_damping[r["damping"]].append(r)

    aggregates = []
    for damping in sorted(by_damping.keys()):
        probes = by_damping[damping]
        basins = [r["dominant_basin"] for r in probes]
        basin_counts = Counter(basins)

        unique_basins = len(basin_counts)
        bits = math.log2(unique_basins) if unique_basins > 1 else 0

        # Self-attraction: how many nodes land on themselves
        self_attract = sum(1 for r in probes if r["dominant_basin"] == r["inject_id"])
        self_attract_pct = 100.0 * self_attract / len(probes) if probes else 0

        # Top attractor share: what % of probes go to the #1 basin
        top_basin, top_count = basin_counts.most_common(1)[0]
        top_share_pct = 100.0 * top_count / len(probes) if probes else 0

        # Mean entropy across all final states
        mean_entropy = sum(r["final_entropy"] for r in probes) / len(probes) if probes else 0
        mean_maxRho = sum(r["final_maxRho"] for r in probes) / len(probes) if probes else 0

        # Basin concentration: Herfindahl index (sum of squared shares)
        shares = [c / len(probes) for c in basin_counts.values()]
        herfindahl = sum(s * s for s in shares)

        # Effective number of basins (inverse Herfindahl)
        effective_basins = 1.0 / herfindahl if herfindahl > 0 else 0

        # Decay factor per tick: 1 - (damping * dt * 0.1)
        decay_per_tick = 1.0 - (damping * PROBE_DT * 0.1)
        # After 200 steps, remaining fraction
        remaining_frac = max(0, decay_per_tick) ** PROBE_STEPS

        aggregates.append({
            "damping": damping,
            "unique_basins": unique_basins,
            "bits": round(bits, 3),
            "self_attract_pct": round(self_attract_pct, 1),
            "top_basin": top_basin,
            "top_share_pct": round(top_share_pct, 1),
            "mean_entropy": round(mean_entropy, 4),
            "mean_maxRho": round(mean_maxRho, 2),
            "herfindahl": round(herfindahl, 4),
            "effective_basins": round(effective_basins, 1),
            "decay_per_tick": round(decay_per_tick, 4),
            "rho_remaining_pct": round(100 * remaining_frac, 4),
        })

    return aggregates


# =====================================================================
# Sweep 2: 2D Phase Map (damping × growth)
# =====================================================================

def select_representative_nodes(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    original_ids: list[Any],
    n_sample: int = 40,
) -> list[Any]:
    """
    Select representative nodes: high-degree hub, low-degree periphery,
    and mid-degree bridge nodes.  Always includes the known 'vulnerable 11'
    from basin_jeans_stability.
    """
    deg = Counter()
    for n in raw_nodes:
        deg[n["id"]] = 0
    for e in raw_edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1

    sorted_ids = sorted(original_ids, key=lambda x: deg.get(x, 0), reverse=True)

    # Must-include: the 11 nodes known to shift first
    vulnerable_labels = {
        "par", "johannine grove", "mystery school", "holorian",
        "melchizedek", "loch", "john", "christine hayes", "plain",
        "church", "mazur",
    }
    label_to_id = {n["label"].lower(): n["id"] for n in raw_nodes}
    must_include = set()
    for lbl in vulnerable_labels:
        nid = label_to_id.get(lbl)
        if nid is not None:
            must_include.add(nid)

    # Build sample: must-include + top-degree + bottom-degree + mid
    sample = set(must_include)
    n_remaining = n_sample - len(sample)
    if n_remaining > 0:
        top_n = n_remaining // 3
        bot_n = n_remaining // 3
        mid_n = n_remaining - top_n - bot_n

        for nid in sorted_ids[:top_n * 2]:
            if nid not in sample and len(sample) < len(must_include) + top_n:
                sample.add(nid)
        for nid in sorted_ids[-(bot_n * 2):]:
            if nid not in sample and len(sample) < len(must_include) + top_n + bot_n:
                sample.add(nid)
        mid_start = len(sorted_ids) // 2 - mid_n
        for nid in sorted_ids[mid_start: mid_start + mid_n * 2]:
            if nid not in sample and len(sample) < n_sample:
                sample.add(nid)

    return list(sample)


def run_phase_map(
    baseline_results: list[dict],
    grown_graphs: dict[str, tuple[list, list, dict]],
    original_ids: list[Any],
    labels: dict[Any, str],
    sample_ids: list[Any] | None = None,
) -> list[dict]:
    """
    For each (damping, growth_condition), probe the grown graph and
    compare against baseline to get stability metrics.

    Uses sample_ids (representative subset) for the grown probes,
    but maps against full baseline for those same IDs.
    """
    probe_ids = sample_ids if sample_ids is not None else original_ids
    phase_rows = []

    for cond_name, (g_nodes, g_edges, g_stats) in grown_graphs.items():
        # Build label map including synth nodes
        g_labels = dict(labels)
        for n in g_nodes:
            if n["id"] not in g_labels:
                g_labels[n["id"]] = n["label"]

        print(f"\n  === Phase map: {cond_name} ({g_stats['total_nodes']} nodes) ===")
        total = len(DAMPING_SWEEP) * len(probe_ids)
        done = 0
        t0 = time.time()

        for damping in DAMPING_SWEEP:
            # Get baseline map for this damping (from full sweep)
            base_map = {}
            for r in baseline_results:
                if r["damping"] == damping:
                    base_map[r["inject_id"]] = r["dominant_basin"]

            # Probe grown graph (sample only)
            post_map = {}
            for nid in probe_ids:
                r = probe_basin(g_nodes, g_edges, nid,
                                PROBE_INJECTION_AMOUNT, damping)
                post_map[nid] = r["dominant_basin"]
                done += 1

            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"    [{cond_name}] {done}/{total} "
                      f"({elapsed:.1f}s, ~{eta:.0f}s remaining)")

            # Compare (only probed nodes)
            same = sum(1 for nid in probe_ids
                       if base_map.get(nid) == post_map.get(nid))
            shifted = len(probe_ids) - same
            stability = 100.0 * same / len(probe_ids) if probe_ids else 0

            # Basin sets
            base_basins = {base_map[nid] for nid in probe_ids if nid in base_map} - {None}
            post_basins = set(post_map.values()) - {None}
            synth_basins = {b for b in post_basins
                           if isinstance(b, str) and b.startswith("synth_")}
            orig_post = post_basins - synth_basins

            intersection = base_basins & orig_post
            union = base_basins | orig_post
            jaccard = len(intersection) / len(union) if union else 1.0

            # Synth capture: how many probes land on synth basins
            synth_captured = sum(1 for nid in probe_ids
                                 if isinstance(post_map.get(nid), str)
                                 and post_map[nid].startswith("synth_"))
            synth_capture_pct = 100.0 * synth_captured / len(probe_ids)

            # Monopole detection: does one basin capture > 50% of probes?
            post_counts = Counter(post_map.values())
            top_basin, top_count = post_counts.most_common(1)[0]
            monopole_pct = 100.0 * top_count / len(probe_ids)

            phase_rows.append({
                "condition": cond_name,
                "damping": damping,
                "total_probes": len(probe_ids),
                "same_basin": same,
                "shifted": shifted,
                "stability_pct": round(stability, 1),
                "jaccard": round(jaccard, 4),
                "baseline_basins": len(base_basins),
                "post_basins": len(post_basins),
                "synth_basins": len(synth_basins),
                "synth_capture_pct": round(synth_capture_pct, 1),
                "top_basin": g_labels.get(top_basin, str(top_basin)),
                "monopole_pct": round(monopole_pct, 1),
                "synth_count": g_stats["synth_count"],
                "total_nodes": g_stats["total_nodes"],
            })

    return phase_rows


# =====================================================================
# Sweep 3: Convergence / Critical Slowing Down
# =====================================================================

def run_convergence_sweep(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    original_ids: list[Any],
    sample_ids: list[Any] | None = None,
) -> list[dict]:
    """
    Near the transition zone, measure how quickly basins stabilize.
    Uses 20 representative nodes (top-degree + bottom-degree + random)
    to keep runtime manageable.
    """
    if sample_ids is None:
        # Pick 20 representative nodes: 7 high-degree, 7 low-degree, 6 mid
        deg = Counter()
        for n in raw_nodes:
            deg[n["id"]] = 0
        for e in raw_edges:
            deg[e["from"]] += 1
            deg[e["to"]] += 1

        sorted_nodes = sorted(original_ids, key=lambda x: deg.get(x, 0), reverse=True)
        sample_ids = sorted_nodes[:7] + sorted_nodes[-7:] + sorted_nodes[len(sorted_nodes)//2 - 3: len(sorted_nodes)//2 + 3]
        sample_ids = list(set(sample_ids))  # dedupe
        print(f"  Convergence sample: {len(sample_ids)} nodes")

    results = []
    total = len(CONVERGENCE_DAMPINGS) * len(sample_ids)
    done = 0
    t0 = time.time()

    for damping in CONVERGENCE_DAMPINGS:
        for nid in sample_ids:
            r = probe_basin_with_convergence(
                raw_nodes, raw_edges, nid,
                PROBE_INJECTION_AMOUNT, damping,
                max_steps=CONVERGENCE_MAX_STEPS,
            )
            results.append(r)
            done += 1

        elapsed = time.time() - t0
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        print(f"  [convergence] d={damping}: {done}/{total} "
              f"({elapsed:.1f}s, ~{eta:.0f}s remaining)")

    return results


def aggregate_convergence(results: list[dict]) -> list[dict]:
    """Per-damping convergence stats."""
    by_damping: dict[float, list[dict]] = defaultdict(list)
    for r in results:
        by_damping[r["damping"]].append(r)

    agg = []
    for damping in sorted(by_damping.keys()):
        trials = by_damping[damping]
        conv_steps = [t["converge_step"] for t in trials]
        n_trans = [t["n_transitions"] for t in trials]

        agg.append({
            "damping": damping,
            "n_probes": len(trials),
            "mean_converge_step": round(sum(conv_steps) / len(conv_steps), 1),
            "max_converge_step": max(conv_steps),
            "min_converge_step": min(conv_steps),
            "mean_transitions": round(sum(n_trans) / len(n_trans), 2),
            "max_transitions": max(n_trans),
            "pct_slow_converge": round(100.0 * sum(1 for s in conv_steps if s > 300) / len(conv_steps), 1),
        })

    return agg


# =====================================================================
# Output: Run Bundle
# =====================================================================

def write_run_bundle(
    baseline_agg: list[dict],
    phase_rows: list[dict],
    convergence_agg: list[dict],
    grown_stats: dict[str, dict],
    elapsed_sec: float,
):
    """Write the complete run bundle markdown report."""
    lines = []
    lines.append("# Damping Phase Map — Run Bundle")
    lines.append("")
    lines.append("## Experiment: Mapping the Third Hidden Knob")
    lines.append("")
    lines.append("**Question**: Where is the critical damping that separates")
    lines.append("physics-dominated computation from topology-dominated computation?")
    lines.append("Is the transition sharp or gradual? What emergent phenomena appear?")
    lines.append("")
    lines.append(f"**Runtime**: {elapsed_sec:.1f}s ({elapsed_sec/60:.1f} min)")
    lines.append(f"**Damping sweep**: {DAMPING_SWEEP}")
    lines.append(f"**Probe config**: {PROBE_STEPS} steps, dt={PROBE_DT}, "
                 f"c_press={PROBE_C_PRESS}, injection={PROBE_INJECTION_AMOUNT}")
    lines.append("")

    # --- Sweep 1: Baseline ---
    lines.append("## Sweep 1: Baseline Damping Landscape")
    lines.append("")
    lines.append("How does the original 140-node graph's basin structure change")
    lines.append("as damping increases?")
    lines.append("")
    lines.append("| Damping | Basins | Bits | Self-Attract% | Top Share% | Top Basin | Eff.Basins | Decay/tick | Rho@200 |")
    lines.append("|---------|--------|------|---------------|------------|-----------|------------|------------|---------|")
    for a in baseline_agg:
        lines.append(f"| {a['damping']:.1f} | {a['unique_basins']} | {a['bits']:.2f} | "
                     f"{a['self_attract_pct']:.1f} | {a['top_share_pct']:.1f} | "
                     f"{a['top_basin']} | {a['effective_basins']:.1f} | "
                     f"{a['decay_per_tick']:.4f} | {a['rho_remaining_pct']:.2f}% |")
    lines.append("")

    # --- Sweep 2: Phase Map ---
    lines.append("## Sweep 2: Damping × Growth Phase Map")
    lines.append("")
    lines.append("### Growth Conditions")
    lines.append("")
    for cond_name, stats in grown_stats.items():
        lines.append(f"- **{cond_name}**: {stats['total_nodes']} nodes, "
                     f"{stats['synth_count']} synths, {stats['total_edges']} edges, "
                     f"Jcrit={stats['jcrit']}, strategy={stats['strategy']}")
    lines.append("")

    lines.append("### Stability by Damping × Condition")
    lines.append("")
    lines.append("| Damping | Mild Stab% | Med Stab% | Ext Stab% | Mild Synth% | Med Synth% | Ext Synth% | Mild Mono% | Med Mono% | Ext Mono% |")
    lines.append("|---------|------------|-----------|-----------|-------------|------------|------------|------------|-----------|-----------|")

    # Organize by damping
    phase_by_damp: dict[float, dict[str, dict]] = defaultdict(dict)
    for row in phase_rows:
        phase_by_damp[row["damping"]][row["condition"]] = row

    for damping in DAMPING_SWEEP:
        cells = phase_by_damp.get(damping, {})
        mild = cells.get("mild", {})
        med = cells.get("medium", {})
        ext = cells.get("extreme", {})
        lines.append(
            f"| {damping:.1f} | "
            f"{mild.get('stability_pct', '-')} | {med.get('stability_pct', '-')} | {ext.get('stability_pct', '-')} | "
            f"{mild.get('synth_capture_pct', '-')} | {med.get('synth_capture_pct', '-')} | {ext.get('synth_capture_pct', '-')} | "
            f"{mild.get('monopole_pct', '-')} | {med.get('monopole_pct', '-')} | {ext.get('monopole_pct', '-')} |"
        )
    lines.append("")

    # Detailed per-condition tables
    for cond_name in ["mild", "medium", "extreme"]:
        lines.append(f"### {cond_name.title()} Condition — Detail")
        lines.append("")
        lines.append("| Damping | Stability% | Jaccard | Base Basins | Post Basins | Synth Basins | Synth Capture% | Top Basin | Monopole% |")
        lines.append("|---------|------------|---------|-------------|-------------|--------------|----------------|-----------|-----------|")
        for row in phase_rows:
            if row["condition"] == cond_name:
                lines.append(
                    f"| {row['damping']:.1f} | {row['stability_pct']} | {row['jaccard']:.4f} | "
                    f"{row['baseline_basins']} | {row['post_basins']} | {row['synth_basins']} | "
                    f"{row['synth_capture_pct']} | {row['top_basin']} | {row['monopole_pct']} |"
                )
        lines.append("")

    # --- Sweep 3: Convergence ---
    lines.append("## Sweep 3: Convergence & Critical Slowing Down")
    lines.append("")
    lines.append("Near the transition, how quickly do basins stabilize?")
    lines.append("Slow convergence near d_crit signals a second-order phase transition.")
    lines.append("")
    lines.append("| Damping | Mean Conv.Step | Max Conv. | Min Conv. | Mean Trans. | Max Trans. | %Slow(>300) |")
    lines.append("|---------|----------------|-----------|-----------|-------------|------------|-------------|")
    for a in convergence_agg:
        lines.append(
            f"| {a['damping']:.1f} | {a['mean_converge_step']:.1f} | "
            f"{a['max_converge_step']} | {a['min_converge_step']} | "
            f"{a['mean_transitions']:.2f} | {a['max_transitions']} | "
            f"{a['pct_slow_converge']:.1f} |"
        )
    lines.append("")

    # --- Observations placeholder ---
    lines.append("## Observations")
    lines.append("")
    lines.append("*(To be filled after analysis)*")
    lines.append("")

    # --- Exports ---
    lines.append("## Exports")
    lines.append("")
    lines.append("- `baseline_sweep.csv` — per-damping aggregate stats")
    lines.append("- `phase_map.csv` — damping × condition stability data")
    lines.append("- `convergence_sweep.csv` — convergence timing near transition")
    lines.append("- `damping_phase_map_run_bundle.md` — this file")
    lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = OUT_DIR / "damping_phase_map_run_bundle.md"
    bundle_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Run bundle → {bundle_path}")


# =====================================================================
# Main
# =====================================================================

def main():
    t_global = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load original graph
    with open(DEFAULT_GRAPH_PATH, "r") as f:
        data = json.load(f)
    raw_nodes = data["rawNodes"]
    raw_edges = data["rawEdges"]
    original_ids = [n["id"] for n in raw_nodes]
    labels = {n["id"]: n["label"] for n in raw_nodes}
    print(f"Original graph: {len(raw_nodes)} nodes, {len(raw_edges)} edges")

    # ─── Sweep 1: Baseline (with cache) ───
    baseline_cache = OUT_DIR / "baseline_raw.json"
    if baseline_cache.exists():
        print(f"\n{'='*60}")
        print("SWEEP 1: Loading cached baseline")
        print(f"{'='*60}")
        with open(baseline_cache, "r") as f:
            baseline_results = json.load(f)
        baseline_agg = aggregate_baseline(baseline_results, len(original_ids))
        t1_elapsed = 0.0
        print(f"  Loaded {len(baseline_results)} cached baseline results")
    else:
        print(f"\n{'='*60}")
        print("SWEEP 1: Baseline Damping Landscape")
        print(f"  {len(DAMPING_SWEEP)} dampings × {len(original_ids)} nodes = "
              f"{len(DAMPING_SWEEP) * len(original_ids)} trials")
        print(f"{'='*60}")
        t1 = time.time()
        baseline_results = run_baseline_sweep(raw_nodes, raw_edges, original_ids, labels)
        baseline_agg = aggregate_baseline(baseline_results, len(original_ids))
        t1_elapsed = time.time() - t1
        print(f"  Baseline sweep done in {t1_elapsed:.1f}s")

        # Cache raw baseline for re-runs
        with open(baseline_cache, "w") as f:
            json.dump(baseline_results, f)
        print(f"  Cached → {baseline_cache}")

    # Save baseline aggregate CSV
    baseline_csv = OUT_DIR / "baseline_sweep.csv"
    with open(baseline_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=baseline_agg[0].keys())
        w.writeheader()
        w.writerows(baseline_agg)
    print(f"  → {baseline_csv}")

    # Print baseline table live
    print("\n  Baseline landscape:")
    print(f"  {'Damp':>6} {'Basins':>6} {'Bits':>5} {'Self%':>6} {'Top%':>5} {'Eff.B':>6} {'DecayTk':>8} {'Rho%':>8}")
    for a in baseline_agg:
        print(f"  {a['damping']:>6.1f} {a['unique_basins']:>6} {a['bits']:>5.2f} "
              f"{a['self_attract_pct']:>6.1f} {a['top_share_pct']:>5.1f} "
              f"{a['effective_basins']:>6.1f} {a['decay_per_tick']:>8.4f} "
              f"{a['rho_remaining_pct']:>7.2f}%")

    # ─── Grow the graphs (once) ───
    print(f"\n{'='*60}")
    print("GROWING GRAPHS (one-time)")
    print(f"{'='*60}")
    grown_graphs: dict[str, tuple[list, list, dict]] = {}
    grown_stats: dict[str, dict] = {}
    for cond_name, jcrit, strategy, normalize in GROWTH_CONDITIONS:
        print(f"  Growing '{cond_name}': Jcrit={jcrit}, strategy={strategy}")
        t_g = time.time()
        g_nodes, g_edges, g_stats = grow_graph(jcrit, strategy,
                                                normalize_synth_mass=normalize)
        grown_graphs[cond_name] = (g_nodes, g_edges, g_stats)
        grown_stats[cond_name] = g_stats
        print(f"    → {g_stats['total_nodes']} nodes, {g_stats['synth_count']} synths, "
              f"{g_stats['total_edges']} edges ({time.time() - t_g:.1f}s)")

    # ─── Sweep 2: Phase Map ───
    print(f"\n{'='*60}")
    print("SWEEP 2: Damping × Growth Phase Map")

    # Use representative sample for phase map (40 nodes vs 140)
    sample_ids = select_representative_nodes(raw_nodes, raw_edges, original_ids, n_sample=40)
    print(f"  Using {len(sample_ids)} representative nodes (of {len(original_ids)})")

    cond_count = len(GROWTH_CONDITIONS)
    total2 = len(DAMPING_SWEEP) * len(sample_ids) * cond_count
    print(f"  {len(DAMPING_SWEEP)} dampings × {len(sample_ids)} probes × "
          f"{cond_count} conditions = {total2} trials")
    print(f"{'='*60}")
    t2 = time.time()
    phase_rows = run_phase_map(baseline_results, grown_graphs, original_ids,
                               labels, sample_ids=sample_ids)
    t2_elapsed = time.time() - t2
    print(f"\n  Phase map done in {t2_elapsed:.1f}s")

    # Save phase map CSV
    phase_csv = OUT_DIR / "phase_map.csv"
    with open(phase_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=phase_rows[0].keys())
        w.writeheader()
        w.writerows(phase_rows)
    print(f"  → {phase_csv}")

    # Print phase map live
    print("\n  Phase map (Stability%):")
    print(f"  {'Damp':>6} {'Mild':>8} {'Medium':>8} {'Extreme':>8}")
    phase_by_damp: dict[float, dict[str, dict]] = defaultdict(dict)
    for row in phase_rows:
        phase_by_damp[row["damping"]][row["condition"]] = row
    for d in DAMPING_SWEEP:
        cells = phase_by_damp.get(d, {})
        vals = []
        for c in ["mild", "medium", "extreme"]:
            v = cells.get(c, {}).get("stability_pct", "-")
            vals.append(f"{v:>8}" if isinstance(v, (int, float)) else f"{v:>8}")
        print(f"  {d:>6.1f} {''.join(vals)}")

    # ─── Sweep 3: Convergence ───
    print(f"\n{'='*60}")
    print("SWEEP 3: Convergence & Critical Slowing Down")
    print(f"{'='*60}")
    t3 = time.time()
    convergence_results = run_convergence_sweep(raw_nodes, raw_edges, original_ids)
    convergence_agg = aggregate_convergence(convergence_results)
    t3_elapsed = time.time() - t3
    print(f"\n  Convergence sweep done in {t3_elapsed:.1f}s")

    # Save convergence CSV
    conv_csv = OUT_DIR / "convergence_sweep.csv"
    with open(conv_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=convergence_agg[0].keys())
        w.writeheader()
        w.writerows(convergence_agg)
    print(f"  → {conv_csv}")

    # Print convergence live
    print("\n  Convergence near transition:")
    print(f"  {'Damp':>6} {'MeanConv':>9} {'MaxConv':>8} {'MeanTr':>8} {'%Slow':>6}")
    for a in convergence_agg:
        print(f"  {a['damping']:>6.1f} {a['mean_converge_step']:>9.1f} "
              f"{a['max_converge_step']:>8} {a['mean_transitions']:>8.2f} "
              f"{a['pct_slow_converge']:>6.1f}")

    # ─── Write Run Bundle ───
    total_elapsed = time.time() - t_global
    write_run_bundle(baseline_agg, phase_rows, convergence_agg,
                     grown_stats, total_elapsed)

    print(f"\n{'='*60}")
    print(f"COMPLETE in {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"  Sweep 1 (baseline):    {t1_elapsed:.1f}s")
    print(f"  Sweep 2 (phase map):   {t2_elapsed:.1f}s")
    print(f"  Sweep 3 (convergence): {t3_elapsed:.1f}s")
    print(f"  Outputs → {OUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
