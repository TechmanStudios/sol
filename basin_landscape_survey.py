#!/usr/bin/env python3
"""
SOL Basin Landscape Survey
===========================

Maps which nodes become attractor basins under different parameter
regimes across the 140-node manifold.

Experiments:
    1. Baseline decay (no injection, just evolve from initial state)
    2. Per-node injection survey (inject each node individually, track basins)
    3. Parameter sweep (vary c_press and damping, track basin formation)
    4. Group-level injection (inject all spirit, all bridge, single tech)

Outputs:
    - Basin frequency map:  how often each node becomes rhoMax
    - Energy retention map: mean rho per node after equilibrium
    - Hot/cold node classification
    - Parameter phase map (c_press x damping -> dominant basin)
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))

from sol_engine import SOLEngine, compute_metrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_trial(*, c_press=0.1, damping=0.2, dt=0.12,
              inject_label=None, inject_id=None, inject_amount=50.0,
              steps=500, rng_seed=42, sample_interval=50) -> dict:
    """
    Run a single trial and return basin/metric trajectory.

    Returns:
        {
            "params": {...},
            "final_metrics": {...},
            "basin_trajectory": [(step, rhoMaxId, maxRho), ...],
            "node_rho_final": {id: rho, ...},
            "dominant_basin": id,
            "basin_visits": {id: count, ...},
        }
    """
    engine = SOLEngine.from_default_graph(
        dt=dt, c_press=c_press, damping=damping, rng_seed=rng_seed
    )

    # Inject if specified
    if inject_label:
        engine.inject(inject_label, inject_amount)
    elif inject_id is not None:
        engine.inject_by_id(inject_id, inject_amount)

    basin_trajectory = []
    basin_visits = defaultdict(int)

    for s in range(1, steps + 1):
        engine.step()
        if s % sample_interval == 0 or s == steps:
            m = engine.compute_metrics()
            bid = m["rhoMaxId"]
            basin_trajectory.append((s, bid, m["maxRho"]))
            if bid is not None:
                basin_visits[bid] = basin_visits.get(bid, 0) + 1

    final_metrics = engine.compute_metrics()
    node_rho = {n["id"]: n["rho"] for n in engine.physics.nodes}

    # Dominant basin = most frequently visited rhoMax
    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None

    return {
        "params": {"c_press": c_press, "damping": damping, "dt": dt,
                    "inject_label": inject_label, "inject_id": inject_id,
                    "inject_amount": inject_amount, "steps": steps},
        "final_metrics": final_metrics,
        "basin_trajectory": basin_trajectory,
        "node_rho_final": node_rho,
        "dominant_basin": dominant,
        "basin_visits": dict(basin_visits),
    }


def load_node_labels() -> dict:
    """Return {id: label} from the default graph."""
    graph_path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(graph_path) as f:
        data = json.load(f)
    return {n["id"]: n["label"] for n in data["rawNodes"]}


def load_node_groups() -> dict:
    """Return {id: group} from the default graph."""
    graph_path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(graph_path) as f:
        data = json.load(f)
    return {n["id"]: n.get("group", "bridge") for n in data["rawNodes"]}


# ---------------------------------------------------------------------------
# Experiment 1: Baseline Decay
# ---------------------------------------------------------------------------

def experiment_baseline():
    """Run with a single grail injection, watch natural basin formation."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 1: Baseline (single grail injection)")
    print("=" * 60)

    result = run_trial(inject_label="grail", inject_amount=50.0,
                       steps=1000, sample_interval=100)
    labels = load_node_labels()

    print(f"\nFinal metrics:")
    fm = result["final_metrics"]
    print(f"  entropy:     {fm['entropy']:.4f}")
    print(f"  mass:        {fm['mass']:.4f}")
    print(f"  maxRho:      {fm['maxRho']:.4f}")
    print(f"  rhoMaxId:    {fm['rhoMaxId']} ({labels.get(fm['rhoMaxId'], '?')})")
    print(f"  activeCount: {fm['activeCount']}")

    print(f"\nBasin trajectory:")
    for step, bid, rho in result["basin_trajectory"]:
        bid_str = f"{bid:3d}" if bid is not None else "  -"
        lbl = labels.get(bid, "(none)") if bid is not None else "(none)"
        print(f"  step {step:5d}: basin={bid_str} ({lbl:<25}) "
              f"maxRho={rho:.4f}")

    # Top 10 nodes by final rho
    sorted_rho = sorted(result["node_rho_final"].items(),
                        key=lambda x: x[1], reverse=True)[:10]
    print(f"\nTop 10 nodes by final rho:")
    for nid, rho in sorted_rho:
        print(f"  [{nid:3d}] {labels.get(nid, '?'):<25} rho={rho:.6f}")

    return result


# ---------------------------------------------------------------------------
# Experiment 2: Per-Node Injection Survey
# ---------------------------------------------------------------------------

