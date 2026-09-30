#!/usr/bin/env python3
"""
Experiment 13 — Half-Adder Generalization (Q5 Investigation)

Q5: "Does the 2-input combinational logic (A+B→grail, A-only→metatron)
     hold across damping regimes, or is it specific to d=0.2?"

Six probes:
  A — Full truth table across 12 damping values (48 trials)
  B — w0 amplification rescue at high dampings (48 trials)
  C — Fine boundary mapping around collapse point (~40 trials)
  D — Alternative B-encodings (cold, rev-seq, hub-wall) (36 trials)
  E — Output channel diversity (entropy, coherence, iton as info carriers)
  F — Full adder attempt (3 inputs: injection + highway + clock) (16 trials)

Target: ~200 trials, ~500s compute
"""

import sys, os, copy, json, time
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools", "sol-core"))
from sol_engine import SOLEngine

# ── Constants ────────────────────────────────────────────────────────────
GRAPH_PATH = os.path.join(os.path.dirname(__file__), "tools", "sol-core", "default_graph.json")
DT = 0.12
C_PRESS = 0.05
STEPS = 500
SAMPLE_EVERY = 10

# Standard injection: grail(40), metatron(35), pyramid(30), christ(25), light_codes(20) = 150
STANDARD_INJECTIONS = [
    ("grail", 40), ("metatron", 35), ("pyramid", 30),
    ("christ", 25), ("light codes", 20),
]

# Node IDs for key nodes
INJ_NAME_TO_ID = {"grail": 1, "metatron": 9, "pyramid": 29, "christ": 2, "light_codes": 23}

# ── Graph loading ────────────────────────────────────────────────────────
def load_graph():
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        g = json.load(f)
    return g["rawNodes"], g["rawEdges"]

def get_labels(nodes):
    return {n["id"]: n["label"] for n in nodes}

def get_groups(nodes):
    return {n["id"]: n.get("group", "bridge") for n in nodes}

# ── Engine helpers ───────────────────────────────────────────────────────
def make_engine(nodes, edges, damping, seed=42):
    return SOLEngine.from_graph(nodes, edges, dt=DT, c_press=C_PRESS,
                                damping=damping, rng_seed=seed)

def apply_standard_injection(engine):
    for label, amount in STANDARD_INJECTIONS:
        engine.inject(label, amount)

def set_edge_weights(edges, nodes, rule_fn):
    groups = get_groups(nodes)
    mod = copy.deepcopy(edges)
    count = 0
    for e in mod:
        new_w0 = rule_fn(e, groups)
        if new_w0 != 1.0:
            count += 1
        e["w0"] = new_w0
    return mod, count

def spirit_rule(w0_val):
    """Returns rule: spirit-adjacent edges get w0_val, all others 1.0."""
    def fn(e, grps):
        if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
            return w0_val
        return 1.0
    return fn

def hub_wall_rule(e, grps):
    """Suppress top-3 hubs (par[79], johannine grove[82], mystery school[89])."""
    hubs = {79, 82, 89}
    if e["from"] in hubs or e["to"] in hubs:
        return 0.1
    return 1.0

