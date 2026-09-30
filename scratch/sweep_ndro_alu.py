import sys
import os
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
from sol_engine import SOLEngine
from test_ptg_alu import build_base_graph

def run_trial(input_A, input_B, psi_bias_C, steps_compute=30):
    nodes, edges = build_base_graph(psi_bias_C)
    engine = SOLEngine.from_graph(nodes, edges, c_press=1.0, damping=0.01)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 1e-7
    engine.physics.conductance_gamma = 8.0
    engine.physics.psi_diffusion = 1.2
    engine.physics.psi_relax_base = 8.0
    
    battery_cfg = {
        "qMax": 80.0,
        "qThresh": 5.0,
        "leakLambda": 0.01,
        "avalancheGain": 5.0,
        "resonanceBoost": 4.0,
        "dampingClamp": 0.1,
        "flipThreshold": 0.65,
        "collapseFactor": 0.10,
        "resonanceDrive": 3.0,
        "dampingDrag": 0.3,
        "diodeResonanceOut": 1.0,
        "diodeResonanceIn": 1.0,
        "diodeDampingOut": 1.0,
        "diodeDampingIn": 1.0
    }
    engine.physics.battery_cfg = battery_cfg
    
    # Init input A
    if input_A:
        engine.physics.node_by_id["BATTERY_A"]["b_state"] = 1
        engine.physics.node_by_id["BATTERY_A"]["b_charge"] = 1.0
        engine.physics.node_by_id["BATTERY_A"]["psi"] = 1.0
        engine.physics.node_by_id["BATTERY_A"]["psi_bias"] = 1.0
        engine.physics.node_by_id["HOST_A"]["rho"] = 40.0
        engine.physics.node_by_id["BATTERY_A"]["rho"] = 20.0
    else:
        engine.physics.node_by_id["BATTERY_A"]["b_state"] = -1
        engine.physics.node_by_id["BATTERY_A"]["b_charge"] = 0.0
        engine.physics.node_by_id["BATTERY_A"]["psi"] = -1.0
        engine.physics.node_by_id["BATTERY_A"]["psi_bias"] = -1.0
        
    # Init input B
    if input_B:
        engine.physics.node_by_id["BATTERY_B"]["b_state"] = 1
        engine.physics.node_by_id["BATTERY_B"]["b_charge"] = 1.0
        engine.physics.node_by_id["BATTERY_B"]["psi"] = 1.0
        engine.physics.node_by_id["BATTERY_B"]["psi_bias"] = 1.0
        engine.physics.node_by_id["HOST_B"]["rho"] = 40.0
        engine.physics.node_by_id["BATTERY_B"]["rho"] = 20.0
    else:
        engine.physics.node_by_id["BATTERY_B"]["b_state"] = -1
        engine.physics.node_by_id["BATTERY_B"]["b_charge"] = 0.0
        engine.physics.node_by_id["BATTERY_B"]["psi"] = -1.0
        engine.physics.node_by_id["BATTERY_B"]["psi_bias"] = -1.0

    steps = 100 + steps_compute + 50
    for s in range(steps):
        damping_val = 0.01
        
        if s < 50:
            damping_val = 0.0
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = -1.0
            engine.physics.node_by_id["READOUT"]["psi_bias"] = -1.0
            if input_A:
                engine.physics.node_by_id["HOST_A"]["psi_bias"] = 1.0
            if input_B:
                engine.physics.node_by_id["HOST_B"]["psi_bias"] = 1.0
                
        elif 50 <= s < 100:
            damping_val = 0.0
            if s == 50:
                for edge in engine.physics.edges:
                    edge["flux"] = 0.0
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = -1.0
            engine.physics.node_by_id["READOUT"]["psi_bias"] = -1.0
            
        elif 100 <= s < 100 + steps_compute:
            damping_val = 0.01
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = 1.0
            engine.physics.node_by_id["READOUT"]["psi_bias"] = -1.0
            if input_A:
                engine.physics.node_by_id["HOST_A"]["psi_bias"] = 1.0
            if input_B:
                engine.physics.node_by_id["HOST_B"]["psi_bias"] = 1.0
                
        else:
            # Hold 2 Phase
            damping_val = 0.0
            if s == 100 + steps_compute:
                for edge in engine.physics.edges:
                    edge["flux"] = 0.0
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = -1.0
            engine.physics.node_by_id["READOUT"]["psi_bias"] = -1.0
            
        engine.step(dt=0.05, damping=damping_val)
        
    n_bat_c = engine.physics.node_by_id["BATTERY_C"]
    
    # Check input battery states at the end of the simulation
    state_a = engine.physics.node_by_id["BATTERY_A"]["b_state"]
    state_b = engine.physics.node_by_id["BATTERY_B"]["b_state"]
    mass_a = engine.physics.node_by_id["HOST_A"]["rho"]
    mass_b = engine.physics.node_by_id["HOST_B"]["rho"]
    
    return n_bat_c["b_state"] == 1, state_a, state_b, mass_a, mass_b

def main():
    print("Sweeping psi_bias_C for OR and AND logic under 30-step Compute phase...")
    print("Bias C | Inputs | Latched C | Bat A State (Mass) | Bat B State (Mass)")
    print("-" * 75)
    
    for ab in [0.25, 0.28, 0.30, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.38, 0.40]:
        for A, B in [(0, 0), (1, 0), (1, 1)]:
            lat_c, lat_a, lat_b, mass_a, mass_b = run_trial(A, B, ab)
            # Format inputs
            str_a = f"{lat_a:2d} ({mass_a:4.1f})" if A else " - (-)"
            str_b = f"{lat_b:2d} ({mass_b:4.1f})" if B else " - (-)"
            print(f" {ab:5.2f} | A={A}, B={B} | C_Lat={str(lat_c):5s} | A={str_a} | B={str_b}")
        print("-" * 75)

if __name__ == "__main__":
    main()
