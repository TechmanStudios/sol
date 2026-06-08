import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from verify_split_load import run_trial_split_load

def optimize_zero_cross(phi_act, phi_cr):
    t1 = phi_cr + math.pi / 2
    t2 = phi_cr - math.pi / 2
    return t1 if math.cos(t1 - phi_act) > 0 else t2

def main():
    resonator_multiplier = 10.0
    gate_w0 = 0.5
    baseline_rho = 15.0
    
    R_0 = {}
    R_half_pi = {}
    
    print("Running debug calibration...", flush=True)
    
    for pair_idx in range(8):
        b_sine = 2 * pair_idx
        b_cos = 2 * pair_idx + 1
        
        # Sine active, match phase = 0.0
        p_temp = [0.0] * 16
        deltas, _ = run_trial_split_load(1 << b_sine, 0, p_temp, resonator_multiplier, gate_w0)
        R_0[(b_sine, 'sine')] = deltas[b_sine]
        R_0[(b_cos, 'sine')] = deltas[b_cos]
        
        # Sine active, match phase = pi/2
        p_temp = [0.0] * 16
        p_temp[b_sine] = math.pi / 2
        p_temp[b_cos] = math.pi / 2
        deltas, _ = run_trial_split_load(1 << b_sine, 0, p_temp, resonator_multiplier, gate_w0)
        R_half_pi[(b_sine, 'sine')] = deltas[b_sine]
        R_half_pi[(b_cos, 'sine')] = deltas[b_cos]
        
        # Cosine active, match phase = 0.0
        p_temp = [0.0] * 16
        deltas, _ = run_trial_split_load(1 << b_cos, 0, p_temp, resonator_multiplier, gate_w0)
        R_0[(b_sine, 'cosine')] = deltas[b_sine]
        R_0[(b_cos, 'cosine')] = deltas[b_cos]
        
        # Cosine active, match phase = pi/2
        p_temp = [0.0] * 16
        p_temp[b_sine] = math.pi / 2
        p_temp[b_cos] = math.pi / 2
        deltas, _ = run_trial_split_load(1 << b_cos, 0, p_temp, resonator_multiplier, gate_w0)
        R_half_pi[(b_sine, 'cosine')] = deltas[b_sine]
        R_half_pi[(b_cos, 'cosine')] = deltas[b_cos]
        
        # Print raw measurements
        print(f"\nPair {pair_idx}:")
        print(f"  Sine Active:")
        print(f"    Match Sine   : R_0={R_0[(b_sine, 'sine')]:.4f}, R_pi2={R_half_pi[(b_sine, 'sine')]:.4f}")
        print(f"    Match Cosine : R_0={R_0[(b_cos, 'sine')]:.4f}, R_pi2={R_half_pi[(b_cos, 'sine')]:.4f}")
        print(f"  Cosine Active:")
        print(f"    Match Sine   : R_0={R_0[(b_sine, 'cosine')]:.4f}, R_pi2={R_half_pi[(b_sine, 'cosine')]:.4f}")
        print(f"    Match Cosine : R_0={R_0[(b_cos, 'cosine')]:.4f}, R_pi2={R_half_pi[(b_cos, 'cosine')]:.4f}")
        
        # Calculate phases
        phi_sine_active = math.atan2(R_half_pi[(b_sine, 'sine')], R_0[(b_sine, 'sine')])
        phi_sine_cross = math.atan2(R_half_pi[(b_sine, 'cosine')], R_0[(b_sine, 'cosine')])
        
        phi_cos_active = math.atan2(R_half_pi[(b_cos, 'cosine')], R_0[(b_cos, 'cosine')])
        phi_cos_cross = math.atan2(R_half_pi[(b_cos, 'sine')], R_0[(b_cos, 'sine')])
        
        theta_sine = optimize_zero_cross(phi_sine_active, phi_sine_cross)
        theta_cos = optimize_zero_cross(phi_cos_active, phi_cos_cross)
        
        print(f"  Phases:")
        print(f"    Sine Active Phase   : {phi_sine_active*180/math.pi:.1f} deg")
        print(f"    Sine Cross Phase    : {phi_sine_cross*180/math.pi:.1f} deg")
        print(f"    Cosine Active Phase : {phi_cos_active*180/math.pi:.1f} deg")
        print(f"    Cosine Cross Phase  : {phi_cos_cross*180/math.pi:.1f} deg")
        print(f"    Calibrated Sine     : {theta_sine*180/math.pi:.1f} deg")
        print(f"    Calibrated Cosine   : {theta_cos*180/math.pi:.1f} deg")

if __name__ == "__main__":
    main()
