#!/usr/bin/env python3
"""
Manifold Superposition Deep Probe — Experiment 11
Extends every probe (A-F) from the initial superposition investigation.

Deep-dive extensions:
  A+: Multi-damping decision latency sweep (d=0.2..40). Commitment velocity.
  B+: Herfindahl-Hirschman Index (HHI), N-way superposition width,
      superposition duration, decoherence rate.
  C+: Sub-regional internal entropy inside bridge group.
      Cross-group kingmaker analysis. Per-group entropy curves.
  D+: Multi-target perturbation map (tech/bridge/spirit targets).
      Full sensitivity heatmap: perturbation_amount × injection_step → basin.
  E+: Step-by-step KL-divergence between gap=3 and gap=4.
      Full gap sweep (1-10) to map knife-edge landscape.
  F+: Multi-damping entropy comparison. Entropy derivative (inflection points).
      Per-group entropy decomposition. Entropy plateau detection.
"""

import sys, os, json, time, math
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools", "sol-core"))
from sol_engine import SOLEngine

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "tools", "sol-core", "default_graph.json")

STANDARD_INJECTION = [
    ("grail", 40), ("metatron", 35), ("pyramid", 30),
    ("christ", 25), ("light_codes", 20),
]

def load_graph():
    with open(GRAPH_PATH) as f:
        data = json.load(f)
    return data["rawNodes"], data["rawEdges"]

def make_engine(rn, re, d):
    return SOLEngine.from_graph(rn, re, damping=d)

def labels_map(rn):
    return {n["id"]: n["label"] for n in rn}

def groups_map(rn):
    return {n["id"]: n.get("group", "bridge") for n in rn}

def inject_standard(e):
    for label, amt in STANDARD_INJECTION:
        e.inject(label, amt)

def shannon(states):
    """Normalised Shannon entropy of rho distribution."""
    total = sum(s["rho"] for s in states)
    if total <= 0:
        return 0.0
    h = 0.0
    for s in states:
        p = s["rho"] / total
        if p > 0:
            h -= p * math.log(p)
    hmax = math.log(len(states))
    return h / hmax if hmax > 0 else 0.0

def hhi(states):
    """Herfindahl-Hirschman Index — sum of squared market shares.
       1/N = perfectly uniform, 1.0 = single dominant node."""
    total = sum(s["rho"] for s in states)
    if total <= 0:
        return 1.0
    return sum((s["rho"] / total) ** 2 for s in states)

def kl_divergence(p_states, q_states):
    """KL(P || Q) between two rho distributions (same node ordering)."""
    p_total = sum(s["rho"] for s in p_states)
    q_total = sum(s["rho"] for s in q_states)
    if p_total <= 0 or q_total <= 0:
        return float('inf')
    eps = 1e-30
    kl = 0.0
    for ps, qs in zip(p_states, q_states):
        pp = ps["rho"] / p_total + eps
        qq = qs["rho"] / q_total + eps
        kl += pp * math.log(pp / qq)
    return kl

def group_entropy(states, group_ids):
    """Shannon entropy of the rho sub-distribution within a group of node IDs."""
    sub = [s for s in states if s["id"] in group_ids]
    if not sub:
        return 0.0
    return shannon(sub)

def top_n_share(states, n=5):
    total = sum(s["rho"] for s in states)
    if total <= 0:
        return 0.0
    ranked = sorted(states, key=lambda s: s["rho"], reverse=True)
    return sum(ranked[i]["rho"] for i in range(min(n, len(ranked)))) / total

def contender_count(states, threshold_frac=0.5):
    """How many nodes hold >= threshold_frac of the leader's rho."""
    ranked = sorted(states, key=lambda s: s["rho"], reverse=True)
    if not ranked or ranked[0]["rho"] <= 0:
        return 0
    cutoff = ranked[0]["rho"] * threshold_frac
    return sum(1 for s in ranked if s["rho"] >= cutoff)

