#!/usr/bin/env python3
"""
Experiment 14 — Q12: Symmetry-Breaking Group Specificity
=========================================================

Q12: "Which injection groups (spirit, christic, etc.) reliably override the
standard attractor, and is this group→basin mapping damping-dependent?"

Probe A: Full group × damping matrix (12 groups × 9 dampings = 108 trials)
Probe B: Single-node injection atlas (28 nodes × 3 dampings = 84 trials)
Probe C: Cooperation test — 1 node @ 150 vs 3 nodes @ 50 (≤30 trials)
Probe D: Energy-scaling stability (3 groups × 3 energies × 3 dampings = 27 trials)
Probe E: Cross-group mixtures (6 mixes × 3 dampings = 18 trials)

Expected: ~267 trials, ~25 min at ~6 s/trial.

Engine: tools/sol-core/sol_engine.py (SHA256: 5316e4fd...562eef, IMMUTABLE)
Graph:  tools/sol-core/default_graph.json (140 nodes, 845 edges, IMMUTABLE)
"""

from __future__ import annotations

import copy
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

# ── paths ──────────────────────────────────────────────────────────────────
_SOL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
from sol_engine import SOLEngine  # noqa: E402

# ── constants ──────────────────────────────────────────────────────────────
DT = 0.12
C_PRESS = 0.1
STEPS = 500
SAMPLE_INTERVAL = 5
TOTAL_ENERGY = 150.0  # match standard injection total

STANDARD_INJECTIONS = [
    ("grail", 40.0),
    ("metatron", 35.0),
    ("pyramid", 30.0),
    ("christ", 25.0),
    ("light codes", 20.0),
]

DAMPINGS = [0.2, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 55.0]
KEY_DAMPINGS = [0.2, 5.0, 20.0]

# 12 injection groups — each sums to 150 total energy
INJECTION_GROUPS = {
    "standard": [("grail", 40), ("metatron", 35), ("pyramid", 30),
                 ("christ", 25), ("light codes", 20)],
    "spirit_core": [("christ", 50), ("metatron", 50), ("christic", 50)],
    "spirit_periphery": [("venus", 50), ("thothhorra", 50), ("merkabah", 50)],
    "temple_cluster": [("temple doors", 50), ("temple of", 50),
                       ("rite akashic", 50)],
    "christine_solo": [("christine hayes", 150)],
    "metatronic_cluster": [("metatron", 50), ("metatronic", 50),
                           ("maia christianne", 50)],
    "bridge_low_deg": [("journey", 50), ("dragon", 50), ("moon", 50)],
    "bridge_high_deg": [("johannine grove", 50), ("mystery school", 50),
                        ("par", 50)],
    "cold_nodes": [("john", 30), ("par", 30), ("johannine grove", 30),
                   ("mystery school", 30), ("christine hayes", 30)],
    "tech_solo": [("light codes", 150)],
    "christ_solo": [("christ", 150)],
    "scattered_bridge": [("isis", 10), ("osiris", 10), ("ark", 10),
                         ("orion", 10), ("eye", 10), ("loch", 10),
                         ("maia nartoomid", 10), ("god", 10), ("pyramid", 10),
                         ("templar", 10), ("plain", 10), ("holorian", 10),
                         ("mazur", 10), ("star lineages", 10), ("sun", 10)],
}

# Single-node atlas: all 18 spirit + 10 selected bridge
ATLAS_NODES = [
    # Spirit (18)
    "christ", "temple doors", "numis'om", "metatron", "venus",
    "new earth star", "christic", "akashic practice", "thothhorra",
    "merkabah", "rite akashic", "temple of", "metatronic",
    "spirit heart", "christine hayes", "christos", "maia christianne",
    "thothhorra khandr",
    # Bridge (10 — spread of degrees)
    "grail", "pyramid", "johannine grove", "mystery school", "par",
    "john", "church", "plain", "journey", "dragon",
]

