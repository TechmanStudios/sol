import sys
import os
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_prime import run_level11_trial

def main():
    baseline = 15.0
    steps = 24  # 24 steps for fine resolution
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print("Fine Phase Sweep for Sine bits:")
    for b in [0, 2, 4, 6]:
        b_local = b % 8
        f_idx = b_local // 2
        p = [13.0, 17.0, 19.0, 23.0][f_idx]
        print(f"\nSweeping bit {b} (period {p}):")
        
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[b] = ph
            val_X = (1 << b)
            deltas, _ = run_level11_trial(val_X, 0, temp_phases, is_calibrating=True, baseline_rho=baseline, query_steps=40, settle_steps=15)
            print(f"  phase = {ph:.4f} ({ph/math.pi:.4f} * pi) -> delta = {deltas[b]:+.4f}")

if __name__ == "__main__":
    main()
