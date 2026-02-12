#!/usr/bin/env python3
"""
Basin Stability Under Jeans Collapse
======================================
Tier 1, Item 1: Does SOL's computational identity survive structural growth?

C28 proves 30 basins (4.9 bits) on the fixed 140-node graph.
The Jeans cosmology experiment *grows* the graph via synth nodes.
This experiment answers: do the basins persist, shift, or multiply
when topology changes underneath them?

Design:
  Phase 1 — BASELINE:  Probe all 140 nodes × 3 dampings on original graph.
  Phase 2 — GROW:      Run Jeans collapse under 3 structural conditions
                       to produce topologies of varying richness.
  Phase 3 — RE-PROBE:  Reset dynamics on each grown graph, re-probe
                       same 140 nodes × 3 dampings.
  Phase 4 — COMPARE:   Basin overlap, new basins, bit capacity change.

Structural conditions:
  - mild:    Jcrit=18, blast        → ~141 nodes (1 synth)
  - medium:  Jcrit=18, cluster_spray → ~145 nodes (5 synths)
  - extreme: Jcrit=8,  blast        → ~280 nodes (140 synths)

Outputs:
  - data/basin_jeans_stability/baseline_basins.csv
  - data/basin_jeans_stability/post_jeans_basins.csv
  - data/basin_jeans_stability/comparison_summary.csv
  - data/basin_jeans_stability/basin_jeans_stability_run_bundle.md
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

# Re-use Jeans machinery from the cosmology experiment
from jeans_cosmology_experiment import (
    SynthSpawner, apply_tractor_beam, _build_adjacency,
    INJECTION_STRATEGIES,
)

# =====================================================================
# Configuration
# =====================================================================

PROBE_DAMPINGS = [0.2, 5.0, 20.0]
PROBE_INJECTION_AMOUNT = 50.0
PROBE_STEPS = 200
PROBE_SAMPLE_INTERVAL = 20
PROBE_C_PRESS = 0.1
PROBE_DT = 0.12
PROBE_RNG_SEED = 42

# Jeans growth phase
GROWTH_STEPS = 200
GROWTH_DT = 0.12
GROWTH_C_PRESS = 0.1
GROWTH_DAMPING = 0.2
GROWTH_RNG_SEED = 42
GROWTH_TRACTOR_RATE = 0.05

# Conditions: (name, jcrit, strategy_name, normalize_synth_mass)
# normalize=False: synths keep their natural semanticMass (10.0) = topology + mass
# normalize=True:  synths reset to semanticMass=1.0 = pure topology effect
GROWTH_CONDITIONS = [
    ("mild",         18.0, "blast",         False),
    ("medium",       18.0, "cluster_spray", False),
    ("extreme",       8.0, "blast",         False),
]

OUT_DIR = _HERE / "data" / "basin_jeans_stability"


# =====================================================================
# Basin Detection (adapted from basin_landscape_survey.py)
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
    Build a fresh engine from the given topology, inject into one node,
    run `steps` ticks, and return the dominant basin.
    """
    physics, _ = create_engine(raw_nodes, raw_edges, rng_seed=rng_seed)

    # Set damping-appropriate params
    # (c_press stays fixed; damping is the variable)

    # Find target node and inject
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


def run_basin_survey(
    raw_nodes: list[dict],
    raw_edges: list[dict],
    original_ids: list[Any],
    dampings: list[float],
    label: str = "survey",
) -> list[dict]:
    """
    For each (original_node, damping), probe the dominant basin.
    Returns list of result dicts.
    """
    results = []
    total = len(original_ids) * len(dampings)
    done = 0
    t0 = time.time()

    for damping in dampings:
        for nid in original_ids:
            r = probe_basin(raw_nodes, raw_edges, nid, PROBE_INJECTION_AMOUNT, damping)
            r["survey"] = label
            results.append(r)
            done += 1
            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"  [{label}] {done}/{total} trials "
                      f"({elapsed:.1f}s elapsed, ~{eta:.0f}s remaining)")

    return results


# =====================================================================
# Jeans Growth: grow the graph, extract the topology
# =====================================================================