# Cross-group mixtures (75 energy each side = 150 total)
CROSS_MIXTURES = {
    "spirit+bridge_hi": [("christ", 37.5), ("metatron", 37.5),
                         ("johannine grove", 37.5), ("par", 37.5)],
    "spirit+cold": [("christic", 50), ("metatronic", 50),
                    ("john", 25), ("par", 25)],
    "temple+meta": [("temple doors", 37.5), ("temple of", 37.5),
                    ("metatron", 37.5), ("metatronic", 37.5)],
    "bridge_hi+lo": [("johannine grove", 37.5), ("mystery school", 37.5),
                     ("journey", 37.5), ("dragon", 37.5)],
    "core+periphery": [("christ", 37.5), ("metatron", 37.5),
                       ("venus", 37.5), ("thothhorra", 37.5)],
    "tech+spirit": [("light codes", 75), ("christ", 37.5), ("christic", 37.5)],
}


# ── graph utilities ────────────────────────────────────────────────────────
def load_graph():
    path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(path) as f:
        data = json.load(f)
    return data["rawNodes"], data["rawEdges"]


def get_labels(raw_nodes):
    return {n["id"]: n["label"] for n in raw_nodes}


def get_groups(raw_nodes):
    return {n["id"]: n.get("group", "bridge") for n in raw_nodes}


def make_engine(raw_nodes, raw_edges, damping, seed=42):
    return SOLEngine.from_graph(
        raw_nodes, raw_edges,
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed,
    )


# ── analysis ───────────────────────────────────────────────────────────────
def run_and_analyze(engine, steps=STEPS, sample_every=SAMPLE_INTERVAL):
    """Step engine, collect samples, compute metrics."""
    basin_visits: dict[int, int] = defaultdict(int)
    rho_samples: list[list[float]] = []

    for s in range(1, steps + 1):
        engine.step()
        if s % sample_every == 0:
            m = engine.compute_metrics()
            bid = m["rhoMaxId"]
            if bid is not None:
                basin_visits[bid] = basin_visits.get(bid, 0) + 1
            rho_samples.append([n["rho"] for n in engine.physics.nodes])

    final = engine.compute_metrics()

    # Coherence
    rho_arr = np.array(rho_samples) if rho_samples else np.zeros((1, len(engine.physics.nodes)))
    id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}
    inj_ids = [1, 2, 9, 23, 29]
    inj_indices = [id_to_idx[nid] for nid in inj_ids if nid in id_to_idx]
    corrs = []
    for a in range(len(inj_indices)):
        for b in range(a + 1, len(inj_indices)):
            t1 = rho_arr[:, inj_indices[a]].copy()
            t2 = rho_arr[:, inj_indices[b]].copy()
            r1, r2 = np.ptp(t1), np.ptp(t2)
            if r1 > 0 and r2 > 0:
                t1n = (t1 - t1.mean()) / r1
                t2n = (t2 - t2.mean()) / r2
                c = np.corrcoef(t1n, t2n)[0, 1]
                if not np.isnan(c):
                    corrs.append(abs(c))
    coherence = float(np.mean(corrs)) if corrs else 0.0

    # Iton
    node_edges_map: dict[int, list] = defaultdict(list)
    for ei, e in enumerate(engine.physics.edges):
        node_edges_map[e["from"]].append((ei, "from"))
        node_edges_map[e["to"]].append((ei, "to"))
    n_pass = 0
    total_active = 0
    for ni, n in enumerate(engine.physics.nodes):
        nid = n["id"]
        inflow = outflow = 0.0
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
    iton = n_pass / total_active if total_active > 0 else 0.0

    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
    dom_frac = (basin_visits.get(dominant, 0) / max(1, sum(basin_visits.values()))
                if dominant else 0.0)

    return {
        "dominant_basin": dominant,
        "dominant_basin_frac": round(dom_frac, 3),
        "iton_score": round(iton, 3),
        "coherence": round(coherence, 4),
        "final_mass": round(final["mass"], 4),
        "final_entropy": round(final["entropy"], 4),
    }


def fmt(nid, labels):
    if nid is None:
        return "None"
    return f"{labels.get(nid, '?')}[{nid}]"


