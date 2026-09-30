#!/usr/bin/env python3
"""
Q7 Investigation: Temporal Injection Cadence — Minimum Distinguishing Difference

Goal: Find the minimum temporal difference (in injection timing) that produces
a distinct basin attractor at d=5.0.

Approach:
  A. Gap sweep:       Fixed 5 pulses of 30 energy, vary inter-pulse gap 1→200 steps
  B. Pulse-count sweep: Fixed 150 total energy, vary N pulses (1→30), gap=50
  C. Onset delay:     Fixed single injection, vary when it happens (step 0→400)
  D. Ordering sweep:  Fixed nodes & amounts but vary temporal order of injections
  E. Fine-grain resolution: Once we find a transition, zoom in with step-by-step resolution

All experiments use d=5.0 (confirmed temporally sensitive) and d=0.2 (turbulent comparison).
"""

import sys
import os
import json
import time
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools", "sol-core"))
from sol_engine import SOLPhysics, create_engine, compute_metrics, SOLEngine

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "tools", "sol-core", "default_graph.json")

# Standard injection protocol
STANDARD_INJECTION = [
    ("grail", 40), ("metatron", 35), ("pyramid", 30),
    ("christ", 25), ("light_codes", 20),
]
TOTAL_ENERGY = sum(e for _, e in STANDARD_INJECTION)  # 150


def load_graph():
    with open(GRAPH_PATH) as f:
        data = json.load(f)
    return data["rawNodes"], data["rawEdges"]


def make_engine(raw_nodes, raw_edges, damping):
    return SOLEngine.from_graph(raw_nodes, raw_edges, damping=damping)


def get_basin(engine, raw_nodes):
    m = engine.compute_metrics()
    node_id = m["rhoMaxId"]
    labels = {n["id"]: n["label"] for n in raw_nodes}
    label = labels.get(node_id, f"id:{node_id}")
    return f"{label}[{node_id}]"


def probe_a_gap_sweep(raw_nodes, raw_edges, damping, total_steps=500):
    """Sweep inter-pulse gap from 1 to 250 steps. 5 pulses of 30 energy to 'grail'."""
    print(f"\n{'='*70}")
    print(f"PROBE A: Gap Sweep at d={damping}")
    print(f"  Protocol: 5 × inject('grail', 30), gap varies, settle to {total_steps} total steps")
    print(f"{'='*70}")

    gaps = [1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200, 250]
    results = []

    for gap in gaps:
        e = make_engine(raw_nodes, raw_edges, damping)
        for pulse in range(5):
            e.inject("grail", 30.0)
            e.run(gap)
        # Settle for remaining steps
        used = 5 * gap
        remain = max(0, total_steps - used)
        if remain > 0:
            e.run(remain)
        basin = get_basin(e, raw_nodes)
        results.append({"gap": gap, "basin": basin})
        print(f"  gap={gap:>4} steps → {basin}")

    # Find transitions
    transitions = []
    for i in range(1, len(results)):
        if results[i]["basin"] != results[i-1]["basin"]:
            transitions.append((results[i-1]["gap"], results[i]["gap"],
                                results[i-1]["basin"], results[i]["basin"]))
    if transitions:
        print(f"\n  TRANSITIONS FOUND: {len(transitions)}")
        for g1, g2, b1, b2 in transitions:
            print(f"    gap {g1}→{g2}: {b1} → {b2}")
    else:
        print(f"\n  NO TRANSITIONS — basin is gap-invariant at d={damping}")

    return results, transitions


