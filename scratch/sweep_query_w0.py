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

def optimize_zero_cross(phi_act, phi_cr):
    t1 = phi_cr + math.pi / 2
    t2 = phi_cr - math.pi / 2
    return t1 if math.cos(t1 - phi_act) > 0 else t2

class Level11SequencerSweep(MicroInstructionSequencer):
    def __init__(self, group, query_w0=0.5, match_weight_scale=1.0, dt=0.04, baseline_rho=15.0, query_steps=120, settle_steps=15):
        super().__init__(group, dt)
        self.min_active_register_mass = float('inf')
        self.history = []
        self.baseline_rho = baseline_rho
        self.query_steps = query_steps
        self.settle_steps = settle_steps
        
        self.periods = [10.0, 12.0, 15.0, 20.0]
        self.omegas = [2 * math.pi / (p * self.dt) for p in self.periods]
        self.calibrated_phases = [0.0] * 16
        
        # Query coupling & weights
        self.query_w0 = query_w0
        base_weights = [150.0, 100.0, 80.0, 60.0]
        self.match_weights = [w * match_weight_scale for w in base_weights]

    def get_reg_gate_params(self, b: int) -> tuple[float, float]:
        b_local = b % 8
        f_idx = b_local // 2
        omega = self.omegas[f_idx]
        is_cosine = (b_local % 2 == 1)
        phase_offset = 0.5 * math.pi if is_cosine else 0.0
        return omega, phase_offset

    def get_match_gate_params(self, b: int) -> tuple[float, float]:
        b_local = b % 8
        f_idx = b_local // 2
        omega = self.omegas[f_idx]
        return omega, self.calibrated_phases[b]

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
            for b in range(16):
                is_sine = (b % 2 == 0)
                if is_sine and (val & (1 << b)):
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
            
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                is_sine = (b % 2 == 0)
                if is_sine and (val & (1 << b)):
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 5.0
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
            for s in range(40):
                t = s * self.dt
                for b in range(16):
                    is_sine = (b % 2 == 0)
                    if is_sine and (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 1.0 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                        
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
            for b in range(16):
                is_cos = (b % 2 == 1)
                if is_cos and (val & (1 << b)):
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
            
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                is_cos = (b % 2 == 1)
                if is_cos and (val & (1 << b)):
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 5.0
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
            for s in range(40):
                t = s * self.dt
                for b in range(16):
                    is_cos = (b % 2 == 1)
                    if is_cos and (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 1.0 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                        
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
                
        elif op == "QUERY_16":
            phase_invert = (len(inst.args) > 0 and inst.args[0] == "minus")
            
            self.group.get_node("P_Bus0")["rho"] = self.baseline_rho
            self.group.get_node("P_Bus1")["rho"] = self.baseline_rho
            for b in range(16):
                self.group.get_node(f"Gate_Match{b}")["rho"] = self.baseline_rho
                
            for e in self.group.engine.physics.edges:
                is_resonator = (
                    (e["from"].startswith("S_R") and e["to"].endswith("_B")) or
                    (e["to"].startswith("S_R") and e["from"].endswith("_B"))
                )
                if not is_resonator:
                    e["flux"] = 0.0
                
            active_regs = []
            for reg in ['X', 'Y']:
                is_active = False
                for b in range(16):
                    bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                    if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                        is_active = True
                        break
                if is_active:
                    active_regs.append(reg)
                    
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            for reg in ['X', 'Y']:
                for b in range(16):
                    self.group.engine.write_enable(f"S_R{reg}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
                    self.group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = True
                    
            # Set query_w0 dynamically
            for b in range(16):
                gate_id = f"Gate_Match{b}"
                self.group.engine.write_enable(gate_id)
                lane = b // 8
                self.group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
                self.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = self.query_w0
                self.group.get_node(gate_id)["psi_bias"] = 0.0
                
            for reg in ['X', 'Y']:
                for b in range(16):
                    self.group.get_node(f"S_R{reg}_Bit{b}")["psi_bias"] = 0.0
                    self.group.get_node(f"S_R{reg}_Bit{b}_B")["psi_bias"] = 0.0
            self.group.get_node("P_Bus0")["psi_bias"] = 0.0
            self.group.get_node("P_Bus1")["psi_bias"] = 0.0
            
            for b in range(16):
                basin = self.group.semantic.basins[f"Basin_Val{b}"]
                for nid in basin.node_ids:
                    self.group.engine.write_enable(nid)
                    if nid == basin.bridge_id:
                        self.group.engine.write_enable(nid)
                    else:
                        self.group.get_node(nid)["psi_bias"] = 0.0
                    
            for s in range(self.query_steps):
                t = s * self.dt
                for reg in ['X', 'Y']:
                    for b in range(16):
                        lane = b // 8
                        g_active = f"GATE_{reg}_Bit{b}"
                        bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                        is_bit_active = (bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.5)
                        if reg in active_regs and is_bit_active:
                            omega, phase_val = self.get_reg_gate_params(b)
                            val_psi = 1.0 * math.sin(omega * t + phase_val)
                            self.group.get_node(g_active)["psi"] = val_psi
                            self.group.get_node(g_active)["psi_bias"] = val_psi
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                            self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = self.query_w0
                        else:
                            self.group.get_node(g_active)["psi_bias"] = -1.0
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                            
                for b in range(16):
                    gate_id = f"Gate_Match{b}"
                    dest_basin_id = f"Basin_Val{b}"
                    bridge_node = self.group.semantic.basins[dest_basin_id].bridge_id
                    
                    self.group.set_edge_connection(gate_id, bridge_node, True)
                    f_idx = (b % 8) // 2
                    self.group.get_edge(gate_id, bridge_node)["w0"] = self.match_weights[f_idx]
                    
                    omega, phase_val = self.get_match_gate_params(b)
                    if phase_invert:
                        phase_val += math.pi
                    val_psi = 1.0 * math.sin(omega * t + phase_val)
                    self.group.get_node(bridge_node)["psi"] = val_psi
                    self.group.get_node(bridge_node)["psi_bias"] = val_psi
                    
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for s in range(40):
                for reg in ['X', 'Y']:
                    for b in range(16):
                        lane = b // 8
                        g_active = f"GATE_{reg}_Bit{b}"
                        self.group.get_node(g_active)["psi_bias"] = -1.0
                        self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                        
                for b in range(16):
                    gate_id = f"Gate_Match{b}"
                    self.group.set_edge_connection(gate_id, self.group.semantic.basins[f"Basin_Val{b}"].bridge_id, False)
                    
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()

    def record_telemetry(self):
        active_masses = []
        for reg in ['X', 'Y']:
            for b in range(16):
                bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                host = self.group.get_node(f"S_R{reg}_Bit{b}")
                if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                    active_masses.append(bat["rho"] + host["rho"])
                        
        if active_masses:
            min_act = min(active_masses)
            if min_act < self.min_active_register_mass:
                self.min_active_register_mass = min_act
                
        self.history.append({
            "step": len(self.history),
            "min_active_register_mass": self.min_active_register_mass if self.min_active_register_mass != float('inf') else 0.0
        })

def run_trial(val_X: int, val_Y: int, calibrated_phases: list[float], query_w0, match_weight_scale, resonator_multiplier=20.0, baseline_rho=15.0, query_steps=120, settle_steps=15):
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
        
    from calibrate_linear_receiver_driven import MHRALevel11ProcessingManifoldLinear, Level11ManifoldGroupLinear
    processing = MHRALevel11ProcessingManifoldLinear(baseline_rho=baseline_rho, resonator_multiplier=resonator_multiplier, gate_w0=5.0)
    
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
        
    sequencer = Level11SequencerSweep(group, query_w0=query_w0, match_weight_scale=match_weight_scale, dt=0.04, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
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

def calibrate_analytical(query_w0, match_weight_scale, resonator_multiplier=20.0):
    R_0 = {}
    R_half_pi = {}
    
    for pair_idx in range(8):
        b_sine = 2 * pair_idx
        b_cos = 2 * pair_idx + 1
        
        # Sine active, match phase = 0.0
        p_temp = [0.0] * 16
        deltas, _ = run_trial(1 << b_sine, 0, p_temp, query_w0, match_weight_scale, resonator_multiplier)
        R_0[(b_sine, 'sine')] = deltas[b_sine]
        R_0[(b_cos, 'sine')] = deltas[b_cos]
        
        # Sine active, match phase = pi/2
        p_temp = [0.0] * 16
        p_temp[b_sine] = math.pi / 2
        p_temp[b_cos] = math.pi / 2
        deltas, _ = run_trial(1 << b_sine, 0, p_temp, query_w0, match_weight_scale, resonator_multiplier)
        R_half_pi[(b_sine, 'sine')] = deltas[b_sine]
        R_half_pi[(b_cos, 'sine')] = deltas[b_cos]
        
        # Cosine active, match phase = 0.0
        p_temp = [0.0] * 16
        deltas, _ = run_trial(1 << b_cos, 0, p_temp, query_w0, match_weight_scale, resonator_multiplier)
        R_0[(b_sine, 'cosine')] = deltas[b_sine]
        R_0[(b_cos, 'cosine')] = deltas[b_cos]
        
        # Cosine active, match phase = pi/2
        p_temp = [0.0] * 16
        p_temp[b_sine] = math.pi / 2
        p_temp[b_cos] = math.pi / 2
        deltas, _ = run_trial(1 << b_cos, 0, p_temp, query_w0, match_weight_scale, resonator_multiplier)
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
        
        theta_sine = optimize_zero_cross(phi_sine_active, phi_sine_cross)
        theta_cos = optimize_zero_cross(phi_cos_active, phi_cos_cross)
        
        calibrated_phases[b_sine] = theta_sine % (2 * math.pi)
        calibrated_phases[b_cos] = theta_cos % (2 * math.pi)
        
    return calibrated_phases

def test_config(query_w0, match_weight_scale):
    # 1. Calibrate
    phases = calibrate_analytical(query_w0, match_weight_scale)
    
    # 2. Test Case A
    val_X = 0b1010110011110001
    expected_X = [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
    
    deltas, min_mass = run_trial(val_X, 0, phases, query_w0, match_weight_scale)
    
    passed = True
    active_deltas = []
    flat_deltas = []
    
    for i in range(16):
        exp_val = expected_X[i]
        d = deltas[i]
        if exp_val == 1:
            active_deltas.append(d)
            if d < 0.2:
                passed = False
        else:
            flat_deltas.append(d)
            if d >= 0.1:
                passed = False
                
    avg_act = sum(active_deltas) / len(active_deltas) if active_deltas else 0.0
    min_act = min(active_deltas) if active_deltas else 0.0
    avg_flat = sum(flat_deltas) / len(flat_deltas) if flat_deltas else 0.0
    max_flat = max(flat_deltas) if flat_deltas else 0.0
    
    return passed, min_act, avg_act, max_flat, avg_flat, min_mass

def main():
    print("Sweeping query_w0 and match_weight_scale...", flush=True)
    # Let's sweep query_w0 from 0.1 to 1.5, and match_weight_scale from 0.5 to 5.0
    configs = [
        # (query_w0, match_weight_scale)
        (0.2, 2.0),
        (0.2, 5.0),
        (0.5, 1.0),
        (0.5, 2.0),
        (0.5, 3.0),
        (1.0, 0.5),
        (1.0, 1.0),
        (1.5, 0.3),
        (1.5, 0.5),
        (2.0, 0.2),
        (2.0, 0.4),
        (3.0, 0.1),
        (3.0, 0.2),
    ]
    
    for qw, mw in configs:
        try:
            passed, min_act, avg_act, max_flat, avg_flat, min_mass = test_config(qw, mw)
            print(f"w0={qw:.2f}, scale={mw:.2f} | Passed={passed} | Act Min={min_act:+.4f} (Avg={avg_act:+.4f}) | Flat Max={max_flat:+.4f} (Avg={avg_flat:+.4f}) | Mass={min_mass:.2f}", flush=True)
        except Exception as e:
            print(f"w0={qw:.2f}, scale={mw:.2f} failed: {e}", flush=True)

if __name__ == "__main__":
    main()