# ── probes ─────────────────────────────────────────────────────────────────
def probe_a(raw_nodes, raw_edges, labels):
    """Full group × damping matrix: 12 groups × 9 dampings."""
    print("\n" + "=" * 70)
    print("PROBE A: Group × Damping Matrix (12 groups × 9 dampings)")
    print("=" * 70)

    results = []
    trials = 0

    # First get standard basins as reference
    std_basins = {}
    for d in DAMPINGS:
        eng = make_engine(raw_nodes, raw_edges, d)
        for lbl, amt in STANDARD_INJECTIONS:
            eng.inject(lbl, amt)
        a = run_and_analyze(eng)
        std_basins[d] = a["dominant_basin"]
        trials += 1

    for group_name, injections in INJECTION_GROUPS.items():
        print(f"\n  Group: {group_name}")
        for d in DAMPINGS:
            eng = make_engine(raw_nodes, raw_edges, d)
            for lbl, amt in injections:
                eng.inject(lbl, float(amt))
            a = run_and_analyze(eng)

            shifted = a["dominant_basin"] != std_basins[d]
            tag = "SHIFT" if shifted else "same"
            print(f"    d={d:5.1f}: basin={fmt(a['dominant_basin'], labels):30s}  "
                  f"iton={a['iton_score']:.3f}  coh={a['coherence']:.4f}  "
                  f"mass={a['final_mass']:.4f}  [{tag}]")

            results.append({
                "group": group_name,
                "damping": d,
                "basin_id": a["dominant_basin"],
                "basin_label": fmt(a["dominant_basin"], labels),
                "iton": a["iton_score"],
                "coherence": a["coherence"],
                "mass": a["final_mass"],
                "entropy": a["final_entropy"],
                "std_basin_id": std_basins[d],
                "std_basin_label": fmt(std_basins[d], labels),
                "shifted": shifted,
            })
            trials += 1

    # Summary table
    print("\n  --- SHIFT SUMMARY ---")
    print(f"  {'Group':<22s}", end="")
    for d in DAMPINGS:
        print(f"  d={d:<5.1f}", end="")
    print()
    for group_name in INJECTION_GROUPS:
        print(f"  {group_name:<22s}", end="")
        for d in DAMPINGS:
            row = [r for r in results if r["group"] == group_name and r["damping"] == d]
            if row and row[0]["shifted"]:
                print(f"  {'SHIFT':>7s}", end="")
            else:
                print(f"  {'---':>7s}", end="")
        print()

    # Group reliability: how many dampings shifted?
    print("\n  --- GROUP RELIABILITY ---")
    for group_name in INJECTION_GROUPS:
        group_rows = [r for r in results if r["group"] == group_name]
        n_shift = sum(1 for r in group_rows if r["shifted"])
        unique_basins = len(set(r["basin_id"] for r in group_rows))
        print(f"  {group_name:<22s}: {n_shift}/9 dampings shifted, "
              f"{unique_basins} unique basins")

    return results, trials


