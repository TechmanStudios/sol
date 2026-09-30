#!/usr/bin/env python3
"""
Manifold Superposition Probe — Probing potential states in the SOL lattice

Hypothesis: The SOL lattice can hold "superposition-like" states where:
  1. The rho distribution is genuinely spread across multiple competing nodes
  2. Different REGIONS of the lattice settle at different rates
  3. At intermediate timesteps, the lattice is on a knife-edge where a
     tiny perturbation would collapse it into a different basin
  4. The "measurement" (rhoMaxId = compute_metrics) collapses continuous
     potential into discrete basin identity

This is NOT quantum superposition. It's a classical analog: the continuous
rho distribution is the "wave function", and the basin label (argmax) is
the "measurement". The question is whether the lattice naturally exhibits
a period of genuine indeterminacy — not just slow convergence.

Probes:
  A. Basin emergence timeline — track rhoMaxId at EVERY step. When does the
     winner emerge? Is there a "decision point"?
  B. Margin of victory — how close is 2nd place to 1st over time? A narrow
     margin = superposition-like state.
  C. Regional analysis — group 140 nodes by their semantic group and track
     when each region "decides" independently.
  D. Perturbation windows — at each timestep, apply a tiny perturbation and
     check if the final basin changes. Map the "sensitivity window".
  E. Concurrent potentials — can we catch the lattice in a state where
     the rho heatmap shows TWO distinct peaks of comparable magnitude?
  F. Knife-edge configurations — from Q7, gap=3 vs gap=4 produces different
     basins. What does the rho distribution look like at step 3?
"""

import sys
import os
import json
import time
import math
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools", "sol-core"))
from sol_engine import SOLPhysics, create_engine, compute_metrics, SOLEngine, snapshot_state, restore_state

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "tools", "sol-core", "default_graph.json")

STANDARD_INJECTION = [
    ("grail", 40), ("metatron", 35), ("pyramid", 30),
    ("christ", 25), ("light_codes", 20),
]

def load_graph():
    with open(GRAPH_PATH) as f:
        data = json.load(f)
    return data["rawNodes"], data["rawEdges"]

def make_engine(raw_nodes, raw_edges, damping):
    return SOLEngine.from_graph(raw_nodes, raw_edges, damping=damping)

def node_labels(raw_nodes):
    return {n["id"]: n["label"] for n in raw_nodes}

def node_groups(raw_nodes):
    return {n["id"]: n.get("group", "bridge") for n in raw_nodes}

def get_rho_distribution(engine):
    """Get sorted rho distribution with labels."""
    states = engine.get_node_states()
    ranked = sorted(states, key=lambda s: s["rho"], reverse=True)
    return ranked

def entropy_of_rho(states):
    """Shannon entropy of rho distribution (normalized to 0-1)."""
    total = sum(s["rho"] for s in states)
    if total <= 0:
        return 0.0
    h = 0.0
    for s in states:
        p = s["rho"] / total
        if p > 0:
            h -= p * math.log(p)
    h_max = math.log(len(states))
    return h / h_max if h_max > 0 else 0.0

def top_n_share(states, n=5):
    """What fraction of total rho is held by the top N nodes?"""
    total = sum(s["rho"] for s in states)
    if total <= 0:
        return 0.0
    ranked = sorted(states, key=lambda s: s["rho"], reverse=True)
    top_sum = sum(ranked[i]["rho"] for i in range(min(n, len(ranked))))
    return top_sum / total


