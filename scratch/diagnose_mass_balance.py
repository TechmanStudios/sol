import sys
import os
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)
from test_logos_vm_level11_pdm_prime import (
    MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer
)

class CustomSequencer(Level11Sequencer):
    def __init__(self, group: Level11ManifoldGroup, dt: float = 0.08, baseline_rho=15.0, query_steps=120, settle_steps=15):
        super().__init__(group, dt, baseline_rho, query_steps, settle_steps)
        self.match_weights = [30.0, 20.0, 15.0, 10.0]

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
                bat["isBattery"] = False
                host["psi_bias"] = 0.0
                bat["psi_bias"] = 0.0
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
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 10.0
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                g_other = f"GATE_{other_reg}_Bit{b}"
                self.group.get_node(g_other)["psi_bias"] = -1.0
                self.group.set_edge_connection(g_other, f"P_Bus{lane}", False)
            amp = 80.0
            for s in range(150):
                t = len(self.history) * self.dt
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
                for b in range(16):
                    if (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 0.3 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                # Modulation
                num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
                src_rho0 = 15.0
                if num_active0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin0 += math.sin(omega * t + phase_val)
                    src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
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
            for s in range(self.settle_steps):
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
        elif op == "QUERY_16":
            self.group.get_node("P_Bus0")["rho"] = self.baseline_rho
            self.group.get_node("P_Bus1")["rho"] = self.baseline_rho
            for b in range(16):
                self.group.get_node(f"Gate_Match{b}")["rho"] = self.baseline_rho
            active_regs = ["X"]
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            for reg in ['X', 'Y']:
                for b in range(16):
                    self.group.engine.write_enable(f"S_R{reg}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
                    self.group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = False
            for b in range(16):
                gate_id = f"Gate_Match{b}"
                self.group.engine.write_enable(gate_id)
                lane = b // 8
                self.group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
                f_idx = (b % 8) // 2
                self.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = self.match_weights[f_idx]
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
                    self.group.get_node(nid)["psi_bias"] = 0.0
            print("\n--- QUERY_16 Step-by-Step ---")
            for s in range(40):
                t = len(self.history) * self.dt
                for reg in ['X', 'Y']:
                    for b in range(16):
                        lane = b // 8
                        g_active = f"GATE_{reg}_Bit{b}"
                        if reg in active_regs:
                            omega, phase_val = self.get_reg_gate_params(b)
                            val_psi = 0.3 * math.sin(omega * t + phase_val)
                            self.group.get_node(g_active)["psi"] = val_psi
                            self.group.get_node(g_active)["psi_bias"] = val_psi
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                            self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 10.0 # SET COUPLING TO 10.0
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
                    val_psi = 0.3 * math.sin(omega * t + phase_val)
                    self.group.get_node(gate_id)["psi"] = val_psi
                    self.group.get_node(gate_id)["psi_bias"] = val_psi
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                if s in [0, 20, 40, 50, 59]:
                    b0_dest = self.group.get_node(self.group.semantic.basins["Basin_Val0"].bridge_id)
                    b1_dest = self.group.get_node(self.group.semantic.basins["Basin_Val1"].bridge_id)
                    print(f"  Step {s:2d}: P_Bus0 rho={self.group.get_node('P_Bus0')['rho']:.4f}, Basin0 bridge rho={b0_dest['rho']:.4f}, Basin1 bridge rho={b1_dest['rho']:.4f}")
            for s in range(20):
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
        else:
            super().execute_instruction(inst)

def run_diagnose():
    baseline_rho = 15.0
    val_X = 1
    ph = 4.712389  # Peak phase
    
    nodes = []
    edges = []
    basins = []
    for i in range(16):
        n_val, e_val, b_val = UniversalManifold.build_semantic_basin(f"Basin_Val{i}", num_nodes=10, start_idx=i*10)
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
        
    processing = MHRALevel11ProcessingManifold(baseline_rho=baseline_rho)
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    # Disable decay and Jeans
    group.engine.physics.semantic_cfg["decayRate"] = 0.0
    group.engine.physics.jeans_cfg = None
    
    # Prime query basin hub to 450.0 (pressure 15.0)
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
            
    group.prime_register('X', active=True, baseline_rho=baseline_rho)
    group.prime_register('Y', active=False, baseline_rho=baseline_rho)
        
    sequencer = CustomSequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=40, settle_steps=15)
    sequencer.calibrated_phases = [4.712389] * 16
    sequencer.is_calibrating = False
    
    # Exec LOAD_16 & QUERY_16
    sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    
    print("=== AFTER LOAD_16 STATE ===")
    for nid in ["S_RX_Bit0", "S_RX_Bit0_B", "S_RX_Bit1", "S_RX_Bit1_B"]:
        node = group.get_node(nid)
        print(f"  Node {nid}: rho = {node['rho']:.4f}, p = {node['p']:.4f}")
        
    sequencer.execute_instruction(Instruction("QUERY_16", []))
    
    print("=== FINAL STATE DIAGNOSTIC ===")
    
    # Print Basin_Val0 nodes
    print("\nValue Basin 0 (Active Bit):")
    basin = group.semantic.basins["Basin_Val0"]
    for nid in basin.node_ids:
        node = group.get_node(nid)
        print(f"  Node {nid}: rho = {node['rho']:.4f}, p = {node['p']:.4f}, mass = {node['semanticMass']:.2f}")
        
    # Print Basin_Val1 nodes
    print("\nValue Basin 1 (Flat Bit):")
    basin = group.semantic.basins["Basin_Val1"]
    for nid in basin.node_ids:
        node = group.get_node(nid)
        print(f"  Node {nid}: rho = {node['rho']:.4f}, p = {node['p']:.4f}, mass = {node['semanticMass']:.2f}")
        
    # Print Register X Bit 0 nodes
    print("\nRegister X Bit 0 Resonator:")
    for nid in ["S_RX_Bit0", "S_RX_Bit0_B"]:
        node = group.get_node(nid)
        print(f"  Node {nid}: rho = {node['rho']:.4f}, p = {node['p']:.4f}, mass = {node['semanticMass']:.2f}")
        
    # Print Bus and Match gates
    print("\nBus and Match Gates:")
    print(f"  P_Bus0: rho = {group.get_node('P_Bus0')['rho']:.4f}, p = {group.get_node('P_Bus0')['p']:.4f}")
    print(f"  Gate_Match0: rho = {group.get_node('Gate_Match0')['rho']:.4f}, p = {group.get_node('Gate_Match0')['p']:.4f}")
    print(f"  Gate_Match1: rho = {group.get_node('Gate_Match1')['rho']:.4f}, p = {group.get_node('Gate_Match1')['p']:.4f}")

if __name__ == "__main__":
    run_diagnose()