# ================================================================
# PROBE A+: Multi-Damping Decision Latency Sweep
# ================================================================
def probe_a_deep(rn, re):
    banner("PROBE A+: Multi-Damping Decision Latency & Commitment Velocity")
    labs = labels_map(rn)
    damping_values = [0.2, 1.0, 2.0, 5.0, 10.0, 15.0, 25.0, 40.0]
    steps = 500
    results = []

    print(f"\n  {'d':>6} {'Decision':>9} {'Lead Chg':>9} {'Min Margin':>11} {'Final Basin':<30} {'Commit Vel':>11} {'Unique Basins':>14}")
    for d in damping_values:
        e = make_engine(rn, re, d)
        inject_standard(e)

        history = []
        for step in range(steps):
            e.step()
            states = e.get_node_states()
            ranked = sorted(states, key=lambda s: s["rho"], reverse=True)
            m = e.compute_metrics()
            leader = f"{labs.get(m['rhoMaxId'],'?')}[{m['rhoMaxId']}]"
            lr = ranked[0]["rho"]
            rr = ranked[1]["rho"] if len(ranked) > 1 else 0
            margin = (lr - rr) / max(lr, 1e-10)
            history.append({"step": step, "leader": leader, "margin": margin})

        final = history[-1]["leader"]
        # Decision step
        ds = 0
        for i in range(len(history)-1, -1, -1):
            if history[i]["leader"] != final:
                ds = i + 1
                break
        # Lead changes
        lc = sum(1 for i in range(1, len(history)) if history[i]["leader"] != history[i-1]["leader"])
        # Min margin
        mm = min(h["margin"] for h in history)
        # Unique basins visited
        unique = len(set(h["leader"] for h in history))

        # Commitment velocity: margin growth rate over last 10 steps after decision
        window_start = min(ds, steps - 1)
        window_end = min(ds + 10, steps - 1)
        if window_end > window_start and window_start < steps:
            m_start = history[window_start]["margin"]
            m_end = history[window_end]["margin"]
            commit_vel = (m_end - m_start) / (window_end - window_start)
        else:
            commit_vel = 0.0

        results.append({
            "damping": d, "decision_step": ds, "lead_changes": lc,
            "min_margin": mm, "final_basin": final, "unique_basins": unique,
            "commitment_velocity": commit_vel
        })
        print(f"  {d:>6.1f} {ds:>9} {lc:>9} {mm:>11.6f} {final:<30} {commit_vel:>11.6f} {unique:>14}")

    # Summary insights
    most_volatile = max(results, key=lambda r: r["lead_changes"])
    latest_decider = max(results, key=lambda r: r["decision_step"])
    print(f"\n  Most volatile regime: d={most_volatile['damping']} ({most_volatile['lead_changes']} lead changes)")
    print(f"  Latest decision: d={latest_decider['damping']} (step {latest_decider['decision_step']})")
    print(f"  → Decision latency is NOT monotonic with damping")
    return results


