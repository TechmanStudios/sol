import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_final import run_level11_trial

baseline = 15.0
query_steps = 120
settle_steps = 30

steps = 12
phases = [2 * math.pi * i / steps for i in range(steps)]

print("Phase (rad) | Phase (deg) | Bit 0 Delta (Sine) | Bit 1 Delta (Cosine)")
print("-" * 75)

for i, ph in enumerate(phases):
    # Test Bit 0 (Sine)
    temp_phases_0 = [0.0] * 16
    temp_phases_0[0] = ph
    deltas_0, _ = run_level11_trial(1, 0, temp_phases_0, baseline, query_steps, settle_steps)
    
    # Test Bit 1 (Cosine)
    temp_phases_1 = [0.0] * 16
    temp_phases_1[1] = ph
    deltas_1, _ = run_level11_trial(2, 0, temp_phases_1, baseline, query_steps, settle_steps)
    
    print(f"{ph:11.6f} | {i*30:11.1f} | {deltas_0[0]:18.6f} | {deltas_1[1]:18.6f}")
