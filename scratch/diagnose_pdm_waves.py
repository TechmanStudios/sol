import sys
import time
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer
)
from test_pdm_search import MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer

def diagnose():
    baseline_rho = 15.0
    val_X = 0b1010110011110001
    
    calibrated_phases = [4.712389, 4.712389, 4.712389, 4.712389, 2.617994, 2.617994, 1.047198, 1.047198]
    calibrated_phases = calibrated_phases + calibrated_phases
    
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
    
    group.engine.physics.conductance_max = 200.0
    group.engine.physics.conductance_gamma = 4.0
    
    # Prime registers to 300
    for b in range(16):
        group.get_node(f"S_RX_Bit{b}")["rho"] = 300.0
        group.get_node(f"S_RX_Bit{b}_B")["rho"] = 300.0
        group.get_node(f"S_RY_Bit{b}")["rho"] = 300.0
        group.get_node(f"S_RY_Bit{b}_B")["rho"] = 300.0
        
        # Mark active/inactive state in psi
        group.get_node(f"S_RX_Bit{b}")["psi"] = -1.0
        group.get_node(f"S_RX_Bit{b}_B")["psi"] = -1.0
        group.get_node(f"S_RX_Bit{b}_B")["b_state"] = -1
        group.get_node(f"S_RX_Bit{b}_B")["b_charge"] = 0.0
        group.get_node(f"S_RY_Bit{b}")["psi"] = -1.0
        group.get_node(f"S_RY_Bit{b}_B")["psi"] = -1.0
        group.get_node(f"S_RY_Bit{b}_B")["b_state"] = -1
        group.get_node(f"S_RY_Bit{b}_B")["b_charge"] = 0.0

    class DiagnosticSequencer(Level11Sequencer):
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
            is_cosine = (b_local % 2 == 1)
            phase_offset = 0.5 * math.pi if is_cosine else 0.0
            return omega, self.calibrated_phases[b] + phase_offset

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
                    self.group.engine.write_enable(f"Gate_Match{b}")
                    lane = b // 8
                    self.group.set_edge_connection(f"P_Bus{lane}", f"Gate_Match{b}", False)
                    
                for nid in self.group.semantic.basins["Basin_Query"].node_ids:
                    self.group.engine.write_enable(nid)
                    
                for b in range(16):
                    lane = b // 8
                    g_target = f"GATE_{reg_name}_Bit{b}"
                    if (val & (1 << b)):
                        self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                        self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 1.0
                    else:
                        self.group.get_node(g_target)["psi_bias"] = -1.0
                        self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                        
                    g_other = f"GATE_{other_reg}_Bit{b}"
                    self.group.get_node(g_other)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_other, f"P_Bus{lane}", False)
                    
                amp = 8.0
                
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
                                
                    # Lane 0
                    num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
                    src_rho0 = 15.0
                    if num_active0 > 0:
                        sum_sin0 = 0.0
                        for b in range(8):
                            if (val & (1 << b)):
                                omega, phase_val = self.get_reg_gate_params(b)
                                sum_sin0 += math.sin(omega * t + phase_val)
                        src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                        
                    # Lane 1
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
                    
                    self.group.engine.step(dt=self.dt, damping=0.5)
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
                # Let's run query and log details of Bit 0 (Active) vs Bit 1 (Flat)
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
                        self.group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = False
                    
                # Match gates connect to P_Bus0/1
                for b in range(16):
                    gate_id = f"Gate_Match{b}"
                    self.group.engine.write_enable(gate_id)
                    lane = b // 8
                    self.group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
                    f_idx = (b % 8) // 2
                    self.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = self.match_weights[f_idx]
                    self.group.get_node(gate_id)["psi_bias"] = 0.0
                    
                for b in range(16):
                    basin = self.group.semantic.basins[f"Basin_Val{b}"]
                    for nid in basin.node_ids:
                        self.group.engine.write_enable(nid)
                        self.group.get_node(nid)["psi_bias"] = 0.0

                print(f"{'Step':5s} | {'Bus0_rho':8s} | {'Bit0_Host_rho':13s} | {'Bit0_Host_psi':13s} | {'Bit1_Host_rho':13s} | {'Bit1_Host_psi':13s} | {'Val0_rho':8s} | {'Val1_rho':8s}")
                print("-" * 100)
                
                for s in range(120):
                    t = len(self.history) * self.dt
                    
                    # Set register access gates
                    for b in range(16):
                        lane = b // 8
                        g_active = f"GATE_X_Bit{b}"
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 0.3 * math.sin(omega * t + phase_val)
                        self.group.get_node(g_active)["psi"] = val_psi
                        self.group.get_node(g_active)["psi_bias"] = val_psi
                        self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                        self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 1.0
                        
                    # Set match gate outputs
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
                    
                    if s % 10 == 0:
                        bus0_rho = self.group.get_node("P_Bus0")["rho"]
                        b0_rho = self.group.get_node("S_RX_Bit0")["rho"]
                        b0_psi = self.group.get_node("S_RX_Bit0")["psi"]
                        b1_rho = self.group.get_node("S_RX_Bit1")["rho"]
                        b1_psi = self.group.get_node("S_RX_Bit1")["psi"]
                        val0_rho = self.group.get_node(self.group.semantic.basins["Basin_Val0"].bridge_id)["rho"]
                        val1_rho = self.group.get_node(self.group.semantic.basins["Basin_Val1"].bridge_id)["rho"]
                        print(f"{s:5d} | {bus0_rho:8.2f} | {b0_rho:13.2f} | {b0_psi:13.4f} | {b1_rho:13.2f} | {b1_psi:13.4f} | {val0_rho:8.2f} | {val1_rho:8.2f}")

    sequencer = DiagnosticSequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120)
    sequencer.calibrated_phases = calibrated_phases
    group.engine.integration_mode = "euler"
    
    # Run LOAD_16 first!
    sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    # Then run QUERY_16!
    sequencer.execute_instruction(Instruction("QUERY_16", []))

if __name__ == "__main__":
    diagnose()
