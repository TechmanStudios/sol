import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_final import run_level11_trial

# Let's run a trial with only bit 0 active
# and check what the psi values look like.
# We will intercept the simulation loop or just run it.
# Actually, let's write a custom simulation loop here to print the psi values!

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction
)
from test_logos_vm_level11_pdm_final import (
    Level11ManifoldGroup, Level11Sequencer, MHRALevel11ProcessingManifold
)

def debug_run():
    baseline_rho = 15.0
    query_steps = 20
    settle_steps = 15
    calibrated_phases = [0.0] * 16
    
    # Build manifold
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
        
    processing = MHRALevel11ProcessingManifold(baseline_rho=baseline_rho)
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    # Prime X bit 1 (Cosine, period 5.0)
    group.prime_register('X', active=True, baseline_rho=baseline_rho)
    group.prime_register('Y', active=True, baseline_rho=baseline_rho)
    
    sequencer = Level11Sequencer(group, dt=0.04, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
    sequencer.calibrated_phases = calibrated_phases
    
    # Run load
    print("--- Running LOAD_16 X, 2 (bit 1 active) ---")
    sequencer.execute_instruction(Instruction("LOAD_16", ["X", 2]))
    sequencer.execute_instruction(Instruction("LOAD_16", ["Y", 0]))
    
    # Start QUERY_16
    print("\n--- Starting QUERY_16 ---")
    # Execute query manually to print values
    inst = Instruction("QUERY_16", ["plus"])
    
    # Reset bus and matching gate densities to 15.0 at query start to clear transients
    sequencer.group.get_node("P_Bus0")["rho"] = sequencer.baseline_rho
    sequencer.group.get_node("P_Bus1")["rho"] = sequencer.baseline_rho
    for b in range(16):
        sequencer.group.get_node(f"Gate_Match{b}")["rho"] = sequencer.baseline_rho
        
    # Reset all edge fluxes to 0.0
    for e in sequencer.group.engine.physics.edges:
        is_resonator = (
            (e["from"].startswith("S_R") and e["to"].endswith("_B")) or
            (e["to"].startswith("S_R") and e["from"].endswith("_B"))
        )
        if not is_resonator:
            e["flux"] = 0.0
        
    # Write-enable processing nodes
    sequencer.group.engine.write_enable("P_Bus0")
    sequencer.group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for b in range(16):
            sequencer.group.engine.write_enable(f"S_R{reg}_Bit{b}")
            sequencer.group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
            sequencer.group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = False
            
    for b in range(16):
        gate_id = f"Gate_Match{b}"
        sequencer.group.engine.write_enable(gate_id)
        lane = b // 8
        sequencer.group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
        sequencer.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = 5.0
        sequencer.group.get_node(gate_id)["psi_bias"] = 0.0
        
    # Clear residual waves
    for nid in ["P_Bus0", "P_Bus1"]:
        node = sequencer.group.get_node(nid)
        node["psi"] = 0.0
        node["psi_bias"] = 0.0
    for b in range(16):
        for prefix in ["Gate_Match", "GATE_X_Bit", "GATE_Y_Bit"]:
            node = sequencer.group.get_node(f"{prefix}{b}")
            node["psi"] = 0.0
            node["psi_bias"] = 0.0
        basin = sequencer.group.semantic.basins[f"Basin_Val{b}"]
        for nid in basin.node_ids:
            sequencer.group.engine.write_enable(nid)
            node = sequencer.group.get_node(nid)
            node["psi"] = 0.0
            node["psi_bias"] = 0.0
            
    # Print header
    print(f"{'Step':5s} | {'GATE_X_Bit1 psi':16s} | {'GATE_X_Bit1 rho':15s} | {'P_Bus0 rho':12s} | {'Gate_Match0 rho':15s}")
    print("-" * 75)
    
    for s in range(query_steps):
        t = s * sequencer.dt
        # Drive active gate 1
        omega, phase_val = sequencer.get_reg_gate_params(1) # Bit 1 is Cosine (phase pi/2)
        val_psi = 1.0 * math.sin(omega * t + phase_val)
        
        g_active = "GATE_X_Bit1"
        sequencer.group.get_node(g_active)["psi"] = val_psi
        sequencer.group.get_node(g_active)["psi_bias"] = val_psi
        sequencer.group.set_edge_connection(g_active, "P_Bus0", True)
        sequencer.group.get_edge(g_active, "P_Bus0")["w0"] = 5.0
        
        # Drive matching gates (match phase = 0.0)
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            dest_basin_id = f"Basin_Val{b}"
            bridge_node = sequencer.group.semantic.basins[dest_basin_id].bridge_id
            
            sequencer.group.set_edge_connection(gate_id, bridge_node, True)
            f_idx = (b % 8) // 2
            sequencer.group.get_edge(gate_id, bridge_node)["w0"] = sequencer.match_weights[f_idx]
            
            omega_m, phase_val_m = sequencer.get_match_gate_params(b)
            val_psi_m = 1.0 * math.sin(omega_m * t + phase_val_m)
            sequencer.group.get_node(bridge_node)["psi"] = val_psi_m
            sequencer.group.get_node(bridge_node)["psi_bias"] = val_psi_m
            
        sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
        
        # Print densities
        g_psi = sequencer.group.get_node("GATE_X_Bit1")["psi"]
        g_rho = sequencer.group.get_node("GATE_X_Bit1")["rho"]
        bus_rho = sequencer.group.get_node("P_Bus0")["rho"]
        m0_rho = sequencer.group.get_node("Gate_Match0")["rho"]
        print(f"{s:5d} | {g_psi:+16.6f} | {g_rho:+15.6f} | {bus_rho:+12.6f} | {m0_rho:+15.6f}")

if __name__ == "__main__":
    debug_run()
