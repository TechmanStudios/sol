import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level10_mhra import run_mhra_trial

def run_trial_with_weight(query_A, query_B, w0_B, phase_A, phase_B, phi_in_A, phi_in_B):
    from test_logos_vm_level10_mhra import UniversalManifold, SemanticManifold, MHRADualProcessingManifold, MHRAManifoldGroup, MHRASequencer, Instruction
    
    baseline_rho = 15.0
    nodes_q, edges_q, basin_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=0)
    nodes_val_a, edges_val_a, basin_val_a = UniversalManifold.build_semantic_basin("Basin_ValA", num_nodes=10, start_idx=10)
    nodes_val_b, edges_val_b, basin_val_b = UniversalManifold.build_semantic_basin("Basin_ValB", num_nodes=10, start_idx=20)
    
    semantic = SemanticManifold(
        nodes=nodes_q + nodes_val_a + nodes_val_b,
        edges=edges_q + edges_val_a + edges_val_b,
        basins=[basin_q, basin_val_a, basin_val_b]
    )
    for n in semantic.nodes:
        n["rho"] = baseline_rho
        
    processing = MHRADualProcessingManifold(baseline_rho=baseline_rho)
    group = MHRAManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    # Prime query input
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline_rho
            
    for b_name in ["Basin_ValA", "Basin_ValB"]:
        basin = group.semantic.basins[b_name]
        for nid in basin.node_ids:
            group.get_node(nid)["rho"] = baseline_rho
            
    active_reg_A = (query_A != "NULL")
    active_reg_B = (query_B != "NULL")
    
    group.prime_register('A', active=active_reg_A)
    if active_reg_A:
        group.get_node("S_RA")["rho"] = baseline_rho
        group.get_node("S_RA_B")["rho"] = 0.0
        
    group.prime_register('B', active=active_reg_B)
    if active_reg_B:
        group.get_node("S_RB")["rho"] = baseline_rho
        group.get_node("S_RB_B")["rho"] = 0.0
        
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    # Custom sequencer that uses w0_B during QUERY_MHRA
    class CustomMHRASequencer(MHRASequencer):
        def __init__(self, group, w0_B, **kwargs):
            super().__init__(group, **kwargs)
            self.w0_B = w0_B
            
        def execute_instruction(self, inst):
            op = inst.op.upper()
            if op == "QUERY_MHRA":
                self.group.engine.write_enable("P_Bus")
                self.group.engine.write_enable("S_RA")
                self.group.engine.write_enable("S_RA_B")
                self.group.engine.write_enable("S_RB")
                self.group.engine.write_enable("S_RB_B")
                self.group.engine.write_enable("Gate_MatchA")
                self.group.engine.write_enable("Gate_MatchB")
                
                self.group.get_node("S_RA")["psi_bias"] = 0.0
                self.group.get_node("S_RA_B")["psi_bias"] = 0.0
                self.group.get_node("S_RB")["psi_bias"] = 0.0
                self.group.get_node("S_RB_B")["psi_bias"] = 0.0
                self.group.get_node("GATE_A")["psi_bias"] = 0.0
                self.group.get_node("GATE_B")["psi_bias"] = 0.0
                self.group.get_node("P_Bus")["psi_bias"] = 0.0
                self.group.get_node("Gate_MatchA")["psi_bias"] = 0.0
                self.group.get_node("Gate_MatchB")["psi_bias"] = 0.0
                
                self.group.set_edge_connection("P_Bus", "Gate_MatchA", True)
                self.group.set_edge_connection("P_Bus", "Gate_MatchB", True)
                self.group.get_edge("P_Bus", "Gate_MatchA")["w0"] = 10.0
                self.group.get_edge("P_Bus", "Gate_MatchB")["w0"] = self.w0_B
                
                for nid in self.group.semantic.basins["Basin_ValA"].node_ids:
                    self.group.engine.write_enable(nid)
                    self.group.get_node(nid)["psi_bias"] = 0.0
                for nid in self.group.semantic.basins["Basin_ValB"].node_ids:
                    self.group.engine.write_enable(nid)
                    self.group.get_node(nid)["psi_bias"] = 0.0
                    
                active_regs = []
                for reg in ['A', 'B']:
                    bat = self.group.get_node(f"S_R{reg}_B")
                    if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                        active_regs.append(reg)
                        
                for s in range(120):
                    t = len(self.history) * self.dt
                    for reg in ['A', 'B']:
                        gate_id = f"GATE_{reg}"
                        if reg in active_regs:
                            self.group.get_node(gate_id)["psi_bias"] = 1.0
                            self.group.set_edge_connection(gate_id, "P_Bus", True)
                            self.group.get_edge(gate_id, "P_Bus")["w0"] = 10.0
                        else:
                            self.group.get_node(gate_id)["psi_bias"] = -1.0
                            self.group.set_edge_connection(gate_id, "P_Bus", False)
                    
                    self.group.set_edge_connection("Gate_MatchA", self.group.semantic.basins["Basin_ValA"].bridge_id, True)
                    self.group.set_edge_connection("Gate_MatchB", self.group.semantic.basins["Basin_ValB"].bridge_id, True)
                    self.group.get_edge("Gate_MatchA", self.group.semantic.basins["Basin_ValA"].bridge_id)["w0"] = 10.0
                    self.group.get_edge("Gate_MatchB", self.group.semantic.basins["Basin_ValB"].bridge_id)["w0"] = self.w0_B
                    
                    self.group.get_node("Gate_MatchA")["psi"] = math.sin(self.omega_A * t + self.phase_A)
                    self.group.get_node("Gate_MatchB")["psi"] = math.sin(self.omega_B * t + self.phase_B)
                    
                    self.group.engine.step(dt=self.dt, damping=0.0)
                    self.record_telemetry()
                    
                for s in range(20):
                    self.group.get_node("GATE_A")["psi_bias"] = -1.0
                    self.group.get_node("GATE_B")["psi_bias"] = -1.0
                    self.group.set_edge_connection("GATE_A", "P_Bus", False)
                    self.group.set_edge_connection("GATE_B", "P_Bus", False)
                    self.group.set_edge_connection("Gate_MatchA", self.group.semantic.basins["Basin_ValA"].bridge_id, False)
                    self.group.set_edge_connection("Gate_MatchB", self.group.semantic.basins["Basin_ValB"].bridge_id, False)
                    self.group.engine.step(dt=self.dt, damping=0.0)
                    self.record_telemetry()
            else:
                super().execute_instruction(inst)
                
    sequencer = CustomMHRASequencer(group, w0_B, dt=0.08, baseline_rho=baseline_rho, phase_A=phase_A, phase_B=phase_B, phi_in_A=phi_in_A, phi_in_B=phi_in_B, null_period=13.0)
    
    if query_A != "NULL":
        sequencer.execute_instruction(Instruction("LOAD_QUERY", ["A", query_A]))
    if query_B != "NULL":
        sequencer.execute_instruction(Instruction("LOAD_QUERY", ["B", query_B]))
        
    sequencer.execute_instruction(Instruction("QUERY_MHRA", []))
    
    dest_A_id = group.semantic.basins["Basin_ValA"].bridge_id
    dest_B_id = group.semantic.basins["Basin_ValB"].bridge_id
    delta_A = group.get_node(dest_A_id)["rho"] - baseline_rho
    delta_B = group.get_node(dest_B_id)["rho"] - baseline_rho
    
    return delta_A, delta_B

