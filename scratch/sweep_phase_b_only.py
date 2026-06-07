import sys
import math
from pathlib import Path

# Add project root and scratch paths
sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_isbattery_false import run_sweep_trial_custom

def main():
    p_A = 10
    p_B = 25
    np = 18
    
    # Defaults from test_logos_vm_level9_hcam.py
    phase_A = 1.5707963267948966
    phi_in_A = 2.35619449
    phi_in_B = 4.71238898
    
    steps = 32
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print(f"{'phase_B':<7} | {'B:dB':<8} | {'A:dB':<8} | {'N:dB':<8}")
    print("-" * 40)
    
    for phase_B in phases:
        # Case B: Query B (measure dB)
        _, dB_B = run_sweep_trial_custom("B", phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B)
        # Case A: Query A (measure dB)
        _, dB_A = run_sweep_trial_custom("A", phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B)
        # Case Null: Query NULL (measure dB)
        _, dB_N = run_sweep_trial_custom("NULL", phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B)
        
        status = ""
        if dB_B >= 0.2 and dB_A < 0.1 and dB_N < 0.1:
            status = " *candidate*"
            
        print(f"{phase_B:<7.4f} | {dB_B:<+8.4f} | {dB_A:<+8.4f} | {dB_N:<+8.4f}{status}")

if __name__ == "__main__":
    main()
