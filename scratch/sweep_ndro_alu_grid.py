import sys
import os
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
from sol_engine import SOLEngine
from test_ptg_alu import build_base_graph

def run_trial(input_A, input_B, psi_bias_C, bus_bias, res_drive=50.0):
    nodes, edges = build_base_graph(psi_bias_C)
    engine = SOLEngine.from_graph(nodes, edges, c_press=1.0, damping=0.01)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 1e-7
    engine.physics.conductance_gamma = 8.0
    engine.physics.psi_diffusion = 1.2
    engine.physics.psi_relax_base = 8.0
    engine.physics.battery_cfg = {
        'qMax': 80.0, 'qThresh': 5.0, 'leakLambda': 0.01, 'avalancheGain': 5.0, 
        'resonanceBoost': 4.0, 'dampingClamp': 0.1, 'flipThreshold': 0.65, 
        'collapseFactor': 0.1, 'resonanceDrive': res_drive, 'dampingDrag': 0.3, 
        'diodeResonanceOut': 1.0, 'diodeResonanceIn': 1.0, 'diodeDampingOut': 1.0, 
        'diodeDampingIn': 1.0
    }
    
    if input_A:
        engine.physics.node_by_id["BATTERY_A"].update({'b_state': 1, 'b_charge': 1.0, 'psi': 1.0, 'psi_bias': 1.0, 'rho': 20.0})
        engine.physics.node_by_id["HOST_A"]["rho"] = 40.0
    else:
        engine.physics.node_by_id["BATTERY_A"].update({'b_state': -1, 'b_charge': 0.0, 'psi': -1.0, 'psi_bias': -1.0, 'rho': 0.0})
        
    if input_B:
        engine.physics.node_by_id["BATTERY_B"].update({'b_state': 1, 'b_charge': 1.0, 'psi': 1.0, 'psi_bias': 1.0, 'rho': 20.0})
        engine.physics.node_by_id["HOST_B"]["rho"] = 40.0
    else:
        engine.physics.node_by_id["BATTERY_B"].update({'b_state': -1, 'b_charge': 0.0, 'psi': -1.0, 'psi_bias': -1.0, 'rho': 0.0})

    for s in range(150): # Run Write (50) + Hold (50) + Compute (30) + Verify (20)
        damping_val = 0.01
        if s < 50:
            damping_val = 0.0
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = -1.0
            engine.physics.node_by_id["BUS"]["psi_bias"] = -1.0
            engine.physics.node_by_id["READOUT"]["psi_bias"] = -1.0
            if input_A: engine.physics.node_by_id["HOST_A"]["psi_bias"] = 1.0
            if input_B: engine.physics.node_by_id["HOST_B"]["psi_bias"] = 1.0
        elif 50 <= s < 100:
            damping_val = 0.0
            if s == 50:
                for edge in engine.physics.edges: edge["flux"] = 0.0
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = -1.0
            engine.physics.node_by_id["BUS"]["psi_bias"] = -1.0
            engine.physics.node_by_id["READOUT"]["psi_bias"] = -1.0
        elif 100 <= s < 130:
            damping_val = 0.01
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = 1.0
            engine.physics.node_by_id["BUS"]["psi_bias"] = bus_bias
            engine.physics.node_by_id["READOUT"]["psi_bias"] = bus_bias
            if input_A: engine.physics.node_by_id["HOST_A"]["psi_bias"] = 1.0
            if input_B: engine.physics.node_by_id["HOST_B"]["psi_bias"] = 1.0
        else:
            damping_val = 0.0
            if s == 130:
                for edge in engine.physics.edges: edge["flux"] = 0.0
            for g in ["GATE_A", "GATE_B", "GATE_C"]:
                engine.physics.node_by_id[g]["psi_bias"] = -1.0
            engine.physics.node_by_id["BUS"]["psi_bias"] = -1.0
            engine.physics.node_by_id["READOUT"]["psi_bias"] = -1.0
            
        engine.step(dt=0.05, damping=damping_val)
        
    n_bat_c = engine.physics.node_by_id["BATTERY_C"]
    lat_a = engine.physics.node_by_id["BATTERY_A"]["b_state"] == 1
    lat_b = engine.physics.node_by_id["BATTERY_B"]["b_state"] == 1
    return n_bat_c["b_state"] == 1, lat_a, lat_b

def main():
    print("Searching for valid NDRO-ALU configurations...")
    bus_biases = [-1.0, -0.5, 0.0, 0.5, 1.0]
    
    # We sweep ab from -0.3 to 0.5 with steps of 0.01
    ab_vals = [round(x * 0.01, 2) for x in range(-30, 51)]
    
    solutions = []
    
    for bus in bus_biases:
        for ab_or in ab_vals:
            # Check OR condition
            or00, _, _ = run_trial(0, 0, ab_or, bus)
            if or00: continue
            or10, a_active, _ = run_trial(1, 0, ab_or, bus)
            if not or10 or not a_active: continue
            or01, _, b_active = run_trial(0, 1, ab_or, bus)
            if not or01 or not b_active: continue
            or11, a_active, b_active = run_trial(1, 1, ab_or, bus)
            if not or11 or not a_active or not b_active: continue
            
            # OR works! Now let's find a matching AND bias for this bus bias
            for ab_and in ab_vals:
                and00, _, _ = run_trial(0, 0, ab_and, bus)
                if and00: continue
                and10, a_active, _ = run_trial(1, 0, ab_and, bus)
                if and10 or not a_active: continue
                and01, _, b_active = run_trial(0, 1, ab_and, bus)
                if and01 or not b_active: continue
                and11, a_active, b_active = run_trial(1, 1, ab_and, bus)
                if not and11 or not a_active or not b_active: continue
                
                solutions.append({
                    "bus_bias": bus,
                    "or_bias": ab_or,
                    "and_bias": ab_and
                })
                
    print(f"Found {len(solutions)} configurations:")
    for s in solutions:
        print(f"Bus Bias={s['bus_bias']:4.1f} | OR Bias={s['or_bias']:5.2f} | AND Bias={s['and_bias']:5.2f}")

if __name__ == "__main__":
    main()
