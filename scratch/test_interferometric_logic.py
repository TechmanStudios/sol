#!/usr/bin/env python3
"""
SOL Manifold XNOR Logic Gate Proof
==================================
Demonstrates that the SOL manifold can perform binary logical computation (XNOR)
directly in-conduit. Inputs are encoded as phase-keys (0 rad for '0', pi rad for '1').
Constructive interference yields '1' (high amplitude), and destructive interference
yields '0' (low amplitude).
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
from test_interferometric_addition import build_test_graph, run_interference_trial

def main():
    print("======================================================================")
    print("  SOL MANIFOLD INTERFEROMETRIC XNOR LOGIC GATE PROOF")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 0.2
    
    # Input waves amplitude
    A = 3.0
    
    # Binary combinations
    combos = [
        {"A": 0, "B": 0, "phase_A": 0.0,         "phase_B": 0.0,         "expected_xnor": 1},
        {"A": 0, "B": 1, "phase_A": 0.0,         "phase_B": math.pi,     "expected_xnor": 0},
        {"A": 1, "B": 0, "phase_A": math.pi,     "phase_B": 0.0,         "expected_xnor": 0},
        {"A": 1, "B": 1, "phase_A": math.pi,     "phase_B": math.pi,     "expected_xnor": 1},
    ]
    
    # Amplitude threshold to distinguish 0 and 1
    # Max is ~0.026 (constructive), Min is ~0.001 (destructive)
    # Threshold at 0.010 is a very safe mid-point
    threshold = 0.010
    
    print(f"  Threshold for Logical '1': Amplitude > {threshold:.4f}\n")
    print("  Evaluating Truth Table:")
    print("  --------------------------------------------------------------------")
    print("   Input A | Input B | Phase A | Phase B | Mixer Amp | XNOR Out | Status")
    print("  --------------------------------------------------------------------")
    
    passed = True
    for c in combos:
        # Run trial
        amp = run_interference_trial(A, A, c["phase_B"] - c["phase_A"], dt, steps, c_press, damping)
        
        # Threshold logic
        xnor_out = 1 if amp > threshold else 0
        match = xnor_out == c["expected_xnor"]
        if not match:
            passed = False
            
        print(f"      {c['A']}    |    {c['B']}    |  {c['phase_A']:.2f}   |  {c['phase_B']:.2f}   |  {amp:.6f} |    {xnor_out}     | {'OK' if match else 'FAIL'}")
        
    print("  --------------------------------------------------------------------")
    print(f"  * Overall XNOR Gate Validation: {'PASSED' if passed else 'FAILED'}")
    
    if passed:
        print("\n  [STATUS] SUCCESS: Manifold XNOR logic gate verified!")
        print("  Binary inputs were computed to XNOR outputs using pure wave interferometry.")
    else:
        print("\n  [STATUS] FAILED: Logic outputs do not match expected truth table.")
    print("======================================================================")

if __name__ == "__main__":
    main()
