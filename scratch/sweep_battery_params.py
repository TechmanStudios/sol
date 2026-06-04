#!/usr/bin/env python3
import sys
import os
import math
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent

import importlib.util
telemetry_path = _SOL_ROOT / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "hardWare"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "firmWare" / "ExcitonEngine"))

from test_insulated_battery_latch import compile_hierarchical_manifold, analyze_latch_metrics
from sol_engine import SOLEngine

def run_simulation_custom(nodes_all, edges_all, sa_p, sb_p, mixer_p, sa_c, sb_c, mixer_c,
                          battery_node_id, damping, freq, amp, dt, steps, battery_cfg):
    nodes_cloned = [dict(n) for n in nodes_all]
    
    # Initialize psi of parent nodes to 1.0, child nodes to -1.0
    for n in nodes_cloned:
        if n["id"].startswith("parent_"):
            n["psi_bias"] = 1.0
            n["psi"] = 1.0
        else:
            n["psi_bias"] = -1.0
            n["psi"] = -1.0
            
    if battery_node_id:
        for n in nodes_cloned:
            if n["id"] == battery_node_id:
                n["isBattery"] = True
                n["b_state"] = -1
                n["b_charge"] = 0.0
                n["psi_bias"] = -1.0
                n["psi"] = -1.0
                
    engine = SOLEngine.from_graph(nodes_cloned, edges_all, c_press=2.0, damping=damping)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 0.0
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.6
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None
    engine.physics.jeans_cfg = None
    engine.physics.vort_cfg = None
    
    if battery_node_id:
        engine.physics.battery_cfg = battery_cfg
        
    engine.save_baseline()
    omega_drive = 2.0 * math.pi / (24.0 * dt)
    mixer_p_rhos = []
    mixer_c_rhos = []
    
    for s in range(steps):
        t = s * dt
        if s == 100:
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and edge["to"] == sa_c:
                    edge["w0"] = 0.001
        if s == 200:
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and edge["to"] == sa_c:
                    edge["w0"] = 156.25
                    
        if s <= 100:
            engine.physics.node_by_id[sa_p]["rho"] = 10.0 + 0.1 * math.sin(omega_drive * t + 0.26)
            engine.physics.node_by_id[sb_p]["rho"] = 10.0 + 0.1 * math.sin(omega_drive * t + 0.26)
            
            t0 = 3.0
            sigma = 1.5
            envelope = math.exp(-((t - t0) ** 2) / (2.0 * sigma ** 2))
            soliton_val = amp * math.sin(freq * t) * envelope
            engine.physics.node_by_id[sb_c]["rho"] = 10.0 + soliton_val
            engine.physics.node_by_id[sb_c]["psi"] = 1.0
            
        engine.step(dt=dt)
        mixer_p_rhos.append(engine.physics.node_by_id[mixer_p]["rho"])
        mixer_c_rhos.append(engine.physics.node_by_id[mixer_c]["rho"])
        
    return mixer_p_rhos, mixer_c_rhos

def main():
    nodes_p, edges_p, sa_p, sb_p, mixer_p = compile_hierarchical_manifold("parent", 64, 42)
    nodes_c, edges_c, sa_c, sb_c, mixer_c = compile_hierarchical_manifold("child", 32, 149)
    
    battery_node_id = "child_node_0000"
    # Use 10.0 coupling to avoid instant flip
    edges_c.append({"from": mixer_c, "to": battery_node_id, "w0": 10.0, "kind": "tax"})
    
    wormhole_edges = [{"from": mixer_p, "to": sa_c, "w0": 156.25, "kind": "tax"}]
    nodes_all = nodes_p + nodes_c
    edges_all = edges_p + edges_c + wormhole_edges
    
    dt = 0.08
    steps = 350
    damping = 0.01
    freq = 3.2725
    amp = 3.0
    
    # Baseline Case A
    p_rhos_a, c_rhos_a = run_simulation_custom(
        nodes_all, edges_all, sa_p, sb_p, mixer_p, sa_c, sb_c, mixer_c,
        None, damping, freq, amp, dt, steps, None
    )
    metrics_a = analyze_latch_metrics(p_rhos_a, c_rhos_a)
    print(f"Case A (Passive) | write_amp={metrics_a['write_amp']:.4f} | recalled_amp={metrics_a['recalled_amp']:.4f} | transfer_eff={metrics_a['transfer_efficiency']*100:.2f}%\n")
    
    # Sweep
    best_boost = 0.0
    best_params = {}
    
    # Sweep parameters
    for qMax in [10.0, 30.0, 60.0]:
        for avalancheGain in [1.0, 3.0, 6.0]:
            for resonanceBoost in [1.5, 4.0, 8.0]:
                for dampingClamp in [0.05, 0.15, 0.35]:
                    cfg = {
                        "qMax": qMax,
                        "qThresh": 5.0,
                        "leakLambda": 0.02,
                        "avalancheGain": avalancheGain,
                        "resonanceBoost": resonanceBoost,
                        "dampingClamp": dampingClamp,
                        "flipThreshold": 0.65,
                        "collapseFactor": 0.10,
                        "resonanceDrive": 2.5,
                        "dampingDrag": 0.2,
                        "diodeResonanceOut": 1.25,
                        "diodeResonanceIn": 0.80,
                        "diodeDampingOut": 0.25,
                        "diodeDampingIn": 1.00
                    }
                    p_rhos_b, c_rhos_b = run_simulation_custom(
                        nodes_all, edges_all, sa_p, sb_p, mixer_p, sa_c, sb_c, mixer_c,
                        battery_node_id, damping, freq, amp, dt, steps, cfg
                    )
                    metrics_b = analyze_latch_metrics(p_rhos_b, c_rhos_b)
                    
                    boost = metrics_b['recalled_amp'] / max(1e-6, metrics_a['recalled_amp'])
                    eff_boost = metrics_b['transfer_efficiency'] / max(1e-6, metrics_a['transfer_efficiency'])
                    
                    if boost > best_boost:
                        best_boost = boost
                        best_params = {
                            "qMax": qMax,
                            "avalancheGain": avalancheGain,
                            "resonanceBoost": resonanceBoost,
                            "dampingClamp": dampingClamp,
                            "recalled_amp": metrics_b['recalled_amp'],
                            "write_amp": metrics_b['write_amp'],
                            "transfer_eff": metrics_b['transfer_efficiency'],
                            "retention": metrics_b['retention_ratio']
                        }
                    
                    print(f"Sweep | qMax={qMax} avgGain={avalancheGain} resBoost={resonanceBoost} dampClamp={dampingClamp} | recalled={metrics_b['recalled_amp']:.4f} (boost={boost:.2f}x) | write={metrics_b['write_amp']:.4f} | transfer={metrics_b['transfer_efficiency']*100:.2f}% | retention={metrics_b['retention_ratio']*100:.2f}%")
                    
    print("\n==================================================")
    print("BEST PARAMETERS FOUND:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"  Best Recall Amplitude Boost: {best_boost:.2f}x")
    print("==================================================")

if __name__ == "__main__":
    main()
