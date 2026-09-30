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
    
    steps = 16
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print("Step 1: Finding candidates for Channel A (matching A and rejecting reversed-phase A)...")
    candidates_A = []
    for phase_A in phases:
        for phi_in_A in phases:
            dA_A, _ = run_sweep_trial_custom("A", phi_in_A, 0.0, p_A, p_B, 18.0, phase_A, 0.0)
            dA_Rev, _ = run_sweep_trial_custom("PHASE_REV_A", phi_in_A, 0.0, p_A, p_B, 18.0, phase_A, 0.0)
            if dA_A >= 0.2 and dA_Rev < 0.1:
                candidates_A.append((phase_A, phi_in_A))
                
    print(f"Found {len(candidates_A)} candidates for Channel A.")
    
    print("\nStep 2: Finding candidates for Channel B (matching B)...")
    candidates_B = []
    for phase_B in phases:
        for phi_in_B in phases:
            _, dB_B = run_sweep_trial_custom("B", 0.0, phi_in_B, p_A, p_B, 18.0, 0.0, phase_B)
            if dB_B >= 0.2:
                candidates_B.append((phase_B, phi_in_B))
                
    print(f"Found {len(candidates_B)} candidates for Channel B.")
    
    print("\nStep 3: Checking coupled cross-rejections, coupled matches, and Null query cancellations...")
    
    null_periods = [12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]
    
    found_sol = False
    for p_A_val, phi_A_val in candidates_A:
        for p_B_val, phi_B_val in candidates_B:
            # 1. Re-evaluate dB_B under the coupled system (both gates configured)
            dA_B, dB_B = run_sweep_trial_custom("B", phi_A_val, phi_B_val, p_A, p_B, 18.0, p_A_val, p_B_val)
            if dB_B < 0.2:
                continue
            if dA_B >= 0.1:
                continue
                
            # 2. Re-evaluate dA_A and dB_A under the coupled system
            dA_A, dB_A = run_sweep_trial_custom("A", phi_A_val, phi_B_val, p_A, p_B, 18.0, p_A_val, p_B_val)
            if dA_A < 0.2:
                continue
            if dB_A >= 0.1:
                continue
                
            # 3. Check reversed phase rejection for A under coupled system
            dA_Rev, _ = run_sweep_trial_custom("PHASE_REV_A", phi_A_val, phi_B_val, p_A, p_B, 18.0, p_A_val, p_B_val)
            if dA_Rev >= 0.1:
                continue
                
            # 4. Check Null query cancellations under coupled system
            for np in null_periods:
                dA_N, dB_N = run_sweep_trial_custom("NULL", phi_A_val, phi_B_val, p_A, p_B, np, p_A_val, p_B_val)
                if dA_N < 0.1 and dB_N < 0.1:
                    print(f"\n*** SUCCESSFUL SOLUTIONS FOUND ***")
                    print(f"phase_A  = {p_A_val:.6f} ({p_A_val/math.pi:.4f} * pi)")
                    print(f"phi_in_A = {phi_A_val:.6f} ({phi_A_val/math.pi:.4f} * pi)")
                    print(f"phase_B  = {p_B_val:.6f} ({p_B_val/math.pi:.4f} * pi)")
                    print(f"phi_in_B = {phi_B_val:.6f} ({phi_B_val/math.pi:.4f} * pi)")
                    print(f"null_period = {np}")
                    print(f"dA_A={dA_A:+.4f}, dA_Rev={dA_Rev:+.4f}, dA_B={dA_B:+.4f}, dA_N={dA_N:+.4f}")
                    print(f"dB_B={dB_B:+.4f}, dB_A={dB_A:+.4f}, dB_N={dB_N:+.4f}")
                    found_sol = True
                    break
            if found_sol:
                break
        if found_sol:
            break

if __name__ == "__main__":
    main()
