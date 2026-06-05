#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Hybrid Sub-system Framework (Level 5: Manifold-Systems)
============================================================
An object-oriented, programmable framework for executing multi-cycle analog
and semantic programs on coupled SOL substrates.
"""

import sys
import os
import math
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

# Add sol-core path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Force bind telemetry to prevent collisions
import importlib.util
telemetry_path = sol_root / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine

@dataclass
class BasinConfig:
    name: str
    hub_id: str
    bridge_id: str
    node_ids: list[str]

class UniversalManifold:
    """
    Universal Manifold (UM) Compiler/Loader:
    Compiles bare topological templates into structured semantic manifolds
    organized as attractor basins with hubs and spokes.
    """
    @staticmethod
    def build_semantic_basin(basin_id: str, num_nodes: int, start_idx: int) -> tuple[list[dict], list[dict], BasinConfig]:
        """
        Builds a single semantic basin with a hub node, spoke nodes, and a bridge node.
        """
        nodes = []
        edges = []
        node_ids = []
        
        hub_id = f"S{start_idx}"
        bridge_id = f"S{start_idx + num_nodes - 1}"
        
        for idx in range(num_nodes):
            node_id = f"S{start_idx + idx}"
            node_ids.append(node_id)
            # Hub node has high semantic mass (capacitance)
            sm = 30.0 if idx == 0 else 1.0
            nodes.append({
                "id": node_id,
                "label": f"Semantic_{basin_id}_{node_id}",
                "group": "semantic",
                "rho": 5.0,
                "psi": -1.0,
                "psi_bias": -1.0,
                "semanticMass": sm,
                "semanticMass0": sm
            })
            
        # Hub to spokes connections
        for idx in range(1, num_nodes):
            spoke_id = f"S{start_idx + idx}"
            edges.append({"from": hub_id, "to": spoke_id, "w0": 1.5})
            
        config = BasinConfig(name=basin_id, hub_id=hub_id, bridge_id=bridge_id, node_ids=node_ids)
        return nodes, edges, config

class SemanticManifold:
    """
    Semantic Manifold Wrapper:
    Maintains the state and configuration of memory attractor basins (RAM/ROM).
    """
    def __init__(self, nodes: list[dict], edges: list[dict], basins: list[BasinConfig]):
        self.nodes = nodes
        self.edges = edges
        self.basins = {b.name: b for b in basins}

class ProcessingManifold:
    """
    Processing Manifold Wrapper:
    Maintains the nodes, registers, gates, and summing core of the blank processing unit.
    """
    def __init__(self):
        self.nodes = []
        self.edges = []
        
        # Register A (Host + Battery)
        self.nodes.extend([
            {"id": "S_RA", "label": "RegisterA_Host", "group": "processing", "rho": 5.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
            {"id": "S_RA_B", "label": "RegisterA_Battery", "group": "processing", "rho": 0.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
        ])
        self.edges.append({"from": "S_RA", "to": "S_RA_B", "w0": 20.0})

        # Register B (Host + Battery)
        self.nodes.extend([
            {"id": "S_RB", "label": "RegisterB_Host", "group": "processing", "rho": 5.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
            {"id": "S_RB_B", "label": "RegisterB_Battery", "group": "processing", "rho": 0.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
        ])
        self.edges.append({"from": "S_RB", "to": "S_RB_B", "w0": 20.0})

        # Register C (Host + Battery)
        self.nodes.extend([
            {"id": "S_RC", "label": "RegisterC_Host", "group": "processing", "rho": 5.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
            {"id": "S_RC_B", "label": "RegisterC_Battery", "group": "processing", "rho": 0.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
        ])
        self.edges.append({"from": "S_RC", "to": "S_RC_B", "w0": 20.0})

        # Register D (Host + Battery)
        self.nodes.extend([
            {"id": "S_RD", "label": "RegisterD_Host", "group": "processing", "rho": 5.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
            {"id": "S_RD_B", "label": "RegisterD_Battery", "group": "processing", "rho": 0.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
        ])
        self.edges.append({"from": "S_RD", "to": "S_RD_B", "w0": 20.0})

        # ALU Routing Gates (controlled by psi_bias)
        self.nodes.extend([
            {"id": "GATE_A", "label": "Gate_A", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0},
            {"id": "GATE_B", "label": "Gate_B", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0},
            {"id": "GATE_C", "label": "Gate_C", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0},
            {"id": "GATE_D", "label": "Gate_D", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0}
        ])

        # Summing Core Node
        self.nodes.append(
            {"id": "P_Sum", "label": "Proc_SummingJunction", "group": "processing", "rho": 0.0, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0}
        )

        # Internal ALU Edges
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

class ManifoldGroup:
    """
    Manifold Group Orchestrator:
    Combines SemanticManifold and ProcessingManifold into a unified substrate.
    Instantiates and manages the SOLEngine instance and gated wormhole connections.
    """
    def __init__(self, semantic: SemanticManifold, processing: ProcessingManifold, c_press: float = 1.0, damping: float = 0.01):
        self.semantic = semantic
        self.processing = processing
        
        # Merge nodes and edges
        self.raw_nodes = []
        self.raw_nodes.extend(semantic.nodes)
        self.raw_nodes.extend(processing.nodes)
        
        self.raw_edges = []
        self.raw_edges.extend(semantic.edges)
        self.raw_edges.extend(processing.edges)
        
        # Add gated wormholes linking Semantic bridges to P_Sum dynamically
        for b_name, b_cfg in semantic.basins.items():
            # Robust input/output basin classification (inputs: Basin_A/B/Cin; outputs: Basin_C/SUM/CARRY/Cout)
            is_input = b_name in ("Basin_A", "Basin_B", "Basin_Cin") or b_name.endswith("A") or b_name.endswith("B") or "in" in b_name.lower()
            if is_input:
                self.raw_edges.append({
                    "from": b_cfg.bridge_id, "to": "P_Sum",
                    "w0": 0.0001, "kind": "wormhole", "background": False
                })
            else:
                self.raw_edges.append({
                    "from": "P_Sum", "to": b_cfg.bridge_id,
                    "w0": 0.0001, "kind": "wormhole", "background": False
                })
        
        # Build engine
        self.engine = SOLEngine.from_graph(self.raw_nodes, self.raw_edges, c_press=c_press, damping=damping)
        self.engine.integration_mode = "rk4"
        
        # Set physical parameters matching physical ALU guidelines
        self.engine.physics.conductance_max = 200.0
        self.engine.physics.conductance_min = 1e-7
        self.engine.physics.conductance_gamma = 8.0
        self.engine.physics.psi_diffusion = 1.2
        self.engine.physics.psi_relax_base = 8.0
        self.engine.physics.psi_global_nudge = 0.0
        
        # Apply battery configuration (avalanche gain memory cells)
        self.engine.physics.battery_cfg = {
            "qMax": 80.0,
            "qThresh": 5.0,
            "leakLambda": 0.01,
            "avalancheGain": 5.0,
            "resonanceBoost": 4.0,
            "dampingClamp": 0.1,
            "flipThreshold": 0.65,
            "collapseFactor": 0.10,
            "resonanceDrive": 50.0,
            "dampingDrag": 0.3,
            "diodeResonanceOut": 1.0,
            "diodeResonanceIn": 1.0,
            "diodeDampingOut": 1.0,
            "diodeDampingIn": 1.0
        }
        
    def step(self, dt: float = 0.05, damping: float = 0.01):
        self.engine.step(dt=dt, damping=damping)
        
    def get_node(self, node_id: str) -> dict:
        return self.engine.physics.node_by_id[node_id]
        
    def get_edge(self, from_id: str, to_id: str) -> dict:
        return next(e for e in self.engine.physics.edges if e["from"] == from_id and e["to"] == to_id)
        
    def set_edge_connection(self, from_id: str, to_id: str, connected: bool):
        edge = self.get_edge(from_id, to_id)
        if connected:
            edge["from_idx"] = self.engine.physics.node_index_by_id[from_id]
            edge["to_idx"] = self.engine.physics.node_index_by_id[to_id]
        else:
            edge["from_idx"] = None
            edge["to_idx"] = None
        
    def prime_basin(self, name: str, active: bool):
        """Primes a semantic basin with either active (1.0) or collapsed (-1.0) belief and baseline mass."""
        basin = self.semantic.basins[name]
        state = 1.0 if active else -1.0
        for nid in basin.node_ids:
            node = self.get_node(nid)
            node["psi"] = state
            node["psi_bias"] = state
            if active and nid == basin.hub_id:
                node["rho"] = 60.0
            else:
                node["rho"] = 5.0

    def prime_register(self, name: str, active: bool):
        """Primes an ALU register with active or collapsed state."""
        host = self.get_node(f"S_R{name}")
        bat = self.get_node(f"S_R{name}_B")
        if active:
            bat["b_state"] = 1
            bat["b_charge"] = 1.0
            bat["psi"] = 1.0
            bat["psi_bias"] = 1.0
            host["psi"] = 1.0
            host["psi_bias"] = 1.0
            host["rho"] = 40.0
            bat["rho"] = 20.0
        else:
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = -1.0
            host["rho"] = 5.0
            bat["rho"] = 0.0

@dataclass
class Instruction:
    op: str  # 'LOAD', 'STORE', 'OR', 'AND', 'COPY', 'CLEAR', 'RESET_CORE'
    args: list[Any] = field(default_factory=list)

class MicroInstructionSequencer:
    """
    Micro-Instruction Sequencer:
    Takes a program (list of Instruction objects) and executes it step-by-step
    by controlling routing gates, wormholes, and biases of the ManifoldGroup.
    """
    def __init__(self, group: ManifoldGroup, dt: float = 0.05):
        self.group = group
        self.dt = dt
        self.history = []
        
    def set_wormhole_connections(self, active_basin_name: Optional[str] = None, is_load: bool = True):
        for b_name, b_cfg in self.group.semantic.basins.items():
            # Robust input/output basin classification (inputs: Basin_A/B/Cin; outputs: Basin_C/SUM/CARRY/Cout)
            is_input = b_name in ("Basin_A", "Basin_B", "Basin_Cin") or b_name.endswith("A") or b_name.endswith("B") or "in" in b_name.lower()
            if is_input: # input basin
                conn = (is_load and b_name == active_basin_name)
                self.group.set_edge_connection(b_cfg.bridge_id, "P_Sum", conn)
            else: # output basin
                conn = (not is_load and b_name == active_basin_name)
                self.group.set_edge_connection("P_Sum", b_cfg.bridge_id, conn)
        
    def apply_holding_biases_processing(self):
        for name in ["S_RA", "S_RB", "S_RC", "S_RD"]:
            if name + "_B" in self.group.engine.physics.node_by_id:
                state = self.group.get_node(name + "_B")["b_state"]
                self.group.get_node(name)["psi_bias"] = 1.0 if state == 1 else -1.0

    def apply_holding_biases_semantic(self):
        # Keeps spokes aligned with hub belief to prevent dilution drag
        for name, basin in self.group.semantic.basins.items():
            hub = self.group.get_node(basin.hub_id)
            state = 1.0 if hub["psi"] >= 0 else -1.0
            for nid in basin.node_ids:
                self.group.get_node(nid)["psi_bias"] = state

    def configure_alu_output_routing(self, active_dest: Optional[str], default_w0: float = 0.0001):
        for r in ['C', 'D']:
            try:
                conn = (r == active_dest or active_dest is None)
                self.group.set_edge_connection("P_Sum", f"GATE_{r}", conn)
                edge = self.group.get_edge("P_Sum", f"GATE_{r}")
                edge["w0"] = 5.0 if r == active_dest else default_w0
            except StopIteration:
                pass

    def normalize_register_masses(self):
        """Locks register masses back to nominal levels (DRAM voltage regulator)."""
        for name in ["S_RA", "S_RB"]:
            bat = self.group.get_node(name + "_B")
            host = self.group.get_node(name)
            if bat["b_state"] == 1:
                host["rho"] = 40.0
                bat["rho"] = 20.0
            else:
                host["rho"] = 5.0
                bat["rho"] = 0.0

    def execute_instruction(self, inst: Instruction):
        """Runs the step sequence for a single instruction."""
        op = inst.op.upper()
        
        # Determine target and register names safely
        if op == "LOAD":
            reg, basin_name = inst.args[0], inst.args[1]
            gate_name = f"GATE_{reg}"
            target_reg = f"S_R{reg}"
            bridge_id = self.group.semantic.basins[basin_name].bridge_id
            
            # Phase 1: Open gate and load (40 steps)
            for _ in range(40):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if reg == r else -1.0
                
                self.configure_alu_output_routing(reg)
                
                # Dynamic wormhole connection
                self.set_wormhole_connections(basin_name, is_load=True)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 15.0 if b_name == basin_name else 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                
                # Drive bridge belief to transfer value
                hub_val = self.group.get_node(self.group.semantic.basins[basin_name].hub_id)["psi"]
                bridge_bias = 1.0 if hub_val >= 0 else -1.0
                self.group.get_node(bridge_id)["psi_bias"] = bridge_bias
                
                # Maintain non-target registers holding states
                self.apply_holding_biases_processing()
                self.group.get_node(target_reg)["psi_bias"] = bridge_bias
                
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()
                
            # Phase 2: Close gate (15 steps)
            for _ in range(15):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "STORE":
            reg, basin_name = inst.args[0], inst.args[1]  # Expected 'C', 'Basin_C'
            bridge_id = self.group.semantic.basins[basin_name].bridge_id
            
            # Phase 1: Open write gate and store (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if reg == r else -1.0
                
                self.configure_alu_output_routing(reg)
                self.set_wormhole_connections(basin_name, is_load=False)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 15.0 if b_name == basin_name else 0.0001
                    except StopIteration:
                        pass
                
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                
                reg_state = self.group.get_node(f"S_R{reg}_B")["b_state"]
                state_val = 1.0 if reg_state == 1 else -1.0
                self.group.get_node(f"S_R{reg}")["psi_bias"] = state_val
                for nid in self.group.semantic.basins[basin_name].node_ids:
                    self.group.get_node(nid)["psi_bias"] = state_val
                
                self.group.step(dt=self.dt)
                self.record_telemetry()
                
            # Phase 2: Close gate and hold (20 steps)
            for _ in range(20):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=False)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op in ("OR", "AND", "OR_MS", "AND_MS", "NOT", "NAND", "NOR", "XOR", "XNOR"):
            # Determine destination register (defaults to 'C')
            dest = inst.args[0] if len(inst.args) > 0 else 'C'
            dest_reg = f"S_R{dest}"
            dest_gate = f"GATE_{dest}"
            
            # Determine if we are doing physical threshold logic or mixed-signal logic
            is_mixed_signal = op in ("OR_MS", "AND_MS", "NOT", "NAND", "NOR", "XOR", "XNOR")
            
            if is_mixed_signal:
                # Read register states from memristive batteries A and B
                latched_A = self.group.get_node("S_RA_B")["b_state"] == 1
                latched_B = self.group.get_node("S_RB_B")["b_state"] == 1
                
                if op == "AND_MS":
                    should_trigger = latched_A and latched_B
                elif op == "OR_MS":
                    should_trigger = latched_A or latched_B
                elif op == "NOT":
                    src = inst.args[1] if len(inst.args) > 1 else 'A'
                    val = latched_A if src == 'A' else latched_B
                    should_trigger = not val
                elif op == "NAND":
                    should_trigger = not (latched_A and latched_B)
                elif op == "NOR":
                    should_trigger = not (latched_A or latched_B)
                elif op == "XOR":
                    should_trigger = latched_A != latched_B
                elif op == "XNOR":
                    should_trigger = latched_A == latched_B
                
                # Mixed-signal compute: drive accumulator dest directly based on should_trigger
                duration = 30
                for _ in range(duration):
                    for r in ['A', 'B', 'C', 'D']:
                        g_id = f"GATE_{r}"
                        if g_id in self.group.engine.physics.node_by_id:
                            self.group.get_node(g_id)["psi_bias"] = 1.0 if r == dest else -1.0
                    self.configure_alu_output_routing(dest)
                    self.set_wormhole_connections(None, is_load=True)
                    for b_name, b_cfg in self.group.semantic.basins.items():
                        try:
                            self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                        except StopIteration:
                            pass
                        try:
                            self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                        except StopIteration:
                            pass
                    
                    self.apply_holding_biases_processing()
                    self.apply_holding_biases_semantic()
                    
                    state_dest = 1.0 if should_trigger else -1.0
                    self.group.get_node(dest_reg)["psi_bias"] = state_dest
                    self.group.get_node(dest_reg)["psi"] = state_dest
                    
                    self.group.step(dt=self.dt)
                    self.record_telemetry()
            else:
                # Purely physical threshold logic for OR / AND
                bias_val = 0.18 if op == "OR" else 0.19
                duration = 30 if op == "OR" else 29
                
                # Phase 1: Open ALU Gates and Compute
                for _ in range(duration):
                    for r in ['A', 'B', 'C', 'D']:
                        g_id = f"GATE_{r}"
                        if g_id in self.group.engine.physics.node_by_id:
                            self.group.get_node(g_id)["psi_bias"] = 1.0 if r in ('A', 'B', dest) else -1.0
                    self.configure_alu_output_routing(dest)
                    self.set_wormhole_connections(None, is_load=True)
                    for b_name, b_cfg in self.group.semantic.basins.items():
                        try:
                            self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                        except StopIteration:
                            pass
                        try:
                            self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                        except StopIteration:
                            pass
                    
                    self.apply_holding_biases_processing()
                    self.apply_holding_biases_semantic()
                    self.group.get_node(dest_reg)["psi_bias"] = bias_val
                    
                    self.group.step(dt=self.dt)
                    self.record_telemetry()
            
            # Common Phase 2: Close Gates and Settle (25 steps)
            for _ in range(25):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(dest)
                self.set_wormhole_connections(None, is_load=True)
                self.apply_holding_biases_processing()
                if not is_mixed_signal:
                    self.group.get_node(dest_reg)["psi_bias"] = bias_val
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "COPY":
            src, dest = inst.args[0], inst.args[1]  # Expect 'C', 'A'
            src_reg = f"S_R{src}"
            src_reg_b = f"S_R{src}_B"
            dest_reg = f"S_R{dest}"
            
            # Phase 1: Route through Summing Junction (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if (r == src or r == dest) else -1.0
                self.configure_alu_output_routing(dest if dest in ('C', 'D') else (src if src in ('C', 'D') else None))
                self.set_wormhole_connections(None, is_load=True)
                
                c_state = self.group.get_node(src_reg_b)["b_state"]
                self.group.get_node(src_reg)["psi_bias"] = 1.0 if c_state == 1 else -1.0
                # Destination bias dynamic assist
                self.group.get_node(dest_reg)["psi_bias"] = 0.5 if c_state == 1 else -1.0
                
                # Keep other registers holding
                for r in ['A', 'B', 'C', 'D']:
                    if r != src and r != dest:
                        other_reg = f"S_R{r}"
                        if other_reg + "_B" in self.group.engine.physics.node_by_id:
                            other_state = self.group.get_node(other_reg + "_B")["b_state"]
                            self.group.get_node(other_reg)["psi_bias"] = 1.0 if other_state == 1 else -1.0
                
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()
                
            # Phase 2: Close Gates and Hold (15 steps)
            for _ in range(15):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "CLEAR":
            reg = inst.args[0]  # Expect 'C'
            reg_host = f"S_R{reg}"
            reg_bat = f"S_R{reg}_B"
            
            # Phase 1: Collapse Battery (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)
                
                # Maintain other registers
                self.apply_holding_biases_processing()
                
                # Actively discharge charge and force bias negative
                self.group.get_node(reg_bat)["b_charge"] = 0.0
                self.group.get_node(reg_bat)["psi_bias"] = -1.0
                self.group.get_node(reg_bat)["psi"] = -1.0
                self.group.get_node(reg_bat)["b_state"] = -1
                self.group.get_node(reg_host)["psi_bias"] = -1.0
                self.group.get_node(reg_host)["psi"] = -1.0
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "RESET_CORE":
            # Ground summing junction and clear fluxes (20 steps)
            for _ in range(20):
                # Programmatic ground on tick 1
                self.set_wormhole_connections(None, is_load=True)
                self.configure_alu_output_routing(None, default_w0=5.0)
                for node_id in ["GATE_A", "GATE_B", "GATE_C", "GATE_D", "P_Sum", "S_RC", "S_RC_B", "S_RD", "S_RD_B"]:
                    if node_id not in self.group.engine.physics.node_by_id:
                        continue
                    node = self.group.get_node(node_id)
                    node["psi"] = -1.0 if node_id != "P_Sum" else 0.0
                    if node_id in ("S_RC", "S_RD"):
                        node["rho"] = 5.0
                    elif node_id in ("S_RC_B", "S_RD_B"):
                        node["rho"] = 0.0
                        node["b_state"] = -1
                        node["b_charge"] = 0.0
                        node["psi_bias"] = -1.0
                    else:
                        node["rho"] = 0.0
                for edge in self.group.engine.physics.edges:
                    edge["flux"] = 0.0
                
                # DRAM mass regulation normalization
                self.normalize_register_masses()
                
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

    def record_telemetry(self):
        bat_a = self.group.get_node("S_RA_B")
        bat_b = self.group.get_node("S_RB_B")
        bat_c = self.group.get_node("S_RC_B")
        bat_d = self.group.get_node("S_RD_B") if "S_RD_B" in self.group.engine.physics.node_by_id else None
        
        rho_basin_a = sum(self.group.get_node(f"S{i}")["rho"] for i in range(10) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_b = sum(self.group.get_node(f"S{i}")["rho"] for i in range(10, 20) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_c = sum(self.group.get_node(f"S{i}")["rho"] for i in range(20, 30) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_d = sum(self.group.get_node(f"S{i}")["rho"] for i in range(30, 40) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_e = sum(self.group.get_node(f"S{i}")["rho"] for i in range(40, 50) if f"S{i}" in self.group.engine.physics.node_by_id)
        
        rho_reg_a = self.group.get_node("S_RA")["rho"] + bat_a["rho"]
        rho_reg_b = self.group.get_node("S_RB")["rho"] + bat_b["rho"]
        rho_reg_c = self.group.get_node("S_RC")["rho"] + bat_c["rho"]
        rho_reg_d = (self.group.get_node("S_RD")["rho"] + bat_d["rho"]) if bat_d else 0.0
        
        # Determine basin states safely
        b_a_state = 1 if (f"S0" in self.group.engine.physics.node_by_id and self.group.get_node("S0")["psi"] >= 0) else 0
        b_b_state = 1 if (f"S10" in self.group.engine.physics.node_by_id and self.group.get_node("S10")["psi"] >= 0) else 0
        b_c_state = 1 if (f"S20" in self.group.engine.physics.node_by_id and self.group.get_node("S20")["psi"] >= 0) else 0
        b_d_state = 1 if (f"S30" in self.group.engine.physics.node_by_id and self.group.get_node("S30")["psi"] >= 0) else 0
        b_e_state = 1 if (f"S40" in self.group.engine.physics.node_by_id and self.group.get_node("S40")["psi"] >= 0) else 0
        
        self.history.append({
            "step": len(self.history),
            "basin_a_state": b_a_state,
            "basin_b_state": b_b_state,
            "basin_c_state": b_c_state,
            "basin_d_state": b_d_state,
            "basin_e_state": b_e_state,
            "reg_a_state": float(bat_a["b_state"]),
            "reg_b_state": float(bat_b["b_state"]),
            "reg_c_state": float(bat_c["b_state"]),
            "reg_d_state": float(bat_d["b_state"]) if bat_d else 0.0,
            "rho_basin_a": rho_basin_a,
            "rho_basin_b": rho_basin_b,
            "rho_basin_c": rho_basin_c,
            "rho_basin_d": rho_basin_d,
            "rho_basin_e": rho_basin_e,
            "rho_reg_a": rho_reg_a,
            "rho_reg_b": rho_reg_b,
            "rho_reg_c": rho_reg_c,
            "rho_reg_d": rho_reg_d,
            "psi_sum": self.group.get_node("P_Sum")["psi"]
        })

    def run_program(self, program: list[Instruction]) -> list[dict]:
        self.history = []
        for inst in program:
            self.execute_instruction(inst)
        return self.history
