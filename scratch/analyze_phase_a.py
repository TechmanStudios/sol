import sys
import math
import json
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
    
    steps = 8  # 8 steps to make it fast
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    phi_in_B = 0.0
    phase_B = 0.0
    
    results = []
    
    for phase_A in phases:
        for phi_in_A in phases:
            # Case A: Query A
            dA_A, _ = run_sweep_trial_custom("A", phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B)
            # Case B: Query B
            dA_B, _ = run_sweep_trial_custom("B", phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B)
            # Case Null: Query NULL
            dA_N, _ = run_sweep_trial_custom("NULL", phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B)
            # Case Phase: Query PHASE_REV_A
            dA_Rev, _ = run_sweep_trial_custom("PHASE_REV_A", phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B)
            
            results.append({
                "phase_A": phase_A,
                "phi_in_A": phi_in_A,
                "dA_A": dA_A,
                "dA_B": dA_B,
                "dA_N": dA_N,
                "dA_Rev": dA_Rev
            })
            
    # Save results to JSON
    out_path = sol_root / "scratch" / "sweep_phase_a_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Sweep completed. Saved {len(results)} results to {out_path}")

if __name__ == "__main__":
    main()