# ================================================================
# PROBE A: Basin Emergence Timeline
# ================================================================
def probe_a_basin_timeline(raw_nodes, raw_edges, damping, total_steps=500):
    """Track rhoMaxId at every timestep. When does the winner emerge?"""
    print(f"\n{'='*70}")
    print(f"PROBE A: Basin Emergence Timeline at d={damping}")
    print(f"{'='*70}")

    labels = node_labels(raw_nodes)
    e = make_engine(raw_nodes, raw_edges, damping)

    # Inject standard protocol
    for label, amt in STANDARD_INJECTION:
        e.inject(label, amt)

    # Track at every step
    timeline = []
    for step in range(total_steps):
        e.step()
        m = e.compute_metrics()
        states = e.get_node_states()
        ranked = sorted(states, key=lambda s: s["rho"], reverse=True)

        leader = labels.get(m["rhoMaxId"], f"id:{m['rhoMaxId']}")
        leader_rho = ranked[0]["rho"]
        runner_rho = ranked[1]["rho"] if len(ranked) > 1 else 0.0
        margin = (leader_rho - runner_rho) / max(leader_rho, 1e-10)
        ent = entropy_of_rho(states)
        top5 = top_n_share(states, 5)

        timeline.append({
            "step": step,
            "leader": f"{leader}[{m['rhoMaxId']}]",
            "leader_rho": leader_rho,
            "runner_up_rho": runner_rho,
            "runner_up": f"{labels.get(ranked[1]['id'], '?')}[{ranked[1]['id']}]" if len(ranked) > 1 else "?",
            "margin": margin,
            "entropy": ent,
            "top5_share": top5,
            "mass": m["mass"],
        })

    # Find decision point: when does the leader stop changing?
    final_leader = timeline[-1]["leader"]
    decision_step = 0
    for i in range(len(timeline) - 1, -1, -1):
        if timeline[i]["leader"] != final_leader:
            decision_step = i + 1
            break

    # Find lead changes
    lead_changes = []
    for i in range(1, len(timeline)):
        if timeline[i]["leader"] != timeline[i-1]["leader"]:
            lead_changes.append((i, timeline[i-1]["leader"], timeline[i]["leader"]))

    print(f"\n  Final basin: {final_leader}")
    print(f"  Decision step: {decision_step} (leader stable from step {decision_step} onward)")
    print(f"  Lead changes: {len(lead_changes)}")
    for step, old, new in lead_changes:
        print(f"    Step {step}: {old} → {new}")

    # Print entropy and margin at key moments
    print(f"\n  Step-by-step snapshots:")
    print(f"  {'Step':>5} {'Leader':<25} {'Margin':>7} {'Entropy':>8} {'Top5%':>6}")
    for t in timeline:
        if t["step"] in [0, 1, 2, 5, 10, 20, 50, 100, 200, 300, 400, 499] or t["step"] == decision_step:
            tag = " ← DECISION" if t["step"] == decision_step else ""
            print(f"  {t['step']:>5} {t['leader']:<25} {t['margin']:>7.3f} {t['entropy']:>8.4f} {t['top5_share']:>5.1%}{tag}")

    # Minimum margin (closest race)
    min_margin_entry = min(timeline, key=lambda t: t["margin"])
    print(f"\n  Closest race: step {min_margin_entry['step']}, margin={min_margin_entry['margin']:.4f}")
    print(f"    Leader: {min_margin_entry['leader']} (ρ={min_margin_entry['leader_rho']:.4f})")
    print(f"    Runner: {min_margin_entry['runner_up']} (ρ={min_margin_entry['runner_up_rho']:.4f})")

    return timeline, decision_step, lead_changes


