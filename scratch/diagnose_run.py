import sys
import os
import math
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent
os.environ["SOL_TELEMETRY_ENABLED"] = "false"
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
from sol_engine import SOLEngine

def main():
    omega = 0.15
    gate_w0 = 8.0
    gate_bias = 0.3
    host_bias = 0.3
    depletion_thresh = 15.0
    init_rho = 40.0
    steps = 500
    dt = 0.05

    nodes = [
        {"id": "HOST_A", "label": "HOST_A", "group": "tech", "rho": 0.0, "psi": -1.0, "psi_bias": host_bias, "W_z": 0.0, "U_z": 35.0, "b_z": 5.0},
        {"id": "BATTERY_A", "label": "BATTERY_A", "group": "tech", "rho": 0.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "W_z": 0.0, "U_z": 0.0, "b_z": 10.0},
        {"id": "GATE_AB", "label": "GATE_AB", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": gate_bias, "W_z": 0.0, "U_z": 0.0, "b_z": 10.0},
        
        {"id": "HOST_B", "label": "HOST_B", "group": "spirit", "rho": 0.0, "psi": -1.0, "psi_bias": host_bias, "W_z": 0.0, "U_z": 35.0, "b_z": 5.0},
        {"id": "BATTERY_B", "label": "BATTERY_B", "group": "spirit", "rho": 0.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "W_z": 0.0, "U_z": 0.0, "b_z": 10.0},
        {"id": "GATE_BA", "label": "GATE_BA", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": gate_bias, "W_z": 0.0, "U_z": 0.0, "b_z": 10.0},
    ]
    
    edges = [
        {"from": "HOST_A", "to": "BATTERY_A", "w0": 20.0, "kind": "tax"},
        {"from": "HOST_A", "to": "GATE_AB", "w0": gate_w0, "kind": "tax"},
        {"from": "GATE_AB", "to": "HOST_B", "w0": gate_w0, "kind": "tax"},
        
        {"from": "HOST_B", "to": "BATTERY_B", "w0": 20.0, "kind": "tax"},
        {"from": "HOST_B", "to": "GATE_BA", "w0": gate_w0, "kind": "tax"},
        {"from": "GATE_BA", "to": "HOST_A", "w0": gate_w0, "kind": "tax"},
    ]

    engine = SOLEngine.from_graph(nodes, edges, c_press=1.0, damping=0.25)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 1e-7
    engine.physics.conductance_gamma = 8.0
    engine.physics.psi_diffusion = 1.5
    engine.physics.psi_relax_base = 8.0
    
    engine.physics.gated_recurrent_cfg = {
        "enabled": True,
        "W_z": 0.0, "U_z": 35.0, "b_z": -2.5,
        "W_r": 0.0, "U_r": 0.0, "b_r": 10.0
    }
    
    engine.physics.phase_cfg = {
        "omega": omega,
        "surfaceTension": 1.2,
        "deepViscosity": 0.8
    }
    
    engine.physics.battery_cfg = {
        "qMax": 60.0,
        "qThresh": 5.0,
        "leakLambda": 0.015,
        "avalancheGain": 6.0,
        "resonanceBoost": 4.0,
        "dampingClamp": 0.1,
        "flipThreshold": 0.85,
        "collapseFactor": 0.12,
        "resonanceDrive": 60.0,
        "dampingDrag": 0.5,
        "diodeResonanceOut": 1.0,
        "diodeResonanceIn": 1.0,
        "diodeDampingOut": 1.0,
        "diodeDampingIn": 1.0
    }
    
    # Init Battery A active, B collapsed
    engine.physics.node_by_id["BATTERY_A"]["b_state"] = 1
    engine.physics.node_by_id["BATTERY_A"]["b_charge"] = 1.0
    engine.physics.node_by_id["BATTERY_A"]["psi"] = 1.0
    engine.physics.node_by_id["BATTERY_A"]["psi_bias"] = 1.0
    engine.physics.node_by_id["HOST_A"]["rho"] = init_rho
    engine.physics.node_by_id["BATTERY_A"]["rho"] = 20.0
    engine.physics.node_by_id["HOST_A"]["psi"] = 1.0
    engine.physics.node_by_id["HOST_A"]["psi_bias"] = host_bias
    
    engine.physics.node_by_id["BATTERY_B"]["b_state"] = -1
    engine.physics.node_by_id["BATTERY_B"]["b_charge"] = 0.0
    engine.physics.node_by_id["BATTERY_B"]["psi"] = -1.0
    engine.physics.node_by_id["BATTERY_B"]["psi_bias"] = -1.0

    print("Step | Phase | Batt_A_S | Host_A_Rho | Host_A_Psi | GATE_AB_Rho | GATE_AB_Psi | Host_B_Rho | Host_B_Psi | Batt_B_Chg | Batt_B_S")
    print("-" * 135)

    for s in range(steps):
        state_A = engine.physics.node_by_id["BATTERY_A"]["b_state"]
        state_B = engine.physics.node_by_id["BATTERY_B"]["b_state"]
        
        # Calculate current global heartbeat phase
        phase = math.cos(engine.physics.phase_cfg["omega"] * engine.physics._t * 10)
        
        # Physical mass depletion collapse threshold + phase modulation
        if state_A == 1 and engine.physics.node_by_id["HOST_A"]["rho"] < depletion_thresh:
            engine.physics.node_by_id["HOST_A"]["psi_bias"] = -1.0
        else:
            engine.physics.node_by_id["HOST_A"]["psi_bias"] = host_bias if phase > -0.2 else -1.0
            
        if state_B == 1 and engine.physics.node_by_id["HOST_B"]["rho"] < depletion_thresh:
            engine.physics.node_by_id["HOST_B"]["psi_bias"] = -1.0
        else:
            engine.physics.node_by_id["HOST_B"]["psi_bias"] = host_bias if phase < 0.2 else -1.0

        engine.step(dt=dt)
        
        phase = math.cos(engine.physics.phase_cfg["omega"] * engine.physics._t * 10)
        
        h_a_rho = engine.physics.node_by_id["HOST_A"]["rho"]
        h_a_psi = engine.physics.node_by_id["HOST_A"]["psi"]
        g_ab_rho = engine.physics.node_by_id["GATE_AB"]["rho"]
        g_ab_psi = engine.physics.node_by_id["GATE_AB"]["psi"]
        h_b_rho = engine.physics.node_by_id["HOST_B"]["rho"]
        h_b_psi = engine.physics.node_by_id["HOST_B"]["psi"]
        b_b_chg = engine.physics.node_by_id["BATTERY_B"]["b_charge"]
        b_b_state = engine.physics.node_by_id["BATTERY_B"]["b_state"]
        
        curr_state_a = engine.physics.node_by_id["BATTERY_A"]["b_state"]
        curr_state_b = engine.physics.node_by_id["BATTERY_B"]["b_state"]
        if curr_state_a != state_A or curr_state_b != state_B or s % 20 == 0:
            print(f"{s:4d} | {phase:5.2f} | {curr_state_a:8.1f} | {h_a_rho:10.2f} | {h_a_psi:10.4f} | {g_ab_rho:11.2f} | {g_ab_psi:11.4f} | {h_b_rho:10.2f} | {h_b_psi:10.4f} | {b_b_chg:10.4f} | {curr_state_b:8.1f}")

if __name__ == "__main__":
    main()
