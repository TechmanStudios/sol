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
    MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer, run_level11_trial
)

def run_sweep():
    baseline_rho = 15.0
    val_X = 1  # Only bit 0 is active (period 13.0, Sine)
    
    steps = 16
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print("Sweeping phase for bit 0 (Active) and bit 1 (Flat)...")
    print("Disabling Jeans collapse and semantic mass decay...")
    
    for idx, ph in enumerate(phases):
        temp_phases = [0.0] * 16
        temp_phases[0] = ph
        temp_phases[1] = ph
        
        # Build manifold and configure
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
        
        # Prime query basin hub to 450.0 (pressure 15.0) to prevent mass sink
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
            
        sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
        sequencer.calibrated_phases = temp_phases
        sequencer.is_calibrating = False
        
        # Exec LOAD_16 & QUERY_16
        sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
        sequencer.execute_instruction(Instruction("QUERY_16", []))
        
        deltas = []
        for i in [0, 1]:
            dest_id = group.semantic.basins[f"Basin_Val{i}"].bridge_id
            delta = group.get_node(dest_id)["rho"] - baseline_rho
            deltas.append(delta)
            
        print(f"Phase {ph:.4f} ({ph/math.pi:.2f}*pi): Bit 0 delta = {deltas[0]:+.6f}, Bit 1 delta = {deltas[1]:+.6f}")

if __name__ == "__main__":
    run_sweep()
