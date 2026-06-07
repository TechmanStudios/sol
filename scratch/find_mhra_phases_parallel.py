#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# See LICENSE in the repository root for details.
"""
Parallel 4D phase/frequency search for SOL Level 10 MHRA
========================================================
"""
import sys
import math
import multiprocessing
import time
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level10_mhra import run_mhra_trial

p_A = 10.0
p_B = 25.0

def check_combination(args):
    phase_A, phi_in_A, phase_B, phi_in_B, null_period = args
    
    # 1. Verify Case C (Parallel Superimposed Recall)
    dA_C, dB_C, hist_C = run_mhra_trial("A", "B", 15.0, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    min_mass_C = hist_C[-1]["min_active_register_mass"]
    if dA_C < 0.2 or dB_C < 0.2 or min_mass_C < 14.0:
        return None
        
    # 2. Verify Case A (A active, B silent)
    dA_A, dB_A, hist_A = run_mhra_trial("A", "NULL", 15.0, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    min_mass_A = hist_A[-1]["min_active_register_mass"]
    if dA_A < 0.2 or dB_A >= 0.1 or min_mass_A < 14.0:
        return None
        
    # 3. Verify Case B (A silent, B active)
    dA_B, dB_B, hist_B = run_mhra_trial("NULL", "B", 15.0, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    min_mass_B = hist_B[-1]["min_active_register_mass"]
    if dB_B < 0.2 or dA_B >= 0.1 or min_mass_B < 14.0:
        return None
        
    # 4. Verify Case D (Phase-reversed rejection)
    dA_D, dB_D, hist_D = run_mhra_trial("PHASE_REV_A", "NULL", 15.0, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    if dA_D >= 0.1 or dB_D >= 0.1:
        return None
        
    # 5. Verify Case E (Both silent)
    dA_E, dB_E, hist_E = run_mhra_trial("NULL", "NULL", 15.0, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    if dA_E >= 0.1 or dB_E >= 0.1:
        return None
        
    return {
        "phase_A": phase_A, "phi_in_A": phi_in_A,
        "phase_B": phase_B, "phi_in_B": phi_in_B,
        "null_period": null_period,
        "dA_A": dA_A, "dB_A": dB_A,
        "dA_B": dA_B, "dB_B": dB_B,
        "dA_C": dA_C, "dB_C": dB_C,
        "dA_D": dA_D, "dB_D": dB_D,
        "min_mass": min(min_mass_C, min_mass_A, min_mass_B)
    }

def main():
    num_processes = 3
    print(f"Starting Level 10 4D parallel sweep using {num_processes} processes...")
    
    # 8 steps of phase (45 degrees increments)
    steps = 8
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    null_periods = [13.0, 15.0, 18.0]
    
    for np in null_periods:
        print(f"\n--- Sweeping with null_period = {np} ---")
        tasks = []
        for phase_A in phases:
            for phi_in_A in phases:
                for phase_B in phases:
                    for phi_in_B in phases:
                        tasks.append((phase_A, phi_in_A, phase_B, phi_in_B, np))
                        
        print(f"Total tasks to check: {len(tasks)}")
        
        with multiprocessing.Pool(processes=num_processes) as pool:
            # Use imap_unordered to stop on first success
            for result in pool.imap_unordered(check_combination, tasks):
                if result is not None:
                    print(f"\n*** SUCCESSFUL SOLUTION FOUND ***")
                    print(f"phase_A  = {result['phase_A']:.6f} ({result['phase_A']/math.pi:.4f} * pi)")
                    print(f"phi_in_A = {result['phi_in_A']:.6f} ({result['phi_in_A']/math.pi:.4f} * pi)")
                    print(f"phase_B  = {result['phase_B']:.6f} ({result['phase_B']/math.pi:.4f} * pi)")
                    print(f"phi_in_B = {result['phi_in_B']:.6f} ({result['phi_in_B']/math.pi:.4f} * pi)")
                    print(f"null_period = {result['null_period']}")
                    print(f"Case A: dA_A={result['dA_A']:+.4f}, dB_A={result['dB_A']:+.4f}")
                    print(f"Case B: dA_B={result['dA_B']:+.4f}, dB_B={result['dB_B']:+.4f}")
                    print(f"Case C: dA_C={result['dA_C']:+.4f}, dB_C={result['dB_C']:+.4f}")
                    print(f"Worst min_mass = {result['min_mass']:.2f}")
                    
                    pool.terminate()
                    sys.exit(0)
                    
    print("\nSweep complete. No successful solutions found.")
    sys.exit(1)

if __name__ == "__main__":
    main()
