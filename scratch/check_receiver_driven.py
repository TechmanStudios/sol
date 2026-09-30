import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from debug_passive_gates import (
    MHRALevel11ProcessingManifoldWeak, Level11ManifoldGroupWeak, Level11SequencerWeak
)
from hybrid_subsystem_framework import UniversalManifold, SemanticManifold, Instruction
from sol_engine import snapshot_state, restore_state

class Level11SequencerReceiverDriven(Level11SequencerWeak):
    def execute_instruction(self, inst: Instruction):
        op = inst.op.upper()
        if op == "LOAD_16":
            # Use the standard LOAD_16 from debug_passive_gates.py (which drives register gates and modulates bus)
            super().execute_instruction(inst)
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
                self.group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
                self.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = 5.0 # Strong coupling
                self.group.get_node(gate_id)["psi_bias"] = 0.0 # Passive match gates!
                
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
                            # Active modulator gate: driven!
                            omega, phase_val = self.get_reg_gate_params(b)
                            val_psi = 1.0 * math.sin(omega * t + phase_val)
                            self.group.get_node(g_active)["psi"] = val_psi
                            self.group.get_node(g_active)["psi_bias"] = val_psi
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                            self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 5.0
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
                    
                    # Receiver-driven: drive the value basin bridge node's psi!
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

def run_trial_receiver_driven(val_X: int, val_Y: int, calibrated_phases: list[float], baseline_rho=15.0, query_steps=120, settle_steps=15):
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
        
    sequencer = Level11SequencerReceiverDriven(group, dt=0.04, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
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
    
    return deltas

def main():
    print("Calibrating under receiver-driven scheme...")
    calibrated = [0.0] * 16
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    for b in range(2): # calibrate bit 0 and 1
        best_phase = 0.0
        max_delta = -float('inf')
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[b] = ph
            val_X = 1 << b
            deltas = run_trial_receiver_driven(val_X, 0, temp_phases, query_steps=120, settle_steps=30)
            if deltas[b] > max_delta:
                max_delta = deltas[b]
                best_phase = ph
        print(f"Calibrated Bit {b}: {best_phase:.4f} (deg: {best_phase * 180 / math.pi:.1f}) with max_delta {max_delta:.4f}")
        calibrated[b] = best_phase
        
    print("\nRunning sweep on Bit 0 (with Bit 1 active)...")
    print("Phase (rad) | Phase (deg) | Bit 0 Delta | Bit 1 Delta")
    print("-" * 60)
    for ph in phases:
        temp_phases = list(calibrated)
        temp_phases[0] = ph
        # Load only Bit 1
        deltas = run_trial_receiver_driven(2, 0, temp_phases, query_steps=120, settle_steps=30)
        print(f"{ph:11.6f} | {ph * 180 / math.pi:11.1f} | {deltas[0]:11.6f} | {deltas[1]:11.6f}")

if __name__ == "__main__":
    main()
