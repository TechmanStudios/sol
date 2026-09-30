#!/usr/bin/env python3
import sys
import math
import time
from pathlib import Path
from multiprocessing import Pool

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_passive import Level11ManifoldGroup

def evaluate_trial(args):
    c_max_val, val_X, val_Y, temp_phases, baseline, query_steps, settle_steps, load_damping, bit_idx = args
    
    original_init = Level11ManifoldGroup.__init__
    def patched_init(self_group, semantic, processing, c_press=2.0, damping=0.0):
        original_init(self_group, semantic, processing, c_press, damping)
        self_group.engine.physics.conductance_max = c_max_val
    Level11ManifoldGroup.__init__ = patched_init
    
    try:
        from test_damping_pdm import run_damped_trial
        deltas = run_damped_trial(val_X, val_Y, temp_phases, baseline, query_steps, settle_steps, load_damping)
        return deltas[bit_idx]
    finally:
        Level11ManifoldGroup.__init__ = original_init

def main():
    baseline = 15.0
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    c_max_values = [800.0, 1000.0, 1200.0]
    damping_values = [0.55, 0.6, 0.65]
    periods = [10.0, 14.0, 18.0, 22.0]
    
    tasks = []
    task_keys = []
    
    for c_max in c_max_values:
        for d in damping_values:
            for f_idx in [0, 1, 2, 3]:
                bit_sine = 2 * f_idx
                bit_cosine = 2 * f_idx + 1
                
                # Sine tasks
                for ph in phases:
                    temp_phases = [0.0] * 16
                    temp_phases[bit_sine] = ph
                    tasks.append((c_max, (1 << bit_sine), 0, temp_phases, baseline, 150, 0, d, bit_sine))
                    task_keys.append((c_max, d, f_idx, "sine", ph))
                    
                # Cosine tasks
                for ph in phases:
                    temp_phases = [0.0] * 16
                    temp_phases[bit_cosine] = ph
                    tasks.append((c_max, (1 << bit_cosine), 0, temp_phases, baseline, 150, 0, d, bit_cosine))
                    task_keys.append((c_max, d, f_idx, "cosine", ph))
                
    print(f"Launching {len(tasks)} tasks on 3 parallel workers...", flush=True)
    t0 = time.time()
    
    with Pool(processes=3) as pool:
        results = pool.map(evaluate_trial, tasks)
        
    print(f"Sweep completed in {time.time() - t0:.2f} seconds", flush=True)
    
    results_map = {}
    for (c_max, d, f_idx, mode, ph), delta in zip(task_keys, results):
        if (c_max, d, f_idx) not in results_map:
            results_map[(c_max, d, f_idx)] = {"sine": {}, "cosine": {}}
        results_map[(c_max, d, f_idx)][mode][ph] = delta
        
    for c_max in c_max_values:
        for d in damping_values:
            print(f"=== conductance_max = {c_max} | load_damping = {d} ===")
            all_separated = True
            for f_idx in range(4):
                p = periods[f_idx]
                sine_data = results_map[(c_max, d, f_idx)]["sine"]
                best_phase_sine = max(sine_data, key=sine_data.get)
                max_delta_sine = sine_data[best_phase_sine]
                
                cosine_data = results_map[(c_max, d, f_idx)]["cosine"]
                best_phase_cosine = max(cosine_data, key=cosine_data.get)
                max_delta_cosine = cosine_data[best_phase_cosine]
                
                diff = (best_phase_cosine - best_phase_sine) % (2 * math.pi)
                # We want the phase difference to be close to 0.5*pi (i.e. between 0.33*pi and 1.67*pi, excluding 0 and pi)
                # Orthogonal is ideal (0.5*pi or 1.5*pi)
                is_orthogonal = (0.3 * math.pi <= diff <= 0.7 * math.pi) or (1.3 * math.pi <= diff <= 1.7 * math.pi)
                print(f"  Period {p:4.1f}: Sine Match = {best_phase_sine/math.pi:4.2f}*pi (max={max_delta_sine:+.2f}) | Cosine Match = {best_phase_cosine/math.pi:4.2f}*pi (max={max_delta_cosine:+.2f}) | Diff = {diff/math.pi:4.2f}*pi {'[OK]' if is_orthogonal else '[LOCKED]'}")
                if not is_orthogonal or max_delta_sine < 0.2 or max_delta_cosine < 0.2:
                    all_separated = False
            if all_separated:
                print(f"*** FOUND WORKING COMBO: conductance_max={c_max}, load_damping={d} ***", flush=True)

if __name__ == "__main__":
    main()