def grow_graph(
    jcrit: float,
    strategy_name: str,
    steps: int = GROWTH_STEPS,
    normalize_synth_mass: bool = False,
) -> tuple[list[dict], list[dict], dict]:
    """
    Run Jeans collapse for `steps` ticks and return the grown topology.

    Returns:
        (raw_nodes, raw_edges, growth_stats)

    The returned nodes/edges are the grown graph with all dynamic state
    reset to defaults (rho=0, p=0, psi=0, no stellar flags) so that
    they can be used for a clean basin probe.
    """
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
        # Inject if scheduled
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

    # Collect stats before reset
    star_count = sum(1 for n in physics.nodes if n.get("isStellar"))
    synth_count = sum(1 for n in physics.nodes if n.get("isSynth"))
    total_nodes = len(physics.nodes)
    total_edges = len(physics.edges)

    growth_stats = {
        "jcrit": jcrit,
        "strategy": strategy_name,
        "growth_steps": steps,
        "star_count": star_count,
        "synth_count": synth_count,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "synth_events": len(spawner.events),
        "normalize_synth_mass": normalize_synth_mass,
    }

    # Extract topology as raw nodes/edges with dynamics RESET
    # This isolates the question: does the topology change alone alter basins?
    raw_nodes = []
    for n in physics.nodes:
        raw_node = {
            "id": n["id"],
            "label": n["label"],
            "group": n.get("group", "bridge"),
            "rho": 0.0,
            "p": 0.0,
            "psi": 0.0,
            "psi_bias": 0.0,
            "semanticMass": n.get("semanticMass0", 1.0),
            "semanticMass0": n.get("semanticMass0", 1.0),
            "lastInteractionTime": 0.0,
            "isSingularity": False,
        }
        # Preserve original structural properties but NOT dynamic state
        if n.get("isBattery"):
            raw_node["isBattery"] = True
            raw_node["b_q"] = n.get("b_q", 0)
            raw_node["b_charge"] = n.get("b_charge", 0)
            raw_node["b_state"] = n.get("b_state", "idle")
        # If normalizing, give synth nodes the same mass as originals
        if normalize_synth_mass and n.get("isSynth"):
            raw_node["semanticMass"] = 1.0
            raw_node["semanticMass0"] = 1.0
        raw_nodes.append(raw_node)

    raw_edges = []
    for e in physics.edges:
        raw_edge = {
            "from": e["from"],
            "to": e["to"],
            "w0": e.get("w0", 0.70),
            "background": e.get("background", False),
            "kind": e.get("kind", "?"),
        }
        raw_edges.append(raw_edge)

    return raw_nodes, raw_edges, growth_stats


# =====================================================================
# Analysis: Compare baseline vs post-Jeans basins
# =====================================================================

def compare_basins(
    baseline_results: list[dict],
    post_results: list[dict],
    labels: dict[Any, str],
    condition_name: str,
) -> dict:
    """
    Compare basin assignments between baseline and post-Jeans probes.

    Returns comparison stats for one condition × all dampings.
    """
    comparisons = {}

    for damping in PROBE_DAMPINGS:
        # Build maps: inject_id -> dominant_basin
        base_map = {}
        for r in baseline_results:
            if r["damping"] == damping:
                base_map[r["inject_id"]] = r["dominant_basin"]

        post_map = {}
        for r in post_results:
            if r["damping"] == damping:
                post_map[r["inject_id"]] = r["dominant_basin"]

        # Only compare nodes present in BOTH
        common_ids = set(base_map.keys()) & set(post_map.keys())

        # Basin identity comparison
        same_basin = 0
        shifted_basin = 0
        shifts = []
        for nid in common_ids:
            if base_map[nid] == post_map[nid]:
                same_basin += 1
            else:
                shifted_basin += 1
                shifts.append({
                    "inject_id": nid,
                    "inject_label": labels.get(nid, "?"),
                    "baseline_basin": base_map[nid],
                    "baseline_label": labels.get(base_map[nid], "?"),
                    "post_basin": post_map[nid],
                    "post_label": labels.get(post_map[nid], "?"),
                })

        # Basin sets
        baseline_basins = set(base_map.values()) - {None}
        post_basins = set(post_map.values()) - {None}

        # Separate synth basins (new nodes that became attractors)
        synth_basins = {b for b in post_basins if isinstance(b, str) and b.startswith("synth_")}
        original_post_basins = post_basins - synth_basins

        # Jaccard similarity (on original nodes only)
        intersection = baseline_basins & original_post_basins
        union = baseline_basins | original_post_basins
        jaccard = len(intersection) / len(union) if union else 1.0

        # Information capacity
        baseline_bits = math.log2(max(1, len(baseline_basins)))
        post_bits = math.log2(max(1, len(post_basins)))

        comparisons[damping] = {
            "condition": condition_name,
            "damping": damping,
            "total_probes": len(common_ids),
            "same_basin": same_basin,
            "shifted_basin": shifted_basin,
            "stability_pct": round(same_basin / max(1, len(common_ids)) * 100, 1),
            "baseline_basin_count": len(baseline_basins),
            "post_basin_count": len(post_basins),
            "synth_basin_count": len(synth_basins),
            "original_post_basin_count": len(original_post_basins),
            "surviving_basins": len(intersection),
            "lost_basins": len(baseline_basins - original_post_basins),
            "new_basins": len(original_post_basins - baseline_basins),
            "jaccard_similarity": round(jaccard, 4),
            "baseline_bits": round(baseline_bits, 2),
            "post_bits": round(post_bits, 2),
            "delta_bits": round(post_bits - baseline_bits, 2),
            "synth_basins": sorted(str(b) for b in synth_basins),
            "shifts": shifts,
        }

    return comparisons


