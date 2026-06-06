#!/usr/bin/env python3
import sys
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level8_fdm import run_fdm_trial

print("Diagnosing Case 00 (No Input):")
delta_A, delta_B, history = run_fdm_trial(False, False)
print(f"Final Deltas: delta_A={delta_A:+.4f}, delta_B={delta_B:+.4f}")
print("Selected History Steps:")
for idx in [0, 10, 20, 39, 40, 50, 54, 55, 65, 75, 95, 114, 115, 125, 134]:
    if idx < len(history):
        step_data = history[idx]
        print(f"Step {idx:3d}: reg_a_rho={step_data['reg_a_rho']:.4f}, sum_rho={step_data['sum_rho']:.4f}, out_a_rho={step_data['out_a_rho']:.4f}, out_b_rho={step_data['out_b_rho']:.4f}")

print("\nDiagnosing Case 10 (Channel A Active):")
delta_A, delta_B, history = run_fdm_trial(True, False)
print(f"Final Deltas: delta_A={delta_A:+.4f}, delta_B={delta_B:+.4f}")
print("Selected History Steps:")
for idx in [0, 10, 20, 39, 40, 50, 54, 55, 65, 75, 95, 114, 115, 125, 134]:
    if idx < len(history):
        step_data = history[idx]
        print(f"Step {idx:3d}: reg_a_rho={step_data['reg_a_rho']:.4f}, sum_rho={step_data['sum_rho']:.4f}, out_a_rho={step_data['out_a_rho']:.4f}, out_b_rho={step_data['out_b_rho']:.4f}")
