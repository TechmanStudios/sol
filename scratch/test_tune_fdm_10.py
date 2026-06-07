#!/usr/bin/env python3
import sys
import os
import json
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)

class FDMProcessingManifold:
    def __init__(self, baseline_rho=10.0):
        self.nodes = []
        self.edges = []
        for reg in ['A', 'B', 'C', 'D']:
            host_id = f"S_R{reg}"
            bat_id = f"S_R{reg}_B"
            # Host and battery match pressure of baseline_rho=10.0 (mass 1.0) -> rho = 200.0
            self.nodes.extend([
                {"id": host_id, "label": f"Register{reg}_Host", "group": "processing", "rho": 200.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
                {"id": bat_id, "label": f"Register{reg}_Battery", "group": "processing", "rho": 200.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
            ])
            self.edges.append({"from": host_id, "to": bat_id, "w0": 150.0})
        for reg in ['A', 'B', 'C', 'D']:
            gate_id = f"GATE_{reg}"
            self.nodes.append(
                {"id": gate_id, "label": f"Gate_{reg}", "group": "bridge", "rho": baseline_rho, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0}
            )
        self.nodes.append(
            {"id": "P_Sum", "label": "Proc_SummingJunction", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0}
        )
        self.edges.extend([
            {"from": "S_RA", "to": "GATE_A", "w0": 5.0},
            {"from": "GATE_A", "to": "P_Sum", "w0": 5.0, "kind": "wormhole", "background": False},
            {"from": "S_RB", "to": "GATE_B", "w0": 5.0},
            {"from": "GATE_B", "to": "P_Sum", "w0": 5.0, "kind": "wormhole", "background": False},
            {"from": "P_Sum", "to": "GATE_C", "w0": 5.0, "kind": "wormhole", "background": False},
            {"from": "GATE_C", "to": "S_RC", "w0": 5.0, "kind": "wormhole", "background": False},
            {"from": "P_Sum", "to": "GATE_D", "w0": 5.0, "kind": "wormhole", "background": False},
            {"from": "GATE_D", "to": "S_RD", "w0": 5.0, "kind": "wormhole", "background": False}
        ])
        self.nodes.extend([
            {"id": "Router_A", "label": "Router_A", "group": "bridge", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0},
            {"id": "Router_B", "label": "Router_B", "group": "bridge", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0}
        ])
        self.edges.extend([
            {"from": "P_Sum", "to": "Router_A", "w0": 5.0, "kind": "wormhole", "background": False},
            {"from": "P_Sum", "to": "Router_B", "w0": 5.0, "kind": "wormhole", "background": False}
        ])

class FDMManifoldGroup(ManifoldGroup):
    def __init__(self, semantic: SemanticManifold, processing: FDMProcessingManifold, c_press: float = 2.0, damping: float = 0.0):
        self.semantic = semantic
        self.processing = processing
        self.raw_nodes = []
        self.raw_nodes.extend(semantic.nodes)
        self.raw_nodes.extend(processing.nodes)
        self.raw_edges = []
        self.raw_edges.extend(semantic.edges)
        self.raw_edges.extend(processing.edges)
        self.raw_edges.extend([
            {"from": semantic.basins["Basin_InA"].bridge_id, "to": "P_Sum", "w0": 0.0001, "kind": "wormhole", "background": False},
            {"from": semantic.basins["Basin_InB"].bridge_id, "to": "P_Sum", "w0": 0.0001, "kind": "wormhole", "background": False}
        ])
        self.raw_edges.extend([
            {"from": "Router_A", "to": semantic.basins["Basin_OutA"].bridge_id, "w0": 0.0001, "kind": "wormhole", "background": False},
            {"from": "Router_B", "to": semantic.basins["Basin_OutB"].bridge_id, "w0": 0.0001, "kind": "wormhole", "background": False}
        ])
        from sol_engine import SOLEngine
        self.engine = SOLEngine.from_graph(self.raw_nodes, self.raw_edges, c_press=c_press, damping=damping)
        self.engine.integration_mode = "rk4"
        self.engine.physics.conductance_max = 200.0
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

    def prime_register(self, name: str, active: bool):
        host = self.get_node(f"S_R{name}")
        bat = self.get_node(f"S_R{name}_B")
        if active:
            bat["b_state"] = 1
            bat["b_charge"] = 1.0
            bat["psi"] = 1.0
            bat["psi_bias"] = 1.0
            host["psi"] = 1.0
            host["psi_bias"] = 1.0
            host["rho"] = 200.0
            bat["rho"] = 200.0
        else:
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = -1.0
            host["rho"] = 10.0
            bat["rho"] = 0.0

class FDMSequencer(MicroInstructionSequencer):
    def __init__(self, group: FDMManifoldGroup, dt: float = 0.08, baseline_rho=10.0, phase_A=0.0, phase_B=0.0):
        super().__init__(group, dt)
        self.min_active_register_mass = float('inf')
        self.history = []
        self.omega_A = 2 * math.pi / (10 * self.dt)
        self.omega_B = 2 * math.pi / (25 * self.dt)
        self.baseline_rho = baseline_rho
        self.phase_A = phase_A
        self.phase_B = phase_B

    def execute_instruction(self, inst: Instruction):
        op = inst.op.upper()
        if op == "LOAD_FDM":
            active_A = inst.args[0]
            active_B = inst.args[1]
            
            # Write-enable inputs, register, and summing core
            self.group.engine.write_enable("P_Sum")
            self.group.engine.write_enable("S_RA")
            self.group.engine.write_enable("S_RA_B")
            self.group.engine.write_enable("Router_A")
            self.group.engine.write_enable("Router_B")
            for nid in self.group.semantic.basins["Basin_InA"].node_ids:
                self.group.engine.write_enable(nid)
            for nid in self.group.semantic.basins["Basin_InB"].node_ids:
                self.group.engine.write_enable(nid)

            # Isolate routers during LOAD
            self.group.set_edge_connection("P_Sum", "Router_A", False)
            self.group.set_edge_connection("P_Sum", "Router_B", False)

            for s in range(60):
                t = len(self.history) * self.dt
                self.group.set_edge_connection(self.group.semantic.basins["Basin_InA"].bridge_id, "P_Sum", True)
                self.group.set_edge_connection(self.group.semantic.basins["Basin_InB"].bridge_id, "P_Sum", True)
                self.group.get_edge(self.group.semantic.basins["Basin_InA"].bridge_id, "P_Sum")["w0"] = 10.0
                self.group.get_edge(self.group.semantic.basins["Basin_InB"].bridge_id, "P_Sum")["w0"] = 10.0
                self.group.get_node("GATE_A")["psi_bias"] = 1.0
                self.group.set_edge_connection("GATE_A", "P_Sum", True)
                self.group.get_edge("GATE_A", "P_Sum")["w0"] = 10.0
                
                # Balanced amplitudes (8.0, 8.0) around baseline 10.0
                amp_A = 8.0
                amp_B = 8.0
                src_rho_A = self.baseline_rho + amp_A * math.sin(self.omega_A * t) if active_A else self.baseline_rho
                src_rho_B = self.baseline_rho + amp_B * math.sin(self.omega_B * t) if active_B else self.baseline_rho
                self.group.get_node(self.group.semantic.basins["Basin_InA"].bridge_id)["rho"] = src_rho_A
                self.group.get_node(self.group.semantic.basins["Basin_InB"].bridge_id)["rho"] = src_rho_B
                
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for s in range(15):
                self.group.set_edge_connection(self.group.semantic.basins["Basin_InA"].bridge_id, "P_Sum", False)
                self.group.set_edge_connection(self.group.semantic.basins["Basin_InB"].bridge_id, "P_Sum", False)
                self.group.get_node("GATE_A")["psi_bias"] = -1.0
                self.group.set_edge_connection("GATE_A", "P_Sum", False)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()

        elif op == "STORE_FDM":
            # Write-enable routers, registers, summing core, and outputs
            self.group.engine.write_enable("P_Sum")
            self.group.engine.write_enable("S_RA")
            self.group.engine.write_enable("S_RA_B")
            self.group.engine.write_enable("Router_A")
            self.group.engine.write_enable("Router_B")
            
            # Neutralize DC belief gradients by setting psi_bias = 0.0 everywhere
            self.group.get_node("S_RA")["psi_bias"] = 0.0
            self.group.get_node("S_RA_B")["psi_bias"] = 0.0
            self.group.get_node("GATE_A")["psi_bias"] = 0.0
            self.group.get_node("P_Sum")["psi_bias"] = 0.0
            self.group.get_node("Router_A")["psi_bias"] = 0.0
            self.group.get_node("Router_B")["psi_bias"] = 0.0
            
            # Connect routers to summing core
            self.group.set_edge_connection("P_Sum", "Router_A", True)
            self.group.set_edge_connection("P_Sum", "Router_B", True)
            self.group.get_edge("P_Sum", "Router_A")["w0"] = 10.0
            self.group.get_edge("P_Sum", "Router_B")["w0"] = 10.0

            for nid in self.group.semantic.basins["Basin_OutA"].node_ids:
                self.group.engine.write_enable(nid)
                # Neutralize belief bias to 0.0
                self.group.get_node(nid)["psi_bias"] = 0.0
            for nid in self.group.semantic.basins["Basin_OutB"].node_ids:
                self.group.engine.write_enable(nid)
                # Neutralize belief bias to 0.0
                self.group.get_node(nid)["psi_bias"] = 0.0

            for s in range(120):
                t = len(self.history) * self.dt
                self.group.get_node("GATE_A")["psi_bias"] = 1.0 # Keep register open
                self.group.set_edge_connection("GATE_A", "P_Sum", True)
                self.group.get_edge("GATE_A", "P_Sum")["w0"] = 10.0
                self.group.set_edge_connection("Router_A", self.group.semantic.basins["Basin_OutA"].bridge_id, True)
                self.group.set_edge_connection("Router_B", self.group.semantic.basins["Basin_OutB"].bridge_id, True)
                self.group.get_edge("Router_A", self.group.semantic.basins["Basin_OutA"].bridge_id)["w0"] = 10.0
                self.group.get_edge("Router_B", self.group.semantic.basins["Basin_OutB"].bridge_id)["w0"] = 10.0
                
                self.group.get_node("Router_A")["psi"] = math.sin(self.omega_A * t + self.phase_A)
                self.group.get_node("Router_B")["psi"] = math.sin(self.omega_B * t + self.phase_B)
                
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for s in range(20):
                self.group.get_node("GATE_A")["psi_bias"] = -1.0
                self.group.set_edge_connection("GATE_A", "P_Sum", False)
                self.group.set_edge_connection("Router_A", self.group.semantic.basins["Basin_OutA"].bridge_id, False)
                self.group.set_edge_connection("Router_B", self.group.semantic.basins["Basin_OutB"].bridge_id, False)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()

    def record_telemetry(self):
        bat_a = self.group.get_node("S_RA_B")
        host_a = self.group.get_node("S_RA")
        tot_rho = bat_a["rho"] + host_a["rho"]
        if tot_rho < self.min_active_register_mass:
            self.min_active_register_mass = tot_rho
        self.history.append({
            "step": len(self.history),
            "reg_a_rho": float(host_a["rho"]),
            "reg_a_psi": float(host_a["psi"]),
            "sum_rho": float(self.group.get_node("P_Sum")["rho"]),
            "router_a_psi": float(self.group.get_node("Router_A")["psi"]),
            "router_b_psi": float(self.group.get_node("Router_B")["psi"]),
            "out_a_rho": float(self.group.get_node(self.group.semantic.basins["Basin_OutA"].bridge_id)["rho"]),
            "out_b_rho": float(self.group.get_node(self.group.semantic.basins["Basin_OutB"].bridge_id)["rho"]),
            "min_active_register_mass": self.min_active_register_mass
        })

def run_fdm_trial(active_A: bool, active_B: bool, baseline_rho=10.0, phase_A=0.0, phase_B=0.0) -> tuple[float, float, list[dict]]:
    nodes_ina, edges_ina, basin_ina = UniversalManifold.build_semantic_basin("Basin_InA", num_nodes=10, start_idx=0)
    nodes_inb, edges_inb, basin_inb = UniversalManifold.build_semantic_basin("Basin_InB", num_nodes=10, start_idx=10)
    nodes_outa, edges_outa, basin_outa = UniversalManifold.build_semantic_basin("Basin_OutA", num_nodes=10, start_idx=20)
    nodes_outb, edges_outb, basin_outb = UniversalManifold.build_semantic_basin("Basin_OutB", num_nodes=10, start_idx=30)
    
    semantic = SemanticManifold(
        nodes=nodes_ina + nodes_inb + nodes_outa + nodes_outb,
        edges=edges_ina + edges_inb + edges_outa + edges_outb,
        basins=[basin_ina, basin_inb, basin_outa, basin_outb]
    )
    for n in semantic.nodes:
        n["rho"] = baseline_rho
    processing = FDMProcessingManifold(baseline_rho=baseline_rho)
    group = FDMManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    group.prime_basin("Basin_InA", active=active_A)
    group.prime_basin("Basin_InB", active=active_B)
    
    for b_name in ["Basin_InA", "Basin_InB", "Basin_OutA", "Basin_OutB"]:
        basin = group.semantic.basins[b_name]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            if nid == basin.hub_id:
                node["rho"] = 300.0
            else:
                node["rho"] = baseline_rho
            
    group.prime_register('A', active=True)
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    sequencer = FDMSequencer(group, dt=0.08, baseline_rho=baseline_rho, phase_A=phase_A, phase_B=phase_B)
    sequencer.execute_instruction(Instruction("LOAD_FDM", [active_A, active_B]))
    sequencer.execute_instruction(Instruction("STORE_FDM", []))
    
    dest_A_id = group.semantic.basins["Basin_OutA"].bridge_id
    dest_B_id = group.semantic.basins["Basin_OutB"].bridge_id
    delta_A = group.get_node(dest_A_id)["rho"] - baseline_rho
    delta_B = group.get_node(dest_B_id)["rho"] - baseline_rho
    
    return delta_A, delta_B, sequencer.history

def main():
    baseline = 10.0
    steps = 16
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print(f"Starting 2D phase sweep at baseline = {baseline}...")
    
    best_score = -1
    best_phases = None
    best_deltas = None
    
    for i, p_A in enumerate(phases):
        for j, p_B in enumerate(phases):
            try:
                d00_A, d00_B, h00 = run_fdm_trial(False, False, baseline, p_A, p_B)
                d10_A, d10_B, h10 = run_fdm_trial(True, False, baseline, p_A, p_B)
                d01_A, d01_B, h01 = run_fdm_trial(False, True, baseline, p_A, p_B)
                d11_A, d11_B, h11 = run_fdm_trial(True, True, baseline, p_A, p_B)
            except Exception as e:
                continue
                
            m00 = h00[-1]["min_active_register_mass"]
            m10 = h10[-1]["min_active_register_mass"]
            m01 = h01[-1]["min_active_register_mass"]
            m11 = h11[-1]["min_active_register_mass"]
            
            cond_00 = (d00_A < 0.1) and (d00_B < 0.1)
            cond_10 = (d10_A >= 0.2) and (d10_B < 0.1)
            cond_01 = (d01_A < 0.1) and (d01_B >= 0.2)
            cond_11 = (d11_A >= 0.2) and (d11_B >= 0.2)
            cond_mass = min(m00, m10, m01, m11) >= 14.0
            
            passed_cases = sum([cond_00, cond_10, cond_01, cond_11, cond_mass])
            
            if passed_cases >= 4:
                print(f"FOUND Phases A={p_A:.3f}, B={p_B:.3f} | Score={passed_cases}/5")
                print(f"  00: A={d00_A:+.3f}, B={d00_B:+.3f}")
                print(f"  10: A={d10_A:+.3f}, B={d10_B:+.3f}")
                print(f"  01: A={d01_A:+.3f}, B={d01_B:+.3f}")
                print(f"  11: A={d11_A:+.3f}, B={d11_B:+.3f}")
                print(f"  Min Mass = {min(m00, m10, m01, m11):.1f}")
                
            if passed_cases > best_score:
                best_score = passed_cases
                best_phases = (p_A, p_B)
                best_deltas = (d00_A, d00_B, d10_A, d10_B, d01_A, d01_B, d11_A, d11_B)
                
    print("\n=== SWEEP COMPLETED ===")
    if best_phases:
        p_A, p_B = best_phases
        print(f"Best Phases: A = {p_A:.4f}, B = {p_B:.4f} (Score: {best_score}/5)")
        print(f"Deltas at best phases:")
        print(f"  Case 00: A={best_deltas[0]:+.4f}, B={best_deltas[1]:+.4f}")
        print(f"  Case 10: A={best_deltas[2]:+.4f}, B={best_deltas[3]:+.4f}")
        print(f"  Case 01: A={best_deltas[4]:+.4f}, B={best_deltas[5]:+.4f}")
        print(f"  Case 11: A={best_deltas[6]:+.4f}, B={best_deltas[7]:+.4f}")

if __name__ == "__main__":
    main()
