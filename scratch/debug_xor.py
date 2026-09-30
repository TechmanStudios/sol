import sys
from pathlib import Path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_hybrid_alu_expanded import run_gate_trial

history_and = run_gate_trial("AND", 1, 1)

print("Step | C_state | C_mass | C_psi | P_Sum_psi | A_psi | B_psi | A_mass | B_mass")
# Focus on compute phase: steps 110 to 164
for step in range(110, 163):
    h = history_and[step]
    print(f"{step:4d} | {h['reg_c_state']:7.1f} | {h['rho_reg_c']:6.1f} | {h['psi_sum']:9.3f} | {h['reg_a_state']:5.1f} | {h['reg_b_state']:5.1f} | {h['rho_reg_a']:6.1f} | {h['rho_reg_b']:6.1f}")
