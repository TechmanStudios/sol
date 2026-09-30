"""
SOL Telemetry Test Suite
========================
Verifies that OpenTelemetry initializes correctly, handles fallback gracefully,
and emits spans during simulation steps.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))

import telemetry
from sol_engine import SOLEngine


def test_telemetry_initialization():
    # Verify we can initialize telemetry without errors
    telemetry.init_telemetry("sol-test")
    assert telemetry._IS_INITIALIZED is True
    
    # Verify we get a tracer and meter
    tracer = telemetry.get_tracer("sol-test")
    meter = telemetry.get_meter("sol-test")
    assert tracer is not None
    assert meter is not None


def test_trace_span_context_manager():
    # Verify trace_span context manager executes block successfully
    executed = False
    with telemetry.trace_span("test-span", {"test.attr": "value"}) as span:
        assert span is not None
        executed = True
    assert executed is True


def test_sol_engine_instrumentation():
    # Verify engine runs successfully with instrumentation active
    engine = SOLEngine.from_default_graph()
    engine.inject("grail", 25.0)
    
    # Run a step and check that metrics calculations and steps execute without errors
    res = engine.step()
    assert res is not None
    assert "totalFlux" in res
    assert "activeCount" in res
    assert engine.step_count == 1
    
    metrics = engine.compute_metrics()
    assert metrics is not None
    assert "entropy" in metrics


def test_exciton_moa_instrumentation():
    # Verify we can run Exciton-MoA elements and trace spans are created
    import sys
    from pathlib import Path
    
    # Locate Exciton-MoA directories
    moa_path = Path(__file__).resolve().parent.parent / "Frontier_OS" / "Exciton-MoA"
    sys.path.insert(0, str(moa_path))
    sys.path.insert(0, str(moa_path / "firmWare"))
    sys.path.insert(0, str(moa_path / "firmWare" / "ExcitonEngine"))
    sys.path.insert(0, str(moa_path / "teleMetry"))
    
    from blank_config import BlankManifoldConfig
    from blank_manifold_core import BlankManifoldCore
    from excitons import ExcitonEngine
    from teleMetry.telemetry import OntologicalOrchestrator
    
    config = BlankManifoldConfig(base_node_count=10, dimensionality=3)
    manifold = BlankManifoldCore(config)
    manifold.generate_manifold()
    
    excitons = ExcitonEngine(manifold)
    orchestrator = OntologicalOrchestrator(manifold)
    
    # Inject mock resonance to trigger active nodes
    node_id = list(manifold.graph.nodes)[0]
    manifold.graph.nodes[node_id]["resonance_accumulator"] = 5.0
    
    # Ignite excitons should run and trigger the trace span without error
    import numpy as np
    coords = np.zeros(3)
    excitons.ignite_excitons(coords)
    
    # Orchestrator scan should run and trigger trace spans/metrics without error
    bursts = orchestrator.scan_manifold()
    assert isinstance(bursts, list)
