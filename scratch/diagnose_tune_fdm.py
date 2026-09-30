#!/usr/bin/env python3
import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_tune_fdm import run_fdm_trial

def test_config(phase_A, phase_B, baseline=1.5):
    print(f"=== Testing Phase A = {phase_A:.4f}, Phase B = {phase_B:.4f}, Baseline = {baseline} ===")
    cases = [
        (False, False, "Case 00 (No Input)"),
        (True, False, "Case 10 (Channel A Active)"),
        (False, True, "Case 01 (Channel B Active)"),
        (True, True, "Case 11 (Both Active)")
    ]
    for active_A, active_B, label in cases:
        delta_A, delta_B, history = run_fdm_trial(active_A, active_B, baseline, phase_A, phase_B)
        min_mass = history[-1]["min_active_register_mass"]
        print(f"  {label:30s}: delta_A = {delta_A:+.4f}, delta_B = {delta_B:+.4f}, min_mass = {min_mass:.2f}")

if __name__ == "__main__":
    # Test best phases found in sweep: Phase A = pi, Phase B = 3pi/2
    test_config(math.pi, 1.5 * math.pi)