def experiment_injection_survey():
    """Inject each node individually and track where basins form."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Per-Node Injection Survey (140 trials)")
    print("=" * 60)

    labels = load_node_labels()
    groups = load_node_groups()
    all_ids = sorted(labels.keys())

    basin_freq = defaultdict(int)       # how often each node is dominant
    injection_results = {}              # inject_id -> dominant basin id

    t0 = time.time()
    for nid in all_ids:
        result = run_trial(inject_id=nid, inject_amount=50.0,
                           steps=500, sample_interval=50)
        dominant = result["dominant_basin"]
        basin_freq[dominant] += 1
        injection_results[nid] = {
            "dominant_basin": dominant,
            "dominant_label": labels.get(dominant, "?"),
            "final_maxRho": result["final_metrics"]["maxRho"],
            "final_entropy": result["final_metrics"]["entropy"],
        }
    elapsed = time.time() - t0

    print(f"\nCompleted 140 injection trials in {elapsed:.1f}s")

    # Basin frequency: how many different injections lead to each basin
    print(f"\nBasin Frequency (which nodes attract across all injections):")
    sorted_basins = sorted(basin_freq.items(), key=lambda x: x[1], reverse=True)
    for bid, count in sorted_basins[:20]:
        pct = count / len(all_ids) * 100
        bar = "#" * int(pct / 2)
        print(f"  [{bid:3d}] {labels.get(bid, '?'):<25} "
              f"{count:3d}/140 ({pct:5.1f}%) {bar}")

    # Self-attractors: nodes that become their own basin when injected
    self_attract = [nid for nid in all_ids
                    if injection_results[nid]["dominant_basin"] == nid]
    print(f"\nSelf-attractors ({len(self_attract)} nodes held their own injection):")
    for nid in self_attract:
        print(f"  [{nid:3d}] {labels.get(nid, '?'):<25} "
              f"group={groups.get(nid, '?')}")

    # Cold nodes: never become dominant basin
    all_dominant = set(injection_results[nid]["dominant_basin"] for nid in all_ids)
    cold_nodes = [nid for nid in all_ids if nid not in all_dominant]
    print(f"\nCold nodes ({len(cold_nodes)} never became dominant basin):")
    for nid in cold_nodes[:20]:
        print(f"  [{nid:3d}] {labels.get(nid, '?'):<25} "
              f"group={groups.get(nid, '?')}")
    if len(cold_nodes) > 20:
        print(f"  ... and {len(cold_nodes) - 20} more")

    return {"basin_freq": dict(basin_freq),
            "injection_results": injection_results,
            "self_attractors": self_attract,
            "cold_nodes": cold_nodes}


# ---------------------------------------------------------------------------
# Experiment 3: Parameter Phase Diagram
# ---------------------------------------------------------------------------

def experiment_parameter_sweep():
    """Sweep c_press x damping and map dominant basins."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Parameter Phase Diagram (c_press x damping)")
    print("=" * 60)

    labels = load_node_labels()

    c_press_values = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    damping_values = [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]

    # Inject the same node each time to hold injection constant
    inject_label = "grail"  # node 1, a bridge node
    phase_map = {}
    basin_per_regime = defaultdict(int)

    t0 = time.time()
    for cp in c_press_values:
        for damp in damping_values:
            result = run_trial(c_press=cp, damping=damp,
                               inject_label=inject_label,
                               inject_amount=50.0,
                               steps=500, sample_interval=50)
            dom = result["dominant_basin"]
            phase_map[(cp, damp)] = {
                "dominant_basin": dom,
                "label": labels.get(dom, "?"),
                "entropy": result["final_metrics"]["entropy"],
                "maxRho": result["final_metrics"]["maxRho"],
                "mass": result["final_metrics"]["mass"],
                "activeCount": result["final_metrics"]["activeCount"],
            }
            basin_per_regime[dom] += 1
    elapsed = time.time() - t0

    print(f"\nCompleted {len(c_press_values) * len(damping_values)} "
          f"parameter combinations in {elapsed:.1f}s")

    # Print phase diagram as grid
    print(f"\nPhase Diagram (dominant basin ID):")
    header = "c_press\\damp  " + "  ".join(f"{d:>6.2f}" for d in damping_values)
    print(header)
    print("-" * len(header))
    for cp in c_press_values:
        row = f"  {cp:>6.2f}     "
        for damp in damping_values:
            pm = phase_map[(cp, damp)]
            bid = pm["dominant_basin"]
            row += f"  {bid:>6d}"
        print(row)

    print(f"\nPhase Diagram (dominant basin labels):")
    for cp in c_press_values:
        for damp in damping_values:
            pm = phase_map[(cp, damp)]
            print(f"  cp={cp:.2f} d={damp:.2f} -> "
                  f"[{pm['dominant_basin']:3d}] {pm['label']:<20} "
                  f"entropy={pm['entropy']:.3f} maxRho={pm['maxRho']:.4f} "
                  f"active={pm['activeCount']}")

    # How many distinct basins across all regimes?
    unique_basins = set(basin_per_regime.keys())
    print(f"\nUnique basins across all {len(phase_map)} regimes: "
          f"{len(unique_basins)}")
    for bid, cnt in sorted(basin_per_regime.items(), key=lambda x: -x[1]):
        print(f"  [{bid:3d}] {labels.get(bid, '?'):<25} "
              f"appears in {cnt} regime(s)")

    return {"phase_map": {f"{k[0]}_{k[1]}": v for k, v in phase_map.items()},
            "basin_per_regime": dict(basin_per_regime)}


