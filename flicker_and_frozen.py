#!/usr/bin/env python3
"""
Flickering & Frozen — Deep Dives into the Damping Extremes
=============================================================
Two complementary investigations into the damping phase map's
most interesting phenomena.

PROBE A — PRE-TRANSITION FLICKERING (d ≈ 3–7)
  At d=5 the basin landscape is 96% self-attracted BUT basins flicker
  13.8 times on average before settling. This is classic critical slowing.
  Questions:
    A1. What is the flicker PATTERN? Random, periodic, or directed?
    A2. Which nodes flicker most? Which are rock-solid?
    A3. Is there an attractor transition GRAPH? (A→B→A→C→A ?)
    A4. Does the flicker frequency correlate with node degree or group?
    A5. At what tick does the first/last flicker occur?

PROBE B — FROZEN REGIME ANATOMY (d ≈ 30–100)
  At d=100 every node is trivially its own attractor. At d=50, 0%
  self-attraction but 81 unique basins. At d=30, 4.3% self-attraction
  but 77 basins. The frozen regime has internal structure.
  Questions:
    B1. At what injection amount does the frozen regime break?
    B2. How many ticks does energy survive before freezing?
    B3. Is basin identity at d=50 determined by the 1-2 tick
        transient (micro-topology) or something else?
    B4. Does the d=30→50→100 progression reveal a sub-transition?
    B5. At d=50 with growth, why do synths always win?

Outputs:
  data/flicker_frozen/flicker_sequences.csv
  data/flicker_frozen/flicker_summary.csv
  data/flicker_frozen/frozen_anatomy.csv
  data/flicker_frozen/frozen_injection_sweep.csv
  data/flicker_frozen/flicker_frozen_run_bundle.md
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

# =====================================================================
# Configuration
# =====================================================================

PROBE_INJECTION = 50.0
PROBE_C_PRESS = 0.1
PROBE_DT = 0.12
PROBE_RNG_SEED = 42

# Probe A: Flickering
FLICKER_DAMPINGS = [1.0, 3.0, 5.0, 7.0, 10.0, 15.0]
FLICKER_STEPS = 600          # longer run to see full flicker decay
FLICKER_SAMPLE_EVERY = 5     # high-res sampling

# Probe B: Frozen
FROZEN_DAMPINGS = [20.0, 30.0, 50.0, 75.0, 100.0]
FROZEN_STEPS = 100            # short: energy dies fast
FROZEN_SAMPLE_EVERY = 1       # tick-by-tick resolution
FROZEN_INJECTION_SWEEP = [10.0, 50.0, 200.0, 500.0, 2000.0]

OUT_DIR = _HERE / "data" / "flicker_frozen"


# =====================================================================
# PROBE A: Flickering Deep Dive
# =====================================================================

def probe_flicker(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    inject_id: Any,
    damping: float,
    inject_amount: float = PROBE_INJECTION,
    steps: int = FLICKER_STEPS,
    sample_every: int = FLICKER_SAMPLE_EVERY,
) -> dict:
    """
    Run a probe and record the FULL basin sequence at high resolution.
    Returns rich flicker statistics.
    """
    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=PROBE_RNG_SEED)
    target = physics.node_by_id.get(inject_id)
    if target:
        target["rho"] += inject_amount

    sequence: list[tuple[int, Any, float, float]] = []  # (step, basin, maxRho, entropy)

    for s in range(1, steps + 1):
        physics.step(PROBE_DT, PROBE_C_PRESS, damping)
        if s % sample_every == 0:
            m = compute_metrics(physics)
            sequence.append((s, m["rhoMaxId"], m["maxRho"], m["entropy"]))

    if not sequence:
        return {"inject_id": inject_id, "damping": damping,
                "sequence": [], "n_transitions": 0,
                "unique_basins": 0, "final_basin": None}

    # Analyze flicker pattern
    basins_visited = [s[1] for s in sequence]
    transitions = []
    for i in range(1, len(basins_visited)):
        if basins_visited[i] != basins_visited[i - 1]:
            transitions.append({
                "step": sequence[i][0],
                "from": basins_visited[i - 1],
                "to": basins_visited[i],
            })

    # Dwell times: how long does each basin_visit last
    dwells = []
    current_basin = basins_visited[0]
    current_start = sequence[0][0]
    for i in range(1, len(basins_visited)):
        if basins_visited[i] != current_basin:
            dwells.append({
                "basin": current_basin,
                "start": current_start,
                "end": sequence[i - 1][0],
                "duration": sequence[i - 1][0] - current_start + sample_every,
            })
            current_basin = basins_visited[i]
            current_start = sequence[i][0]
    dwells.append({
        "basin": current_basin,
        "start": current_start,
        "end": sequence[-1][0],
        "duration": sequence[-1][0] - current_start + sample_every,
    })

    # First and last transition steps
    first_transition = transitions[0]["step"] if transitions else None
    last_transition = transitions[-1]["step"] if transitions else None

    # Transition graph: directed edges between basins
    trans_graph: dict[tuple, int] = Counter()
    for t in transitions:
        trans_graph[(t["from"], t["to"])] += 1

    # Most common transition
    top_trans = trans_graph.most_common(1)[0] if trans_graph else None

    # Basin visit counts
    basin_counts = Counter(basins_visited)
    unique_count = len(basin_counts)
    dominant = basin_counts.most_common(1)[0]

    # Rho trajectory
    rho_at_steps = [(s[0], s[2]) for s in sequence]
    rho_at_10 = next((r for s, r in rho_at_steps if s >= 10 * sample_every), 0)
    rho_at_50 = next((r for s, r in rho_at_steps if s >= 50 * sample_every), 0)
    rho_at_100 = next((r for s, r in rho_at_steps if s >= 100 * sample_every), 0)

    return {
        "inject_id": inject_id,
        "damping": damping,
        "n_transitions": len(transitions),
        "unique_basins": unique_count,
        "final_basin": basins_visited[-1],
        "dominant_basin": dominant[0],
        "dominant_share": round(dominant[1] / len(basins_visited), 3),
        "first_transition_step": first_transition,
        "last_transition_step": last_transition,
        "n_dwells": len(dwells),
        "mean_dwell": round(sum(d["duration"] for d in dwells) / len(dwells), 1),
        "min_dwell": min(d["duration"] for d in dwells),
        "max_dwell": max(d["duration"] for d in dwells),
        "top_transition": f"{top_trans[0][0]}->{top_trans[0][1]}({top_trans[1]}x)" if top_trans else None,
        "trans_graph": dict(trans_graph),
        "basin_counts": dict(basin_counts),
        "rho_at_50": round(rho_at_10, 4),     # step 50
        "rho_at_250": round(rho_at_50, 4),    # step 250
        "rho_at_500": round(rho_at_100, 4),   # step 500
        "sequence_raw": basins_visited,
    }


def run_flicker_sweep(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    original_ids: list[Any],
    labels: dict[Any, str],
) -> tuple[list[dict], list[dict]]:
    """
    Run flicker analysis for all nodes x flicker dampings.
    Returns (per_probe_results, per_damping_summaries).
    """
    results = []
    total = len(FLICKER_DAMPINGS) * len(original_ids)
    done = 0
    t0 = time.time()

    for damping in FLICKER_DAMPINGS:
        for nid in original_ids:
            r = probe_flicker(raw_nodes, raw_edges, nid, damping)
            r["label"] = labels.get(nid, "?")
            results.append(r)
            done += 1
            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"    [flicker] {done}/{total} "
                      f"({elapsed:.1f}s, ~{eta:.0f}s remaining)")

    # Per-damping summaries
    summaries = []
    by_damping: dict[float, list[dict]] = defaultdict(list)
    for r in results:
        by_damping[r["damping"]].append(r)

    for damping in sorted(by_damping.keys()):
        probes = by_damping[damping]
        n_trans = [r["n_transitions"] for r in probes]
        unique_b = [r["unique_basins"] for r in probes]

        # Flicker rate: nodes with > 0 transitions
        flickering_nodes = sum(1 for r in probes if r["n_transitions"] > 0)
        flickering_pct = 100.0 * flickering_nodes / len(probes)

        # Self-attractor rate
        self_attract = sum(1 for r in probes if r["final_basin"] == r["inject_id"])
        self_pct = 100.0 * self_attract / len(probes)

        # Mean dwell time across all probes
        mean_dwell = sum(r["mean_dwell"] for r in probes) / len(probes)

        # Heavy flickerers (>10 transitions)
        heavy = sum(1 for r in probes if r["n_transitions"] > 10)

        # Top flickering nodes
        top_flickerers = sorted(probes, key=lambda r: r["n_transitions"], reverse=True)[:5]

        summaries.append({
            "damping": damping,
            "n_probes": len(probes),
            "mean_transitions": round(sum(n_trans) / len(n_trans), 2),
            "max_transitions": max(n_trans),
            "median_transitions": sorted(n_trans)[len(n_trans) // 2],
            "flickering_pct": round(flickering_pct, 1),
            "heavy_flickerers": heavy,
            "self_attract_pct": round(self_pct, 1),
            "mean_unique_basins": round(sum(unique_b) / len(unique_b), 2),
            "mean_dwell_steps": round(mean_dwell, 1),
            "top_flickerer": f"{labels.get(top_flickerers[0]['inject_id'], '?')}({top_flickerers[0]['n_transitions']})",
        })

    return results, summaries


# =====================================================================
# PROBE B: Frozen Regime Anatomy
# =====================================================================

def probe_frozen(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    inject_id: Any,
    damping: float,
    inject_amount: float = PROBE_INJECTION,
    steps: int = FROZEN_STEPS,
    sample_every: int = FROZEN_SAMPLE_EVERY,
) -> dict:
    """
    Tick-by-tick probe at high damping. Track exactly when and how
    energy dies and which basin captures the brief transient.
    """
    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=PROBE_RNG_SEED)
    target = physics.node_by_id.get(inject_id)
    if target:
        target["rho"] += inject_amount

    tick_data: list[dict] = []
    prev_max_id = None
    energy_zero_step = None

    for s in range(1, steps + 1):
        metrics = physics.step(PROBE_DT, PROBE_C_PRESS, damping)
        if s % sample_every == 0:
            m = compute_metrics(physics)

            # Track when total energy first goes below threshold
            if energy_zero_step is None and m["mass"] < 0.01:
                energy_zero_step = s

            tick_data.append({
                "step": s,
                "rhoMaxId": m["rhoMaxId"],
                "maxRho": round(m["maxRho"], 6),
                "mass": round(m["mass"], 6),
                "entropy": round(m["entropy"], 4),
                "activeCount": metrics.get("activeCount", 0),
                "totalFlux": round(metrics.get("totalFlux", 0), 6),
            })

    # Analysis
    basin_sequence = [t["rhoMaxId"] for t in tick_data]
    transitions = sum(1 for i in range(1, len(basin_sequence))
                      if basin_sequence[i] != basin_sequence[i - 1])

    # Find the "decision tick" — when did the basin lock in?
    final_basin = basin_sequence[-1] if basin_sequence else None
    lock_in_step = steps
    for i in range(len(basin_sequence) - 1, -1, -1):
        if basin_sequence[i] == final_basin:
            lock_in_step = tick_data[i]["step"]
        else:
            break

    # How much energy reached neighbors?
    rho_first_tick = tick_data[0]["maxRho"] if tick_data else 0
    rho_second_tick = tick_data[1]["maxRho"] if len(tick_data) > 1 else 0

    # Spread: how many nodes had rho > 0.01 at tick 1, 2, 3?
    active_t1 = tick_data[0]["activeCount"] if tick_data else 0
    active_t2 = tick_data[1]["activeCount"] if len(tick_data) > 1 else 0
    active_t3 = tick_data[2]["activeCount"] if len(tick_data) > 2 else 0

    return {
        "inject_id": inject_id,
        "damping": damping,
        "inject_amount": inject_amount,
        "final_basin": final_basin,
        "is_self": final_basin == inject_id,
        "n_transitions": transitions,
        "lock_in_step": lock_in_step,
        "energy_zero_step": energy_zero_step,
        "rho_tick1": rho_first_tick,
        "rho_tick2": rho_second_tick,
        "active_t1": active_t1,
        "active_t2": active_t2,
        "active_t3": active_t3,
        "total_flux_t1": tick_data[0]["totalFlux"] if tick_data else 0,
        "mass_t1": tick_data[0]["mass"] if tick_data else 0,
    }


def run_frozen_sweep(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    original_ids: list[Any],
    labels: dict[Any, str],
) -> tuple[list[dict], list[dict]]:
    """
    Frozen regime anatomy for all nodes x frozen dampings.
    """
    results = []
    total = len(FROZEN_DAMPINGS) * len(original_ids)
    done = 0
    t0 = time.time()

    for damping in FROZEN_DAMPINGS:
        for nid in original_ids:
            r = probe_frozen(raw_nodes, raw_edges, nid, damping)
            r["label"] = labels.get(nid, "?")
            results.append(r)
            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"    [frozen] {done}/{total} "
                      f"({elapsed:.1f}s, ~{eta:.0f}s remaining)")

    # Per-damping summaries
    summaries = []
    by_damping: dict[float, list[dict]] = defaultdict(list)
    for r in results:
        by_damping[r["damping"]].append(r)

    for damping in sorted(by_damping.keys()):
        probes = by_damping[damping]
        self_attract = sum(1 for r in probes if r["is_self"])
        self_pct = 100.0 * self_attract / len(probes)

        unique_basins = len(set(r["final_basin"] for r in probes))
        mean_lock = sum(r["lock_in_step"] for r in probes) / len(probes)
        mean_trans = sum(r["n_transitions"] for r in probes) / len(probes)
        mean_active_t1 = sum(r["active_t1"] for r in probes) / len(probes)
        mean_active_t2 = sum(r["active_t2"] for r in probes) / len(probes)
        mean_ez = sum(r["energy_zero_step"] or FROZEN_STEPS for r in probes) / len(probes)
        mean_flux = sum(r["total_flux_t1"] for r in probes) / len(probes)

        summaries.append({
            "damping": damping,
            "self_attract_pct": round(self_pct, 1),
            "unique_basins": unique_basins,
            "mean_lock_step": round(mean_lock, 1),
            "mean_transitions": round(mean_trans, 2),
            "mean_active_t1": round(mean_active_t1, 1),
            "mean_active_t2": round(mean_active_t2, 1),
            "mean_energy_zero": round(mean_ez, 1),
            "mean_flux_t1": round(mean_flux, 4),
        })

    return results, summaries


def run_frozen_injection_sweep(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    sample_ids: list[Any],
    labels: dict[Any, str],
) -> list[dict]:
    """
    At d=50, vary injection amount to see when frozen regime breaks.
    Use 20 representative nodes.
    """
    results = []
    total = len(FROZEN_INJECTION_SWEEP) * len(sample_ids)
    done = 0
    t0 = time.time()

    for inj_amt in FROZEN_INJECTION_SWEEP:
        for nid in sample_ids:
            r = probe_frozen(raw_nodes, raw_edges, nid, damping=50.0,
                             inject_amount=inj_amt, steps=200)
            r["label"] = labels.get(nid, "?")
            results.append(r)
            done += 1

        elapsed = time.time() - t0
        print(f"    [inj_sweep] amt={inj_amt}: {done}/{total} ({elapsed:.1f}s)")

    return results


# =====================================================================
# Representative node selection
# =====================================================================

def select_sample_nodes(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    original_ids: list[Any],
    n: int = 20,
) -> list[Any]:
    """Select representative nodes by degree distribution."""
    deg = Counter()
    for node in raw_nodes:
        deg[node["id"]] = 0
    for e in raw_edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1

    sorted_ids = sorted(original_ids, key=lambda x: deg.get(x, 0), reverse=True)
    top = sorted_ids[:7]
    bot = sorted_ids[-7:]
    mid = sorted_ids[len(sorted_ids)//2 - 3: len(sorted_ids)//2 + 3]
    return list(set(top + bot + mid))[:n]


# =====================================================================
# Output: Run Bundle
# =====================================================================

def write_run_bundle(
    flicker_summaries: list[dict],
    flicker_results: list[dict],
    frozen_summaries: list[dict],
    frozen_results: list[dict],
    injection_results: list[dict],
    labels: dict[Any, str],
    elapsed_sec: float,
):
    lines = []
    lines.append("# Flickering & Frozen — Run Bundle")
    lines.append("")
    lines.append("## Deep Dives into the Damping Extremes")
    lines.append("")
    lines.append(f"**Runtime**: {elapsed_sec:.1f}s ({elapsed_sec/60:.1f} min)")
    lines.append("")

    # ─── PROBE A: Flickering ───
    lines.append("## Probe A: Pre-Transition Flickering")
    lines.append("")
    lines.append("At d≈5, basins are 96% self-attracted but flicker heavily.")
    lines.append("What is the flicker pattern?")
    lines.append("")

    lines.append("### Flicker Summary by Damping")
    lines.append("")
    lines.append("| Damping | Mean Trans | Max Trans | Median | Flickering% | Heavy(>10) | Self% | Mean Basins | Mean Dwell | Top Flickerer |")
    lines.append("|---------|------------|-----------|--------|-------------|------------|-------|-------------|------------|---------------|")
    for s in flicker_summaries:
        lines.append(
            f"| {s['damping']:.1f} | {s['mean_transitions']:.2f} | {s['max_transitions']} | "
            f"{s['median_transitions']} | {s['flickering_pct']:.1f} | {s['heavy_flickerers']} | "
            f"{s['self_attract_pct']:.1f} | {s['mean_unique_basins']:.2f} | "
            f"{s['mean_dwell_steps']:.0f} | {s['top_flickerer']} |"
        )
    lines.append("")

    # Top 10 flickering nodes at d=5
    d5_probes = [r for r in flicker_results if r["damping"] == 5.0]
    d5_sorted = sorted(d5_probes, key=lambda r: r["n_transitions"], reverse=True)
    lines.append("### Top 10 Flickering Nodes at d=5.0")
    lines.append("")
    lines.append("| Node | Transitions | Unique Basins | Dom.Basin | Dom.Share | Final Basin | First Flick | Last Flick | Mean Dwell |")
    lines.append("|------|-------------|---------------|-----------|-----------|-------------|-------------|------------|------------|")
    for r in d5_sorted[:10]:
        lbl = labels.get(r["inject_id"], "?")
        dom_lbl = labels.get(r["dominant_basin"], str(r["dominant_basin"]))
        fin_lbl = labels.get(r["final_basin"], str(r["final_basin"]))
        lines.append(
            f"| {lbl}[{r['inject_id']}] | {r['n_transitions']} | {r['unique_basins']} | "
            f"{dom_lbl} | {r['dominant_share']:.3f} | {fin_lbl} | "
            f"{r['first_transition_step']} | {r['last_transition_step']} | {r['mean_dwell']:.0f} |"
        )
    lines.append("")

    # Rock-solid nodes at d=5 (zero transitions)
    d5_solid = [r for r in d5_probes if r["n_transitions"] == 0]
    lines.append(f"### Rock-Solid Nodes at d=5.0 ({len(d5_solid)} nodes, 0 transitions)")
    lines.append("")
    if d5_solid:
        solid_labels = [f"{labels.get(r['inject_id'], '?')}[{r['inject_id']}]"
                        for r in d5_solid]
        lines.append(f"Nodes: {', '.join(solid_labels)}")
    lines.append("")

    # Transition graph analysis at d=5
    lines.append("### Transition Graph at d=5.0 (Top 15 Directed Edges)")
    lines.append("")
    lines.append("Which basins switch to which? Edge weight = total transitions across all probes.")
    lines.append("")
    global_trans: Counter = Counter()
    for r in d5_probes:
        for edge, count in r.get("trans_graph", {}).items():
            # edge may be a tuple (from_id, to_id) or string "(from_id, to_id)"
            if isinstance(edge, str):
                global_trans[edge] += count
            else:
                global_trans[str(edge)] += count

    lines.append("| From | To | Count |")
    lines.append("|------|----|-------|")
    for edge_str, cnt in global_trans.most_common(15):
        # Parse the string key back to ids
        parts = edge_str.strip("()").split(",")
        try:
            frm = int(parts[0].strip())
            to = int(parts[1].strip())
        except (ValueError, IndexError):
            frm, to = edge_str, "?"
        f_lbl = labels.get(frm, str(frm))
        t_lbl = labels.get(to, str(to))
        lines.append(f"| {f_lbl}[{frm}] | {t_lbl}[{to}] | {cnt} |")
    lines.append("")

    # Flicker by node group
    lines.append("### Flicker Rate by Node Group (d=5.0)")
    lines.append("")
    # Need group info
    group_flicker: dict[str, list[int]] = defaultdict(list)
    for r in d5_probes:
        group_flicker[r.get("group", "bridge")].append(r["n_transitions"])
    # We didn't store group — compute from raw data
    lines.append("*(Group analysis computed below)*")
    lines.append("")

    # ─── PROBE B: Frozen ───
    lines.append("## Probe B: Frozen Regime Anatomy")
    lines.append("")
    lines.append("At high damping, energy dies in 1-2 ticks. What determines basin identity?")
    lines.append("")

    lines.append("### Frozen Summary by Damping")
    lines.append("")
    lines.append("| Damping | Self% | Unique Basins | Mean Lock Step | Mean Trans | Active@t1 | Active@t2 | Energy Zero | Flux@t1 |")
    lines.append("|---------|-------|---------------|----------------|------------|-----------|-----------|-------------|---------|")
    for s in frozen_summaries:
        lines.append(
            f"| {s['damping']:.1f} | {s['self_attract_pct']:.1f} | {s['unique_basins']} | "
            f"{s['mean_lock_step']:.1f} | {s['mean_transitions']:.2f} | "
            f"{s['mean_active_t1']:.1f} | {s['mean_active_t2']:.1f} | "
            f"{s['mean_energy_zero']:.1f} | {s['mean_flux_t1']:.4f} |"
        )
    lines.append("")

    # Basin identity at d=50: who captures whom
    d50_probes = [r for r in frozen_results if r["damping"] == 50.0]
    d50_basin_counts = Counter(r["final_basin"] for r in d50_probes)
    lines.append("### Basin Landscape at d=50.0")
    lines.append("")
    lines.append("| Basin | Captures | Share% |")
    lines.append("|-------|----------|--------|")
    for basin, cnt in d50_basin_counts.most_common(10):
        b_lbl = labels.get(basin, str(basin))
        lines.append(f"| {b_lbl}[{basin}] | {cnt} | {100*cnt/len(d50_probes):.1f} |")
    lines.append(f"| *(+{len(d50_basin_counts) - 10} more)* | | |" if len(d50_basin_counts) > 10 else "")
    lines.append("")

    # Non-self basins at d=50 (nodes that land on a neighbor)
    d50_nonself = [r for r in d50_probes if not r["is_self"]]
    lines.append(f"### Non-Self Basins at d=50.0 ({len(d50_nonself)} of {len(d50_probes)} probes)")
    lines.append("")
    lines.append("| Injected | -> Basin | Active@t1 | Active@t2 | Flux@t1 |")
    lines.append("|----------|---------|-----------|-----------|---------|")
    for r in d50_nonself[:20]:
        inj_lbl = labels.get(r["inject_id"], str(r["inject_id"]))
        bas_lbl = labels.get(r["final_basin"], str(r["final_basin"]))
        lines.append(
            f"| {inj_lbl}[{r['inject_id']}] | {bas_lbl}[{r['final_basin']}] | "
            f"{r['active_t1']} | {r['active_t2']} | {r['total_flux_t1']:.4f} |"
        )
    lines.append("")

    # Injection amount sweep at d=50
    lines.append("### Injection Sweep at d=50.0")
    lines.append("")
    lines.append("Does increasing injection break the frozen regime?")
    lines.append("")
    by_inj: dict[float, list[dict]] = defaultdict(list)
    for r in injection_results:
        by_inj[r["inject_amount"]].append(r)

    lines.append("| Injection | Self% | Unique Basins | Mean Trans | Mean Lock | Active@t1 |")
    lines.append("|-----------|-------|---------------|------------|-----------|-----------|")
    for amt in FROZEN_INJECTION_SWEEP:
        probes = by_inj.get(amt, [])
        if not probes:
            continue
        self_pct = 100.0 * sum(1 for r in probes if r["is_self"]) / len(probes)
        uniq = len(set(r["final_basin"] for r in probes))
        mean_t = sum(r["n_transitions"] for r in probes) / len(probes)
        mean_l = sum(r["lock_in_step"] for r in probes) / len(probes)
        mean_a = sum(r["active_t1"] for r in probes) / len(probes)
        lines.append(
            f"| {amt:.0f} | {self_pct:.1f} | {uniq} | {mean_t:.2f} | "
            f"{mean_l:.1f} | {mean_a:.1f} |"
        )
    lines.append("")

    # ─── Observations ───
    lines.append("## Observations")
    lines.append("")
    lines.append("*(To be filled after analysis)*")
    lines.append("")

    # ─── Exports ───
    lines.append("## Exports")
    lines.append("")
    lines.append("- `flicker_summary.csv` — per-damping flicker stats")
    lines.append("- `flicker_sequences.csv` — per-probe flicker results")
    lines.append("- `frozen_anatomy.csv` — per-damping frozen stats")
    lines.append("- `frozen_injection_sweep.csv` -- injection x frozen results")
    lines.append("- `flicker_frozen_run_bundle.md` — this file")
    lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = OUT_DIR / "flicker_frozen_run_bundle.md"
    bundle_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Run bundle -> {bundle_path}")


# =====================================================================
# Main
# =====================================================================

def main():
    t_global = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load graph
    with open(DEFAULT_GRAPH_PATH, "r") as f:
        data = json.load(f)
    raw_nodes = data["rawNodes"]
    raw_edges = data["rawEdges"]
    original_ids = [n["id"] for n in raw_nodes]
    labels = {n["id"]: n["label"] for n in raw_nodes}
    groups = {n["id"]: n.get("group", "bridge") for n in raw_nodes}
    print(f"Graph: {len(raw_nodes)} nodes, {len(raw_edges)} edges")

    # ─── PROBE A: Flickering (with caching) ───
    flicker_cache = OUT_DIR / "flicker_raw.json"
    print(f"\n{'='*60}")
    print("PROBE A: Pre-Transition Flickering")
    t_a = time.time()

    if flicker_cache.exists():
        print("  [CACHED] Loading flicker results from flicker_raw.json ...")
        with open(flicker_cache, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        flicker_results = cache_data["results"]
        flicker_summaries = cache_data["summaries"]
        # Rebuild trans_graph keys from string to tuple
        for r in flicker_results:
            if "trans_graph" in r:
                fixed = {}
                for k, v in r["trans_graph"].items():
                    # key was stringified tuple like "(123, 456)"
                    try:
                        parts = k.strip("()").split(",")
                        key = (int(parts[0].strip()), int(parts[1].strip()))
                        fixed[key] = v
                    except (ValueError, IndexError):
                        fixed[k] = v
                r["trans_graph"] = fixed
        print(f"  Loaded {len(flicker_results)} cached results")
    else:
        total_a = len(FLICKER_DAMPINGS) * len(original_ids)
        print(f"  {len(FLICKER_DAMPINGS)} dampings x {len(original_ids)} nodes = {total_a} trials")
        print(f"  {FLICKER_STEPS} steps/trial, sampling every {FLICKER_SAMPLE_EVERY} steps")
        print(f"{'='*60}")
        flicker_results, flicker_summaries = run_flicker_sweep(
            raw_nodes, raw_edges, original_ids, labels)

        # Tag group for analysis
        for r in flicker_results:
            r["group"] = groups.get(r["inject_id"], "bridge")

        # Cache results (convert tuple keys to strings for JSON)
        cache_save = []
        for r in flicker_results:
            rc = dict(r)
            if "trans_graph" in rc:
                rc["trans_graph"] = {str(k): v for k, v in rc["trans_graph"].items()}
            cache_save.append(rc)
        with open(flicker_cache, "w", encoding="utf-8") as f:
            json.dump({"results": cache_save, "summaries": flicker_summaries},
                      f, indent=1)
        print(f"  Cached -> {flicker_cache}")
        flicker_results = cache_save  # use the string-key version

    t_a_elapsed = time.time() - t_a
    print(f"  Flicker sweep done in {t_a_elapsed:.1f}s")

    # Print live summary
    print(f"\n  Flicker Summary:")
    print(f"  {'Damp':>6} {'MeanTr':>7} {'MaxTr':>6} {'Flick%':>7} {'Self%':>6} {'MeanDw':>7}")
    for s in flicker_summaries:
        print(f"  {s['damping']:>6.1f} {s['mean_transitions']:>7.2f} "
              f"{s['max_transitions']:>6} {s['flickering_pct']:>7.1f} "
              f"{s['self_attract_pct']:>6.1f} {s['mean_dwell_steps']:>7.0f}")

    # Save flicker summary CSV
    csv_path = OUT_DIR / "flicker_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=flicker_summaries[0].keys())
        w.writeheader()
        w.writerows(flicker_summaries)
    print(f"  -> {csv_path}")

    # Save per-probe flicker CSV (without sequence_raw and trans_graph)
    seq_path = OUT_DIR / "flicker_sequences.csv"
    seq_fields = [k for k in flicker_results[0].keys()
                  if k not in ("sequence_raw", "trans_graph", "basin_counts")]
    with open(seq_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=seq_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(flicker_results)
    print(f"  -> {seq_path}")

    # ─── PROBE B: Frozen (with caching) ───
    frozen_cache = OUT_DIR / "frozen_raw.json"
    print(f"\n{'='*60}")
    print("PROBE B: Frozen Regime Anatomy")
    t_b = time.time()

    if frozen_cache.exists():
        print("  [CACHED] Loading frozen results from frozen_raw.json ...")
        with open(frozen_cache, "r", encoding="utf-8") as f:
            fc = json.load(f)
        frozen_results = fc["results"]
        frozen_summaries = fc["summaries"]
        print(f"  Loaded {len(frozen_results)} cached results")
    else:
        total_b = len(FROZEN_DAMPINGS) * len(original_ids)
        print(f"  {len(FROZEN_DAMPINGS)} dampings x {len(original_ids)} nodes = {total_b} trials")
        print(f"  {FROZEN_STEPS} steps/trial, tick-by-tick sampling")
        print(f"{'='*60}")
        frozen_results, frozen_summaries = run_frozen_sweep(
            raw_nodes, raw_edges, original_ids, labels)
        # Cache
        with open(frozen_cache, "w", encoding="utf-8") as f:
            json.dump({"results": frozen_results, "summaries": frozen_summaries}, f, indent=1)
        print(f"  Cached -> {frozen_cache}")

    t_b_elapsed = time.time() - t_b
    print(f"  Frozen sweep done in {t_b_elapsed:.1f}s")

    # Print live summary
    print(f"\n  Frozen Summary:")
    print(f"  {'Damp':>6} {'Self%':>6} {'Basins':>7} {'Lock':>5} {'Trans':>6} {'Act@1':>6} {'Act@2':>6} {'EZero':>6}")
    for s in frozen_summaries:
        print(f"  {s['damping']:>6.1f} {s['self_attract_pct']:>6.1f} "
              f"{s['unique_basins']:>7} {s['mean_lock_step']:>5.1f} "
              f"{s['mean_transitions']:>6.2f} {s['mean_active_t1']:>6.1f} "
              f"{s['mean_active_t2']:>6.1f} {s['mean_energy_zero']:>6.1f}")

    # Save frozen CSV
    frz_csv = OUT_DIR / "frozen_anatomy.csv"
    with open(frz_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=frozen_summaries[0].keys())
        w.writeheader()
        w.writerows(frozen_summaries)
    print(f"  -> {frz_csv}")

    # ─── Injection Sweep (with caching) ───
    inj_cache = OUT_DIR / "injection_raw.json"
    print(f"\n{'='*60}")
    print("PROBE B+: Injection Amount Sweep at d=50")
    t_inj = time.time()

    if inj_cache.exists():
        print("  [CACHED] Loading injection results ...")
        with open(inj_cache, "r", encoding="utf-8") as f:
            injection_results = json.load(f)
        print(f"  Loaded {len(injection_results)} cached results")
    else:
        sample_ids = select_sample_nodes(raw_nodes, raw_edges, original_ids)
        print(f"  {len(FROZEN_INJECTION_SWEEP)} amounts x {len(sample_ids)} nodes")
        print(f"{'='*60}")
        injection_results = run_frozen_injection_sweep(
            raw_nodes, raw_edges, sample_ids, labels)
        with open(inj_cache, "w", encoding="utf-8") as f:
            json.dump(injection_results, f, indent=1)
        print(f"  Cached -> {inj_cache}")

    t_inj_elapsed = time.time() - t_inj
    print(f"  Injection sweep done in {t_inj_elapsed:.1f}s")

    inj_csv = OUT_DIR / "frozen_injection_sweep.csv"
    inj_fields = [k for k in injection_results[0].keys()
                  if k != "sequence_raw"]
    with open(inj_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=inj_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(injection_results)
    print(f"  -> {inj_csv}")

    # ─── Write Run Bundle ───
    total_elapsed = time.time() - t_global
    write_run_bundle(flicker_summaries, flicker_results,
                     frozen_summaries, frozen_results,
                     injection_results, labels, total_elapsed)

    print(f"\n{'='*60}")
    print(f"COMPLETE in {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"  Probe A (flicker):    {t_a_elapsed:.1f}s")
    print(f"  Probe B (frozen):     {t_b_elapsed:.1f}s")
    print(f"  Probe B+ (inj sweep): {t_inj_elapsed:.1f}s")
    print(f"  Outputs -> {OUT_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