def probe_b_pulse_count(raw_nodes, raw_edges, damping, total_steps=500):
    """Fixed 150 total energy to 'grail', split into N equal pulses with gap=50."""
    print(f"\n{'='*70}")
    print(f"PROBE B: Pulse Count Sweep at d={damping}")
    print(f"  Protocol: N × inject('grail', 150/N), gap=50, settle to {total_steps} total")
    print(f"{'='*70}")

    pulse_counts = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30]
    gap = 50
    results = []

    for n in pulse_counts:
        e = make_engine(raw_nodes, raw_edges, damping)
        per_pulse = TOTAL_ENERGY / n
        for pulse in range(n):
            e.inject("grail", per_pulse)
            e.run(gap)
        used = n * gap
        remain = max(0, total_steps - used)
        if remain > 0:
            e.run(remain)
        basin = get_basin(e, raw_nodes)
        results.append({"n_pulses": n, "per_pulse": round(per_pulse, 1), "basin": basin})
        print(f"  N={n:>3} ({per_pulse:>6.1f} each) → {basin}")

    transitions = []
    for i in range(1, len(results)):
        if results[i]["basin"] != results[i-1]["basin"]:
            transitions.append((results[i-1]["n_pulses"], results[i]["n_pulses"],
                                results[i-1]["basin"], results[i]["basin"]))
    if transitions:
        print(f"\n  TRANSITIONS: {len(transitions)}")
        for n1, n2, b1, b2 in transitions:
            print(f"    N={n1}→{n2}: {b1} → {b2}")
    else:
        print(f"\n  NO TRANSITIONS — basin is pulse-count-invariant at d={damping}")

    return results, transitions


def probe_c_onset_delay(raw_nodes, raw_edges, damping, total_steps=500):
    """Single standard injection at varying onset times."""
    print(f"\n{'='*70}")
    print(f"PROBE C: Onset Delay Sweep at d={damping}")
    print(f"  Protocol: wait N steps, apply standard injection, settle to {total_steps}")
    print(f"{'='*70}")

    delays = [0, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 400]
    results = []

    for delay in delays:
        e = make_engine(raw_nodes, raw_edges, damping)
        if delay > 0:
            e.run(delay)
        for label, amt in STANDARD_INJECTION:
            e.inject(label, amt)
        remain = max(0, total_steps - delay)
        e.run(remain)
        basin = get_basin(e, raw_nodes)
        results.append({"delay": delay, "basin": basin})
        print(f"  delay={delay:>4} → {basin}")

    transitions = []
    for i in range(1, len(results)):
        if results[i]["basin"] != results[i-1]["basin"]:
            transitions.append((results[i-1]["delay"], results[i]["delay"],
                                results[i-1]["basin"], results[i]["basin"]))
    if transitions:
        print(f"\n  TRANSITIONS: {len(transitions)}")
        for d1, d2, b1, b2 in transitions:
            print(f"    delay {d1}→{d2}: {b1} → {b2}")
    else:
        print(f"\n  NO TRANSITIONS — basin is onset-invariant at d={damping}")

    return results, transitions


def probe_d_ordering(raw_nodes, raw_edges, damping, total_steps=500):
    """Same 5 injections, different temporal orderings with inter-injection gap."""
    print(f"\n{'='*70}")
    print(f"PROBE D: Injection Ordering at d={damping}")
    print(f"  Protocol: 5 standard injections in different orders, gap=25 between each")
    print(f"{'='*70}")

    # Different orderings of the standard 5 injections
    orderings = {
        "standard":        [0, 1, 2, 3, 4],         # grail→metatron→pyramid→christ→light_codes
        "reverse":         [4, 3, 2, 1, 0],         # light_codes→christ→pyramid→metatron→grail
        "big_first":       [0, 1, 2, 3, 4],         # same as standard (already sorted big→small)
        "small_first":     [4, 3, 2, 1, 0],         # same as reverse
        "alternating":     [0, 4, 1, 3, 2],         # grail, light_codes, metatron, christ, pyramid
        "middle_out":      [2, 1, 3, 0, 4],         # pyramid, metatron, christ, grail, light_codes
        "random_a":        [3, 0, 4, 2, 1],         # christ, grail, light_codes, pyramid, metatron
        "random_b":        [1, 4, 0, 3, 2],         # metatron, light_codes, grail, christ, pyramid
        "simultaneous":    "sim",                     # all at once (no gap)
    }

    gap = 25
    results = []

    for name, order in orderings.items():
        e = make_engine(raw_nodes, raw_edges, damping)

        if order == "sim":
            # All injections at once, no gap
            for label, amt in STANDARD_INJECTION:
                e.inject(label, amt)
            e.run(total_steps)
        else:
            for idx in order:
                label, amt = STANDARD_INJECTION[idx]
                e.inject(label, amt)
                e.run(gap)
            remain = max(0, total_steps - 5 * gap)
            if remain > 0:
                e.run(remain)

        basin = get_basin(e, raw_nodes)
        if order == "sim":
            seq_desc = "all-at-once"
        else:
            seq_desc = "→".join(STANDARD_INJECTION[i][0][:4] for i in order)
        results.append({"name": name, "sequence": seq_desc, "basin": basin})
        print(f"  {name:<16} ({seq_desc}) → {basin}")

    unique = set(r["basin"] for r in results)
    print(f"\n  UNIQUE BASINS: {len(unique)}")
    for b in sorted(unique):
        configs = [r["name"] for r in results if r["basin"] == b]
        print(f"    {b}: {configs}")

    return results


