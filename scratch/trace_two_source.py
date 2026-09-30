#!/usr/bin/env python3
"""
Diagnostic script for two-source propagation
"""
import sys
import os
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine
from test_fixed_psi_multiplication import build_test_graph

def run_trace(A1, A2, dt, steps, c_press, damping, phase_offset):
    raw_nodes, raw_edges = build_test_graph()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    
    omega1 = 2.0 * math.pi / (10.0 * dt)
    omega2 = 2.0 * math.pi / (25.0 * dt)
    omega_diff = omega1 - omega2
    
    engine.write_enable("Mixer")
    engine.write_enable("Destination")
    engine.physics.node_by_id["Destination"]["rho"] = 0.0
    engine.physics.node_by_id["Mixer"]["rho"] = 0.0
    
    traces = []
    for s in range(steps):
        t = s * dt
        engine.physics.node_by_id["SourceA"]["rho"] = 10.0 + A1 * math.sin(omega1 * t)
        engine.physics.node_by_id["SourceB"]["rho"] = 10.0 + A2 * math.sin(omega2 * t)
        
        val = math.sin(omega_diff * t + phase_offset)
        engine.physics.node_by_id["Mixer"]["psi"] = val
        engine.physics.node_by_id["Mixer"]["psi_bias"] = val
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
        if s >= 350:
            traces.append({
                "step": s,
                "mixer_rho": engine.physics.node_by_id["Mixer"]["rho"],
                "mixer_p": engine.physics.node_by_id["Mixer"]["p"],
                "mixer_psi": engine.physics.node_by_id["Mixer"]["psi"],
                "dest_rho": engine.physics.node_by_id["Destination"]["rho"],
            })
            
    return traces

def main():
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 0.2
    phase = 0.0
    
    tr1 = run_trace(2.0, 2.0, dt, steps, c_press, damping, phase)
    print("--- CASE 1 (A1=2, A2=2) ---")
    print(f"Mixer Rho range: {min(x['mixer_rho'] for x in tr1):.6f} to {max(x['mixer_rho'] for x in tr1):.6f}")
    print(f"Dest Rho final: {tr1[-1]['dest_rho']:.6f}")
    
    tr3 = run_trace(4.0, 4.0, dt, steps, c_press, damping, phase)
    print("\n--- CASE 3 (A1=4, A2=4) ---")
    print(f"Mixer Rho range: {min(x['mixer_rho'] for x in tr3):.6f} to {max(x['mixer_rho'] for x in tr3):.6f}")
    print(f"Dest Rho final: {tr3[-1]['dest_rho']:.6f}")

if __name__ == "__main__":
    main()
