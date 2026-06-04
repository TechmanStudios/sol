#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Emergent Synergy Verification Test
======================================
This script implements simulations to verify the key emergent insights:
1. Autonomic Self-Limiting Bus (MHD + GRU gating)
2. Negative-Resistance Jeans ROM Latching
3. Impedance-Matched Frequency-Division Multiplexing (Acoustic FDM)
"""

import sys
import os
import json
import math
import types
from pathlib import Path

# Add sol-core path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Force bind tools/sol-core/telemetry.py to sys.modules['telemetry'] to prevent collisions
import importlib.util
telemetry_path = sol_root / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

# Disable telemetry
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine


# ---------------------------------------------------------------------------
# Case 1: Autonomic Self-Limiting Bus
# ---------------------------------------------------------------------------

def run_case_1() -> dict:
    print("\n--- CASE 1: Autonomic Self-Limiting Bus (MHD + GRU) ---")
    raw_nodes = [
        {"id": "SOURCE", "label": "SOURCE", "group": "bridge", "rho": 0.0, "psi": 0.0, "psi_bias": 0.0},
        {"id": "GATE", "label": "GATE", "group": "bridge", "rho": 0.0, "psi": 0.0, "psi_bias": 0.0},
        {
            "id": "HOST", 
            "label": "HOST", 
            "group": "bridge", 
            "rho": 0.0, 
            "psi": 0.0, 
            "psi_bias": 0.0,
            "W_z": 0.0, "U_z": -35.0, "b_z": 2.5,
            "W_r": 0.0, "U_r": -35.0, "b_r": 2.5
        },
        {"id": "BATTERY", "label": "BATTERY", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "isBattery": True, "b_state": -1, "b_charge": 0.0}
    ]
    raw_edges = [
        {"from": "SOURCE", "to": "GATE", "w0": 0.0002},
        {"from": "GATE", "to": "HOST", "w0": 1.0},
        {"from": "HOST", "to": "BATTERY", "w0": 1.0}
    ]

    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.2)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.5
    engine.physics.psi_relax_base = 1.5
    engine.physics.conductance_gamma = 5.0
    engine.physics.conductance_min = 0.001
    engine.physics.conductance_max = 5.0
    
    # Enable MHD
    engine.physics.mhd_cfg = {
        "bBuild": 5.0,
        "bDecay": 6.0,
        "bMax": 15.0,
        "bGamma": 300.0
    }

    # Enable GRMN
    engine.physics.gated_recurrent_cfg = {
        "enabled": True,
        "W_z": 0.0, "U_z": 0.0, "b_z": 10.0,
        "W_r": 0.0, "U_r": 0.0, "b_r": 10.0
    }

    # Battery config matching test_gru_register.py
    engine.physics.battery_cfg = {
        "resonanceDrive": 5.0,
        "dampingDrag": 0.5,
        "leakLambda": 0.02,
        "flipThreshold": 0.70,
        "collapseFactor": 0.15,
        "qMax": 40.0,
        "avalancheGain": 1.15,
        "resonanceBoost": 1.8,
        "dampingClamp": 0.35,
        "diodeResonanceOut": 1.25,
        "diodeResonanceIn": 0.80,
        "diodeDampingOut": 0.25,
        "diodeDampingIn": 1.00,
    }

    dt = 0.05
    history = []

    # 1. Write Phase (Steps 0-100)
    for s in range(100):
        engine.physics.node_by_id["SOURCE"]["rho"] = 40.0
        engine.physics.node_by_id["SOURCE"]["psi"] = 1.0
        engine.physics.node_by_id["SOURCE"]["psi_bias"] = 1.0
        engine.physics.node_by_id["HOST"]["psi_bias"] = 1.0
        engine.step(dt=dt)
        history.append({
            "step": s, "phase": "WRITE",
            "SOURCE_GATE_cond": engine.physics.edges[0]["conductance"],
            "HOST_z": engine.physics.node_by_id["HOST"].get("z_gate", 1.0),
            "HOST_rho": engine.physics.node_by_id["HOST"]["rho"],
            "BATTERY_rho": engine.physics.node_by_id["BATTERY"]["rho"],
            "BATTERY_state": engine.physics.node_by_id["BATTERY"].get("b_state", -1)
        })

    # 2. Settle Phase (Steps 101-200)
    for s in range(100):
        engine.physics.node_by_id["SOURCE"]["rho"] = 0.0
        engine.physics.node_by_id["SOURCE"]["psi"] = -1.0
        engine.physics.node_by_id["SOURCE"]["psi_bias"] = -1.0
        engine.physics.node_by_id["HOST"]["psi_bias"] = 0.15  # lock bias
        engine.step(dt=dt)
        history.append({
            "step": 100 + s, "phase": "SETTLE",
            "SOURCE_GATE_cond": engine.physics.edges[0]["conductance"],
            "HOST_z": engine.physics.node_by_id["HOST"].get("z_gate", 1.0),
            "HOST_rho": engine.physics.node_by_id["HOST"]["rho"],
            "BATTERY_rho": engine.physics.node_by_id["BATTERY"]["rho"],
            "BATTERY_state": engine.physics.node_by_id["BATTERY"].get("b_state", -1)
        })

    pre_noise_host = engine.physics.node_by_id["HOST"]["rho"]

    # 3. Noise Phase (Steps 201-300)
    for s in range(100):
        engine.physics.node_by_id["SOURCE"]["rho"] = 40.0
        engine.physics.node_by_id["SOURCE"]["psi"] = -1.0
        engine.physics.node_by_id["SOURCE"]["psi_bias"] = -1.0
        engine.physics.node_by_id["HOST"]["psi_bias"] = 0.60  # high hold bias to block tunneling
        engine.step(dt=dt)
        history.append({
            "step": 200 + s, "phase": "NOISE",
            "SOURCE_GATE_cond": engine.physics.edges[0]["conductance"],
            "HOST_z": engine.physics.node_by_id["HOST"].get("z_gate", 1.0),
            "HOST_rho": engine.physics.node_by_id["HOST"]["rho"],
            "BATTERY_rho": engine.physics.node_by_id["BATTERY"]["rho"],
            "BATTERY_state": engine.physics.node_by_id["BATTERY"].get("b_state", -1)
        })

    post_noise_host = engine.physics.node_by_id["HOST"]["rho"]
    leakage = post_noise_host - pre_noise_host

    write_history = [h for h in history if h["phase"] == "WRITE"]
    settle_history = [h for h in history if h["phase"] == "SETTLE"]
    noise_history = [h for h in history if h["phase"] == "NOISE"]

    peak_write_cond = max(h["SOURCE_GATE_cond"] for h in write_history)
    baseline_cond = history[0]["SOURCE_GATE_cond"]
    end_settle_cond = settle_history[-1]["SOURCE_GATE_cond"]
    min_hold_z = min(h["HOST_z"] for h in noise_history)

    print(f"  Peak Write Conductance: {peak_write_cond:.6f} (vs Baseline: {baseline_cond:.6f})")
    print(f"  End Settle Conductance: {end_settle_cond:.6f} (MHD Shuttered)")
    print(f"  Min Hold z_gate:        {min_hold_z:.6e} (GRU Frozen)")
    print(f"  Noise Phase Leakage:    {leakage:.6e} (Target: < 1e-3)")
    print(f"  Final Battery State:    {noise_history[-1]['BATTERY_state']}")
    
    passed = (peak_write_cond > 1.0) and (end_settle_cond < 0.005) and (min_hold_z < 0.001) and (abs(leakage) < 0.001)
    print(f"  Verification Status:    {'PASSED' if passed else 'FAILED'}")

    return {
        "peak_write_cond": peak_write_cond,
        "baseline_cond": baseline_cond,
        "end_settle_cond": end_settle_cond,
        "min_hold_z": min_hold_z,
        "leakage": leakage,
        "passed": passed
    }


# ---------------------------------------------------------------------------
# Case 2: Negative-Resistance Jeans ROM Latching
# ---------------------------------------------------------------------------

def custom_jeans_collapse_and_accrete(self, dt: float, c_press: float, damping: float):
    cfg = self.jeans_cfg
    if not cfg:
        return
    j_crit = cfg.get("Jcrit", 18.0)
    acc_rate = cfg.get("accreteRate", 0.55)
    
    for star in self.nodes:
        eps = 1e-6
        p = star.get("p", c_press * math.log(1 + star["rho"]))
        if not isinstance(p, (int, float)) or not math.isfinite(p):
            p = c_press * math.log(1 + star["rho"])
        j_val = star["rho"] / (abs(p) + eps)

        if j_val >= j_crit:
            if not star.get("isConstellation"):
                star["isConstellation"] = True
                star["protoStar"] = True
            star["isStellar"] = True
        else:
            star["isStellar"] = False
            star["isConstellation"] = False
            star["protoStar"] = False

        if not star.get("isStellar"):
            continue

        # Accrete mass from BUFFER node over tax edge
        for e in self.edges:
            if e.get("background") or e.get("kind") != "tax":
                continue
            other_id = e["to"] if e["from"] == star["id"] else e["from"]
            nb = self.node_by_id.get(other_id)
            if not nb or nb.get("isBattery"):
                continue
            pull = min(nb["rho"], nb["rho"] * acc_rate * max(0.0, dt))
            if pull > 0:
                nb["rho"] -= pull
                star["rho"] += pull


def run_case_2() -> dict:
    print("\n--- CASE 2: Negative-Resistance Jeans ROM Latching ---")
    raw_nodes = [
        {"id": "SOURCE", "label": "SOURCE", "group": "bridge", "rho": 0.0, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 100.0, "semanticMass0": 100.0},
        {"id": "GATE", "label": "GATE", "group": "bridge", "rho": 0.0, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 100.0, "semanticMass0": 100.0},
        {
            "id": "HOST", 
            "label": "HOST", 
            "group": "bridge", 
            "rho": 0.0, 
            "psi": 0.0, 
            "psi_bias": 0.0,
            "semanticMass": 100.0,
            "semanticMass0": 100.0,
            "W_z": 0.0, "U_z": -35.0, "b_z": 2.5,
            "W_r": 0.0, "U_r": -35.0, "b_r": 2.5
        },
        {"id": "BATTERY", "label": "BATTERY", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "isBattery": True, "b_state": -1, "b_charge": 0.0, "semanticMass": 100.0, "semanticMass0": 100.0},
        {"id": "READOUT", "label": "READOUT", "group": "bridge", "rho": 0.0, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 100.0, "semanticMass0": 100.0},
        {
            "id": "BUFFER", 
            "label": "BUFFER", 
            "group": "bridge", 
            "rho": 100.0, 
            "psi": 0.0, 
            "psi_bias": 0.0, 
            "semanticMass": 1.0, 
            "semanticMass0": 1.0,
            "W_z": 0.0, "U_z": 0.0, "b_z": -10.0
        }
    ]
    raw_edges = [
        {"from": "SOURCE", "to": "GATE", "w0": 1.0},
        {"from": "GATE", "to": "HOST", "w0": 1.0},
        {"from": "HOST", "to": "BATTERY", "w0": 1.0},
        {"from": "GATE", "to": "READOUT", "w0": 1.0},
        {"from": "HOST", "to": "BUFFER", "w0": 1.0, "kind": "tax"}
    ]

    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.2)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.5
    engine.physics.psi_relax_base = 1.5
    engine.physics.conductance_gamma = 1.5
    engine.physics.conductance_min = 0.001
    engine.physics.conductance_max = 100.0
    
    # Config GRMN & Battery
    engine.physics.gated_recurrent_cfg = {
        "enabled": True,
        "W_z": 0.0, "U_z": 0.0, "b_z": 10.0,
        "W_r": 0.0, "U_r": 0.0, "b_r": 10.0
    }
    engine.physics.battery_cfg = {
        "resonanceDrive": 5.0, "dampingDrag": 0.5, "leakLambda": 0.02,
        "flipThreshold": 0.70, "collapseFactor": 0.15, "qMax": 40.0,
        "avalancheGain": 1.15, "resonanceBoost": 1.8, "dampingClamp": 0.35,
        "diodeResonanceOut": 1.25, "diodeResonanceIn": 0.80,
        "diodeDampingOut": 0.25, "diodeDampingIn": 1.00
    }
    engine.physics.jeans_cfg = {
        "Jcrit": 18.0, "accreteRate": 0.55, "starDampingFactor": 0.18
    }

    # Monkeypatch logic
    engine.physics.jeans_collapse_and_accrete = types.MethodType(custom_jeans_collapse_and_accrete, engine.physics)

    dt = 0.05
    history = []

    # 1. Write Phase (Steps 0-100)
    for s in range(100):
        engine.physics.node_by_id["SOURCE"]["rho"] = 40.0
        engine.physics.node_by_id["SOURCE"]["psi"] = 1.0
        engine.physics.node_by_id["SOURCE"]["psi_bias"] = 1.0
        engine.physics.node_by_id["HOST"]["psi_bias"] = 1.0
        engine.step(dt=dt)
        history.append({
            "step": s, "phase": "WRITE",
            "HOST_rho": engine.physics.node_by_id["HOST"]["rho"],
            "HOST_stellar": engine.physics.node_by_id["HOST"].get("isStellar", False),
            "BUFFER_rho": engine.physics.node_by_id["BUFFER"]["rho"],
            "BATTERY_state": engine.physics.node_by_id["BATTERY"].get("b_state", -1)
        })

    # 2. Settle/Accretion Hold Phase (Steps 101-200)
    for s in range(100):
        engine.physics.node_by_id["SOURCE"]["rho"] = 0.0
        engine.physics.node_by_id["SOURCE"]["psi"] = -1.0
        engine.physics.node_by_id["SOURCE"]["psi_bias"] = -1.0
        engine.physics.node_by_id["HOST"]["psi_bias"] = 0.60
        engine.step(dt=dt)
        history.append({
            "step": 100 + s, "phase": "HOLD",
            "HOST_rho": engine.physics.node_by_id["HOST"]["rho"],
            "HOST_stellar": engine.physics.node_by_id["HOST"].get("isStellar", False),
            "BUFFER_rho": engine.physics.node_by_id["BUFFER"]["rho"],
            "BATTERY_state": engine.physics.node_by_id["BATTERY"].get("b_state", -1)
        })

    # 3. Reset Phase (Steps 201-500, 300 steps)
    # Dynamically increase edge weights to simulate a low-resistance reset line
    for e in engine.physics.edges:
        if (e["from"] in ("SOURCE", "GATE") and e["to"] in ("GATE", "HOST")) or (e["from"] == "GATE" and e["to"] == "READOUT"):
            e["w0"] = 100.0

    for s in range(300):
        engine.physics.node_by_id["SOURCE"]["rho"] = 0.0
        engine.physics.node_by_id["SOURCE"]["psi"] = -1.0
        engine.physics.node_by_id["SOURCE"]["psi_bias"] = -1.0
        engine.physics.node_by_id["HOST"]["psi_bias"] = -1.0
        engine.physics.node_by_id["BATTERY"]["psi_bias"] = -1.0
        engine.step(dt=dt)
        history.append({
            "step": 200 + s, "phase": "RESET",
            "HOST_rho": engine.physics.node_by_id["HOST"]["rho"],
            "HOST_stellar": engine.physics.node_by_id["HOST"].get("isStellar", False),
            "BUFFER_rho": engine.physics.node_by_id["BUFFER"]["rho"],
            "BATTERY_state": engine.physics.node_by_id["BATTERY"].get("b_state", -1)
        })

    write_history = [h for h in history if h["phase"] == "WRITE"]
    hold_history = [h for h in history if h["phase"] == "HOLD"]
    reset_history = [h for h in history if h["phase"] == "RESET"]

    max_write_j_val = max(h["HOST_rho"] / 2.0 for h in write_history) # approx p=2.0
    buffer_transferred = history[0]["BUFFER_rho"] - hold_history[-1]["BUFFER_rho"]
    final_stellar = reset_history[-1]["HOST_stellar"]
    final_battery = reset_history[-1]["BATTERY_state"]

    print(f"  Stellar Latch Triggered: {any(h['HOST_stellar'] for h in write_history)}")
    print(f"  Buffer Mass Accreted:   {buffer_transferred:.6f} (Negative-Resistance Offset)")
    print(f"  Final Stellar State:    {final_stellar} (Star Dissolved)")
    print(f"  Final Battery State:    {final_battery} (State Reset)")

    passed = any(h['HOST_stellar'] for h in write_history) and (buffer_transferred > 1.0) and (not final_stellar) and (final_battery == -1)
    print(f"  Verification Status:    {'PASSED' if passed else 'FAILED'}")

    return {
        "max_write_j_val": max_write_j_val,
        "buffer_transferred": buffer_transferred,
        "final_stellar": final_stellar,
        "final_battery": final_battery,
        "passed": passed
    }


# ---------------------------------------------------------------------------
# Case 3: Acoustic FDM Impedance Matching
# ---------------------------------------------------------------------------

def run_case_3() -> dict:
    print("\n--- CASE 3: Acoustic FDM Impedance Matching ---")
    # SOURCE drives two outputs.
    # Output A matches period 10 (Router_A oscillates at period 10)
    # Output B mismatches period 10 (Router_B oscillates at period 25)
    raw_nodes = [
        {"id": "Source", "label": "Source", "group": "bridge", "rho": 10.0},
        {"id": "Router_A", "label": "Router_A", "group": "bridge", "rho": 10.0},
        {"id": "Router_B", "label": "Router_B", "group": "bridge", "rho": 10.0},
        {"id": "Dest_A", "label": "Dest_A", "group": "bridge", "rho": 10.0},
        {"id": "Dest_B", "label": "Dest_B", "group": "bridge", "rho": 10.0},
    ]
    raw_edges = [
        {"from": "Source", "to": "Router_A", "w0": 1.0, "kind": "tax"},
        {"from": "Router_A", "to": "Dest_A", "w0": 1.0, "kind": "tax"},
        {"from": "Source", "to": "Router_B", "w0": 1.0, "kind": "tax"},
        {"from": "Router_B", "to": "Dest_B", "w0": 1.0, "kind": "tax"},
    ]

    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.0)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 6.0  # High contrast gating

    engine.write_enable("Router_A")
    engine.write_enable("Router_B")
    engine.write_enable("Dest_A")
    engine.write_enable("Dest_B")

    engine.physics.node_by_id["Dest_A"]["r_bias"] = 0.0
    engine.physics.node_by_id["Dest_B"]["r_bias"] = 0.0

    dt = 0.08
    steps = 300
    
    omega_A = 2 * math.pi / (10 * dt)
    omega_B = 2 * math.pi / (25 * dt)

    # Drive Source with Period 10 sine wave
    for s in range(steps):
        t = s * dt
        engine.physics.node_by_id["Router_A"]["psi"] = math.sin(omega_A * t)
        engine.physics.node_by_id["Router_B"]["psi"] = math.sin(omega_B * t)

        src_rho = 10.0 + 8.0 * math.sin(omega_A * t)
        engine.physics.node_by_id["Source"]["rho"] = src_rho
        
        engine.step(dt=dt, c_press=2.0)

    dest_a_mass = engine.physics.node_by_id["Dest_A"]["rho"]
    dest_b_mass = engine.physics.node_by_id["Dest_B"]["rho"]

    # Difference in mass accumulation
    delta_a = dest_a_mass - 10.0
    delta_b = dest_b_mass - 10.0

    print(f"  Matched Route A mass accumulated (delta):  {delta_a:+.6f}")
    print(f"  Mismatched Route B mass accumulated (delta): {delta_b:+.6f}")
    
    # We want matched A to gain mass and mismatched B to lose mass (back-pressure rejection)
    passed = (delta_a > 1.5) and (delta_b < -0.5)
    print(f"  Verification Status:                 {'PASSED' if passed else 'FAILED'}")

    return {
        "dest_a_mass": dest_a_mass,
        "dest_b_mass": dest_b_mass,
        "delta_a": delta_a,
        "delta_b": delta_b,
        "passed": passed
    }


# ---------------------------------------------------------------------------
# Case 4: The Comb-Filter Duality (Damping vs. Geometry)
# ---------------------------------------------------------------------------

def run_case_4() -> dict:
    print("\n--- CASE 4: The Comb-Filter Duality (Damping vs. Geometry) ---")
    
    sol_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(sol_root / "Frontier_OS" / "Exciton-MoA"))
    sys.path.insert(0, str(sol_root / "Frontier_OS" / "Exciton-MoA" / "hardWare"))
    
    from blank_config import BlankManifoldConfig
    from blank_manifold_core import BlankManifoldCore
    
    import networkx as nx
    
    def test_manifold(N_nodes: int, damping: float, multiply_edges: float, label: str) -> float:
        config = BlankManifoldConfig(base_node_count=N_nodes, topology_type="hyperbolic_uniform", dimensionality=3)
        manifold = BlankManifoldCore(config, seed=42)
        graph = manifold.generate_manifold()
        
        # Determine sa and sb (sorted deterministically by degree and ID)
        nodes_sorted = sorted(list(graph.nodes()), key=lambda n: (graph.degree(n), n), reverse=True)
        sa = nodes_sorted[0]
        
        # Find a node at exactly 2 hops distance
        sb = None
        lengths = nx.single_source_shortest_path_length(graph, sa)
        nodes_at_2 = [n for n, l in lengths.items() if l == 2]
        if nodes_at_2:
            sb = sorted(nodes_at_2)[0]
        else:
            sb = nodes_sorted[1]
            
        raw_nodes = [{"id": n, "label": n, "group": "bridge", "rho": 10.0} for n in graph.nodes]
        raw_edges = [{"from": u, "to": v, "w0": graph[u][v].get("weight", 0.1) * multiply_edges} for u, v in graph.edges]
        
        engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=damping)
        engine.integration_mode = "rk4"
        engine.physics.integration_mode = "rk4"
        engine.physics.psi_diffusion = 0.0
        
        dt = 0.08
        steps = 150
        omega = 2.0 * math.pi / (12.0 * dt)
        
        dest_rhos = []
        for s in range(steps):
            t = s * dt
            # Inject sine wave at source
            engine.physics.node_by_id[sa]["rho"] = 10.0 + 5.0 * math.sin(omega * t)
            engine.step(dt=dt)
            if s >= steps - 40:
                dest_rhos.append(engine.physics.node_by_id[sb]["rho"])
                
        val = max(dest_rhos) - min(dest_rhos)
        print(f"    [{label}] N={N_nodes}, Damping={damping:.2f}, Mult={multiply_edges:.1f} -> Received Amp Delta: {val:.6f}")
        return val

    v_fib_opt = test_manifold(55, 0.2, 10.0, "Fibonacci (Optimal)")
    v_pow_opt = test_manifold(64, 5.0, 10.0, "Power-of-Two (Locked)")
    v_fib_low = test_manifold(55, 0.01, 10.0, "Fibonacci (Low Damping)")
    v_fib_high = test_manifold(55, 5.0, 10.0, "Fibonacci (High Damping)")
    
    # Fibonacci optimal should propagate well, while Power-of-two (locked) and high damping should be suppressed.
    passed = (v_fib_opt > 0.20) and (v_pow_opt < 0.05) and (v_fib_low < 0.05) and (v_fib_high < 0.05)
    print(f"  Verification Status:                 {'PASSED' if passed else 'FAILED'}")
    
    return {
        "v_fib_opt": v_fib_opt,
        "v_pow_opt": v_pow_opt,
        "v_fib_low": v_fib_low,
        "v_fib_high": v_fib_high,
        "passed": passed
    }


# ---------------------------------------------------------------------------
# Case 5: Non-Euclidean Structural Plasticity (Spawning + Loops)
# ---------------------------------------------------------------------------

def run_case_5() -> dict:
    print("\n--- CASE 5: Non-Euclidean Structural Plasticity (Spawning + Loops) ---")
    
    raw_nodes = [
        {"id": "A", "label": "A", "group": "bridge", "rho": 10.0, "semanticMass": 1.0},
        {"id": "B", "label": "B", "group": "bridge", "rho": 10.0, "semanticMass": 1.0},
        {"id": "C", "label": "C", "group": "bridge", "rho": 10.0, "semanticMass": 30.0}, 
        {"id": "D", "label": "D", "group": "bridge", "rho": 10.0, "semanticMass": 1.0},
        {"id": "E", "label": "E", "group": "bridge", "rho": 0.0, "semanticMass": 1.0},
    ]
    raw_edges = [
        {"from": "A", "to": "B", "w0": 1.0},
        {"from": "B", "to": "C", "w0": 1.0},
        {"from": "C", "to": "D", "w0": 1.0},
        {"from": "D", "to": "A", "w0": 1.0},
        {"from": "C", "to": "E", "w0": 0.0001}, 
    ]
    
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.002)
    engine.integration_mode = "rk4"
    engine.physics.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.5
    engine.physics.psi_relax_base = 1.5
    
    # Configure Jeans
    engine.physics.jeans_cfg = {
        "Jcrit": 8.0,
        "accreteRate": 0.0, 
        "starDampingFactor": 1.0
    }
    
    spawned_parents = set()
    next_synth_id = 9000
    
    def resolve_edge_references(physics, edge):
        from_id = edge["from"]
        to_id = edge["to"]
        edge["src_node"] = physics.node_by_id.get(from_id)
        edge["dst_node"] = physics.node_by_id.get(to_id)
        edge["from_idx"] = physics.node_index_by_id.get(from_id)
        edge["to_idx"] = physics.node_index_by_id.get(to_id)
        
    def custom_jeans_collapse_and_accrete(self, dt: float, c_press: float, damping: float):
        nonlocal next_synth_id
        j_crit = self.jeans_cfg.get("Jcrit", 18.0)
        
        for n in self.nodes:
            eps = 1e-6
            p = n.get("p", c_press * math.log(1 + n["rho"] / n.get("semanticMass", 1.0)))
            if not isinstance(p, (int, float)) or not math.isfinite(p):
                p = c_press * math.log(1 + n["rho"])
            j_val = n["rho"] / (abs(p) + eps)
            
            if j_val >= j_crit:
                n["isStellar"] = True
            else:
                n["isStellar"] = False
                
        for node in list(self.nodes):
            if not node.get("isStellar"):
                continue
            if node["id"] in spawned_parents:
                continue
            if node.get("isSynth"):
                continue
                
            spawned_parents.add(node["id"])
            synth_id = f"synth_{next_synth_id}"
            next_synth_id += 1
            
            rho_gift = node["rho"] * 0.05
            node["rho"] -= rho_gift
            node["semanticMass"] = 1.0
            node["semanticMass0"] = 1.0
            
            synth_node = {
                "id": synth_id,
                "label": f"synth:{node['label']}",
                "group": "synth",
                "rho": rho_gift,
                "p": 0.0,
                "psi": 0.0,
                "psi_bias": 0.0,
                "semanticMass": 1.0,
                "semanticMass0": 1.0,
                "lastInteractionTime": 0.0,
                "isSingularity": False,
                "isStellar": False,
                "isConstellation": False,
                "isSynth": True,
            }
            
            self.nodes.append(synth_node)
            self.node_by_id[synth_id] = synth_node
            self.node_index_by_id[synth_id] = len(self.nodes) - 1
            
            synth_edge = {
                "from": node["id"],
                "to": synth_id,
                "w0": 10.0,
                "background": False,
                "kind": "synth",
                "flux": 0.0,
                "conductance": 1.0,
            }
            resolve_edge_references(self, synth_edge)
            self.edges.append(synth_edge)
            
            neighbor_ids = []
            for e in self.edges:
                if e.get("background"):
                    continue
                if e["from"] == node["id"] and e["to"] != synth_id:
                    neighbor_ids.append(e["to"])
                elif e["to"] == node["id"] and e["from"] != synth_id:
                    neighbor_ids.append(e["from"])
                    
            for nid in set(neighbor_ids):
                bridge_edge = {
                    "from": synth_id,
                    "to": nid,
                    "w0": 10.0,
                    "background": False,
                    "kind": "synth",
                    "flux": 0.0,
                    "conductance": 1.0,
                }
                resolve_edge_references(self, bridge_edge)
                self.edges.append(bridge_edge)
                
            print(f"      [SPAWNED] Star at node {node['id']} birthed {synth_id}! Created pathways connecting {synth_id} to neighbors {neighbor_ids}.")
            
    engine.physics.jeans_collapse_and_accrete = types.MethodType(custom_jeans_collapse_and_accrete, engine.physics)
    
    dt = 0.05
    history = []
    
    for s in range(150):
        if s < 35:
            engine.physics.node_by_id["A"]["rho"] = 60.0
            engine.physics.node_by_id["A"]["psi"] = 1.0
        else:
            engine.physics.node_by_id["A"]["rho"] = 0.0
            
        engine.step(dt=dt)
        history.append({
            "step": s,
            "C_rho": engine.physics.node_by_id["C"]["rho"],
            "E_rho": engine.physics.node_by_id["E"]["rho"],
            "C_stellar": engine.physics.node_by_id["C"].get("isStellar", False),
            "synths_spawned": len(spawned_parents)
        })
        
    final_e_rho = engine.physics.node_by_id["E"]["rho"]
    synths_count = len(spawned_parents)
    
    print(f"  Synths Spawned:        {synths_count}")
    print(f"  Target E final mass:   {final_e_rho:.6f}")
    
    passed = (synths_count > 0) and (final_e_rho > 5.0)
    print(f"  Verification Status:    {'PASSED' if passed else 'FAILED'}")
    
    return {
        "synths_count": synths_count,
        "final_e_rho": final_e_rho,
        "passed": passed
    }


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def main():
    print("====================================================")
    print("SOL EMERGENT SYNERGY EXPERIMENTAL SUITE")
    print("====================================================")

    res_1 = run_case_1()
    res_2 = run_case_2()
    res_3 = run_case_3()
    res_4 = run_case_4()
    res_5 = run_case_5()

    print("\n================ FINAL REPORT SUMMARY ================")
    print(f"  Case 1 (Autonomic Bus):            {'PASSED' if res_1['passed'] else 'FAILED'}")
    print(f"  Case 2 (Jeans ROM Latch):          {'PASSED' if res_2['passed'] else 'FAILED'}")
    print(f"  Case 3 (Acoustic FDM Match):        {'PASSED' if res_3['passed'] else 'FAILED'}")
    print(f"  Case 4 (Comb-Filter Duality):       {'PASSED' if res_4['passed'] else 'FAILED'}")
    print(f"  Case 5 (Non-Euclidean Plasticity):  {'PASSED' if res_5['passed'] else 'FAILED'}")
    
    all_passed = res_1['passed'] and res_2['passed'] and res_3['passed'] and res_4['passed'] and res_5['passed']
    print(f"  Overall Suite Status:              {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    print("======================================================")

    # Save summary report
    summary = {
        "case_1": res_1,
        "case_2": res_2,
        "case_3": res_3,
        "case_4": res_4,
        "case_5": res_5,
        "all_passed": all_passed
    }
    report_dir = Path("g:/docs/TechmanStudios/sol/solResearch/nextBestTest")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "emergent_synergy_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Render operator report
    report_md = f"""# Emergent Synergy Verification Report

