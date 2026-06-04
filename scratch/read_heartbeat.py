import json
from pathlib import Path

results_file = Path("solResearch/nextBestTest/heartbeat_oscillator_results.json")
if not results_file.exists():
    print(f"Results file {results_file} does not exist!")
    exit(1)

with open(results_file) as f:
    data = json.load(f)

history = data["heartbeat"]["history"]

print("Step | Phase | Batt_A_S | Host_A_Rho | Host_A_Psi | GATE_AB_Psi | Host_B_Rho | Host_B_Psi | Batt_B_Chg | Batt_B_S")
print("-" * 120)

for h in history[0:45]:
    print(f"{h['step']:4d} | {h['phase_value']:5.2f} | {h['BATTERY_A_state']:8.1f} | {h['HOST_A_rho']:10.2f} | {h['HOST_A_psi']:10.4f} | {h['GATE_AB_psi']:11.4f} | {h['HOST_B_rho']:10.2f} | {h['HOST_B_psi']:10.4f} | {h['BATTERY_B_charge']:10.4f} | {h['BATTERY_B_state']:8.1f}")