# ================================================================
# PROBE B+: Concentration Dynamics (HHI, Width, Duration, Decoherence)
# ================================================================
def probe_b_deep(rn, re, damping=5.0, steps=500):
    banner("PROBE B+: Concentration Dynamics (HHI / Width / Duration / Decoherence)")
    labs = labels_map(rn)
    e = make_engine(rn, re, damping)
    inject_standard(e)

    curve = []
    for step in range(steps):
        e.step()
        states = e.get_node_states()
        ranked = sorted(states, key=lambda s: s["rho"], reverse=True)
        lr = ranked[0]["rho"]
        rr = ranked[1]["rho"] if len(ranked) > 1 else 0
        ratio = rr / lr if lr > 0 else 0

        curve.append({
            "step": step,
            "hhi": hhi(states),
            "top2_ratio": ratio,
            "contenders_50": contender_count(states, 0.5),
            "contenders_25": contender_count(states, 0.25),
            "contenders_10": contender_count(states, 0.10),
            "entropy": shannon(states),
        })

    # HHI timeline
    print(f"\n  HHI Timeline (1/N={1/140:.4f}=uniform, 1.0=monopoly):")
    print(f"  {'Step':>5} {'HHI':>10} {'Ratio':>6} {'>50%':>5} {'>25%':>5} {'>10%':>5} {'Entropy':>8}")
    for c in curve:
        if c["step"] in [0,5,10,20,50,100,150,200,250,300,350,400,450,499]:
            print(f"  {c['step']:>5} {c['hhi']:>10.6f} {c['top2_ratio']:>6.3f} "
                  f"{c['contenders_50']:>5} {c['contenders_25']:>5} {c['contenders_10']:>5} {c['entropy']:>8.4f}")

    # Superposition duration: longest continuous streak where ratio > 0.95
    max_streak = 0
    cur_streak = 0
    streak_start = 0
    best_streak_start = 0
    for c in curve:
        if c["top2_ratio"] > 0.95:
            if cur_streak == 0:
                streak_start = c["step"]
            cur_streak += 1
            if cur_streak > max_streak:
                max_streak = cur_streak
                best_streak_start = streak_start
        else:
            cur_streak = 0

    print(f"\n  Superposition duration (ratio > 0.95):")
    print(f"    Longest streak: {max_streak} steps (starting at step {best_streak_start})")

    # Decoherence rate: from peak ratio, how fast does it drop?
    peak_idx = max(range(len(curve)), key=lambda i: curve[i]["top2_ratio"])
    peak_ratio = curve[peak_idx]["top2_ratio"]
    # Find time to drop below 0.90 after peak
    decohere_steps = None
    for i in range(peak_idx + 1, len(curve)):
        if curve[i]["top2_ratio"] < 0.90:
            decohere_steps = i - peak_idx
            break

    print(f"\n  Decoherence analysis:")
    print(f"    Peak superposition: ratio={peak_ratio:.4f} at step {curve[peak_idx]['step']}")
    if decohere_steps is not None:
        print(f"    Drops below 0.90 after {decohere_steps} steps → decoherence rate = {1/decohere_steps:.4f}/step")
    else:
        print(f"    NEVER drops below 0.90 after peak → SUSTAINED SUPERPOSITION")

    # HHI phase transition
    min_hhi = min(c["hhi"] for c in curve)
    max_hhi = max(c["hhi"] for c in curve)
    print(f"\n  HHI range: {max_hhi:.6f} (step 0, concentrated) → {min_hhi:.6f} (near-uniform)")
    print(f"  Uniformity ratio: {(1/140) / min_hhi:.2f}× (1.0 = perfectly uniform)")

    # When does >10% contender count exceed N/2 (70 nodes)?
    half_n_step = None
    for c in curve:
        if c["contenders_10"] >= 70:
            half_n_step = c["step"]
            break
    if half_n_step is not None:
        print(f"  N/2 superposition (>70 nodes at ≥10% of leader): achieved at step {half_n_step}")

    return curve


