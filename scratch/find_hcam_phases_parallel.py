import sys
import math
import multiprocessing
from pathlib import Path

# Add project root and scratch paths
sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_isbattery_false import run_sweep_trial_custom

p_A = 10.0
p_B = 25.0

def eval_cand_A(args):
    phase_A, phi_in_A = args
    dA_A, _ = run_sweep_trial_custom("A", phi_in_A, 0.0, p_A, p_B, 18.0, phase_A, 0.0)
    dA_Rev, _ = run_sweep_trial_custom("PHASE_REV_A", phi_in_A, 0.0, p_A, p_B, 18.0, phase_A, 0.0)
    if dA_A >= 0.2 and dA_Rev < 0.1:
        return (phase_A, phi_in_A)
    return None

def eval_cand_B(args):
    phase_B, phi_in_B = args
    _, dB_B = run_sweep_trial_custom("B", 0.0, phi_in_B, p_A, p_B, 18.0, 0.0, phase_B)
    if dB_B >= 0.2:
        return (phase_B, phi_in_B)
    return None

def check_combination(args):
    p_A_val, phi_A_val, p_B_val, phi_B_val = args
    
    # 1. Re-evaluate dB_B under the coupled system (both gates configured)
    dA_B, dB_B = run_sweep_trial_custom("B", phi_A_val, phi_B_val, p_A, p_B, 18.0, p_A_val, p_B_val)
    if dB_B < 0.2 or dA_B >= 0.1:
        return None
        
    # 2. Re-evaluate dA_A and dB_A under the coupled system
    dA_A, dB_A = run_sweep_trial_custom("A", phi_A_val, phi_B_val, p_A, p_B, 18.0, p_A_val, p_B_val)
    if dA_A < 0.2 or dB_A >= 0.1:
        return None
        
    # 3. Check reversed phase rejection for A under coupled system
    dA_Rev, _ = run_sweep_trial_custom("PHASE_REV_A", phi_A_val, phi_B_val, p_A, p_B, 18.0, p_A_val, p_B_val)
    if dA_Rev >= 0.1:
        return None
        
    # 4. Check Null query cancellations under coupled system
    null_periods = [12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0]
    for np in null_periods:
        dA_N, dB_N = run_sweep_trial_custom("NULL", phi_A_val, phi_B_val, p_A, p_B, np, p_A_val, p_B_val)
        if dA_N < 0.1 and dB_N < 0.1:
            return {
                "phase_A": p_A_val, "phi_in_A": phi_A_val,
                "phase_B": p_B_val, "phi_in_B": phi_B_val,
                "null_period": np,
                "dA_A": dA_A, "dA_Rev": dA_Rev, "dA_B": dA_B, "dA_N": dA_N,
                "dB_B": dB_B, "dB_A": dB_A, "dB_N": dB_N
            }
    return None

def main():
    # Capped at 3 processes for safety/stability
    num_processes = 3
    print(f"Starting parallel sweep using {num_processes} processes...")
    
    steps = 16
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    # Grid search coordinates
    cand_A_tasks = [(phase_A, phi_in_A) for phase_A in phases for phi_in_A in phases]
    cand_B_tasks = [(phase_B, phi_in_B) for phase_B in phases for phi_in_B in phases]
    
    with multiprocessing.Pool(processes=num_processes) as pool:
        print("Step 1: Finding candidates for Channel A...")
        candidates_A_raw = pool.map(eval_cand_A, cand_A_tasks)
        candidates_A = [c for c in candidates_A_raw if c is not None]
        print(f"Found {len(candidates_A)} candidates for Channel A.")
        
        print("Step 2: Finding candidates for Channel B...")
        candidates_B_raw = pool.map(eval_cand_B, cand_B_tasks)
        candidates_B = [c for c in candidates_B_raw if c is not None]
        print(f"Found {len(candidates_B)} candidates for Channel B.")
        
        print("Step 3: Checking coupled combinations...")
        combo_tasks = []
        for p_A_val, phi_A_val in candidates_A:
            for p_B_val, phi_B_val in candidates_B:
                combo_tasks.append((p_A_val, phi_A_val, p_B_val, phi_B_val))
                
        print(f"Checking {len(combo_tasks)} coupled combinations...")
        # Use imap_unordered to stop early when a solution is found
        for result in pool.imap_unordered(check_combination, combo_tasks):
            if result is not None:
                print(f"\n*** SUCCESSFUL SOLUTION FOUND ***")
                print(f"phase_A  = {result['phase_A']:.6f} ({result['phase_A']/math.pi:.4f} * pi)")
                print(f"phi_in_A = {result['phi_in_A']:.6f} ({result['phi_in_A']/math.pi:.4f} * pi)")
                print(f"phase_B  = {result['phase_B']:.6f} ({result['phase_B']/math.pi:.4f} * pi)")
                print(f"phi_in_B = {result['phi_in_B']:.6f} ({result['phi_in_B']/math.pi:.4f} * pi)")
                print(f"null_period = {result['null_period']}")
                print(f"dA_A={result['dA_A']:+.4f}, dA_Rev={result['dA_Rev']:+.4f}, dA_B={result['dA_B']:+.4f}, dA_N={result['dA_N']:+.4f}")
                print(f"dB_B={result['dB_B']:+.4f}, dB_A={result['dB_A']:+.4f}, dB_N={result['dB_N']:+.4f}")
                
                # Terminate pool and exit
                pool.terminate()
                sys.exit(0)
                
    print("Sweep complete. No successful solutions found.")

if __name__ == "__main__":
    main()
