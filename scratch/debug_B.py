#!/usr/bin/env python3
import sys
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SOL_ROOT / "scratch"))
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "hardWare"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "firmWare" / "ExcitonEngine"))

from test_insulated_battery_latch import compile_hierarchical_manifold
from sweep_battery_params import run_simulation_custom
from sol_engine import SOLEngine

def main():
    nodes_p, edges_p, sa_p, sb_p, mixer_p = compile_hierarchical_manifold('parent', 64, 42)
    nodes_cA, edges_cA, sa_cA, sb_cA, mixer_cA = compile_hierarchical_manifold('childA', 32, 149)
    nodes_cB, edges_cB, sa_cB, sb_cB, mixer_cB = compile_hierarchical_manifold('childB', 32, 200)
    
    batteryA_id = "childA_node_0000"
    batteryB_id = "childB_node_0000"
    
    edges_cA.append({"from": mixer_cA, "to": batteryA_id, "w0": 10.0, "kind": "tax"})
    edges_cB.append({"from": mixer_cB, "to": batteryB_id, "w0": 10.0, "kind": "tax"})
    
    wormhole_A = [{"from": mixer_p, "to": sa_cA, "w0": 156.25, "kind": "tax"}]
    wormhole_B = [{"from": mixer_p, "to": sa_cB, "w0": 156.25, "kind": "tax"}]
    
    nodes_all = nodes_p + nodes_cA + nodes_cB
    edges_all = edges_p + edges_cA + edges_cB + wormhole_A + wormhole_B
    
    # Run the same Trial B setup
    keys = (sa_p, sb_p, mixer_p, sa_cA, sb_cA, mixer_cA, sa_cB, sb_cB, mixer_cB, batteryA_id, batteryB_id)
    
    # Let's run a manual simulation loop to inspect the psi value of childB nodes
    nodes_cloned = [dict(n) for n in nodes_all]
    for n in nodes_cloned:
        if n["id"].startswith("parent_"):
            n["psi_bias"] = 1.0
            n["psi"] = 1.0
        else:
            n["psi_bias"] = -0.05
            n["psi"] = -0.05
            
    for n in nodes_cloned:
        if n["id"] == batteryA_id or n["id"] == batteryB_id:
            n["isBattery"] = True
            n["b_state"] = -1
            n["b_charge"] = 0.0
            n["psi_bias"] = -0.05
            n["psi"] = -0.05
            
    battery_cfg = {
        "qMax": 60.0,
        "qThresh": 5.0,
        "leakLambda": 0.02,
        "avalancheGain": 6.0,
        "resonanceBoost": 8.0,
        "dampingClamp": 0.05,
        "flipThreshold": 0.65,
        "collapseFactor": 0.10,
        "resonanceDrive": 2.5,
        "dampingDrag": 0.2,
        "diodeResonanceOut": 1.25,
        "diodeResonanceIn": 0.80,
        "diodeDampingOut": 0.25,
        "diodeDampingIn": 1.00
    }
    
    engine = SOLEngine.from_graph(nodes_cloned, edges_all, c_press=2.0, damping=0.01)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 0.0
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 1.2
    engine.physics.conductance_gamma = 1.0
    engine.physics.battery_cfg = battery_cfg
    
    dt = 0.08
    freqB = 6.0
    amp = 3.0
    
    for s in range(100):
        t = s * dt
        # Write B only: Wormhole B open, A closed
        for edge in engine.physics.edges:
            if edge["from"] == mixer_p and edge["to"] == sa_cA:
                edge["w0"] = 0.001
            if edge["from"] == mixer_p and edge["to"] == sa_cB:
                edge["w0"] = 156.25
                
        engine.physics.node_by_id[sa_p]["rho"] = 10.0 + 0.1 * math.sin(t)
        engine.physics.node_by_id[sb_p]["rho"] = 10.0 + 0.1 * math.sin(t)
        
        t0 = 3.0
        sigma = 1.5
        envelope = math.exp(-((t - t0) ** 2) / (2.0 * sigma ** 2))
        soliton_val = amp * math.sin(freqB * t) * envelope
        engine.physics.node_by_id[sb_cB]["rho"] = 10.0 + soliton_val
        engine.physics.node_by_id[sb_cB]["psi"] = 1.0
        
        engine.step(dt=dt)
        
        b = engine.physics.node_by_id[batteryB_id]
        mixer_B = engine.physics.node_by_id[mixer_cB]
        sa_B = engine.physics.node_by_id[sa_cB]
        if s % 10 == 0:
            print(f"step {s:03d} | charge={b['b_charge']:.4f} | state={b['b_state']} | mixer_B_psi={mixer_B['psi']:.4f} | sb_cB_psi={engine.physics.node_by_id[sb_cB]['psi']:.4f} | sa_cB_psi={sa_B['psi']:.4f}")

if __name__ == "__main__":
    import math
    main()