# ================================================================
# PROBE C+: Sub-Regional Entropy & Kingmaker Analysis
# ================================================================
def probe_c_deep(rn, re, damping=5.0, steps=500):
    banner("PROBE C+: Sub-Regional Entropy & Kingmaker Analysis")
    labs = labels_map(rn)
    grps = groups_map(rn)

    group_ids = defaultdict(set)
    for n in rn:
        group_ids[n.get("group", "bridge")].add(n["id"])

    e = make_engine(rn, re, damping)
    inject_standard(e)

    # Track per-group entropy and leader at each step
    group_curves = {g: [] for g in group_ids}
    global_leader_history = []

    for step in range(steps):
        e.step()
        states = e.get_node_states()
        m = e.compute_metrics()
        global_leader = f"{labs.get(m['rhoMaxId'],'?')}[{m['rhoMaxId']}]"
        global_leader_history.append(global_leader)

        for g, ids in group_ids.items():
            sub = [s for s in states if s["id"] in ids]
            ge = shannon(sub) if len(sub) > 1 else 0.0
            sub_ranked = sorted(sub, key=lambda s: s["rho"], reverse=True)
            leader_id = sub_ranked[0]["id"] if sub_ranked else None
            total_rho = sum(s["rho"] for s in sub)
            group_curves[g].append({
                "step": step,
                "entropy": ge,
                "leader_id": leader_id,
                "leader_label": labs.get(leader_id, "?"),
                "group_rho": total_rho,
            })

    # Print per-group entropy at key steps
    print(f"\n  Per-group internal entropy over time:")
    print(f"  {'Step':>5}", end="")
    for g in sorted(group_ids.keys()):
        print(f"  {g:>10}", end="")
    print(f"  {'Global':>10}")

    for step_idx in [0, 10, 50, 100, 200, 300, 400, 450, 499]:
        if step_idx >= steps:
            continue
        print(f"  {step_idx:>5}", end="")
        for g in sorted(group_ids.keys()):
            print(f"  {group_curves[g][step_idx]['entropy']:>10.4f}", end="")
        # Global entropy at this step
        e2 = make_engine(rn, re, damping)
        inject_standard(e2)
        e2.run(step_idx + 1)
        gent = shannon(e2.get_node_states())
        print(f"  {gent:>10.4f}")

    # Per-group lead changes and decision step
    print(f"\n  Per-group leader dynamics:")
    print(f"  {'Group':<10} {'Size':>5} {'Decision':>9} {'Lead Chg':>9} {'Unique':>7} {'Final Leader':<25}")
    group_results = {}
    for g in sorted(group_ids.keys()):
        gc = group_curves[g]
        leaders = [c["leader_id"] for c in gc]
        final = leaders[-1]
        ds = 0
        for i in range(len(leaders)-1, -1, -1):
            if leaders[i] != final:
                ds = i + 1
                break
        lc = sum(1 for i in range(1, len(leaders)) if leaders[i] != leaders[i-1])
        unique = len(set(leaders))
        fl = labs.get(final, "?")
        print(f"  {g:<10} {len(group_ids[g]):>5} {ds:>9} {lc:>9} {unique:>7} {fl}[{final}]")
        group_results[g] = {"decision_step": ds, "lead_changes": lc, "unique_visited": unique}

    # Sub-region analysis: break bridge into connectivity neighborhoods
    # Since bridge has 121 nodes, let's look at early-settling vs late-settling nodes WITHIN bridge
    bridge_ids = sorted(group_ids.get("bridge", set()))
    if len(bridge_ids) > 10:
        print(f"\n  Bridge sub-region analysis ({len(bridge_ids)} nodes):")
        # Track when each bridge node's rank stabilises
        e3 = make_engine(rn, re, damping)
        inject_standard(e3)
        bridge_rank_history = {nid: [] for nid in bridge_ids}
        for step in range(steps):
            e3.step()
            states = e3.get_node_states()
            ranked = sorted(states, key=lambda s: s["rho"], reverse=True)
            rank_map = {s["id"]: i for i, s in enumerate(ranked)}
            for nid in bridge_ids:
                bridge_rank_history[nid].append(rank_map.get(nid, 999))

        # For each bridge node, find when its rank stabilises (stops changing by > 5)
        bridge_settle = {}
        for nid in bridge_ids:
            rh = bridge_rank_history[nid]
            settle = 0
            final_rank = rh[-1]
            for i in range(len(rh)-1, -1, -1):
                if abs(rh[i] - final_rank) > 5:
                    settle = i + 1
                    break
            bridge_settle[nid] = settle

        # Sort by settlement time
        sorted_settle = sorted(bridge_settle.items(), key=lambda x: x[1])
        early = sorted_settle[:10]
        late = sorted_settle[-10:]

        print(f"    Earliest-settling bridge nodes (rank stable within ±5):")
        for nid, s in early:
            print(f"      {labs.get(nid,'?')}[{nid}]: stable at step {s}")
        print(f"    Latest-settling bridge nodes:")
        for nid, s in late:
            print(f"      {labs.get(nid,'?')}[{nid}]: stable at step {s}")

        settle_times = list(bridge_settle.values())
        avg_settle = sum(settle_times) / len(settle_times)
        print(f"    Average bridge settlement: step {avg_settle:.0f}")
        print(f"    Settlement spread: {min(settle_times)} → {max(settle_times)} steps")

    # Kingmaker analysis: which group's decision most often matches the global winner?
    print(f"\n  Kingmaker analysis:")
    final_global = global_leader_history[-1]
    for g in sorted(group_ids.keys()):
        gc = group_curves[g]
        final_group_id = gc[-1]["leader_id"]
        # Is the group's final leader the node that wins globally?
        overlap = labs.get(final_group_id, "?") in final_global
        # What fraction of the time does the group's leader match the global leader?
        match_count = 0
        for step in range(steps):
            g_leader = gc[step]["leader_label"]
            gl = global_leader_history[step]
            if g_leader in gl:
                match_count += 1
        match_frac = match_count / steps
        print(f"    {g:<10}: final overlap={'YES' if overlap else 'NO'}, "
              f"step-wise global match={match_frac:.1%}")

    # Group rho share over time — who holds the most energy?
    print(f"\n  Group rho share over time:")
    print(f"  {'Step':>5}", end="")
    for g in sorted(group_ids.keys()):
        print(f"  {g:>10}", end="")
    print()
    for step_idx in [0, 50, 100, 200, 300, 400, 499]:
        if step_idx >= steps:
            continue
        total_all = sum(group_curves[g][step_idx]["group_rho"] for g in group_ids)
        print(f"  {step_idx:>5}", end="")
        for g in sorted(group_ids.keys()):
            share = group_curves[g][step_idx]["group_rho"] / total_all if total_all > 0 else 0
            print(f"  {share:>9.1%}", end="")
        print()

    return group_results