# =====================================================================
# Output Writers
# =====================================================================

def write_probe_csv(results: list[dict], path: Path, labels: dict):
    """Write basin probe results to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "survey", "damping", "inject_id", "inject_label",
        "dominant_basin", "dominant_basin_label",
        "final_maxRho", "final_entropy", "final_mass",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "survey": r.get("survey", ""),
                "damping": r["damping"],
                "inject_id": r["inject_id"],
                "inject_label": labels.get(r["inject_id"], "?"),
                "dominant_basin": r["dominant_basin"],
                "dominant_basin_label": labels.get(r["dominant_basin"], "?")
                    if r["dominant_basin"] is not None else "",
                "final_maxRho": round(r["final_maxRho"], 6),
                "final_entropy": round(r["final_entropy"], 6),
                "final_mass": round(r["final_mass"], 6),
            })
    print(f"  Wrote {path} ({len(results)} rows)")


def write_comparison_csv(all_comparisons: dict, path: Path):
    """Write comparison summary to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "condition", "damping",
        "total_probes", "same_basin", "shifted_basin", "stability_pct",
        "baseline_basin_count", "post_basin_count",
        "synth_basin_count", "original_post_basin_count",
        "surviving_basins", "lost_basins", "new_basins",
        "jaccard_similarity", "baseline_bits", "post_bits", "delta_bits",
    ]
    rows = []
    for condition_name, damping_map in all_comparisons.items():
        for damping, comp in damping_map.items():
            rows.append({k: comp[k] for k in fieldnames})
    rows.sort(key=lambda r: (r["condition"], r["damping"]))

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {path} ({len(rows)} rows)")


