import sys
import math
from pathlib import Path

# Add project root and scratch paths
sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, Instruction
)
from test_logos_vm_level9_hcam import (
    HCAMProcessingManifold, HCAMManifoldGroup
)
from test_isbattery_false import SwappedHCAMSequencer, run_sweep_trial_custom

def main():
    p_A = 10
    p_B = 25
    np = 18
    
    steps = 16
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    # We will assume some arbitrary placeholder phase_B and phi_in_B just to run the trials,
    # but we only look at delta_A measurements since they depend purely on phase_A, phi_in_A,
    # and the query frequency.
    phi_in_B = 0.0
    phase_B = 0.0
    
    print(f"{'phase_A':<7} | {'phi_in_A':<8} | {'A:dA':<8} | {'B:dA':<8} | {'N:dA':<8} | {'Rev:dA':<8}")
    print("-" * 60)
    
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
            
            # Print only if A:dA >= 0.2 and all other rejections are < 0.1
            if dA_A >= 0.2 and dA_B < 0.1 and dA_N < 0.1 and dA_Rev < 0.1:
                print(f"{phase_A:<7.4f} | {phi_in_A:<8.4f} | {dA_A:<+8.4f} | {dA_B:<+8.4f} | {dA_N:<+8.4f} | {dA_Rev:<+8.4f} | *candidate*")
            elif dA_A >= 0.2:
                # print(f"{phase_A:<7.4f} | {phi_in_A:<8.4f} | {dA_A:<+8.4f} | {dA_B:<+8.4f} | {dA_N:<+8.4f} | {dA_Rev:<+8.4f}")
                pass

if __name__ == "__main__":
    main()
