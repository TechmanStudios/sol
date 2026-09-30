#!/usr/bin/env python3
import sys
import os
import math
from pathlib import Path

_SOL_ROOT = Path(__file__).resolve().parent.parent
os.environ["SOL_TELEMETRY_ENABLED"] = "false"
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
from sol_engine import SOLEngine

def run_sim(omega, gate_w0, gate_bias, host_bias, depletion_thresh, init_rho, steps=500, dt=0.05):
    # Build graph
    nodes = [
        {"id": "HOST_A", "label": "HOST_A", "group": "tech", "rho": 0.0, "psi": -1.0, "psi_bias": host_bias},
        {"id": "BATTERY_A", "label": "BATTERY_A", "group": "tech", "rho": 0.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "W_z": 0.0, "U_z": 0.0, "b_z": 10.0},
        {"id": "GATE_AB", "label": "GATE_AB", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": gate_bias, "W_z": 0.0, "U_z": 0.0, "b_z": 10.0},
        
        {"id": "HOST_B", "label": "HOST_B", "group": "spirit", "rho": 0.0, "psi": -1.0, "psi_bias": host_bias},
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

    transitions_a = 0
    transitions_b = 0
    periods = []
    last_t = None
    prev_state_a = 1.0
    prev_state_b = -1.0

    for s in range(steps):
        state_A = engine.physics.node_by_id["BATTERY_A"]["b_state"]
        state_B = engine.physics.node_by_id["BATTERY_B"]["b_state"]
        
        # Physical mass depletion collapse threshold
        if engine.physics.node_by_id["HOST_A"]["rho"] < depletion_thresh:
            engine.physics.node_by_id["HOST_A"]["psi_bias"] = -1.0
        else:
            engine.physics.node_by_id["HOST_A"]["psi_bias"] = host_bias
            
        if engine.physics.node_by_id["HOST_B"]["rho"] < depletion_thresh:
            engine.physics.node_by_id["HOST_B"]["psi_bias"] = -1.0
        else:
            engine.physics.node_by_id["HOST_B"]["psi_bias"] = host_bias

        engine.step(dt=dt)
        
        curr_state_a = engine.physics.node_by_id["BATTERY_A"]["b_state"]
        curr_state_b = engine.physics.node_by_id["BATTERY_B"]["b_state"]

        if curr_state_a != prev_state_a:
            transitions_a += 1
            if curr_state_a == 1.0:
                if last_t is not None:
                    periods.append(s - last_t)
                last_t = s
        if curr_state_b != prev_state_b:
            transitions_b += 1

        prev_state_a = curr_state_a
        prev_state_b = curr_state_b

    return transitions_a, transitions_b, len(periods)

def main():
    omegas = [0.10, 0.15, 0.20, 0.25, 0.30]
    gate_w0s = [1.0, 2.0, 4.0, 8.0]
    gate_biases = [-0.5, -0.2, 0.0, 0.3]
    host_biases = [-0.2, 0.0, 0.3]
    depletion_thresholds = [10.0, 15.0, 20.0]
    init_rhos = [30.0, 40.0, 60.0]

    print("Starting parameter sweep...")
    total_runs = len(omegas) * len(gate_w0s) * len(gate_biases) * len(host_biases) * len(depletion_thresholds) * len(init_rhos)
    print(f"Total configurations to test: {total_runs}")
    
    checked = 0
    passed_configs = []
    
    for omega in omegas:
        for gate_w0 in gate_w0s:
            for gate_bias in gate_biases:
                for host_bias in host_biases:
                    for depletion_thresh in depletion_thresholds:
                        for init_rho in init_rhos:
                            checked += 1
                            trans_a, trans_b, cycles = run_sim(
                                omega, gate_w0, gate_bias, host_bias, depletion_thresh, init_rho
                            )
                            if cycles >= 3 and trans_a >= 6 and trans_b >= 6:
                                config = {
                                    "omega": omega,
                                    "gate_w0": gate_w0,
                                    "gate_bias": gate_bias,
                                    "host_bias": host_bias,
                                    "depletion_thresh": depletion_thresh,
                                    "init_rho": init_rho,
                                    "cycles": cycles,
                                    "trans_a": trans_a,
                                    "trans_b": trans_b
                                }
                                passed_configs.append(config)
                                print(f"FOUND WORKING CONFIG! cycles={cycles}, trans_a={trans_a}, trans_b={trans_b}")
                                print(config)
                            if checked % 200 == 0:
                                print(f"Progress: {checked}/{total_runs} (found {len(passed_configs)} working configs)")
                                
    print(f"\nSweep completed. Found {len(passed_configs)} working configurations.")
    if passed_configs:
        print("Top working configuration:")
        print(passed_configs[0])

if __name__ == "__main__":
    main()
