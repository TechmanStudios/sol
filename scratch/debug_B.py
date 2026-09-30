import sys
import math
from pathlib import Path

# Add project root and scratch paths
sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level9_hcam import run_hcam_trial
from test_isbattery_false import run_sweep_trial_custom

def main():
    phase_A = 0.39269908169872414
    phi_in_A = 0.78539816
    phase_B = 1.5707963267948966
    phi_in_B = 1.96349541
    
    print("Running Trial B via test_logos_vm_level9_hcam...")
    dA_real, dB_real, hist_real = run_hcam_trial("B", baseline_rho=15.0, phase_A=phase_A, phase_B=phase_B)
    
    print("\nRunning Trial B via run_sweep_trial_custom...")
    # SwappedHCAMSequencer uses phi_in_A, phi_in_B as arguments
    dA_sweep, dB_sweep = run_sweep_trial_custom("B", phi_in_A, phi_in_B, 10.0, 25.0, 14.0, phase_A, phase_B)
    
    print(f"\nFinal delta_B Comparison:")
    print(f"  Real Run:  delta_B = {dB_real:+.6f}")
    print(f"  Sweep Run: delta_B = {dB_sweep:+.6f}")

if __name__ == "__main__":
    main()