def run_and_measure(engine, steps=STEPS):
    """Run engine and collect comprehensive metrics."""
    basin_visits = defaultdict(int)
    rho_samples = []
    for s in range(1, steps + 1):
        engine.step()
        if s % SAMPLE_EVERY == 0:
            m = engine.compute_metrics()
            bid = m["rhoMaxId"]
            if bid is not None:
                basin_visits[bid] = basin_visits.get(bid, 0) + 1
            rho_samples.append([n["rho"] for n in engine.physics.nodes])

    final = engine.compute_metrics()
    n_nodes = len(engine.physics.nodes)
    rho_arr = np.array(rho_samples) if rho_samples else np.zeros((1, n_nodes))

    # Basin
    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
    basin_frac = (basin_visits.get(dominant, 0) / max(1, sum(basin_visits.values()))
                  if dominant else 0.0)

    # Iton: fraction of nodes that are pass-through relays
    final_rho = rho_arr[-1] if len(rho_arr) > 0 else np.zeros(n_nodes)
    total_mass = np.sum(final_rho)
    sources, sinks, relays = 0, 0, 0
    if total_mass > 1e-9:
        for j in range(n_nodes):
            frac = final_rho[j] / total_mass
            if frac > 1.0 / n_nodes * 1.5:
                sources += 1
            elif frac < 1.0 / n_nodes * 0.5:
                sinks += 1
            else:
                relays += 1
    iton = relays / max(1, n_nodes)

    # Coherence: correlation of oscillation among injection nodes
    inj_ids = list(INJ_NAME_TO_ID.values())
    if len(rho_arr) > 5:
        inj_traces = rho_arr[:, inj_ids]
        corrs = []
        for i in range(len(inj_ids)):
            for j in range(i + 1, len(inj_ids)):
                if np.std(inj_traces[:, i]) > 1e-12 and np.std(inj_traces[:, j]) > 1e-12:
                    c = np.corrcoef(inj_traces[:, i], inj_traces[:, j])[0, 1]
                    corrs.append(abs(c))
        coherence = float(np.mean(corrs)) if corrs else 0.0
    else:
        coherence = 0.0

    # Entropy (normalized Shannon entropy of rho distribution)
    if total_mass > 1e-9:
        p = final_rho / total_mass
        p = p[p > 1e-15]
        entropy = -np.sum(p * np.log2(p)) / np.log2(n_nodes)
    else:
        entropy = 0.0

    # Mode count (nodes with CoV > 0.01)
    mode_count = 0
    if len(rho_arr) > 5:
        for j in range(n_nodes):
            col = rho_arr[:, j]
            if np.mean(col) > 1e-12:
                cov = np.std(col) / np.mean(col)
                if cov > 0.01:
                    mode_count += 1

    return {
        "basin_id": dominant,
        "basin_frac": round(basin_frac, 3),
        "iton": round(iton, 3),
        "mass": round(float(final["mass"]), 4),
        "coherence": round(coherence, 4),
        "entropy": round(entropy, 4),
        "mode_count": mode_count,
        "maxRho": round(float(final["maxRho"]), 6),
    }


def fmt_basin(nid, labels):
    if nid is None:
        return "None"
    return f"{labels.get(nid, '?')}[{nid}]"


# ══════════════════════════════════════════════════════════════════════════
# PROBE A: Full truth table × damping sweep
# ══════════════════════════════════════════════════════════════════════════
def probe_a(raw_nodes, raw_edges, labels):
    """Test all 4 input combos at 12 damping values."""
    print("\n" + "=" * 70)
    print("PROBE A: Full truth table x damping sweep")
    print("=" * 70)

    dampings = [0.2, 1.0, 2.0, 5.0, 7.5, 10.0, 12.0, 15.0, 20.0, 30.0, 40.0, 55.0]
    combos = [(False, False), (True, False), (False, True), (True, True)]
    combo_labels = ["(0,0)", "(1,0)", "(0,1)", "(1,1)"]

    results = []
    trials = 0

    for d in dampings:
        row_data = {"damping": d, "combos": {}}
        for (a_on, b_on), clbl in zip(combos, combo_labels):
            if b_on:
                mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3.0))
            else:
                mod_edges = copy.deepcopy(raw_edges)

            engine = make_engine(raw_nodes, mod_edges, d)

            if a_on:
                apply_standard_injection(engine)

            if not a_on and not b_on:
                # No energy — just run to confirm null
                engine.run(STEPS)
                m = {"basin_id": None, "basin_frac": 0, "iton": 0, "mass": 0,
                     "coherence": 0, "entropy": 0, "mode_count": 0, "maxRho": 0}
            else:
                m = run_and_measure(engine)

            trials += 1
            row_data["combos"][clbl] = {
                "basin": fmt_basin(m["basin_id"], labels),
                "basin_id": m["basin_id"],
                "basin_frac": m["basin_frac"],
                "iton": m["iton"],
                "mass": m["mass"],
                "coherence": m["coherence"],
                "entropy": m["entropy"],
            }

        results.append(row_data)

        # Print truth table row
        c = row_data["combos"]
        print(f"\n  d={d:5.1f}:")
        print(f"    (0,0) = {c['(0,0)']['basin']:30s}  mass={c['(0,0)']['mass']:.4f}")
        print(f"    (1,0) = {c['(1,0)']['basin']:30s}  mass={c['(1,0)']['mass']:.4f}  iton={c['(1,0)']['iton']:.3f}")
        print(f"    (0,1) = {c['(0,1)']['basin']:30s}  mass={c['(0,1)']['mass']:.4f}  iton={c['(0,1)']['iton']:.3f}")
        print(f"    (1,1) = {c['(1,1)']['basin']:30s}  mass={c['(1,1)']['mass']:.4f}  iton={c['(1,1)']['iton']:.3f}")

        # Check distinguishability
        basins_10 = c["(1,0)"]["basin"]
        basins_01 = c["(0,1)"]["basin"]
        basins_11 = c["(1,1)"]["basin"]
        distinct = len({basins_10, basins_01, basins_11})
        xor_like = basins_10 != basins_11 and basins_01 != basins_11
        print(f"    -> {distinct} distinct basins | XOR-like: {xor_like}")

    return results, trials


