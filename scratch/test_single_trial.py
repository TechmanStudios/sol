import sys
import time
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_fast_sweep import run_suite
from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer
)
from test_pdm_search import MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer

def run_single_trial_measure():
    baseline_rho = 15.0
    val_X = 0b1010110011110001
    temp_phases = [0.0] * 16
    
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
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0, cond_max=1000.0)
    
    def custom_prime_register(reg_name: str, active: bool, baseline_rho=15.0):
        for b in range(16):
            host = group.get_node(f"S_R{reg_name}_Bit{b}")
            bat = group.get_node(f"S_R{reg_name}_Bit{b}_B")
            host["rho"] = baseline_rho
            bat["rho"] = baseline_rho
            if active:
                bat["b_state"] = 1
                bat["b_charge"] = 1.0
                bat["psi"] = 1.0
                bat["psi_bias"] = 1.0
                host["psi"] = 1.0
                host["psi_bias"] = 1.0
            else:
                bat["b_state"] = -1
                bat["b_charge"] = 0.0
                bat["psi"] = -1.0
                bat["psi_bias"] = -1.0
                host["psi"] = -1.0
                host["psi_bias"] = -1.0
    group.prime_register = custom_prime_register
    
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    group.prime_register('X', active=True, baseline_rho=baseline_rho)
    group.prime_register('Y', active=False, baseline_rho=baseline_rho)
        
    t0 = time.time()
    # Let's test with rk4
    group.engine.integration_mode = "rk4"
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
    sequencer.calibrated_phases = temp_phases
    sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    sequencer.execute_instruction(Instruction("QUERY_16", []))
    t1 = time.time()
    print(f"rk4 trial took {t1 - t0:.4f} seconds.")
    
    # Let's test with euler
    group.engine.integration_mode = "euler"
    sequencer2 = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
    sequencer2.calibrated_phases = temp_phases
    t0 = time.time()
    sequencer2.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    sequencer2.execute_instruction(Instruction("QUERY_16", []))
    t1 = time.time()
    print(f"euler trial took {t1 - t0:.4f} seconds.")

if __name__ == "__main__":
    run_single_trial_measure()
