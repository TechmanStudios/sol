#!/usr/bin/env python3
"""
SOL Analog Conduit Multiplication with Positive-Only Mass Injection
===================================================================
Drives the manifold by injecting mass dynamically (I0 * (1 + sin(omega * t)) * dt)
into Source A and Source B, preserving natural pressure-flow conservation and
proving that the rectified output scales quadratically (I0^2) with the injection scale.
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
    raw_nodes = [
        {"id": "SourceA", "label": "SourceA", "group": "bridge", "rho": 0.0},
        {"id": "SourceB", "label": "SourceB", "group": "bridge", "rho": 0.0},
        {"id": "Mixer", "label": "Mixer", "group": "bridge", "rho": 0.0},
        {"id": "Destination", "label": "Destination", "group": "bridge", "rho": 0.0, "semanticMass": 10000.0},
    ]
    raw_edges = [
        {"from": "SourceA", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "SourceB", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "Mixer", "to": "Destination", "w0": 1.0, "kind": "tax"},
    ]
    return raw_nodes, raw_edges

def run_multiplication_trial(I0: float, dt: float, steps: int, c_press: float, damping: float, phase_offset: float) -> float:
    raw_nodes, raw_edges = build_test_graph()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None  # Disable MHD feedback
    
    omega1 = 2.0 * math.pi / (10.0 * dt)
    omega2 = 2.0 * math.pi / (25.0 * dt)
    omega_diff = omega1 - omega2
    
    engine.write_enable("Mixer")
    engine.write_enable("Destination")
    
    for s in range(steps):
        t = s * dt
        # Calculate dynamic mass injection rate
        injA = I0 * (1.0 + math.sin(omega1 * t)) * dt
        injB = I0 * (1.0 + math.sin(omega2 * t)) * dt
        
        engine.inject_by_id("SourceA", injA)
        engine.inject_by_id("SourceB", injB)
        
        # Drive Mixer psi and psi_bias
        val = math.sin(omega_diff * t + phase_offset)
        engine.physics.node_by_id["Mixer"]["psi"] = val
        engine.physics.node_by_id["Mixer"]["psi_bias"] = val
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
    return engine.physics.node_by_id["Destination"]["rho"]

def main():
    print("======================================================================")
    print("  SOL MANIFOLD MULTIPLICATION VIA MASS INJECTION")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 1.0  # Standard damping to bound total mass
    
    # Step 1: Calibrate phase sweep using I0 = 1.0
    print("  Step 1: Sweeping demodulator phase to calibrate propagation delay...")
    best_phase = 0.0
    best_diff = 0.0
    
    for p_idx in range(16):
        phase = (p_idx / 16.0) * 2.0 * math.pi
        mass_plus = run_multiplication_trial(1.0, dt, steps, c_press, damping, phase)
        mass_minus = run_multiplication_trial(1.0, dt, steps, c_press, damping, phase + math.pi)
        diff = mass_plus - mass_minus
        print(f"    Phase = {phase:5.3f} rad | A+ (phase): {mass_plus:.6f} | A- (phase+pi): {mass_minus:.6f} | Net: {diff:+.6f}")
        if abs(diff) > abs(best_diff):
            best_diff = diff
            best_phase = phase
            
    print(f"\n  --> Calibrated Phase Offset: {best_phase:.4f} rad (Max differential: {best_diff:+.6f})\n")
    
    # Step 2: Run scaling cases
    cases = [
        {"id": "Case 1 (Small)",  "I0": 1.0, "expected_ratio": 1.0},
        {"id": "Case 2 (Medium)", "I0": 2.0, "expected_ratio": 4.0},
        {"id": "Case 3 (Large)",  "I0": 3.0, "expected_ratio": 9.0},
    ]
    
    results = []
    
    for c in cases:
        print(f"  Running {c['id']}: I0 = {c['I0']:.1f} (Expected scaling scale = {c['expected_ratio']:.1f})")
        mass_plus = run_multiplication_trial(c["I0"], dt, steps, c_press, damping, best_phase)
        mass_minus = run_multiplication_trial(c["I0"], dt, steps, c_press, damping, best_phase + math.pi)
        net_mass = mass_plus - mass_minus
        results.append({
            "id": c["id"],
            "I0": c["I0"],
            "expected_ratio": c["expected_ratio"],
            "net_mass": net_mass
        })
        print(f"    --> A+ Mass: {mass_plus:.6f} | A- Mass: {mass_minus:.6f} | Net differential: {net_mass:+.6f}")
        
    print("----------------------------------------------------------------------")
    print("  Analog Computing Scaling Analysis (Double-Differential):")
    print("----------------------------------------------------------------------")
    
    # Fit scaling coefficient K: net_mass = K * I0^2
    base_ratio = results[0]["expected_ratio"]
    base_net_mass = results[0]["net_mass"]
    K = base_net_mass / base_ratio
    print(f"  Calculated scaling coefficient (K): {K:.6f}")
    
    max_err = 0.0
    for r in results:
        expected_mass = K * r["expected_ratio"]
        error = abs(r["net_mass"] - expected_mass)
        error_pct = (error / abs(expected_mass)) * 100.0 if expected_mass != 0 else 0.0
        max_err = max(max_err, error_pct)
        print(f"  {r['id']}: I0 = {r['I0']:.1f} | Net Mass = {r['net_mass']:+.6f} | Expected = {expected_mass:+.6f} (Error: {error_pct:.2f}%)")
        
    print("----------------------------------------------------------------------")
    passed = max_err < 15.0
    print(f"  * Maximum scaling deviation: {max_err:.2f}%")
    print(f"  * Status: {'PASSED' if passed else 'FAILED'}")
    
    if passed:
        print("\n  [STATUS] SUCCESS: Mass-injected manifold multiplication verified!")
    else:
        print("\n  [STATUS] FAILED: Scaling error exceeds tolerance threshold.")
    print("======================================================================")

if __name__ == "__main__":
    main()