# ══════════════════════════════════════════════════════════════════════════
# PROBE B: w0 amplification rescue
# ══════════════════════════════════════════════════════════════════════════
def probe_b(raw_nodes, raw_edges, labels):
    """Test if amplifying spirit highway w0 rescues half-adder at high dampings."""
    print("\n" + "=" * 70)
    print("PROBE B: w0 amplification rescue")
    print("=" * 70)

    w0_values = [2.0, 3.0, 5.0, 10.0, 20.0, 50.0]
    # Test at dampings where we expect challenges
    dampings = [0.2, 5.0, 10.0, 15.0, 20.0, 40.0]
    trials = 0
    results = []

    for d in dampings:
        row = {"damping": d, "w0_tests": {}}
        for w0 in w0_values:
            # Only need A-only and A+B to check if they differ
            # A-only (injection, no highway)
            engine_a = make_engine(raw_nodes, copy.deepcopy(raw_edges), d)
            apply_standard_injection(engine_a)
            m_a = run_and_measure(engine_a)
            trials += 1

            # A+B (injection + spirit highway at w0)
            mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(w0))
            engine_ab = make_engine(raw_nodes, mod_edges, d)
            apply_standard_injection(engine_ab)
            m_ab = run_and_measure(engine_ab)
            trials += 1

            basin_a = fmt_basin(m_a["basin_id"], labels)
            basin_ab = fmt_basin(m_ab["basin_id"], labels)
            differs = basin_a != basin_ab

            row["w0_tests"][w0] = {
                "basin_a_only": basin_a,
                "basin_a_plus_b": basin_ab,
                "differs": differs,
                "iton_a": m_a["iton"],
                "iton_ab": m_ab["iton"],
            }

        results.append(row)

        # Print summary
        print(f"\n  d={d:5.1f}:")
        for w0 in w0_values:
            t = row["w0_tests"][w0]
            mark = "DIFF" if t["differs"] else "SAME"
            print(f"    w0={w0:5.1f}: A-only={t['basin_a_only']:25s}  "
                  f"A+B={t['basin_a_plus_b']:25s}  [{mark}]")

    return results, trials