def probe_e_fine_grain(raw_nodes, raw_edges, damping, param_name, param_range,
                        run_fn, total_steps=500):
    """Fine-grain sweep between two parameter values where a transition was found."""
    print(f"\n{'='*70}")
    print(f"PROBE E: Fine-Grain Resolution at d={damping}")
    print(f"  Sweeping {param_name} from {param_range[0]} to {param_range[-1]}")
    print(f"{'='*70}")

    results = []
    for val in param_range:
        basin = run_fn(val, raw_nodes, raw_edges, damping, total_steps)
        results.append({"param": val, "basin": basin})
        print(f"  {param_name}={val:>6} → {basin}")

    transitions = []
    for i in range(1, len(results)):
        if results[i]["basin"] != results[i-1]["basin"]:
            transitions.append((results[i-1]["param"], results[i]["param"],
                                results[i-1]["basin"], results[i]["basin"]))

    if transitions:
        print(f"\n  TRANSITIONS: {len(transitions)}")
        for v1, v2, b1, b2 in transitions:
            print(f"    {param_name}={v1}→{v2}: {b1} → {b2}")
        print(f"  MINIMUM DISTINGUISHING CADENCE: Δ{param_name} ≤ {transitions[0][1] - transitions[0][0]}")
    return results, transitions


def gap_runner(gap, raw_nodes, raw_edges, damping, total_steps):
    """Helper for fine-grain gap sweep."""
    e = make_engine(raw_nodes, raw_edges, damping)
    for pulse in range(5):
        e.inject("grail", 30.0)
        e.run(gap)
    used = 5 * gap
    remain = max(0, total_steps - used)
    if remain > 0:
        e.run(remain)
    return get_basin(e, raw_nodes)


def probe_f_gap_with_ordering(raw_nodes, raw_edges, damping, total_steps=500):
    """Combine gap sweep with multi-node ordered injection for richer temporal signal."""
    print(f"\n{'='*70}")
    print(f"PROBE F: Gap × Ordering Interaction at d={damping}")
    print(f"  Protocol: Standard 5-node injection with different gaps between each")
    print(f"{'='*70}")

    gaps = [1, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150]
    orderings = {
        "standard": [0, 1, 2, 3, 4],
        "reverse":  [4, 3, 2, 1, 0],
    }

    results = []
    for name, order in orderings.items():
        print(f"\n  Ordering: {name}")
        for gap in gaps:
            try:
                e = make_engine(raw_nodes, raw_edges, damping)
                for idx in order:
                    label, amt = STANDARD_INJECTION[idx]
                    e.inject(label, amt)
                    e.run(gap)
                remain = max(0, total_steps - 5 * gap)
                if remain > 0:
                    e.run(remain)
                basin = get_basin(e, raw_nodes)
                results.append({"ordering": name, "gap": gap, "basin": basin})
                print(f"    gap={gap:>4} → {basin}")
            except (OverflowError, ValueError, TypeError) as ex:
                results.append({"ordering": name, "gap": gap, "basin": f"ERROR:{ex}"})
                print(f"    gap={gap:>4} → ERROR: {ex}")

    # Cross-compare: at which gaps do orderings produce different basins?
    print(f"\n  ORDER-SENSITIVE GAPS:")
    for gap in gaps:
        basins_at_gap = {r["ordering"]: r["basin"] for r in results if r["gap"] == gap}
        if len(set(basins_at_gap.values())) > 1:
            print(f"    gap={gap}: {basins_at_gap} ← ORDERING MATTERS")
        else:
            print(f"    gap={gap}: {list(basins_at_gap.values())[0]} (order-insensitive)")

    return results