def probe_b(raw_nodes, raw_edges, labels):
    """Single-node injection atlas: 28 nodes × 3 dampings."""
    print("\n" + "=" * 70)
    print("PROBE B: Single-Node Injection Atlas (28 nodes × 3 dampings)")
    print("=" * 70)

    groups_map = get_groups(raw_nodes)
    node_lookup = {n["label"]: n["id"] for n in raw_nodes}

    # Standard basins reference
    std_basins = {}
    trials = 0
    for d in KEY_DAMPINGS:
        eng = make_engine(raw_nodes, raw_edges, d)
        for lbl, amt in STANDARD_INJECTIONS:
            eng.inject(lbl, amt)
        a = run_and_analyze(eng)
        std_basins[d] = a["dominant_basin"]
        trials += 1

    results = []
    for node_label in ATLAS_NODES:
        nid = node_lookup.get(node_label)
        if nid is None:
            print(f"  WARNING: node '{node_label}' not found, skipping")
            continue
        grp = groups_map.get(nid, "bridge")
        print(f"\n  Node: {node_label}[{nid}] (group={grp})")
        for d in KEY_DAMPINGS:
            eng = make_engine(raw_nodes, raw_edges, d)
            eng.inject(node_label, TOTAL_ENERGY)
            a = run_and_analyze(eng)
            shifted = a["dominant_basin"] != std_basins[d]
            tag = "SHIFT" if shifted else "same"
            print(f"    d={d:5.1f}: basin={fmt(a['dominant_basin'], labels):30s}  "
                  f"mass={a['final_mass']:.4f}  [{tag}]")
            results.append({
                "node_label": node_label,
                "node_id": nid,
                "node_group": grp,
                "damping": d,
                "basin_id": a["dominant_basin"],
                "basin_label": fmt(a["dominant_basin"], labels),
                "iton": a["iton_score"],
                "coherence": a["coherence"],
                "mass": a["final_mass"],
                "shifted": shifted,
            })
            trials += 1

    # Summary: which nodes are symmetry breakers?
    print("\n  --- SYMMETRY BREAKERS ---")
    breakers = {}
    for r in results:
        k = r["node_label"]
        if k not in breakers:
            breakers[k] = {"shifts": 0, "total": 0, "group": r["node_group"]}
        breakers[k]["total"] += 1
        if r["shifted"]:
            breakers[k]["shifts"] += 1

    for lbl, info in sorted(breakers.items(), key=lambda x: x[1]["shifts"],
                             reverse=True):
        if info["shifts"] > 0:
            print(f"  {lbl:<25s} ({info['group']:>6s}): "
                  f"{info['shifts']}/{info['total']} dampings shifted")

    return results, trials


def probe_c(raw_nodes, raw_edges, labels, probe_a_results):
    """Cooperation test: does basin shift require the group or just one node?"""
    print("\n" + "=" * 70)
    print("PROBE C: Group Cooperation Test")
    print("=" * 70)

    # Find groups that shifted at d=0.2 or d=5.0
    shifting_groups = set()
    for r in probe_a_results:
        if r["shifted"] and r["damping"] in [0.2, 5.0]:
            shifting_groups.add(r["group"])

    if not shifting_groups:
        print("  No groups shifted at d=0.2 or d=5.0 — skipping cooperation test")
        return [], 0

    results = []
    trials = 0

    for group_name in sorted(shifting_groups):
        if group_name == "standard":
            continue
        injections = INJECTION_GROUPS[group_name]
        # Skip solo groups
        if len(injections) == 1:
            print(f"\n  {group_name}: solo injection, skip cooperation test")
            continue

        print(f"\n  Group: {group_name}")
        for d in [0.2, 5.0]:
            # Run full group injection (3 nodes × 50 = 150)
            eng_group = make_engine(raw_nodes, raw_edges, d)
            for lbl, amt in injections:
                eng_group.inject(lbl, float(amt))
            a_group = run_and_analyze(eng_group)
            trials += 1

            # Run each node solo at 150
            solo_results = []
            for lbl, _ in injections:
                eng_solo = make_engine(raw_nodes, raw_edges, d)
                eng_solo.inject(lbl, TOTAL_ENERGY)
                a_solo = run_and_analyze(eng_solo)
                solo_results.append((lbl, a_solo["dominant_basin"]))
                trials += 1

            group_basin = a_group["dominant_basin"]
            solo_basins = [s[1] for s in solo_results]
            cooperative = group_basin not in solo_basins
            tag = "COOPERATIVE" if cooperative else "DOMINATED"

            solo_str = ", ".join(f"{s[0]}→{fmt(s[1], labels)}" for s in solo_results)
            print(f"    d={d:5.1f}: group→{fmt(group_basin, labels):25s}  "
                  f"solos=[{solo_str}]  [{tag}]")

            results.append({
                "group": group_name,
                "damping": d,
                "group_basin": group_basin,
                "group_basin_label": fmt(group_basin, labels),
                "solo_basins": [{
                    "node": s[0],
                    "basin_id": s[1],
                    "basin_label": fmt(s[1], labels),
                } for s in solo_results],
                "cooperative": cooperative,
            })

    return results, trials


