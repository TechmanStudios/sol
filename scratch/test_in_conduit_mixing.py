#!/usr/bin/env python3
"""
SOL In-Conduit Analog Mixing Test
===================================
Empirically verifies that the logarithmic equation of state in the SOL engine
causes non-linear harmonic mixing, generating sum and difference frequencies
when multiple wave packets are superimposed.
"""

import sys
import os
import math
from pathlib import Path

# Add sol-core path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))

# Disable telemetry for fast run
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine

def build_test_chain() -> tuple[list[dict], list[dict]]:
    """Build a simple 3-node chain: Source -> Mixer -> Destination."""
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

def compute_dft_amplitude(signal: list[float], dt: float, omega: float) -> float:
    """Compute the amplitude of a specific frequency component using Discrete Fourier Transform."""
    n = len(signal)
    if n == 0:
        return 0.0
    
    # We subtract the mean to isolate dynamic AC oscillations from DC offsets
    mean_val = sum(signal) / n
    ac_signal = [x - mean_val for x in signal]
    
    cos_sum = 0.0
    sin_sum = 0.0
    for idx, val in enumerate(ac_signal):
        t = idx * dt
        cos_sum += val * math.cos(omega * t)
        sin_sum += val * math.sin(omega * t)
        
    # Scale amplitude (factor of 2 for single-sided spectrum amplitude)
    cos_amp = (2.0 / n) * cos_sum
    sin_amp = (2.0 / n) * sin_sum
    return math.sqrt(cos_amp**2 + sin_amp**2)

def main():
    print("======================================================================")
    print("  SOL IN-CONDUIT ANALOG MIXING VALIDATION")
    print("======================================================================")
    
    # 1. Setup Simulation Constants
    dt = 0.08
    steps = 400
    c_press = 2.0
    
    # Frequencies: Period 10 steps (omega_1) and Period 25 steps (omega_2)
    omega_1 = 2.0 * math.pi / (10.0 * dt)  # 2.5 * pi ~ 7.854 rad/s
    omega_2 = 2.0 * math.pi / (25.0 * dt)  # 1.0 * pi ~ 3.142 rad/s
    
    # Expected mix frequencies
    omega_diff = omega_1 - omega_2        # 1.5 * pi ~ 4.712 rad/s
    omega_sum = omega_1 + omega_2         # 3.5 * pi ~ 10.996 rad/s
    omega_harm1 = 2.0 * omega_1           # 5.0 * pi ~ 15.708 rad/s
    omega_harm2 = 2.0 * omega_2           # 2.0 * pi ~ 6.283 rad/s
    
    print(f"  Inputs:  w_1 = {omega_1:.4f} rad/s (P = 10 steps)")
    print(f"           w_2 = {omega_2:.4f} rad/s (P = 25 steps)")
    print(f"  Expected Mixing Products:")
    print(f"           w_diff = {omega_diff:.4f} rad/s (P = 16.67 steps)")
    print(f"           w_sum  = {omega_sum:.4f} rad/s (P = 7.14 steps)")
    print(f"           2*w_1  = {omega_harm1:.4f} rad/s (P = 5 steps)")
    print(f"           2*w_2  = {omega_harm2:.4f} rad/s (P = 12.5 steps)")
    print("----------------------------------------------------------------------")
    
    # 2. Initialize Engine
    raw_nodes, raw_edges = build_test_chain()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=0.0)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    
    # Enable all gates
    engine.write_enable("Mixer")
    engine.write_enable("Destination")
    
    # 3. Step Simulation & Log Telemetry
    mixer_rho_trace = []
    mixer_p_trace = []
    source_rho_trace = []
    
    for s in range(steps):
        t = s * dt
        # Superimpose the two input frequencies at the Source
        src_rho = 10.0 + 4.0 * math.sin(omega_1 * t) + 4.0 * math.sin(omega_2 * t)
        engine.physics.node_by_id["Source"]["rho"] = src_rho
        
        engine.step(dt=dt, c_press=c_press)
        
        source_rho_trace.append(src_rho)
        mixer_rho_trace.append(engine.physics.node_by_id["Mixer"]["rho"])
        mixer_p_trace.append(engine.physics.node_by_id["Mixer"]["p"])
        
    # We ignore the first 50 steps to let transients settle
    settle_offset = 50
    signal_rho = mixer_rho_trace[settle_offset:]
    signal_p = mixer_p_trace[settle_offset:]
    
    # 4. Perform Frequency Analysis (DFT) on Mixer Node
    print("  Running Discrete Fourier Transform (DFT) on Mixer density...")
    amp_in1 = compute_dft_amplitude(signal_rho, dt, omega_1)
    amp_in2 = compute_dft_amplitude(signal_rho, dt, omega_2)
    amp_diff = compute_dft_amplitude(signal_rho, dt, omega_diff)
    amp_sum = compute_dft_amplitude(signal_rho, dt, omega_sum)
    amp_harm1 = compute_dft_amplitude(signal_rho, dt, omega_harm1)
    amp_harm2 = compute_dft_amplitude(signal_rho, dt, omega_harm2)
    
    print("\n  DFT Spectral Amplitude Results at Mixer Node:")
    print("  ==================================================")
    print(f"  Input w_1 (fundamental 1):  {amp_in1:.6f}")
    print(f"  Input w_2 (fundamental 2):  {amp_in2:.6f}")
    print(f"  --------------------------------------------------")
    print(f"  Difference w_diff (w_1-w_2): {amp_diff:.6f}  <-- MIXING PRODUCT")
    print(f"  Sum w_sum (w_1+w_2):         {amp_sum:.6f}  <-- MIXING PRODUCT")
    print(f"  Harmonic 2*w_1:              {amp_harm1:.6f}")
    print(f"  Harmonic 2*w_2:              {amp_harm2:.6f}")
    print("  ==================================================")
    
    # 5. Validation Check
    # Mixing products are successfully generated if their amplitudes are non-trivial
    threshold = 1e-4
    has_diff = amp_diff > threshold
    has_sum = amp_sum > threshold
    
    print("\n  Validation Assessment:")
    print(f"  * Difference frequency detected (>{threshold}): {'SUCCESS' if has_diff else 'FAIL'}")
    print(f"  * Sum frequency detected (>{threshold}):        {'SUCCESS' if has_sum else 'FAIL'}")
    
    if has_diff and has_sum:
        print("\n  [STATUS] PASSED: In-Conduit Analog Mixing is empirically validated!")
        print("  The logarithmic pressure curve correctly generates harmonic mix products.")
    else:
        print("\n  [STATUS] FAILED: Mixing products are below detection threshold.")
        
    print("======================================================================")

if __name__ == "__main__":
    main()
