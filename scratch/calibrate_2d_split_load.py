import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)
from sol_engine import snapshot_state, restore_state
from verify_split_load import Level11SequencerSplitLoad, run_trial_split_load

def main():
    print("Running E2E 2D Joint Calibration with Split Load...", flush=True)
    
    steps = 24
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    resonator_multiplier = 10.0
    gate_w0 = 0.5
    
    # Grid storage
    # We will store the results of all 576 trials.
    # Grid size: steps x steps
    # For each grid point (i_sine, i_cos):
    # We run 3 trials:
    # 1. Sine active: val_X = 0b0101010101010101
    # 2. Cosine active: val_X = 0b1010101010101010
    # 3. Neither active: val_X = 0
    
    sine_active_val = 0b0101010101010101
    cos_active_val = 0b1010101010101010
    neither_active_val = 0
    
    # To store deltas: [i_sine][i_cos] -> deltas (16 floats)
    deltas_sine_act = [[None for _ in range(steps)] for _ in range(steps)]
    deltas_cos_act = [[None for _ in range(steps)] for _ in range(steps)]
    deltas_neither_act = [[None for _ in range(steps)] for _ in range(steps)]
    
    print("Starting 2D phase sweep (24x24)...", flush=True)
    t0 = time.time()
    
    for i_sine in range(steps):
        for i_cos in range(steps):
            ph_sine = phases[i_sine]
            ph_cos = phases[i_cos]
            
            temp_phases = [0.0] * 16
            for k in range(8):
                temp_phases[2*k] = ph_sine
                temp_phases[2*k+1] = ph_cos
                
            # Run 3 trials
            d_sine, _ = run_trial_split_load(sine_active_val, 0, temp_phases, resonator_multiplier, gate_w0)
            d_cos, _ = run_trial_split_load(cos_active_val, 0, temp_phases, resonator_multiplier, gate_w0)
            d_neither, _ = run_trial_split_load(neither_active_val, 0, temp_phases, resonator_multiplier, gate_w0)
            
            deltas_sine_act[i_sine][i_cos] = d_sine
            deltas_cos_act[i_sine][i_cos] = d_cos
            deltas_neither_act[i_sine][i_cos] = d_neither
            
        print(f"  Sweep progress: {i_sine+1}/{steps} rows complete", flush=True)
        
    print(f"Sweep complete in {time.time() - t0:.1f} seconds. Finding optimal phase pairs...", flush=True)
    
    calibrated_phases = [0.0] * 16
    
    for pair_idx in range(8):
        b_sine = 2 * pair_idx
        b_cos = 2 * pair_idx + 1
        
        best_pair = None
        best_score = -float('inf')
        
        for i_sine in range(steps):
            for i_cos in range(steps):
                act_sine = deltas_sine_act[i_sine][i_cos][b_sine]
                cross_cos_sine = deltas_sine_act[i_sine][i_cos][b_cos]
                
                act_cos = deltas_cos_act[i_sine][i_cos][b_cos]
                cross_sine_cos = deltas_cos_act[i_sine][i_cos][b_sine]
                
                self_sine = deltas_neither_act[i_sine][i_cos][b_sine]
                self_cos = deltas_neither_act[i_sine][i_cos][b_cos]
                
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
            # Find best relaxed pair
            min_violation = float('inf')
            for i_sine in range(steps):
                for i_cos in range(steps):
                    act_sine = deltas_sine_act[i_sine][i_cos][b_sine]
                    cross_cos_sine = deltas_sine_act[i_sine][i_cos][b_cos]
                    act_cos = deltas_cos_act[i_sine][i_cos][b_cos]
                    cross_sine_cos = deltas_cos_act[i_sine][i_cos][b_sine]
                    self_sine = deltas_neither_act[i_sine][i_cos][b_sine]
                    self_cos = deltas_neither_act[i_sine][i_cos][b_cos]
                    
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
        
    print("\ncalibrated_phases = [")
    for ph in calibrated_phases:
        print(f"    {ph:.6f},")
    print("]")
    
    # Run E2E test cases
    from verify_split_load import test_calibrated_phases_split_load
    test_calibrated_phases_split_load(calibrated_phases, resonator_multiplier, gate_w0)

if __name__ == "__main__":
    import time
    main()