def probe_d(raw_nodes, raw_edges, labels, probe_a_results):
    """Energy scaling: does basin shift hold at 50, 150, 300 total energy?"""
    print("\n" + "=" * 70)
    print("PROBE D: Energy Scaling Stability")
    print("=" * 70)

    # Pick 3-4 groups that shifted most
    shift_counts = defaultdict(int)
    for r in probe_a_results:
        if r["shifted"]:
            shift_counts[r["group"]] += 1
    top_groups = sorted(shift_counts, key=shift_counts.get, reverse=True)[:4]
    if not top_groups:
        print("  No groups shifted — skipping scaling test")
        return [], 0

    energies = [50.0, 150.0, 300.0]
    results = []
    trials = 0

    for group_name in top_groups:
        injections = INJECTION_GROUPS[group_name]
        print(f"\n  Group: {group_name}")

        for total_e in energies:
            # Scale each injection proportionally
            orig_total = sum(amt for _, amt in injections)
            scale = total_e / orig_total

            for d in KEY_DAMPINGS:
                eng = make_engine(raw_nodes, raw_edges, d)
                for lbl, amt in injections:
                    eng.inject(lbl, float(amt) * scale)
                a = run_and_analyze(eng)
                trials += 1

                print(f"    E={total_e:5.0f}, d={d:5.1f}: "
                      f"basin={fmt(a['dominant_basin'], labels):25s}  "
                      f"mass={a['final_mass']:.4f}")

                results.append({
                    "group": group_name,
                    "total_energy": total_e,
                    "damping": d,
                    "basin_id": a["dominant_basin"],
                    "basin_label": fmt(a["dominant_basin"], labels),
                    "mass": a["final_mass"],
                    "iton": a["iton_score"],
                })

    # Check stability: same basin across all energies?
    print("\n  --- SCALING STABILITY ---")
    for group_name in top_groups:
        for d in KEY_DAMPINGS:
            rows = [r for r in results
                    if r["group"] == group_name and r["damping"] == d]
            basins = [r["basin_id"] for r in rows]
            stable = len(set(basins)) == 1
            tag = "STABLE" if stable else "VARIABLE"
            basin_str = " / ".join(fmt(b, labels) for b in basins)
            print(f"  {group_name:<20s} d={d:5.1f}: {basin_str}  [{tag}]")

    return results, trials


def probe_e(raw_nodes, raw_edges, labels):
    """Cross-group mixtures: do 50/50 mixes create novel basins?"""
    print("\n" + "=" * 70)
    print("PROBE E: Cross-Group Mixtures")
    print("=" * 70)

    # Get standard basins for reference
    std_basins = {}
    trials = 0
    for d in KEY_DAMPINGS:
        eng = make_engine(raw_nodes, raw_edges, d)
        for lbl, amt in STANDARD_INJECTIONS:
            eng.inject(lbl, amt)
        a = run_and_analyze(eng)
        std_basins[d] = a["dominant_basin"]
        trials += 1

    # Also collect all basins seen in Probe A for novelty check
    results = []

    for mix_name, injections in CROSS_MIXTURES.items():
        print(f"\n  Mix: {mix_name}")
        for d in KEY_DAMPINGS:
            eng = make_engine(raw_nodes, raw_edges, d)
            for lbl, amt in injections:
                eng.inject(lbl, float(amt))
            a = run_and_analyze(eng)
            shifted = a["dominant_basin"] != std_basins[d]
            tag = "SHIFT" if shifted else "same"
            trials += 1

            print(f"    d={d:5.1f}: basin={fmt(a['dominant_basin'], labels):30s}  "
                  f"iton={a['iton_score']:.3f}  [{tag}]")

            results.append({
                "mixture": mix_name,
                "damping": d,
                "basin_id": a["dominant_basin"],
                "basin_label": fmt(a["dominant_basin"], labels),
                "iton": a["iton_score"],
                "coherence": a["coherence"],
                "mass": a["final_mass"],
                "shifted": shifted,
            })

    return results, trials


