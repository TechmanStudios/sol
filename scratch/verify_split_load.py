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
from calibrate_linear_receiver_driven import (
    MHRALevel11ProcessingManifoldLinear, Level11ManifoldGroupLinear, Level11SequencerLinear
)

class Level11SequencerSplitLoad(Level11SequencerLinear):
    def execute_instruction(self, inst: Instruction):
        op = inst.op.upper()
        if op == "LOAD_16":
            reg_name = inst.args[0]
            val = int(inst.args[1])
            other_reg = "Y" if reg_name == "X" else "X"
            
            # 1. Initialize resonators and gates as write-locked by default
            for b in range(16):
                host = self.group.get_node(f"S_R{reg_name}_Bit{b}")
                bat = self.group.get_node(f"S_R{reg_name}_Bit{b}_B")
                self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}")
                self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}_B")
                
                if (val & (1 << b)):
                    bat["isBattery"] = True
                    host["psi_bias"] = 0.0
                    bat["psi_bias"] = 0.0
                else:
                    bat["isBattery"] = True
                    bat["b_state"] = -1
                    bat["b_charge"] = 0.0
                    bat["psi"] = -1.0
                    bat["psi_bias"] = -1.0
                    host["psi"] = -1.0
                    host["psi_bias"] = -1.0
                
                self.group.engine.write_lock(f"S_R{other_reg}_Bit{b}")
                self.group.engine.write_lock(f"S_R{other_reg}_Bit{b}_B")
                
            for b in range(16):
                self.group.engine.write_lock(f"Gate_Match{b}")
                lane = b // 8
                self.group.set_edge_connection(f"P_Bus{lane}", f"Gate_Match{b}", False)
                
            for b in range(16):
                basin = self.group.semantic.basins[f"Basin_Val{b}"]
                for nid in basin.node_ids:
                    self.group.engine.write_lock(nid)
                    
            for nid in self.group.semantic.basins["Basin_Query"].node_ids:
                self.group.engine.write_enable(nid)
                
            amp = 150.0
            
            # --- PHASE 1: Load SINE bits (even bits) ---
            # Write-enable ONLY the active Sine resonators
            for b in range(16):
                is_sine = (b % 2 == 0)
                if is_sine and (val & (1 << b)):
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
            
            # Connect only active Sine gates
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                is_sine = (b % 2 == 0)
                if is_sine and (val & (1 << b)):
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = self.gate_w0
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
            for s in range(40):
                t = s * self.dt
                # Drive active Sine gates
                for b in range(16):
                    is_sine = (b % 2 == 0)
                    if is_sine and (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 1.0 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                        
                # Modulate bus with active Sine waves
                # Lane 0
                num_sine0 = sum(1 for b in range(8) if (b % 2 == 0) and (val & (1 << b)))
                src_rho0 = 15.0
                if num_sine0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (b % 2 == 0) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin0 += math.sin(omega * t + phase_val)
                    src_rho0 += (amp / math.sqrt(num_sine0)) * sum_sin0
                # Lane 1
                num_sine1 = sum(1 for b in range(8, 16) if (b % 2 == 0) and (val & (1 << b)))
                src_rho1 = 15.0
                if num_sine1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (b % 2 == 0) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin1 += math.sin(omega * t + phase_val)
                    src_rho1 += (amp / math.sqrt(num_sine1)) * sum_sin1
                    
                self.group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
                self.group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            # Disconnect all Sine gates and WRITE-LOCK all Sine resonators
            for b in range(16):
                is_sine = (b % 2 == 0)
                if is_sine:
                    lane = b // 8
                    g_target = f"GATE_{reg_name}_Bit{b}"
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}_B")
                    
            # --- PHASE 2: Load COSINE bits (odd bits) ---
            # Write-enable ONLY the active Cosine resonators
            for b in range(16):
                is_cos = (b % 2 == 1)
                if is_cos and (val & (1 << b)):
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
            
            # Connect only active Cosine gates
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                is_cos = (b % 2 == 1)
                if is_cos and (val & (1 << b)):
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = self.gate_w0
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
            for s in range(40):
                t = s * self.dt
                # Drive active Cosine gates
                for b in range(16):
                    is_cos = (b % 2 == 1)
                    if is_cos and (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 1.0 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                        
                # Modulate bus with active Cosine waves
                # Lane 0
                num_cos0 = sum(1 for b in range(8) if (b % 2 == 1) and (val & (1 << b)))
                src_rho0 = 15.0
                if num_cos0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (b % 2 == 1) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin0 += math.sin(omega * t + phase_val)
                    src_rho0 += (amp / math.sqrt(num_cos0)) * sum_sin0
                # Lane 1
                num_cos1 = sum(1 for b in range(8, 16) if (b % 2 == 1) and (val & (1 << b)))
                src_rho1 = 15.0
                if num_cos1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (b % 2 == 1) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin1 += math.sin(omega * t + phase_val)
                    src_rho1 += (amp / math.sqrt(num_cos1)) * sum_sin1
                    
                self.group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
                self.group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            # Disconnect all Cosine gates and WRITE-LOCK all Cosine resonators
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                self.group.get_node(g_target)["psi_bias"] = -1.0
                self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                is_cos = (b % 2 == 1)
                if is_cos:
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}_B")
                
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            for b in range(16):
                basin = self.group.semantic.basins[f"Basin_Val{b}"]
                for nid in basin.node_ids:
                    self.group.engine.write_enable(nid)
            
            for s in range(self.settle_steps):
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
        else:
            # QUERY_16 remains receiver-driven
            super().execute_instruction(inst)

