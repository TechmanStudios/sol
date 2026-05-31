#!/usr/bin/env python3
"""
SOL Analog Conduit Multiplication Trace Debugger
"""

import sys
import os
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine

def build_test_chain():
    raw_nodes = [
        {"id": "Source", "label": "Source", "group": "bridge", "rho": 10.0},
        {"id": "Mixer", "label": "Mixer", "group": "bridge", "rho": 10.0},
        {"id": "Destination", "label": "Destination", "group": "bridge", "rho": 10.0},
    ]
    raw_edges = [
        {"from": "Source", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "Mixer", "to": "Destination", "w0": 1.0, "kind": "tax"},
    ]
    return raw_nodes, raw_edges

def run_debug(A1: float, A2: float, dt: float, steps: int, c_press: float, damping: float, phase: float, active_demod: bool):
    raw_nodes, raw_edges = build_test_chain()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    
    omega1 = 2.0 * math.pi / (15.0 * dt)
    omega2 = 2.0 * math.pi / (25.0 * dt)
    omega_diff = omega1 - omega2
    
    engine.write_enable("Mixer")
    engine.write_enable("Destination")
    engine.physics.node_by_id["Destination"]["rho"] = 0.0
    engine.physics.node_by_id["Mixer"]["rho"] = 0.0
    
    traces = []
    
    for s in range(steps):
        t = s * dt
        src_rho = 10.0 + A1 * math.sin(omega1 * t) + A2 * math.sin(omega2 * t)
        engine.physics.node_by_id["Source"]["rho"] = src_rho
        
        if active_demod:
            engine.physics.node_by_id["Mixer"]["psi"] = math.sin(omega_diff * t + phase)
        else:
            engine.physics.node_by_id["Mixer"]["psi"] = 0.0
            
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
        if s >= 300: # Log the last 100 steps
            traces.append({
                "step": s,
                "src_rho": src_rho,
                "mixer_rho": engine.physics.node_by_id["Mixer"]["rho"],
                "mixer_psi": engine.physics.node_by_id["Mixer"]["psi"],
                "dest_rho": engine.physics.node_by_id["Destination"]["rho"],
                "edge1_cond": engine.physics.edges[0]["conductance"],
                "edge2_cond": engine.physics.edges[1]["conductance"],
                "edge1_flux": engine.physics.edges[0]["flux"],
                "edge2_flux": engine.physics.edges[1]["flux"],
            })
            
    return traces

def main():
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 5.0
    phase = 5.890
    
    print("--- CASE 1 (A1=2, A2=2), ACTIVE ---")
    tr1_act = run_debug(2.0, 2.0, dt, steps, c_press, damping, phase, True)
    print(f"Final Dest Rho (Active): {tr1_act[-1]['dest_rho']:.6f}")
    print(f"Mixer Rho range: {min(x['mixer_rho'] for x in tr1_act):.4f} to {max(x['mixer_rho'] for x in tr1_act):.4f}")
    print(f"Edge2 Flux range: {min(x['edge2_flux'] for x in tr1_act):+.4f} to {max(x['edge2_flux'] for x in tr1_act):+.4f}")
    
    print("\n--- CASE 1 (A1=2, A2=2), REF ---")
    tr1_ref = run_debug(2.0, 2.0, dt, steps, c_press, damping, phase, False)
    print(f"Final Dest Rho (Ref): {tr1_ref[-1]['dest_rho']:.6f}")
    
    print("\n--- CASE 3 (A1=4, A2=4), ACTIVE ---")
    tr3_act = run_debug(4.0, 4.0, dt, steps, c_press, damping, phase, True)
    print(f"Final Dest Rho (Active): {tr3_act[-1]['dest_rho']:.6f}")
    print(f"Mixer Rho range: {min(x['mixer_rho'] for x in tr3_act):.4f} to {max(x['mixer_rho'] for x in tr3_act):.4f}")
    print(f"Edge2 Flux range: {min(x['edge2_flux'] for x in tr3_act):+.4f} to {max(x['edge2_flux'] for x in tr3_act):+.4f}")
    
    print("\n--- CASE 3 (A1=4, A2=4), REF ---")
    tr3_ref = run_debug(4.0, 4.0, dt, steps, c_press, damping, phase, False)
    print(f"Final Dest Rho (Ref): {tr3_ref[-1]['dest_rho']:.6f}")

if __name__ == "__main__":
    main()
