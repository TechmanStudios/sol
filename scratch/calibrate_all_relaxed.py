import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from calibrate_linear_receiver_driven import run_trial_linear

def main():
    print("Running All-Bit Relaxed Joint Calibration...", flush=True)
    steps = 24
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    resonator_multiplier = 2.0
    gate_w0 = 1.5
    
    calibrated_phases = [0.0] * 16
    
    # We will calibrate each of the 8 pairs
    for pair_idx in range(8):
        b_sine = 2 * pair_idx
        b_cos = 2 * pair_idx + 1
        print(f"\nCalibrating Pair {pair_idx}: Bit {b_sine} (Sine) and Bit {b_cos} (Cosine)...", flush=True)
        
        # 1. Sweep with Sine active
        arr_sine_sine = [0.0] * steps  # Sine response when Sine active
        arr_cos_sine = [0.0] * steps   # Cosine response when Sine active
        for i, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[b_sine] = ph
            temp_phases[b_cos] = ph
            deltas, _ = run_trial_linear(1 << b_sine, 0, temp_phases, resonator_multiplier, gate_w0)
            arr_sine_sine[i] = deltas[b_sine]
            arr_cos_sine[i] = deltas[b_cos]
            
        # 2. Sweep with Cosine active
        arr_sine_cos = [0.0] * steps   # Sine response when Cosine active
        arr_cos_cos = [0.0] * steps    # Cosine response when Cosine active
        for i, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[b_sine] = ph
            temp_phases[b_cos] = ph
            deltas, _ = run_trial_linear(1 << b_cos, 0, temp_phases, resonator_multiplier, gate_w0)
            arr_sine_cos[i] = deltas[b_sine]
            arr_cos_cos[i] = deltas[b_cos]
            
        # 3. Sweep with Neither active
        arr_sine_neither = [0.0] * steps
        arr_cos_neither = [0.0] * steps
        for i, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[b_sine] = ph
            temp_phases[b_cos] = ph
            deltas, _ = run_trial_linear(0, 0, temp_phases, resonator_multiplier, gate_w0)
            arr_sine_neither[i] = deltas[b_sine]
            arr_cos_neither[i] = deltas[b_cos]
            
        # 4. Search for the best phase pair
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
                
                # Check 6 conditions:
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
                        best_pair = (i_sine, i_cos, act_sine, cross_sine_cos, self_sine, act_cos, cross_cos_sine, self_cos)
                        
        if best_pair is None:
            print(f"WARNING: No valid pair found for Pair {pair_idx} under strict flat threshold!", flush=True)
            # Find best relaxed pair (relaxing self_sine and self_cos if needed)
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
                            best_pair = (i_sine, i_cos, act_sine, cross_sine_cos, self_sine, act_cos, cross_cos_sine, self_cos)
            
            i_sine, i_cos, act_sine, cross_sine_cos, self_sine, act_cos, cross_cos_sine, self_cos = best_pair
            print(f"  Best relaxed pair: sine_ph={phases[i_sine]*180/math.pi:.1f} deg, cos_ph={phases[i_cos]*180/math.pi:.1f} deg | violation={min_violation:.4f}")
        else:
            i_sine, i_cos, act_sine, cross_sine_cos, self_sine, act_cos, cross_cos_sine, self_cos = best_pair
            print(f"  Found valid pair: sine_ph={phases[i_sine]*180/math.pi:.1f} deg, cos_ph={phases[i_cos]*180/math.pi:.1f} deg | score={best_score:.4f}")
            
        print(f"    Sine Match: active={act_sine:+.4f}, cross={cross_sine_cos:+.4f}, self={self_sine:+.4f}")
        print(f"    Cosine Match: active={act_cos:+.4f}, cross={cross_cos_sine:+.4f}, self={self_cos:+.4f}")
        
        calibrated_phases[b_sine] = phases[i_sine]
        calibrated_phases[b_cos] = phases[i_cos]
        
    print("\nCalibration Complete!", flush=True)
    print("calibrated_phases = [")
    for ph in calibrated_phases:
        print(f"    {ph:.6f},")
    print("]")
    
    # Run test suite with these phases
    from calibrate_linear_receiver_driven import test_calibrated_phases
    test_calibrated_phases(calibrated_phases, resonator_multiplier, gate_w0)

if __name__ == "__main__":
    main()