# ---------------------------------------------------------------------------
# Experiment 4: Group-Level Injection
# ---------------------------------------------------------------------------

def experiment_group_injection():
    """Inject energy into node groups and track basin formation."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 4: Group-Level Injection")
    print("=" * 60)

    labels = load_node_labels()
    groups = load_node_groups()

    group_nodes = defaultdict(list)
    for nid, g in groups.items():
        group_nodes[g].append(nid)

    results = {}
    for group_name, node_ids in sorted(group_nodes.items()):
        engine = SOLEngine.from_default_graph(rng_seed=42)
        # Inject 50.0 into every node in this group
        for nid in node_ids:
            engine.inject_by_id(nid, 50.0)

        basin_visits = defaultdict(int)
        for s in range(1, 501):
            engine.step()
            if s % 50 == 0:
                m = engine.compute_metrics()
                basin_visits[m["rhoMaxId"]] = basin_visits.get(m["rhoMaxId"], 0) + 1

        final = engine.compute_metrics()
        dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None

        # Top 5 nodes by rho in this group
        node_rho = sorted(
            [(nid, n["rho"]) for n in engine.physics.nodes
             for nid in [n["id"]] if groups.get(nid) == group_name],
            key=lambda x: x[1], reverse=True
        )[:5]

        results[group_name] = {
            "injected_nodes": len(node_ids),
            "dominant_basin": dominant,
            "dominant_label": labels.get(dominant, "?"),
            "final_entropy": final["entropy"],
            "final_maxRho": final["maxRho"],
            "final_mass": final["mass"],
            "active_count": final["activeCount"],
            "top_nodes": node_rho,
        }

        print(f"\n  Group: {group_name} ({len(node_ids)} nodes injected)")
        print(f"    Dominant basin: [{dominant}] {labels.get(dominant, '?')}")
        print(f"    entropy={final['entropy']:.4f} maxRho={final['maxRho']:.4f} "
              f"mass={final['mass']:.2f} active={final['activeCount']}")
        print(f"    Top rho within group:")
        for nid, rho in node_rho:
            print(f"      [{nid:3d}] {labels.get(nid, '?'):<25} rho={rho:.4f}")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  SOL BASIN LANDSCAPE SURVEY")
    print("  140 nodes | 845 edges | Sacred Manifold")
    print("=" * 60)

    t_start = time.time()

    r1 = experiment_baseline()
    r2 = experiment_injection_survey()
    r3 = experiment_parameter_sweep()
    r4 = experiment_group_injection()

    total_time = time.time() - t_start

    # ---- Summary ----
    print("\n" + "=" * 60)
    print("  SURVEY SUMMARY")
    print("=" * 60)

    labels = load_node_labels()

    print(f"\nTotal runtime: {total_time:.1f}s")
    print(f"\nBaseline dominant basin: [{r1['dominant_basin']}] "
          f"{labels.get(r1['dominant_basin'], '?')}")

    top_basins = sorted(r2["basin_freq"].items(), key=lambda x: -x[1])[:5]
    print(f"\nTop 5 universal attractors (injection survey):")
    for bid, cnt in top_basins:
        print(f"  [{bid:3d}] {labels.get(bid, '?'):<25} attracted {cnt}/140 injections")

    print(f"\nSelf-attractors: {len(r2['self_attractors'])}")
    print(f"Cold nodes: {len(r2['cold_nodes'])}")
    print(f"Unique basins across parameter sweep: "
          f"{len(r3['basin_per_regime'])}")

    # Save results
    out_path = _SOL_ROOT / "data" / "basin_landscape_survey.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    survey_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_sec": round(total_time, 2),
        "baseline": {
            "dominant_basin": r1["dominant_basin"],
            "final_metrics": r1["final_metrics"],
            "basin_trajectory": r1["basin_trajectory"],
        },
        "injection_survey": {
            "basin_freq": r2["basin_freq"],
            "self_attractors": r2["self_attractors"],
            "cold_nodes": r2["cold_nodes"],
            "total_trials": 140,
        },
        "parameter_sweep": r3,
        "group_injection": {
            k: {kk: vv for kk, vv in v.items() if kk != "top_nodes"}
            for k, v in r4.items()
        },
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(survey_data, f, indent=2, default=str)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
