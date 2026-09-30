#!/usr/bin/env python3
"""
SOL Two-Source Manifold Analog Multiplication Proof
===================================================
Demonstrates true manifold computing: two independent input signals propagate from
separate Source nodes (A and B), superimpose and mix non-linearly at the Mixer node,
and are demodulated into the Destination node.
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
    # SourceA and SourceB converge on Mixer, which connects to Destination
    raw_nodes = [
        {"id": "SourceA", "label": "SourceA", "group": "bridge", "rho": 10.0},
        {"id": "SourceB", "label": "SourceB", "group": "bridge", "rho": 10.0},
        {"id": "Mixer", "label": "Mixer", "group": "bridge", "rho": 10.0},
        {"id": "Destination", "label": "Destination", "group": "bridge", "rho": 10.0, "semanticMass": 10000.0},
    ]
    raw_edges = [
        {"from": "SourceA", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "SourceB", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "Mixer", "to": "Destination", "w0": 1.0, "kind": "tax"},
    ]
    return raw_nodes, raw_edges

def run_multiplication_trial(A1: float, A2: float, dt: float, steps: int, c_press: float, damping: float, phase_offset: float) -> float:
    raw_nodes, raw_edges = build_test_graph()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    
    # Fundamental periods of 10 and 25 steps
    omega1 = 2.0 * math.pi / (10.0 * dt)
    omega2 = 2.0 * math.pi / (25.0 * dt)
    omega_diff = omega1 - omega2
    
    engine.write_enable("Mixer")
    engine.write_enable("Destination")
    engine.physics.node_by_id["Destination"]["rho"] = 0.0
    engine.physics.node_by_id["Mixer"]["rho"] = 0.0
    
    for s in range(steps):
        t = s * dt
        # Drive the two sources independently
        engine.physics.node_by_id["SourceA"]["rho"] = 10.0 + A1 * math.sin(omega1 * t)
        engine.physics.node_by_id["SourceB"]["rho"] = 10.0 + A2 * math.sin(omega2 * t)
        
        # Drive Mixer psi
        engine.physics.node_by_id["Mixer"]["psi"] = math.sin(omega_diff * t + phase_offset)
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
    return engine.physics.node_by_id["Destination"]["rho"]

def main():
    print("======================================================================")
    print("  SOL TWO-SOURCE MANIFOLD MULTIPLICATION PROOF")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 0.2  # Low damping for efficient wave propagation
    
    # We calibrate the phase sweep using Case 1 (A1=2, A2=2)
    # Double-differential sweep: Phase vs Phase + Pi
    print("  Step 1: Sweeping demodulator phase to calibrate propagation delay...")
    best_phase = 0.0
    best_diff = 0.0
    
    for p_idx in range(16):
        phase = (p_idx / 16.0) * 2.0 * math.pi
        mass_plus = run_multiplication_trial(2.0, 2.0, dt, steps, c_press, damping, phase)
        mass_minus = run_multiplication_trial(2.0, 2.0, dt, steps, c_press, damping, phase + math.pi)
        diff = mass_plus - mass_minus
        print(f"    Phase = {phase:5.3f} rad | A+ (phase): {mass_plus:.6f} | A- (phase+pi): {mass_minus:.6f} | Net: {diff:+.6f}")
        if abs(diff) > abs(best_diff):
            best_diff = diff
            best_phase = phase
            
    print(f"\n  --> Calibrated Phase Offset: {best_phase:.4f} rad (Max differential: {best_diff:+.6f})\n")
    
    cases = [
        {"id": "Case 1 (Small)",  "A1": 2.0, "A2": 2.0, "product": 4.0},
        {"id": "Case 2 (Medium)", "A1": 4.0, "A2": 2.0, "product": 8.0},
        {"id": "Case 3 (Large)",  "A1": 4.0, "A2": 4.0, "product": 16.0},
    ]
    
    results = []
    
    for c in cases:
        print(f"  Running {c['id']}: A1 = {c['A1']:.1f}, A2 = {c['A2']:.1f} (Expected product = {c['product']:.1f})")
        mass_plus = run_multiplication_trial(c["A1"], c["A2"], dt, steps, c_press, damping, best_phase)
        mass_minus = run_multiplication_trial(c["A1"], c["A2"], dt, steps, c_press, damping, best_phase + math.pi)
        net_mass = mass_plus - mass_minus
        results.append({
            "id": c["id"],
            "product": c["product"],
            "net_mass": net_mass
        })
        print(f"    --> A+ Mass: {mass_plus:.6f} | A- Mass: {mass_minus:.6f} | Net differential: {net_mass:+.6f}")
        
    print("----------------------------------------------------------------------")
    print("  Analog Computing Scaling Analysis (Double-Differential):")
    print("----------------------------------------------------------------------")
    
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
        print("\n  [STATUS] SUCCESS: Two-source manifold multiplication verified!")
    else:
        print("\n  [STATUS] FAILED: Scaling error exceeds tolerance threshold.")
    print("======================================================================")

if __name__ == "__main__":
    main()