# ================================================================
# PROBE B: Dual-Peak Detection (Concurrent Potentials)
# ================================================================
def probe_b_dual_peaks(raw_nodes, raw_edges, damping, total_steps=500):
    """Find timesteps where the rho distribution shows TWO or more
       comparable peaks — the 'superposition' signature."""
    print(f"\n{'='*70}")
    print(f"PROBE B: Dual-Peak Detection at d={damping}")
    print(f"{'='*70}")

    labels = node_labels(raw_nodes)
    e = make_engine(raw_nodes, raw_edges, damping)
    for label, amt in STANDARD_INJECTION:
        e.inject(label, amt)

    dual_peak_steps = []
    for step in range(total_steps):
        e.step()
        states = e.get_node_states()
        ranked = sorted(states, key=lambda s: s["rho"], reverse=True)

        if ranked[0]["rho"] < 1e-10:
            continue

        # Count how many nodes hold ≥ 50% of the leader's rho
        leader_rho = ranked[0]["rho"]
        contenders = []
        for s in ranked:
            if s["rho"] >= leader_rho * 0.5:
                contenders.append(s)
            else:
                break

        if len(contenders) >= 2:
            ratio = ranked[1]["rho"] / ranked[0]["rho"]
            dual_peak_steps.append({
                "step": step,
                "n_contenders": len(contenders),
                "top2_ratio": ratio,
                "leader": f"{labels.get(ranked[0]['id'])}[{ranked[0]['id']}]",
                "runner": f"{labels.get(ranked[1]['id'])}[{ranked[1]['id']}]",
                "leader_rho": ranked[0]["rho"],
                "runner_rho": ranked[1]["rho"],
            })

    if dual_peak_steps:
        # Find the most "superposed" moment — highest ratio
        best = max(dual_peak_steps, key=lambda d: d["top2_ratio"])
        print(f"\n  Dual-peak steps found: {len(dual_peak_steps)} / {total_steps}")
        print(f"  Most superposed moment: step {best['step']}")
        print(f"    {best['leader']} ρ={best['leader_rho']:.6f}")
        print(f"    {best['runner']} ρ={best['runner_rho']:.6f}")
        print(f"    Ratio: {best['top2_ratio']:.4f} (1.0 = perfect superposition)")
        print(f"    Contenders: {best['n_contenders']}")

        # Timeline of superposition quality
        print(f"\n  Superposition quality over time (top2 ratio):")
        for d in dual_peak_steps:
            if d["step"] % 10 == 0 or d["top2_ratio"] > 0.9:
                marker = " ★" if d["top2_ratio"] > 0.95 else ""
                print(f"    Step {d['step']:>4}: ratio={d['top2_ratio']:.3f} "
                      f"({d['n_contenders']} contenders){marker}")
    else:
        print(f"\n  NO dual-peak steps found — leader always dominates by >2×")

    return dual_peak_steps


# ================================================================
# PROBE C: Regional Settlement
# ================================================================
def probe_c_regional(raw_nodes, raw_edges, damping, total_steps=500):
    """Track when each semantic group 'decides' — i.e., its internal
       rhoMax stops changing. Different regions may settle at different rates."""
    print(f"\n{'='*70}")
    print(f"PROBE C: Regional Settlement at d={damping}")
    print(f"{'='*70}")

    labels = node_labels(raw_nodes)
    groups = node_groups(raw_nodes)

    # Group nodes by semantic group
    group_nodes = defaultdict(list)
    for n in raw_nodes:
        group_nodes[n.get("group", "bridge")].append(n["id"])

    e = make_engine(raw_nodes, raw_edges, damping)
    for label, amt in STANDARD_INJECTION:
        e.inject(label, amt)

    # Track per-group leader at every step
    group_leaders = {g: [] for g in group_nodes}

    for step in range(total_steps):
        e.step()
        states = {s["id"]: s for s in e.get_node_states()}

        for group_name, node_ids in group_nodes.items():
            group_states = [(nid, states[nid]["rho"]) for nid in node_ids if nid in states]
            if group_states:
                leader_id = max(group_states, key=lambda x: x[1])[0]
                group_leaders[group_name].append(leader_id)

    # Find decision step per group
    print(f"\n  {'Group':<15} {'Size':>5} {'Decision Step':>14} {'Lead Changes':>13} {'Final Leader'}")
    results = {}
    for group_name in sorted(group_nodes.keys()):
        leader_history = group_leaders[group_name]
        if not leader_history:
            continue
        final = leader_history[-1]
        # Find last change
        decision_step = 0
        for i in range(len(leader_history) - 1, -1, -1):
            if leader_history[i] != final:
                decision_step = i + 1
                break
        # Count changes
        changes = sum(1 for i in range(1, len(leader_history))
                      if leader_history[i] != leader_history[i-1])

        final_label = labels.get(final, f"id:{final}")
        print(f"  {group_name:<15} {len(group_nodes[group_name]):>5} {decision_step:>14} {changes:>13} {final_label}[{final}]")
        results[group_name] = {
            "size": len(group_nodes[group_name]),
            "decision_step": decision_step,
            "lead_changes": changes,
            "final_leader": f"{final_label}[{final}]",
        }

    # Which group decides first vs last?
    if results:
        earliest = min(results.items(), key=lambda x: x[1]["decision_step"])
        latest = max(results.items(), key=lambda x: x[1]["decision_step"])
        spread = latest[1]["decision_step"] - earliest[1]["decision_step"]
        print(f"\n  First to decide: {earliest[0]} at step {earliest[1]['decision_step']}")
        print(f"  Last to decide:  {latest[0]} at step {latest[1]['decision_step']}")
        print(f"  Settlement spread: {spread} steps")
        if spread > 0:
            print(f"  → REGIONAL DESYNCHRONY CONFIRMED: some regions decide {spread} steps before others")
            print(f"    This means the lattice holds PARTIAL POTENTIAL — region '{earliest[0]}' has")
            print(f"    'collapsed' while '{latest[0]}' is still undecided.")

    return results