def run_trial_split_load(val_X: int, val_Y: int, calibrated_phases: list[float], resonator_multiplier=10.0, gate_w0=0.5, baseline_rho=15.0, query_steps=120, settle_steps=15):
    nodes = []
    edges = []
    basins = []
    
    for i in range(16):
        n_val, e_val, b_val = UniversalManifold.build_semantic_basin(f"Basin_Val{i}", num_nodes=10, start_idx=i*10)
        for n in n_val:
            if n["id"] == b_val.hub_id:
                n["semanticMass"] = 1.0
                n["semanticMass0"] = 1.0
        nodes.extend(n_val)
        edges.extend(e_val)
        basins.append(b_val)
        
    n_q, e_q, b_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=160)
    nodes.extend(n_q)
    edges.extend(e_q)
    basins.append(b_q)
    
    semantic = SemanticManifold(nodes, edges, basins)
    for n in semantic.nodes:
        n["rho"] = baseline_rho * n.get("semanticMass", 1.0)
        
    processing = MHRALevel11ProcessingManifoldLinear(baseline_rho=baseline_rho, resonator_multiplier=resonator_multiplier, gate_w0=gate_w0)
    group = Level11ManifoldGroupLinear(semantic, processing, c_press=2.0, damping=0.0)
    
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 450.0
        else:
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    active_X = (val_X != 0)
    active_Y = (val_Y != 0)
    
    group.prime_register('X', active=active_X, baseline_rho=baseline_rho, resonator_multiplier=resonator_multiplier)
    group.prime_register('Y', active=active_Y, baseline_rho=baseline_rho, resonator_multiplier=resonator_multiplier)
        
    sequencer = Level11SequencerSplitLoad(group, dt=0.04, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps, gate_w0=gate_w0)
    sequencer.calibrated_phases = calibrated_phases
        
    if active_X:
        sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    if active_Y:
        sequencer.execute_instruction(Instruction("LOAD_16", ["Y", val_Y]))
        
    post_load_snap = snapshot_state(group.engine.physics)
    
    sequencer.execute_instruction(Instruction("QUERY_16", ["plus"]))
    rhos_plus = [group.get_node(group.semantic.basins[f"Basin_Val{i}"].bridge_id)["rho"] for i in range(16)]
    
    restore_state(group.engine.physics, post_load_snap)
    
    sequencer.execute_instruction(Instruction("QUERY_16", ["minus"]))
    rhos_minus = [group.get_node(group.semantic.basins[f"Basin_Val{i}"].bridge_id)["rho"] for i in range(16)]
    
    deltas = [(rhos_plus[i] - rhos_minus[i]) / 2.0 for i in range(16)]
    return deltas, sequencer.min_active_register_mass