# ══════════════════════════════════════════════════════════════════════════
# PROBE C: Fine boundary mapping
# ══════════════════════════════════════════════════════════════════════════
def probe_c(raw_nodes, raw_edges, labels, collapse_d):
    """Fine sweep around the collapse point with 0.5 step resolution."""
    print("\n" + "=" * 70)
    print(f"PROBE C: Fine boundary around collapse (centered on d={collapse_d})")
    print("=" * 70)

    # Sweep ±3 around the collapse point
    d_start = max(0.2, collapse_d - 3.0)
    d_end = collapse_d + 3.0
    dampings = np.arange(d_start, d_end + 0.25, 0.5)

    trials = 0
    results = []

    for d in dampings:
        d = round(float(d), 1)
        row = {"damping": d}

        # A-only
        engine_a = make_engine(raw_nodes, copy.deepcopy(raw_edges), d)
        apply_standard_injection(engine_a)
        m_a = run_and_measure(engine_a)
        trials += 1

        # A+B (w0=3.0)
        mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3.0))
        engine_ab = make_engine(raw_nodes, mod_edges, d)
        apply_standard_injection(engine_ab)
        m_ab = run_and_measure(engine_ab)
        trials += 1

        # B-only (highway, no injection)
        engine_b = make_engine(raw_nodes, mod_edges, d)
        engine_b.run(STEPS)
        m_b = {"basin_id": None, "mass": 0.0}
        trials += 1

        # Record: does (0,1) have any energy without injection?
        # Actually B-only with no injection = no energy. But check:
        engine_b2 = make_engine(raw_nodes, mod_edges, d)
        # No injection at all — highway alone doesn't add energy
        engine_b2.run(STEPS)
        fm_b2 = engine_b2.compute_metrics()

        basin_a = fmt_basin(m_a["basin_id"], labels)
        basin_ab = fmt_basin(m_ab["basin_id"], labels)
        differs = m_a["basin_id"] != m_ab["basin_id"]

        row["basin_a_only"] = basin_a
        row["basin_a_plus_b"] = basin_ab
        row["differs"] = differs
        row["iton_a"] = m_a["iton"]
        row["iton_ab"] = m_ab["iton"]
        row["coherence_a"] = m_a["coherence"]
        row["coherence_ab"] = m_ab["coherence"]
        row["entropy_a"] = m_a["entropy"]
        row["entropy_ab"] = m_ab["entropy"]

        results.append(row)
        mark = "DIFF" if differs else "SAME"
        print(f"  d={d:5.1f}: A-only={basin_a:25s}  A+B={basin_ab:25s}  [{mark}]"
              f"  iton_diff={m_ab['iton'] - m_a['iton']:+.3f}")

    return results, trials


# ══════════════════════════════════════════════════════════════════════════
# PROBE D: Alternative B-encodings
# ══════════════════════════════════════════════════════════════════════════
def probe_d(raw_nodes, raw_edges, labels):
    """Test different B-signal encodings: cold injection, rev-seq, hub-wall."""
    print("\n" + "=" * 70)
    print("PROBE D: Alternative B-encodings")
    print("=" * 70)

    dampings = [0.2, 5.0, 10.0]
    trials = 0
    results = []

    # Define B-encodings
    b_encodings = {
        "spirit_3x": ("weight", spirit_rule(3.0)),
        "hub_wall": ("weight", hub_wall_rule),
        "cold_inject": ("inject", [("orion", 40), ("numis'om", 35), ("christos", 30)]),
        "rev_seq": ("seq", None),  # Reverse-sequential injection
    }

    for d in dampings:
        row = {"damping": d, "encodings": {}}

        # Baseline: A-only
        engine_a = make_engine(raw_nodes, copy.deepcopy(raw_edges), d)
        apply_standard_injection(engine_a)
        m_a = run_and_measure(engine_a)
        trials += 1
        basin_a = fmt_basin(m_a["basin_id"], labels)

        for enc_name, (enc_type, enc_data) in b_encodings.items():
            if enc_type == "weight":
                mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, enc_data)
                engine_ab = make_engine(raw_nodes, mod_edges, d)
                apply_standard_injection(engine_ab)
            elif enc_type == "inject":
                engine_ab = make_engine(raw_nodes, copy.deepcopy(raw_edges), d)
                apply_standard_injection(engine_ab)
                for lbl, amt in enc_data:
                    engine_ab.inject(lbl, amt)
            elif enc_type == "seq":
                # Reverse sequential: inject in reverse order with gaps
                engine_ab = make_engine(raw_nodes, copy.deepcopy(raw_edges), d)
                for lbl, amt in reversed(STANDARD_INJECTIONS):
                    engine_ab.inject(lbl, amt)
                    engine_ab.run(50)
                # Will run remaining steps in run_and_measure

            m_ab = run_and_measure(engine_ab)
            trials += 1
            basin_ab = fmt_basin(m_ab["basin_id"], labels)
            differs = m_a["basin_id"] != m_ab["basin_id"]

            row["encodings"][enc_name] = {
                "basin_a_only": basin_a,
                "basin_a_plus_b": basin_ab,
                "differs": differs,
                "iton_a": m_a["iton"],
                "iton_ab": m_ab["iton"],
            }

        results.append(row)

        # Print
        print(f"\n  d={d:5.1f}: A-only = {basin_a}")
        for enc_name in b_encodings:
            t = row["encodings"][enc_name]
            mark = "DIFF" if t["differs"] else "SAME"
            print(f"    B={enc_name:15s}: A+B={t['basin_a_plus_b']:25s}  [{mark}]"
                  f"  iton_diff={t['iton_ab'] - t['iton_a']:+.3f}")

    return results, trials