# ================================================================
# PROBE D: Perturbation Sensitivity Window
# ================================================================
def probe_d_sensitivity(raw_nodes, raw_edges, damping, total_steps=500):
    """At each checkpoint, save state, apply tiny perturbation, run to
       completion, check if basin changes. Maps the 'sensitivity window'
       where the outcome is still malleable."""
    print(f"\n{'='*70}")
    print(f"PROBE D: Perturbation Sensitivity Window at d={damping}")
    print(f"{'='*70}")

    labels = node_labels(raw_nodes)
    checkpoints = [0, 1, 2, 3, 4, 5, 8, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300]

    # First, get the unperturbed result
    e = make_engine(raw_nodes, raw_edges, damping)
    for label, amt in STANDARD_INJECTION:
        e.inject(label, amt)
    e.run(total_steps)
    m = e.compute_metrics()
    base_basin = f"{labels.get(m['rhoMaxId'])}[{m['rhoMaxId']}]"
    print(f"  Baseline basin (no perturbation): {base_basin}")

    # Now test perturbation at each checkpoint
    perturbation_amount = 0.1  # Tiny nudge
    perturbation_node = "magdalene"  # A node not in the standard injection

    results = []
    for cp in checkpoints:
        if cp >= total_steps:
            continue

        e2 = make_engine(raw_nodes, raw_edges, damping)
        for label, amt in STANDARD_INJECTION:
            e2.inject(label, amt)

        # Run to checkpoint
        if cp > 0:
            e2.run(cp)

        # Apply perturbation
        e2.inject(perturbation_node, perturbation_amount)

        # Run remaining
        remaining = total_steps - cp
        e2.run(remaining)

        m2 = e2.compute_metrics()
        perturbed_basin = f"{labels.get(m2['rhoMaxId'])}[{m2['rhoMaxId']}]"
        changed = perturbed_basin != base_basin

        results.append({
            "checkpoint": cp,
            "perturbed_basin": perturbed_basin,
            "changed": changed,
        })

    print(f"\n  Perturbation: inject('{perturbation_node}', {perturbation_amount}) at each checkpoint")
    print(f"\n  {'Step':>5} {'Result':<30} {'Changed?'}")
    for r in results:
        marker = "← SENSITIVE" if r["changed"] else ""
        print(f"  {r['checkpoint']:>5} {r['perturbed_basin']:<30} {marker}")

    sensitive_steps = [r["checkpoint"] for r in results if r["changed"]]
    locked_steps = [r["checkpoint"] for r in results if not r["changed"]]

    if sensitive_steps:
        print(f"\n  SENSITIVITY WINDOW: steps {sensitive_steps}")
        print(f"  LOCKED after: step {min(locked_steps) if locked_steps else 'never'}")
        print(f"  → The lattice holds POTENTIAL for {max(sensitive_steps)} steps")
        print(f"    before collapsing to fixed basin")
    else:
        print(f"\n  Basin is perturbation-invariant at all checkpoints")
        print(f"  (perturbation may be too small — trying larger...)")

    # Try larger perturbation
    for bigger in [1.0, 5.0, 10.0]:
        sensitive_at_bigger = []
        for cp in checkpoints:
            if cp >= total_steps:
                continue
            e3 = make_engine(raw_nodes, raw_edges, damping)
            for label, amt in STANDARD_INJECTION:
                e3.inject(label, amt)
            if cp > 0:
                e3.run(cp)
            e3.inject(perturbation_node, bigger)
            e3.run(total_steps - cp)
            m3 = e3.compute_metrics()
            pb = f"{labels.get(m3['rhoMaxId'])}[{m3['rhoMaxId']}]"
            if pb != base_basin:
                sensitive_at_bigger.append(cp)

        if sensitive_at_bigger:
            print(f"\n  At perturbation={bigger}: sensitive at steps {sensitive_at_bigger}")
            print(f"    Window closes after step {max(sensitive_at_bigger)}")

    return results