def calibrate_split_load(resonator_multiplier=10.0, gate_w0=0.5):
    print("Calibrating all 16 bits with Split Load...", flush=True)
    steps = 24
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    R_0 = {}
    R_half_pi = {}
    
    for pair_idx in range(8):
        b_sine = 2 * pair_idx
        b_cos = 2 * pair_idx + 1
        print(f"  Calibrating pair: Bit {b_sine} (Sine) and Bit {b_cos} (Cosine)", flush=True)
        
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
        
    calibrated_phases = [0.0] * 16
    for pair_idx in range(8):
        b_sine = 2 * pair_idx
        b_cos = 2 * pair_idx + 1
        
        phi_sine_active = math.atan2(R_half_pi[(b_sine, 'sine')], R_0[(b_sine, 'sine')])
        phi_sine_cross = math.atan2(R_half_pi[(b_sine, 'cosine')], R_0[(b_sine, 'cosine')])
        
        phi_cos_active = math.atan2(R_half_pi[(b_cos, 'cosine')], R_0[(b_cos, 'cosine')])
        phi_cos_cross = math.atan2(R_half_pi[(b_cos, 'sine')], R_0[(b_cos, 'sine')])
        
        def optimize_zero_cross(phi_act, phi_cr):
            t1 = phi_cr + math.pi / 2
            t2 = phi_cr - math.pi / 2
            return t1 if math.cos(t1 - phi_act) > 0 else t2
            
        theta_sine = optimize_zero_cross(phi_sine_active, phi_sine_cross)
        theta_cos = optimize_zero_cross(phi_cos_active, phi_cos_cross)
        
        calibrated_phases[b_sine] = theta_sine % (2 * math.pi)
        calibrated_phases[b_cos] = theta_cos % (2 * math.pi)
        
    return calibrated_phases

def test_calibrated_phases_split_load(calibrated_phases, resonator_multiplier=10.0, gate_w0=0.5):
    print("\nStarting Verification Cases...", flush=True)
    cases = [
        {
            "name": "Case A: Single-Register 16-Bit Word Recall",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case B: Simultaneous Dual-Register Parallel Recall",
            "val_X": 0b1010000000001111,
            "val_Y": 0b0101111111110000,
            "expected_X": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            "expected_Y": [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0]
        },
        {
            "name": "Case C: Selective Bit Masking (Odd Bits)",
            "val_X": 0b1010101010101010,
            "val_Y": 0,
            "expected_X": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case D: Phase-Reversed Rejection",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        }
    ]
    
    suite_ok = True
    worst_min_mass = float('inf')
    
    for idx, c in enumerate(cases):
        print(f"\nTrial {idx+1}/{len(cases)}: {c['name']}...", flush=True)
        
        if idx == 3: # Case D
            phases = list(calibrated_phases)
            phases[0] = (phases[0] + math.pi) % (2 * math.pi)
            deltas, min_mass = run_trial_split_load(c["val_X"], c["val_Y"], phases, resonator_multiplier, gate_w0)
        else:
            deltas, min_mass = run_trial_split_load(c["val_X"], c["val_Y"], calibrated_phases, resonator_multiplier, gate_w0)
            
        passed = True
        
        if idx == 1: # Case B
            expected = [c["expected_X"][i] | c["expected_Y"][i] for i in range(16)]
        else:
            expected = c["expected_X"]
            
        if idx == 3: # Case D
            expected[0] = 0
            
        print("  Bit verification:", flush=True)
        for i in range(16):
            exp_val = expected[i]
            d = deltas[i]
            if exp_val == 1:
                if d < 0.2:
                    passed = False
                    print(f"    [FAIL] Bit {i:2d} (Active): delta = {d:+.4f} (expected >= 0.2)", flush=True)
                else:
                    print(f"    [PASS] Bit {i:2d} (Active): delta = {d:+.4f}", flush=True)
            else:
                if d >= 0.1:
                    passed = False
                    print(f"    [FAIL] Bit {i:2d} (Flat):   delta = {d:+.4f} (expected < 0.1)", flush=True)
                else:
                    print(f"    [PASS] Bit {i:2d} (Flat):   delta = {d:+.4f}", flush=True)
                    
        if min_mass < worst_min_mass:
            worst_min_mass = min_mass
            
        print(f"  Result: Passed={passed} | min_mass={min_mass:.2f}", flush=True)
        if not passed:
            suite_ok = False
            
    print(f"\nVerification Suite Result: {'PASSED' if (suite_ok and worst_min_mass >= 14.0) else 'FAILED'}")
    print(f"Worst active register mass: {worst_min_mass:.2f} (threshold >= 14.0)")

def main():
    resonator_multiplier = 10.0
    gate_w0 = 0.5
    phases = calibrate_split_load(resonator_multiplier, gate_w0)
    test_calibrated_phases_split_load(phases, resonator_multiplier, gate_w0)

if __name__ == "__main__":
    main()
