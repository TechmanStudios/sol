"""
SOL Continuous Manifold ODE and Gated Recurrent Node Tests
==========================================================
Verifies RK4 integration stability, conservation of mass, and gate-based modulation.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))

from sol_engine import SOLEngine, SOLPhysics


def test_rk4_backward_compatibility():
    """Verify that enabling RK4 does not crash and runs standard steps."""
    engine = SOLEngine.from_default_graph()
    engine.integration_mode = "rk4"
    
    engine.inject("grail", 20.0)
    res = engine.step(dt=0.01)
    
    assert res is not None
    assert "totalFlux" in res
    assert "activeCount" in res
    assert engine.step_count == 1
    
    metrics = engine.compute_metrics()
    assert metrics["mass"] > 0


def test_rk4_conservation_of_mass():
    """Verify that RK4 integration preserves mass (excluding decay)."""
    # Create engine with damping=0 to eliminate physical decay
    engine = SOLEngine.from_default_graph(damping=0.0)
    engine.integration_mode = "rk4"
    
    # Set all node groups to 'bridge' to disable phase gating and ensure all nodes stay awake
    for n in engine.physics.nodes:
        n["group"] = "bridge"
    
    # Disable semantic mass decay temporarily
    engine.physics.semantic_cfg["decayRate"] = 0.0
    engine.physics.battery_cfg = None # disable battery pulse injections
    
    engine.inject("grail", 50.0)
    initial_metrics = engine.compute_metrics()
    initial_mass = initial_metrics["mass"]
    
    # Run several steps with RK4
    for _ in range(10):
        engine.step(dt=0.05, damping=0.0)
        
    final_metrics = engine.compute_metrics()
    final_mass = final_metrics["mass"]
    
    # Mass should be conserved (numerical tolerance threshold)
    assert abs(final_mass - initial_mass) < 1e-6


def test_gated_recurrent_update_gate():
    """Verify update gate (z) locks density retention when z -> 0."""
    engine = SOLEngine.from_default_graph()
    
    # Inject mass
    node_label = "grail"
    engine.inject(node_label, 30.0)
    
    # Discover the target node
    node = next(n for n in engine.physics.nodes if n["label"].lower() == node_label)
    initial_rho = node["rho"]
    
    # Configure gated update to be closed (z_gate -> 0)
    # z_i = sigmoid(W_z * rho_i + U_z * psi_i + b_z)
    # Using b_z = -10.0 makes z_gate -> 0
    engine.gated_recurrent_cfg = {
        "enabled": True,
        "W_z": 0.0,
        "U_z": 0.0,
        "b_z": -10.0,  # fully closed
        "W_r": 0.0,
        "U_r": 0.0,
        "b_r": 10.0,   # open
    }
    
    # Run a step
    engine.step(dt=0.1)
    
    # Density should remain locked despite connections and decay
    assert abs(node["rho"] - initial_rho) < 1e-5
    assert node["z_gate"] < 1e-3


def test_gated_recurrent_reset_gate():
    """Verify reset gate (r) mutes pressure outflux when r -> 0."""
    # Create engine with two nodes and a simple edge to test transport
    raw_nodes = [
        {"id": "A", "label": "NodeA", "group": "bridge", "rho": 50.0},
        {"id": "B", "label": "NodeB", "group": "bridge", "rho": 0.0},
    ]
    raw_edges = [
        {"from": "A", "to": "B", "w0": 1.0, "kind": "tax"},
    ]
    
    engine = SOLEngine.from_graph(raw_nodes, raw_edges)
    
    # With reset gate closed on A, its pressure should be 0, so no transport to B
    engine.gated_recurrent_cfg = {
        "enabled": True,
        "W_z": 0.0,
        "U_z": 0.0,
        "b_z": 10.0,   # update open
        "W_r": 0.0,
        "U_r": 0.0,
        "b_r": -10.0,  # reset closed (mutes pressure)
    }
    
    # Run a step
    res = engine.step(dt=0.1)
    
    # Flux should be extremely close to 0 because pressure gradients are muted
    assert res["totalFlux"] < 1e-4
    assert engine.physics.node_by_id["B"]["rho"] < 1e-4


def test_addressable_register_io_cycle():
    """Verify write-enable, write-lock, and read-enable (primitive 1) behavior."""
    for mode in ["forward_euler", "rk4"]:
        raw_nodes = [
            {"id": "A", "label": "NodeA", "group": "bridge", "rho": 0.0},
            {"id": "B", "label": "NodeB", "group": "bridge", "rho": 0.0},
            {"id": "C", "label": "NodeC", "group": "bridge", "rho": 0.0},
        ]
        raw_edges = [
            {"from": "A", "to": "B", "w0": 1.0, "kind": "tax"},
            {"from": "B", "to": "C", "w0": 1.0, "kind": "tax"},
        ]

        engine = SOLEngine.from_graph(raw_nodes, raw_edges)
        engine.integration_mode = mode
        
        # Turn off automatic global gating so we only test node-specific overrides
        # Or let's test it with gated_recurrent_cfg = enabled: True but with neutral biases
        engine.gated_recurrent_cfg = {
            "enabled": True,
            "W_z": 0.0, "U_z": 0.0, "b_z": 0.0,
            "W_r": 0.0, "U_r": 0.0, "b_r": 0.0,
        }

        # Step 1: Write-enable NodeA and inject mass
        assert engine.write_enable("NodeA")
        assert engine.inject("NodeA", 50.0)
        
        # Run a few steps to let it integrate
        engine.step(dt=0.01)
        node_a = engine.physics.node_by_id["A"]
        assert node_a["rho"] > 40.0
        
        # Step 2: Lock NodeA (z_bias = -20.0, r_bias = -20.0) -> z_gate -> 0, r_gate -> 0
        assert engine.write_lock("NodeA")
        
        # Write-enable NodeB so it can receive mass (if any flowed)
        assert engine.write_enable("NodeB")
        
        # Save starting mass of NodeA when locked
        locked_mass = node_a["rho"]
        
        # Run 100 steps
        for _ in range(100):
            engine.step(dt=0.01)
            
        # NodeA should hold its mass perfectly (since z_gate is 0, inhibiting flux and decay)
        # NodeB and NodeC should remain at 0 mass (since r_gate of A is 0, inhibiting outflux)
        node_b = engine.physics.node_by_id["B"]
        node_c = engine.physics.node_by_id["C"]
        
        assert abs(node_a["rho"] - locked_mass) < 1e-3
        assert node_b["rho"] < 1e-3
        assert node_c["rho"] < 1e-3
        
        # Step 3: Read-enable NodeA (z_bias = 0.0, r_bias = 10.0) -> z_gate is active/normal, r_gate -> 1.0
        # Let's keep NodeB write-enabled (z_bias = 10.0) so it can receive mass
        assert engine.read_enable("NodeA")
        
        # Run 50 steps
        for _ in range(50):
            engine.step(dt=0.02)
            
        # Mass should have successfully flowed from A to B (and potentially B to C if B read-enabled)
        # Let's verify that B now has non-trivial mass
        assert node_b["rho"] > 0.05


def test_semantic_and_gate():
    """Verify that a node with customized weights behaves as a semantic AND gate."""
    # Setup: A -> C <- B, C -> D
    # We want C's reset gate (r) to only open when both A and B have active density flowing to C
    raw_nodes = [
        {"id": "A", "label": "NodeA", "group": "bridge", "rho": 0.0},
        {"id": "B", "label": "NodeB", "group": "bridge", "rho": 0.0},
        {"id": "C", "label": "NodeC", "group": "bridge", "rho": 0.0,
         "W_r": 1.0, "b_r": -15.0}, # Overrides to need density > 15 to open reset gate
        {"id": "D", "label": "NodeD", "group": "bridge", "rho": 0.0},
    ]
    raw_edges = [
        {"from": "A", "to": "C", "w0": 1.0, "kind": "tax"},
        {"from": "B", "to": "C", "w0": 1.0, "kind": "tax"},
        {"from": "C", "to": "D", "w0": 1.0, "kind": "tax"},
    ]
    
    # Test Scenario 1: Only NodeA is active
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0)
    engine.physics.node_by_id["A"]["rho"] = 25.0
    engine.physics.node_by_id["B"]["rho"] = 0.0
    
    # Step simulation to let flow occur
    for _ in range(100):
        engine.step(dt=0.04)
        
    # Since only A was active, the mass in C should be < 15
    # This density is < 15, so C's reset gate should remain closed, and D should have no mass
    assert engine.physics.node_by_id["C"]["rho"] < 15.0
    assert engine.physics.node_by_id["D"]["rho"] < 0.01
    
    # Test Scenario 2: Both NodeA and NodeB are active
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0)
    engine.physics.node_by_id["A"]["rho"] = 25.0
    engine.physics.node_by_id["B"]["rho"] = 25.0
    
    for _ in range(100):
        engine.step(dt=0.04)
        
    # Combined inputs should push C's density above 15, opening the reset gate to flow mass to D
    assert engine.physics.node_by_id["C"]["rho"] > 15.0
    assert engine.physics.node_by_id["D"]["rho"] > 0.5  # Mass successfully flowed to D!


def test_semantic_not_gate():
    """Verify that a node with customized weights behaves as a semantic NOT gate."""
    # Setup PMOS transistor NOT gate: S (Source constant) -> B (Gate) -> C (Output/Drain)
    # Control input A also connected to B.
    # B is normally open and flows mass from S to C.
    # But if A is active, it floods B, closing B's reset gate, suppressing flow to C.
    raw_nodes = [
        {"id": "S", "label": "NodeS", "group": "bridge", "rho": 20.0},
        {"id": "A", "label": "NodeA", "group": "bridge", "rho": 0.0},
        {"id": "B", "label": "NodeB", "group": "bridge", "rho": 0.0,
         "W_r": -3.0, "b_r": 12.0}, # Overrides to close gate when B's density is high
        {"id": "C", "label": "NodeC", "group": "bridge", "rho": 0.0},
    ]
    raw_edges = [
        {"from": "S", "to": "B", "w0": 1.0, "kind": "tax"},
        {"from": "A", "to": "B", "w0": 1.0, "kind": "tax"},
        {"from": "B", "to": "C", "w0": 1.0, "kind": "tax"},
    ]
    
    # Test Scenario 1: A is inactive
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0)
    # Run steps to verify normal flow from S through B to C
    for _ in range(100):
        engine.step(dt=0.04)
    # Flow to C is enabled
    assert engine.physics.node_by_id["C"]["rho"] > 1.0
    
    # Test Scenario 2: A is highly active, injecting mass to B
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0)
    engine.physics.node_by_id["A"]["rho"] = 100.0
    # Run steps
    for _ in range(100):
        engine.step(dt=0.04)
    # B's reset gate closed, flow to C is suppressed
    assert engine.physics.node_by_id["C"]["rho"] < 0.3


def test_belief_gated_router():
    """Verify that flow can be gated by belief field polarity."""
    # Setup: A -> B -> C
    # B's reset gate is gated by its belief field average: U_r = 10.0, b_r = -5.0
    raw_nodes = [
        {"id": "A", "label": "NodeA", "group": "bridge", "rho": 50.0},
        {"id": "B", "label": "NodeB", "group": "bridge", "rho": 0.0,
         "U_r": 10.0, "b_r": -5.0}, # Router node
        {"id": "C", "label": "NodeC", "group": "bridge", "rho": 0.0},
    ]
    raw_edges = [
        {"from": "A", "to": "B", "w0": 1.0, "kind": "tax"},
        {"from": "B", "to": "C", "w0": 1.0, "kind": "tax"},
    ]
    
    # Scenario 1: Negative belief context on B (psi_bias = -1.0) -> gate remains closed
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0)
    engine.physics.node_by_id["B"]["psi_bias"] = -1.0
    engine.physics.node_by_id["B"]["psi"] = -1.0
    
    for _ in range(100):
        engine.step(dt=0.04)
        
    # Flow from B to C should be blocked
    assert engine.physics.node_by_id["C"]["rho"] < 0.01
    
    # Scenario 2: Positive belief context on B (psi_bias = 1.0) -> gate opens
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0)
    engine.physics.node_by_id["B"]["psi_bias"] = 1.0
    engine.physics.node_by_id["B"]["psi"] = 1.0
    
    for _ in range(100):
        engine.step(dt=0.04)
        
    # Flow from B to C should be enabled
    assert engine.physics.node_by_id["C"]["rho"] > 0.5


def test_self_terminating_thought_loop():
    """Verify that a feedback thought loop halts automatically using self-routing logic."""
    for mode in ["forward_euler", "rk4"]:
        raw_nodes = [
            {"id": "A", "label": "NodeA", "group": "bridge", "rho": 50.0},
            {"id": "B", "label": "NodeB", "group": "bridge", "rho": 0.0,
             "W_r": -3.0, "b_r": 12.0},  # Closes its own reset gate when density is high
        ]
        raw_edges = [
            {"from": "A", "to": "B", "w0": 1.0, "kind": "tax"},
            {"from": "B", "to": "A", "w0": 1.0, "kind": "tax"},
        ]

        engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0)
        engine.integration_mode = mode

        # Run Early-Terminating Loop
        result = engine.run_until_halt(max_steps=250, flux_threshold=1e-3, dt=0.1)

        # Verify correct early termination
        assert result["halted"] is True
        assert result["steps_run"] < 250
        assert result["final_flux"] < 1e-3
        
        # Verify that B absorbed the majority of the mass and A is empty
        assert engine.physics.node_by_id["A"]["rho"] < 0.01
        assert engine.physics.node_by_id["B"]["rho"] > 40.0



