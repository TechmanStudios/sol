import sys
import math
from pathlib import Path

# Add project root and scratch paths
sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, Instruction, BasinConfig
)
from test_logos_vm_level9_hcam import (
    HCAMProcessingManifold, HCAMManifoldGroup, HCAMSequencer
)

class SwappedHCAMSequencer(HCAMSequencer):
    def __init__(self, group, dt=0.08, baseline_rho=15.0, phase_A=0.0, phase_B=0.0, phi_in_A=0.0, phi_in_B=0.0, null_period=18.0):
        super().__init__(group, dt, baseline_rho, phase_A, phase_B)
        self.phi_in_A = phi_in_A
        self.phi_in_B = phi_in_B
        self.omega_null = 2 * math.pi / (null_period * self.dt)
        
    def execute_instruction(self, inst: Instruction):
        op = inst.op.upper()
        if op == "LOAD_QUERY":
            query_type = inst.args[0]
            self.group.engine.write_enable("P_Bus")
            self.group.engine.write_enable("S_RA")
            self.group.engine.write_enable("S_RA_B")
            self.group.engine.write_enable("Gate_MatchA")
            self.group.engine.write_enable("Gate_MatchB")
            for nid in self.group.semantic.basins["Basin_Query"].node_ids:
                self.group.engine.write_enable(nid)
                
            self.group.set_edge_connection("P_Bus", "Gate_MatchA", False)
            self.group.set_edge_connection("P_Bus", "Gate_MatchB", False)
            
            for s in range(60):
                t = len(self.history) * self.dt
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus", True)
                self.group.get_edge(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus")["w0"] = 10.0
                self.group.get_node("GATE_A")["psi_bias"] = 1.0
                self.group.set_edge_connection("GATE_A", "P_Bus", True)
                self.group.get_edge("GATE_A", "P_Bus")["w0"] = 10.0
                
                amp = 8.0
                if query_type == "A":
                    src_rho = self.baseline_rho + amp * math.sin(self.omega_A * t + self.phi_in_A)
                elif query_type == "B":
                    src_rho = self.baseline_rho + amp * math.sin(self.omega_B * t + self.phi_in_B)
                elif query_type == "PHASE_REV_A":
                    src_rho = self.baseline_rho + amp * math.sin(self.omega_A * t + self.phi_in_A + math.pi)
                else: # "NULL"
                    src_rho = self.baseline_rho + amp * math.sin(self.omega_null * t)
                    
                self.group.get_node(self.group.semantic.basins["Basin_Query"].bridge_id)["rho"] = src_rho
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for s in range(15):
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus", False)
                self.group.get_node("GATE_A")["psi_bias"] = -1.0
                self.group.set_edge_connection("GATE_A", "P_Bus", False)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
        else:
            super().execute_instruction(inst)

def run_sweep_trial_custom(query_type: str, phi_in_A, phi_in_B, p_A, p_B, np, phase_A, phase_B) -> tuple[float, float]:
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
        
    processing = HCAMProcessingManifold(baseline_rho=baseline_rho)
    group = HCAMManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
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
            
    group.prime_register('A', active=True)
    group.get_node("S_RA")["rho"] = baseline_rho
    group.get_node("S_RA_B")["rho"] = 0.0
    
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    class CustomHCAMSequencer(SwappedHCAMSequencer):
        def __init__(self, group, dt=0.08, baseline_rho=15.0, phase_A=0.0, phase_B=0.0, phi_in_A=0.0, phi_in_B=0.0, p_A=10.0, p_B=25.0, np=18.0):
            super().__init__(group, dt, baseline_rho, phase_A, phase_B, phi_in_A, phi_in_B, np)
            self.omega_A = 2 * math.pi / (p_A * self.dt)
            self.omega_B = 2 * math.pi / (p_B * self.dt)
            
    sequencer = CustomHCAMSequencer(group, dt=0.08, baseline_rho=baseline_rho, phase_A=phase_A, phase_B=phase_B, phi_in_A=phi_in_A, phi_in_B=phi_in_B, p_A=p_A, p_B=p_B, np=np)
    sequencer.execute_instruction(Instruction("LOAD_QUERY", [query_type]))
    sequencer.execute_instruction(Instruction("QUERY_HCAM", []))
    
    dest_A_id = group.semantic.basins["Basin_ValA"].bridge_id
    dest_B_id = group.semantic.basins["Basin_ValB"].bridge_id
    delta_A = group.get_node(dest_A_id)["rho"] - baseline_rho
    delta_B = group.get_node(dest_B_id)["rho"] - baseline_rho
    
    return delta_A, delta_B

def main():
    p_A = 10
    p_B = 25
    np = 18
    
    steps = 8
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    best_phase_A = 2.356194
    best_phi_in_A = 1.570796
    
    print(f"Sweeping Channel B with fixed Channel A: phase_A={best_phase_A:.4f}, phi_in_A={best_phi_in_A:.4f}")
    print(f"{'phase_B':<7} | {'phi_B':<7} | {'B:dA':<8} | {'B:dB':<8} | {'A:dA':<8} | {'A:dB':<8} | {'N:dA':<8} | {'N:dB':<8}")
    print("-" * 85)
    
    for phase_B in phases:
        for phi_in_B in phases:
            d01_A, d01_B = run_sweep_trial_custom("B", best_phi_in_A, phi_in_B, p_A, p_B, np, best_phase_A, phase_B)
            d10_A, d10_B = run_sweep_trial_custom("A", best_phi_in_A, phi_in_B, p_A, p_B, np, best_phase_A, phase_B)
            dnull_A, dnull_B = run_sweep_trial_custom("NULL", best_phi_in_A, phi_in_B, p_A, p_B, np, best_phase_A, phase_B)
            
            # Print only configurations where B:dB >= 0.2
            if d01_B >= 0.2:
                print(f"{phase_B:<7.4f} | {phi_in_B:<7.4f} | {d01_A:<+8.4f} | {d01_B:<+8.4f} | {d10_A:<+8.4f} | {d10_B:<+8.4f} | {dnull_A:<+8.4f} | {dnull_B:<+8.4f}")

if __name__ == "__main__":
    main()
