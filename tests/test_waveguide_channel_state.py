# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Tests for SOL Waveguide Sandbox Channel State
"""

import pytest
from sol_waveguide_channel_state import (
    build_waveguide_channel_state,
    validate_waveguide_channel_id,
    execute_waveguide_channel_send,
    execute_waveguide_channel_recv,
    execute_waveguide_channel_route,
    execute_waveguide_channel_fence,
    snapshot_waveguide_channel_state,
    compare_waveguide_channel_states
)
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_micro_isa_v1_spec import (
    set_waveguide_channel_state_enabled,
    build_micro_isa_v1_opcode_spec
)
from sol_micro_isa_v1_capability_matrix import (
    build_micro_isa_v1_capability_matrix,
    assert_micro_isa_v1_extension_compliance
)
from sol_waveguide_optimization_pass_manager import (
    run_waveguide_optimization_passes
)
from sol_waveguide_trace_replay import (
    replay_waveguide_execution_trace,
    validate_waveguide_channel_trace_metadata
)
from sol_strict_backend_execution_proof import (
    build_strict_backend_support_matrix
)

# 1. Channel state construction
def test_channel_state_construction():
    state = build_waveguide_channel_state(width_bits=32, channel_count=8)
    assert state["width_bits"] == 32
    assert state["channel_count"] == 8
    assert len(state["channels"]) == 8
    assert state["channels"][0]["valid"] is False
    assert state["channels"][0]["value"] == 0

# 2. Channel send
def test_channel_send():
    state = build_waveguide_channel_state(width_bits=32)
    meta = execute_waveguide_channel_send(state, 2, 0x123456789)
    assert meta["channel_id"] == 2
    assert meta["value_masked"] == 0x23456789  # masked to 32 bits
    assert state["channels"][2]["valid"] is True
    assert state["channels"][2]["value"] == 0x23456789

    with pytest.raises(ValueError):
        execute_waveguide_channel_send(state, 99, 100)  # out of bounds

# 3. Channel receive
def test_channel_recv():
    state = build_waveguide_channel_state(width_bits=32, clear_on_recv=True)
    execute_waveguide_channel_send(state, 1, 42)
    val, meta = execute_waveguide_channel_recv(state, 1)
    assert val == 42
    assert meta["channel_valid_before"] is True
    assert meta["channel_valid_after"] is False  # cleared on recv
    assert state["channels"][1]["valid"] is False

    # Receive from empty channel
    val2, meta2 = execute_waveguide_channel_recv(state, 1)
    assert val2 == 0
    assert meta2["channel_valid_before"] is False
    assert meta2["empty_recv_triggered"] is True
    assert state["empty_flag_triggered"] is True

# 4. Channel route
def test_channel_route():
    state = build_waveguide_channel_state(width_bits=32)
    execute_waveguide_channel_send(state, 3, 999)
    
    # Route with mask = 0 (not taken)
    meta = execute_waveguide_channel_route(state, 4, 3, 0)
    assert meta["route_enabled"] is False
    assert state["channels"][4]["valid"] is False
    
    # Route with mask = 1 (taken)
    meta2 = execute_waveguide_channel_route(state, 4, 3, 1)
    assert meta2["route_enabled"] is True
    assert state["channels"][4]["valid"] is True
    assert state["channels"][4]["value"] == 999

# 5. Bridge integration
def test_bridge_integration():
    # Write to channel 2 and receive from it
    prog = [
        ("LOAD_IMM", "R2", 55),
        ("WG_CHAN_SEND", 2, "R2"),
        ("WG_CHAN_RECV", "R3", 2),
        ("HALT",)
    ]
    
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        optimization_profile="FULL_SAFE_OPTIMIZED"
    )
    config.enable_micro_isa_v1_candidates = True
    config.micro_isa_version = "v1"
    config.enable_waveguide_channel_state = True

    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog, state, config)
    assert report.success is True
    assert state.registers["R3"] == 55

# 6. Scheduler safety
def test_scheduler_safety():
    prog = [
        ("LOAD_IMM", "R2", 123),
        ("WG_CHAN_SEND", 1, "R2"),
        ("WG_CHAN_FENCE",),
        ("WG_CHAN_RECV", "R3", 1),
        ("HALT",)
    ]
    
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        optimization_profile="FULL_SAFE_OPTIMIZED"
    )
    config.enable_micro_isa_v1_candidates = True
    config.micro_isa_version = "v1"
    config.enable_waveguide_channel_state = True

    clean_insts, labels, diamonds, skipped, windows, pc_to_scheduler, report, sched_rep = run_waveguide_optimization_passes(
        prog, config, 32
    )
    
    # Verify fence and send/recv/route are barriers (is_barrier is True)
    barriers = [pc for pc, meta in pc_to_scheduler.items() if meta.get("is_barrier")]
    assert len(barriers) >= 3

# 7. Trace replay
def test_trace_replay():
    prog = [
        ("LOAD_IMM", "R2", 77),
        ("WG_CHAN_SEND", 0, "R2"),
        ("WG_CHAN_RECV", "R4", 0),
        ("HALT",)
    ]
    config = WaveguideControlMemoryBridgeConfig(
        width=32,
        optimization_profile="FULL_SAFE_OPTIMIZED"
    )
    config.enable_micro_isa_v1_candidates = True
    config.micro_isa_version = "v1"
    config.enable_waveguide_channel_state = True
    
    state = build_waveguide_control_memory_state(width=32)
    report = execute_waveguide_control_memory_program(prog, state, config)
    
    # Run trace replay on trace steps
    ok, err, final_state = replay_waveguide_execution_trace(32, report.trace_steps)
    assert ok is True
    assert final_state["registers"]["R4"] == 77
    assert final_state["channel_snapshot"] is not None

# 8. Spec/matrix integration
def test_spec_matrix_integration():
    set_waveguide_channel_state_enabled(False)
    spec = build_micro_isa_v1_opcode_spec()
    assert spec["WG_CHAN_SEND"]["status"] == "UNSUPPORTED"
    
    set_waveguide_channel_state_enabled(True)
    spec2 = build_micro_isa_v1_opcode_spec()
    assert spec2["WG_CHAN_SEND"]["status"] == "TRACE_VALIDATED"
    
    # Capability matrix reports as emulated when enabled
    matrix = build_micro_isa_v1_capability_matrix(spec2, None)
    assert matrix.matrix["pdm_waveguide_microcoded_strict"]["WG_CHAN_SEND"] == "emulated"

# 9. Benchmark integration
def test_benchmark_integration():
    from sol_waveguide_optimization_benchmark import build_waveguide_benchmark_suite
    suite = build_waveguide_benchmark_suite(32)
    ids = [c["case_id"] for c in suite]
    assert "v1_wg_chan_send_basic" in ids
    assert "v1_wg_chan_recv_after_send" in ids
    assert "v1_wg_chan_recv_empty" in ids

# 10. Strict proof
def test_strict_proof():
    support_matrix_obj = build_strict_backend_support_matrix(results=[])
    matrix = support_matrix_obj.matrix
    assert "supports_v1_waveguide_channel_sandbox_state" in matrix["pdm_waveguide_microcoded_strict"]
    assert matrix["pdm_waveguide_microcoded_strict"]["supports_v1_waveguide_channel_sandbox_state"] == "validated"
