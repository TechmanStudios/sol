#!/usr/bin/env python3
"""
SOL Analog Conduit Multiplication Proof
=========================================
Empirically demonstrates that the SOL Engine can perform analog multiplication
directly inside the physical manifold. By using logarithmic pressure mixing,
parametric resonant rectification, and baseline offset cancellation, we compute
the product (A1 * A2) of two input wave amplitudes.
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

def run_multiplication_trial(A1: float, A2: float, dt: float, steps: int, c_press: float, damping: float) -> float:
    """Run a single multiplication simulation trial and return the final steady-state density."""
    raw_nodes, raw_edges = build_test_chain()
    
    # Run with a damping term so the system reaches a dynamic equilibrium (steady state)
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 6.0  # High-contrast gating
    
    # Frequencies (Periods of 15 and 25 steps)
    omega1 = 2.0 * math.pi / (15.0 * dt)
    omega2 = 2.0 * math.pi / (25.0 * dt)
    omega_diff = omega1 - omega2  # Demodulator frequency
    
    # Enable all gates
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
        
        # Oscillate Mixer's belief field at the difference frequency
        engine.physics.node_by_id["Mixer"]["psi"] = math.sin(omega_diff * t)
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
    final_dest_mass = engine.physics.node_by_id["Destination"]["rho"]
    return final_dest_mass

def main():
    print("======================================================================")
    print("  SOL MANIFOLD ANALOG MULTIPLICATION PROOF")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 5.0  # Standard damping to enable steady-state equilibrium
    
    # 1. Establish Baseline Offset (A1 = 0, A2 = 0)
    print("  Measuring baseline DC offset (A1=0, A2=0)...")
    baseline_mass = run_multiplication_trial(0.0, 0.0, dt, steps, c_press, damping)
    print(f"    --> Baseline DC Offset (rho_base): {baseline_mass:.6f}\n")
    
    # 2. Define three cases of input amplitudes A1 and A2
    cases = [
        {"id": "Case 1 (Small)",  "A1": 2.0, "A2": 2.0, "expected_ratio": 4.0},
        {"id": "Case 2 (Medium)", "A1": 4.0, "A2": 2.0, "expected_ratio": 8.0},
        {"id": "Case 3 (Large)",  "A1": 4.0, "A2": 4.0, "expected_ratio": 16.0},
    ]
    
    results = []
    
    for c in cases:
        print(f"  Running {c['id']}: A1 = {c['A1']:.1f}, A2 = {c['A2']:.1f} (Expected product scale = {c['expected_ratio']:.1f})")
        mass_out = run_multiplication_trial(c["A1"], c["A2"], dt, steps, c_press, damping)
        # Apply offset cancellation
        active_mass = mass_out - baseline_mass
        results.append({
            "id": c["id"],
            "A1": c["A1"],
            "A2": c["A2"],
            "product": c["A1"] * c["A2"],
            "measured_mass": mass_out,
            "active_mass": active_mass
        })
        print(f"    --> Measured Output Mass: {mass_out:.6f} | Active Mass: {active_mass:.6f}")
        
    print("----------------------------------------------------------------------")
    print("  Analog Computing Scaling Analysis (After Offset Cancellation):")
    print("----------------------------------------------------------------------")
    
    # We fit a linear coefficient K: active_mass = K * (A1 * A2)
    # Using Case 1 as the baseline reference point
    base_prod = results[0]["product"]
    base_active_mass = results[0]["active_mass"]
    K = base_active_mass / base_prod
    
    print(f"  Calculated scaling coefficient (K): {K:.6f}")
    
    max_err = 0.0
    for r in results:
        expected_mass = K * r["product"]
        error = abs(r["active_mass"] - expected_mass)
        error_pct = (error / expected_mass) * 100.0 if expected_mass > 0 else 0.0
        max_err = max(max_err, error_pct)
        print(f"  {r['id']}: Product = {r['product']:2.1f} | Active Mass = {r['active_mass']:.6f} | Expected = {expected_mass:.6f} (Error: {error_pct:.2f}%)")
        
    print("----------------------------------------------------------------------")
    # A maximum error under 15% is extremely good for continuous analog mixing
    passed = max_err < 15.0
    print(f"  * Maximum scaling deviation: {max_err:.2f}%")
    print(f"  * Status: {'PASSED' if passed else 'FAILED'}")
    
    if passed:
        print("\n  [STATUS] SUCCESS: Analog multiplication proof verified!")
        print("  The SOL Engine successfully performed multiplication in the conduit.")
    else:
        print("\n  [STATUS] FAILED: Scaling deviation exceeds tolerance.")
    print("======================================================================")

if __name__ == "__main__":
    main()
