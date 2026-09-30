import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from calibrate_linear_receiver_driven import run_trial_linear, test_calibrated_phases

def run_calibration_and_case_A(resonator_multiplier, gate_w0):
    steps = 12  # Use 12 steps for faster search
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    calibrated_phases = [0.0] * 16
    
    # Calibrate each pair
    for pair_idx in range(8):
        b_sine = 2 * pair_idx
        b_cos = 2 * pair_idx + 1
        
        arr_sine_sine = [0.0] * steps
        arr_cos_sine = [0.0] * steps
        for i, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[b_sine] = ph
            temp_phases[b_cos] = ph
            deltas, _ = run_trial_linear(1 << b_sine, 0, temp_phases, resonator_multiplier, gate_w0)
            arr_sine_sine[i] = deltas[b_sine]
            arr_cos_sine[i] = deltas[b_cos]
            
        arr_sine_cos = [0.0] * steps
        arr_cos_cos = [0.0] * steps
        for i, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[b_sine] = ph
            temp_phases[b_cos] = ph
            deltas, _ = run_trial_linear(1 << b_cos, 0, temp_phases, resonator_multiplier, gate_w0)
            arr_sine_cos[i] = deltas[b_sine]
            arr_cos_cos[i] = deltas[b_cos]
            
        arr_sine_neither = [0.0] * steps
        arr_cos_neither = [0.0] * steps
        for i, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[b_sine] = ph
            temp_phases[b_cos] = ph
            deltas, _ = run_trial_linear(0, 0, temp_phases, resonator_multiplier, gate_w0)
            arr_sine_neither[i] = deltas[b_sine]
            arr_cos_neither[i] = deltas[b_cos]
            
        best_pair = None
        best_score = -float('inf')
        
        for i_sine in range(steps):
            for i_cos in range(steps):
                act_sine = arr_sine_sine[i_sine]
                cross_cos_sine = arr_cos_sine[i_cos]
                act_cos = arr_cos_cos[i_cos]
                cross_sine_cos = arr_sine_cos[i_sine]
                self_sine = arr_sine_neither[i_sine]
                self_cos = arr_cos_neither[i_cos]
                
                cond1 = act_sine >= 0.2
                cond2 = act_cos >= 0.2
                cond3 = cross_sine_cos < 0.1
                cond4 = cross_cos_sine < 0.1
                cond5 = self_sine < 0.1
                cond6 = self_cos < 0.1
                
                if cond1 and cond2 and cond3 and cond4 and cond5 and cond6:
                    score = act_sine + act_cos - max(0.0, cross_sine_cos) - max(0.0, cross_cos_sine) - max(0.0, self_sine) - max(0.0, self_cos)
                    if score > best_score:
                        best_score = score
                        best_pair = (i_sine, i_cos)
                        
        if best_pair is None:
            # Relaxed fallback
            min_violation = float('inf')
            for i_sine in range(steps):
                for i_cos in range(steps):
                    act_sine = arr_sine_sine[i_sine]
                    cross_cos_sine = arr_cos_sine[i_cos]
                    act_cos = arr_cos_cos[i_cos]
                    cross_sine_cos = arr_sine_cos[i_sine]
                    self_sine = arr_sine_neither[i_sine]
                    self_cos = arr_cos_neither[i_cos]
                    
                    if act_sine >= 0.2 and act_cos >= 0.2:
                        violation = max(0.0, cross_sine_cos - 0.1) + max(0.0, cross_cos_sine - 0.1) + max(0.0, self_sine - 0.1) + max(0.0, self_cos - 0.1)
                        if violation < min_violation:
                            min_violation = violation
                            best_pair = (i_sine, i_cos)
                            
        calibrated_phases[b_sine] = phases[best_pair[0]]
        calibrated_phases[b_cos] = phases[best_pair[1]]
        
    # Evaluate Case A
    val_X = 0b1010110011110001
    expected_X = [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
    
    deltas, min_mass = run_trial_linear(val_X, 0, calibrated_phases, resonator_multiplier, gate_w0)
    
    passed = True
    for i in range(16):
        exp = expected_X[i]
        d = deltas[i]
        if exp == 1:
            if d < 0.2:
                passed = False
        else:
            if d >= 0.1:
                passed = False
                
    return passed, deltas, min_mass, calibrated_phases

def main():
    print("Searching parameter space for stable E2E combination...", flush=True)
    # Search grid
    w0_vals = [0.5, 0.8, 1.0, 1.2, 1.5]
    mult_vals = [2.0, 3.0, 5.0, 10.0]
    
    for w0 in w0_vals:
        for mult in mult_vals:
            print(f"\nTesting: gate_w0 = {w0}, resonator_multiplier = {mult}...", flush=True)
            passed, deltas, min_mass, phases = run_calibration_and_case_A(mult, w0)
            print(f"  Result: Passed={passed} | min_mass={min_mass:.2f}")
            if passed:
                print(f"  SUCCESS! Found working parameters: gate_w0 = {w0}, resonator_multiplier = {mult}")
                print(f"  Calibrated phases: {[round(p, 4) for p in phases]}")
                return

if __name__ == "__main__":
    main()
