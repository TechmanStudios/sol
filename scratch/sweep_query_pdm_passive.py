import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_passive import run_level11_trial, calibrate_pdm_phases

def test_query_steps(query_steps):
    print(f"\n--- Testing query_steps = {query_steps} ---", flush=True)
    baseline = 15.0
    settle_steps = 0
    try:
        calibrated_phases = calibrate_pdm_phases(baseline, query_steps, settle_steps)
    except Exception as e:
        print(f"Calibration failed: {e}")
        return False
        
    cases = [
        {
            "name": "Case A: Single-Register 16-Bit Word Recall",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case B: Simultaneous Dual-Register Parallel Recall",
            "val_X": 0b1010000000001111,
            "val_Y": 0b0101111111110000,
            "expected_X": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            "expected_Y": [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0]
        },
        {
            "name": "Case C: Selective Bit Masking (Odd Bits)",
            "val_X": 0b1010101010101010,
            "val_Y": 0,
            "expected_X": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case D: Phase-Reversed Rejection",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        }
    ]
    
    suite_ok = True
    worst_min_mass = float('inf')
    
    for idx, c in enumerate(cases):
        if idx == 3: # Case D
            phases = list(calibrated_phases)
            phases[0] = (phases[0] + math.pi) % (2 * math.pi)
            deltas, history = run_level11_trial(c["val_X"], c["val_Y"], phases, baseline, query_steps, settle_steps)
        else:
            deltas, history = run_level11_trial(c["val_X"], c["val_Y"], calibrated_phases, baseline, query_steps, settle_steps)
            
        passed = True
        if idx == 1:
            expected = [c["expected_X"][i] | c["expected_Y"][i] for i in range(16)]
        else:
            expected = c["expected_X"]
            
        if idx == 3:
            expected[0] = 0
            
        for i in range(16):
            exp_val = expected[i]
            d = deltas[i]
            if exp_val == 1:
                if d < 0.2:
                    passed = False
            else:
                if d >= 0.1:
                    passed = False
                    
        min_mass = history[-1]["min_active_register_mass"]
        if min_mass < worst_min_mass:
            worst_min_mass = min_mass
        print(f"  {c['name']}: passed={passed}, min_mass={min_mass:.2f}")
        if not passed:
            suite_ok = False
            
    mass_ok = worst_min_mass >= 14.0
    print(f"  Suite verdict: {suite_ok and mass_ok} (suite_ok={suite_ok}, mass_ok={mass_ok})")
    return suite_ok and mass_ok

def main():
    for q_steps in [20, 25, 30, 35, 40, 45, 50, 60, 80]:
        if test_query_steps(q_steps):
            print(f"SUCCESS: query_steps = {q_steps} passes all cases!")
            break

if __name__ == "__main__":
    main()
