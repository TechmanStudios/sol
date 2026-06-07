import sys
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm import run_level11_trial

def main():
    baseline = 15.0
    query_steps = 150
    settle_steps = 0
    
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print("Running diagnostic sweep for all 8 channels...")
    for f_idx in range(4):
        p = [10.0, 14.0, 18.0, 22.0][f_idx]
        print(f"\n--- Period {p} ---")
        for is_cosine in [False, True]:
            channel_name = "Cosine" if is_cosine else "Sine"
            bit = 2 * f_idx + 1 if is_cosine else 2 * f_idx
            print(f"\nSweeping {channel_name} (Bit {bit}):")
            
            # Load only this bit
            val_X = 1 << bit
            
            for idx, ph in enumerate(phases):
                temp_phases = [0.0] * 16
                temp_phases[bit] = ph
                deltas, _ = run_level11_trial(val_X, 0, temp_phases, baseline, query_steps, settle_steps)
                d = deltas[bit]
                print(f"  Phase {ph:.4f} ({ph/math.pi:.4f}*pi) -> delta = {d:+.4f}")

if __name__ == "__main__":
    main()