# ══════════════════════════════════════════════════════════════════════════
# PROBE E: Output channel diversity
# ══════════════════════════════════════════════════════════════════════════
def probe_e(probe_a_results, labels):
    """Analyze which output channels carry information across damping.
    Uses data already collected in Probe A — no new trials needed."""
    print("\n" + "=" * 70)
    print("PROBE E: Output channel diversity (from Probe A data)")
    print("=" * 70)

    print(f"\n  {'d':>5s} | {'Basin distinct':>14s} | {'Iton range':>12s} | "
          f"{'Coh range':>12s} | {'Ent range':>12s} | {'Info channels':>13s}")
    print("  " + "-" * 80)

    channel_summary = []

    for row in probe_a_results:
        d = row["damping"]
        combos = row["combos"]
        active_keys = ["(1,0)", "(0,1)", "(1,1)"]
        active = {k: combos[k] for k in active_keys if k in combos}

        basins = [v["basin"] for v in active.values()]
        itons = [v["iton"] for v in active.values()]
        cohs = [v["coherence"] for v in active.values()]
        ents = [v["entropy"] for v in active.values()]

        basin_distinct = len(set(basins))
        iton_range = max(itons) - min(itons) if itons else 0
        coh_range = max(cohs) - min(cohs) if cohs else 0
        ent_range = max(ents) - min(ents) if ents else 0

        # Count information-carrying channels (threshold: range > 0.01)
        channels = 0
        chan_names = []
        if basin_distinct >= 2:
            channels += 1
            chan_names.append("basin")
        if iton_range > 0.01:
            channels += 1
            chan_names.append("iton")
        if coh_range > 0.01:
            channels += 1
            chan_names.append("coh")
        if ent_range > 0.01:
            channels += 1
            chan_names.append("ent")

        channel_summary.append({
            "damping": d,
            "basin_distinct": basin_distinct,
            "iton_range": round(iton_range, 3),
            "coh_range": round(coh_range, 4),
            "ent_range": round(ent_range, 4),
            "channels": channels,
            "channel_names": chan_names,
        })

        print(f"  {d:5.1f} | {basin_distinct:14d} | {iton_range:12.3f} | "
              f"{coh_range:12.4f} | {ent_range:12.4f} | {channels:2d} ({','.join(chan_names)})")

    return channel_summary


