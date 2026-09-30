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

class MHRALevel11ProcessingManifoldWeak:
    def __init__(self, baseline_rho=15.0):
        self.nodes = []
        self.edges = []
        
        # Registers X and Y, each running with 16 independent resonators
        for reg in ['X', 'Y']:
            for b in range(16):
                host_id = f"S_R{reg}_Bit{b}"
                bat_id = f"S_R{reg}_Bit{b}_B"
                self.nodes.extend([
                    {"id": host_id, "label": f"Register{reg}_Bit{b}_Host", "group": "processing", "rho": baseline_rho * 20.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
                    {"id": bat_id, "label": f"Register{reg}_Bit{b}_Battery", "group": "processing", "rho": baseline_rho * 20.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
                ])
                # Prime coprime periods matching the verified prime configuration
                b_local = b % 8
                f_idx = b_local // 2
                p = [10.0, 12.0, 15.0, 20.0][f_idx]
                dt = 0.04
                omega = (2 * math.pi) / (p * dt)
                w0_tuned = 10.0 * (omega ** 2)
                self.edges.append({"from": host_id, "to": bat_id, "w0": w0_tuned})
                
        # Register access gates (16 gates per register)
        for reg in ['X', 'Y']:
            for b in range(16):
                gate_id = f"GATE_{reg}_Bit{b}"
                self.nodes.append(
                    {"id": gate_id, "label": f"Gate_{reg}_Bit{b}", "group": "bridge", "rho": baseline_rho, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0}
                )
                
        # Dual Shared Waveguide Bus Nodes
        self.nodes.extend([
            {"id": "P_Bus0", "label": "Shared_Bus_Lane0", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0},
            {"id": "P_Bus1", "label": "Shared_Bus_Lane1", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0}
        ])
        
        # Connect registers to respective bus lanes (bits 0-7 to Bus 0, bits 8-15 to Bus 1)
        # Weak register-to-bus coupling w0 = 0.2 to prevent phase pulling
        for reg in ['X', 'Y']:
            for b in range(16):
                gate_id = f"GATE_{reg}_Bit{b}"
                lane = b // 8
                self.edges.extend([
                    {"from": f"S_R{reg}_Bit{b}", "to": gate_id, "w0": 5.0},
                    {"from": gate_id, "to": f"P_Bus{lane}", "w0": 5.0, "kind": "wormhole", "background": False}
                ])
            
        # 16 matching gates (0-7 connect to P_Bus0, 8-15 connect to P_Bus1)
        # Weak bus-to-match-gate coupling w0 = 0.2 to prevent phase pulling
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            self.nodes.append(
                {"id": gate_id, "label": gate_id, "group": "bridge", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0}
            )
            lane = b // 8
            self.edges.append(
                {"from": f"P_Bus{lane}", "to": gate_id, "w0": 5.0, "kind": "wormhole", "background": False}
            )

class Level11ManifoldGroupWeak(ManifoldGroup):
    def __init__(self, semantic: SemanticManifold, processing: MHRALevel11ProcessingManifoldWeak, c_press: float = 2.0, damping: float = 0.0):
        self.semantic = semantic
        self.processing = processing
        self.raw_nodes = []
        self.raw_nodes.extend(semantic.nodes)
        self.raw_nodes.extend(processing.nodes)
        self.raw_edges = []
        self.raw_edges.extend(semantic.edges)
        self.raw_edges.extend(processing.edges)
        
        # Connect query input basin to BOTH bus lanes (very weak background weight)
        self.raw_edges.extend([
            {"from": semantic.basins["Basin_Query"].bridge_id, "to": "P_Bus0", "w0": 0.0001, "kind": "wormhole", "background": False},
            {"from": semantic.basins["Basin_Query"].bridge_id, "to": "P_Bus1", "w0": 0.0001, "kind": "wormhole", "background": False}
        ])
        
        # Connect matching gates to target value destination basins
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            self.raw_edges.append(
                {"from": gate_id, "to": semantic.basins[f"Basin_Val{b}"].bridge_id, "w0": 0.0001, "kind": "wormhole", "background": False}
            )
            
        from sol_engine import SOLEngine
        self.engine = SOLEngine.from_graph(self.raw_nodes, self.raw_edges, c_press=c_press, damping=damping)
        self.engine.integration_mode = "rk4"
        self.engine.physics.semantic_cfg["decayRate"] = 0.0
        self.engine.physics.jeans_cfg = None
        self.engine.physics.conductance_max = 50000.0
        self.engine.physics.conductance_min = 1e-7
        self.engine.physics.conductance_gamma = 6.0
        self.engine.physics.psi_diffusion = 0.0
        self.engine.physics.psi_relax_base = 8.0
        self.engine.physics.psi_global_nudge = 0.0
        self.engine.physics.battery_cfg = {
            "qMax": 80.0, "qThresh": 5.0, "leakLambda": 0.01, "avalancheGain": 5.0,
            "resonanceBoost": 4.0, "dampingClamp": 0.1, "flipThreshold": 0.65,
            "collapseFactor": 0.10, "resonanceDrive": 50.0, "dampingDrag": 0.3,
            "diodeResonanceOut": 1.0, "diodeResonanceIn": 1.0, "diodeDampingOut": 1.0, "diodeDampingIn": 1.0
        }

    def prime_register(self, reg_name: str, active: bool, baseline_rho=15.0):
        for b in range(16):
            host = self.get_node(f"S_R{reg_name}_Bit{b}")
            bat = self.get_node(f"S_R{reg_name}_Bit{b}_B")
            if active:
                bat["b_state"] = 1
                bat["b_charge"] = 1.0
                bat["psi"] = 1.0
                bat["psi_bias"] = 1.0
                host["psi"] = 1.0
                host["psi_bias"] = 1.0
                host["rho"] = baseline_rho * 20.0
                bat["rho"] = baseline_rho * 20.0
            else:
                bat["b_state"] = -1
                bat["b_charge"] = 0.0
                bat["psi"] = -1.0
                bat["psi_bias"] = -1.0
                host["psi"] = -1.0
                host["psi_bias"] = -1.0
                host["rho"] = baseline_rho * 20.0
                bat["rho"] = baseline_rho * 20.0

class Level11SequencerWeak(MicroInstructionSequencer):
    def __init__(self, group: Level11ManifoldGroupWeak, dt: float = 0.04, baseline_rho=15.0, query_steps=120, settle_steps=15):
        super().__init__(group, dt)
        self.min_active_register_mass = float('inf')
        self.history = []
        self.baseline_rho = baseline_rho
        self.query_steps = query_steps
        self.settle_steps = settle_steps
        
        self.periods = [10.0, 12.0, 15.0, 20.0]
        self.omegas = [2 * math.pi / (p * self.dt) for p in self.periods]
        self.calibrated_phases = [0.0] * 16
        self.match_weights = [120.0, 80.0, 60.0, 40.0]

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
            
            for b in range(16):
                host = self.group.get_node(f"S_R{reg_name}_Bit{b}")
                bat = self.group.get_node(f"S_R{reg_name}_Bit{b}_B")
                self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
                
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
                
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                if (val & (1 << b)):
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 0.2
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
                g_other = f"GATE_{other_reg}_Bit{b}"
                self.group.get_node(g_other)["psi_bias"] = -1.0
                self.group.set_edge_connection(g_other, f"P_Bus{lane}", False)
                
            amp = 150.0
            
            for s in range(80):
                t = s * self.dt
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
                
                for b in range(16):
                    if (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 1.0 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                
                # Modulate superposition of active bits directly onto P_Bus nodes
                # Lane 0 (bits 0..7)
                num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
                src_rho0 = 15.0
                if num_active0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin0 += math.sin(omega * t + phase_val)
                    src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                    
                # Lane 1 (bits 8..15)
                num_active1 = sum(1 for b in range(8, 16) if (val & (1 << b)))
                src_rho1 = 15.0
                if num_active1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin1 += math.sin(omega * t + phase_val)
                    src_rho1 += (amp / math.sqrt(num_active1)) * sum_sin1
                    
                self.group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
                self.group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
                
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                self.group.get_node(g_target)["psi_bias"] = -1.0
                self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                
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
                    
            for b in range(16):
                gate_id = f"Gate_Match{b}"
                self.group.engine.write_enable(gate_id)
                lane = b // 8
                self.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = 5.0  # STRONG COUPLING WITH PASSIVE GATES
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
                    
            for s in range(self.query_steps):
                t = s * self.dt
                for reg in ['X', 'Y']:
                    for b in range(16):
                        lane = b // 8
                        g_active = f"GATE_{reg}_Bit{b}"
                        
                        bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                        is_bit_active = (bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.5)
                        if reg in active_regs and is_bit_active:
                            # PASSIVE GATE: do NOT overwrite psi! Just write-enable and set bias to 0
                            self.group.get_node(g_active)["psi_bias"] = 0.0
                            self.group.engine.write_enable(g_active)
                            self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 5.0
                        else:
                            self.group.get_node(g_active)["psi_bias"] = -1.0
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                            
                for b in range(16):
                    gate_id = f"Gate_Match{b}"
                    dest_basin_id = f"Basin_Val{b}"
                    
                    self.group.set_edge_connection(gate_id, self.group.semantic.basins[dest_basin_id].bridge_id, True)
                    f_idx = (b % 8) // 2
                    self.group.get_edge(gate_id, self.group.semantic.basins[dest_basin_id].bridge_id)["w0"] = self.match_weights[f_idx]
                    
                    omega, phase_val = self.get_match_gate_params(b)
                    if phase_invert:
                        phase_val += math.pi
                    val_psi = 1.0 * math.sin(omega * t + phase_val)
                    self.group.get_node(gate_id)["psi"] = val_psi
                    self.group.get_node(gate_id)["psi_bias"] = val_psi
                    
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

def run_passive_trial(val_X: int, val_Y: int, calibrated_phases: list[float], baseline_rho=15.0, query_steps=120, settle_steps=15) -> tuple[list[float], list[dict]]:
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
        
    processing = MHRALevel11ProcessingManifoldWeak(baseline_rho=baseline_rho)
    group = Level11ManifoldGroupWeak(semantic, processing, c_press=2.0, damping=0.0)
    
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
    
    group.prime_register('X', active=active_X, baseline_rho=baseline_rho)
    group.prime_register('Y', active=active_Y, baseline_rho=baseline_rho)
        
    sequencer = Level11SequencerWeak(group, dt=0.04, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
    sequencer.calibrated_phases = calibrated_phases
    
    if active_X:
        sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    if active_Y:
        sequencer.execute_instruction(Instruction("LOAD_16", ["Y", val_Y]))
        
    post_load_snap = snapshot_state(group.engine.physics)
    
    pre_query_rhos = []
    for i in range(16):
        dest_id = group.semantic.basins[f"Basin_Val{i}"].bridge_id
        pre_query_rhos.append(group.get_node(dest_id)["rho"])

    sequencer.execute_instruction(Instruction("QUERY_16", ["plus"]))
    
    rhos_plus = []
    for i in range(16):
        dest_id = group.semantic.basins[f"Basin_Val{i}"].bridge_id
        rhos_plus.append(group.get_node(dest_id)["rho"])
        
    plus_history = list(sequencer.history)
    
    restore_state(group.engine.physics, post_load_snap)
    
    load_history_len = len(plus_history) - (query_steps + 40)
    sequencer.history = plus_history[:load_history_len]
    sequencer.min_active_register_mass = float('inf')
    
    sequencer.execute_instruction(Instruction("QUERY_16", ["minus"]))
    
    rhos_minus = []
    for i in range(16):
        dest_id = group.semantic.basins[f"Basin_Val{i}"].bridge_id
        rhos_minus.append(group.get_node(dest_id)["rho"])
        
    deltas = []
    for i in range(16):
        delta = (rhos_plus[i] - rhos_minus[i]) / 2.0
        deltas.append(delta)
    
    for reg in ['X', 'Y']:
        for b in range(16):
            bat = group.get_node(f"S_R{reg}_Bit{b}_B")
            host = group.get_node(f"S_R{reg}_Bit{b}")
            bat["isBattery"] = True
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = -1.0
            host["rho"] = baseline_rho * 20.0
            bat["rho"] = baseline_rho * 20.0
            
    return deltas, plus_history

def run_passive_trial_wrapper(val_X: int, val_Y: int, calibrated_phases: list[float], baseline_rho=15.0, query_steps=120, settle_steps=15):
    return run_passive_trial(val_X, val_Y, calibrated_phases, baseline_rho, query_steps, settle_steps)


# Run phase sweep
def test_phase_sweep():
    baseline = 15.0
    query_steps = 120
    settle_steps = 30
    
    # Let's calibrate phases under the passive scheme first!
    print("Calibrating under passive scheme...")
    calibrated = [0.0] * 16
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    for b in range(2): # just calibrate bit 0 and 1
        best_phase = 0.0
        max_delta = -float('inf')
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[b] = ph
            # Load the corresponding bit (1 for bit 0, 2 for bit 1)
            val_X = 1 << b
            deltas, _ = run_passive_trial(val_X, 0, temp_phases, baseline_rho=baseline, query_steps=query_steps, settle_steps=settle_steps)
            if deltas[b] > max_delta:
                max_delta = deltas[b]
                best_phase = ph
        print(f"Calibrated Bit {b}: {best_phase:.4f} (deg: {best_phase * 180 / math.pi:.1f}) with max_delta {max_delta:.4f}")
        calibrated[b] = best_phase
        
    print("\nRunning sweep on Bit 0 (with Bit 1 active)...")
    print("Phase (rad) | Phase (deg) | Bit 0 Delta | Bit 1 Delta")
    print("-" * 60)
    for ph in phases:
        # Load only Bit 1
        temp_phases = list(calibrated)
        temp_phases[0] = ph
        deltas, _ = run_passive_trial(2, 0, temp_phases, baseline, query_steps, settle_steps)
        print(f"{ph:11.6f} | {ph * 180 / math.pi:11.1f} | {deltas[0]:11.6f} | {deltas[1]:11.6f}")

if __name__ == "__main__":
    test_phase_sweep()
