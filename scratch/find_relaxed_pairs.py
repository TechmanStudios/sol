import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from check_linear_regime import run_trial_linear

def main():
    print("Testing Relaxed Joint Calibration for Bit 0 and Bit 1...")
    steps = 24
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    arr_D_A = [0.0] * steps
    arr_D_BA = [0.0] * steps
    arr_D_AB = [0.0] * steps
    arr_D_B = [0.0] * steps
    
    print("Sweeping Bit 0 active...")
    for i, ph in enumerate(phases):
        temp_phases = [0.0] * 16
        temp_phases[0] = ph
        temp_phases[1] = ph
        deltas = run_trial_linear(1, 0, temp_phases, resonator_multiplier=2.0, gate_w0=1.5)
        arr_D_A[i] = deltas[0]
        arr_D_BA[i] = deltas[1]
        
    print("Sweeping Bit 1 active...")
    for i, ph in enumerate(phases):
        temp_phases = [0.0] * 16
        temp_phases[0] = ph
        temp_phases[1] = ph
        deltas = run_trial_linear(2, 0, temp_phases, resonator_multiplier=2.0, gate_w0=1.5)
        arr_D_AB[i] = deltas[0]
        arr_D_B[i] = deltas[1]
        
    print("\nSearching for relaxed pairs (i_A, i_B)...")
    valid_pairs = []
    for i_A in range(steps):
        for i_B in range(steps):
            act_A = arr_D_A[i_A]
            cross_BA = arr_D_BA[i_B]
            act_B = arr_D_B[i_B]
            cross_AB = arr_D_AB[i_A]
            
            # Relaxed condition: active >= 0.2 and crosstalk < 0.1 (can be negative!)
            if act_A >= 0.2 and cross_BA < 0.1 and act_B >= 0.2 and cross_AB < 0.1:
                score = act_A + act_B - max(0.0, cross_BA) - max(0.0, cross_AB)
                valid_pairs.append((i_A, i_B, act_A, cross_BA, act_B, cross_AB, score))
                
    if not valid_pairs:
        print("No relaxed pairs found!")
    else:
        valid_pairs.sort(key=lambda x: x[6], reverse=True)
        print(f"Found {len(valid_pairs)} valid relaxed pairs. Top 5:")
        for idx, (i_A, i_B, act_A, cross_BA, act_B, cross_AB, score) in enumerate(valid_pairs[:5]):
            print(f"Pair {idx+1}: i_A={i_A} ({phases[i_A]*180/math.pi:.1f} deg), i_B={i_B} ({phases[i_B]*180/math.pi:.1f} deg)")
            print(f"  act_A={act_A:+.4f}, cross_BA={cross_BA:+.4f}")
            print(f"  act_B={act_B:+.4f}, cross_AB={cross_AB:+.4f}, score={score:.4f}")

if __name__ == "__main__":
    main()
