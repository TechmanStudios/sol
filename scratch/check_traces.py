import json

with open("solResearch/nextBestTest/wormhole_recall_results.json", "r") as f:
    data = json.load(f)

print("--- CONFIG 1 (gamma = 0.0) Child Mixer Trace ---")
c1_mixer = data["config_1"]["mixer_c"]
for step in range(100, 205, 10):
    val = c1_mixer[step]
    print(f"  Step {step}: {val:.6f}")

print("\n--- CONFIG 3 (gamma = 0.05) Child Mixer Trace ---")
c3_mixer = data["config_3"]["mixer_c"]
for step in range(100, 205, 10):
    val = c3_mixer[step]
    print(f"  Step {step}: {val:.6f}")
