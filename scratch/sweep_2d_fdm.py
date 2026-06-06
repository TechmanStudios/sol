#!/usr/bin/env python3
import sys
import math
import json
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_tune_fdm import run_fdm_trial

def main():
    baseline = 1.5
    if len(sys.argv) > 1:
        baseline = float(sys.argv[1])
        
    steps = 16
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print(f"Starting 2D phase sweep ({steps}x{steps} = {steps*steps} combinations)...")
    
    best_score = -1
    best_phases = None
    best_deltas = None
    
    for i, p_A in enumerate(phases):
        for j, p_B in enumerate(phases):
            # Run all 4 cases
            try:
                d00_A, d00_B, h00 = run_fdm_trial(False, False, baseline, p_A, p_B)
                d10_A, d10_B, h10 = run_fdm_trial(True, False, baseline, p_A, p_B)
                d01_A, d01_B, h01 = run_fdm_trial(False, True, baseline, p_A, p_B)
                d11_A, d11_B, h11 = run_fdm_trial(True, True, baseline, p_A, p_B)
            except Exception as e:
                continue
                
            # Check invariants
            m00 = h00[-1]["min_active_register_mass"]
            m10 = h10[-1]["min_active_register_mass"]
            m01 = h01[-1]["min_active_register_mass"]
            m11 = h11[-1]["min_active_register_mass"]
            
            # Criteria checks
            cond_00 = (d00_A < 0.1) and (d00_B < 0.1)
            cond_10 = (d10_A >= 0.2) and (d10_B < 0.1)
            cond_01 = (d01_A < 0.1) and (d01_B >= 0.2)
            cond_11 = (d11_A >= 0.2) and (d11_B >= 0.2)
            cond_mass = min(m00, m10, m01, m11) >= 14.0
            
            passed_cases = sum([cond_00, cond_10, cond_01, cond_11, cond_mass])
            
            # Print if we pass at least 3 cases
            if passed_cases >= 3:
                print(f"Phases A={p_A:.3f}, B={p_B:.3f} | Score={passed_cases}/5")
                print(f"  00: A={d00_A:+.3f}, B={d00_B:+.3f}")
                print(f"  10: A={d10_A:+.3f}, B={d10_B:+.3f}")
                print(f"  01: A={d01_A:+.3f}, B={d01_B:+.3f}")
                print(f"  11: A={d11_A:+.3f}, B={d11_B:+.3f}")
                print(f"  Min Mass = {min(m00, m10, m01, m11):.1f}")
                
            if passed_cases > best_score:
                best_score = passed_cases
                best_phases = (p_A, p_B)
                best_deltas = (d00_A, d00_B, d10_A, d10_B, d01_A, d01_B, d11_A, d11_B)
                
    print("\n=== SWEEP COMPLETED ===")
    if best_phases:
        p_A, p_B = best_phases
        print(f"Best Phases: A = {p_A:.4f}, B = {p_B:.4f} (Score: {best_score}/5)")
        print(f"Deltas at best phases:")
        print(f"  Case 00: A={best_deltas[0]:+.4f}, B={best_deltas[1]:+.4f}")
        print(f"  Case 10: A={best_deltas[2]:+.4f}, B={best_deltas[3]:+.4f}")
        print(f"  Case 01: A={best_deltas[4]:+.4f}, B={best_deltas[5]:+.4f}")
        print(f"  Case 11: A={best_deltas[6]:+.4f}, B={best_deltas[7]:+.4f}")
    else:
        print("No valid configurations found.")

if __name__ == "__main__":
    main()