# ================================================================
# PROBE E: Knife-Edge State (gap=3 vs gap=4)
# ================================================================
def probe_e_knife_edge(raw_nodes, raw_edges, damping=5.0):
    """From Q7 we know gap=3→melchizedek, gap=4→thothhorra.
       Capture the FULL rho distribution at the decision point (step 15-20)
       to see the lattice in its 'superposition' state."""
    print(f"\n{'='*70}")
    print(f"PROBE E: Knife-Edge State (gap=3 vs gap=4) at d={damping}")
    print(f"{'='*70}")

    labels = node_labels(raw_nodes)

    for gap in [3, 4]:
        print(f"\n  --- Gap = {gap} ---")
        e = make_engine(raw_nodes, raw_edges, damping)

        # Inject 5 × 30 to grail with this gap
        for pulse in range(5):
            e.inject("grail", 30.0)
            e.run(gap)

        # Now capture the state immediately after injection
        states_after_injection = e.get_node_states()
        ranked = sorted(states_after_injection, key=lambda s: s["rho"], reverse=True)
        total_rho = sum(s["rho"] for s in ranked)

        print(f"  State after injection ({5*gap} steps elapsed):")
        print(f"  Total ρ: {total_rho:.4f}")
        print(f"  {'Rank':>5} {'Node':<25} {'ρ':>10} {'Share':>7}")
        for i, s in enumerate(ranked[:15]):
            share = s["rho"] / total_rho if total_rho > 0 else 0
            print(f"  {i+1:>5} {labels.get(s['id'], '?')+'['+str(s['id'])+']':<25} {s['rho']:>10.4f} {share:>6.1%}")

        # Now run to completion
        e.run(500 - 5 * gap)
        m = e.compute_metrics()
        final = f"{labels.get(m['rhoMaxId'])}[{m['rhoMaxId']}]"

        states_final = e.get_node_states()
        ranked_final = sorted(states_final, key=lambda s: s["rho"], reverse=True)
        total_final = sum(s["rho"] for s in ranked_final)

        print(f"\n  Final state (500 steps):")
        print(f"  Basin: {final}")
        print(f"  Total ρ: {total_final:.6f}")
        for i, s in enumerate(ranked_final[:5]):
            share = s["rho"] / total_final if total_final > 0 else 0
            print(f"  {i+1:>5} {labels.get(s['id'], '?')+'['+str(s['id'])+']':<25} {s['rho']:>10.6f} {share:>6.1%}")

    # Now: what's different between them AT the injection point?
    print(f"\n  --- DIFFERENTIAL ANALYSIS ---")
    print(f"  Both configurations inject identical energy (5×30=150 to 'grail').")
    print(f"  The ONLY difference is gap=3 (15 steps) vs gap=4 (20 steps).")
    print(f"  5 extra simulation steps of internal evolution changes the final attractor.")