def main():
    phase_A = 2.356194
    phase_B = 0.0
    phi_in_A = 1.570796
    phi_in_B = 1.570796
    
    print("Lowering Gate_MatchB weight (w0_B) and checking Case C (Parallel Superimposed Recall)...")
    print(f"{'w0_B':<6} | {'dA_C':<8} | {'dB_C':<8} | {'dA_A':<8} | {'dB_A':<8} | {'dA_B':<8} | {'dB_B':<8}")
    print("-" * 70)
    
    for w0_B in [5.0, 3.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005]:
        # Case C
        dA_C, dB_C = run_trial_with_weight("A", "B", w0_B, phase_A, phase_B, phi_in_A, phi_in_B)
        # Case A
        dA_A, dB_A = run_trial_with_weight("A", "NULL", w0_B, phase_A, phase_B, phi_in_A, phi_in_B)
        # Case B
        dA_B, dB_B = run_trial_with_weight("NULL", "B", w0_B, phase_A, phase_B, phi_in_A, phi_in_B)
        
        print(f"{w0_B:<6.3f} | {dA_C:<+8.4f} | {dB_C:<+8.4f} | {dA_A:<+8.4f} | {dB_A:<+8.4f} | {dA_B:<+8.4f} | {dB_B:<+8.4f}")

if __name__ == "__main__":
    main()
