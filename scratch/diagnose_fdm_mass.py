import sys
import math
from pathlib import Path

# Add project root and scratch paths
sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level8_fdm import run_fdm_trial

print("Running Level 8 FDM Case 10 diagnostic...")
delta_A, delta_B, history = run_fdm_trial(True, False)
print(f"Final results: delta_A={delta_A:+.4f}, delta_B={delta_B:+.4f}")

# Print periodic telemetry to see where the mass flows
print("\nStep-by-step Telemetry:")
print(f"{'Step':<6} | {'Reg_Host_Rho':<12} | {'Reg_Bat_Rho':<12} | {'Sum_Rho':<10} | {'Router_A_Psi':<12} | {'Router_B_Psi':<12} | {'Out_A_Rho':<10} | {'Out_B_Rho':<10}")
print("-" * 100)
for idx, h in enumerate(history):
    # Print every 10 steps to keep output readable
    if idx % 10 == 0 or idx == len(history) - 1:
        # get host and bat rho at this step
        # Note: history only recorded the sum of host and bat rho as reg_a_rho? No, let's check what history holds.
        # history in FDM holds: "reg_a_rho": float(host_a["rho"])
        # wait! It didn't hold bat_a["rho"] separately.
        print(f"{h['step']:<6} | {h['reg_a_rho']:<12.4f} | {'N/A':<12} | {h['sum_rho']:<10.4f} | {h['router_a_psi']:<12.4f} | {h['router_b_psi']:<12.4f} | {h['out_a_rho']:<10.4f} | {h['out_b_rho']:<10.4f}")