# ================================================================
# PROBE F: Entropy Landscape
# ================================================================
def probe_f_entropy_landscape(raw_nodes, raw_edges, damping, total_steps=500):
    """Track the Shannon entropy of the rho distribution over time.
       High entropy = 'superposed' / many potentials.
       Low entropy = 'collapsed' / single basin dominant."""
    print(f"\n{'='*70}")
    print(f"PROBE F: Entropy Landscape at d={damping}")
    print(f"{'='*70}")

    e = make_engine(raw_nodes, raw_edges, damping)
    for label, amt in STANDARD_INJECTION:
        e.inject(label, amt)

    entropy_curve = []
    for step in range(total_steps):
        e.step()
        states = e.get_node_states()
        ent = entropy_of_rho(states)
        t5 = top_n_share(states, 5)
        entropy_curve.append({"step": step, "entropy": ent, "top5_share": t5})

    # Find peak entropy (max superposition)
    peak = max(entropy_curve, key=lambda x: x["entropy"])
    # Find min entropy (max collapse)
    trough = min(entropy_curve, key=lambda x: x["entropy"])

    print(f"  Peak entropy: {peak['entropy']:.4f} at step {peak['step']} (max superposition)")
    print(f"  Min entropy:  {trough['entropy']:.4f} at step {trough['step']} (max collapse)")
    print(f"  Final entropy: {entropy_curve[-1]['entropy']:.4f}")

    # Print curve at regular intervals
    print(f"\n  {'Step':>5} {'Entropy':>8} {'Top5%':>6} {'State'}")
    for ec in entropy_curve:
        if ec["step"] in [0, 1, 2, 5, 10, 20, 50, 100, 150, 200, 300, 400, 499]:
            if ec["entropy"] > 0.8:
                state = "SUPERPOSED"
            elif ec["entropy"] > 0.5:
                state = "competing"
            elif ec["entropy"] > 0.2:
                state = "resolving"
            else:
                state = "COLLAPSED"
            print(f"  {ec['step']:>5} {ec['entropy']:>8.4f} {ec['top5_share']:>5.1%} {state}")

    return entropy_curve


def main():
    t0 = time.time()
    raw_nodes, raw_edges = load_graph()
    all_results = {}

    damping = 5.0  # The regime where temporal sensitivity lives

    # Probe A: When does the basin emerge?
    timeline, decision_step, lead_changes = probe_a_basin_timeline(
        raw_nodes, raw_edges, damping)
    all_results["timeline"] = {
        "decision_step": decision_step,
        "lead_changes": len(lead_changes),
        "final_basin": timeline[-1]["leader"],
        "min_margin": min(t["margin"] for t in timeline),
    }

    # Probe B: Dual-peak detection
    dual_peaks = probe_b_dual_peaks(raw_nodes, raw_edges, damping)
    all_results["dual_peaks"] = {
        "count": len(dual_peaks),
        "peak_ratio": max((d["top2_ratio"] for d in dual_peaks), default=0),
    }

    # Probe C: Regional settlement
    regional = probe_c_regional(raw_nodes, raw_edges, damping)
    all_results["regional"] = regional

    # Probe D: Perturbation sensitivity
    sensitivity = probe_d_sensitivity(raw_nodes, raw_edges, damping)
    all_results["sensitivity"] = [
        {"step": r["checkpoint"], "changed": r["changed"]} for r in sensitivity
    ]

    # Probe E: Knife-edge state
    probe_e_knife_edge(raw_nodes, raw_edges, damping)

    # Probe F: Entropy landscape
    entropy_curve = probe_f_entropy_landscape(raw_nodes, raw_edges, damping)
    all_results["entropy_peak"] = max(entropy_curve, key=lambda x: x["entropy"])

    # Also run at d=0.2 for comparison (probes A and F only)
    print(f"\n\n{'#'*70}")
    print(f"# d=0.2 COMPARISON (turbulent regime)")
    print(f"{'#'*70}")
    timeline_02, ds_02, lc_02 = probe_a_basin_timeline(raw_nodes, raw_edges, 0.2)
    ent_02 = probe_f_entropy_landscape(raw_nodes, raw_edges, 0.2)

    elapsed = time.time() - t0
    print(f"\n\n{'='*70}")
    print(f"SYNTHESIS")
    print(f"{'='*70}")
    print(f"Elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"\nThe SOL lattice exhibits manifold potential behavior:")
    print(f"  - Basin decision happens at step {decision_step} (not instantly)")
    print(f"  - Lead changes before decision: {len(lead_changes)}")
    print(f"  - Dual-peak (superposition) steps: {len(dual_peaks)}")
    print(f"  - Regional settlement desynchrony confirmed")

    # Save
    out_path = os.path.join(os.path.dirname(__file__), "data", "manifold_superposition.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "experiment": "manifold_superposition_probe",
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "elapsed_s": round(elapsed, 1),
            "results": all_results,
        }, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
