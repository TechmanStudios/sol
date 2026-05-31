#!/usr/bin/env python3
"""
SOL Interferometric Wave Addition and Subtraction Proof
======================================================
Demonstrates analog computation on the manifold using wave interferometry.
By injecting two waves of the same frequency at Source A and Source B,
we perform addition (in-phase, constructive) and subtraction (out-of-phase,
destructive) directly at the Mixer node.
"""

import sys
import os
import math
from pathlib import Path

# Add sol-core path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))

# Disable telemetry
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine

def build_test_graph() -> tuple[list[dict], list[dict]]:
    # Source A and Source B both connect to Mixer
    raw_nodes = [
        {"id": "SourceA", "label": "SourceA", "group": "bridge", "rho": 10.0},
        {"id": "SourceB", "label": "SourceB", "group": "bridge", "rho": 10.0},
        {"id": "Mixer", "label": "Mixer", "group": "bridge", "rho": 10.0},
    ]
    raw_edges = [
        {"from": "SourceA", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "SourceB", "to": "Mixer", "w0": 1.0, "kind": "tax"},
    ]
    return raw_nodes, raw_edges

def run_interference_trial(A1: float, A2: float, theta: float, dt: float, steps: int, c_press: float, damping: float) -> float:
    raw_nodes, raw_edges = build_test_graph()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None  # Disable MHD feedback for pure wave linear propagation
    
    # Fundamental period of 12 steps
    omega = 2.0 * math.pi / (12.0 * dt)
    
    mixer_rhos = []
    
    for s in range(steps):
        t = s * dt
        # Drive SourceA and SourceB with phase offset theta
        engine.physics.node_by_id["SourceA"]["rho"] = 10.0 + A1 * math.sin(omega * t)
        engine.physics.node_by_id["SourceB"]["rho"] = 10.0 + A2 * math.sin(omega * t + theta)
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
        # Log Mixer rho in the last 100 steps (steady state)
        if s >= steps - 100:
            mixer_rhos.append(engine.physics.node_by_id["Mixer"]["rho"])
            
    # Return the peak-to-peak amplitude (max - min) of the Mixer density oscillation
    amplitude = max(mixer_rhos) - min(mixer_rhos)
    return amplitude

def main():
    print("======================================================================")
    print("  SOL MANIFOLD WAVE INTERFEROMETRY (ADDITION & SUBTRACTION) PROOF")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 0.2
    
    A1 = 3.0
    A2 = 3.0
    
    print(f"  Inputs: SourceA Amp = {A1:.1f}, SourceB Amp = {A2:.1f}")
    print("  Sweeping relative phase difference (theta) from 0 to 2*pi...")
    print("----------------------------------------------------------------------")
    print("   Theta (rad) | Theta (deg) | Mixer Oscillation Amplitude (Peak-to-Peak)")
    print("----------------------------------------------------------------------")
    
    amplitudes = []
    phases = []
    
    # Sweep theta from 0 to 2*pi in 12 steps
    for idx in range(13):
        theta = (idx / 12.0) * 2.0 * math.pi
        deg = (idx / 12.0) * 360.0
        amp = run_interference_trial(A1, A2, theta, dt, steps, c_press, damping)
        amplitudes.append(amp)
        phases.append(theta)
        
        # Draw a tiny ASCII bar to visualize the amplitude
        bar = "#" * int(amp * 15.0)
        print(f"    {theta:8.3f}   |   {deg:5.1f}°   |   {amp:.6f}  {bar}")
        
    print("----------------------------------------------------------------------")
    
    max_amp = max(amplitudes)
    min_amp = min(amplitudes)
    max_idx = amplitudes.index(max_amp)
    min_idx = amplitudes.index(min_amp)
    
    print(f"  * Maximum Amplitude (Addition): {max_amp:.6f} at {phases[max_idx]*180/math.pi:.1f}°")
    print(f"  * Minimum Amplitude (Subtraction): {min_amp:.6f} at {phases[min_idx]*180/math.pi:.1f}°")
    
    ratio = max_amp / max(1e-6, min_amp)
    print(f"  * Contrast Ratio (Addition/Subtraction): {ratio:.2f}")
    
    # Verification: For successful interferometric computation, the constructive
    # amplitude must be significantly larger than the destructive amplitude (contrast ratio > 5.0)
    passed = ratio > 5.0
    print(f"  * Status: {'PASSED' if passed else 'FAILED'}")
    
    if passed:
        print("\n  [STATUS] SUCCESS: Analog wave interferometry computation verified!")
        print("  The manifold successfully performs Addition (constructive) and Subtraction (destructive).")
    else:
        print("\n  [STATUS] FAILED: Contrast ratio is too low for distinct logic resolution.")
    print("======================================================================")

if __name__ == "__main__":
    main()
