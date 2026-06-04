import json
from pathlib import Path

results_file = Path("solResearch/nextBestTest/heartbeat_oscillator_results.json")
if not results_file.exists():
    print(f"Results file {results_file} does not exist!")
    exit(1)

with open(results_file) as f:
    data = json.load(f)

history = data["heartbeat"]["history"]

print("=== TIMELINE ANALYSIS ===")
print("Step | Phase | Surf_Act | Deep_Act | Batt_A_S | Batt_A_Chg | Host_A_Rho | Host_A_Psi | Batt_B_S | Batt_B_Chg | Host_B_Rho | Host_B_Psi")
print("-" * 125)

for h in history:  # print all steps
    print(f"{h['step']:4d} | {h['phase_value']:6.3f} | {str(h['is_surface_active']):8s} | {str(h['is_deep_active']):8s} | {h['BATTERY_A_state']:8.1f} | {h['BATTERY_A_charge']:10.4f} | {h['HOST_A_rho']:10.2f} | {h['HOST_A_psi']:10.4f} | {h['BATTERY_B_state']:8.1f} | {h['BATTERY_B_charge']:10.4f} | {h['HOST_B_rho']:10.2f} | {h['HOST_B_psi']:10.4f}")