def write_run_bundle(
    baseline_results: list[dict],
    all_comparisons: dict,
    growth_stats_all: dict,
    labels: dict,
    path: Path,
    elapsed_sec: float,
):
    """Write the full run bundle markdown."""
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Basin Stability Under Jeans Collapse - Run Bundle\n")
    lines.append("## Question")
    lines.append("Does SOL's computational identity (its basin structure) survive")
    lines.append("when Jeans collapse adds new nodes and edges to the graph?\n")
    lines.append("C28 proves 30 basins (4.9 bits) on the fixed 140-node graph.")
    lines.append("If basins persist after structural growth, SOL's identity is")
    lines.append("physics-dependent, not topology-dependent.")
    lines.append("If they shift, topology IS the program.\n")

    lines.append("## Invariants")
    lines.append(f"- dt = {PROBE_DT}")
    lines.append(f"- c_press = {PROBE_C_PRESS}")
    lines.append(f"- probe_steps = {PROBE_STEPS}")
    lines.append(f"- injection_amount = {PROBE_INJECTION_AMOUNT}")
    lines.append(f"- rng_seed = {PROBE_RNG_SEED}")
    lines.append(f"- growth_steps = {GROWTH_STEPS}")
    lines.append(f"- elapsed = {elapsed_sec:.1f}s\n")

    lines.append("## Dampings Probed")
    for d in PROBE_DAMPINGS:
        lines.append(f"- d = {d}")
    lines.append("")

    # Growth conditions
    lines.append("## Structural Growth Conditions\n")
    lines.append("| Condition | Jcrit | Strategy | Normalize | Stars | Synths | Total Nodes | Total Edges |")
    lines.append("|-----------|------:|----------|-----------|------:|-------:|------------:|------------:|")
    for cond_name, stats in growth_stats_all.items():
        norm_str = "Yes" if stats.get("normalize_synth_mass") else "No"
        lines.append(
            f"| {cond_name} | {stats['jcrit']} | {stats['strategy']} | {norm_str} | "
            f"{stats['star_count']} | {stats['synth_count']} | "
            f"{stats['total_nodes']} | {stats['total_edges']} |"
        )
    lines.append("")

    # Baseline basin summary per damping
    lines.append("## Baseline Basin Summary\n")
    for damping in PROBE_DAMPINGS:
        damp_results = [r for r in baseline_results if r["damping"] == damping]
        basin_counter = Counter(r["dominant_basin"] for r in damp_results)
        unique_basins = len(basin_counter)
        bits = math.log2(max(1, unique_basins))
        lines.append(f"### d = {damping}")
        lines.append(f"- Unique basins: {unique_basins} ({bits:.2f} bits)")

        # Top basins
        top = basin_counter.most_common(10)
        lines.append(f"- Top basins:")
        for bid, count in top:
            pct = count / len(damp_results) * 100
            lbl = labels.get(bid, "?")
            lines.append(f"  - {lbl}[{bid}]: {count}/140 ({pct:.1f}%)")
        lines.append("")

    # Comparison results
    lines.append("## Post-Jeans Comparison\n")
    lines.append("| Condition | Damping | Stability% | Same | Shifted | "
                 "Base Basins | Post Basins | Synth Basins | "
                 "Surviving | Lost | New | Jaccard | Base Bits | Post Bits | +/- Bits |")
    lines.append("|-----------|--------:|-----------:|-----:|--------:|"
                 "-----------:|------------:|-------------:|"
                 "----------:|-----:|----:|--------:|----------:|----------:|---------:|")
    for cond_name in sorted(all_comparisons.keys()):
        for damping in PROBE_DAMPINGS:
            c = all_comparisons[cond_name][damping]
            lines.append(
                f"| {cond_name} | {damping} | {c['stability_pct']} | "
                f"{c['same_basin']} | {c['shifted_basin']} | "
                f"{c['baseline_basin_count']} | {c['post_basin_count']} | "
                f"{c['synth_basin_count']} | "
                f"{c['surviving_basins']} | {c['lost_basins']} | "
                f"{c['new_basins']} | {c['jaccard_similarity']} | "
                f"{c['baseline_bits']} | {c['post_bits']} | "
                f"{c['delta_bits']:+.2f} |"
            )
    lines.append("")

    # Detail: which basins shifted?
    lines.append("## Basin Shifts (Detail)\n")
    for cond_name in sorted(all_comparisons.keys()):
        for damping in PROBE_DAMPINGS:
            c = all_comparisons[cond_name][damping]
            shifts = c.get("shifts", [])
            if not shifts:
                continue
            lines.append(f"### {cond_name}, d={damping} ({len(shifts)} shifts)\n")
            lines.append("| Injected Node | Baseline Basin | Post-Jeans Basin |")
            lines.append("|---------------|----------------|------------------|")
            for sh in shifts[:30]:  # cap at 30 to keep manageable
                lines.append(
                    f"| {sh['inject_label']}[{sh['inject_id']}] | "
                    f"{sh['baseline_label']}[{sh['baseline_basin']}] | "
                    f"{sh['post_label']}[{sh['post_basin']}] |"
                )
            if len(shifts) > 30:
                lines.append(f"| ... | ({len(shifts) - 30} more) | |")
            lines.append("")

    # Synth basins detail
    lines.append("## Synth Nodes as Attractors\n")
    any_synth_basins = False
    for cond_name in sorted(all_comparisons.keys()):
        for damping in PROBE_DAMPINGS:
            c = all_comparisons[cond_name][damping]
            sb = c.get("synth_basins", [])
            if sb:
                any_synth_basins = True
                lines.append(f"- **{cond_name}, d={damping}**: {len(sb)} synth basin(s): {', '.join(sb)}")
    if not any_synth_basins:
        lines.append("No synth nodes became dominant basins in any condition.")
    lines.append("")

    # Observations placeholder
    lines.append("## Observations\n")
    lines.append("*(To be filled after analysis)*\n")

    lines.append("## Exports")
    lines.append("- `baseline_basins.csv` - baseline probe results")
    lines.append("- `post_jeans_basins.csv` - post-Jeans probe results")
    lines.append("- `comparison_summary.csv` - condition x damping comparison")
    lines.append("- `basin_jeans_stability_run_bundle.md` - this file")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Wrote {path}")


# =====================================================================
# Main Orchestrator
# =====================================================================

