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
    def __init__(self, group, dt=0.08, baseline_rho=15.0, phase_A=0.0, phase_B=0.0, phi_in_A=0.0, phi_in_B=0.0, null_period=15.0):
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

def run_sweep_trial_custom(query_type: str, phi_in_A, phi_in_B, period_A, period_B, null_period=15.0) -> tuple[float, float, float]:
    baseline_rho = 15.0
    phase_A = 1.570796
    phase_B = 0.785398
    
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
    for n in processing.nodes:
        if n.get("isBattery"):
            n["isBattery"] = False
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
        def __init__(self, group, dt=0.08, baseline_rho=15.0, phase_A=0.0, phase_B=0.0, phi_in_A=0.0, phi_in_B=0.0, p_A=10.0, p_B=25.0, np=15.0):
            super().__init__(group, dt, baseline_rho, phase_A, phase_B, phi_in_A, phi_in_B, np)
            self.omega_A = 2 * math.pi / (p_A * self.dt)
            self.omega_B = 2 * math.pi / (p_B * self.dt)
            self.omega_null = 2 * math.pi / (np * self.dt)
            
    sequencer = CustomHCAMSequencer(group, dt=0.08, baseline_rho=baseline_rho, phase_A=phase_A, phase_B=phase_B, phi_in_A=phi_in_A, phi_in_B=phi_in_B, p_A=period_A, p_B=period_B, np=null_period)
    sequencer.execute_instruction(Instruction("LOAD_QUERY", [query_type]))
    sequencer.execute_instruction(Instruction("QUERY_HCAM", []))
    
    dest_A_id = group.semantic.basins["Basin_ValA"].bridge_id
    dest_B_id = group.semantic.basins["Basin_ValB"].bridge_id
    delta_A = group.get_node(dest_A_id)["rho"] - baseline_rho
    delta_B = group.get_node(dest_B_id)["rho"] - baseline_rho
    
    min_mass = sequencer.min_active_register_mass
    return delta_A, delta_B, min_mass

def main():
    steps = 8
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print("=== SWEEPING SPECIFIC ORTHOGONAL CANDIDATES ===")
    candidates = [
        (10, 23),
        (10, 27),
        (11, 25),
        (9, 25)
    ]
    
    best_config = None
    
    for p_A, p_B in candidates:
        print(f"\nEvaluating period_A={p_A}, period_B={p_B}...")
        
        # 1. Sweep phi_A for Channel A matching & phase-reversed rejection
        working_phi_A = []
        for phi_A in phases:
            d_A, d_B, m = run_sweep_trial_custom("A", phi_A, 0.0, p_A, p_B)
            d_A_rev, d_B_rev, m_rev = run_sweep_trial_custom("PHASE_REV_A", phi_A, 0.0, p_A, p_B)
            
            # Match A must be >= 0.2, phase-reversed A must be < 0.1
            if d_A >= 0.2 and d_A_rev < 0.1:
                working_phi_A.append((phi_A, d_A, d_A_rev))
                
        if not working_phi_A:
            print("  No working phase found for Channel A.")
            continue
            
        # 2. Sweep phi_B for Channel B matching
        working_phi_B = []
        for phi_B in phases:
            d_A, d_B, m = run_sweep_trial_custom("B", 0.0, phi_B, p_A, p_B)
            if d_B >= 0.2:
                working_phi_B.append((phi_B, d_B))
                
        if not working_phi_B:
            print("  No working phase found for Channel B.")
            continue
            
        # 3. Test cross-talk and find the best phase pair
        found = False
        for phi_A, d_A, d_A_rev in working_phi_A:
            for phi_B, d_B in working_phi_B:
                # Run full Case A to check B cross-talk
                d10_A, d10_B, m10 = run_sweep_trial_custom("A", phi_A, phi_B, p_A, p_B)
                # Run full Case B to check A cross-talk
                d01_A, d01_B, m01 = run_sweep_trial_custom("B", phi_A, phi_B, p_A, p_B)
                
                # Check cross-talk constraints: d10_B < 0.1 and d01_A < 0.1
                if d10_B < 0.1 and d01_A < 0.1:
                    print(f"  FOUND CONFIG: phi_A={phi_A:.4f}, phi_B={phi_B:.4f}")
                    print(f"    Query A: delta_A={d10_A:+.4f}, delta_B={d10_B:+.4f}")
                    print(f"    Query B: delta_A={d01_A:+.4f}, delta_B={d01_B:+.4f}")
                    print(f"    Query A_rev: delta_A={d_A_rev:+.4f}")
                    
                    # Sweep Null period for this working configuration
                    print(f"    Sweeping Null Period for A={p_A}, B={p_B}...")
                    null_periods = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
                    for np in null_periods:
                        if np == p_A or np == p_B:
                            continue
                        d_A_null, d_B_null, m_null = run_sweep_trial_custom("NULL", phi_A, phi_B, p_A, p_B, np)
                        print(f"      np={np} | delta_A={d_A_null:+.4f}, delta_B={d_B_null:+.4f}")
                        if d_A_null < 0.1 and d_B_null < 0.1:
                            print(f"    ==> WORKING NULL PERIOD FOUND: np={np} | delta_A={d_A_null:+.4f}, delta_B={d_B_null:+.4f}")
                            best_config = (p_A, p_B, phi_A, phi_B, np)
                            break
                    found = True
                    break
            if found:
                break

    if best_config is not None:
        p_A, p_B, phi_A, phi_B, np = best_config
        print(f"\n--> Discovered Working Configuration:")
        print(f"  period_A = {p_A}")
        print(f"  period_B = {p_B}")
        print(f"  phi_in_A = {phi_A:.6f}")
        print(f"  phi_in_B = {phi_B:.6f}")
        print(f"  null_period = {np}")
    else:
        print("\nNo complete configuration with working Null period was found.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
