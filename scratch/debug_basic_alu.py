import sys
import os
from pathlib import Path

# Add project root and scratch paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_hybrid_alu import run_hybrid_alu_trial

res = run_hybrid_alu_trial(1, 0, "AND")

print("Step | C_state | C_mass | Sum_psi | A_psi | B_psi | C_psi | A_mass | B_mass")
# Compute is steps 50 to 80.
for step in range(50, 100):
    print(f"{step:4d} | {res['state_c'][step]:7.1f} | {res['rho_host_c'][step]:6.1f} | {res['psi_sum'][step]:9.3f} | {res['state_a'][step]:5.1f} | {res['state_b'][step]:5.1f} | {res['psi_host_c'][step]:5.2f} | {res['rho_host_a'][step]:6.1f} | {res['rho_host_b'][step]:6.1f}")
