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

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add sol-core path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Force bind telemetry to prevent collisions
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
    battery_id: str | None = None

class UniversalManifold:
    """
    Universal Manifold (UM) Compiler/Loader:
    Compiles bare topological templates into structured semantic manifolds
    organized as attractor basins with hubs and spokes.
    """
    @staticmethod
    def build_semantic_basin(
        basin_id: str,
        num_nodes: int,
        start_idx: int,
        pure_wave: bool = False,
    ) -> tuple[list[dict], list[dict], BasinConfig]:
        """
        Builds a single semantic basin with a hub node, spoke nodes, and a bridge node.
        When pure_wave=True, attaches an internal phase-locked memory battery pocket so
        the basin sustains and transfers continuous wave states without Python holding biases.
        """
        nodes = []
        edges = []
        node_ids = []
        
        hub_id = f"S{start_idx}"
        bridge_id = f"S{start_idx + num_nodes - 1}"
        battery_id = f"S{start_idx}_B" if pure_wave else None
        
        for idx in range(num_nodes):
            node_id = f"S{start_idx + idx}"
            node_ids.append(node_id)
            # Hub node has high semantic mass (capacitance)
            sm = 30.0 if idx == 0 else 1.0
            init_bias = 0.0 if pure_wave else -1.0
            nodes.append({
                "id": node_id,
                "label": f"Semantic_{basin_id}_{node_id}",
                "group": "semantic",
                "rho": 5.0,
                "psi": -1.0,
                "psi_bias": init_bias,
                "semanticMass": sm,
                "semanticMass0": sm
            })
            
        # Hub to spokes connections
        for idx in range(1, num_nodes):
            spoke_id = f"S{start_idx + idx}"
            edges.append({"from": hub_id, "to": spoke_id, "w0": 1.5})

        if pure_wave and battery_id is not None:
            nodes.append({
                "id": battery_id,
                "label": f"Semantic_{basin_id}_Battery",
                "group": "semantic",
                "rho": 0.0,
                "isBattery": True,
                "b_state": -1,
                "b_charge": 0.0,
                "psi": -1.0,
                "psi_bias": -1.0,
                "semanticMass": 20.0,
                "semanticMass0": 20.0,
            })
            # 2 internal battery filaments hold hub strongly against spokes while remaining overwritable by 6 store filaments
            for k in range(2):
                edges.append({"from": hub_id, "to": battery_id, "w0": 10.0, "role": f"basin_bat_{basin_id}_{k}"})
            # 5 internal hub <-> bridge filaments for lossless pure-wave LOAD/STORE within RK4 stability bound
            for k in range(5):
                edges.append({"from": hub_id, "to": bridge_id, "w0": 3.0, "role": f"basin_bridge_{basin_id}_{k}"})
            
        config = BasinConfig(
            name=basin_id,
            hub_id=hub_id,
            bridge_id=bridge_id,
            node_ids=node_ids,
            battery_id=battery_id,
        )
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
    When pure_wave=True, provisions continuous acoustic-phase wave interference cavities
    (threshold resonator, anti-phase destructive inverter, two-source destructive XOR
    cavity, and phase-transistor CMOVE coupler) eliminating all Python boolean shortcuts.
    """
    def __init__(self, pure_wave: bool = False):
        self.pure_wave = pure_wave
        self.nodes = []
        self.edges = []
        init_host_bias = 0.0 if pure_wave else -1.0
        
        for r in ("A", "B", "C", "D"):
            self.nodes.extend([
                {
                    "id": f"S_R{r}",
                    "label": f"Register{r}_Host",
                    "group": "processing",
                    "rho": 5.0,
                    "psi": -1.0,
                    "psi_bias": init_host_bias,
                    "semanticMass": 20.0,
                    "semanticMass0": 20.0,
                },
                {
                    "id": f"S_R{r}_B",
                    "label": f"Register{r}_Battery",
                    "group": "processing",
                    "rho": 0.0,
                    "isBattery": True,
                    "b_state": -1,
                    "b_charge": 0.0,
                    "psi": -1.0,
                    "psi_bias": -1.0,
                    "semanticMass": 20.0,
                    "semanticMass0": 20.0,
                },
            ])
            if pure_wave:
                # 2 internal battery filaments hold S_R{r} strongly during read while remaining overwritable by 5 write filaments
                for k in range(2):
                    self.edges.append({"from": f"S_R{r}", "to": f"S_R{r}_B", "w0": 10.0, "role": f"reg_bat_{r}"})
            else:
                self.edges.append({"from": f"S_R{r}", "to": f"S_R{r}_B", "w0": 20.0})

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

        if not pure_wave:
            # Legacy Internal ALU Edges
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
        else:
            # Symmetric Pure-Wave Register <-> Gate <-> P_Sum Filaments
            for r in ("A", "B", "C", "D"):
                # Gate sense path (1 filament each: minimal back-action on S_R{r} which has 2 battery filaments)
                self.edges.append({
                    "from": f"S_R{r}", "to": f"GATE_{r}",
                    "w0": 6.0, "kind": "wormhole", "background": False, "role": f"pw_reg_read_{r}",
                })
                self.edges.append({
                    "from": f"GATE_{r}", "to": "P_Sum",
                    "w0": 6.0, "kind": "wormhole", "background": False, "role": f"pw_bus_in_{r}",
                })
                # Direct Battery-Coupled Read Repeater for lossless COPY/STORE/Gate Superposition (6 filaments out of S_R{r}_B)
                for k in range(6):
                    self.edges.append({
                        "from": f"S_R{r}_B", "to": "P_Sum",
                        "w0": 1.0, "kind": "wormhole", "background": True, "role": f"pw_bat_drive_sum_{r}",
                    })
                # Direct 1-hop P_Sum -> S_R{r} write path for lossless pure-wave LOAD/COPY (6 filaments overcome 2 reg_bat filaments)
                for k in range(6):
                    self.edges.append({
                        "from": "P_Sum", "to": f"S_R{r}",
                        "w0": 3.0, "kind": "wormhole", "background": False, "role": f"pw_sum_write_{r}",
                    })
                # Write path from GATE_{r} -> S_R{r} for Phase Phi_2 Cavity-to-Register commit (5 filaments)
                for k in range(5):
                    self.edges.append({
                        "from": "P_Sum", "to": f"GATE_{r}",
                        "w0": 2.0, "kind": "wormhole", "background": False, "role": f"pw_bus_out_{r}",
                    })
                    self.edges.append({
                        "from": f"GATE_{r}", "to": f"S_R{r}",
                        "w0": 2.0, "kind": "wormhole", "background": False, "role": f"pw_reg_write_{r}",
                    })

            # Pure Wave-Interference Logic Cavities (acoustic-to-phase symmetry breaking)
            self.nodes.extend([
                # Neutral-phase (psi=0.0) continuous acoustic pressure pump (zero phase back-leakage!)
                {
                    "id": "P_Wave_Ref",
                    "label": "Wave_Carrier_Pump",
                    "group": "processing",
                    "rho": 500.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 0.5,
                    "semanticMass0": 0.5,
                },
                # Excitatory / Inhibitory GRMN Reset-Gated Waveguides (native SOLPhysics W_r, U_r, b_r)
                {
                    "id": "P_Excite_Gate",
                    "label": "Wave_Excite_Transistor",
                    "group": "processing",
                    "rho": 120.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                    "W_r": 0.0,
                    "U_r": 120.0,
                    "b_r": 0.0,
                },
                {
                    "id": "P_Quench_Gate",
                    "label": "Wave_Destructive_Quench_Transistor",
                    "group": "processing",
                    "rho": 120.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                    "W_r": 0.0,
                    "U_r": -120.0,
                    "b_r": 0.0,
                },
                # Dual Acoustic-to-Phase Transduction Cavities, Anti-Phase Sink, & Cavity Phase-Lock Resonator
                # Separating Excite and Quench into isolated cavities prevents an OFF gate (r_gate=0) from back-draining an ON branch
                {
                    "id": "P_Wave_Cavity",
                    "label": "Wave_Resonance_Cavity_1",
                    "group": "processing",
                    "rho": 0.0,
                    "psi": -0.4,
                    "psi_bias": 1.85,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                },
                {
                    "id": "P_Wave_Cavity_2",
                    "label": "Wave_Resonance_Cavity_2",
                    "group": "processing",
                    "rho": 0.0,
                    "psi": -0.4,
                    "psi_bias": 1.85,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                },
                {
                    "id": "P_Wave_Sink",
                    "label": "Wave_AntiPhase_Anchor",
                    "group": "processing",
                    "rho": 5.0,
                    "isBattery": True,
                    "b_state": -1,
                    "b_charge": 0.0,
                    "psi": -1.0,
                    "psi_bias": -1.0,
                    "semanticMass": 20.0,
                    "semanticMass0": 20.0,
                },
                {
                    "id": "P_Wave_Out_B",
                    "label": "Wave_Cavity_PhaseLock",
                    "group": "processing",
                    "rho": 0.0,
                    "isBattery": True,
                    "b_state": -1,
                    "b_charge": 0.0,
                    "psi": -1.0,
                    "psi_bias": -1.0,
                    "semanticMass": 10.0,
                    "semanticMass0": 10.0,
                },
                # Conditional Wave-Transistor Gate for pure-wave CMOVE
                {
                    "id": "P_CMove_Gate",
                    "label": "Wave_CMove_Transistor",
                    "group": "processing",
                    "rho": 0.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                    "W_r": 0.0,
                    "U_r": 120.0,
                    "b_r": 0.0,
                },
            ])
            # High-conductance acoustic carrier waveguides (w0=15000 saturates conductance_max=200 even at negative phase so r_gate governs cleanly)
            self.edges.extend([
                {"from": "P_Wave_Ref", "to": "P_Excite_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_ref_to_excite"},
                {"from": "P_Wave_Ref", "to": "P_Quench_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_ref_to_quench"},
                {"from": "P_Excite_Gate", "to": "P_Quench_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_excite_to_quench"},
                {"from": "P_Excite_Gate", "to": "P_Wave_Cavity", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_excite_to_cavity"},
                {"from": "P_Quench_Gate", "to": "P_Wave_Cavity", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_quench_to_cavity"},
                {"from": "P_Quench_Gate", "to": "P_Wave_Cavity_2", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_quench_to_cavity2"},
                {"from": "P_Wave_Ref", "to": "P_CMove_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_ref_to_cmove"},
                {"from": "P_CMove_Gate", "to": "P_Quench_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_cmove_to_quench"},
                {"from": "P_Wave_Cavity", "to": "P_Wave_Out_B", "w0": 80.0, "kind": "wormhole", "background": False, "role": "pw_cavity_to_out_b"},
                {"from": "P_Wave_Cavity_2", "to": "P_Wave_Out_B", "w0": 80.0, "kind": "wormhole", "background": False, "role": "pw_cavity2_to_out_b"},
            ])
            # 5 phase-sensing filaments from P_Sum into Excite / Quench gates (yields wide margin within RK4 stability bound)
            for k in range(5):
                self.edges.append({
                    "from": "P_Sum", "to": "P_Excite_Gate",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_sum_sense_excite",
                })
                self.edges.append({
                    "from": "P_Sum", "to": "P_Quench_Gate",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_sum_sense_quench",
                })
            # Dual anti-phase anchor filaments + P_Wave_Out_B keep OFF cavities strictly negative (psi < -0.10) even under +0.75 gate pull
            for k in range(2):
                self.edges.append({
                    "from": "P_Wave_Cavity", "to": "P_Wave_Sink",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_cavity_sink",
                })
                self.edges.append({
                    "from": "P_Wave_Cavity_2", "to": "P_Wave_Sink",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_cavity2_sink",
                })
            # High-fanout phase waveguides from P_Wave_Out_B -> GATE_{r} (6 background phase filaments: zero drain on cavity!)
            for r in ("A", "B", "C", "D"):
                for k in range(6):
                    self.edges.append({
                        "from": "P_Wave_Out_B", "to": f"GATE_{r}",
                        "w0": 1.0, "kind": "wormhole", "background": True, "role": f"pw_cavity_to_gate_{r}",
                    })
                # CMOVE phase-sense bundles: dest -> P_CMove_Gate and cond -> P_Quench_Gate (5 filaments each)
                for k in range(5):
                    self.edges.append({
                        "from": f"S_R{r}_B", "to": "P_CMove_Gate",
                        "w0": 0.0001, "kind": "wormhole", "background": True, "role": f"pw_cmove_dest_{r}",
                    })
                    self.edges.append({
                        "from": f"S_R{r}_B", "to": "P_Quench_Gate",
                        "w0": 0.0001, "kind": "wormhole", "background": True, "role": f"pw_cmove_cond_{r}",
                    })

class ManifoldGroup:
    """
    Manifold Group Orchestrator:
    Combines SemanticManifold and ProcessingManifold into a unified substrate.
    Instantiates and manages the SOLEngine instance and gated wormhole connections.
    """
    def __init__(
        self,
        semantic: SemanticManifold,
        processing: ProcessingManifold,
        c_press: float = 1.0,
        damping: float = 0.01,
        pure_wave: bool | None = None,
    ):
        self.semantic = semantic
        self.processing = processing
        self.pure_wave = bool(getattr(processing, "pure_wave", False)) if pure_wave is None else bool(pure_wave)

        # Merge nodes and edges
        self.raw_nodes = []
        self.raw_nodes.extend(semantic.nodes)
        self.raw_nodes.extend(processing.nodes)

        self.raw_edges = []
        self.raw_edges.extend(semantic.edges)
        self.raw_edges.extend(processing.edges)

        # Add bidirectional gated wormholes linking ALL Semantic bridges <-> P_Sum dynamically
        # so Basin_Sel, Basin_S, Basin_R, Basin_Q, Basin_Qbar, and Basin_Scratch_* can both LOAD and STORE.
        for b_name, b_cfg in semantic.basins.items():
            if self.pure_wave:
                # 6 phase filaments from basin battery -> P_Sum during LOAD (background=True prevents draining basin battery!)
                src_node = b_cfg.battery_id or b_cfg.bridge_id
                for _ in range(6):
                    self.raw_edges.append({
                        "from": src_node, "to": "P_Sum",
                        "w0": 1.0, "kind": "wormhole", "background": True, "role": f"wh_load_{b_name}",
                    })
                # 8 write filaments from P_Sum -> hub_id during STORE (1-hop waveguide overcomes 2 internal basin battery filaments!)
                for _ in range(8):
                    self.raw_edges.append({
                        "from": "P_Sum", "to": b_cfg.hub_id,
                        "w0": 3.0, "kind": "wormhole", "background": False, "role": f"wh_store_{b_name}",
                    })
            else:
                self.raw_edges.append({
                    "from": b_cfg.bridge_id, "to": "P_Sum",
                    "w0": 0.0001, "kind": "wormhole", "background": False, "role": f"wh_load_{b_name}",
                })
                self.raw_edges.append({
                    "from": "P_Sum", "to": b_cfg.bridge_id,
                    "w0": 0.0001, "kind": "wormhole", "background": False, "role": f"wh_store_{b_name}",
                })

        # Build engine
        self.engine = SOLEngine.from_graph(self.raw_nodes, self.raw_edges, c_press=c_press, damping=damping)
        self.engine.integration_mode = "rk4"

        # Set physical parameters matching physical ALU guidelines (pure_wave D=1.5 keeps lambda_max * dt < 1.8 < 2.785)
        self.engine.physics.conductance_max = 200.0
        self.engine.physics.conductance_min = 1e-7
        self.engine.physics.conductance_gamma = 8.0
        self.engine.physics.psi_diffusion = 1.5 if self.pure_wave else 1.2
        self.engine.physics.psi_relax_base = 4.0 if self.pure_wave else 8.0
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
            "diodeDampingIn": 1.0,
        }

        # Index role-tagged edges for O(1) pure-wave waveguide switching and preserve explicit background flags
        self._edges_by_role: dict[str, list[dict]] = {}
        self._active_dynamic_roles: set[str] = set()
        for idx, e in enumerate(self.engine.physics.edges):
            if idx < len(self.raw_edges) and "background" in self.raw_edges[idx]:
                e["background"] = bool(self.raw_edges[idx]["background"])
                e["_orig_background"] = bool(self.raw_edges[idx]["background"])
            role = e.get("role")
            if role:
                self._edges_by_role.setdefault(role, []).append(e)

        # Disconnect all dynamic wormholes initially
        for role in self._edges_by_role:
            if role.startswith(("wh_", "pw_")):
                self.set_role_connection(role, False)

    def step(self, dt: float = 0.05, damping: float = 0.01):
        self.engine.step(dt=dt, damping=damping)

    def run_steps(
        self,
        steps: int,
        dt: float = 0.05,
        damping: float = 0.01,
        *,
        pre_step_node: dict | None = None,
        pre_step_rho: float = 500.0,
        pre_step_psi: float = 0.0,
    ) -> None:
        self.engine.run_steps(
            steps,
            dt=dt,
            damping=damping,
            pre_step_node=pre_step_node,
            pre_step_rho=pre_step_rho,
            pre_step_psi=pre_step_psi,
        )

    def get_node(self, node_id: str) -> dict:
        return self.engine.physics.node_by_id[node_id]

    def get_edge(self, from_id: str, to_id: str) -> dict:
        return next(e for e in self.engine.physics.edges if e["from"] == from_id and e["to"] == to_id)

    def get_edges(self, from_id: str, to_id: str) -> list[dict]:
        return [e for e in self.engine.physics.edges if e["from"] == from_id and e["to"] == to_id]

    def set_edge_connection(self, from_id: str, to_id: str, connected: bool):
        for edge in self.get_edges(from_id, to_id):
            if connected:
                edge["from_idx"] = self.engine.physics.node_index_by_id[from_id]
                edge["to_idx"] = self.engine.physics.node_index_by_id[to_id]
            else:
                edge["from_idx"] = None
                edge["to_idx"] = None

    def set_role_connection(self, role: str, connected: bool):
        node_idx_map = self.engine.physics.node_index_by_id
        is_dyn = role.startswith(("wh_", "pw_"))
        if connected:
            for edge in self._edges_by_role.get(role, ()):
                edge["from_idx"] = node_idx_map[edge["from"]]
                edge["to_idx"] = node_idx_map[edge["to"]]
                edge["background"] = bool(edge.get("_orig_background", edge.get("background", False)))
            if is_dyn:
                self._active_dynamic_roles.add(role)
        else:
            for edge in self._edges_by_role.get(role, ()):
                edge["from_idx"] = None
                edge["to_idx"] = None
                # Also shield disconnected battery-touching waveguides from update_batteries
                edge["background"] = True
                if is_dyn:
                    edge["flux"] = 0.0
            if is_dyn:
                self._active_dynamic_roles.discard(role)

    def disconnect_all_dynamic_roles(self) -> None:
        if not self._active_dynamic_roles:
            return
        for role in tuple(self._active_dynamic_roles):
            for edge in self._edges_by_role.get(role, ()):
                edge["from_idx"] = None
                edge["to_idx"] = None
                edge["background"] = True
                edge["flux"] = 0.0
        self._active_dynamic_roles.clear()
        
    def prime_basin(self, name: str, active: bool):
        """Primes a semantic basin with either active (1.0) or collapsed (-1.0) belief and baseline mass."""
        basin = self.semantic.basins[name]
        state = 1.0 if active else -1.0
        for nid in basin.node_ids:
            node = self.get_node(nid)
            node["psi"] = state
            node["psi_bias"] = 0.0 if self.pure_wave else state
            if active and nid == basin.hub_id:
                node["rho"] = 60.0
            else:
                node["rho"] = 5.0
        if basin.battery_id and basin.battery_id in self.engine.physics.node_by_id:
            bat = self.get_node(basin.battery_id)
            bat["b_state"] = 1 if active else -1
            bat["b_charge"] = 1.0 if active else 0.0
            bat["psi"] = state
            bat["psi_bias"] = state
            bat["rho"] = 20.0 if active else 0.0

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
            host["psi_bias"] = 0.0 if self.pure_wave else 1.0
            host["rho"] = 40.0
            bat["rho"] = 20.0
        else:
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = 0.0 if self.pure_wave else -1.0
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
    When pure_wave=True, all memory transfers and logic gates execute strictly
    through continuous SOLEngine RK4 acoustic pressure, phase diffusion, and
    wave-interference cavities with zero Python boolean shortcuts on b_state.
    """
    def __init__(
        self,
        group: ManifoldGroup,
        dt: float = 0.05,
        pure_wave: bool | None = None,
        wave_threshold_offset: float = 0.0,
        record_substep_telemetry: bool = True,
    ):
        self.group = group
        self.dt = dt
        self.pure_wave = bool(getattr(group, "pure_wave", False)) if pure_wave is None else bool(pure_wave)
        self.wave_threshold_offset = float(wave_threshold_offset)
        self.record_substep_telemetry = bool(record_substep_telemetry)
        self.history: list[dict[str, Any]] = []
        self.python_boolean_shortcuts_used: int = 0
        self.wave_gate_telemetry: list[dict[str, Any]] = []

        node_by_id = self.group.engine.physics.node_by_id
        zero_bias_nodes: list[dict] = []
        for r in ("A", "B", "C", "D"):
            if f"S_R{r}" in node_by_id:
                zero_bias_nodes.append(node_by_id[f"S_R{r}"])
            if f"GATE_{r}" in node_by_id:
                zero_bias_nodes.append(node_by_id[f"GATE_{r}"])
        for basin in self.group.semantic.basins.values():
            for nid in basin.node_ids:
                if nid in node_by_id:
                    zero_bias_nodes.append(node_by_id[nid])
        self._pw_zero_bias_nodes = zero_bias_nodes
        self._p_sum_node = node_by_id["P_Sum"]
        self._pw_ref_node = node_by_id.get("P_Wave_Ref")
        self._pw_sink_node = node_by_id.get("P_Wave_Sink")
        self._pw_cav_nodes = [node_by_id[cid] for cid in ("P_Wave_Cavity", "P_Wave_Cavity_2") if cid in node_by_id]
        self._pw_out_b_node = node_by_id.get("P_Wave_Out_B")
        self._pw_gate_nodes = [
            node_by_id[gid]
            for gid in ("P_Excite_Gate", "P_Quench_Gate", "P_CMove_Gate")
            if gid in node_by_id
        ]

    def set_wormhole_connections(self, active_basin_name: str | None = None, is_load: bool = True):
        for b_name, b_cfg in self.group.semantic.basins.items():
            load_conn = bool(is_load and b_name == active_basin_name)
            store_conn = bool((not is_load) and b_name == active_basin_name)
            if f"wh_load_{b_name}" in self.group._edges_by_role:
                self.group.set_role_connection(f"wh_load_{b_name}", load_conn)
            else:
                try:
                    self.group.set_edge_connection(b_cfg.bridge_id, "P_Sum", load_conn)
                except StopIteration:
                    pass
            if f"wh_store_{b_name}" in self.group._edges_by_role:
                self.group.set_role_connection(f"wh_store_{b_name}", store_conn)
            else:
                try:
                    self.group.set_edge_connection("P_Sum", b_cfg.bridge_id, store_conn)
                except StopIteration:
                    pass

    def apply_holding_biases_processing(self):
        if self.pure_wave:
            for name in ["S_RA", "S_RB", "S_RC", "S_RD"]:
                if name in self.group.engine.physics.node_by_id:
                    self.group.get_node(name)["psi_bias"] = 0.0
            return
        for name in ["S_RA", "S_RB", "S_RC", "S_RD"]:
            if name + "_B" in self.group.engine.physics.node_by_id:
                state = self.group.get_node(name + "_B")["b_state"]
                self.group.get_node(name)["psi_bias"] = 1.0 if state == 1 else -1.0

    def apply_holding_biases_semantic(self):
        if self.pure_wave:
            for basin in self.group.semantic.basins.values():
                for nid in basin.node_ids:
                    self.group.get_node(nid)["psi_bias"] = 0.0
            return
        # Keeps spokes aligned with hub belief to prevent dilution drag
        for basin in self.group.semantic.basins.values():
            hub = self.group.get_node(basin.hub_id)
            state = 1.0 if hub["psi"] >= 0 else -1.0
            for nid in basin.node_ids:
                self.group.get_node(nid)["psi_bias"] = state

    def configure_alu_output_routing(self, active_dest: str | None, default_w0: float = 0.0001):
        if self.pure_wave:
            return
        for r in ['C', 'D']:
            try:
                conn = (r == active_dest or active_dest is None)
                self.group.set_edge_connection("P_Sum", f"GATE_{r}", conn)
                edge = self.group.get_edge("P_Sum", f"GATE_{r}")
                edge["w0"] = 5.0 if r == active_dest else default_w0
            except StopIteration:
                pass

    def _reset_pure_wave_routes(self):
        """Disconnects all dynamic pure-wave waveguides and resets neutral carrier biases without reading b_state."""
        self.group.disconnect_all_dynamic_roles()
        for n in self._pw_zero_bias_nodes:
            n["psi_bias"] = 0.0
        p_sum = self._p_sum_node
        p_sum["psi_bias"] = 0.0
        p_sum["psi"] = 0.0
        p_sum["rho"] = 0.0
        ref = self._pw_ref_node
        if ref is not None:
            ref["rho"] = 500.0
            ref["psi"] = 0.0
            ref["psi_bias"] = 0.0
        sink = self._pw_sink_node
        if sink is not None:
            sink["isBattery"] = True
            sink["b_state"] = -1
            sink["b_charge"] = 0.0
            sink["rho"] = 5.0
            sink["psi"] = -1.0
            sink["psi_bias"] = -1.0
        for cav in self._pw_cav_nodes:
            cav["rho"] = 0.0
            cav["psi"] = -0.4
            cav["psi_bias"] = 1.85
        out_b = self._pw_out_b_node
        if out_b is not None:
            out_b["b_state"] = -1
            out_b["b_charge"] = 0.0
            out_b["psi"] = -1.0
            out_b["psi_bias"] = -1.0
            out_b["rho"] = 0.0
        for gn in self._pw_gate_nodes:
            gn["rho"] = 0.0
            gn["psi"] = 0.0
            gn["psi_bias"] = 0.0

    def _advance_pure_wave_steps(self, steps: int, *, pump_ref: bool = False) -> None:
        if steps <= 0:
            return
        ref_node = self._pw_ref_node if pump_ref else None
        if self.record_substep_telemetry:
            for _ in range(steps):
                if ref_node is not None:
                    ref_node["rho"] = 500.0
                    ref_node["psi"] = 0.0
                self.group.step(dt=self.dt)
                self.record_telemetry()
        else:
            self.group.run_steps(
                steps,
                dt=self.dt,
                pre_step_node=ref_node,
                pre_step_rho=500.0,
                pre_step_psi=0.0,
            )

    def _settle_pure_wave(self, steps: int = 10):
        self._reset_pure_wave_routes()
        self._advance_pure_wave_steps(steps)
        if steps > 0 and not self.record_substep_telemetry:
            self.record_telemetry()

    def normalize_register_masses(self):
        """Locks register masses back to nominal levels (DRAM voltage regulator)."""
        if self.pure_wave:
            # In pure-wave mode, register batteries self-maintain mass without Python b_state branching
            return
        for name in ["S_RA", "S_RB"]:
            bat = self.group.get_node(name + "_B")
            host = self.group.get_node(name)
            if bat["b_state"] == 1:
                host["rho"] = 40.0
                bat["rho"] = 20.0
            else:
                host["rho"] = 5.0
                bat["rho"] = 0.0

    def _commit_pure_wave_cavity_to_register(self, dest: str, op_label: str, psi_sum_end: float, psi_cav_end: float, rho_cav_end: float):
        """
        Clock Phase Phi_2: Disconnects Stage-1 interference sense waveguides so Master Resonator
        P_Wave_Out_B holds its phase-locked wave eigenstate, and couples P_Wave_Out_B -> GATE_{dest} -> S_R{dest}.
        """
        self.group.disconnect_all_dynamic_roles()

        self.group.set_role_connection(f"pw_cavity_to_gate_{dest}", True)
        self.group.set_role_connection(f"pw_reg_write_{dest}", True)
        self._advance_pure_wave_steps(45)

        dest_bat = self.group.get_node(f"S_R{dest}_B")
        dest_host = self.group.get_node(f"S_R{dest}")
        out_b = self.group.get_node("P_Wave_Out_B")
        tau = float(self.group.engine.physics.battery_cfg.get("flipThreshold", 0.65))

        self.wave_gate_telemetry.append({
            "op": op_label,
            "dest": dest,
            "psi_sum": round(psi_sum_end, 5),
            "psi_cavity": round(psi_cav_end, 5),
            "rho_cavity": round(rho_cav_end, 4),
            "master_out_b_state": int(out_b["b_state"]),
            "dest_b_charge": round(float(dest_bat["b_charge"]), 5),
            "dest_b_state": int(dest_bat["b_state"]),
            "charge_margin_vs_tau": round(abs(float(dest_bat["b_charge"]) - tau), 5),
            "dest_register_mass": round(float(dest_host["rho"] + dest_bat["rho"]), 4),
        })
        self._settle_pure_wave(10)

    def _execute_pure_wave_gate(self, op: str, dest: str, src_a: str = "A", src_b: str = "B"):
        """
        Executes logic gates strictly through 3-phase continuous acoustic-phase wave superposition,
        GRMN wave-transistor quenching, acoustic-to-phase cavity symmetry breaking, and
        master-slave resonator phase locking — ZERO Python boolean evaluation on b_state.
        """
        self._reset_pure_wave_routes()

        # Clock Phase Phi_0 (12 RK4 steps): Pre-settle P_Sum and wave-transistor gate phases
        # before opening acoustic carrier pump P_Wave_Ref so zero t=0 transient mass leaks.
        if op == "NOT_WAVE":
            self.group.set_role_connection(f"pw_bat_drive_sum_{src_a}", True)
        else:
            self.group.set_role_connection(f"pw_bat_drive_sum_{src_a}", True)
            self.group.set_role_connection(f"pw_bat_drive_sum_{src_b}", True)

        excite = self.group.get_node("P_Excite_Gate")
        quench = self.group.get_node("P_Quench_Gate")

        gain = 120.0
        thresh_or = -0.20 + self.wave_threshold_offset
        thresh_and = 0.20 + self.wave_threshold_offset
        thresh_not = 0.00 + self.wave_threshold_offset

        excite["W_r"] = 0.0
        quench["W_r"] = 0.0

        if op in ("OR", "OR_WAVE"):
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_or
            self.group.set_role_connection("pw_sum_sense_excite", True)
        elif op in ("AND", "AND_WAVE"):
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_excite", True)
        elif op == "NOT_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_not
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "NOR_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_or
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "NAND_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "XOR_WAVE":
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_or
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_excite", True)
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "XNOR_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_or
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_excite", True)
            self.group.set_role_connection("pw_sum_sense_quench", True)
        else:
            raise ValueError(f"Unsupported pure-wave gate opcode: {op}")

        self.group.set_role_connection("pw_cavity_sink", True)
        self.group.set_role_connection("pw_cavity_to_out_b", True)
        if op == "XNOR_WAVE":
            self.group.set_role_connection("pw_cavity2_sink", True)
            self.group.set_role_connection("pw_cavity2_to_out_b", True)

        self._advance_pure_wave_steps(12)

        # Clock Phase Phi_1 (45 RK4 steps): Open acoustic carrier pump waveguides
        if op in ("OR", "OR_WAVE", "AND", "AND_WAVE"):
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_excite_to_cavity", True)
        elif op in ("NOT_WAVE", "NOR_WAVE", "NAND_WAVE"):
            self.group.set_role_connection("pw_ref_to_quench", True)
            self.group.set_role_connection("pw_quench_to_cavity", True)
        elif op == "XOR_WAVE":
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_excite_to_quench", True)
            self.group.set_role_connection("pw_quench_to_cavity", True)
        elif op == "XNOR_WAVE":
            self.group.set_role_connection("pw_ref_to_quench", True)
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_quench_to_cavity2", True)
            self.group.set_role_connection("pw_excite_to_cavity", True)

        self._advance_pure_wave_steps(45, pump_ref=True)

        psi_sum_end = float(self.group.get_node("P_Sum")["psi"])
        cav1 = self.group.get_node("P_Wave_Cavity")
        cav2 = self.group.get_node("P_Wave_Cavity_2")
        psi_cav_end = float(max(cav1["psi"], cav2["psi"])) if op == "XNOR_WAVE" else float(cav1["psi"])
        rho_cav_end = float(cav1["rho"] + cav2["rho"]) if op == "XNOR_WAVE" else float(cav1["rho"])

        # Clock Phase Phi_2: Commit Master Resonator P_Wave_Out_B to destination register
        self._commit_pure_wave_cavity_to_register(dest, op, psi_sum_end, psi_cav_end, rho_cav_end)

    def execute_instruction(self, inst: Instruction):
        """Runs the step sequence for a single instruction."""
        op = inst.op.upper()

        # Native Lumina physical control instructions (NUDGE, SETTLE, ASSERT_MASS)
        if op == "NUDGE":
            basin_name, amount = str(inst.args[0]), float(inst.args[1])
            if basin_name in self.group.semantic.basins:
                b_cfg = self.group.semantic.basins[basin_name]
                self.group.get_node(b_cfg.hub_id)["rho"] += amount
            elif basin_name in self.group.engine.physics.node_by_id:
                self.group.get_node(basin_name)["rho"] += amount
            elif f"S_R{basin_name}" in self.group.engine.physics.node_by_id:
                self.group.get_node(f"S_R{basin_name}")["rho"] += amount
            self.record_telemetry()
            return

        if op == "SETTLE":
            steps = int(inst.args[0])
            if self.pure_wave:
                self._reset_pure_wave_routes()
                if steps > 0:
                    self._advance_pure_wave_steps(steps)
                    if not self.record_substep_telemetry:
                        self.record_telemetry()
                return
            for _ in range(max(0, steps)):
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()
            return

        if op == "ASSERT_MASS":
            target_name, min_rho = str(inst.args[0]), float(inst.args[1])
            if target_name in self.group.semantic.basins:
                b_cfg = self.group.semantic.basins[target_name]
                actual_rho = sum(self.group.get_node(nid)["rho"] for nid in b_cfg.node_ids)
                if b_cfg.battery_id and b_cfg.battery_id in self.group.engine.physics.node_by_id:
                    actual_rho += self.group.get_node(b_cfg.battery_id)["rho"]
            elif f"S_R{target_name}" in self.group.engine.physics.node_by_id:
                actual_rho = self.group.get_node(f"S_R{target_name}")["rho"] + self.group.get_node(f"S_R{target_name}_B")["rho"]
            elif target_name in self.group.engine.physics.node_by_id:
                actual_rho = self.group.get_node(target_name)["rho"]
            else:
                raise KeyError(f"Unknown ASSERT_MASS target: {target_name}")
            if actual_rho < min_rho:
                raise AssertionError(
                    f"Physical mass preservation violated on {target_name}: rho={actual_rho:.3f} < {min_rho:.3f}"
                )
            return

        # Pure-wave physical memory transfers (zero Python b_state / hub['psi'] shortcuts)
        if self.pure_wave and op == "LOAD":
            reg, basin_name = inst.args[0], inst.args[1]
            self._reset_pure_wave_routes()
            self.group.set_role_connection(f"wh_load_{basin_name}", True)
            self.group.set_role_connection(f"pw_sum_write_{reg}", True)
            self._advance_pure_wave_steps(45)
            self._settle_pure_wave(10)
            return

        if self.pure_wave and op == "STORE":
            reg, basin_name = inst.args[0], inst.args[1]
            self._reset_pure_wave_routes()
            self.group.set_role_connection(f"pw_bat_drive_sum_{reg}", True)
            self.group.set_role_connection(f"wh_store_{basin_name}", True)
            self._advance_pure_wave_steps(50)
            self._settle_pure_wave(10)
            return

        if self.pure_wave and op == "COPY":
            src, dest = inst.args[0], inst.args[1]
            if src == dest:
                self._settle_pure_wave(5)
                return
            self._reset_pure_wave_routes()
            self.group.set_role_connection(f"pw_bat_drive_sum_{src}", True)
            self.group.set_role_connection(f"pw_sum_write_{dest}", True)
            self._advance_pure_wave_steps(45)
            self._settle_pure_wave(10)
            return

        if self.pure_wave and op == "CMOVE":
            dest, src, cond = inst.args[0], inst.args[1], inst.args[2]
            if src == dest:
                self._settle_pure_wave(5)
                return
            self._reset_pure_wave_routes()
            # Pure-wave dual-cavity multiplexer: (cond & src) | (~cond & dest)
            #   Path B: S_R{cond}_B + S_R{src}_B -> P_Sum -> P_Excite_Gate(thresh_and) -> P_Wave_Cavity
            #   Path A: P_Wave_Ref -> P_CMove_Gate(dest) -> P_Quench_Gate(~cond) -> P_Wave_Cavity_2
            gain = 120.0
            thresh_and = 0.20 + self.wave_threshold_offset
            thresh_cmove = -0.20 + self.wave_threshold_offset
            thresh_quench = 0.20 + self.wave_threshold_offset

            excite = self.group.get_node("P_Excite_Gate")
            cmove_gate = self.group.get_node("P_CMove_Gate")
            quench = self.group.get_node("P_Quench_Gate")
            excite["W_r"] = 0.0
            cmove_gate["W_r"] = 0.0
            quench["W_r"] = 0.0

            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_and
            cmove_gate["U_r"] = gain
            cmove_gate["b_r"] = -gain * thresh_cmove
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_quench

            # Clock Phase Phi_0 (12 RK4 steps): Pre-settle Path B (P_Sum -> P_Excite_Gate) and
            # Path A (P_CMove_Gate, P_Quench_Gate) phases while keeping both cavities anchored < 0.
            self.group.set_role_connection("pw_cavity_sink", True)
            self.group.set_role_connection("pw_cavity_to_out_b", True)
            self.group.set_role_connection("pw_cavity2_sink", True)
            self.group.set_role_connection("pw_cavity2_to_out_b", True)
            self.group.set_role_connection(f"pw_bat_drive_sum_{cond}", True)
            self.group.set_role_connection(f"pw_bat_drive_sum_{src}", True)
            self.group.set_role_connection("pw_sum_sense_excite", True)
            self.group.set_role_connection(f"pw_cmove_dest_{dest}", True)
            self.group.set_role_connection(f"pw_cmove_cond_{cond}", True)

            self._advance_pure_wave_steps(12)

            # Clock Phase Phi_1 (65 RK4 steps): Open carrier pump into dual isolated cavities
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_excite_to_cavity", True)
            self.group.set_role_connection("pw_ref_to_cmove", True)
            self.group.set_role_connection("pw_cmove_to_quench", True)
            self.group.set_role_connection("pw_quench_to_cavity2", True)

            self._advance_pure_wave_steps(65, pump_ref=True)

            psi_sum_end = float(self.group.get_node("P_Sum")["psi"])
            cav1 = self.group.get_node("P_Wave_Cavity")
            cav2 = self.group.get_node("P_Wave_Cavity_2")
            psi_cav_end = float(max(cav1["psi"], cav2["psi"]))
            rho_cav_end = float(cav1["rho"] + cav2["rho"])
            self._commit_pure_wave_cavity_to_register(dest, "CMOVE_WAVE", psi_sum_end, psi_cav_end, rho_cav_end)
            return

        if self.pure_wave and op in (
            "OR", "OR_WAVE", "AND", "AND_WAVE",
            "NOT_WAVE", "NAND_WAVE", "NOR_WAVE", "XOR_WAVE", "XNOR_WAVE",
            "NOT", "NAND", "NOR", "XOR", "XNOR",
        ):
            dest = inst.args[0] if len(inst.args) > 0 else "C"
            canonical_wave_op = {
                "NOT": "NOT_WAVE",
                "NAND": "NAND_WAVE",
                "NOR": "NOR_WAVE",
                "XOR": "XOR_WAVE",
                "XNOR": "XNOR_WAVE",
            }.get(op, op)
            src_a = inst.args[1] if (canonical_wave_op == "NOT_WAVE" and len(inst.args) > 1) else "A"
            self._execute_pure_wave_gate(canonical_wave_op, dest=dest, src_a=src_a, src_b="B")
            return

        if self.pure_wave and op in ("AND_MS", "OR_MS"):
            raise RuntimeError(
                f"Pure-wave execution mode forbids mixed-signal Python boolean shortcut opcode '{op}'."
            )

        # Determine target and register names safely
        if op == "LOAD":
            self.python_boolean_shortcuts_used += 1
            reg, basin_name = inst.args[0], inst.args[1]
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
                self.group.step(self.dt)
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
                self.group.step(self.dt)
                self.record_telemetry()

        elif op == "LOAD_INDIRECT":
            reg, array_prefix, addr_reg = inst.args[0], inst.args[1], inst.args[2]
            # Decode 1-bit or 2-bit address registers
            if isinstance(addr_reg, list):
                msb_state = self.group.get_node(f"S_R{addr_reg[0]}_B")["b_state"]
                lsb_state = self.group.get_node(f"S_R{addr_reg[1]}_B")["b_state"]
                msb = 1 if msb_state == 1 else 0
                lsb = 1 if lsb_state == 1 else 0
                index = (msb << 1) | lsb
            else:
                addr_state = self.group.get_node(f"S_R{addr_reg}_B")["b_state"]
                index = 1 if addr_state == 1 else 0
                
            # Apply Bank Paging: if Basin_Page exists and is active, offset by 4
            if "Basin_Page" in self.group.semantic.basins:
                page_hub = self.group.semantic.basins["Basin_Page"].hub_id
                page_active = self.group.get_node(page_hub)["psi"] >= 0
                if page_active:
                    index += 4
            basin_name = f"Basin_{array_prefix}{index}"
            if self.pure_wave:
                self.execute_instruction(Instruction("LOAD", [reg, basin_name]))
                return
            self.python_boolean_shortcuts_used += 1

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
                self.group.step(self.dt)
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
                self.group.step(self.dt)
                self.record_telemetry()

        elif op == "STORE":
            self.python_boolean_shortcuts_used += 1
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

        elif op == "STORE_INDIRECT":
            reg, array_prefix, addr_reg = inst.args[0], inst.args[1], inst.args[2]
            # Decode 1-bit or 2-bit address registers
            if isinstance(addr_reg, list):
                msb_state = self.group.get_node(f"S_R{addr_reg[0]}_B")["b_state"]
                lsb_state = self.group.get_node(f"S_R{addr_reg[1]}_B")["b_state"]
                msb = 1 if msb_state == 1 else 0
                lsb = 1 if lsb_state == 1 else 0
                index = (msb << 1) | lsb
            else:
                addr_state = self.group.get_node(f"S_R{addr_reg}_B")["b_state"]
                index = 1 if addr_state == 1 else 0
                
            # Apply Bank Paging: if Basin_Page exists and is active, offset by 4
            if "Basin_Page" in self.group.semantic.basins:
                page_hub = self.group.semantic.basins["Basin_Page"].hub_id
                page_active = self.group.get_node(page_hub)["psi"] >= 0
                if page_active:
                    index += 4
            basin_name = f"Basin_{array_prefix}{index}"
            if self.pure_wave:
                self.execute_instruction(Instruction("STORE", [reg, basin_name]))
                return
            self.python_boolean_shortcuts_used += 1
            
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
                
                self.group.step(self.dt)
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

        elif op in (
            "OR", "AND", "OR_WAVE", "AND_WAVE",
            "OR_MS", "AND_MS", "NOT", "NAND", "NOR", "XOR", "XNOR",
            "NOT_WAVE", "NAND_WAVE", "NOR_WAVE", "XOR_WAVE", "XNOR_WAVE",
        ):
            # Determine destination register (defaults to 'C')
            dest = inst.args[0] if len(inst.args) > 0 else 'C'
            dest_reg = f"S_R{dest}"
            if op in ("OR_WAVE", "AND_WAVE"):
                op = "OR" if op == "OR_WAVE" else "AND"
            elif op in ("NOT_WAVE", "NAND_WAVE", "NOR_WAVE", "XOR_WAVE", "XNOR_WAVE"):
                op = op.replace("_WAVE", "")
            
            # Determine if we are doing physical threshold logic or mixed-signal logic
            is_mixed_signal = op in ("OR_MS", "AND_MS", "NOT", "NAND", "NOR", "XOR", "XNOR")
            
            if is_mixed_signal:
                self.python_boolean_shortcuts_used += 1
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
            self.python_boolean_shortcuts_used += 1
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

        elif op == "CMOVE":
            self.python_boolean_shortcuts_used += 1
            dest, src, cond = inst.args[0], inst.args[1], inst.args[2]
            src_reg = f"S_R{src}"
            src_reg_b = f"S_R{src}_B"
            dest_reg = f"S_R{dest}"
            cond_reg_b = f"S_R{cond}_B"
            
            # Read condition battery state
            cond_active = (self.group.get_node(cond_reg_b)["b_state"] == 1)
            
            # Phase 1: Route through Summing Junction (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        if cond_active and (r == src or r == dest):
                            self.group.get_node(g_id)["psi_bias"] = 1.0
                        else:
                            self.group.get_node(g_id)["psi_bias"] = -1.0
                            
                self.configure_alu_output_routing(dest if dest in ('C', 'D') else (src if src in ('C', 'D') else None))
                self.set_wormhole_connections(None, is_load=True)
                
                src_state = self.group.get_node(src_reg_b)["b_state"]
                if cond_active:
                    self.group.get_node(src_reg)["psi_bias"] = 1.0 if src_state == 1 else -1.0
                    self.group.get_node(dest_reg)["psi_bias"] = 0.5 if src_state == 1 else -1.0
                else:
                    self.group.get_node(src_reg)["psi_bias"] = 1.0 if src_state == 1 else -1.0
                    dest_state = self.group.get_node(dest_reg + "_B")["b_state"]
                    self.group.get_node(dest_reg)["psi_bias"] = 1.0 if dest_state == 1 else -1.0
                
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
            if self.pure_wave:
                self._reset_pure_wave_routes()
                bat_node = self.group.get_node(reg_bat)
                host_node = self.group.get_node(reg_host)
                for _ in range(30):
                    bat_node["b_charge"] = 0.0
                    bat_node["psi_bias"] = -1.0
                    bat_node["psi"] = -1.0
                    bat_node["b_state"] = -1
                    host_node["rho"] = 5.0
                    bat_node["rho"] = 0.0
                    host_node["psi_bias"] = 0.0
                    host_node["psi"] = -1.0
                    self.group.step(dt=self.dt)
                    if self.record_substep_telemetry:
                        self.record_telemetry()
                if not self.record_substep_telemetry:
                    self.record_telemetry()
                return

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
                self.group.get_node(reg_host)["rho"] = 5.0
                self.group.get_node(reg_bat)["rho"] = 0.0
                self.group.get_node(reg_host)["psi_bias"] = -1.0
                self.group.get_node(reg_host)["psi"] = -1.0
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "RESET_CORE":
            if self.pure_wave:
                self._reset_pure_wave_routes()
                for r in ("C", "D"):
                    if f"S_R{r}" in self.group.engine.physics.node_by_id:
                        self.group.get_node(f"S_R{r}")["rho"] = 5.0
                        self.group.get_node(f"S_R{r}")["psi"] = -1.0
                        self.group.get_node(f"S_R{r}")["psi_bias"] = 0.0
                    if f"S_R{r}_B" in self.group.engine.physics.node_by_id:
                        bat = self.group.get_node(f"S_R{r}_B")
                        bat["rho"] = 0.0
                        bat["b_state"] = -1
                        bat["b_charge"] = 0.0
                        bat["psi"] = -1.0
                        bat["psi_bias"] = -1.0
                self._advance_pure_wave_steps(15)
                if not self.record_substep_telemetry:
                    self.record_telemetry()
                return
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
        
        # Determine basin states safely across arbitrary basin counts (including scratch/ALU basins > 5)
        basin_states: dict[str, int] = {}
        basin_rhos: dict[str, float] = {}
        for b_name, b_cfg in self.group.semantic.basins.items():
            if b_cfg.battery_id and b_cfg.battery_id in self.group.engine.physics.node_by_id:
                b_state_val = 1 if self.group.get_node(b_cfg.battery_id)["b_state"] == 1 else 0
                b_rho_val = sum(self.group.get_node(nid)["rho"] for nid in b_cfg.node_ids) + self.group.get_node(b_cfg.battery_id)["rho"]
            else:
                b_state_val = 1 if (b_cfg.hub_id in self.group.engine.physics.node_by_id and self.group.get_node(b_cfg.hub_id)["psi"] >= 0) else 0
                b_rho_val = sum(self.group.get_node(nid)["rho"] for nid in b_cfg.node_ids if nid in self.group.engine.physics.node_by_id)
            basin_states[b_name] = b_state_val
            basin_rhos[b_name] = b_rho_val

        basin_list = list(self.group.semantic.basins.keys())
        def _legacy_b_state(idx: int, fallback_hub: str) -> int:
            if idx < len(basin_list):
                return basin_states[basin_list[idx]]
            return 1 if (fallback_hub in self.group.engine.physics.node_by_id and self.group.get_node(fallback_hub)["psi"] >= 0) else 0

        b_a_state = _legacy_b_state(0, "S0")
        b_b_state = _legacy_b_state(1, "S10")
        b_c_state = _legacy_b_state(2, "S20")
        b_d_state = _legacy_b_state(3, "S30")
        b_e_state = _legacy_b_state(4, "S40")
        
        self.history.append({
            "step": len(self.history),
            "basin_a_state": b_a_state,
            "basin_b_state": b_b_state,
            "basin_c_state": b_c_state,
            "basin_d_state": b_d_state,
            "basin_e_state": b_e_state,
            "basin_states": basin_states,
            "basin_rhos": basin_rhos,
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