def main():
    t_start = time.time()

    # Load labels for reporting
    with open(DEFAULT_GRAPH_PATH, "r") as f:
        default_data = json.load(f)
    labels = {n["id"]: n["label"] for n in default_data["rawNodes"]}
    original_ids = sorted(n["id"] for n in default_data["rawNodes"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Phase 1: Baseline basin survey
    # ------------------------------------------------------------------
    print("=" * 70)
    print("PHASE 1: Baseline Basin Survey (140 nodes x 3 dampings = 420 trials)")
    print("=" * 70)

    baseline_nodes = deepcopy(default_data["rawNodes"])
    baseline_edges = deepcopy(default_data["rawEdges"])

    baseline_results = run_basin_survey(
        baseline_nodes, baseline_edges,
        original_ids, PROBE_DAMPINGS,
        label="baseline",
    )

    write_probe_csv(baseline_results, OUT_DIR / "baseline_basins.csv", labels)

    # Quick baseline summary
    for damping in PROBE_DAMPINGS:
        damp_results = [r for r in baseline_results if r["damping"] == damping]
        basins = set(r["dominant_basin"] for r in damp_results)
        print(f"  Baseline d={damping}: {len(basins)} unique basins "
              f"({math.log2(max(1, len(basins))):.2f} bits)")

    # ------------------------------------------------------------------
    # Phase 2 & 3: Grow graphs, then probe post-Jeans
    # ------------------------------------------------------------------
    all_post_results = []
    all_comparisons = {}
    growth_stats_all = {}

    for cond_name, jcrit, strategy_name, normalize in GROWTH_CONDITIONS:
        print(f"\n{'=' * 70}")
        norm_tag = " [mass normalized]" if normalize else ""
        print(f"PHASE 2: Growing topology: {cond_name} "
              f"(Jcrit={jcrit}, strategy={strategy_name}){norm_tag}")
        print("=" * 70)

        grown_nodes, grown_edges, g_stats = grow_graph(jcrit, strategy_name,
                                                          normalize_synth_mass=normalize)
        growth_stats_all[cond_name] = g_stats

        print(f"  Growth complete: {g_stats['total_nodes']} nodes, "
              f"{g_stats['total_edges']} edges, "
              f"{g_stats['synth_count']} synths, "
              f"{g_stats['star_count']} stars")

        # Update labels with synth nodes
        for n in grown_nodes:
            if n["id"] not in labels:
                labels[n["id"]] = n["label"]

        print(f"\nPHASE 3: Post-Jeans Basin Probe: {cond_name} "
              f"(140 nodes x 3 dampings = 420 trials)")

        post_results = run_basin_survey(
            grown_nodes, grown_edges,
            original_ids, PROBE_DAMPINGS,
            label=f"post_{cond_name}",
        )
        all_post_results.extend(post_results)

        # Quick post summary
        for damping in PROBE_DAMPINGS:
            damp_results = [r for r in post_results if r["damping"] == damping]
            basins = set(r["dominant_basin"] for r in damp_results)
            synth_basins = {b for b in basins if isinstance(b, str) and str(b).startswith("synth_")}
            print(f"  Post-Jeans d={damping}: {len(basins)} unique basins "
                  f"({len(synth_basins)} synth)")

        # Compare
        comparisons = compare_basins(
            baseline_results, post_results, labels, cond_name
        )
        all_comparisons[cond_name] = comparisons

        for damping in PROBE_DAMPINGS:
            c = comparisons[damping]
            print(f"  d={damping}: stability={c['stability_pct']}%, "
                  f"jaccard={c['jaccard_similarity']}, "
                  f"basins {c['baseline_basin_count']}->{c['post_basin_count']} "
                  f"(+{c['delta_bits']:+.2f} bits)")

    # ------------------------------------------------------------------
    # Phase 4: Write outputs
    # ------------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("PHASE 4: Writing outputs")
    print("=" * 70)

    write_probe_csv(all_post_results, OUT_DIR / "post_jeans_basins.csv", labels)
    write_comparison_csv(all_comparisons, OUT_DIR / "comparison_summary.csv")

    elapsed = time.time() - t_start
    write_run_bundle(
        baseline_results, all_comparisons, growth_stats_all,
        labels, OUT_DIR / "basin_jeans_stability_run_bundle.md", elapsed
    )

    print(f"\nDone. Total elapsed: {elapsed:.1f}s")
    print(f"All outputs in: {OUT_DIR}")


if __name__ == "__main__":
    main()