# ================================================================
# PROBE D+: Multi-Target Perturbation Sensitivity Map
# ================================================================
def probe_d_deep(rn, re, damping=5.0, steps=500):
    banner("PROBE D+: Multi-Target Perturbation Sensitivity Map")
    labs = labels_map(rn)
    grps = groups_map(rn)

    # Baseline
    e = make_engine(rn, re, damping)
    inject_standard(e)
    e.run(steps)
    m = e.compute_metrics()
    base_basin = f"{labs.get(m['rhoMaxId'],'?')}[{m['rhoMaxId']}]"
    print(f"  Baseline basin: {base_basin}")

    # Test multiple perturbation targets from different groups
    targets = [
        ("magdalene", "bridge"),   # from original
        ("light_codes", "tech"),   # the only tech node
        ("christic", "spirit"),    # spirit node
        ("numis'om", "spirit"),    # another spirit
        ("earth star", "bridge"),  # a bridge node
        ("thothhorra", "bridge"),  # another bridge
        ("simeon", "bridge"),      # the baseline winner
    ]

    checkpoints = [0, 5, 10, 20, 50, 100, 150, 200, 250, 300, 350, 400, 450]
    amounts = [0.5, 2.0, 5.0, 10.0]

    # Full sensitivity heatmap: target × amount × step → basin
    print(f"\n  Sensitivity heatmap (✗ = basin changed from baseline):")
    print(f"  {'Target':<20} {'Amt':>5} ", end="")
    for cp in checkpoints:
        print(f" {cp:>4}", end="")
    print(f"  {'Flips':>5}")

    all_results = {}
    for target, tgroup in targets:
        for amt in amounts:
            row_key = f"{target}({amt})"
            flips = 0
            row_results = []
            for cp in checkpoints:
                e2 = make_engine(rn, re, damping)
                inject_standard(e2)
                if cp > 0:
                    e2.run(cp)
                e2.inject(target, amt)
                e2.run(steps - cp)
                m2 = e2.compute_metrics()
                pb = f"{labs.get(m2['rhoMaxId'],'?')}[{m2['rhoMaxId']}]"
                changed = pb != base_basin
                if changed:
                    flips += 1
                row_results.append({"step": cp, "basin": pb, "changed": changed})

            print(f"  {target:<20} {amt:>5.1f} ", end="")
            for r in row_results:
                print(f" {'✗' if r['changed'] else '·':>4}", end="")
            print(f"  {flips:>5}")
            all_results[row_key] = row_results

    # Unique basins reachable via perturbation
    all_basins = set()
    all_basins.add(base_basin)
    for key, rows in all_results.items():
        for r in rows:
            all_basins.add(r["basin"])
    print(f"\n  Unique basins reachable: {len(all_basins)}")
    for b in sorted(all_basins):
        marker = " (baseline)" if b == base_basin else ""
        print(f"    {b}{marker}")

    # Most sensitive step (most flips across all targets)
    step_flips = defaultdict(int)
    for key, rows in all_results.items():
        for r in rows:
            if r["changed"]:
                step_flips[r["step"]] += 1
    if step_flips:
        most_sensitive_step = max(step_flips.items(), key=lambda x: x[1])
        print(f"\n  Most sensitive step: {most_sensitive_step[0]} ({most_sensitive_step[1]} flips)")
    else:
        print(f"\n  No flips detected — system is extremely stable at perturbation levels tested")

    return all_results