# ── main ───────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 70)
    print("EXPERIMENT 14 — Q12: Symmetry-Breaking Group Specificity")
    print("=" * 70)

    raw_nodes, raw_edges = load_graph()
    labels = get_labels(raw_nodes)
    total_trials = 0

    # --- Probe A ---
    pa_results, pa_trials = probe_a(raw_nodes, raw_edges, labels)
    total_trials += pa_trials

    # --- Probe B ---
    pb_results, pb_trials = probe_b(raw_nodes, raw_edges, labels)
    total_trials += pb_trials

    # --- Probe C ---
    pc_results, pc_trials = probe_c(raw_nodes, raw_edges, labels, pa_results)
    total_trials += pc_trials

    # --- Probe D ---
    pd_results, pd_trials = probe_d(raw_nodes, raw_edges, labels, pa_results)
    total_trials += pd_trials

    # --- Probe E ---
    pe_results, pe_trials = probe_e(raw_nodes, raw_edges, labels)
    total_trials += pe_trials

    elapsed = time.time() - t0

    # ── grand summary ──
    print("\n" + "=" * 70)
    print("GRAND SUMMARY")
    print("=" * 70)

    # Probe A summary
    n_shifting_groups = len(set(r["group"] for r in pa_results if r["shifted"]))
    total_shifts = sum(1 for r in pa_results if r["shifted"])
    all_basins = set(r["basin_id"] for r in pa_results if r["basin_id"] is not None)
    print(f"\n  Probe A: {n_shifting_groups}/{len(INJECTION_GROUPS)} groups can shift basins")
    print(f"           {total_shifts}/{len(pa_results)} group×damping combinations shift")
    print(f"           {len(all_basins)} unique basins across all groups")

    # Probe B summary
    breakers = set()
    for r in pb_results:
        if r["shifted"]:
            breakers.add(r["node_label"])
    print(f"\n  Probe B: {len(breakers)}/{len(ATLAS_NODES)} nodes are symmetry breakers")
    pb_spirit_break = sum(1 for lbl in breakers
                          if any(r["node_group"] == "spirit"
                                 for r in pb_results if r["node_label"] == lbl))
    pb_bridge_break = len(breakers) - pb_spirit_break
    print(f"           {pb_spirit_break} spirit, {pb_bridge_break} bridge")

    # Probe C summary
    if pc_results:
        n_coop = sum(1 for r in pc_results if r["cooperative"])
        print(f"\n  Probe C: {n_coop}/{len(pc_results)} cooperative (group ≠ any solo)")
    else:
        print("\n  Probe C: skipped")

    # Probe D summary
    if pd_results:
        stable_count = 0
        total_check = 0
        for g in set(r["group"] for r in pd_results):
            for d in KEY_DAMPINGS:
                rows = [r for r in pd_results if r["group"] == g and r["damping"] == d]
                basins = set(r["basin_id"] for r in rows)
                total_check += 1
                if len(basins) == 1:
                    stable_count += 1
        print(f"\n  Probe D: {stable_count}/{total_check} group×damping combos "
              f"energy-stable")

    # Probe E summary
    if pe_results:
        mix_shifts = sum(1 for r in pe_results if r["shifted"])
        print(f"\n  Probe E: {mix_shifts}/{len(pe_results)} cross-group mixtures shift basin")

    print(f"\n  Total trials: {total_trials}")
    print(f"  Total time:   {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # ── save data ──
    data_dir = _SOL_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    out_path = data_dir / "q12_symmetry_breaking.json"

    payload = {
        "experiment": "14_q12_symmetry_breaking",
        "total_trials": total_trials,
        "elapsed_s": round(elapsed, 1),
        "probe_a": pa_results,
        "probe_b": pb_results,
        "probe_c": pc_results,
        "probe_d": pd_results,
        "probe_e": pe_results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  Data saved to {out_path}")


if __name__ == "__main__":
    main()
