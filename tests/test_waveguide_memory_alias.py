# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Verification suite for the SOL Waveguide Memory Alias + Shard Range Analysis Bridge.
"""

import pytest
from typing import Dict, Any, List

from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_waveguide_memory_alias import (
    build_waveguide_memory_access,
    build_waveguide_memory_range,
    classify_waveguide_memory_alias,
    validate_waveguide_memory_reorder_safety,
    get_instruction_memory_alias_metadata
)
from sol_waveguide_scoreboard_scheduler import build_waveguide_scoreboard
from sol_waveguide_predication import detect_waveguide_branch_diamonds, analyze_waveguide_predication_safety
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    WaveguideControlMemoryBridgeConfig,
    execute_waveguide_control_memory_program
)
from sol_waveguide_trace_replay import validate_waveguide_trace_metadata, replay_waveguide_execution_trace
from sol_strict_backend_execution_proof import (
    StrictBackendProgramCase,
    run_strict_backend_program_case,
    snapshot_active_state,
    verify_active_state
)

# 1. Memory Access Parsing
def test_memory_access_parsing():
    # Static LOAD
    inst_load = WideWordProgramInstruction(op="LOAD", dst="R1", src1=100)
    inst_load.shard = "A"
    inst_load.width = 32
    access = build_waveguide_memory_access(inst_load, pc=1)
    
    assert access is not None
    assert access["opcode"] == "LOAD"
    assert access["access_kind"] == "read"
    assert access["shard_id"] == "A"
    assert access["address"] == 100
    assert access["address_kind"] == "static"
    assert access["width_bits"] == 32
    assert access["range_start"] == 100
    assert access["range_end"] == 103  # 100 + 4 - 1
    assert access["is_dynamic"] is False
    assert access["is_barrier"] is False
    assert access["barrier_reason"] is None
    
    # Static STORE
    inst_store = WideWordProgramInstruction(op="STORE", dst="R2", src1=200)
    inst_store.shard = "B"
    inst_store.width = 64
    access2 = build_waveguide_memory_access(inst_store, pc=2)
    
    assert access2 is not None
    assert access2["opcode"] == "STORE"
    assert access2["access_kind"] == "write"
    assert access2["shard_id"] == "B"
    assert access2["address"] == 200
    assert access2["width_bits"] == 64
    assert access2["range_start"] == 200
    assert access2["range_end"] == 207  # 200 + 8 - 1
    assert access2["is_dynamic"] is False
    assert access2["is_barrier"] is False
    
    # Invalid address (negative)
    inst_neg = WideWordProgramInstruction(op="LOAD", dst="R1", src1=-5)
    access_neg = build_waveguide_memory_access(inst_neg, pc=3)
    assert access_neg["is_barrier"] is True
    assert access_neg["barrier_reason"] == "negative_address_out_of_bounds"
    
    # Dynamic Address
    inst_dyn = WideWordProgramInstruction(op="LOAD", dst="R1", src1="R2")
    access_dyn = build_waveguide_memory_access(inst_dyn, pc=4)
    assert access_dyn["is_dynamic"] is True
    assert access_dyn["is_barrier"] is True
    assert access_dyn["barrier_reason"] == "dynamic_address_unknown_alias"

# 2. Alias Classification
def test_alias_classification():
    # Same shard, same address
    a1 = {"shard_id": "A", "address": 100, "width_bits": 32, "range_start": 100, "range_end": 103, "is_barrier": False}
    a2 = {"shard_id": "A", "address": 100, "width_bits": 32, "range_start": 100, "range_end": 103, "is_barrier": False}
    assert classify_waveguide_memory_alias(a1, a2) == "MUST_ALIAS"
    
    # Same shard, overlapping ranges
    a3 = {"shard_id": "A", "address": 100, "width_bits": 32, "range_start": 100, "range_end": 103, "is_barrier": False}
    a4 = {"shard_id": "A", "address": 102, "width_bits": 32, "range_start": 102, "range_end": 105, "is_barrier": False}
    assert classify_waveguide_memory_alias(a3, a4) == "MAY_ALIAS"
    
    # Same shard, disjoint ranges
    a5 = {"shard_id": "A", "address": 100, "width_bits": 32, "range_start": 100, "range_end": 103, "is_barrier": False}
    a6 = {"shard_id": "A", "address": 104, "width_bits": 32, "range_start": 104, "range_end": 107, "is_barrier": False}
    assert classify_waveguide_memory_alias(a5, a6) == "NO_ALIAS"
    
    # Different shards
    a7 = {"shard_id": "A", "address": 100, "width_bits": 32, "range_start": 100, "range_end": 103, "is_barrier": False}
    a8 = {"shard_id": "B", "address": 100, "width_bits": 32, "range_start": 100, "range_end": 103, "is_barrier": False}
    assert classify_waveguide_memory_alias(a7, a8) == "NO_ALIAS"
    
    # Dynamic/barrier address
    a9 = {"shard_id": "A", "is_barrier": True, "barrier_reason": "dynamic"}
    assert classify_waveguide_memory_alias(a7, a9) == "UNKNOWN_ALIAS"

# 3. Scheduler Integration
def test_scheduler_integration():
    # Independent LOADs (disjoint static ranges, same shard)
    i1 = WideWordProgramInstruction(op="LOAD", dst="R1", src1=10)
    i1.shard = "A"
    i1.width = 32
    i2 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=20)
    i2.shard = "A"
    i2.width = 32
    
    superblocks, scheduled, report = build_waveguide_scoreboard([i1, i2], [], enable_memory_alias_analysis=True)
    # Both are independent loads, so they must batch in wavefront 0
    assert len(scheduled[0]) == 1  # 1 wavefront batch containing both instructions
    assert len(scheduled[0][0]) == 2
    
    # Overlapping STORE/LOAD does not batch
    i3 = WideWordProgramInstruction(op="STORE", dst="R1", src1=10)
    i3.shard = "A"
    i3.width = 32
    i4 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=10)
    i4.shard = "A"
    i4.width = 32
    
    superblocks, scheduled2, report2 = build_waveguide_scoreboard([i3, i4], [], enable_memory_alias_analysis=True)
    # Conflicts on address, so must be scheduled sequentially in 2 wavefronts
    assert len(scheduled2[0]) == 2
    assert scheduled2[0][0] == [0]
    assert scheduled2[0][1] == [1]

# 4. Predication Integration
def test_predication_integration():
    # Branch diamond with static LOAD only is allowed when memory alias analysis is enabled
    prog = [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=1),
        WideWordProgramInstruction(op="CMP", dst="R1", src1=0),
        WideWordProgramInstruction(op="JZ", dst="target"),
        WideWordProgramInstruction(op="LOAD", dst="R2", src1=4),
        WideWordProgramInstruction(op="JMP", dst="end"),
        "target:",
        WideWordProgramInstruction(op="LOAD", dst="R2", src1=8),
        "end:",
        WideWordProgramInstruction(op="HALT")
    ]
    # Set shard and width on memory ops
    for inst in prog:
        if isinstance(inst, WideWordProgramInstruction) and inst.op in ("LOAD", "STORE"):
            inst.shard = "A"
            inst.width = 32
            
    clean_prog = [inst for inst in prog if not isinstance(inst, str)]
    labels = {"target": 5, "end": 6}
    diamonds, skipped = detect_waveguide_branch_diamonds(clean_prog, labels, enable_memory_alias_analysis=True)
    assert len(diamonds) == 1
    assert diamonds[0].diamond_type == "if_else"
    
    # Store in diamond is rejected
    prog_store = [
        WideWordProgramInstruction(op="MOV", dst="R1", src1=1),
        WideWordProgramInstruction(op="CMP", dst="R1", src1=0),
        WideWordProgramInstruction(op="JZ", dst="target"),
        WideWordProgramInstruction(op="STORE", dst="R2", src1=4),
        WideWordProgramInstruction(op="JMP", dst="end"),
        "target:",
        WideWordProgramInstruction(op="STORE", dst="R2", src1=8),
        "end:",
        WideWordProgramInstruction(op="HALT")
    ]
    for inst in prog_store:
        if isinstance(inst, WideWordProgramInstruction) and inst.op in ("LOAD", "STORE"):
            inst.shard = "A"
            inst.width = 32
    clean_prog_store = [inst for inst in prog_store if not isinstance(inst, str)]
    diamonds_store, skipped_store = detect_waveguide_branch_diamonds(clean_prog_store, labels, enable_memory_alias_analysis=True)
    assert len(diamonds_store) == 0
    assert len(skipped_store) > 0

# 5. Execution Equivalence
def test_execution_equivalence():
    prog = [
        WideWordProgramInstruction(op="MOV", dst="R10", src1=100),
        WideWordProgramInstruction(op="MOV", dst="R11", src1=200),
        WideWordProgramInstruction(op="LOAD", dst="R8", src1=10),
        WideWordProgramInstruction(op="LOAD", dst="R9", src1=20),
        WideWordProgramInstruction(op="HALT")
    ]
    for inst in prog:
        if isinstance(inst, WideWordProgramInstruction) and inst.op in ("LOAD", "STORE"):
            inst.shard = "A"
            inst.width = 32
            
    # Run raw
    state_raw = build_waveguide_control_memory_state(width=32)
    config_raw = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_branch_predication=False,
        enable_pipeline_compaction=False,
        enable_scoreboard_scheduling=False,
        enable_memory_alias_analysis=False
    )
    report_raw = execute_waveguide_control_memory_program(prog, state_raw, config_raw)
    assert report_raw.success is True
    
    # Run with memory alias and scheduling
    state_opt = build_waveguide_control_memory_state(width=32)
    config_opt = WaveguideControlMemoryBridgeConfig(
        width=32,
        enable_branch_predication=False,
        enable_pipeline_compaction=False,
        enable_scoreboard_scheduling=True,
        enable_memory_alias_analysis=True
    )
    report_opt = execute_waveguide_control_memory_program(prog, state_opt, config_opt)
    assert report_opt.success is True
    
    # Check states match
    assert state_raw.registers == state_opt.registers
    assert state_raw.flags == state_opt.flags
    assert state_raw.memory.cells == state_opt.memory.cells
    assert state_raw.pc == state_opt.pc

# 6. Trace Replay Audit
def test_trace_replay_auditing():
    # Valid trace step metadata is accepted by the validator
    from sol_waveguide_control_memory_bridge import WaveguideControlMemoryInstructionTrace
    
    inst = WideWordProgramInstruction(op="LOAD", dst="R1", src1=10)
    inst.shard = "A"
    inst.width = 32
    
    meta = get_instruction_memory_alias_metadata(inst, 1, [inst], enable_memory_alias_analysis=True, width=32)
    
    step = WaveguideControlMemoryInstructionTrace(
        step_index=0,
        pc_before=1,
        pc_after=2,
        instruction=inst,
        layer_used="waveguide_memory_shard",
        sol_result=0,
        oracle_result=0,
        sol_flags={},
        oracle_flags={},
        match=True
    )
    setattr(step, "memory_alias_metadata", meta)
    
    ok, err = validate_waveguide_trace_metadata([step], 5, 32)
    assert ok is True
    
    # Falsely marked NO_ALIAS overlapping ranges rejected
    inst2 = WideWordProgramInstruction(op="STORE", dst="R1", src1=10)
    inst2.shard = "A"
    inst2.width = 32
    
    step2 = WaveguideControlMemoryInstructionTrace(
        step_index=1,
        pc_before=2,
        pc_after=3,
        instruction=inst2,
        layer_used="waveguide_memory_shard",
        sol_result=0,
        oracle_result=0,
        sol_flags={},
        oracle_flags={},
        match=True
    )
    # Manually fabricate falsely marked NO_ALIAS overlapping metadata
    meta2 = {
        "memory_alias_analysis_enabled": True,
        "memory_accesses": [
            {
                "pc": 2,
                "opcode": "STORE",
                "access_kind": "write",
                "shard_id": "A",
                "address": 10,
                "address_kind": "static",
                "width_bits": 32,
                "range_start": 10,
                "range_end": 13,
                "is_dynamic": False,
                "is_barrier": False,
            }
        ],
        "alias_classification": "NO_ALIAS", # Falsely claimed
        "memory_reorder_safe": True,
        "shard_id": "A",
        "range_start": 10,
        "range_end": 13
    }
    setattr(step2, "memory_alias_metadata", meta2)
    
    # Revalidate steps together: should detect overlap conflict because step 0 reads address 10, and step 2 writes address 10 in shard A.
    ok2, err2 = validate_waveguide_trace_metadata([step, step2], 5, 32)
    assert ok2 is False
    assert "Overlap/conflict detected" in err2

# 7. Strict Capability Proof Compliance
def test_strict_capability_proof_compliance():
    case = StrictBackendProgramCase(
        name="test_mem_proof",
        program=[
            WideWordProgramInstruction(op="LOAD_IMM", dst="R1", src1=10),
            WideWordProgramInstruction(op="LOAD_IMM", dst="R2", src1=20),
            WideWordProgramInstruction(op="ADD", dst="R3", src1="R1", src2="R2"),
            WideWordProgramInstruction(op="HALT")
        ],
        width=32
    )
    # Check that our target strict backend layer compiles and validates correctly without mutations
    res = run_strict_backend_program_case(case, backend="pdm_waveguide_microcoded_strict")
    assert res.validated is True
    assert res.failed_instruction_count == 0
    assert res.fallback_instruction_count == 0
