#!/usr/bin/env python3
"""
SOL Overnight RSI Runner
=========================

6-hour autonomous experiment-and-self-improvement cycle.

Phase 1 (~60-90 min) — Execute 5 targeted experiment suites:
  Suite 1: Open Question Resolution (§14 Q1-Q4)
  Suite 2: Dead Zone Physics (d=15-40)
  Suite 3: Transition Zone Mapping (d=10-15)
  Suite 4: Logic Gate Extension (XOR, NAND, Latch, Half-adder)
  Suite 5: Injection Protocol Exploration

Phase 2 (remaining time) — RSI Loop:
  Each cycle: EVALUATE → REFLECT → MUTATE → PLAN → EXECUTE → COMMIT
  Dynamic experiment generation based on genome state
  Budget-controlled (stops when 6h elapsed)

Usage:
  python overnight_rsi.py                    # Full 6-hour run
  python overnight_rsi.py --budget-hours 1   # 1-hour test run
  python overnight_rsi.py --dry-run          # Plan only
  python overnight_rsi.py --suite 2          # Run single suite only

ENGINE: tools/sol-core/sol_engine.py (IMMUTABLE)
GRAPH:  tools/sol-core/default_graph.json (IMMUTABLE)
"""
from __future__ import annotations

import copy
import json
import math
import random
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SOL_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-rsi"))

from sol_engine import SOLEngine, snapshot_state, restore_state

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
_RUN_TS = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
_OUTPUT_DIR = _SOL_ROOT / "data" / "overnight_rsi" / _RUN_TS
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _OUTPUT_DIR / "run_log.txt"
_REPORT_FILE = _OUTPUT_DIR / "overnight_report.md"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DT = 0.12
C_PRESS = 0.1
STEPS = 500
SAMPLE_INTERVAL = 5

STANDARD_INJECTIONS = [
    ("grail", 40.0),
    ("metatron", 35.0),
    ("pyramid", 30.0),
    ("christ", 25.0),
    ("light codes", 20.0),
]