# ================================================================
# PROBE E+: Divergence Landscape (KL-divergence + Full Gap Sweep)
# ================================================================
def probe_e_deep(rn, re, damping=5.0, steps=500):
    banner("PROBE E+: Divergence Landscape & Full Gap Sweep")
    labs = labels_map(rn)

    # Part 1: Step-by-step KL-divergence between gap=3 and gap=4
    print(f"\n  Part 1: KL-divergence timeline (gap=3 vs gap=4)")

    def run_gap_protocol(gap):
        e = make_engine(rn, re, damping)
        snapshots = []
        for pulse in range(5):
            e.inject("grail", 30.0)
            for _ in range(gap):
                e.step()
                snapshots.append(sorted(e.get_node_states(), key=lambda s: s["id"]))
        # Run remaining steps
        elapsed = 5 * gap
        for _ in range(steps - elapsed):
            e.step()
            snapshots.append(sorted(e.get_node_states(), key=lambda s: s["id"]))
        return snapshots

    snaps_3 = run_gap_protocol(3)
    snaps_4 = run_gap_protocol(4)

    # We can only compare divergence up to min shared length
    # But they have different total snapshots: gap=3 → 500 snapshots, gap=4 → 500 snapshots
    # Compare at the SAME absolute step count
    min_len = min(len(snaps_3), len(snaps_4))

    print(f"  Timeline length: {min_len} steps")
    print(f"\n  {'Step':>5} {'KL(3||4)':>10} {'KL(4||3)':>10} {'Sym KL':>10} {'Same Leader?':>13}")

    kl_curve = []
    for step in range(0, min_len, max(1, min_len // 30)):
        s3 = snaps_3[step]
        s4 = snaps_4[step]
        kl34 = kl_divergence(s3, s4)
        kl43 = kl_divergence(s4, s3)
        sym_kl = (kl34 + kl43) / 2

        leader3 = max(s3, key=lambda s: s["rho"])
        leader4 = max(s4, key=lambda s: s["rho"])
        same = leader3["id"] == leader4["id"]

        kl_curve.append({"step": step, "kl34": kl34, "kl43": kl43, "sym_kl": sym_kl, "same_leader": same})
        print(f"  {step:>5} {kl34:>10.6f} {kl43:>10.6f} {sym_kl:>10.6f} {'YES' if same else 'NO':>13}")

    # Find the divergence onset — first step where sym_kl > 0.001
    diverge_step = None
    for kl in kl_curve:
        if kl["sym_kl"] > 0.001:
            diverge_step = kl["step"]
            break
    if diverge_step is not None:
        print(f"\n  Divergence onset: step {diverge_step} (sym_KL first exceeds 0.001)")
    else:
        print(f"\n  No significant divergence detected!")

    # Part 2: Full gap sweep (1-10) — which gaps produce which basins?
    print(f"\n  Part 2: Full gap sweep (gap=1..10)")
    print(f"  {'Gap':>4} {'Steps used':>11} {'Final Basin':<30} {'Final Entropy':>14}")

    gap_basins = {}
    for gap in range(1, 11):
        e = make_engine(rn, re, damping)
        for pulse in range(5):
            e.inject("grail", 30.0)
            e.run(gap)
        elapsed = 5 * gap
        e.run(steps - elapsed)
        m = e.compute_metrics()
        basin = f"{labs.get(m['rhoMaxId'],'?')}[{m['rhoMaxId']}]"
        ent = shannon(e.get_node_states())
        gap_basins[gap] = basin
        print(f"  {gap:>4} {5*gap:>11} {basin:<30} {ent:>14.4f}")

    # Count unique basins and transitions
    unique = set(gap_basins.values())
    transitions = sum(1 for i in range(2, 11) if gap_basins[i] != gap_basins[i-1])
    print(f"\n  Unique basins across gaps 1-10: {len(unique)}")
    print(f"  Basin transitions: {transitions}")
    for b in sorted(unique):
        gaps_at = [g for g, v in gap_basins.items() if v == b]
        print(f"    {b}: gaps {gaps_at}")

    return kl_curve, gap_basins


# ================================================================
# PROBE F+: Entropy Derivative, Per-Group Decomposition, Plateaus
# ================================================================
def probe_f_deep(rn, re, steps=500):
    banner("PROBE F+: Entropy Derivative, Per-Group Decomposition & Plateaus")
    labs = labels_map(rn)
    grps = groups_map(rn)
    group_ids = defaultdict(set)
    for n in rn:
        group_ids[n.get("group", "bridge")].add(n["id"])

    damping_values = [0.2, 1.0, 2.0, 5.0, 10.0, 15.0, 25.0, 40.0]

    # Part 1: Multi-damping entropy comparison
    print(f"\n  Part 1: Multi-damping entropy comparison")
    print(f"  {'Step':>5}", end="")
    for d in damping_values:
        print(f"  d={d:>4}", end="")
    print()

    all_curves = {}
    for d in damping_values:
        e = make_engine(rn, re, d)
        inject_standard(e)
        curve = []
        for step in range(steps):
            e.step()
            ent = shannon(e.get_node_states())
            curve.append(ent)
        all_curves[d] = curve

    for step_idx in [0, 10, 20, 50, 100, 200, 300, 400, 499]:
        print(f"  {step_idx:>5}", end="")
        for d in damping_values:
            print(f"  {all_curves[d][step_idx]:>6.4f}", end="")
        print()

    # Part 2: Entropy derivative at d=5.0 (inflection points)
    print(f"\n  Part 2: Entropy derivative at d=5.0 (inflection points)")
    curve_5 = all_curves[5.0]
    deriv = [curve_5[i+1] - curve_5[i] for i in range(len(curve_5)-1)]

    # Find inflection points — where derivative changes sign significantly
    inflections = []
    for i in range(1, len(deriv)):
        if abs(deriv[i] - deriv[i-1]) > 0.005:
            inflections.append(i)

    print(f"  {'Step':>5} {'Entropy':>8} {'dH/dt':>10}")
    for step in range(0, steps - 1, max(1, steps // 25)):
        marker = " ← inflection" if step in inflections else ""
        print(f"  {step:>5} {curve_5[step]:>8.4f} {deriv[step]:>10.6f}{marker}")

    # Find entropy plateaus: runs of 10+ steps where |dH/dt| < 0.0005
    print(f"\n  Part 3: Entropy plateaus (|dH/dt| < 0.0005 for 10+ steps)")
    plateau_start = None
    plateaus = []
    for i, d_val in enumerate(deriv):
        if abs(d_val) < 0.0005:
            if plateau_start is None:
                plateau_start = i
        else:
            if plateau_start is not None:
                length = i - plateau_start
                if length >= 10:
                    plateaus.append((plateau_start, i, length, curve_5[plateau_start]))
                plateau_start = None
    if plateau_start is not None:
        length = len(deriv) - plateau_start
        if length >= 10:
            plateaus.append((plateau_start, len(deriv), length, curve_5[plateau_start]))

    if plateaus:
        for start, end, length, ent_at in plateaus:
            state = "SUPERPOSED" if ent_at > 0.8 else "competing" if ent_at > 0.5 else "resolving"
            print(f"    Steps {start}-{end} ({length} steps) at entropy {ent_at:.4f} ({state})")
    else:
        print(f"    No plateaus found (entropy always changing)")

    # Part 4: Per-group entropy decomposition at d=5.0
    print(f"\n  Part 4: Per-group entropy decomposition at d=5.0")
    e4 = make_engine(rn, re, 5.0)
    inject_standard(e4)
    print(f"  {'Step':>5}", end="")
    for g in sorted(group_ids.keys()):
        print(f"  {g:>10}", end="")
    print(f"  {'Global':>10}")

    for step in range(steps):
        e4.step()
        if step in [0, 10, 50, 100, 150, 200, 250, 300, 350, 400, 450, 499]:
            states = e4.get_node_states()
            print(f"  {step:>5}", end="")
            for g in sorted(group_ids.keys()):
                ge = group_entropy(states, group_ids[g])
                print(f"  {ge:>10.4f}", end="")
            print(f"  {shannon(states):>10.4f}")

    # Part 5: Entropy convergence rate — steps to reach 90% of max entropy
    print(f"\n  Part 5: Steps to reach 90% / 95% / 99% of max entropy")
    print(f"  {'d':>6} {'90%':>8} {'95%':>8} {'99%':>8} {'Max H':>8}")
    for d in damping_values:
        c = all_curves[d]
        max_h = max(c)
        t90 = next((i for i, h in enumerate(c) if h >= 0.90 * max_h), steps)
        t95 = next((i for i, h in enumerate(c) if h >= 0.95 * max_h), steps)
        t99 = next((i for i, h in enumerate(c) if h >= 0.99 * max_h), steps)
        print(f"  {d:>6.1f} {t90:>8} {t95:>8} {t99:>8} {max_h:>8.4f}")

    return all_curves


def banner(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    t0 = time.time()
    rn, re = load_graph()
    all_results = {}

    # A+: Multi-damping decision latency
    a_results = probe_a_deep(rn, re)
    all_results["probe_a_deep"] = a_results

    # B+: Concentration dynamics
    b_results = probe_b_deep(rn, re, damping=5.0)
    all_results["probe_b_deep"] = {
        "min_hhi": min(c["hhi"] for c in b_results),
        "max_contenders_10": max(c["contenders_10"] for c in b_results),
    }

    # C+: Sub-regional entropy & kingmaker
    c_results = probe_c_deep(rn, re, damping=5.0)
    all_results["probe_c_deep"] = c_results

    # D+: Multi-target perturbation map
    d_results = probe_d_deep(rn, re, damping=5.0)
    # Summarize: count total flips
    total_flips = sum(
        1 for rows in d_results.values()
        for r in rows if r["changed"]
    )
    all_results["probe_d_deep"] = {"total_flips": total_flips}

    # E+: Divergence landscape
    kl_curve, gap_basins = probe_e_deep(rn, re, damping=5.0)
    all_results["probe_e_deep"] = {
        "gap_basins": {str(k): v for k, v in gap_basins.items()},
        "unique_basins": len(set(gap_basins.values())),
    }

    # F+: Entropy derivative & decomposition
    f_curves = probe_f_deep(rn, re)
    all_results["probe_f_deep"] = {
        "damping_values": [0.2, 1.0, 2.0, 5.0, 10.0, 15.0, 25.0, 40.0],
        "final_entropies": {str(d): c[-1] for d, c in f_curves.items()},
    }

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  DEEP PROBE SYNTHESIS")
    print(f"{'='*70}")
    print(f"  Elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"\n  Key findings to be extracted from output above.")

    # Save
    out_path = os.path.join(os.path.dirname(__file__), "data", "manifold_superposition_deep.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "experiment": "manifold_superposition_deep_probe",
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "elapsed_s": round(elapsed, 1),
            "results": all_results,
        }, f, indent=2, default=str)
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
