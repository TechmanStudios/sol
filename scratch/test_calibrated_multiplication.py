#!/usr/bin/env python3
"""
SOL Analog Conduit Multiplication Proof with Self-Mixing Cancellation
======================================================================
Empirically demonstrates that the SOL Engine can perform analog multiplication
directly inside the physical manifold. By using a two-trial method (Active minus
Reference), we cancel out the input-dependent self-mixing DC offset (A1^2, A2^2) and
measure the pure cross-product (A1 * A2).
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

def run_multiplication_trial(A1: float, A2: float, dt: float, steps: int, c_press: float, damping: float, phase_offset: float, active_demod: bool) -> float:
    """Run a single simulation trial (either active demodulation or reference static gate)."""
    raw_nodes, raw_edges = build_test_chain()
    
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0  # Smooth, unclamped analog gating
    
    # Frequencies (Periods of 15 and 25 steps)
    omega1 = 2.0 * math.pi / (15.0 * dt)
    omega2 = 2.0 * math.pi / (25.0 * dt)
    omega_diff = omega1 - omega2  # Demodulator frequency
    
    # Enable gates
    engine.write_enable("Mixer")
    engine.write_enable("Destination")
    
    # Initialize destinations to 0 to provide clean forward pressure
    engine.physics.node_by_id["Destination"]["rho"] = 0.0
    engine.physics.node_by_id["Mixer"]["rho"] = 0.0
    
    for s in range(steps):
        t = s * dt
        
        # Drive Source with the two inputs
        src_rho = 10.0 + A1 * math.sin(omega1 * t) + A2 * math.sin(omega2 * t)
        engine.physics.node_by_id["Source"]["rho"] = src_rho
        
        # Drive Mixer's belief field
        if active_demod:
            engine.physics.node_by_id["Mixer"]["psi"] = math.sin(omega_diff * t + phase_offset)
        else:
            engine.physics.node_by_id["Mixer"]["psi"] = 0.0
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
    final_dest_mass = engine.physics.node_by_id["Destination"]["rho"]
    return final_dest_mass

def main():
    print("======================================================================")
    print("  SOL MANIFOLD MULTIPLICATION WITH SELF-MIXING CANCELLATION")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 5.0
    
    # Phase sweep calibration
    print("  Step 1: Sweeping demodulator phase to calibrate propagation delay...")
    best_phase = 0.0
    best_diff = 0.0
    
    # Sweep from 0 to 2*pi with 16 steps
    for p_idx in range(16):
        phase = (p_idx / 16.0) * 2.0 * math.pi
        # Test Case 1: A1=2.0, A2=2.0
        active_mass = run_multiplication_trial(2.0, 2.0, dt, steps, c_press, damping, phase, active_demod=True)
        ref_mass = run_multiplication_trial(2.0, 2.0, dt, steps, c_press, damping, phase, active_demod=False)
        diff = active_mass - ref_mass
        print(f"    Phase = {phase:5.3f} rad | Active: {active_mass:.6f} | Ref: {ref_mass:.6f} | Net (Active-Ref): {diff:+.6f}")
        if abs(diff) > abs(best_diff):
            best_diff = diff
            best_phase = phase
            
    print(f"\n  --> Calibrated Phase Offset: {best_phase:.4f} rad (Max differential response: {best_diff:+.6f})\n")
    
    # Define three cases of input amplitudes A1 and A2
    cases = [
        {"id": "Case 1 (Small)",  "A1": 2.0, "A2": 2.0, "product": 4.0},
        {"id": "Case 2 (Medium)", "A1": 4.0, "A2": 2.0, "product": 8.0},
        {"id": "Case 3 (Large)",  "A1": 4.0, "A2": 4.0, "product": 16.0},
    ]
    
    results = []
    
    for c in cases:
        print(f"  Running {c['id']}: A1 = {c['A1']:.1f}, A2 = {c['A2']:.1f} (Expected product = {c['product']:.1f})")
        active_mass = run_multiplication_trial(c["A1"], c["A2"], dt, steps, c_press, damping, best_phase, active_demod=True)
        ref_mass = run_multiplication_trial(c["A1"], c["A2"], dt, steps, c_press, damping, best_phase, active_demod=False)
        net_mass = active_mass - ref_mass
        results.append({
            "id": c["id"],
            "A1": c["A1"],
            "A2": c["A2"],
            "product": c["product"],
            "net_mass": net_mass
        })
        print(f"    --> Active Mass: {active_mass:.6f} | Reference Mass: {ref_mass:.6f} | Net computed: {net_mass:+.6f}")
        
    print("----------------------------------------------------------------------")
    print("  Analog Computing Scaling Analysis (After Self-Mixing Cancellation):")
    print("----------------------------------------------------------------------")
    
    # Fit scaling coefficient K: net_mass = K * (A1 * A2)
    # Using Case 1 as the reference
    base_prod = results[0]["product"]
    base_net_mass = results[0]["net_mass"]
    K = base_net_mass / base_prod
    
    print(f"  Calculated scaling coefficient (K): {K:.6f}")
    
    max_err = 0.0
    for r in results:
        expected_mass = K * r["product"]
        error = abs(r["net_mass"] - expected_mass)
        error_pct = (error / abs(expected_mass)) * 100.0 if expected_mass != 0 else 0.0
        max_err = max(max_err, error_pct)
        print(f"  {r['id']}: Product = {r['product']:2.1f} | Net Mass = {r['net_mass']:+.6f} | Expected = {expected_mass:+.6f} (Error: {error_pct:.2f}%)")
        
    print("----------------------------------------------------------------------")
    passed = max_err < 15.0
    print(f"  * Maximum scaling deviation: {max_err:.2f}%")
    print(f"  * Status: {'PASSED' if passed else 'FAILED'}")
    
    if passed:
        print("\n  [STATUS] SUCCESS: Calibrated analog multiplication proof verified!")
        print("  The two-trial cancellation successfully isolates the computed product.")
    else:
        print("\n  [STATUS] FAILED: Calibration error exceeds tolerance threshold.")
    print("======================================================================")

if __name__ == "__main__":
    main()
