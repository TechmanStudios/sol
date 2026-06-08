import sys
import os
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_final import run_level11_trial

def main():
    baseline = 15.0
    query_steps = 120
    settle_steps = 30
    
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print("Calibration Search curves:")
    
    # Curve for Bit 0 (Sine)
    print("\n--- Bit 0 (Sine) Response Curve ---")
    print("Phase (rad) | Phase (deg) | Delta 0")
    print("-" * 35)
    for ph in phases:
        temp_phases = [0.0] * 16
        temp_phases[0] = ph
        deltas, _ = run_level11_trial(1, 0, temp_phases, baseline_rho=baseline, query_steps=query_steps, settle_steps=settle_steps)
        print(f"{ph:11.6f} | {ph*180/math.pi:11.1f} | {deltas[0]:+.6f}")
        
    # Curve for Bit 1 (Cosine)
    print("\n--- Bit 1 (Cosine) Response Curve ---")
    print("Phase (rad) | Phase (deg) | Delta 1")
    print("-" * 35)
    for ph in phases:
        temp_phases = [0.0] * 16
        temp_phases[1] = ph
        deltas, _ = run_level11_trial(2, 0, temp_phases, baseline_rho=baseline, query_steps=query_steps, settle_steps=settle_steps)
        print(f"{ph:11.6f} | {ph*180/math.pi:11.1f} | {deltas[1]:+.6f}")

if __name__ == "__main__":
    main()