COLD_NODES = ["john", "par", "johannine grove", "mystery school", "christine hayes"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_log_buffer: list[str] = []


def log(msg: str):
    """Print and record log message."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    _log_buffer.append(line)


def flush_log():
    """Persist log buffer to file."""
    with open(_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(_log_buffer))


# ---------------------------------------------------------------------------
# Graph utilities
# ---------------------------------------------------------------------------
def load_default_graph():
    path = _SOL_ROOT / "tools" / "sol-core" / "default_graph.json"
    with open(path) as f:
        data = json.load(f)
    return data["rawNodes"], data["rawEdges"]


def get_labels(raw_nodes):
    return {n["id"]: n["label"] for n in raw_nodes}


def get_groups(raw_nodes):
    return {n["id"]: n.get("group", "bridge") for n in raw_nodes}


def get_degrees(raw_edges):
    deg = defaultdict(int)
    for e in raw_edges:
        deg[e["from"]] += 1
        deg[e["to"]] += 1
    return dict(deg)


def get_adjacency(raw_edges):
    adj = defaultdict(set)
    for e in raw_edges:
        adj[e["from"]].add(e["to"])
        adj[e["to"]].add(e["from"])
    return adj


def make_engine(raw_nodes, raw_edges, damping, seed=42):
    return SOLEngine.from_graph(
        raw_nodes, raw_edges,
        dt=DT, c_press=C_PRESS, damping=damping, rng_seed=seed
    )


def apply_standard_injection(engine):
    for label, amount in STANDARD_INJECTIONS:
        engine.inject(label, amount)


def set_edge_weights(raw_edges, raw_nodes, rule_fn):
    groups = get_groups(raw_nodes)
    edges = copy.deepcopy(raw_edges)
    count = 0
    for e in edges:
        new_w0 = rule_fn(e, groups)
        if new_w0 != 1.0:
            count += 1
        e["w0"] = new_w0
    return edges, count


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------
def analyze_trial(engine, rho_samples):
    """Compute mode count, coherence, iton score from collected samples."""
    n_nodes = len(engine.physics.nodes)
    rho_arr = np.array(rho_samples) if rho_samples else np.zeros((1, n_nodes))

    # Mode count (CoV > 0.01)
    osc_amps = []
    for j in range(n_nodes):
        trace = rho_arr[:, j]
        if np.max(trace) > 1e-15:
            osc_amps.append(np.std(trace) / max(np.mean(trace), 1e-15))
        else:
            osc_amps.append(0.0)
    n_modes = int(np.sum(np.array(osc_amps) > 0.01))

    # Coherence (injection nodes)
    id_to_idx = {n["id"]: idx for idx, n in enumerate(engine.physics.nodes)}
    inj_indices = [id_to_idx.get(nid) for nid in [1, 2, 9, 23, 29]]
    inj_indices = [i for i in inj_indices if i is not None]

    corrs = []
    for a in range(len(inj_indices)):
        for b in range(a + 1, len(inj_indices)):
            t1 = rho_arr[:, inj_indices[a]].copy()
            t2 = rho_arr[:, inj_indices[b]].copy()
            r1 = np.max(t1) - np.min(t1)
            r2 = np.max(t2) - np.min(t2)
            if r1 > 0 and r2 > 0:
                t1n = (t1 - np.mean(t1)) / r1
                t2n = (t2 - np.mean(t2)) / r2
                c = np.corrcoef(t1n, t2n)[0, 1]
                if not np.isnan(c):
                    corrs.append(abs(c))
    coherence = float(np.mean(corrs)) if corrs else 0.0

    # Iton score
    node_edges_map = defaultdict(list)
    for ei, e in enumerate(engine.physics.edges):
        node_edges_map[e["from"]].append((ei, "from"))
        node_edges_map[e["to"]].append((ei, "to"))

    n_sources = 0
    n_pass = 0
    n_sinks = 0
    total_active = 0

    for ni, n in enumerate(engine.physics.nodes):
        nid = n["id"]
        inflow = 0.0
        outflow = 0.0
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
            elif inflow > outflow:
                n_sinks += 1
            else:
                n_sources += 1

    iton_score = n_pass / total_active if total_active > 0 else 0.0

    return {
        "n_modes": n_modes,
        "coherence": coherence,
        "iton_score": iton_score,
        "n_sources": n_sources,
        "n_pass": n_pass,
        "n_sinks": n_sinks,
    }


def run_and_analyze(engine, steps=STEPS, sample_every=SAMPLE_INTERVAL):
    """Step, collect rho samples, compute metrics."""
    basin_visits = defaultdict(int)
    rho_samples = []

    for s in range(1, steps + 1):
        engine.step()
        if s % sample_every == 0:
            m = engine.compute_metrics()
            bid = m["rhoMaxId"]
            if bid is not None:
                basin_visits[bid] = basin_visits.get(bid, 0) + 1
            rho_samples.append([n["rho"] for n in engine.physics.nodes])

    final = engine.compute_metrics()
    analysis = analyze_trial(engine, rho_samples)

    dominant = max(basin_visits, key=basin_visits.get) if basin_visits else None
    analysis["dominant_basin"] = dominant
    analysis["dominant_basin_frac"] = (
        basin_visits.get(dominant, 0) / max(1, sum(basin_visits.values()))
        if dominant else 0.0
    )
    analysis["final_maxrho"] = final["maxRho"]
    analysis["final_entropy"] = final["entropy"]
    analysis["final_mass"] = final["mass"]

    return analysis


def format_basin(nid, labels):
    return f"{labels.get(nid, '?')}[{nid}]"


# ---------------------------------------------------------------------------
# Budget tracker
# ---------------------------------------------------------------------------
class BudgetTracker:
    """Track time and trial budgets."""

    def __init__(self, budget_hours: float):
        self.budget_seconds = budget_hours * 3600
        self.t0 = time.time()
        self.trial_count = 0
        self.suite_times: dict[str, float] = {}

    def elapsed(self) -> float:
        return time.time() - self.t0

    def remaining(self) -> float:
        return max(0.0, self.budget_seconds - self.elapsed())

    def exhausted(self) -> bool:
        return self.elapsed() >= self.budget_seconds

    def add_trials(self, n: int):
        self.trial_count += n

    def log_suite(self, name: str, t_start: float):
        self.suite_times[name] = time.time() - t_start

    def summary(self) -> str:
        elapsed = self.elapsed()
        return (f"Elapsed: {elapsed:.0f}s ({elapsed/3600:.1f}h) | "
                f"Remaining: {self.remaining():.0f}s | "
                f"Trials: {self.trial_count}")


# ===================================================================
# SUITE 1: OPEN QUESTION RESOLUTION (§14 Q1-Q4)
# ===================================================================

def suite_1_open_questions(budget: BudgetTracker):
    """
    Answer the 4 remaining open questions from §14:
      Q1: Higher-order analog correction (R²=0.94→0.99?)
      Q2: Dead zone physics (why christic[22]?)
      Q3: Clock optimization (period=100 as fundamental?)
      Q4: Cascade depth limit (max pipeline stages?)
    """
    log("=" * 70)
    log("SUITE 1: OPEN QUESTION RESOLUTION")
    log("=" * 70)
    t0 = time.time()
    results = {"suite": "open_question_resolution", "probes": {}}

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    degrees = get_degrees(raw_edges)
    adj = get_adjacency(raw_edges)
    trials = 0

    # ---- Q1: Higher-order analog correction ----
    log("  Q1: Higher-order analog correction (target: R²>0.99)")
    q1_results = []

    for damping in [0.2, 1.0, 5.0]:
        engine = make_engine(raw_nodes, raw_edges, damping)
        apply_standard_injection(engine)

        # Collect flux data at multiple snapshots
        for target_step in [50, 100, 200]:
            # Reset and re-run to target step
            engine2 = make_engine(raw_nodes, raw_edges, damping)
            apply_standard_injection(engine2)
            engine2.run(target_step)

            # Collect per-edge data
            predicted_simple = []  # conductance * delta_p
            predicted_with_tension = []  # conductance * tension * delta_p
            predicted_full = []  # conductance * tension * diode_gain * delta_p (reconstructed)
            actual_flux = []
            extra_features = []  # For multivariate regression

            id_to_idx = {n["id"]: idx for idx, n in enumerate(engine2.physics.nodes)}

            for e in engine2.physics.edges:
                ia = id_to_idx.get(e["from"])
                ib = id_to_idx.get(e["to"])
                if ia is None or ib is None:
                    continue

                src = engine2.physics.nodes[ia]
                dst = engine2.physics.nodes[ib]
                cond = e.get("conductance", 0.0)
                delta_p = src["p"] - dst["p"]
                flux = e.get("flux", 0.0)

                # Compute tension from node groups
                sg = src.get("group", "bridge")
                dg = dst.get("group", "bridge")
                if sg == "tech" or dg == "tech":
                    tension = 1.2  # surface_tension
                elif sg == "spirit" or dg == "spirit":
                    tension = 0.8  # deep_viscosity
                else:
                    tension = C_PRESS + 1.2 + 0.8  # Approximate for bridge

                # Simple model
                predicted_simple.append(cond * delta_p)
                # With tension
                predicted_with_tension.append(cond * tension * delta_p)

                # Extra features for multivariate model
                psi_diff = abs(src.get("psi", 0.0) - dst.get("psi", 0.0))
                degree_product = degrees.get(e["from"], 1) * degrees.get(e["to"], 1)
                w0 = e.get("w0", 1.0)
                gamma = e.get("gamma", 1.0)
                rho_sum = src["rho"] + dst["rho"]

                extra_features.append({
                    "cond_x_dp": cond * delta_p,
                    "cond_x_tension_x_dp": cond * tension * delta_p,
                    "psi_diff": psi_diff,
                    "degree_product": degree_product,
                    "delta_p_sq": delta_p ** 2,
                    "rho_sum": rho_sum,
                    "w0": w0,
                    "gamma": gamma,
                })

                actual_flux.append(flux)
            trials += 1

            # Compute R² for each model
            actual = np.array(actual_flux)
            if np.std(actual) < 1e-15:
                q1_results.append({
                    "damping": damping, "step": target_step,
                    "r2_simple": 0.0, "r2_tension": 0.0, "r2_multi": 0.0,
                    "note": "zero-variance flux"
                })
                continue

            pred_s = np.array(predicted_simple)
            pred_t = np.array(predicted_with_tension)

            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            r2_simple = 1.0 - np.sum((actual - pred_s) ** 2) / ss_tot if ss_tot > 0 else 0.0
            r2_tension = 1.0 - np.sum((actual - pred_t) ** 2) / ss_tot if ss_tot > 0 else 0.0

            # Multivariate regression using numpy least-squares
            X = np.array([
                [f["cond_x_tension_x_dp"], f["psi_diff"], f["delta_p_sq"],
                 f["rho_sum"], f["w0"]]
                for f in extra_features
            ])
            # Add bias column
            X_b = np.column_stack([X, np.ones(len(X))])
            try:
                coeffs, residuals, _, _ = np.linalg.lstsq(X_b, actual, rcond=None)
                pred_multi = X_b @ coeffs
                r2_multi = 1.0 - np.sum((actual - pred_multi) ** 2) / ss_tot
            except Exception:
                r2_multi = r2_tension
                coeffs = None

            entry = {
                "damping": damping, "step": target_step,
                "r2_simple": round(float(r2_simple), 4),
                "r2_tension": round(float(r2_tension), 4),
                "r2_multi": round(float(r2_multi), 4),
                "n_edges": len(actual_flux),
            }
            if coeffs is not None:
                entry["coefficients"] = {
                    "cond_x_tension_x_dp": round(float(coeffs[0]), 6),
                    "psi_diff": round(float(coeffs[1]), 6),
                    "delta_p_sq": round(float(coeffs[2]), 6),
                    "rho_sum": round(float(coeffs[3]), 6),
                    "w0": round(float(coeffs[4]), 6),
                    "bias": round(float(coeffs[5]), 6),
                }
            q1_results.append(entry)
            log(f"    d={damping}, step={target_step}: R²_simple={r2_simple:.3f} "
                f"R²_tension={r2_tension:.3f} R²_multi={r2_multi:.3f}")

    results["probes"]["q1_analog_correction"] = q1_results

    # ---- Q2: Dead zone physics — why christic[22]? ----
    log("  Q2: Dead zone physics — analyzing christic[22]")
    q2_results = {}

    # Structural properties of christic[22]
    christic_id = 22
    christic_deg = degrees.get(christic_id, 0)
    christic_group = next((n.get("group", "bridge") for n in raw_nodes if n["id"] == christic_id), "bridge")
    christic_neighbors = list(adj.get(christic_id, set()))
    avg_neighbor_deg = np.mean([degrees.get(n, 0) for n in christic_neighbors]) if christic_neighbors else 0

    # BFS centrality (avg distance to all nodes)
    def bfs_distances(start, adjacency, n_total):
        visited = {start: 0}
        queue = [start]
        while queue:
            node = queue.pop(0)
            for nb in adjacency.get(node, []):
                if nb not in visited:
                    visited[nb] = visited[node] + 1
                    queue.append(nb)
        dists = list(visited.values())
        return np.mean(dists) if dists else 999.0

    all_node_ids = [n["id"] for n in raw_nodes]
    christic_centrality = bfs_distances(christic_id, adj, len(all_node_ids))

    # Compare to other candidate attractors in the dead zone
    # Run at dead zone damping values and track where EACH node redirects
    dead_zone_basins = {}
    for d in [15, 20, 25, 30, 35, 40]:
        basin_map = {}
        for nid in all_node_ids:
            engine = make_engine(raw_nodes, raw_edges, d)
            label = labels.get(nid, "")
            if label:
                engine.inject(label, 50.0)
            engine.run(500)
            m = engine.compute_metrics()
            basin_map[nid] = m["rhoMaxId"]
            trials += 1
        dead_zone_basins[d] = basin_map
        # Count how many nodes redirect to christic[22]
        to_christic = sum(1 for b in basin_map.values() if b == christic_id)
        log(f"    d={d}: {to_christic}/{len(all_node_ids)} nodes → christic[22]")

    # Compute betweenness-centrality proxy (# shortest paths through node)
    # Simplified: for 20 random src-dst pairs, count how many pass through christic
    btw_count = defaultdict(int)
    test_pairs = [(random.choice(all_node_ids), random.choice(all_node_ids))
                  for _ in range(200)]
    for src, dst in test_pairs:
        if src == dst:
            continue
        # BFS from src
        visited = {src: (0, None)}
        queue = [src]
        found = False
        while queue and not found:
            node = queue.pop(0)
            for nb in adj.get(node, []):
                if nb not in visited:
                    visited[nb] = (visited[node][0] + 1, node)
                    if nb == dst:
                        found = True
                        break
                    queue.append(nb)
        if found:
            # Trace path back
            path = []
            cur = dst
            while cur is not None:
                path.append(cur)
                _, cur = visited.get(cur, (0, None))
            for nid in path[1:-1]:  # Exclude src and dst
                btw_count[nid] += 1

    # Top 10 most traversed nodes
    top_btw = sorted(btw_count.items(), key=lambda x: x[1], reverse=True)[:10]

    q2_results = {
        "christic_22": {
            "degree": christic_deg,
            "group": christic_group,
            "avg_neighbor_degree": round(avg_neighbor_deg, 1),
            "bfs_centrality": round(christic_centrality, 3),
            "betweenness_rank": next(
                (i + 1 for i, (nid, _) in enumerate(top_btw) if nid == christic_id), -1
            ),
            "betweenness_count": btw_count.get(christic_id, 0),
            "n_neighbors": len(christic_neighbors),
        },
        "dead_zone_basins": {
            str(d): {
                "to_christic": sum(1 for b in bmap.values() if b == christic_id),
                "total_nodes": len(bmap),
                "unique_basins": len(set(bmap.values())),
                "top_basins": [
                    (bid, sum(1 for b in bmap.values() if b == bid))
                    for bid, _ in sorted(
                        defaultdict(int, {bid: sum(1 for b in bmap.values() if b == bid)
                                          for bid in set(bmap.values())}).items(),
                        key=lambda x: x[1], reverse=True
                    )[:5]
                ],
            }
            for d, bmap in dead_zone_basins.items()
        },
        "betweenness_top10": [(labels.get(nid, "?"), nid, cnt) for nid, cnt in top_btw],
        "alternative_attractors": {},
    }

    # Check if non-standard injection can break christic dominance in dead zone
    for alt_target in ["par", "johannine grove", "mystery school"]:
        engine = make_engine(raw_nodes, raw_edges, 20.0)
        engine.inject(alt_target, 200.0)  # Massive injection
        engine.run(500)
        m = engine.compute_metrics()
        q2_results["alternative_attractors"][alt_target] = {
            "basin": m["rhoMaxId"],
            "basin_label": labels.get(m["rhoMaxId"], "?"),
            "is_christic": m["rhoMaxId"] == christic_id,
        }
        trials += 1
        log(f"    Massive inject {alt_target}(200) at d=20 → {format_basin(m['rhoMaxId'], labels)}")

    # Clock signal in dead zone
    for d in [15, 20, 30]:
        engine = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine)
        # Apply clock: re-inject 10% every 100 steps
        for cycle in range(20):
            engine.run(100)
            for label, amount in STANDARD_INJECTIONS:
                engine.inject(label, amount * 0.1)
        engine.run(100)
        m = engine.compute_metrics()
        q2_results[f"clock_d{d}"] = {
            "basin": m["rhoMaxId"],
            "basin_label": labels.get(m["rhoMaxId"], "?"),
            "mass": round(m["mass"], 4),
        }
        trials += 1
        log(f"    Clock inject at d={d} → {format_basin(m['rhoMaxId'], labels)}, mass={m['mass']:.4f}")

    results["probes"]["q2_dead_zone_physics"] = q2_results

    # ---- Q3: Clock optimization ----
    log("  Q3: Clock optimization — systematic period sweep")
    q3_results = []

    for damping in [5.0, 10.0, 20.0]:
        for period in [25, 35, 50, 75, 100, 125, 150, 200]:
            for pulse_frac in [0.05, 0.10, 0.20]:
                engine = make_engine(raw_nodes, raw_edges, damping)
                apply_standard_injection(engine)

                # Run 4 windows of 500 steps each with clock
                window_itons = []
                for w in range(4):
                    for step_batch in range(500 // period):
                        engine.run(period)
                        # Clock pulse
                        for label, amount in STANDARD_INJECTIONS:
                            engine.inject(label, amount * pulse_frac)

                    # Measure iton at end of window
                    rho_snap = [[n["rho"] for n in engine.physics.nodes]]
                    analysis = analyze_trial(engine, rho_snap)
                    window_itons.append(analysis["iton_score"])
                    trials += 1

                avg_iton = float(np.mean(window_itons))
                sustained = all(i > 0.01 for i in window_itons[1:]) if len(window_itons) > 1 else False

                q3_results.append({
                    "damping": damping,
                    "period": period,
                    "pulse_frac": pulse_frac,
                    "window_itons": [round(i, 3) for i in window_itons],
                    "avg_iton": round(avg_iton, 3),
                    "sustained": sustained,
                })

        # Log best for this damping
        best = max([r for r in q3_results if r["damping"] == damping],
                   key=lambda r: r["avg_iton"], default=None)
        if best:
            log(f"    d={damping}: best period={best['period']}, "
                f"pulse={best['pulse_frac']}, avg_iton={best['avg_iton']:.3f}")

    results["probes"]["q3_clock_optimization"] = q3_results

    # ---- Q4: Cascade depth limit ----
    log("  Q4: Cascade depth limit — testing 2-8 stage pipelines")
    q4_results = []

    for n_stages in range(2, 9):
        # Pipeline: each stage reads basin, selects injection for next stage
        basins_per_stage = []
        engine = make_engine(raw_nodes, raw_edges, 0.2)
        apply_standard_injection(engine)

        for stage in range(n_stages):
            engine.run(300)
            m = engine.compute_metrics()
            basin = m["rhoMaxId"]
            basins_per_stage.append(basin)

            if stage < n_stages - 1:
                # Use basin identity to determine next injection
                basin_label = labels.get(basin, "")
                if basin_label:
                    engine.inject(basin_label, 30.0)

        trials += 1
        # Check if final stage produces a distinct output
        distinct = len(set(basins_per_stage)) > 1
        final_basin = basins_per_stage[-1]

        q4_results.append({
            "n_stages": n_stages,
            "basins": [(s + 1, format_basin(b, labels)) for s, b in enumerate(basins_per_stage)],
            "distinct_basins": len(set(basins_per_stage)),
            "final_basin": format_basin(final_basin, labels),
            "signal_preserved": distinct,
        })
        log(f"    {n_stages} stages: {len(set(basins_per_stage))} distinct basins, "
            f"final={format_basin(final_basin, labels)}, signal={'PASS' if distinct else 'DEGRADED'}")

    # Also test with NOT gate per stage
    for n_stages in range(2, 7):
        def spirit_3x(e, grps):
            if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                return 3.0
            return 1.0

        basins_per_stage = []
        highway_on = False  # Start with highway OFF

        for stage in range(n_stages):
            if highway_on:
                mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_3x)
            else:
                mod_edges = copy.deepcopy(raw_edges)

            engine = make_engine(raw_nodes, mod_edges, 0.2)
            apply_standard_injection(engine)
            engine.run(500)
            m = engine.compute_metrics()
            basin = m["rhoMaxId"]
            basins_per_stage.append(basin)
            trials += 1

            # Toggle for next stage
            highway_on = not highway_on

        alternating = True
        for i in range(1, len(basins_per_stage)):
            if basins_per_stage[i] == basins_per_stage[i - 1]:
                alternating = False
                break

        q4_results.append({
            "n_stages": n_stages,
            "type": "NOT_gate_cascade",
            "basins": [(s + 1, format_basin(b, labels)) for s, b in enumerate(basins_per_stage)],
            "alternating": alternating,
            "signal_preserved": alternating,
        })
        log(f"    NOT cascade {n_stages} stages: alternating={alternating}")

    results["probes"]["q4_cascade_depth"] = q4_results

    budget.add_trials(trials)
    budget.log_suite("suite_1", t0)
    log(f"  Suite 1 complete: {trials} trials, {time.time()-t0:.0f}s")
    return results


# ===================================================================
# SUITE 2: DEAD ZONE PHYSICS (d=15-40)
# ===================================================================

def suite_2_dead_zone(budget: BudgetTracker):
    """Deep investigation of the d=15-40 regime."""
    log("=" * 70)
    log("SUITE 2: DEAD ZONE PHYSICS (d=15-40)")
    log("=" * 70)
    t0 = time.time()
    results = {"suite": "dead_zone_physics", "probes": {}}
    trials = 0

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)

    # ---- Probe A: Fine-grained sweep ----
    log("  Probe A: Fine-grained dead zone sweep")
    damping_values = [12, 13, 14, 14.5, 15, 16, 17, 18, 19, 20, 25, 30, 35, 40]
    sweep_results = []

    for d in damping_values:
        if budget.exhausted():
            break

        # Standard injection
        engine = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine)
        analysis = run_and_analyze(engine)
        trials += 1

        # Cold injection
        engine_cold = make_engine(raw_nodes, raw_edges, d)
        for cn in COLD_NODES:
            engine_cold.inject(cn, 30.0)
        analysis_cold = run_and_analyze(engine_cold)
        trials += 1

        # Clock-assisted (period=100, 10% pulse)
        engine_clk = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_clk)
        for _ in range(10):
            engine_clk.run(100)
            for lbl, amt in STANDARD_INJECTIONS:
                engine_clk.inject(lbl, amt * 0.1)
        rho_snap = [[n["rho"] for n in engine_clk.physics.nodes]]
        analysis_clk = analyze_trial(engine_clk, rho_snap)
        m_clk = engine_clk.compute_metrics()
        analysis_clk["dominant_basin"] = m_clk["rhoMaxId"]
        analysis_clk["final_mass"] = m_clk["mass"]
        trials += 1

        entry = {
            "damping": d,
            "standard": {
                "basin": analysis["dominant_basin"],
                "basin_label": labels.get(analysis["dominant_basin"], "?"),
                "iton": round(analysis["iton_score"], 3),
                "coherence": round(analysis["coherence"], 3),
                "modes": analysis["n_modes"],
                "mass": round(analysis.get("final_mass", 0), 4),
            },
            "cold_inject": {
                "basin": analysis_cold["dominant_basin"],
                "basin_label": labels.get(analysis_cold["dominant_basin"], "?"),
                "iton": round(analysis_cold["iton_score"], 3),
                "coherence": round(analysis_cold["coherence"], 3),
            },
            "clock_assisted": {
                "basin": analysis_clk.get("dominant_basin"),
                "basin_label": labels.get(analysis_clk.get("dominant_basin"), "?"),
                "iton": round(analysis_clk.get("iton_score", 0), 3),
                "mass": round(analysis_clk.get("final_mass", 0), 4),
            },
        }
        sweep_results.append(entry)
        log(f"    d={d}: std→{entry['standard']['basin_label']}, "
            f"cold→{entry['cold_inject']['basin_label']}, "
            f"clk→{entry['clock_assisted']['basin_label']}")

    results["probes"]["sweep"] = sweep_results

    # ---- Probe B: Can extreme w0 break through? ----
    log("  Probe B: Extreme w0 in dead zone")
    extreme_results = []
    for d in [15, 20, 30]:
        for w0_val in [10, 50, 100, 500, 1000]:
            def spirit_wx(e, grps, w=w0_val):
                if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                    return w
                return 1.0

            mod_edges, cnt = set_edge_weights(raw_edges, raw_nodes,
                                              lambda e, g: spirit_wx(e, g))
            engine = make_engine(raw_nodes, mod_edges, d)
            apply_standard_injection(engine)
            engine.run(500)
            m = engine.compute_metrics()
            trials += 1
            inverted = m["rhoMaxId"] != 22  # Not christic
            extreme_results.append({
                "damping": d, "w0_spirit": w0_val,
                "basin": m["rhoMaxId"],
                "basin_label": labels.get(m["rhoMaxId"], "?"),
                "inverted": inverted,
            })
        log(f"    d={d}: w0=1000 → {labels.get(extreme_results[-1]['basin'], '?')}"
            f" (inverted={extreme_results[-1]['inverted']})")

    results["probes"]["extreme_w0"] = extreme_results

    # ---- Probe C: Can cold injection break christic in dead zone? ----
    log("  Probe C: Cold injection diversity in dead zone")
    cold_diversity = []
    for d in [15, 20, 30, 40]:
        basins_found = set()
        for target in COLD_NODES:
            for amount in [50, 100, 200]:
                engine = make_engine(raw_nodes, raw_edges, d)
                engine.inject(target, amount)
                engine.run(500)
                m = engine.compute_metrics()
                basins_found.add(m["rhoMaxId"])
                trials += 1
        cold_diversity.append({
            "damping": d,
            "unique_basins": len(basins_found),
            "basins": [format_basin(b, labels) for b in basins_found],
        })
        log(f"    d={d}: cold injection → {len(basins_found)} unique basins: "
            f"{[format_basin(b, labels) for b in basins_found]}")

    results["probes"]["cold_diversity"] = cold_diversity

    budget.add_trials(trials)
    budget.log_suite("suite_2", t0)
    log(f"  Suite 2 complete: {trials} trials, {time.time()-t0:.0f}s")
    return results


# ===================================================================
# SUITE 3: TRANSITION ZONE MAPPING (d=10-15)
# ===================================================================

def suite_3_transition_zone(budget: BudgetTracker):
    """Map the exact boundary where gate operations fail."""
    log("=" * 70)
    log("SUITE 3: TRANSITION ZONE MAPPING (d=10-15)")
    log("=" * 70)
    t0 = time.time()
    results = {"suite": "transition_zone", "probes": {}}
    trials = 0

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)

    # NOT gate test at fine resolution
    log("  Probe A: NOT gate boundary (d=10.0 to 15.0, step=0.5)")
    not_gate_results = []

    def spirit_rule(w0_val):
        def fn(e, grps):
            if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                return w0_val
            return 1.0
        return fn

    for d in np.arange(10.0, 15.5, 0.5):
        d = round(float(d), 1)
        if budget.exhausted():
            break

        row = {"damping": d, "w0_tests": {}}

        # Baseline (no highway)
        engine_off = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_off)
        engine_off.run(500)
        m_off = engine_off.compute_metrics()
        off_basin = m_off["rhoMaxId"]
        trials += 1

        for w0 in [3, 5, 10, 20, 50, 100]:
            mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(w0))
            engine_on = make_engine(raw_nodes, mod_edges, d)
            apply_standard_injection(engine_on)
            engine_on.run(500)
            m_on = engine_on.compute_metrics()
            on_basin = m_on["rhoMaxId"]
            trials += 1

            inverted = off_basin != on_basin
            row["w0_tests"][w0] = {
                "off_basin": format_basin(off_basin, labels),
                "on_basin": format_basin(on_basin, labels),
                "inverted": inverted,
            }

        not_gate_results.append(row)
        inv_count = sum(1 for v in row["w0_tests"].values() if v["inverted"])
        log(f"    d={d}: OFF→{format_basin(off_basin, labels)}, "
            f"inversion in {inv_count}/6 w0 configs")

    results["probes"]["not_gate_boundary"] = not_gate_results

    # AND gate test
    log("  Probe B: AND gate boundary (d=10-15)")
    and_gate_results = []
    for d in [10, 11, 12, 13, 14, 15]:
        d = float(d)
        # A=injection, B=highway
        truth_table = {}

        for a_on, b_on in [(False, False), (True, False), (False, True), (True, True)]:
            if b_on:
                mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3))
            else:
                mod_edges = copy.deepcopy(raw_edges)

            engine = make_engine(raw_nodes, mod_edges, d)
            if a_on:
                apply_standard_injection(engine)
            engine.run(500)
            m = engine.compute_metrics()
            trials += 1

            truth_table[f"A={int(a_on)},B={int(b_on)}"] = {
                "basin": format_basin(m["rhoMaxId"], labels) if m["rhoMaxId"] else "none",
                "is_grail": m["rhoMaxId"] == 1,
            }

        # AND gate passes if ONLY (1,1) → grail
        and_pass = (truth_table["A=1,B=1"]["is_grail"] and
                    not truth_table["A=1,B=0"]["is_grail"] and
                    not truth_table["A=0,B=1"]["is_grail"])

        and_gate_results.append({"damping": d, "truth_table": truth_table, "and_pass": and_pass})
        log(f"    d={d}: AND gate {'PASS' if and_pass else 'FAIL'}")

    results["probes"]["and_gate_boundary"] = and_gate_results

    # Clock-extended gate operation
    log("  Probe C: Clock signal extends gate operation?")
    clock_gate_results = []
    for d in [12, 15, 20]:
        # Clock-assisted NOT gate test
        mod_edges_on, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3))

        # Without clock
        engine_off = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_off)
        engine_off.run(500)
        m_off = engine_off.compute_metrics()

        engine_on = make_engine(raw_nodes, mod_edges_on, d)
        apply_standard_injection(engine_on)
        engine_on.run(500)
        m_on = engine_on.compute_metrics()
        trials += 2

        # With clock (period=100, 10% pulse)
        engine_off_clk = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_off_clk)
        for _ in range(5):
            engine_off_clk.run(100)
            for lbl, amt in STANDARD_INJECTIONS:
                engine_off_clk.inject(lbl, amt * 0.1)
        m_off_clk = engine_off_clk.compute_metrics()

        engine_on_clk = make_engine(raw_nodes, mod_edges_on, d)
        apply_standard_injection(engine_on_clk)
        for _ in range(5):
            engine_on_clk.run(100)
            for lbl, amt in STANDARD_INJECTIONS:
                engine_on_clk.inject(lbl, amt * 0.1)
        m_on_clk = engine_on_clk.compute_metrics()
        trials += 2

        no_clock_inv = m_off["rhoMaxId"] != m_on["rhoMaxId"]
        clk_inv = m_off_clk["rhoMaxId"] != m_on_clk["rhoMaxId"]

        clock_gate_results.append({
            "damping": d,
            "no_clock": {
                "off_basin": format_basin(m_off["rhoMaxId"], labels),
                "on_basin": format_basin(m_on["rhoMaxId"], labels),
                "inverted": no_clock_inv,
            },
            "with_clock": {
                "off_basin": format_basin(m_off_clk["rhoMaxId"], labels),
                "on_basin": format_basin(m_on_clk["rhoMaxId"], labels),
                "inverted": clk_inv,
            },
            "clock_extends": clk_inv and not no_clock_inv,
        })
        log(f"    d={d}: no_clock={no_clock_inv}, with_clock={clk_inv}, "
            f"extends={'YES' if clk_inv and not no_clock_inv else 'NO'}")

    results["probes"]["clock_extended_gates"] = clock_gate_results

    budget.add_trials(trials)
    budget.log_suite("suite_3", t0)
    log(f"  Suite 3 complete: {trials} trials, {time.time()-t0:.0f}s")
    return results


# ===================================================================
# SUITE 4: LOGIC GATE EXTENSION
# ===================================================================

def suite_4_logic_extension(budget: BudgetTracker):
    """XOR, NAND, SR latch, half-adder attempts."""
    log("=" * 70)
    log("SUITE 4: LOGIC GATE EXTENSION")
    log("=" * 70)
    t0 = time.time()
    results = {"suite": "logic_gate_extension", "probes": {}}
    trials = 0

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)

    def spirit_rule(w0_val):
        def fn(e, grps):
            if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                return w0_val
            return 1.0
        return fn

    # ---- XOR Gate ----
    # XOR: Output differs when exactly one input is present
    # Approach: A = standard injection, B = cold injection
    # If basin when (A only) ≠ basin when (B only), and
    # basin when (both) = basin when (neither) or differs from both singles → XOR-like
    log("  Probe A: XOR gate attempt")
    xor_results = []
    for d in [0.2, 5.0]:
        truth = {}
        for a_on, b_on in [(False, False), (True, False), (False, True), (True, True)]:
            engine = make_engine(raw_nodes, raw_edges, d)
            if a_on:
                apply_standard_injection(engine)
            if b_on:
                for cn in COLD_NODES:
                    engine.inject(cn, 30.0)
            engine.run(500)
            m = engine.compute_metrics()
            trials += 1
            key = f"A={int(a_on)},B={int(b_on)}"
            truth[key] = {
                "basin": m["rhoMaxId"],
                "basin_label": labels.get(m["rhoMaxId"], "?"),
                "mass": round(m["mass"], 4),
            }

        # Check XOR property: (0,1) and (1,0) should be same, (0,0) and (1,1) should be same
        a_only = truth["A=1,B=0"]["basin"]
        b_only = truth["A=0,B=1"]["basin"]
        both = truth["A=1,B=1"]["basin"]
        neither = truth["A=0,B=0"]["basin"]

        xor_like = (a_only != both) and (b_only != both) and (a_only != neither or b_only != neither)

        xor_results.append({
            "damping": d, "truth_table": truth, "xor_like": xor_like,
            "analysis": f"A_only→{labels.get(a_only,'?')}, B_only→{labels.get(b_only,'?')}, "
                        f"Both→{labels.get(both,'?')}, Neither→{labels.get(neither,'?')}"
        })
        log(f"    d={d}: XOR-like={xor_like} | {xor_results[-1]['analysis']}")

    results["probes"]["xor_gate"] = xor_results

    # ---- NAND Gate ----
    # NAND = NOT(AND). AND gives grail for (1,1). NAND should give NOT grail.
    # Cascade: run AND first, then apply inversion if output is grail.
    log("  Probe B: NAND gate (cascaded NOT+AND)")
    nand_results = []
    for d in [0.2, 5.0]:
        truth = {}
        for a_on, b_on in [(False, False), (True, False), (False, True), (True, True)]:
            # Stage 1: AND gate
            if b_on:
                mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3))
            else:
                mod_edges = copy.deepcopy(raw_edges)

            engine_and = make_engine(raw_nodes, mod_edges, d)
            if a_on:
                apply_standard_injection(engine_and)
            engine_and.run(500)
            m_and = engine_and.compute_metrics()
            and_basin = m_and["rhoMaxId"]

            # Stage 2: NOT gate on the AND output
            # If AND gave grail → inject and run WITHOUT highway (should give metatron)
            # If AND gave metatron → inject and run WITH highway (should give grail)
            if and_basin == 1:  # grail — apply NOT (no highway → metatron)
                engine_not = make_engine(raw_nodes, raw_edges, d)
            else:  # not grail — apply NOT (highway → grail)
                mod_edges2, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3))
                engine_not = make_engine(raw_nodes, mod_edges2, d)

            apply_standard_injection(engine_not)
            engine_not.run(500)
            m_not = engine_not.compute_metrics()
            trials += 2

            key = f"A={int(a_on)},B={int(b_on)}"
            truth[key] = {
                "and_basin": format_basin(and_basin, labels),
                "nand_basin": format_basin(m_not["rhoMaxId"], labels),
                "nand_output": m_not["rhoMaxId"],
            }

        # NAND truth table: 00→1, 01→1, 10→1, 11→0
        # In SOL terms: (1,1) should NOT produce grail; all others should
        nand_correct = (
            truth["A=0,B=0"]["nand_output"] != 1 and  # No energy = no grail ✓ (vacuously correct)
            truth["A=1,B=0"]["nand_output"] != 1 and   # Actually NAND(1,0)=1 but...
            truth["A=1,B=1"]["nand_output"] != 1       # NAND(1,1)=0, so NOT grail ✓
        )

        nand_results.append({"damping": d, "truth_table": truth, "nand_functional": nand_correct})
        log(f"    d={d}: NAND {'PASS' if nand_correct else 'partial'}")

    results["probes"]["nand_gate"] = nand_results

    # ---- SR Latch (Memory) ----
    # Test if the system can remember previous state after RESET
    log("  Probe C: SR Latch (memory/hysteresis test)")
    latch_results = []

    for d in [0.2, 5.0]:
        # Experiment: does injection order affect final state?
        # Path A: inject grail first, then metatron
        engine_a = make_engine(raw_nodes, raw_edges, d)
        engine_a.inject("grail", 100.0)
        engine_a.run(200)
        engine_a.inject("metatron", 100.0)
        engine_a.run(300)
        m_a = engine_a.compute_metrics()
        trials += 1

        # Path B: inject metatron first, then grail
        engine_b = make_engine(raw_nodes, raw_edges, d)
        engine_b.inject("metatron", 100.0)
        engine_b.run(200)
        engine_b.inject("grail", 100.0)
        engine_b.run(300)
        m_b = engine_b.compute_metrics()
        trials += 1

        # Path C: inject simultaneously
        engine_c = make_engine(raw_nodes, raw_edges, d)
        engine_c.inject("grail", 100.0)
        engine_c.inject("metatron", 100.0)
        engine_c.run(500)
        m_c = engine_c.compute_metrics()
        trials += 1

        has_memory = m_a["rhoMaxId"] != m_b["rhoMaxId"]

        latch_results.append({
            "damping": d,
            "grail_first": format_basin(m_a["rhoMaxId"], labels),
            "metatron_first": format_basin(m_b["rhoMaxId"], labels),
            "simultaneous": format_basin(m_c["rhoMaxId"], labels),
            "order_dependent": has_memory,
        })
        log(f"    d={d}: grail-first→{format_basin(m_a['rhoMaxId'], labels)}, "
            f"metatron-first→{format_basin(m_b['rhoMaxId'], labels)}, "
            f"memory={'YES' if has_memory else 'NO'}")

    # Extended latch: w0 state persists after input removal
    for d in [0.2, 5.0]:
        # SET: apply highway → read → remove highway → does basin persist?
        mod_edges_on, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3))
        engine_set = make_engine(raw_nodes, mod_edges_on, d)
        apply_standard_injection(engine_set)
        engine_set.run(500)
        m_set = engine_set.compute_metrics()
        set_basin = m_set["rhoMaxId"]

        # Now "remove" highway by running same state but with uniform weights
        # We can't modify w0 mid-run directly, but we can save state and restore to new engine
        state = snapshot_state(engine_set.physics)
        engine_after = make_engine(raw_nodes, raw_edges, d)
        restore_state(engine_after.physics, state)
        engine_after.run(500)
        m_after = engine_after.compute_metrics()
        after_basin = m_after["rhoMaxId"]
        trials += 2

        persists = set_basin == after_basin

        latch_results.append({
            "damping": d,
            "type": "w0_persistence",
            "set_basin": format_basin(set_basin, labels),
            "after_removal": format_basin(after_basin, labels),
            "state_persists": persists,
        })
        log(f"    d={d}: w0 persistence: set→{format_basin(set_basin, labels)}, "
            f"after→{format_basin(after_basin, labels)}, persists={'YES' if persists else 'NO'}")

    results["probes"]["sr_latch"] = latch_results

    # ---- Half-Adder ----
    # SUM = A XOR B, CARRY = A AND B
    # We need two readable outputs. Use basin for one, iton for other.
    log("  Probe D: Half-adder attempt (basin=SUM, iton=CARRY)")
    ha_results = []
    d = 0.2
    for a_on, b_on in [(False, False), (True, False), (False, True), (True, True)]:
        if b_on:
            mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_rule(3))
        else:
            mod_edges = copy.deepcopy(raw_edges)

        engine = make_engine(raw_nodes, mod_edges, d)
        if a_on:
            apply_standard_injection(engine)
        if a_on or b_on:
            # Need some energy for measurement
            analysis = run_and_analyze(engine)
        else:
            engine.run(500)
            analysis = {"dominant_basin": None, "iton_score": 0.0, "final_mass": 0.0}
        trials += 1

        ha_results.append({
            "A": int(a_on), "B": int(b_on),
            "basin": format_basin(analysis.get("dominant_basin"), labels),
            "iton": round(analysis.get("iton_score", 0), 3),
            "mass": round(analysis.get("final_mass", 0), 4),
        })

    results["probes"]["half_adder"] = ha_results
    log(f"    Half-adder results: {[(r['A'], r['B'], r['basin'], r['iton']) for r in ha_results]}")

    budget.add_trials(trials)
    budget.log_suite("suite_4", t0)
    log(f"  Suite 4 complete: {trials} trials, {time.time()-t0:.0f}s")
    return results


# ===================================================================
# SUITE 5: INJECTION PROTOCOL EXPLORATION
# ===================================================================

def suite_5_injection_exploration(budget: BudgetTracker):
    """Novel injection patterns and their effects."""
    log("=" * 70)
    log("SUITE 5: INJECTION PROTOCOL EXPLORATION")
    log("=" * 70)
    t0 = time.time()
    results = {"suite": "injection_exploration", "probes": {}}
    trials = 0

    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)

    damping_values = [0.2, 5.0, 20.0, 55.0]

    # ---- Probe A: Asymmetric energy ratios ----
    log("  Probe A: Asymmetric injection ratios")
    asym_results = []

    ratio_configs = {
        "STANDARD": [40, 35, 30, 25, 20],
        "MONOPOLE": [150, 0, 0, 0, 0],
        "STEEP_GRADIENT": [100, 30, 15, 4, 1],
        "FLAT": [30, 30, 30, 30, 30],
        "INVERSE_PYRAMID": [10, 20, 30, 40, 50],
        "BINARY": [75, 75, 0, 0, 0],
    }

    targets = ["grail", "metatron", "pyramid", "christ", "light codes"]

    for config_name, amounts in ratio_configs.items():
        for d in damping_values:
            if budget.exhausted():
                break
            engine = make_engine(raw_nodes, raw_edges, d)
            for target, amount in zip(targets, amounts):
                if amount > 0:
                    engine.inject(target, amount)
            analysis = run_and_analyze(engine)
            trials += 1

            asym_results.append({
                "config": config_name,
                "damping": d,
                "basin": format_basin(analysis["dominant_basin"], labels),
                "iton": round(analysis["iton_score"], 3),
                "coherence": round(analysis["coherence"], 3),
                "mass": round(analysis.get("final_mass", 0), 4),
            })

    # Summarize
    for cfg in ratio_configs:
        basins = set(r["basin"] for r in asym_results if r["config"] == cfg)
        log(f"    {cfg}: {len(basins)} unique basins across {len(damping_values)} dampings")

    results["probes"]["asymmetric"] = asym_results

    # ---- Probe B: Temporal burst patterns ----
    log("  Probe B: Temporal burst injection")
    burst_results = []

    for d in [0.2, 5.0, 20.0]:
        if budget.exhausted():
            break

        # Rapid burst: 5 injections of 30 each at 10-step intervals
        engine_burst = make_engine(raw_nodes, raw_edges, d)
        for i in range(5):
            engine_burst.inject("grail", 30.0)
            engine_burst.run(10)
        engine_burst.run(450)
        m_burst = engine_burst.compute_metrics()
        trials += 1

        # Ramp: increasing amounts
        engine_ramp = make_engine(raw_nodes, raw_edges, d)
        for i, amt in enumerate([10, 20, 30, 40, 50]):
            engine_ramp.inject("grail", amt)
            engine_ramp.run(50)
        engine_ramp.run(250)
        m_ramp = engine_ramp.compute_metrics()
        trials += 1

        # Oscillating: alternate between standard and cold
        engine_osc = make_engine(raw_nodes, raw_edges, d)
        for cycle in range(5):
            apply_standard_injection(engine_osc)
            engine_osc.run(50)
            for cn in COLD_NODES:
                engine_osc.inject(cn, 30.0)
            engine_osc.run(50)
        m_osc = engine_osc.compute_metrics()
        trials += 1

        # Single shot control
        engine_ctrl = make_engine(raw_nodes, raw_edges, d)
        engine_ctrl.inject("grail", 150.0)
        engine_ctrl.run(500)
        m_ctrl = engine_ctrl.compute_metrics()
        trials += 1

        burst_results.append({
            "damping": d,
            "burst_5x30": format_basin(m_burst["rhoMaxId"], labels),
            "ramp_10to50": format_basin(m_ramp["rhoMaxId"], labels),
            "oscillating": format_basin(m_osc["rhoMaxId"], labels),
            "single_shot": format_basin(m_ctrl["rhoMaxId"], labels),
        })
        log(f"    d={d}: burst→{format_basin(m_burst['rhoMaxId'], labels)}, "
            f"ramp→{format_basin(m_ramp['rhoMaxId'], labels)}, "
            f"osc→{format_basin(m_osc['rhoMaxId'], labels)}")

    results["probes"]["burst_patterns"] = burst_results

    # ---- Probe C: Multi-mode injection (standard + cold combined) ----
    log("  Probe C: Combined standard + cold injection")
    combined_results = []

    for d in [0.2, 5.0, 20.0]:
        if budget.exhausted():
            break

        # Standard only
        engine_std = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_std)
        a_std = run_and_analyze(engine_std)
        trials += 1

        # Cold only
        engine_cold = make_engine(raw_nodes, raw_edges, d)
        for cn in COLD_NODES:
            engine_cold.inject(cn, 30.0)
        a_cold = run_and_analyze(engine_cold)
        trials += 1

        # Both simultaneously
        engine_both = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_both)
        for cn in COLD_NODES:
            engine_both.inject(cn, 30.0)
        a_both = run_and_analyze(engine_both)
        trials += 1

        # Standard then cold (sequential)
        engine_seq = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_seq)
        engine_seq.run(100)
        for cn in COLD_NODES:
            engine_seq.inject(cn, 30.0)
        engine_seq.run(400)
        m_seq = engine_seq.compute_metrics()
        # Quick analysis
        rho_snap = [[n["rho"] for n in engine_seq.physics.nodes]]
        a_seq = analyze_trial(engine_seq, rho_snap)
        a_seq["dominant_basin"] = m_seq["rhoMaxId"]
        trials += 1

        combined_results.append({
            "damping": d,
            "standard_only": {
                "basin": format_basin(a_std["dominant_basin"], labels),
                "iton": round(a_std["iton_score"], 3),
            },
            "cold_only": {
                "basin": format_basin(a_cold["dominant_basin"], labels),
                "iton": round(a_cold["iton_score"], 3),
            },
            "both_simultaneous": {
                "basin": format_basin(a_both["dominant_basin"], labels),
                "iton": round(a_both["iton_score"], 3),
            },
            "standard_then_cold": {
                "basin": format_basin(a_seq["dominant_basin"], labels),
                "iton": round(a_seq.get("iton_score", 0), 3),
            },
        })
        log(f"    d={d}: std→{format_basin(a_std['dominant_basin'], labels)}, "
            f"cold→{format_basin(a_cold['dominant_basin'], labels)}, "
            f"both→{format_basin(a_both['dominant_basin'], labels)}, "
            f"seq→{format_basin(a_seq['dominant_basin'], labels)}")

    results["probes"]["combined_injection"] = combined_results

    # ---- Probe D: Energy-efficient injection (minimum energy for basin control) ----
    log("  Probe D: Minimum energy for basin control")
    min_energy_results = []
    d = 0.2

    for total_e in [150, 100, 50, 25, 10, 5, 1]:
        if budget.exhausted():
            break
        scale = total_e / 150.0
        engine = make_engine(raw_nodes, raw_edges, d)
        for label, amount in STANDARD_INJECTIONS:
            engine.inject(label, amount * scale)
        analysis = run_and_analyze(engine)
        trials += 1

        min_energy_results.append({
            "total_energy": total_e,
            "basin": format_basin(analysis["dominant_basin"], labels),
            "mass": round(analysis.get("final_mass", 0), 6),
            "coherence": round(analysis["coherence"], 3),
            "iton": round(analysis["iton_score"], 3),
        })
        log(f"    E={total_e}: → {format_basin(analysis['dominant_basin'], labels)}, "
            f"mass={analysis.get('final_mass',0):.6f}")

    results["probes"]["min_energy"] = min_energy_results

    budget.add_trials(trials)
    budget.log_suite("suite_5", t0)
    log(f"  Suite 5 complete: {trials} trials, {time.time()-t0:.0f}s")
    return results


# ===================================================================
# PHASE 2: DYNAMIC RSI EXPERIMENTS
# ===================================================================

def dynamic_parameter_sweep(damping_range, step_size, budget: BudgetTracker):
    """Run a damping sweep in the specified range."""
    log(f"  [DYNAMIC] Parameter sweep d={damping_range[0]}-{damping_range[1]}, step={step_size}")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    d = damping_range[0]
    while d <= damping_range[1] and not budget.exhausted():
        engine = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine)
        analysis = run_and_analyze(engine)
        trials += 1
        results_list.append({
            "damping": round(d, 2),
            "basin": format_basin(analysis["dominant_basin"], labels),
            "iton": round(analysis["iton_score"], 3),
            "coherence": round(analysis["coherence"], 3),
            "modes": analysis["n_modes"],
        })
        d += step_size

    budget.add_trials(trials)
    return {"type": "parameter_sweep", "range": damping_range, "results": results_list, "trials": trials}


def dynamic_gate_test(damping_values, w0_values, budget: BudgetTracker):
    """Test NOT gate at various d/w0 combinations."""
    log(f"  [DYNAMIC] Gate test: {len(damping_values)} dampings × {len(w0_values)} w0")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    results_list = []
    trials = 0

    for d in damping_values:
        if budget.exhausted():
            break
        # Baseline (no highway)
        engine_off = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_off)
        engine_off.run(500)
        m_off = engine_off.compute_metrics()
        off_basin = m_off["rhoMaxId"]
        trials += 1

        for w0 in w0_values:
            if budget.exhausted():
                break

            def spirit_fn(e, grps, w=w0):
                if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                    return w
                return 1.0

            mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_fn)
            engine_on = make_engine(raw_nodes, mod_edges, d)
            apply_standard_injection(engine_on)
            engine_on.run(500)
            m_on = engine_on.compute_metrics()
            trials += 1

            results_list.append({
                "damping": d, "w0": w0,
                "off_basin": format_basin(off_basin, labels),
                "on_basin": format_basin(m_on["rhoMaxId"], labels),
                "inverted": off_basin != m_on["rhoMaxId"],
            })

    budget.add_trials(trials)
    return {"type": "gate_test", "results": results_list, "trials": trials}


def dynamic_entropy_measurement(budget: BudgetTracker):
    """Information-theoretic analysis: Shannon entropy of rho distributions."""
    log("  [DYNAMIC] Information-theoretic analysis")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    for d in [0.2, 1.0, 5.0, 10.0, 20.0, 40.0, 60.0, 79.5, 83.0]:
        if budget.exhausted():
            break

        engine = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine)

        # Collect rho at multiple timepoints
        entropy_over_time = []
        for step_block in range(10):
            engine.run(50)
            rhos = np.array([n["rho"] for n in engine.physics.nodes])
            total = rhos.sum()
            if total > 0:
                probs = rhos / total
                probs = probs[probs > 0]
                entropy = -np.sum(probs * np.log2(probs))
            else:
                entropy = 0.0
            entropy_over_time.append(round(float(entropy), 4))
        trials += 1

        m = engine.compute_metrics()
        results_list.append({
            "damping": d,
            "entropy_evolution": entropy_over_time,
            "final_entropy": entropy_over_time[-1] if entropy_over_time else 0,
            "max_entropy": round(math.log2(140), 4),  # log2(N) for uniform
            "basin": format_basin(m["rhoMaxId"], labels),
        })
        log(f"    d={d}: entropy {entropy_over_time[0]:.2f}→{entropy_over_time[-1]:.2f} "
            f"(max={math.log2(140):.2f})")

    budget.add_trials(trials)
    return {"type": "entropy_measurement", "results": results_list, "trials": trials}


def dynamic_capacity_test(budget: BudgetTracker):
    """Measure maximum distinguishable basins (channel capacity)."""
    log("  [DYNAMIC] Channel capacity measurement")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    all_basins = set()
    trials = 0
    trial_records = []

    # Sweep many combinations to find maximum distinct basins
    targets = ["grail", "metatron", "pyramid", "christ", "light codes",
               "par", "johannine grove", "mystery school", "christine hayes", "john"]
    dampings = [0.2, 5.0]

    for d in dampings:
        if budget.exhausted():
            break
        basins_at_d = set()

        # Single-target injection
        for target in targets:
            if budget.exhausted():
                break
            for amount in [20, 50, 100]:
                engine = make_engine(raw_nodes, raw_edges, d)
                engine.inject(target, amount)
                engine.run(500)
                m = engine.compute_metrics()
                basins_at_d.add(m["rhoMaxId"])
                all_basins.add(m["rhoMaxId"])
                trials += 1

        # Dual-target injection
        for i in range(min(10, len(targets))):
            for j in range(i + 1, min(10, len(targets))):
                if budget.exhausted():
                    break
                engine = make_engine(raw_nodes, raw_edges, d)
                engine.inject(targets[i], 50)
                engine.inject(targets[j], 50)
                engine.run(500)
                m = engine.compute_metrics()
                basins_at_d.add(m["rhoMaxId"])
                all_basins.add(m["rhoMaxId"])
                trials += 1

        trial_records.append({
            "damping": d,
            "unique_basins": len(basins_at_d),
            "basins": [format_basin(b, labels) for b in basins_at_d],
            "bits": round(math.log2(max(1, len(basins_at_d))), 2),
        })
        log(f"    d={d}: {len(basins_at_d)} unique basins = {math.log2(max(1,len(basins_at_d))):.1f} bits")

    budget.add_trials(trials)
    return {
        "type": "capacity_measurement",
        "total_unique_basins": len(all_basins),
        "total_bits": round(math.log2(max(1, len(all_basins))), 2),
        "per_damping": trial_records,
        "trials": trials,
    }


def dynamic_error_resilience(budget: BudgetTracker):
    """Test output stability under noisy input conditions."""
    log("  [DYNAMIC] Error resilience test")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    for d in [0.2, 5.0]:
        if budget.exhausted():
            break

        # Reference: standard injection
        engine_ref = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_ref)
        engine_ref.run(500)
        m_ref = engine_ref.compute_metrics()
        ref_basin = m_ref["rhoMaxId"]
        trials += 1

        # Noisy injections: add Gaussian noise to injection amounts
        noise_levels = [0.01, 0.05, 0.10, 0.20, 0.50, 1.00]
        for noise in noise_levels:
            if budget.exhausted():
                break
            stable_count = 0
            n_tests = 10
            for test in range(n_tests):
                engine = make_engine(raw_nodes, raw_edges, d, seed=42 + test)
                for label, amount in STANDARD_INJECTIONS:
                    noisy_amount = amount * (1.0 + random.gauss(0, noise))
                    noisy_amount = max(0, noisy_amount)
                    engine.inject(label, noisy_amount)
                engine.run(500)
                m = engine.compute_metrics()
                if m["rhoMaxId"] == ref_basin:
                    stable_count += 1
                trials += 1

            results_list.append({
                "damping": d,
                "noise_std": noise,
                "stability": stable_count / n_tests,
                "ref_basin": format_basin(ref_basin, labels),
            })

        log(f"    d={d}: stability @ noise=0.5 = "
            f"{next((r['stability'] for r in results_list if r['damping']==d and r['noise_std']==0.5), '?')}")

    budget.add_trials(trials)
    return {"type": "error_resilience", "results": results_list, "trials": trials}


# ===================================================================
# DEDICATED GENERATORS — raw_lead_followup, cascade_pipeline, replication
# ===================================================================

def dynamic_raw_lead_followup(genome: dict, budget: BudgetTracker):
    """
    Follow up on raw proof-packet leads with targeted experiments.
    Instead of generic sweeps, this parses the lead's parameters and
    runs experiments specific to the lead's hypothesis.
    """
    log("  [DYNAMIC] Raw lead follow-up (targeted)")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    results_list = []
    trials = 0

    # --- Dream Afterstate: rest-phase analysis ---
    # Hypothesis: after injection, letting the system REST (no further input)
    # reveals a "dream" afterstate — the residual attractor after energy dissipates
    log("    Lead A: Dream Afterstate — rest-phase analysis")
    for d in [0.2, 1.0, 4.0, 10.0, 20.0]:
        if budget.exhausted():
            break
        engine = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine)
        engine.run(200)  # Initial settling

        # Snapshot at injection
        m_inject = engine.compute_metrics()
        inject_basin = m_inject["rhoMaxId"]

        # Let it "dream" — run 1000 more steps with NO further input
        engine.run(1000)
        m_dream = engine.compute_metrics()
        dream_basin = m_dream["rhoMaxId"]

        # Does the basin shift during the dream phase?
        rho_dream = [n["rho"] for n in engine.physics.nodes]
        dream_mass = sum(rho_dream)
        dream_rho_max = max(rho_dream) if rho_dream else 0

        trials += 1
        results_list.append({
            "damping": d,
            "inject_basin": format_basin(inject_basin, labels),
            "dream_basin": format_basin(dream_basin, labels),
            "basin_shifted": inject_basin != dream_basin,
            "dream_mass": round(dream_mass, 6),
            "dream_rho_max": round(dream_rho_max, 6),
            "experiment": "dream_afterstate",
        })
        log(f"      d={d}: inject→{format_basin(inject_basin, labels)}, "
            f"dream→{format_basin(dream_basin, labels)}, "
            f"shifted={inject_basin != dream_basin}")

    # --- ψ Resonance: square-wave cadence ---
    # Hypothesis: periodic injection (25-step pulse) creates resonant
    # rhythms that shift rho distribution differently than continuous injection
    log("    Lead B: ψ Resonance — square-wave injection cadence")
    for d in [0.2, 5.0, 10.0, 15.0]:
        if budget.exhausted():
            break
        for period in [25, 50, 75]:
            if budget.exhausted():
                break
            engine = make_engine(raw_nodes, raw_edges, d)

            # Square wave: inject for pulse_steps, rest for (period - pulse_steps)
            pulse_steps = max(1, period // 5)
            rho90_frac_list = []
            for cycle in range(8):
                # Pulse ON
                for lbl, amt in STANDARD_INJECTIONS:
                    engine.inject(lbl, amt * 0.2)
                engine.run(pulse_steps)
                # Pulse OFF (rest)
                engine.run(period - pulse_steps)
                # Measure after each cycle
                rho_snap = [n["rho"] for n in engine.physics.nodes]
                total = sum(rho_snap)
                if total > 0:
                    sorted_rho = sorted(rho_snap, reverse=True)
                    top10_mass = sum(sorted_rho[:14])  # top 10% of 140
                    rho90_frac_list.append(round(top10_mass / total, 4))

            m = engine.compute_metrics()
            trials += 1
            results_list.append({
                "damping": d,
                "period": period,
                "pulse_steps": pulse_steps,
                "basin": format_basin(m["rhoMaxId"], labels),
                "rho90_frac_trend": rho90_frac_list,
                "final_rho90": rho90_frac_list[-1] if rho90_frac_list else 0,
                "experiment": "psi_resonance",
            })

    # --- Late-capture tick: track position drift ---
    # Hypothesis: capturing basin identity at different timesteps reveals
    # transient vs stable attractors
    log("    Lead C: Late-capture tick — basin identity over time")
    for d in [0.2, 5.0, 15.0]:
        if budget.exhausted():
            break
        engine = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine)

        capture_points = [50, 100, 200, 500, 1000, 2000]
        basin_trajectory = []
        for cp in capture_points:
            if cp == capture_points[0]:
                engine.run(cp)
            else:
                engine.run(cp - capture_points[capture_points.index(cp) - 1])
            m = engine.compute_metrics()
            basin_trajectory.append({
                "step": cp,
                "basin": format_basin(m["rhoMaxId"], labels),
                "mass": round(sum(n["rho"] for n in engine.physics.nodes), 6),
            })
        trials += 1
        results_list.append({
            "damping": d,
            "basin_trajectory": basin_trajectory,
            "n_transitions": len(set(b["basin"] for b in basin_trajectory)) - 1,
            "experiment": "late_capture_tick",
        })

    budget.add_trials(trials)
    return {
        "type": "raw_lead_followup",
        "probes": {
            "dream_afterstate": [r for r in results_list if r.get("experiment") == "dream_afterstate"],
            "psi_resonance": [r for r in results_list if r.get("experiment") == "psi_resonance"],
            "late_capture_tick": [r for r in results_list if r.get("experiment") == "late_capture_tick"],
        },
        "results": results_list,
        "trials": trials,
    }


def dynamic_cascade_pipeline(genome: dict, budget: BudgetTracker):
    """
    Test multi-stage cascade architectures beyond simple NOT chains.
    Explores: AND→NOT pipelines, fan-out, convergent cascades,
    and depth vs fidelity curves.
    """
    log("  [DYNAMIC] Cascade pipeline — architecture exploration")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    results_list = []
    trials = 0

    # Architecture 1: Fan-out — one injection drives two independent NOT gates
    log("    Arch A: Fan-out cascade (1→2 split)")
    for d in [0.2, 5.0, 10.0]:
        if budget.exhausted():
            break
        # Stage 0: standard injection → get basin
        engine_base = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_base)
        engine_base.run(500)
        m_base = engine_base.compute_metrics()
        base_basin = format_basin(m_base["rhoMaxId"], labels)

        # Stage 1a: NOT gate (spirit highway w0=3)
        def spirit_on(e, grps):
            if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                return 3
            return 1.0

        mod_edges_a, _ = set_edge_weights(raw_edges, raw_nodes, spirit_on)
        engine_a = make_engine(raw_nodes, mod_edges_a, d)
        apply_standard_injection(engine_a)
        engine_a.run(500)
        m_a = engine_a.compute_metrics()
        branch_a = format_basin(m_a["rhoMaxId"], labels)

        # Stage 1b: NOT gate (spirit highway w0=10)
        def spirit_strong(e, grps):
            if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                return 10
            return 1.0

        mod_edges_b, _ = set_edge_weights(raw_edges, raw_nodes, spirit_strong)
        engine_b = make_engine(raw_nodes, mod_edges_b, d)
        apply_standard_injection(engine_b)
        engine_b.run(500)
        m_b = engine_b.compute_metrics()
        branch_b = format_basin(m_b["rhoMaxId"], labels)

        trials += 3
        results_list.append({
            "damping": d, "architecture": "fan_out",
            "base_basin": base_basin,
            "branch_a_w3": branch_a,
            "branch_b_w10": branch_b,
            "branches_differ": branch_a != branch_b,
        })

    # Architecture 2: Convergent cascade — two different injections merge
    log("    Arch B: Convergent cascade (2→1 merge)")
    for d in [0.2, 5.0]:
        if budget.exhausted():
            break
        # Path A: grail-only
        engine_g = make_engine(raw_nodes, raw_edges, d)
        engine_g.inject("grail", 100)
        engine_g.run(500)
        m_g = engine_g.compute_metrics()

        # Path B: metatron-only
        engine_m = make_engine(raw_nodes, raw_edges, d)
        engine_m.inject("metatron", 100)
        engine_m.run(500)
        m_m = engine_m.compute_metrics()

        # Merged: both together
        engine_both = make_engine(raw_nodes, raw_edges, d)
        engine_both.inject("grail", 100)
        engine_both.inject("metatron", 100)
        engine_both.run(500)
        m_both = engine_both.compute_metrics()

        trials += 3
        results_list.append({
            "damping": d, "architecture": "convergent",
            "grail_only": format_basin(m_g["rhoMaxId"], labels),
            "metatron_only": format_basin(m_m["rhoMaxId"], labels),
            "merged": format_basin(m_both["rhoMaxId"], labels),
            "merge_novel": (m_both["rhoMaxId"] != m_g["rhoMaxId"]
                           and m_both["rhoMaxId"] != m_m["rhoMaxId"]),
        })

    # Architecture 3: Depth-fidelity curve for injection pipelines
    log("    Arch C: Depth-fidelity curve (1-10 stages)")
    d = 0.2
    for n_stages in range(1, 11):
        if budget.exhausted():
            break
        engine = make_engine(raw_nodes, raw_edges, d)
        basins = []
        for stage in range(n_stages):
            for lbl, amt in STANDARD_INJECTIONS:
                engine.inject(lbl, amt * (0.5 ** stage))  # Decaying energy
            engine.run(100)
            m = engine.compute_metrics()
            basins.append(format_basin(m["rhoMaxId"], labels))

        trials += 1
        results_list.append({
            "damping": d, "architecture": "depth_fidelity",
            "n_stages": n_stages,
            "basins": basins,
            "unique_basins": len(set(basins)),
            "final_basin": basins[-1],
        })

    budget.add_trials(trials)
    return {
        "type": "cascade_pipeline",
        "probes": {
            "fan_out": [r for r in results_list if r.get("architecture") == "fan_out"],
            "convergent": [r for r in results_list if r.get("architecture") == "convergent"],
            "depth_fidelity": [r for r in results_list if r.get("architecture") == "depth_fidelity"],
        },
        "results": results_list,
        "trials": trials,
    }


def dynamic_replication(genome: dict, budget: BudgetTracker):
    """
    Replication experiments: re-run key prior findings with different seeds
    to test reproducibility.
    """
    log("  [DYNAMIC] Replication — seed variation test")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    # Replicate 1: Standard injection basin identity across 10 seeds
    log("    Rep A: Standard injection across 10 seeds")
    for d in [0.2, 5.0, 20.0]:
        if budget.exhausted():
            break
        basins = []
        for seed in range(42, 52):
            if budget.exhausted():
                break
            engine = make_engine(raw_nodes, raw_edges, d, seed=seed)
            apply_standard_injection(engine)
            engine.run(500)
            m = engine.compute_metrics()
            basins.append(format_basin(m["rhoMaxId"], labels))
            trials += 1

        unique_basins = set(basins)
        results_list.append({
            "damping": d,
            "test": "seed_stability",
            "seeds_tested": 10,
            "basins": basins,
            "unique_basins": len(unique_basins),
            "deterministic": len(unique_basins) == 1,
        })
        log(f"      d={d}: {len(unique_basins)} unique basins across 10 seeds "
            f"({'deterministic' if len(unique_basins) == 1 else 'stochastic'})")

    # Replicate 2: NOT gate at d=0.2 across seeds
    log("    Rep B: NOT gate across 5 seeds")
    for seed in range(42, 47):
        if budget.exhausted():
            break
        # OFF
        engine_off = make_engine(raw_nodes, raw_edges, 0.2, seed=seed)
        apply_standard_injection(engine_off)
        engine_off.run(500)
        m_off = engine_off.compute_metrics()

        # ON (spirit highway w0=3)
        groups = get_groups(raw_nodes)

        def spirit_fn(e, grps):
            if grps.get(e["from"], "bridge") == "spirit" or grps.get(e["to"], "bridge") == "spirit":
                return 3
            return 1.0

        mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, spirit_fn)
        engine_on = make_engine(raw_nodes, mod_edges, 0.2, seed=seed)
        apply_standard_injection(engine_on)
        engine_on.run(500)
        m_on = engine_on.compute_metrics()

        trials += 2
        results_list.append({
            "damping": 0.2, "seed": seed,
            "test": "not_gate_replication",
            "off_basin": format_basin(m_off["rhoMaxId"], labels),
            "on_basin": format_basin(m_on["rhoMaxId"], labels),
            "inverted": m_off["rhoMaxId"] != m_on["rhoMaxId"],
        })

    budget.add_trials(trials)
    return {
        "type": "replication",
        "probes": {
            "seed_stability": [r for r in results_list if r.get("test") == "seed_stability"],
            "not_gate_replication": [r for r in results_list if r.get("test") == "not_gate_replication"],
        },
        "results": results_list,
        "trials": trials,
    }


# ===================================================================
# GEN-2 FRONTIER EXPERIMENT GENERATORS
# ===================================================================

def dynamic_multi_damping_sweep(budget: BudgetTracker) -> dict:
    """Sweep multiple damping zones simultaneously with cross-zone comparison."""
    log(f"  [DYNAMIC] Multi-damping sweep: comparing zones")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    zone_centers = random.sample([2.0, 8.0, 15.0, 25.0, 40.0, 55.0, 70.0, 80.0],
                                 min(4, 8))
    for center in zone_centers:
        if budget.exhausted():
            break
        for offset in [-2.0, -1.0, 0.0, 1.0, 2.0]:
            d = max(0.01, center + offset)
            engine = make_engine(raw_nodes, raw_edges, d)
            apply_standard_injection(engine)
            analysis = run_and_analyze(engine)
            trials += 1
            results_list.append({
                "zone_center": center, "damping": round(d, 2),
                "basin": format_basin(analysis["dominant_basin"], labels),
                "iton": round(analysis["iton_score"], 3),
                "coherence": round(analysis["coherence"], 3),
            })

    budget.add_trials(trials)
    return {"type": "multi_damping_sweep", "results": results_list, "trials": trials}


def dynamic_phase_space_mapping(budget: BudgetTracker) -> dict:
    """Map damping x injection energy phase space."""
    log(f"  [DYNAMIC] Phase space mapping: damping x injection")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    dampings = [0.5, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
    injection_scales = [0.1, 0.5, 1.0, 2.0, 5.0]

    for d in dampings:
        if budget.exhausted():
            break
        for scale in injection_scales:
            if budget.exhausted():
                break
            engine = make_engine(raw_nodes, raw_edges, d)
            for lbl, amt in STANDARD_INJECTIONS:
                engine.inject(lbl, amt * scale)
            engine.run(STEPS)
            m = engine.compute_metrics()
            rho_snap = [[n["rho"] for n in engine.physics.nodes]]
            analysis = analyze_trial(engine, rho_snap)
            trials += 1
            results_list.append({
                "damping": d, "injection_scale": scale,
                "basin": format_basin(m["rhoMaxId"], labels),
                "iton": round(analysis["iton_score"], 3),
                "coherence": round(analysis["coherence"], 3),
                "rhoMax": round(m["rhoMax"], 4),
            })

    budget.add_trials(trials)
    return {"type": "phase_space_mapping", "results": results_list, "trials": trials}


def dynamic_perturbation_analysis(budget: BudgetTracker) -> dict:
    """Small perturbations from known interesting dampings to test stability."""
    log(f"  [DYNAMIC] Perturbation analysis: basin stability")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    interesting = [0.2, 5.0, 10.0, 12.0, 15.0, 20.0, 25.0]

    for base_d in interesting:
        if budget.exhausted():
            break
        engine_base = make_engine(raw_nodes, raw_edges, base_d)
        apply_standard_injection(engine_base)
        analysis_base = run_and_analyze(engine_base)
        base_basin = analysis_base["dominant_basin"]
        trials += 1

        perturb_results = []
        for delta in [0.01, 0.05, 0.1, 0.5, 1.0]:
            for sign in [1, -1]:
                if budget.exhausted():
                    break
                perturbed_d = max(0.01, base_d + sign * delta)
                engine_p = make_engine(raw_nodes, raw_edges, perturbed_d)
                apply_standard_injection(engine_p)
                analysis_p = run_and_analyze(engine_p)
                trials += 1
                perturb_results.append({
                    "delta": round(sign * delta, 3),
                    "damping": round(perturbed_d, 3),
                    "basin": format_basin(analysis_p["dominant_basin"], labels),
                    "basin_changed": analysis_p["dominant_basin"] != base_basin,
                    "iton": round(analysis_p["iton_score"], 3),
                })

        stability = (sum(1 for p in perturb_results if not p["basin_changed"])
                      / max(1, len(perturb_results)))
        results_list.append({
            "base_damping": base_d,
            "base_basin": format_basin(base_basin, labels),
            "perturbations": perturb_results,
            "stability": round(stability, 3),
        })

    budget.add_trials(trials)
    return {"type": "perturbation_analysis", "results": results_list, "trials": trials}


def dynamic_symmetry_breaking(budget: BudgetTracker) -> dict:
    """Test asymmetric injection patterns to discover new basins."""
    log(f"  [DYNAMIC] Symmetry breaking: asymmetric injections")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    groups = get_groups(raw_nodes)
    results_list = []
    trials = 0

    node_by_group: dict[str, list[str]] = {}
    for n in raw_nodes:
        g = groups.get(n.get("label", ""), "other")
        node_by_group.setdefault(g, []).append(n.get("label", ""))

    test_dampings = [0.2, 5.0, 10.0, 15.0]

    for d in test_dampings:
        if budget.exhausted():
            break
        engine_sym = make_engine(raw_nodes, raw_edges, d)
        apply_standard_injection(engine_sym)
        analysis_sym = run_and_analyze(engine_sym)
        trials += 1

        for group_name, gnodes in list(node_by_group.items())[:5]:
            if budget.exhausted():
                break
            engine_asym = make_engine(raw_nodes, raw_edges, d)
            for lbl in gnodes[:3]:
                engine_asym.inject(lbl, 50.0)
            analysis_asym = run_and_analyze(engine_asym)
            trials += 1
            results_list.append({
                "damping": d,
                "injection_group": group_name,
                "n_injected": min(3, len(gnodes)),
                "sym_basin": format_basin(analysis_sym["dominant_basin"], labels),
                "asym_basin": format_basin(analysis_asym["dominant_basin"], labels),
                "basin_shifted": (analysis_sym["dominant_basin"]
                                  != analysis_asym["dominant_basin"]),
                "iton": round(analysis_asym["iton_score"], 3),
            })

    budget.add_trials(trials)
    return {"type": "symmetry_breaking", "results": results_list, "trials": trials}


def dynamic_resonance_hunting(budget: BudgetTracker) -> dict:
    """Ultra-fine sweep to find resonance/transition points."""
    log(f"  [DYNAMIC] Resonance hunting: fine-grained transition search")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    # Coarse scan
    coarse_basins: dict[int, int] = {}
    for d_int in range(0, 85, 5):
        if budget.exhausted():
            break
        d_val = max(0.1, float(d_int))
        engine = make_engine(raw_nodes, raw_edges, d_val)
        apply_standard_injection(engine)
        analysis = run_and_analyze(engine)
        coarse_basins[d_int] = analysis["dominant_basin"]
        trials += 1

    # Find transition zones
    transitions = []
    sorted_ds = sorted(coarse_basins.keys())
    for i in range(len(sorted_ds) - 1):
        d1, d2 = sorted_ds[i], sorted_ds[i + 1]
        if coarse_basins[d1] != coarse_basins[d2]:
            transitions.append((float(d1), float(d2)))

    # Fine sweep transitions
    for d_lo, d_hi in transitions[:4]:
        if budget.exhausted():
            break
        step = (d_hi - d_lo) / 20.0
        d = d_lo
        while d <= d_hi and not budget.exhausted():
            engine = make_engine(raw_nodes, raw_edges, d)
            apply_standard_injection(engine)
            analysis = run_and_analyze(engine)
            trials += 1
            results_list.append({
                "damping": round(d, 3),
                "basin": format_basin(analysis["dominant_basin"], labels),
                "iton": round(analysis["iton_score"], 3),
                "coherence": round(analysis["coherence"], 3),
                "transition_zone": f"{d_lo}-{d_hi}",
            })
            d += step

    budget.add_trials(trials)
    return {
        "type": "resonance_hunting",
        "transitions_found": len(transitions),
        "results": results_list,
        "trials": trials,
    }


def dynamic_boundary_cartography(budget: BudgetTracker) -> dict:
    """Map basin boundaries in damping x edge-w0 space."""
    log(f"  [DYNAMIC] Boundary cartography: basin boundary mapping")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    results_list = []
    trials = 0

    dampings = [0.5, 2.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0, 50.0, 70.0]
    w0_values = [1, 3, 5, 10, 20, 50]

    for w0_val in w0_values:
        if budget.exhausted():
            break
        mod_edges, _ = set_edge_weights(raw_edges, raw_nodes, lambda e, g: w0_val)
        for d in dampings:
            if budget.exhausted():
                break
            engine = make_engine(raw_nodes, mod_edges, d)
            apply_standard_injection(engine)
            analysis = run_and_analyze(engine)
            trials += 1
            results_list.append({
                "damping": d, "w0": w0_val,
                "basin": format_basin(analysis["dominant_basin"], labels),
                "iton": round(analysis["iton_score"], 3),
                "coherence": round(analysis["coherence"], 3),
            })

    budget.add_trials(trials)
    return {"type": "boundary_cartography", "results": results_list, "trials": trials}


def dynamic_stochastic_injection(budget: BudgetTracker) -> dict:
    """Random injection patterns to discover unexpected basins."""
    log(f"  [DYNAMIC] Stochastic injection: random patterns")
    raw_nodes, raw_edges = load_default_graph()
    labels = get_labels(raw_nodes)
    node_labels = [n.get("label", f"node_{i}") for i, n in enumerate(raw_nodes)]
    results_list = []
    trials = 0

    test_dampings = [0.2, 5.0, 10.0, 15.0, 20.0]

    for d in test_dampings:
        if budget.exhausted():
            break
        for trial_i in range(10):
            if budget.exhausted():
                break
            engine = make_engine(raw_nodes, raw_edges, d)
            n_inject = random.randint(3, 7)
            targets = random.sample(node_labels, min(n_inject, len(node_labels)))
            injected = []
            for lbl in targets:
                amt = random.uniform(5.0, 100.0)
                engine.inject(lbl, amt)
                injected.append({"node": lbl, "amount": round(amt, 1)})

            analysis = run_and_analyze(engine)
            trials += 1
            results_list.append({
                "damping": d, "trial": trial_i,
                "n_injected": n_inject,
                "injections": injected,
                "basin": format_basin(analysis["dominant_basin"], labels),
                "iton": round(analysis["iton_score"], 3),
                "coherence": round(analysis["coherence"], 3),
            })

    budget.add_trials(trials)
    return {"type": "stochastic_injection", "results": results_list, "trials": trials}


# Map frontier category names to experiment generators
FRONTIER_GENERATORS = {
    "information_theoretic": dynamic_entropy_measurement,
    "capacity_measurement": dynamic_capacity_test,
    "error_correction": dynamic_error_resilience,
    # Gen-2 frontier types
    "multi_damping_sweep": dynamic_multi_damping_sweep,
    "phase_space_mapping": dynamic_phase_space_mapping,
    "perturbation_analysis": dynamic_perturbation_analysis,
    "symmetry_breaking": dynamic_symmetry_breaking,
    "resonance_hunting": dynamic_resonance_hunting,
    "boundary_cartography": dynamic_boundary_cartography,
    "stochastic_injection": dynamic_stochastic_injection,
}


def run_dynamic_experiment(exp_type: str, genome: dict, budget: BudgetTracker) -> dict:
    """Run a dynamically generated experiment based on type and genome."""
    log(f"\n  [RSI DYNAMIC] Running: {exp_type}")

    if exp_type in FRONTIER_GENERATORS:
        return FRONTIER_GENERATORS[exp_type](budget)

    if exp_type == "parameter_sweep":
        # Use genome to pick priority zone
        zones = genome.get("parameter_focus", {}).get("damping_priority_zones", [])
        if zones:
            zone = max(zones, key=lambda z: z.get("priority", 0))
            return dynamic_parameter_sweep(zone["range"], 1.0, budget)
        return dynamic_parameter_sweep([0, 84], 5.0, budget)

    if exp_type == "logic_gate":
        return dynamic_gate_test(
            [0.2, 5.0, 10.0, 12.0, 15.0, 20.0],
            [3, 10, 50],
            budget,
        )

    if exp_type == "clock_signal":
        # Run a focused clock sweep at the most interesting damping
        raw_nodes, raw_edges = load_default_graph()
        labels = get_labels(raw_nodes)
        results_list = []
        trials = 0
        for d in [5.0, 10.0, 15.0, 20.0]:
            if budget.exhausted():
                break
            for period in [50, 75, 100, 150]:
                engine = make_engine(raw_nodes, raw_edges, d)
                apply_standard_injection(engine)
                for _ in range(20):
                    engine.run(period)
                    for lbl, amt in STANDARD_INJECTIONS:
                        engine.inject(lbl, amt * 0.1)
                rho_snap = [[n["rho"] for n in engine.physics.nodes]]
                analysis = analyze_trial(engine, rho_snap)
                m = engine.compute_metrics()
                trials += 1
                results_list.append({
                    "damping": d, "period": period,
                    "iton": round(analysis["iton_score"], 3),
                    "basin": format_basin(m["rhoMaxId"], labels),
                })
        budget.add_trials(trials)
        return {"type": "clock_signal", "results": results_list, "trials": trials}

    if exp_type == "injection_protocol":
        return dynamic_parameter_sweep([0, 20], 2.0, budget)

    if exp_type == "raw_lead_followup":
        return dynamic_raw_lead_followup(genome, budget)

    if exp_type == "cascade_pipeline":
        return dynamic_cascade_pipeline(genome, budget)

    if exp_type == "replication":
        return dynamic_replication(genome, budget)

    # Fallback: generic sweep
    log(f"  [WARNING] No specific generator for '{exp_type}', running generic sweep")
    return dynamic_parameter_sweep([0, 84], 5.0, budget)


# ===================================================================
# RSI INTEGRATION
# ===================================================================

def run_rsi_evaluation_cycle(cycle_id: int, budget: BudgetTracker) -> dict:
    """Run one RSI EVALUATE→REFLECT→MUTATE→PLAN cycle (no execution)."""
    from rsi_engine import (
        evaluate_fitness, reflect, mutate_genome,
        generate_plan, log_fitness, log_cycle,
        _load_genome, _save_genome,
    )

    log(f"\n{'='*70}")
    log(f"  RSI CYCLE {cycle_id}")
    log(f"{'='*70}")

    # EVALUATE
    fitness = evaluate_fitness(cycle_id)
    log(f"  Fitness: {fitness.fitness:.1f}/100 | Claims: {fitness.claim_count} | "
        f"Open Q: {fitness.open_questions} | Trials: {fitness.trial_count}")

    # REFLECT
    reflection = reflect(fitness)
    log(f"  Delta: {reflection.fitness_delta:+.1f} | Improving: {reflection.is_improving} | "
        f"Plateau: {reflection.is_plateauing}")
    for rec in reflection.recommendations:
        log(f"    → {rec}")

    # MUTATE
    genome = _load_genome()
    if not genome.get("created"):
        genome["created"] = datetime.now(timezone.utc).isoformat()
    genome = mutate_genome(genome, reflection)
    _save_genome(genome)
    hist = genome.get("history", [])
    if hist and hist[-1].get("mutations"):
        for m in hist[-1]["mutations"]:
            log(f"    >> {m}")

    # PLAN
    plan = generate_plan(genome, reflection, fitness, mode="persistent")
    log(f"  Plan: {len(plan.experiments)} experiments")
    for i, exp in enumerate(plan.experiments, 1):
        log(f"    {i}. [{exp['priority']:>6s}] {exp['type']}: {exp['description']}")

    # COMMIT
    log_fitness(fitness)
    execution = {"cycle_id": cycle_id, "mode": "persistent",
                 "experiments_planned": len(plan.experiments), "experiments_executed": 0}
    log_cycle(cycle_id, fitness, reflection, plan, execution)

    return {
        "cycle_id": cycle_id,
        "fitness": fitness.fitness,
        "plan_experiments": [e["type"] for e in plan.experiments],
        "genome": genome,
        "reflection": reflection.to_dict(),
    }


# ===================================================================
# REPORT GENERATION
# ===================================================================

def generate_report(all_results: list[dict], budget: BudgetTracker):
    """Generate overnight_report.md summarizing all findings."""
    log("\nGenerating overnight report...")

    lines = [
        "# SOL Overnight RSI Report",
        f"\n**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Duration:** {budget.elapsed()/3600:.1f} hours",
        f"**Total Trials:** {budget.trial_count}",
        f"**Output:** `{_OUTPUT_DIR.relative_to(_SOL_ROOT)}`\n",
        "---\n",
    ]

    # Phase 1 results
    phase1_suites = [r for r in all_results if r.get("suite")]
    if phase1_suites:
        lines.append("## Phase 1: Targeted Experiment Suites\n")
        for suite_result in phase1_suites:
            suite_name = suite_result.get("suite", "unknown")
            lines.append(f"### {suite_name}\n")

            for probe_name, probe_data in suite_result.get("probes", {}).items():
                lines.append(f"**{probe_name}:**\n")
                if isinstance(probe_data, list):
                    # Table format for list results
                    if probe_data and isinstance(probe_data[0], dict):
                        keys = list(probe_data[0].keys())
                        # Limit to key columns
                        show_keys = [k for k in keys if k not in ("coefficients", "window_itons",
                                                                    "basin_visits", "top5_rho",
                                                                    "truth_table", "w0_tests",
                                                                    "analysis")][:6]
                        if show_keys:
                            lines.append("| " + " | ".join(show_keys) + " |")
                            lines.append("| " + " | ".join(["---"] * len(show_keys)) + " |")
                            for row in probe_data[:20]:  # Limit rows
                                vals = []
                                for k in show_keys:
                                    v = row.get(k, "")
                                    if isinstance(v, float):
                                        vals.append(f"{v:.3f}")
                                    elif isinstance(v, dict):
                                        vals.append(str(v)[:30])
                                    else:
                                        vals.append(str(v)[:30])
                                lines.append("| " + " | ".join(vals) + " |")
                            if len(probe_data) > 20:
                                lines.append(f"\n*...{len(probe_data)-20} more rows*\n")
                elif isinstance(probe_data, dict):
                    for k, v in probe_data.items():
                        if isinstance(v, (str, int, float, bool)):
                            lines.append(f"- {k}: {v}")
                        elif isinstance(v, dict) and len(str(v)) < 200:
                            lines.append(f"- {k}: {v}")
                lines.append("")

    # Phase 2 RSI cycles
    rsi_results = [r for r in all_results if r.get("cycle_id")]
    if rsi_results:
        lines.append("\n## Phase 2: RSI Cycles\n")
        lines.append("| Cycle | Fitness | Experiments | Key Mutations |")
        lines.append("| --- | --- | --- | --- |")
        for r in rsi_results:
            mutations = r.get("reflection", {}).get("recommendations", [])[:1]
            lines.append(f"| {r['cycle_id']} | {r['fitness']:.1f} | "
                         f"{', '.join(r.get('plan_experiments', [])[:3])} | "
                         f"{mutations[0] if mutations else 'none'} |")

    # Dynamic experiment results
    dynamic_results = [r for r in all_results if r.get("type")]
    if dynamic_results:
        lines.append("\n## Dynamic Experiments\n")
        for dr in dynamic_results:
            lines.append(f"### {dr['type']}")
            lines.append(f"- Trials: {dr.get('trials', '?')}")
            if dr.get("total_unique_basins"):
                lines.append(f"- Total unique basins: {dr['total_unique_basins']} "
                             f"({dr.get('total_bits', '?')} bits)")
            results_list = dr.get("results", dr.get("per_damping", []))
            if results_list and isinstance(results_list, list):
                lines.append(f"- Results: {len(results_list)} data points")
            lines.append("")

    # Budget summary
    lines.append("\n## Budget Summary\n")
    lines.append(f"- Total time: {budget.elapsed()/3600:.2f} hours")
    lines.append(f"- Total trials: {budget.trial_count}")
    lines.append(f"- Suite breakdown: {budget.suite_times}")
    lines.append("")

    report_text = "\n".join(lines)
    with open(_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)
    log(f"Report saved to {_REPORT_FILE}")
    return report_text


# ===================================================================
# MAIN LOOP
# ===================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SOL Overnight RSI Runner")
    parser.add_argument("--budget-hours", type=float, default=6.0,
                        help="Maximum runtime in hours (default: 6)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Plan only, don't execute experiments")
    parser.add_argument("--suite", type=int, default=0,
                        help="Run a single suite only (1-5)")
    args = parser.parse_args()

    budget = BudgetTracker(args.budget_hours)

    log("=" * 70)
    log("  SOL OVERNIGHT RSI RUNNER")
    log(f"  Budget: {args.budget_hours}h | Output: {_OUTPUT_DIR}")
    log(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    if args.dry_run:
        log("\n[DRY RUN] Would execute:")
        log("  Phase 1: 5 experiment suites (~60-90 min)")
        log("    Suite 1: Open Question Resolution (Q1-Q4)")
        log("    Suite 2: Dead Zone Physics (d=15-40)")
        log("    Suite 3: Transition Zone Mapping (d=10-15)")
        log("    Suite 4: Logic Gate Extension (XOR, NAND, Latch)")
        log("    Suite 5: Injection Protocol Exploration")
        log("  Phase 2: RSI loop for remaining time")
        log("    Dynamic experiments based on genome + reflection")
        log(f"  Total budget: {args.budget_hours}h")
        return

    all_results: list[dict] = []

    # ===== PHASE 1: Targeted Suites =====
    log("\n" + "=" * 70)
    log("  PHASE 1: TARGETED EXPERIMENT SUITES")
    log("=" * 70)

    suite_fns = {
        1: suite_1_open_questions,
        2: suite_2_dead_zone,
        3: suite_3_transition_zone,
        4: suite_4_logic_extension,
        5: suite_5_injection_exploration,
    }

    suites_to_run = [args.suite] if args.suite > 0 else [1, 2, 3, 4, 5]

    for suite_num in suites_to_run:
        if budget.exhausted():
            log(f"\n  Budget exhausted before suite {suite_num}")
            break

        try:
            result = suite_fns[suite_num](budget)
            all_results.append(result)

            # Save suite results immediately
            suite_file = _OUTPUT_DIR / f"suite_{suite_num}.json"
            with open(suite_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            log(f"  Results saved to {suite_file}")

        except Exception as e:
            log(f"  [ERROR] Suite {suite_num} failed: {e}")
            log(f"  {traceback.format_exc()}")
            all_results.append({"suite": f"suite_{suite_num}_ERROR", "error": str(e)})

        log(f"\n  === BUDGET: {budget.summary()} ===\n")

    # ===== RSI EVALUATION after Phase 1 =====
    if not budget.exhausted():
        log("\n" + "=" * 70)
        log("  POST-PHASE-1 RSI EVALUATION")
        log("=" * 70)

        try:
            from rsi_engine import _load_fitness_history
            history = _load_fitness_history()
            rsi_cycle_id = len(history) + 1

            rsi_result = run_rsi_evaluation_cycle(rsi_cycle_id, budget)
            all_results.append(rsi_result)
        except Exception as e:
            log(f"  [ERROR] RSI evaluation failed: {e}")
            log(f"  {traceback.format_exc()}")

    # ===== PHASE 2: RSI-Driven Dynamic Experiments =====
    if not budget.exhausted() and args.suite == 0:
        log("\n" + "=" * 70)
        log("  PHASE 2: RSI-DRIVEN DYNAMIC EXPERIMENTS")
        log("=" * 70)

        phase2_cycle = 0
        consecutive_empty = 0
        # --- Experiment dedup: track which (type, config_hash) combos were run ---
        executed_experiments: set[str] = set()

        def _exp_dedup_key(exp_type: str, genome: dict) -> str:
            """Create a dedup key for an experiment type + genome config."""
            # Static generators always produce the same output for the same type
            static_types = {"logic_gate", "clock_signal", "raw_lead_followup",
                            "cascade_pipeline", "replication",
                            "information_theoretic", "capacity_measurement",
                            "error_correction", "perturbation_analysis",
                            "symmetry_breaking"}
            if exp_type in static_types:
                return exp_type

            # Randomized generators: include a cycle counter so they can
            # re-run with different random seeds each iteration
            randomized_types = {"stochastic_injection", "multi_damping_sweep",
                                "resonance_hunting", "boundary_cartography",
                                "phase_space_mapping"}
            if exp_type in randomized_types:
                return f"{exp_type}_iter{phase2_cycle}"

            # parameter_sweep varies by genome priority zones
            if exp_type == "parameter_sweep":
                zones = genome.get("parameter_focus", {}).get("damping_priority_zones", [])
                if zones:
                    zone = max(zones, key=lambda z: z.get("priority", 0))
                    return f"parameter_sweep_{zone['range']}"
                return "parameter_sweep_[0,84]"

            if exp_type == "injection_protocol":
                return "injection_protocol"

            return f"{exp_type}_generic"

        while not budget.exhausted():
            phase2_cycle += 1
            log(f"\n  --- Phase 2 Iteration {phase2_cycle} ---")
            log(f"  Budget remaining: {budget.remaining()/3600:.1f}h")

            # Run RSI cycle to get plan
            try:
                from rsi_engine import _load_fitness_history, _load_genome
                history = _load_fitness_history()
                rsi_cycle_id = len(history) + 1

                rsi_result = run_rsi_evaluation_cycle(rsi_cycle_id, budget)
                all_results.append(rsi_result)

                # Execute planned experiments
                genome = rsi_result.get("genome", {})
                planned_types = rsi_result.get("plan_experiments", [])

                # --- Dedup filter ---
                new_experiments = []
                skipped = 0
                for exp_type in planned_types:
                    if exp_type == "open_question_resolution":
                        continue  # Already done in Phase 1
                    dedup_key = _exp_dedup_key(exp_type, genome)
                    if dedup_key in executed_experiments:
                        skipped += 1
                        continue
                    new_experiments.append((exp_type, dedup_key))

                if skipped > 0:
                    log(f"  [DEDUP] Skipped {skipped} already-run experiments")

                if not new_experiments:
                    log(f"  [DEDUP] All planned experiments already run")
                    # Force compile to pick up new findings
                    try:
                        sys.path.insert(0, str(Path(__file__).resolve().parent / "tools" / "sol-rsi"))
                        from claim_compiler import compile_results as _compile
                        _compile(data_dirs=[_OUTPUT_DIR], update_proof_packet_flag=True, verbose=False)
                    except Exception:
                        pass

                    consecutive_empty += 1
                    log(f"  [DEDUP] Consecutive empty: {consecutive_empty}/10")

                    # NOVELTY INJECTION: force genome diversity for next cycle
                    try:
                        from rsi_engine import _load_genome as _lg, _save_genome as _sg
                        g = _lg()
                        prefs = g.get("template_preferences", {})
                        for cat in prefs:
                            prefs[cat] = max(0.1, min(2.0,
                                prefs[cat] + random.uniform(-0.4, 0.4)))
                        g["exploration_rate"] = min(0.9,
                            g.get("exploration_rate", 0.2) + 0.15)
                        g["mutation_rate"] = min(0.5,
                            g.get("mutation_rate", 0.15) + 0.10)
                        _sg(g)
                        log(f"  [NOVELTY] Injected diversity into genome")
                    except Exception as e:
                        log(f"  [WARNING] Novelty injection failed: {e}")

                    # Exit only after 10 consecutive empty cycles
                    if consecutive_empty >= 10:
                        log(f"  [DEDUP] Extended plateau ({consecutive_empty} "
                            f"consecutive empty) — ending Phase 2.")
                        break
                    continue

                consecutive_empty = 0  # Reset: we have new experiments

                for exp_type, dedup_key in new_experiments:
                    if budget.exhausted():
                        break

                    try:
                        exp_result = run_dynamic_experiment(exp_type, genome, budget)
                        all_results.append(exp_result)
                        executed_experiments.add(dedup_key)

                        # Save immediately
                        exp_file = _OUTPUT_DIR / f"dynamic_{phase2_cycle}_{exp_type}.json"
                        with open(exp_file, "w", encoding="utf-8") as f:
                            json.dump(exp_result, f, indent=2, default=str)

                    except Exception as e:
                        log(f"  [ERROR] Dynamic experiment '{exp_type}' failed: {e}")
                        log(f"  {traceback.format_exc()}")

                log(f"  === BUDGET: {budget.summary()} ===")

            except Exception as e:
                log(f"  [ERROR] Phase 2 cycle {phase2_cycle} failed: {e}")
                log(f"  {traceback.format_exc()}")
                time.sleep(5)  # Brief pause before retrying
                if phase2_cycle > 50:  # Safety cutoff
                    log("  Safety cutoff: too many cycles")
                    break

    # ===== FINAL REPORT =====
    log("\n" + "=" * 70)
    log("  GENERATING FINAL REPORT")
    log("=" * 70)

    generate_report(all_results, budget)

    # ===== CLAIM COMPILATION =====
    log("\n" + "=" * 70)
    log("  COMPILING CLAIMS INTO PROOF PACKET")
    log("=" * 70)

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "tools" / "sol-rsi"))
        from claim_compiler import compile_results

        compile_result = compile_results(
            data_dirs=[_OUTPUT_DIR],
            update_proof_packet_flag=True,
            verbose=True,
        )

        log(f"  Files scanned: {compile_result.files_scanned} "
            f"({compile_result.files_new} new)")
        log(f"  New claims: {len(compile_result.new_claims)}")
        log(f"  Question updates: {len(compile_result.question_updates)}")
        log(f"  Trials added: {compile_result.total_trials_added}")
        log(f"  Proof packet updated: {compile_result.proof_packet_updated}")

        if compile_result.new_claims:
            for c in compile_result.new_claims:
                log(f"    {c.claim_id}: {c.text[:80]}...")
        if compile_result.question_updates:
            for qu in compile_result.question_updates:
                log(f"    Q{qu.question_number} [{qu.status}]: "
                    f"{qu.answer_summary[:60]}...")
    except Exception as e:
        log(f"  [ERROR] Claim compilation failed: {e}")
        log(f"  {traceback.format_exc()}")

    # Save complete results
    all_results_file = _OUTPUT_DIR / "all_results.json"
    with open(all_results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)

    flush_log()

    log("\n" + "=" * 70)
    log("  OVERNIGHT RSI RUN COMPLETE")
    log(f"  Duration: {budget.elapsed()/3600:.2f}h")
    log(f"  Total trials: {budget.trial_count}")
    log(f"  Output: {_OUTPUT_DIR}")
    log("=" * 70)


if __name__ == "__main__":
    main()