def main():
    t0 = time.time()
    raw_nodes, raw_edges = load_graph()
    all_results = {}
    all_transitions = {}

    # ======== d=5.0 — primary target (confirmed temporally sensitive) ========
    damping = 5.0
    print(f"\n\n{'#'*70}")
    print(f"# DAMPING = {damping}")
    print(f"{'#'*70}")

    # --- Probe A: Gap sweep ---
    res_a, trans_a = probe_a_gap_sweep(raw_nodes, raw_edges, damping)
    all_results[f"gap_d{damping}"] = res_a
    all_transitions[f"gap_d{damping}"] = trans_a

    # --- Probe B: Pulse count ---
    res_b, trans_b = probe_b_pulse_count(raw_nodes, raw_edges, damping)
    all_results[f"pulse_d{damping}"] = res_b
    all_transitions[f"pulse_d{damping}"] = trans_b

    # --- Probe C: Onset delay ---
    res_c, trans_c = probe_c_onset_delay(raw_nodes, raw_edges, damping)
    all_results[f"onset_d{damping}"] = res_c
    all_transitions[f"onset_d{damping}"] = trans_c

    # --- Probe D: Ordering ---
    res_d = probe_d_ordering(raw_nodes, raw_edges, damping)
    all_results[f"ordering_d{damping}"] = res_d

    # --- Probe E: Fine-grain zoom on first gap transition ---
    if trans_a:
        g1, g2 = trans_a[0][0], trans_a[0][1]
        fine_range = list(range(g1, g2 + 1))
        res_e, trans_e = probe_e_fine_grain(
            raw_nodes, raw_edges, damping, "gap",
            fine_range, gap_runner
        )
        all_results[f"fine_gap_d{damping}"] = res_e
        all_transitions[f"fine_gap_d{damping}"] = trans_e

    # ======== d=0.2 — turbulent comparison (only gap sweep) ========
    damping = 0.2
    print(f"\n\n{'#'*70}")
    print(f"# DAMPING = {damping} (turbulent comparison)")
    print(f"{'#'*70}")

    res_a2, trans_a2 = probe_a_gap_sweep(raw_nodes, raw_edges, damping)
    all_results[f"gap_d{damping}"] = res_a2
    all_transitions[f"gap_d{damping}"] = trans_a2

    res_d2 = probe_d_ordering(raw_nodes, raw_edges, damping)
    all_results[f"ordering_d{damping}"] = res_d2

    # ---- Summary ----
    elapsed = time.time() - t0
    total_trials = sum(
        len(v) for v in all_results.values()
    )
    print(f"\n\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total trials: {total_trials}")
    print(f"Elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    for key, trans in all_transitions.items():
        if trans:
            print(f"\n  {key}:")
            for v1, v2, b1, b2 in trans:
                print(f"    Δ={v2-v1}: {v1}→{v2} ({b1} → {b2})")

    # Save
    out_path = os.path.join(os.path.dirname(__file__), "data", "q7_temporal_cadence.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "experiment": "Q7_temporal_cadence",
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "total_trials": total_trials,
            "elapsed_s": round(elapsed, 1),
            "results": all_results,
            "transitions": all_transitions,
        }, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