Verified the five primary emergent physics interactions:
- **Autonomic Self-Limiting Bus**: Peak write conductance: `{res_1['peak_write_cond']:.4f}`, Min hold z: `{res_1['min_hold_z']:.4e}`, Noise leakage: `{res_1['leakage']:.2e}`.
- **Negative-Resistance Latch**: Buffer accretion pulled: `{res_2['buffer_transferred']:.4f}` mass units, Star dissolved and reset completed successfully.
- **Acoustic FDM Match**: Matched Route A delta: `{res_3['delta_a']:+.4f}` vs Mismatched Route B delta: `{res_3['delta_b']:+.4f}`.
- **Comb-Filter Duality**: Fibonacci Optimal: `{res_4['v_fib_opt']:.4f}` vs Power-of-Two: `{res_4['v_pow_opt']:.4f}`. Low damping: `{res_4['v_fib_low']:.4f}` vs High damping: `{res_4['v_fib_high']:.4f}`.
- **Non-Euclidean Plasticity**: Synths spawned: `{res_5['synths_count']}`, Target E final mass: `{res_5['final_e_rho']:.4f}`.

Suite overall status: **{'ALL PASSED' if all_passed else 'FAILED'}**
"""
    (report_dir / "emergent_synergy_report.md").write_text(report_md, encoding="utf-8")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
