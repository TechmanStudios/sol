import json
from pathlib import Path

results_file = Path("solResearch/nextBestTest/jeans_rom_results.json")
if not results_file.exists():
    print(f"Results file {results_file} does not exist!")
    exit(1)

with open(results_file) as f:
    data = json.load(f)

jeans = data["jeans"]
history = jeans["history"]

print("=== SETTLE PHASE (First 5 steps and Last 5 steps) ===")
settle = [h for h in history if h["phase"] == "SETTLE"]
for h in settle[:5]:
    print(f"Step {h['step']}: host_rho={h['HOST_rho']:.4f}, buffer_rho={h['BUFFER_rho']:.4f}, host_psi={h['HOST_psi']:.4f}, host_z={h['HOST_z']:.4f}, j_val={h['HOST_j_val']:.4f}, isStellar={h['HOST_isStellar']}")
print("...")
for h in settle[-5:]:
    print(f"Step {h['step']}: host_rho={h['HOST_rho']:.4f}, buffer_rho={h['BUFFER_rho']:.4f}, host_psi={h['HOST_psi']:.4f}, host_z={h['HOST_z']:.4f}, j_val={h['HOST_j_val']:.4f}, isStellar={h['HOST_isStellar']}")

print("\n=== NOISE PHASE (First 15 steps) ===")
noise = [h for h in history if h["phase"] == "NOISE"]
for h in noise[:15]:
    print(f"Step {h['step']}: host_rho={h['HOST_rho']:.4f}, buffer_rho={h['BUFFER_rho']:.4f}, host_psi={h['HOST_psi']:.4f}, host_z={h['HOST_z']:.4f}, j_val={h['HOST_j_val']:.4f}, isStellar={h['HOST_isStellar']}")

print("\n=== NOISE PHASE (Last 5 steps) ===")
for h in noise[-5:]:
    print(f"Step {h['step']}: host_rho={h['HOST_rho']:.4f}, buffer_rho={h['BUFFER_rho']:.4f}, host_psi={h['HOST_psi']:.4f}, host_z={h['HOST_z']:.4f}, j_val={h['HOST_j_val']:.4f}, isStellar={h['HOST_isStellar']}")

# Find battery and buffer info
with open(results_file) as f:
    data = json.load(f)

jeans_history = data["jeans"]["history"]

# Noise phase step range
noise_steps_list = [h for h in jeans_history if h["phase"] == "NOISE"]
step_start = noise_steps_list[0]["step"]
step_end = noise_steps_list[-1]["step"]

# Let's get the raw nodes from the simulation at these steps
# Since we didn't save battery/buffer rho for all steps in the JSON, let's look at what we did save:
# In test_jeans_rom.py:
# "SOURCE_rho", "HOST_rho", "BUFFER_rho", "BATTERY_state", "HOST_psi", "HOST_z", "HOST_isStellar", "HOST_j_val"
# Wait, we did not save BATTERY_rho in the history!
# Let's modify test_jeans_rom.py to save BATTERY_rho and GATE_rho as well so we can do a full mass balance.

