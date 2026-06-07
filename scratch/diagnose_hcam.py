import sys
from pathlib import Path

# Add project root and scratch paths
sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level9_hcam import run_hcam_trial

print("Running Level 9 H-CAM Case Null diagnostic...")
delta_A, delta_B, history = run_hcam_trial("NULL")
print(f"Final results: delta_A={delta_A:+.4f}, delta_B={delta_B:+.4f}")

# Print periodic telemetry to see where the mass flows
print("\nStep-by-step Telemetry:")
print(f"{'Step':<6} | {'Reg_A_Rho':<10} | {'Bus_Rho':<10} | {'Match_A_Psi':<11} | {'Match_B_Psi':<11} | {'Val_A_Rho':<10} | {'Val_B_Rho':<10}")
print("-" * 80)
for idx, h in enumerate(history):
    # Print every 10 steps to keep output readable
    if idx % 10 == 0 or idx == len(history) - 1:
        print(f"{h['step']:<6} | {h['reg_a_rho']:<10.4f} | {h['bus_rho']:<10.4f} | {h['match_a_psi']:<11.4f} | {h['match_b_psi']:<11.4f} | {h['val_a_rho']:<10.4f} | {h['val_b_rho']:<10.4f}")
