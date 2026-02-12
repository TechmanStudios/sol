"""
Jeans Cosmology Experiment — "Density → Collapse → New Structure"
================================================================
Implements the rd1.md "Telekinetic Build" as an executable physics experiment.

Core loop:
  1. Inject energy (rho) into the graph — varying rate and locality
  2. Nodes accumulate density; when J = rho/(|p|+eps) >= Jcrit, node collapses
     into a "Star" (isStellar=True)
  3. Stars accrete neighbors' mass (tractor beam)
  4. Stars that accrete enough mass spawn new *Synth* ("Gold") nodes —
     the engine literally grows new structure from collapse
  5. Wandering attention (saccade) hops between stars and bridges

Two knobs that change the "cosmology":
  A. Collapse threshold (Jcrit)   — 5, 10, 18 (default), 30, 50
  B. Injection strategy           — concentrated blast, slow drizzle, cluster spray

Outputs: per-step trace CSV, condition summary CSV, run bundle Markdown,
         and a cosmology comparison table.

Usage:
    python jeans_cosmology_experiment.py
    python jeans_cosmology_experiment.py --jcrit 18 --strategy blast
    python jeans_cosmology_experiment.py --sweep          # full knob sweep
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from copy import deepcopy
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any

# Resolve imports
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "tools" / "sol-core"))

from sol_engine import (
    SOLEngine, SOLPhysics, compute_metrics, snapshot_state,
    restore_state, create_engine, DEFAULT_GRAPH_PATH, _Rng,
)


# =====================================================================
# Configuration
# =====================================================================

# J = rho / (c_press * ln(1 + rho/m) + eps)
# At c_press=0.1, J → 1/c_press = 10 for any nonzero rho.
# So Jcrit < 10 collapses everything; the interesting physics is [12..100].
JCRIT_VALUES = [8.0, 15.0, 18.0, 30.0, 50.0]

INJECTION_STRATEGIES = {
    "blast": {
        "description": "Single concentrated injection of 200 rho into one node at step 0",
        "injections": [{"label": "grail", "amount": 200, "at_step": 0}],
    },
    "drizzle": {
        "description": "Slow drizzle: 10 rho into 'grail' every 20 steps for 400 steps",
        "injections": [{"label": "grail", "amount": 10, "at_step": s} for s in range(0, 400, 20)],
    },
    "cluster_spray": {
        "description": "Distribute 200 rho across 5 neighboring spirit nodes at step 0",
        "injections": [
            {"label": "christ", "amount": 40, "at_step": 0},
            {"label": "temple doors", "amount": 40, "at_step": 0},
            {"label": "numis'om", "amount": 40, "at_step": 0},
            {"label": "metatron", "amount": 40, "at_step": 0},
            {"label": "venus", "amount": 40, "at_step": 0},
        ],
    },
}

DEFAULT_STEPS = 600
DEFAULT_DT = 0.12
DEFAULT_C_PRESS = 0.1
DEFAULT_DAMPING = 0.2
DEFAULT_RNG_SEED = 42


# =====================================================================
# Synth Node Spawner — the "Active Inference" layer from rd1.md
# =====================================================================

@dataclass
class SynthEvent:
    """Record of a synth node birth."""
    tick: int
    parent_id: Any
    parent_label: str
    synth_id: Any
    synth_label: str
    parent_rho_at_birth: float
    parent_semantic_mass: float


class SynthSpawner:
    """
    When a node crosses stellar threshold, it may spawn a new 'synth' (Gold)
    node — the engine literally grows new structure from collapse.

    Rules:
      - A star can spawn at most 1 synth per star (one "insight" per collapse).
      - Spawn happens when isStellar first becomes True on a node.
      - The synth node inherits 5% of the parent's rho and connects via a
        new edge with kind='synth'.
      - Synths start with high semantic mass (10.0) and a 20-tick stellar
        cooldown to prevent infinite synth-of-synth cascades.
      - The synth label is "synth:{parent_label}".
    """

    SYNTH_COOLDOWN = 20  # ticks before a synth can go stellar
    SYNTH_RHO_GIFT = 0.05  # fraction of parent rho gifted
    SYNTH_INITIAL_MASS = 10.0  # high mass → higher pressure → harder to reach Jcrit

    def __init__(self, physics: SOLPhysics):
        self.physics = physics
        self._spawned_parents: set = set()  # parent ids that already spawned
        self._synth_birth_tick: dict = {}  # synth_id → birth tick
        self.events: list[SynthEvent] = []
        self._next_synth_id = 9000  # synthetic IDs start high

    def check_and_spawn(self, tick: int) -> list[SynthEvent]:
        """Scan for newly stellar nodes and spawn synth nodes."""
        # Enforce cooldown: strip isStellar from synths still in cooldown
        for nid, birth_tick in self._synth_birth_tick.items():
            if tick - birth_tick < self.SYNTH_COOLDOWN:
                node = self.physics.node_by_id.get(nid)
                if node:
                    node["isStellar"] = False
                    node["isConstellation"] = False

        new_events = []
        for node in list(self.physics.nodes):  # copy list since we may modify
            if not node.get("isStellar"):
                continue
            if node["id"] in self._spawned_parents:
                continue
            # Only original graph nodes can parent synths — no synth-of-synth chains
            if node.get("isSynth"):
                continue

            self._spawned_parents.add(node["id"])

            # Birth a synth node
            synth_id = f"synth_{self._next_synth_id}"
            self._next_synth_id += 1
            synth_label = f"synth:{node['label']}"

            # Synth gets a fraction of parent's rho
            rho_gift = node["rho"] * self.SYNTH_RHO_GIFT
            node["rho"] -= rho_gift

            synth_node = {
                "id": synth_id,
                "label": synth_label,
                "group": "synth",
                "rho": rho_gift,
                "p": 0.0,
                "psi": 0.0,
                "psi_bias": 0.0,
                "semanticMass": self.SYNTH_INITIAL_MASS,
                "semanticMass0": self.SYNTH_INITIAL_MASS,
                "lastInteractionTime": 0.0,
                "isSingularity": False,
                "isStellar": False,
                "isConstellation": False,
                "isSynth": True,
            }
            self._synth_birth_tick[synth_id] = tick

            # Add node to physics
            self.physics.nodes.append(synth_node)
            self.physics.node_by_id[synth_id] = synth_node
            self.physics.node_index_by_id[synth_id] = len(self.physics.nodes) - 1

            # Add edge connecting synth to parent
            synth_edge = {
                "from": node["id"],
                "to": synth_id,
                "w0": 0.70,
                "background": False,
                "kind": "synth",
                "flux": 0.0,
                "conductance": 1.0,
            }
            self.physics.edges.append(synth_edge)

            # Also connect synth to parent's neighbors (max 3) for integration
            neighbor_ids = []
            for e in self.physics.edges:
                if e.get("background"):
                    continue
                if e["from"] == node["id"]:
                    neighbor_ids.append(e["to"])
                elif e["to"] == node["id"]:
                    neighbor_ids.append(e["from"])
            # Pick up to 3 strongest neighbors by rho
            neighbors_with_rho = []
            for nid in set(neighbor_ids):
                nb = self.physics.node_by_id.get(nid)
                if nb and nid != synth_id:
                    neighbors_with_rho.append((nid, nb.get("rho", 0)))
            neighbors_with_rho.sort(key=lambda x: x[1], reverse=True)
            for nid, _ in neighbors_with_rho[:3]:
                bridge_edge = {
                    "from": synth_id,
                    "to": nid,
                    "w0": 0.35,
                    "background": False,
                    "kind": "synth",
                    "flux": 0.0,
                    "conductance": 1.0,
                }
                self.physics.edges.append(bridge_edge)

            event = SynthEvent(
                tick=tick,
                parent_id=node["id"],
                parent_label=node["label"],
                synth_id=synth_id,
                synth_label=synth_label,
                parent_rho_at_birth=node["rho"],
                parent_semantic_mass=node.get("semanticMass", 1.0),
            )
            self.events.append(event)
            new_events.append(event)

        return new_events


# =====================================================================
# Tractor Beam — enhanced accretion pull (rd1.md "Visual Physics")
# =====================================================================

def _build_adjacency(physics: SOLPhysics) -> dict:
    """Build adjacency map: node_id -> list of neighbor node_ids (non-background edges)."""
    adj: dict[Any, list] = {n["id"]: [] for n in physics.nodes}
    for e in physics.edges:
        if e.get("background"):
            continue
        a, b = e["from"], e["to"]
        if a in adj:
            adj[a].append(b)
        if b in adj:
            adj[b].append(a)
    return adj


def apply_tractor_beam(physics: SOLPhysics, tractor_rate: float = 0.05,
                        adj: dict | None = None):
    """
    Stars exert a 'tractor beam' on neighbors' rho — pulling an extra
    fraction per tick beyond the normal Jeans accretion.  This simulates
    the "Aha!" gravitational pull described in the Telekinetic build.

    tractor_rate: fraction of neighbor rho pulled per call (default 5%/tick)
    Uses pre-built adjacency list for O(stars × avg_degree) instead of O(stars × edges).
    """
    if adj is None:
        adj = _build_adjacency(physics)
    node_by_id = physics.node_by_id

    for star in physics.nodes:
        if not star.get("isStellar"):
            continue
        star_id = star["id"]
        accreted = 0.0
        for nb_id in adj.get(star_id, ()):
            nb = node_by_id.get(nb_id)
            if not nb or nb.get("isBattery") or nb.get("isStellar"):
                continue  # don't pull from other stars
            pull = nb["rho"] * tractor_rate
            if pull <= 0:
                continue
            nb["rho"] -= pull
            accreted += pull
        star["rho"] += accreted


# =====================================================================
# Extended Metrics (star count, synth count, collapse events per tick)
# =====================================================================

def compute_extended_metrics(physics: SOLPhysics, spawner: SynthSpawner,
                              tick: int) -> dict:
    """Standard metrics + stellar/synth census."""
    base = compute_metrics(physics)
    base["tick"] = tick

    star_count = sum(1 for n in physics.nodes if n.get("isStellar"))
    synth_count = sum(1 for n in physics.nodes if n.get("isSynth"))
    constellation_count = sum(1 for n in physics.nodes if n.get("isConstellation"))
    total_semantic_mass = sum(
        n.get("semanticMass", 1.0) for n in physics.nodes if n.get("isStellar")
    )
    max_semantic_mass = max(
        (n.get("semanticMass", 1.0) for n in physics.nodes if n.get("isStellar")),
        default=0.0,
    )

    base["starCount"] = star_count
    base["synthCount"] = synth_count
    base["constellationCount"] = constellation_count
    base["totalStellarSemanticMass"] = round(total_semantic_mass, 6)
    base["maxStellarSemanticMass"] = round(max_semantic_mass, 6)
    base["totalNodes"] = len(physics.nodes)
    base["totalEdges"] = len(physics.edges)
    base["synthEventsSoFar"] = len(spawner.events)

    return base


# =====================================================================
# Single Condition Runner
# =====================================================================

def run_condition(
    jcrit: float,
    strategy_name: str,
    steps: int = DEFAULT_STEPS,
    dt: float = DEFAULT_DT,
    c_press: float = DEFAULT_C_PRESS,
    damping: float = DEFAULT_DAMPING,
    rng_seed: int = DEFAULT_RNG_SEED,
    tractor_rate: float = 0.05,
    metrics_every: int = 1,
) -> dict:
    """
    Run one condition of the cosmology experiment.

    Returns dict with:
      - label, params
      - trace: list of per-step metrics
      - synth_events: list of SynthEvent dicts
      - first_collapse_tick: int or None
      - final_metrics: dict
    """
    label = f"Jcrit={jcrit}_strategy={strategy_name}"

    # Load fresh engine
    with open(DEFAULT_GRAPH_PATH, "r") as f:
        data = json.load(f)
    physics, _ = create_engine(data["rawNodes"], data["rawEdges"], rng_seed=rng_seed)

    # Override Jcrit
    physics.jeans_cfg["Jcrit"] = jcrit

    # Set up synth spawner
    spawner = SynthSpawner(physics)

    # Build injection schedule
    strategy = INJECTION_STRATEGIES[strategy_name]
    injections = strategy["injections"]
    inj_by_step: dict[int, list[dict]] = {}
    for inj in injections:
        step_num = inj.get("at_step", 0)
        inj_by_step.setdefault(step_num, []).append(inj)

    trace = []
    first_collapse_tick = None
    adj = _build_adjacency(physics)  # pre-build, rebuild when graph grows

    for tick in range(steps):
        # Inject if scheduled
        if tick in inj_by_step:
            for inj in inj_by_step[tick]:
                found = False
                for n in physics.nodes:
                    if n["label"].lower() == inj["label"].lower():
                        n["rho"] += inj["amount"]
                        found = True
                        break
                if not found:
                    # fuzzy match
                    for n in physics.nodes:
                        if inj["label"].lower() in n["label"].lower():
                            n["rho"] += inj["amount"]
                            break

        # Physics step
        physics.step(dt, c_press, damping)

        # Extra tractor beam pull (uses adjacency for speed)
        apply_tractor_beam(physics, tractor_rate, adj)

        # Synth spawning — rebuild adjacency if new nodes were born
        new_births = spawner.check_and_spawn(tick)
        if new_births:
            adj = _build_adjacency(physics)

        # Track first collapse
        if first_collapse_tick is None:
            for n in physics.nodes:
                if n.get("isStellar"):
                    first_collapse_tick = tick
                    break

        # Record metrics
        if (tick + 1) % metrics_every == 0 or tick == steps - 1:
            m = compute_extended_metrics(physics, spawner, tick)
            m["condition"] = label
            m["jcrit"] = jcrit
            m["strategy"] = strategy_name
            trace.append(m)

    final_metrics = trace[-1] if trace else {}

    synth_event_dicts = [
        {
            "tick": ev.tick,
            "parent_id": ev.parent_id,
            "parent_label": ev.parent_label,
            "synth_id": ev.synth_id,
            "synth_label": ev.synth_label,
            "parent_rho_at_birth": round(ev.parent_rho_at_birth, 4),
            "parent_semantic_mass": round(ev.parent_semantic_mass, 4),
        }
        for ev in spawner.events
    ]

    return {
        "label": label,
        "jcrit": jcrit,
        "strategy": strategy_name,
        "strategy_desc": strategy["description"],
        "steps": steps,
        "params": {
            "dt": dt, "c_press": c_press, "damping": damping,
            "rng_seed": rng_seed, "tractor_rate": tractor_rate,
        },
        "trace": trace,
        "synth_events": synth_event_dicts,
        "first_collapse_tick": first_collapse_tick,
        "final_metrics": final_metrics,
    }


# =====================================================================
# Full Sweep
# =====================================================================

def run_sweep(
    jcrit_values: list[float] | None = None,
    strategies: list[str] | None = None,
    steps: int = DEFAULT_STEPS,
    **kwargs,
) -> dict:
    """Run the full Jcrit × injection-strategy sweep."""
    jcrits = jcrit_values or JCRIT_VALUES
    strats = strategies or list(INJECTION_STRATEGIES.keys())

    all_results = []
    total_conditions = len(jcrits) * len(strats)
    print(f"\n{'='*68}")
    print(f"  JEANS COSMOLOGY EXPERIMENT")
    print(f"  Conditions: {total_conditions}  (Jcrit×Strategy = {len(jcrits)}×{len(strats)})")
    print(f"  Steps per condition: {steps}")
    print(f"{'='*68}\n")

    t0 = time.time()
    for j_idx, jcrit in enumerate(jcrits):
        for s_idx, strat_name in enumerate(strats):
            cond_num = j_idx * len(strats) + s_idx + 1
            print(f"  [{cond_num}/{total_conditions}] Jcrit={jcrit:>5.1f}  strategy={strat_name:<15} ", end="", flush=True)
            t_cond = time.time()
            result = run_condition(jcrit, strat_name, steps=steps, **kwargs)
            elapsed = time.time() - t_cond
            fm = result["final_metrics"]
            stars = fm.get("starCount", 0)
            synths = fm.get("synthCount", 0)
            fc = result["first_collapse_tick"]
            fc_str = f"t={fc:>3d}" if fc is not None else "  ---"
            print(f"stars={stars:>3d}  synths={synths:>3d}  first_collapse={fc_str}  ({elapsed:.1f}s)")
            all_results.append(result)

    total_time = time.time() - t0
    print(f"\n  Total runtime: {total_time:.1f}s\n")

    return {
        "sweep_params": {
            "jcrit_values": jcrits,
            "strategies": strats,
            "steps": steps,
        },
        "conditions": all_results,
        "runtime_sec": total_time,
    }


# =====================================================================
# Output Writers
# =====================================================================

def write_trace_csv(results: dict, out_dir: Path):
    """Write all per-step metrics as a single trace CSV."""
    all_rows = []
    for cond in results["conditions"]:
        all_rows.extend(cond["trace"])
    if not all_rows:
        return None

    all_keys = set()
    for r in all_rows:
        all_keys.update(r.keys())
    fieldnames = sorted(all_keys)

    path = out_dir / "jeans_cosmology_trace.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    return path


def write_summary_csv(results: dict, out_dir: Path):
    """Write one-row-per-condition summary."""
    rows = []
    for cond in results["conditions"]:
        fm = cond["final_metrics"]
        row = {
            "condition": cond["label"],
            "jcrit": cond["jcrit"],
            "strategy": cond["strategy"],
            "strategy_desc": cond["strategy_desc"],
            "steps": cond["steps"],
            "first_collapse_tick": cond["first_collapse_tick"],
            "starCount": fm.get("starCount", 0),
            "synthCount": fm.get("synthCount", 0),
            "constellationCount": fm.get("constellationCount", 0),
            "totalNodes": fm.get("totalNodes", 0),
            "totalEdges": fm.get("totalEdges", 0),
            "entropy": round(fm.get("entropy", 0), 6),
            "totalFlux": round(fm.get("totalFlux", 0), 4),
            "mass": round(fm.get("mass", 0), 4),
            "avgRho": round(fm.get("avgRho", 0), 6),
            "maxRho": round(fm.get("maxRho", 0), 4),
            "activeCount": fm.get("activeCount", 0),
            "totalStellarSemanticMass": fm.get("totalStellarSemanticMass", 0),
            "maxStellarSemanticMass": fm.get("maxStellarSemanticMass", 0),
        }
        rows.append(row)

    if not rows:
        return None
    path = out_dir / "jeans_cosmology_summary.csv"
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path


def write_synth_log(results: dict, out_dir: Path):
    """Write a synth birth event log."""
    all_events = []
    for cond in results["conditions"]:
        for ev in cond["synth_events"]:
            row = {"condition": cond["label"], **ev}
            all_events.append(row)

    if not all_events:
        path = out_dir / "jeans_cosmology_synth_log.csv"
        path.write_text("# No synth events recorded\n", encoding="utf-8")
        return path

    path = out_dir / "jeans_cosmology_synth_log.csv"
    fieldnames = list(all_events[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_events)
    return path


def write_run_bundle(results: dict, out_dir: Path):
    """Generate a Markdown run bundle."""
    lines = []
    lines.append("# Jeans Cosmology Experiment — Run Bundle")
    lines.append("")
    lines.append("## Question")
    lines.append("How do the collapse threshold (Jcrit) and injection strategy (blast / drizzle / cluster)")
    lines.append("shape the topology of emergent structure in the SOL graph?")
    lines.append("")
    lines.append("## Hypothesis")
    lines.append("- **Low Jcrit** (5–10): Many stars form quickly → heavy accretion → high synth count → 'rich' cosmology")
    lines.append("- **High Jcrit** (30–50): Few or no collapses → energy dissipates → 'barren' cosmology")
    lines.append("- **Blast injection**: Single hot node collapses first → radial expansion of structure")
    lines.append("- **Drizzle injection**: Slow accumulation → delayed but distributed stellar formation")
    lines.append("- **Cluster spray**: Multiple simultaneous collapses → synth-web between stars")
    lines.append("")

    lines.append("## Invariants")
    params = results["conditions"][0]["params"] if results["conditions"] else {}
    lines.append(f"- dt = {params.get('dt', DEFAULT_DT)}")
    lines.append(f"- c_press = {params.get('c_press', DEFAULT_C_PRESS)}")
    lines.append(f"- damping = {params.get('damping', DEFAULT_DAMPING)}")
    lines.append(f"- tractor_rate = {params.get('tractor_rate', 0.05)}")
    lines.append(f"- rng_seed = {params.get('rng_seed', DEFAULT_RNG_SEED)}")
    lines.append(f"- steps = {results['sweep_params']['steps']}")
    lines.append("")

    lines.append("## Knobs")
    lines.append(f"- **Jcrit**: {results['sweep_params']['jcrit_values']}")
    lines.append(f"- **Strategy**: {results['sweep_params']['strategies']}")
    lines.append("")

    # Cosmology comparison table
    lines.append("## Cosmology Comparison")
    lines.append("")
    lines.append("| Jcrit | Strategy | Stars | Synths | First Collapse | Entropy | Mass | MaxRho | Active |")
    lines.append("|------:|----------|------:|-------:|---------------:|--------:|-----:|-------:|-------:|")
    for cond in results["conditions"]:
        fm = cond["final_metrics"]
        fc = cond["first_collapse_tick"]
        fc_str = str(fc) if fc is not None else "---"
        lines.append(
            f"| {cond['jcrit']:>5.1f} | {cond['strategy']:<14} "
            f"| {fm.get('starCount', 0):>5d} | {fm.get('synthCount', 0):>6d} "
            f"| {fc_str:>14} | {fm.get('entropy', 0):>7.4f} "
            f"| {fm.get('mass', 0):>4.2f} | {fm.get('maxRho', 0):>6.2f} "
            f"| {fm.get('activeCount', 0):>6d} |"
        )
    lines.append("")

    # Synth birth timeline
    lines.append("## Synth Birth Log (First 30 events)")
    lines.append("")
    all_events = []
    for cond in results["conditions"]:
        for ev in cond["synth_events"]:
            all_events.append({**ev, "condition": cond["label"]})
    all_events.sort(key=lambda e: (e["condition"], e["tick"]))

    if all_events:
        lines.append("| Condition | Tick | Parent | Synth | Parent ρ | Semantic Mass |")
        lines.append("|-----------|-----:|--------|-------|----------:|--------------:|")
        for ev in all_events[:30]:
            lines.append(
                f"| {ev['condition'][:40]} | {ev['tick']:>4d} "
                f"| {ev['parent_label']} | {ev['synth_label']} "
                f"| {ev['parent_rho_at_birth']:>8.4f} "
                f"| {ev['parent_semantic_mass']:>13.4f} |"
            )
    else:
        lines.append("*No synth events recorded.*")
    lines.append("")

    # Observations placeholder
    lines.append("## Observations")
    lines.append("")

    # Find richest and most barren cosmologies
    if results["conditions"]:
        richest = max(results["conditions"], key=lambda c: c["final_metrics"].get("synthCount", 0))
        barren = min(results["conditions"], key=lambda c: c["final_metrics"].get("synthCount", 0))
        lines.append(f"- **Richest cosmology**: {richest['label']} — {richest['final_metrics'].get('synthCount',0)} synths, "
                      f"{richest['final_metrics'].get('starCount',0)} stars")
        lines.append(f"- **Most barren cosmology**: {barren['label']} — {barren['final_metrics'].get('synthCount',0)} synths, "
                      f"{barren['final_metrics'].get('starCount',0)} stars")

        # First-collapse analysis
        collapses = [(c["label"], c["first_collapse_tick"]) for c in results["conditions"] if c["first_collapse_tick"] is not None]
        if collapses:
            fastest = min(collapses, key=lambda x: x[1])
            slowest = max(collapses, key=lambda x: x[1])
            lines.append(f"- **Fastest collapse**: {fastest[0]} at tick {fastest[1]}")
            lines.append(f"- **Slowest collapse**: {slowest[0]} at tick {slowest[1]}")

        no_collapse = [c["label"] for c in results["conditions"] if c["first_collapse_tick"] is None]
        if no_collapse:
            lines.append(f"- **No collapse observed**: {', '.join(no_collapse)}")

    lines.append("")
    lines.append("## Exports")
    lines.append("- `jeans_cosmology_summary.csv` — one row per condition")
    lines.append("- `jeans_cosmology_trace.csv` — per-step metrics for all conditions")
    lines.append("- `jeans_cosmology_synth_log.csv` — synth birth event log")
    lines.append("- `jeans_cosmology_run_bundle.md` — this file")
    lines.append("")

    path = out_dir / "jeans_cosmology_run_bundle.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# =====================================================================
# CLI
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Jeans Cosmology Experiment — density → collapse → new structure"
    )
    parser.add_argument("--sweep", action="store_true",
                        help="Run full Jcrit × strategy sweep")
    parser.add_argument("--jcrit", type=float, nargs="+", default=None,
                        help="Jcrit values to test (default: 5,10,18,30,50)")
    parser.add_argument("--strategy", type=str, nargs="+", default=None,
                        choices=list(INJECTION_STRATEGIES.keys()),
                        help="Injection strategies to test")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS,
                        help=f"Steps per condition (default: {DEFAULT_STEPS})")
    parser.add_argument("--tractor-rate", type=float, default=0.05,
                        help="Tractor beam pull fraction per tick (default: 0.05)")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Output directory (default: data/jeans_cosmology/)")

    args = parser.parse_args()

    # Determine what to sweep
    if args.sweep:
        jcrits = args.jcrit or JCRIT_VALUES
        strats = args.strategy or list(INJECTION_STRATEGIES.keys())
    elif args.jcrit or args.strategy:
        jcrits = args.jcrit or [18.0]
        strats = args.strategy or ["blast"]
    else:
        # Default: full sweep
        jcrits = JCRIT_VALUES
        strats = list(INJECTION_STRATEGIES.keys())

    out_dir = Path(args.out_dir) if args.out_dir else _HERE / "data" / "jeans_cosmology"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = run_sweep(
        jcrit_values=jcrits,
        strategies=strats,
        steps=args.steps,
        tractor_rate=args.tractor_rate,
    )

    # Write outputs
    print("Writing outputs...")
    summary_path = write_summary_csv(results, out_dir)
    trace_path = write_trace_csv(results, out_dir)
    synth_path = write_synth_log(results, out_dir)
    bundle_path = write_run_bundle(results, out_dir)

    print(f"  Summary:    {summary_path}")
    print(f"  Trace:      {trace_path}")
    print(f"  Synth log:  {synth_path}")
    print(f"  Run bundle: {bundle_path}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
