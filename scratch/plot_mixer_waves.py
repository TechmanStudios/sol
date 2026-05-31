#!/usr/bin/env python3
import sys
import os
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine
from test_fixed_psi_multiplication import build_test_graph

def main():
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 0.2
    phase_offset = 0.0
    
    raw_nodes, raw_edges = build_test_graph()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None  # Disable magnetic feedback to prevent edge conductance clamping
    
    omega1 = 2.0 * math.pi / (10.0 * dt)
    omega2 = 2.0 * math.pi / (25.0 * dt)
    omega_diff = omega1 - omega2
    
    engine.write_enable("Mixer")
    engine.write_enable("Destination")
    engine.physics.node_by_id["Destination"]["rho"] = 0.0
    engine.physics.node_by_id["Mixer"]["rho"] = 0.0
    
    print("Step | SourceA_rho | SourceB_rho | Mixer_rho | Mixer_psi | Edge2_cond | Edge2_flux")
    print("---------------------------------------------------------------------------------")
    
    for s in range(steps):
        t = s * dt
        # Case 3: A1=4, A2=4
        srcA = 10.0 + 4.0 * math.sin(omega1 * t)
        srcB = 10.0 + 4.0 * math.sin(omega2 * t)
        engine.physics.node_by_id["SourceA"]["rho"] = srcA
        engine.physics.node_by_id["SourceB"]["rho"] = srcB
        
        val = math.sin(omega_diff * t + phase_offset)
        engine.physics.node_by_id["Mixer"]["psi"] = val
        engine.physics.node_by_id["Mixer"]["psi_bias"] = val
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
        if s >= 350:
            edge2 = engine.physics.edges[2] # Mixer -> Destination
            print(f"{s:4d} | {srcA:11.4f} | {srcB:11.4f} | {engine.physics.node_by_id['Mixer']['rho']:9.4f} | {val:9.4f} | {edge2['conductance']:10.4f} | {edge2['flux']:10.4f}")

if __name__ == "__main__":
    main()
