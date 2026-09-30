#!/usr/bin/env python3
"""
SOL Manifold Interferometric Half-Adder Proof
============================================
Scales the interferometric logic design to a parallel half-adder topology.
Computes Sum (XOR) and Carry (AND) simultaneously from two input wave channels
SourceA and SourceB.
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

def build_half_adder_graph() -> tuple[list[dict], list[dict]]:
    raw_nodes = [
        {"id": "SourceA", "label": "SourceA", "group": "bridge", "rho": 10.0},
        {"id": "SourceB", "label": "SourceB", "group": "bridge", "rho": 10.0},
        {"id": "SourceBias_Carry", "label": "SourceBias_Carry", "group": "bridge", "rho": 10.0},
        {"id": "Mixer_Sum", "label": "Mixer_Sum", "group": "bridge", "rho": 10.0},
        {"id": "Mixer_Carry", "label": "Mixer_Carry", "group": "bridge", "rho": 10.0},
    ]
    raw_edges = [
        # Split A to both Sum and Carry
        {"from": "SourceA", "to": "Mixer_Sum", "w0": 1.0, "kind": "tax"},
        {"from": "SourceA", "to": "Mixer_Carry", "w0": 1.0, "kind": "tax"},
        # Split B to both Sum and Carry
        {"from": "SourceB", "to": "Mixer_Sum", "w0": 1.0, "kind": "tax"},
        {"from": "SourceB", "to": "Mixer_Carry", "w0": 1.0, "kind": "tax"},
        # Connect Bias to Carry only
        {"from": "SourceBias_Carry", "to": "Mixer_Carry", "w0": 1.0, "kind": "tax"},
    ]
    return raw_nodes, raw_edges

def run_half_adder_trial(A1: float, A2: float, theta1: float, theta2: float, dt: float, steps: int, c_press: float, damping: float) -> tuple[float, float]:
    raw_nodes, raw_edges = build_half_adder_graph()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None
    
    omega = 2.0 * math.pi / (12.0 * dt)
    
    mixer_sum_rhos = []
    mixer_carry_rhos = []
    
    # Carry bias parameters
    bias_amp = 3.0
    bias_phase = math.pi
    
    for s in range(steps):
        t = s * dt
        # Drive SourceA, SourceB, and the Carry Bias channel
        engine.physics.node_by_id["SourceA"]["rho"] = 10.0 + A1 * math.sin(omega * t + theta1)
        engine.physics.node_by_id["SourceB"]["rho"] = 10.0 + A2 * math.sin(omega * t + theta2)
        engine.physics.node_by_id["SourceBias_Carry"]["rho"] = 10.0 + bias_amp * math.sin(omega * t + bias_phase)
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
        if s >= steps - 100:
            mixer_sum_rhos.append(engine.physics.node_by_id["Mixer_Sum"]["rho"])
            mixer_carry_rhos.append(engine.physics.node_by_id["Mixer_Carry"]["rho"])
            
    amp_sum = max(mixer_sum_rhos) - min(mixer_sum_rhos)
    amp_carry = max(mixer_carry_rhos) - min(mixer_carry_rhos)
    return amp_sum, amp_carry

def main():
    print("======================================================================")
    print("  SOL MANIFOLD ARITHMETIC HALF-ADDER LEDGER (INTERFEROMETRIC)")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 0.2
    
    A = 3.0
    
    # Inputs: 0 -> phase 0, 1 -> phase pi
    combos = [
        {"A": 0, "B": 0, "phase_A": 0.0,     "phase_B": 0.0,     "expected_sum": 0, "expected_carry": 0},
        {"A": 0, "B": 1, "phase_A": 0.0,     "phase_B": math.pi, "expected_sum": 1, "expected_carry": 0},
        {"A": 1, "B": 0, "phase_A": math.pi, "phase_B": 0.0,     "expected_sum": 1, "expected_carry": 0},
        {"A": 1, "B": 1, "phase_A": math.pi, "phase_B": math.pi, "expected_sum": 0, "expected_carry": 1},
    ]
    
    # Logic Thresholds (calibrated from single gate tests)
    threshold_sum = 0.010   # XOR threshold
    threshold_carry = 0.025 # AND threshold
    
    print(f"  Sum (XOR) Threshold:   {threshold_sum:.4f}")
    print(f"  Carry (AND) Threshold: {threshold_carry:.4f}\n")
    
    print("  Truth Table Verification:")
    print("  ---------------------------------------------------------------------------------------")
    print("   Input A | Input B | Sum Amp  | Carry Amp | Sum Out | Carry Out | Expected | Status")
    print("  ---------------------------------------------------------------------------------------")
    
    passed = True
    for c in combos:
        amp_sum, amp_carry = run_half_adder_trial(A, A, c["phase_A"], c["phase_B"], dt, steps, c_press, damping)
        
        # Decide output values
        # XOR logic (invert XNOR behavior):
        sum_out = 0 if amp_sum > threshold_sum else 1
        # AND logic:
        carry_out = 1 if amp_carry > threshold_carry else 0
        
        match = (sum_out == c["expected_sum"]) and (carry_out == c["expected_carry"])
        if not match:
            passed = False
            
        print(f"      {c['A']}    |    {c['B']}    | {amp_sum:.6f} | {amp_carry:.6f}  |    {sum_out}    |     {carry_out}     |  ({c['expected_sum']},{c['expected_carry']})   | {'OK' if match else 'FAIL'}")
        
    print("  ---------------------------------------------------------------------------------------")
    print(f"  * Parallel Half-Adder Suite Validation: {'PASSED' if passed else 'FAILED'}")
    
    if passed:
        print("\n  [STATUS] SUCCESS: Manifold physical half-adder verified!")
        print("  Sum and Carry bits were computed concurrently via parallel wave interference.")
    else:
        print("\n  [STATUS] FAILED: Half-adder outputs do not match expected arithmetic.")
    print("======================================================================")

if __name__ == "__main__":
    main()