# ══════════════════════════════════════════════════════════════════════════
# PROBE F: Full adder attempt (3 inputs)
# ══════════════════════════════════════════════════════════════════════════
def probe_f(raw_nodes, raw_edges, labels):
    """Test 3-input combinations: A=injection, B=highway, C=clock.
    8 input combos at d=0.2 and d=5.0."""
    print("\n" + "=" * 70)
    print("PROBE F: Full adder attempt (3 inputs: injection, highway, clock)")
    print("=" * 70)

    dampings = [0.2, 5.0]
    trials = 0
    results = []

    for d in dampings:
        row = {"damping": d, "combos": {}}
        for a_on in [False, True]:
            for b_on in [False, True]:
                for c_on in [False, True]:
                    lbl = f"({int(a_on)},{int(b_on)},{int(c_on)})"

                    if b_on:
                        mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3.0))
                    else:
                        mod_edges = copy.deepcopy(raw_edges)

                    engine = make_engine(raw_nodes, mod_edges, d)

                    if a_on:
                        apply_standard_injection(engine)

                    if c_on:
                        # Clock: periodic re-injection of 10% every 100 steps
                        for step_block in range(5):  # 5 blocks × 100 steps = 500
                            engine.inject("grail", 4.0)  # 10% of grail's 40
                            engine.run(100)
                        m = run_and_measure(engine, steps=0)  # already ran 500
                        # Actually let's measure properly:
                        # Re-do: just inject clock alongside normal steps
                    else:
                        pass

                    # Simpler approach: build engine, inject, run with optional clock
                    engine2 = make_engine(raw_nodes, mod_edges, d)
                    if a_on:
                        apply_standard_injection(engine2)

                    if c_on and (a_on or b_on):
                        # Clock: inject small pulses periodically during run
                        basin_visits = defaultdict(int)
                        rho_samples = []
                        for s in range(1, STEPS + 1):
                            if s % 100 == 0:
                                engine2.inject("grail", 4.0)
                            engine2.step()
                            if s % SAMPLE_EVERY == 0:
                                met = engine2.compute_metrics()
                                bid = met["rhoMaxId"]
                                if bid is not None:
                                    basin_visits[bid] = basin_visits.get(bid, 0) + 1
                                rho_samples.append([n["rho"] for n in engine2.physics.nodes])

                        dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
                        basin_frac = (basin_visits.get(dominant, 0) / max(1, sum(basin_visits.values()))
                                      if dominant else 0.0)
                        m = {
                            "basin_id": dominant,
                            "basin_frac": round(basin_frac, 3),
                            "iton": 0.0,
                            "mass": round(float(engine2.compute_metrics()["mass"]), 4),
                        }
                    elif not a_on and not b_on and not c_on:
                        engine2.run(STEPS)
                        m = {"basin_id": None, "basin_frac": 0, "iton": 0, "mass": 0}
                    elif not a_on and not c_on:
                        # B-only (highway no injection) = no energy
                        engine2.run(STEPS)
                        fm = engine2.compute_metrics()
                        m = {"basin_id": None, "basin_frac": 0, "iton": 0,
                             "mass": round(float(fm["mass"]), 4)}
                    else:
                        m = run_and_measure(engine2)

                    trials += 1
                    row["combos"][lbl] = {
                        "basin": fmt_basin(m["basin_id"], labels),
                        "basin_id": m.get("basin_id"),
                        "mass": m.get("mass", 0),
                    }

        results.append(row)

        # Print truth table
        print(f"\n  d={d}: (A=injection, B=highway, C=clock)")
        unique_basins = set()
        for lbl in sorted(row["combos"].keys()):
            c = row["combos"][lbl]
            print(f"    {lbl} -> {c['basin']:30s}  mass={c['mass']:.4f}")
            if c["basin"] != "None":
                unique_basins.add(c["basin"])
        print(f"    -> {len(unique_basins)} distinct non-null basins")

    return results, trials


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    raw_nodes, raw_edges = load_graph()
    labels = get_labels(raw_nodes)
    total_trials = 0

    print("=" * 70)
    print("EXPERIMENT 13: Half-Adder Generalization (Q5 Investigation)")
    print(f"Graph: {len(raw_nodes)} nodes, {len(raw_edges)} edges")
    print("=" * 70)

    # ── Probe A ──
    pa_results, pa_trials = probe_a(raw_nodes, raw_edges, labels)
    total_trials += pa_trials

    # Determine collapse point from Probe A
    collapse_d = None
    for row in pa_results:
        c = row["combos"]
        if c["(1,0)"]["basin_id"] == c["(1,1)"]["basin_id"]:
            collapse_d = row["damping"]
            break
    if collapse_d is None:
        collapse_d = 15.0  # Default if no collapse found in sweep

    print(f"\n  >> Half-adder collapse detected at d={collapse_d}")

    # ── Probe B ──
    pb_results, pb_trials = probe_b(raw_nodes, raw_edges, labels)
    total_trials += pb_trials

    # ── Probe C ──
    pc_results, pc_trials = probe_c(raw_nodes, raw_edges, labels, collapse_d)
    total_trials += pc_trials

    # ── Probe D ──
    pd_results, pd_trials = probe_d(raw_nodes, raw_edges, labels)
    total_trials += pd_trials

    # ── Probe E (analytic, uses Probe A data) ──
    pe_results = probe_e(pa_results, labels)

    # ── Probe F ──
    pf_results, pf_trials = probe_f(raw_nodes, raw_edges, labels)
    total_trials += pf_trials

    elapsed = time.time() - t0

    # ── Summary ──
    print("\n" + "=" * 70)
    print("EXPERIMENT 13 SUMMARY")
    print("=" * 70)

    # Determine at which dampings the half-adder works
    working = []
    broken = []
    for row in pa_results:
        d = row["damping"]
        c = row["combos"]
        basin_10 = c["(1,0)"]["basin"]
        basin_11 = c["(1,1)"]["basin"]
        if basin_10 != basin_11:
            working.append(d)
        else:
            broken.append(d)

    print(f"\n  Half-adder WORKS at: {working}")
    print(f"  Half-adder BROKEN at: {broken}")

    if working:
        print(f"\n  Operating regime: d <= {max(working)}")

    # XOR-like (all 3 active combos produce distinct basins)
    xor_dampings = []
    for row in pa_results:
        d = row["damping"]
        c = row["combos"]
        active_basins = {c["(1,0)"]["basin"], c["(0,1)"]["basin"], c["(1,1)"]["basin"]}
        # Remove None basins
        active_basins.discard("None")
        if len(active_basins) >= 2:  # At least 2 distinct non-null
            basins_10 = c["(1,0)"]["basin"]
            basins_01 = c["(0,1)"]["basin"]
            basins_11 = c["(1,1)"]["basin"]
            if basins_10 != basins_11:
                xor_dampings.append(d)

    print(f"  XOR-like behavior at: {xor_dampings}")

    # w0 rescue summary
    print("\n  w0 rescue results:")
    for row in pb_results:
        d = row["damping"]
        rescued = [w0 for w0, t in row["w0_tests"].items() if t["differs"]]
        if rescued:
            print(f"    d={d}: rescued at w0={rescued}")
        else:
            print(f"    d={d}: NO rescue at any w0")

    # Channel diversity
    print("\n  Output channels carrying information:")
    for cs in pe_results:
        print(f"    d={cs['damping']}: {cs['channels']} channels ({', '.join(cs['channel_names'])})")

    # Full adder
    print("\n  Full adder (3-input) distinct basins:")
    for row in pf_results:
        basins = set()
        for combo in row["combos"].values():
            if combo["basin"] != "None":
                basins.add(combo["basin"])
        print(f"    d={row['damping']}: {len(basins)} distinct basins")

    print(f"\n  Total trials: {total_trials}")
    print(f"  Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Save raw data
    out_path = os.path.join(os.path.dirname(__file__), "data", "q5_half_adder.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "probe_a": pa_results,
            "probe_b": pb_results,
            "probe_c": pc_results,
            "probe_d": pd_results,
            "probe_e": pe_results,
            "probe_f": pf_results,
            "collapse_d": collapse_d,
            "working_dampings": working,
            "broken_dampings": broken,
            "total_trials": total_trials,
            "elapsed_s": round(elapsed, 1),
        }, f, indent=2, default=str)
    print(f"\n  Data saved to {out_path}")


if __name__ == "__main__":
    main()
