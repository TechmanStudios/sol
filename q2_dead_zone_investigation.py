#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
  Q2 DEAD ZONE PHYSICS — Deep Investigation
  Experiment 12: Why does christic[22] become the deterministic
  attractor across d=12-40 under standard injection?
═══════════════════════════════════════════════════════════════════════

  Probes:
    A  Energy Flow Tracing — per-step rho tracking from injection to attractor
    B  Injection Ablation — which injection, when removed, breaks the lock?
    C  Neighbor Gateway Severance — which mega-hub connection is critical?
    D  Damping Transition Fingerprint — fine sweep d=8-16 boundary
    E  Energy Retention Race — spirit-node half-life comparison
    F  Phase Gating Knockout — does disabling heartbeat eliminate advantage?

  Uses sol_engine.py (IMMUTABLE, SHA256: 5316e4fd...562eef)
  Graph: default_graph.json (140 nodes, 845 edges, IMMUTABLE)
"""

import sys, os, json, time, math, copy
import numpy as np
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools" / "sol-core"))
from sol_engine import SOLEngine, SOLPhysics, create_engine, compute_metrics, snapshot_state, restore_state

# ── Constants ──────────────────────────────────────────────────────────
GRAPH_PATH = Path(__file__).resolve().parent / "tools" / "sol-core" / "default_graph.json"
DT = 0.12
C_PRESS = 0.1
STEPS = 500
SAMPLE_INTERVAL = 5

STANDARD_INJECTIONS = [
    ("grail", 40), ("metatron", 35), ("pyramid", 30),
    ("christ", 25), ("light_codes", 20),
]
INJECTION_LABELS = [lbl for lbl, _ in STANDARD_INJECTIONS]
TOTAL_INJECTION = sum(a for _, a in STANDARD_INJECTIONS)  # 150

# Known IDs
CHRISTIC_ID = 22
CHRIST_ID = 2
MEGA_HUBS = {79: "par", 82: "johannine grove", 89: "mystery school"}

# ── Helpers ────────────────────────────────────────────────────────────
def load_graph():
    with open(GRAPH_PATH) as f:
        g = json.load(f)
    return g["rawNodes"], g["rawEdges"]

def make_engine(damping, raw_nodes=None, raw_edges=None):
    if raw_nodes and raw_edges:
        return SOLEngine.from_graph(raw_nodes, raw_edges, dt=DT, c_press=C_PRESS, damping=damping, rng_seed=42)
    return SOLEngine.from_default_graph(dt=DT, c_press=C_PRESS, damping=damping, rng_seed=42)

def apply_standard(engine, exclude_label=None):
    for lbl, amt in STANDARD_INJECTIONS:
        if exclude_label and lbl == exclude_label:
            continue
        engine.inject(lbl, amt)

def get_basin(engine):
    m = engine.compute_metrics()
    return m["rhoMaxId"]

def get_label_map(raw_nodes):
    return {n["id"]: n["label"] for n in raw_nodes}

def get_group_map(raw_nodes):
    return {n["id"]: n.get("group", "bridge") for n in raw_nodes}

def fmt(nid, labels):
    return f"{labels.get(nid, '?')}[{nid}]"

RAW_NODES, RAW_EDGES = load_graph()
LABELS = get_label_map(RAW_NODES)
GROUPS = get_group_map(RAW_NODES)
ALL_IDS = [n["id"] for n in RAW_NODES]

# Build adjacency
ADJ = defaultdict(set)
DEG = defaultdict(int)
for e in RAW_EDGES:
    ADJ[e["from"]].add(e["to"])
    ADJ[e["to"]].add(e["from"])
    DEG[e["from"]] += 1
    DEG[e["to"]] += 1

SPIRIT_IDS = sorted([nid for nid in ALL_IDS if GROUPS[nid] == "spirit"])

# ══════════════════════════════════════════════════════════════════════
# PROBE A: Energy Flow Tracing
# ══════════════════════════════════════════════════════════════════════
def probe_a_energy_flow():
    """Track per-node rho at every sample step in the dead zone.
    Identify which nodes accumulate energy and when christic[22] overtakes."""
    print("\n" + "=" * 70)
    print("  PROBE A: ENERGY FLOW TRACING")
    print("  Track rho over 500 steps at d=20, sample every 5 steps")
    print("=" * 70)

    engine = make_engine(20.0)
    apply_standard(engine)

    # Track rho for key nodes: injection sites + spirit nodes + mega-hubs + christic
    track_ids = set()
    INJ_NAME_TO_ID = {"grail": 1, "metatron": 9, "pyramid": 29, "christ": 2, "light_codes": 23}
    for lbl, _ in STANDARD_INJECTIONS:
        track_ids.add(INJ_NAME_TO_ID[lbl])
    track_ids.update(SPIRIT_IDS)
    track_ids.update(MEGA_HUBS.keys())
    track_ids.add(CHRISTIC_ID)
    track_ids = sorted(track_ids)

    rho_traces = {nid: [] for nid in track_ids}
    leader_trace = []  # (step, leader_id, leader_rho) at each sample

    for s in range(1, STEPS + 1):
        engine.step()
        if s % SAMPLE_INTERVAL == 0:
            states = {n["id"]: n["rho"] for n in engine.physics.nodes}
            for nid in track_ids:
                rho_traces[nid].append(states[nid])
            # Find current leader
            max_rho = 0
            leader = None
            for nid in ALL_IDS:
                if states[nid] > max_rho:
                    max_rho = states[nid]
                    leader = nid
            leader_trace.append((s, leader, max_rho))

    # Analysis: when does christic first become leader?
    first_lead_step = None
    for s, lid, _ in leader_trace:
        if lid == CHRISTIC_ID:
            first_lead_step = s
            break

    # Track lead changes
    lead_changes = []
    prev_leader = None
    for s, lid, rho in leader_trace:
        if lid != prev_leader:
            lead_changes.append((s, lid, rho))
            prev_leader = lid

    final_m = engine.compute_metrics()

    print(f"\n  Final basin: {fmt(final_m['rhoMaxId'], LABELS)}")
    print(f"  Christic first leads at step: {first_lead_step}")
    print(f"  Lead changes ({len(lead_changes)}):")
    for s, lid, rho in lead_changes:
        print(f"    step={s:3d} → {fmt(lid, LABELS):40s} rho={rho:.4e}")

    # Energy at step 50, 100, 250, 500 for key nodes
    sample_steps = [10, 20, 50, 100]  # indices into sampled (every 5 steps)
    print(f"\n  Rho snapshots at key steps:")
    for si in sample_steps:
        if si < len(rho_traces[CHRISTIC_ID]):
            actual_step = (si + 1) * SAMPLE_INTERVAL
            print(f"  step={actual_step}:")
            # Sort by rho descending
            rho_at = [(nid, rho_traces[nid][si]) for nid in track_ids if rho_traces[nid][si] > 1e-10]
            rho_at.sort(key=lambda x: -x[1])
            for nid, rho in rho_at[:8]:
                marker = " ◄◄ CHRISTIC" if nid == CHRISTIC_ID else ""
                print(f"    {fmt(nid, LABELS):40s} rho={rho:.4e}{marker}")

    # What fraction of total energy does christic hold at each sample?
    christic_frac = []
    for i in range(len(rho_traces[CHRISTIC_ID])):
        total = sum(rho_traces[nid][i] for nid in track_ids)
        frac = rho_traces[CHRISTIC_ID][i] / max(total, 1e-30)
        christic_frac.append(frac)
    max_frac = max(christic_frac)
    max_frac_step = (christic_frac.index(max_frac) + 1) * SAMPLE_INTERVAL

    print(f"\n  Christic[22] energy fraction:")
    print(f"    Max fraction: {max_frac:.4f} at step {max_frac_step}")
    print(f"    Final fraction: {christic_frac[-1]:.4f}")

    result = {
        "final_basin": final_m["rhoMaxId"],
        "christic_first_lead_step": first_lead_step,
        "n_lead_changes": len(lead_changes),
        "lead_changes": [(s, lid, round(rho, 6)) for s, lid, rho in lead_changes],
        "christic_max_frac": round(max_frac, 6),
        "christic_max_frac_step": max_frac_step,
    }
    return result


# ══════════════════════════════════════════════════════════════════════
# PROBE B: Injection Ablation
# ══════════════════════════════════════════════════════════════════════
def probe_b_injection_ablation():
    """Remove each injection one at a time. Which one breaks the christic lock?"""
    print("\n" + "=" * 70)
    print("  PROBE B: INJECTION ABLATION")
    print("  5 injections × 6 damping values = 30 trials + 6 baseline")
    print("=" * 70)

    damping_values = [12, 15, 20, 25, 30, 40]
    results = {}

    # Baseline
    print("\n  Baseline (full injection):")
    for d in damping_values:
        engine = make_engine(float(d))
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        print(f"    d={d:2d}: basin={fmt(basin, LABELS)}")
        results[f"baseline_d{d}"] = basin

    # Ablation
    print("\n  Ablation (remove one at a time):")
    ablation_results = {}
    for exclude in INJECTION_LABELS:
        ablation_results[exclude] = {}
        excluded_amt = dict(STANDARD_INJECTIONS)[exclude]
        print(f"\n  Excluding {exclude} (-{excluded_amt}):")
        for d in damping_values:
            engine = make_engine(float(d))
            apply_standard(engine, exclude_label=exclude)
            engine.run(STEPS)
            basin = get_basin(engine)
            is_christic = basin == CHRISTIC_ID
            marker = "✓ christic" if is_christic else "✗ DIFFERENT"
            print(f"    d={d:2d}: basin={fmt(basin, LABELS):40s} {marker}")
            ablation_results[exclude][d] = {"basin": basin, "is_christic": is_christic}

    # Redistribution: inject excluded amount into remaining targets
    print("\n  Redistribution (excluded amount split among remaining):")
    redist_results = {}
    for exclude in INJECTION_LABELS:
        excluded_amt = dict(STANDARD_INJECTIONS)[exclude]
        remaining = [(l, a) for l, a in STANDARD_INJECTIONS if l != exclude]
        extra_each = excluded_amt / len(remaining)
        redist_results[exclude] = {}
        for d in [15, 20, 30]:
            engine = make_engine(float(d))
            for lbl, amt in remaining:
                engine.inject(lbl, amt + extra_each)
            engine.run(STEPS)
            basin = get_basin(engine)
            print(f"    excl={exclude:12s} d={d:2d}: basin={fmt(basin, LABELS)}")
            redist_results[exclude][d] = basin

    result = {
        "baselines": results,
        "ablation": {k: {str(d): v for d, v in vals.items()} for k, vals in ablation_results.items()},
        "redistribution": {k: {str(d): v for d, v in vals.items()} for k, vals in redist_results.items()},
    }
    return result


# ══════════════════════════════════════════════════════════════════════
# PROBE C: Neighbor Gateway Severance
# ══════════════════════════════════════════════════════════════════════
def probe_c_gateway_severance():
    """Sever christic[22]'s connection to each mega-hub individually.
    Which one, when cut, breaks the lock?"""
    print("\n" + "=" * 70)
    print("  PROBE C: NEIGHBOR GATEWAY SEVERANCE")
    print("  Cut 1 of 8 neighbors × 6 damping = 48 trials + 6 baseline")
    print("=" * 70)

    neighbors_22 = sorted(ADJ[CHRISTIC_ID])
    damping_values = [12, 15, 20, 25, 30, 40]

    # Baseline
    print("\n  Baseline (full graph):")
    baselines = {}
    for d in damping_values:
        engine = make_engine(float(d))
        apply_standard(engine)
        engine.run(STEPS)
        baselines[d] = get_basin(engine)
        print(f"    d={d:2d}: basin={fmt(baselines[d], LABELS)}")

    # Severance
    print("\n  Sever each neighbor of christic[22]:")
    sever_results = {}
    for cut_id in neighbors_22:
        sever_results[cut_id] = {}
        print(f"\n  Severing [{cut_id}] {LABELS[cut_id]} (deg={DEG[cut_id]}):")
        for d in damping_values:
            # Build modified edge list without the christic-neighbor edge
            mod_edges = [e for e in RAW_EDGES
                         if not ((e["from"] == CHRISTIC_ID and e["to"] == cut_id)
                                 or (e["from"] == cut_id and e["to"] == CHRISTIC_ID))]
            engine = make_engine(float(d), RAW_NODES, mod_edges)
            apply_standard(engine)
            engine.run(STEPS)
            basin = get_basin(engine)
            is_christic = basin == CHRISTIC_ID
            changed = "CHANGED!" if not is_christic else "same"
            print(f"    d={d:2d}: basin={fmt(basin, LABELS):40s} {changed}")
            sever_results[cut_id][d] = {"basin": basin, "is_christic": is_christic}

    # Multi-sever: cut ALL mega-hubs at once
    print("\n  Sever ALL mega-hubs (par+johannine grove+mystery school):")
    mega_ids = list(MEGA_HUBS.keys())
    multi_sever_results = {}
    for d in damping_values:
        mod_edges = [e for e in RAW_EDGES
                     if not ((e["from"] == CHRISTIC_ID and e["to"] in mega_ids)
                             or (e["from"] in mega_ids and e["to"] == CHRISTIC_ID))]
        engine = make_engine(float(d), RAW_NODES, mod_edges)
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        changed = "CHANGED!" if basin != CHRISTIC_ID else "same"
        print(f"    d={d:2d}: basin={fmt(basin, LABELS):40s} {changed}")
        multi_sever_results[d] = basin

    # Sever christ[2] specifically — most direct injection neighbor
    print("\n  Sever christ[2] (direct injection neighbor):")
    christ_sever = {}
    for d in damping_values:
        mod_edges = [e for e in RAW_EDGES
                     if not ((e["from"] == CHRISTIC_ID and e["to"] == CHRIST_ID)
                             or (e["from"] == CHRIST_ID and e["to"] == CHRISTIC_ID))]
        engine = make_engine(float(d), RAW_NODES, mod_edges)
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        changed = "CHANGED!" if basin != CHRISTIC_ID else "same"
        print(f"    d={d:2d}: basin={fmt(basin, LABELS):40s} {changed}")
        christ_sever[d] = basin

    result = {
        "baselines": {str(d): v for d, v in baselines.items()},
        "sever_individual": {
            str(cut_id): {LABELS[cut_id]: {str(d): v for d, v in vals.items()}}
            for cut_id, vals in sever_results.items()
        },
        "sever_all_mega_hubs": {str(d): v for d, v in multi_sever_results.items()},
        "sever_christ": {str(d): v for d, v in christ_sever.items()},
    }
    return result


# ══════════════════════════════════════════════════════════════════════
# PROBE D: Damping Transition Fingerprint
# ══════════════════════════════════════════════════════════════════════
def probe_d_transition_fingerprint():
    """Fine sweep d=8-16 in 0.25 steps to find the exact transition point.
    Track entropy, mass, active count, and basin at each value."""
    print("\n" + "=" * 70)
    print("  PROBE D: DAMPING TRANSITION FINGERPRINT")
    print("  d=8.0 to 16.0 in 0.25 steps = 33 trials")
    print("=" * 70)

    damp_values = [round(8.0 + i * 0.25, 2) for i in range(33)]
    results = []
    prev_basin = None

    for d in damp_values:
        engine = make_engine(d)
        apply_standard(engine)
        engine.run(STEPS)
        m = engine.compute_metrics()
        basin = m["rhoMaxId"]

        transition = ""
        if prev_basin is not None and basin != prev_basin:
            transition = f"  ◄◄ TRANSITION from {fmt(prev_basin, LABELS)}"
        prev_basin = basin

        print(f"  d={d:5.2f}  basin={fmt(basin, LABELS):35s} entropy={m['entropy']:.4f} "
              f"mass={m['mass']:.4e} active={m['activeCount']:3d}{transition}")

        results.append({
            "damping": d,
            "basin": basin,
            "basin_label": LABELS.get(basin, "?"),
            "entropy": round(m["entropy"], 6),
            "mass": round(m["mass"], 8),
            "active": m["activeCount"],
            "maxRho": round(m["maxRho"], 8),
        })

    # Ultra-fine sweep around detected transition
    transitions = []
    for i in range(1, len(results)):
        if results[i]["basin"] != results[i-1]["basin"]:
            transitions.append((results[i-1]["damping"], results[i]["damping"]))

    if transitions:
        print(f"\n  ULTRA-FINE SWEEP around transition(s):")
        for d_low, d_high in transitions:
            ultra_values = [round(d_low + i * 0.05, 3) for i in range(int((d_high - d_low) / 0.05) + 2)]
            for d in ultra_values:
                engine = make_engine(d)
                apply_standard(engine)
                engine.run(STEPS)
                m = engine.compute_metrics()
                basin = m["rhoMaxId"]
                print(f"    d={d:.3f}  basin={fmt(basin, LABELS):35s} entropy={m['entropy']:.4f}")

    result = {
        "sweep": results,
        "transitions": transitions,
    }
    return result


# ══════════════════════════════════════════════════════════════════════
# PROBE E: Energy Retention Race
# ══════════════════════════════════════════════════════════════════════
def probe_e_retention_race():
    """Track per-node rho decay curves for all spirit nodes.
    Measure effective half-life and compare at d=5, d=20, d=40."""
    print("\n" + "=" * 70)
    print("  PROBE E: ENERGY RETENTION RACE")
    print("  18 spirit nodes × 3 damping = 54 solo-injection trials")
    print("=" * 70)

    damping_values = [5.0, 20.0, 40.0]
    results = {}

    for d in damping_values:
        print(f"\n  d={d}:")
        spirit_data = []
        for sid in SPIRIT_IDS:
            engine = make_engine(d)
            # Inject ONLY into this spirit node
            engine.inject_by_id(sid, 50.0)

            rho_trace = []
            for s in range(1, STEPS + 1):
                engine.step()
                rho_trace.append(engine.physics.nodes[engine.physics.node_index_by_id[sid]]["rho"])

            # Calculate half-life (step where rho < 50% of peak)
            peak_rho = max(rho_trace)
            half_life = None
            for i, rho in enumerate(rho_trace):
                if rho < peak_rho * 0.5:
                    half_life = i + 1
                    break

            # Where does the energy go? Check basin
            m = engine.compute_metrics()
            basin = m["rhoMaxId"]

            # How much rho does the injected node retain at end?
            final_rho = rho_trace[-1]
            is_self_attractor = (basin == sid)

            spirit_data.append({
                "id": sid,
                "label": LABELS[sid],
                "peak_rho": round(peak_rho, 6),
                "half_life": half_life,
                "final_rho": round(final_rho, 8),
                "basin": basin,
                "basin_label": LABELS.get(basin, "?"),
                "self_attractor": is_self_attractor,
            })

            marker = "SELF" if is_self_attractor else f"→{fmt(basin, LABELS)}"
            print(f"    [{sid:3d}] {LABELS[sid]:25s} half_life={str(half_life):>4s} "
                  f"final={final_rho:.2e} {marker}")

        results[str(d)] = spirit_data

    # Now compare: at d=20, does christic have special retention properties?
    print(f"\n  COMPARISON at d=20 (sorted by half-life):")
    d20_data = sorted(results["20.0"], key=lambda x: x["half_life"] or 999)
    for item in d20_data:
        hl = item["half_life"]
        arrow = " ◄◄" if item["id"] == CHRISTIC_ID else ""
        print(f"    [{item['id']:3d}] {item['label']:25s} hl={str(hl):>4s} "
              f"basin={item['basin_label']}{arrow}")

    # Standard injection retention race
    print(f"\n  STANDARD INJECTION retention race at d=20:")
    engine = make_engine(20.0)
    apply_standard(engine)

    # Track ALL nodes
    rho_traces_all = {nid: [] for nid in ALL_IDS}
    for s in range(1, STEPS + 1):
        engine.step()
        if s % SAMPLE_INTERVAL == 0:
            for n in engine.physics.nodes:
                rho_traces_all[n["id"]].append(n["rho"])

    # Top 10 at step 50 (index 9)
    for check_step in [10, 50, 100]:
        idx = check_step // SAMPLE_INTERVAL - 1
        first_id = ALL_IDS[0]
        if idx >= 0 and idx < len(rho_traces_all[first_id]):
            print(f"\n    Top 10 at step {check_step}:")
            rho_at = [(nid, rho_traces_all[nid][idx]) for nid in ALL_IDS]
            rho_at.sort(key=lambda x: -x[1])
            for nid, rho in rho_at[:10]:
                grp = GROUPS[nid]
                arrow = " ◄◄ CHRISTIC" if nid == CHRISTIC_ID else ""
                print(f"      [{nid:3d}] {LABELS[nid]:25s} grp={grp:8s} rho={rho:.4e}{arrow}")

    return results


# ══════════════════════════════════════════════════════════════════════
# PROBE F: Phase Gating Knockout
# ══════════════════════════════════════════════════════════════════════
def probe_f_phase_gating_knockout():
    """Run simulations with modified phase gating to test
    whether the heartbeat mechanism is essential to christic dominance.

    Test 1: All nodes always active (no phase gating)
    Test 2: Invert phase gating (spirit active when surface active, vice versa)
    Test 3: Increase deepViscosity (spirit edges carry MORE flux)
    Test 4: Set deepViscosity = surfaceTension (remove spirit/tech asymmetry)
    """
    print("\n" + "=" * 70)
    print("  PROBE F: PHASE GATING KNOCKOUT")
    print("  4 variants × 6 damping = 24 trials + 6 baseline")
    print("=" * 70)

    damping_values = [5.0, 10.0, 12.0, 15.0, 20.0, 40.0]

    # Baseline
    print("\n  Baseline (normal phase gating):")
    baselines = {}
    for d in damping_values:
        engine = make_engine(d)
        apply_standard(engine)
        engine.run(STEPS)
        baselines[d] = get_basin(engine)
        print(f"    d={d:5.1f}: basin={fmt(baselines[d], LABELS)}")

    results = {"baselines": {str(d): v for d, v in baselines.items()}}

    # Test 1: All nodes always active — set all groups to "bridge"
    print("\n  Test 1: ALL NODES = BRIDGE (no phase gating):")
    test1 = {}
    for d in damping_values:
        mod_nodes = [dict(n) for n in RAW_NODES]
        for n in mod_nodes:
            n["group"] = "bridge"  # Bridge is always active
        engine = make_engine(d, mod_nodes, RAW_EDGES)
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        changed = "CHANGED!" if basin != baselines.get(d) else "same"
        print(f"    d={d:5.1f}: basin={fmt(basin, LABELS):40s} {changed}")
        test1[d] = basin
    results["always_active"] = {str(d): v for d, v in test1.items()}

    # Test 2: Swap spirit↔tech
    print("\n  Test 2: SWAP spirit↔tech:")
    test2 = {}
    for d in damping_values:
        mod_nodes = [dict(n) for n in RAW_NODES]
        for n in mod_nodes:
            if n.get("group") == "spirit":
                n["group"] = "tech"
            elif n.get("group") == "tech":
                n["group"] = "spirit"
        engine = make_engine(d, mod_nodes, RAW_EDGES)
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        changed = "CHANGED!" if basin != baselines.get(d) else "same"
        print(f"    d={d:5.1f}: basin={fmt(basin, LABELS):40s} {changed}")
        test2[d] = basin
    results["swapped_groups"] = {str(d): v for d, v in test2.items()}

    # Test 3: deepViscosity = 1.5 (spirit edges carry MORE flux)
    print("\n  Test 3: deepViscosity = 1.5 (amplified spirit flux):")
    test3 = {}
    for d in damping_values:
        engine = make_engine(d)
        engine.physics.phase_cfg["deepViscosity"] = 1.5
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        changed = "CHANGED!" if basin != baselines.get(d) else "same"
        print(f"    d={d:5.1f}: basin={fmt(basin, LABELS):40s} {changed}")
        test3[d] = basin
    results["deep_viscosity_15"] = {str(d): v for d, v in test3.items()}

    # Test 4: deepViscosity = surfaceTension = 1.0 (no asymmetry)
    print("\n  Test 4: deepViscosity = surfaceTension = 1.0 (no asymmetry):")
    test4 = {}
    for d in damping_values:
        engine = make_engine(d)
        engine.physics.phase_cfg["deepViscosity"] = 1.0
        engine.physics.phase_cfg["surfaceTension"] = 1.0
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        changed = "CHANGED!" if basin != baselines.get(d) else "same"
        print(f"    d={d:5.1f}: basin={fmt(basin, LABELS):40s} {changed}")
        test4[d] = basin
    results["no_asymmetry"] = {str(d): v for d, v in test4.items()}

    # Test 5: omega = 0 (no heartbeat oscillation — all always in phase)
    print("\n  Test 5: omega = 0 (no heartbeat — constant phase):")
    test5 = {}
    for d in damping_values:
        engine = make_engine(d)
        engine.physics.phase_cfg["omega"] = 0.0
        apply_standard(engine)
        engine.run(STEPS)
        basin = get_basin(engine)
        changed = "CHANGED!" if basin != baselines.get(d) else "same"
        print(f"    d={d:5.1f}: basin={fmt(basin, LABELS):40s} {changed}")
        test5[d] = basin
    results["omega_zero"] = {str(d): v for d, v in test5.items()}

    return results


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("═" * 70)
    print("  Q2 DEAD ZONE PHYSICS — DEEP INVESTIGATION")
    print("  Experiment 12: Why christic[22] at d=12-40?")
    print("═" * 70)
    t0 = time.time()

    all_results = {}

    all_results["probe_a"] = probe_a_energy_flow()
    all_results["probe_b"] = probe_b_injection_ablation()
    all_results["probe_c"] = probe_c_gateway_severance()
    all_results["probe_d"] = probe_d_transition_fingerprint()
    all_results["probe_e"] = probe_e_retention_race()
    all_results["probe_f"] = probe_f_phase_gating_knockout()

    elapsed = time.time() - t0
    all_results["elapsed_sec"] = round(elapsed, 1)

    # ── Summary ──
    print("\n" + "═" * 70)
    print("  SUMMARY")
    print("═" * 70)
    print(f"  Total runtime: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Trial count
    trials = (
        1 +          # Probe A: 1 run
        36 + 15 +    # Probe B: 6 baseline + 30 ablation + 15 redistribution
        6 + 48 + 6 + 6 +  # Probe C: 6 baseline + 48 sever + 6 multi + 6 christ
        33 +         # Probe D: 33 sweep (+ ultra-fine)
        54 + 1 +     # Probe E: 54 solo inject + 1 standard retention
        6 + 24       # Probe F: 6 baseline + 24 variants (5 tests × ~6 damping, counted as 24+6)
    )
    print(f"  Trials: ~{trials}")

    # Save
    out_path = Path(__file__).resolve().parent / "data" / "q2_dead_zone_deep.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Results saved: {out_path}")

    # Also save text output
    import io
    txt_path = Path(__file__).resolve().parent / "data" / "q2_dead_zone_output.txt"
    print(f"  (Run with redirect for text output: python script.py > {txt_path})")
