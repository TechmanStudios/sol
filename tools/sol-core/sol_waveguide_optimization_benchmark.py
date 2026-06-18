# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Optimization Benchmark Harness
============================================
Benchmarks raw strict, compacted-only, scheduled-only, and compacted+scheduled
execution modes on representative Micro-ISA programs, comparing simulated cycles
and auditing semantic equivalence.
"""

import json
from typing import List, Dict, Any, Tuple, Optional
from sol_wideword_computation_validation import WideWordProgramInstruction
from sol_waveguide_control_memory_bridge import (
    build_waveguide_control_memory_state,
    execute_waveguide_control_memory_program,
    WaveguideControlMemoryBridgeConfig
)
from sol_waveguide_trace_replay import (
    replay_waveguide_execution_trace,
    validate_waveguide_trace_metadata
)

def make_shift_add_multiply_program(a: int, b: int) -> List[Any]:
    return [
        ("MOV", "R3", 0),
        ("MOV", "R4", a),
        ("MOV", "R5", b),
        "loop:",
        ("CMP", "R5", 0),
        ("JZ", "done"),
        ("AND", "R6", "R5", 1),
        ("JZ", "shift"),
        ("ADD", "R3", "R3", "R4"),
        "shift:",
        ("SHL", "R4", "R4", 1),
        ("SHR", "R5", "R5", 1),
        ("JMP", "loop"),
        "done:",
        ("HALT",)
    ]

def make_restoring_division_program(n: int, d: int) -> List[Any]:
    return [
        ("MOV", "R1", n),
        ("MOV", "R2", d),
        ("MOV", "R3", 0),
        ("MOV", "R4", "R1"),
        "loop:",
        ("CMP", "R4", "R2"),
        ("JB", "done"),
        ("SUB", "R4", "R4", "R2"),
        ("ADD", "R3", "R3", 1),
        ("JMP", "loop"),
        "done:",
        ("HALT",)
    ]

def get_lowered_v0_equivalent(program: List[Any], width: int) -> List[Any]:
    from sol_micro_isa_v1_lowering import lower_v1_candidate_to_v0
    from sol_micro_isa_v1_candidates import V1_CANDIDATE_OPCODES
    from sol_wideword_computation_validation import WideWordProgramInstruction
    
    # First adapt program to WideWordProgramInstruction
    adapted = []
    for inst in program:
        if isinstance(inst, str):
            adapted.append(inst)
        elif isinstance(inst, (tuple, list)):
            op = inst[0].upper()
            dst = inst[1] if len(inst) > 1 else None
            if op in ("VEC_PACK", "VEC_UNPACK") and len(inst) == 6:
                src1 = None
                src2 = tuple(inst[2:])
            else:
                src1 = inst[2] if len(inst) > 2 else None
                if len(inst) == 5:
                    src2 = (inst[3], inst[4])
                else:
                    src2 = inst[3] if len(inst) > 3 else None
            adapted.append(WideWordProgramInstruction(op=op, dst=dst, src1=src1, src2=src2))
        else:
            adapted.append(inst)
            
    lowered_program = []
    label_counter = 0
    for inst in adapted:
        if isinstance(inst, str):
            lowered_program.append(inst)
        elif hasattr(inst, "op") and inst.op.upper() in V1_CANDIDATE_OPCODES:
            ops, label_counter, _ = lower_v1_candidate_to_v0(
                inst,
                label_counter,
                width=width,
                enable_waveguide_channel_state=True
            )
            for op_item in ops:
                if isinstance(op_item, str):
                    lowered_program.append(op_item)
                else:
                    # Convert WideWordProgramInstruction back to tuple format
                    lowered_program.append((op_item.op, op_item.dst, op_item.src1, op_item.src2))
        else:
            lowered_program.append((inst.op, inst.dst, inst.src1, inst.src2))
    return lowered_program

def build_waveguide_benchmark_suite(width: int) -> List[Dict[str, Any]]:
    """
    Builds the list of canonical benchmark program cases.
    """
    suite = []
    
    # 1. Straight-line ALU
    suite.append({
        "case_id": "straight_line_alu_independent",
        "description": "Independent ALU operations (MOV, ADD, XOR, AND, OR)",
        "program": [
            ("MOV", "R1", 10),
            ("MOV", "R2", 20),
            ("MOV", "R3", 30),
            ("ADD", "R4", "R1", 5),
            ("XOR", "R5", "R2", 0xFF),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "straight_line_alu_dependent",
        "description": "Dependent ALU register chains",
        "program": [
            ("MOV", "R1", 10),
            ("ADD", "R2", "R1", 5),
            ("ADD", "R3", "R2", 5),
            ("ADD", "R4", "R3", 5),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "straight_line_alu_mixed",
        "description": "Mixed dependent and independent instruction sequences",
        "program": [
            ("MOV", "R1", 10),
            ("MOV", "R2", 20),
            ("ADD", "R3", "R1", "R2"),
            ("MOV", "R4", 30),
            ("MOV", "R5", 40),
            ("ADD", "R6", "R4", "R5"),
            ("ADD", "R7", "R3", "R6"),
            ("HALT",)
        ]
    })
    
    # 2. Flag behavior
    suite.append({
        "case_id": "flag_behavior_zero",
        "description": "Zero-producing arithmetic instruction",
        "program": [
            ("MOV", "R1", 10),
            ("SUB", "R2", "R1", "R1"),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "flag_behavior_carry",
        "description": "Carry-producing addition instruction",
        "program": [
            ("MOV", "R1", 0xFFFFFFFF if width == 32 else 0xFFFFFFFFFFFFFFFF),
            ("ADD", "R2", "R1", 1),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "flag_behavior_sign",
        "description": "Sign-producing subtraction",
        "program": [
            ("MOV", "R1", 10),
            ("SUB", "R2", "R1", 20),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "flag_behavior_borrow",
        "description": "Borrow-producing subtraction",
        "program": [
            ("MOV", "R1", 5),
            ("SUB", "R2", "R1", 10),
            ("HALT",)
        ]
    })
    
    # 3. Branch behavior
    suite.append({
        "case_id": "branch_behavior_jmp",
        "description": "Unconditional jump instruction",
        "program": [
            ("MOV", "R1", 10),
            ("JMP", "skip"),
            ("MOV", "R1", 20),
            "skip:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "branch_behavior_jz_taken",
        "description": "JZ conditional branch taken",
        "program": [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("MOV", "R2", 100),
            "target:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "branch_behavior_jz_not_taken",
        "description": "JZ conditional branch not taken",
        "program": [
            ("MOV", "R1", 10),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("MOV", "R2", 100),
            "target:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "branch_behavior_carry_conditioned",
        "description": "JC conditional branch taken on carry",
        "program": [
            ("MOV", "R1", 0),
            ("SUB", "R2", "R1", 1),
            ("JC", "target"),
            ("MOV", "R3", 100),
            "target:",
            ("HALT",)
        ]
    })
    
    # 4. Memory behavior
    suite.append({
        "case_id": "memory_behavior_load_store",
        "description": "Basic memory LOAD and STORE operations",
        "program": [
            ("MOV", "R1", 100),
            ("STORE", "R1", 10),
            ("LOAD", "R2", 10),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "memory_behavior_load_after_store_same",
        "description": "Memory LOAD immediately after STORE to same address",
        "program": [
            ("MOV", "R1", 100),
            ("STORE", "R1", 20),
            ("LOAD", "R2", 20),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "memory_behavior_independent_scheduling",
        "description": "Memory operations to independent addresses (should allow scheduling)",
        "program": [
            ("MOV", "R1", 100),
            ("STORE", "R1", 10),
            ("MOV", "R2", 200),
            ("STORE", "R2", 20),
            ("LOAD", "R3", 10),
            ("LOAD", "R4", 20),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "memory_behavior_dynamic_barrier",
        "description": "Memory STORE to dynamic address (register address, acts as barrier)",
        "program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 50),
            ("STORE", "R1", "R2"),
            ("LOAD", "R3", "R2"),
            ("HALT",)
        ]
    })
    
    # 5. Wide-word arithmetic
    suite.append({
        "case_id": "wide_word_arithmetic_carry_heavy",
        "description": "Carry-heavy arithmetic causing ripple carry across bytes",
        "program": [
            ("MOV", "R1", 0x01010101 if width == 32 else 0x0101010101010101),
            ("MOV", "R2", 0xFEFEFEFE if width == 32 else 0xFEFEFEFEFEFEFEFE),
            ("ADD", "R3", "R1", "R2"),
            ("ADD", "R4", "R3", 1),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "wide_word_mul_zero",
        "description": "Multiplication loop with operand zero",
        "program": make_shift_add_multiply_program(255, 0)
    })
    
    suite.append({
        "case_id": "wide_word_mul_one",
        "description": "Multiplication loop with operand one",
        "program": make_shift_add_multiply_program(255, 1)
    })
    
    suite.append({
        "case_id": "wide_word_mul_power_of_two",
        "description": "Multiplication loop with power of two operand",
        "program": make_shift_add_multiply_program(128, 8)
    })
    
    suite.append({
        "case_id": "wide_word_mul_max_val",
        "description": "Multiplication loop with max 8-bit operands (255 * 255)",
        "program": make_shift_add_multiply_program(255, 255)
    })
    
    suite.append({
        "case_id": "wide_word_div_one",
        "description": "Restoring division loop with divisor one",
        "program": make_restoring_division_program(10, 1)
    })
    
    suite.append({
        "case_id": "wide_word_div_equal",
        "description": "Restoring division loop with dividend equal to divisor",
        "program": make_restoring_division_program(10, 10)
    })
    
    suite.append({
        "case_id": "wide_word_div_smaller",
        "description": "Restoring division loop with dividend smaller than divisor",
        "program": make_restoring_division_program(5, 10)
    })
    
    suite.append({
        "case_id": "wide_word_div_non_even",
        "description": "Restoring division loop with non-even division (10 / 3)",
        "program": make_restoring_division_program(10, 3)
    })
    
    suite.append({
        "case_id": "wide_word_div_zero",
        "description": "Restoring division loop with division by zero (expects TimeoutError)",
        "program": make_restoring_division_program(10, 0)
    })
    
    # 6. Loop patterns
    suite.append({
        "case_id": "loop_pattern_compactable_mul",
        "description": "Compactable shift-add multiplication loop",
        "program": make_shift_add_multiply_program(5, 4)
    })
    
    suite.append({
        "case_id": "loop_pattern_compactable_div",
        "description": "Compactable restoring division loop",
        "program": make_restoring_division_program(15, 3)
    })
    
    suite.append({
        "case_id": "loop_pattern_generic_uncompactable",
        "description": "Generic loop that must not compact (contains memory STORE)",
        "program": [
            ("MOV", "R1", 5),
            "loop:",
            ("STORE", "R1", 100),
            ("SUB", "R1", "R1", 1),
            ("JNZ", "loop"),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "loop_pattern_no_schedule_across_branch",
        "description": "Loop that must not schedule instructions across branches",
        "program": [
            ("MOV", "R1", 5),
            "loop:",
            ("CMP", "R1", 0),
            ("JZ", "done"),
            ("SUB", "R1", "R1", 1),
            ("JMP", "loop"),
            "done:",
            ("HALT",)
        ]
    })
    
    # 7. Mixed whole-program cases
    suite.append({
        "case_id": "mixed_whole_program_alu_memory_branch",
        "description": "ALU operations, memory storage, and post conditional branch",
        "program": [
            ("MOV", "R1", 10),
            ("STORE", "R1", 100),
            ("LOAD", "R2", 100),
            ("ADD", "R3", "R2", 5),
            ("CMP", "R3", 15),
            ("JZ", "success"),
            ("MOV", "R4", 0),
            ("JMP", "done"),
            "success:",
            ("MOV", "R4", 1),
            "done:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "mixed_whole_program_compact_loop_post_branch",
        "description": "ALU operations, compacted multiply loop, and conditional branch",
        "program": make_shift_add_multiply_program(5, 4) + [
            ("CMP", "R3", 20),
            ("JZ", "ok"),
            ("MOV", "R7", 0),
            ("JMP", "done"),
            "ok:",
            ("MOV", "R7", 1),
            "done:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "mixed_whole_program_prelude_compact_epilogue",
        "description": "Independent prelude operations, compacted multiply loop, and dependent epilogue",
        "program": [
            ("MOV", "R10", 100),
            ("MOV", "R11", 200),
            ("ADD", "R12", "R10", "R11"),
        ] + make_shift_add_multiply_program(5, 4) + [
            ("ADD", "R8", "R3", "R12"),
            ("HALT",)
        ]
    })
    
    # 8. Branch Predication optimization cases
    suite.append({
        "case_id": "pred_branch_skip_taken",
        "description": "Predicated conditional branch skip, taken path (then-arm skipped)",
        "program": [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("ADD", "R2", "R2", 10),
            "target:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "pred_branch_skip_not_taken",
        "description": "Predicated conditional branch skip, not taken path (then-arm executed)",
        "program": [
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("ADD", "R2", "R2", 10),
            "target:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "pred_ifelse_then_selected",
        "description": "Predicated if/else diamond, then-arm selected",
        "program": [
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            ("ADD", "R2", "R2", 10),
            ("JMP", "end_label"),
            "else_label:",
            ("ADD", "R2", "R2", 20),
            "end_label:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "pred_ifelse_else_selected",
        "description": "Predicated if/else diamond, else-arm selected",
        "program": [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            ("ADD", "R2", "R2", 10),
            ("JMP", "end_label"),
            "else_label:",
            ("ADD", "R2", "R2", 20),
            "end_label:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "pred_unsafe_memory_op",
        "description": "Branch diamond containing memory STORE, must skip predication",
        "program": [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("STORE", "R1", 100),
            "target:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "pred_unsafe_nested_branch",
        "description": "Branch diamond containing nested JMP branch, must skip predication",
        "program": [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("JMP", "nested"),
            "nested:",
            ("ADD", "R2", "R2", 5),
            "target:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "pred_unsafe_flag_ambiguity",
        "description": "Branch diamond writing flags that are consumed outside, must skip predication",
        "program": [
            ("MOV", "R1", 0),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            ("ADD", "R2", "R2", 10),
            "target:",
            ("JZ", "outside_target"),
            ("MOV", "R3", 1),
            "outside_target:",
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "pred_mixed_full_optimization",
        "description": "Prelude independent ALU + predicated diamond + compacted multiply loop + scheduled epilogue",
        "program": [
            ("MOV", "R10", 100),
            ("MOV", "R11", 200),
            ("ADD", "R12", "R10", 5),
            ("ADD", "R13", "R11", 10),
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            ("ADD", "R2", "R2", 10),
            ("JMP", "end_label"),
            "else_label:",
            ("ADD", "R2", "R2", 20),
            "end_label:",
        ] + make_shift_add_multiply_program(5, 4)[:-1] + [
            ("ADD", "R8", "R3", "R12"),
            ("ADD", "R9", "R8", "R13"),
            ("HALT",)
        ]
    })
    
    # 9. Memory Alias & Shard Range Analysis optimization cases
    # Case 1: Independent static LOADs, same shard, disjoint ranges
    inst_l1 = WideWordProgramInstruction(op="LOAD", dst="R1", src1=4)
    inst_l1.shard = "A"
    inst_l1.width = 32
    inst_l2 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=8)
    inst_l2.shard = "A"
    inst_l2.width = 32
    suite.append({
        "case_id": "mem_independent_loads",
        "description": "Independent static LOADs, same shard, disjoint ranges",
        "program": [
            inst_l1,
            inst_l2,
            ("HALT",)
        ]
    })
    
    # Case 2: Independent static STOREs, different shards
    inst_s1 = WideWordProgramInstruction(op="STORE", dst="R1", src1=4)
    inst_s1.shard = "A"
    inst_s1.width = 32
    inst_s2 = WideWordProgramInstruction(op="STORE", dst="R2", src1=4)
    inst_s2.shard = "B"
    inst_s2.width = 32
    suite.append({
        "case_id": "mem_independent_stores",
        "description": "Independent static STOREs, different shards",
        "program": [
            ("LOAD_IMM", "R1", 42),
            inst_s1,
            ("LOAD_IMM", "R2", 100),
            inst_s2,
            ("HALT",)
        ]
    })
    
    # Case 3: LOAD after STORE same address, must not reorder
    inst_s3 = WideWordProgramInstruction(op="STORE", dst="R1", src1=4)
    inst_s3.shard = "A"
    inst_s3.width = 32
    inst_l3 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=4)
    inst_l3.shard = "A"
    inst_l3.width = 32
    suite.append({
        "case_id": "mem_hazard_load_after_store",
        "description": "LOAD after STORE same address, must not reorder",
        "program": [
            ("LOAD_IMM", "R1", 42),
            inst_s3,
            inst_l3,
            ("HALT",)
        ]
    })
    
    # Case 4: STORE after LOAD same address, must not reorder
    inst_l4 = WideWordProgramInstruction(op="LOAD", dst="R1", src1=4)
    inst_l4.shard = "A"
    inst_l4.width = 32
    inst_s4 = WideWordProgramInstruction(op="STORE", dst="R2", src1=4)
    inst_s4.shard = "A"
    inst_s4.width = 32
    suite.append({
        "case_id": "mem_hazard_store_after_load",
        "description": "STORE after LOAD same address, must not reorder",
        "program": [
            inst_l4,
            ("LOAD_IMM", "R2", 42),
            inst_s4,
            ("HALT",)
        ]
    })
    
    # Case 5: Overlapping static ranges, must not reorder
    inst_s5 = WideWordProgramInstruction(op="STORE", dst="R1", src1=4)
    inst_s5.shard = "A"
    inst_s5.width = 32  # [4, 7]
    inst_l5 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=6)
    inst_l5.shard = "A"
    inst_l5.width = 32  # [6, 9] (overlaps [4, 7])
    suite.append({
        "case_id": "mem_hazard_overlapping_ranges",
        "description": "Overlapping static ranges, must not reorder",
        "program": [
            ("LOAD_IMM", "R1", 42),
            inst_s5,
            inst_l5,
            ("HALT",)
        ]
    })
    
    # Case 6: Dynamic address, must not optimize
    suite.append({
        "case_id": "mem_dynamic_address_barrier",
        "description": "Dynamic address, must not optimize",
        "program": [
            ("LOAD_IMM", "R1", 4),
            ("LOAD", "R2", "R1"),
            ("HALT",)
        ]
    })
    
    # Case 7: Read-only branch diamond candidate
    inst_dia1 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=4)
    inst_dia1.shard = "A"
    inst_dia1.width = 32
    inst_dia2 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=8)
    inst_dia2.shard = "A"
    inst_dia2.width = 32
    suite.append({
        "case_id": "mem_pred_readonly_diamond",
        "description": "Read-only branch diamond candidate",
        "program": [
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            inst_dia1,
            ("JMP", "end"),
            "target:",
            inst_dia2,
            "end:",
            ("HALT",)
        ]
    })
    
    # Case 8: Branch diamond with STORE, must skip
    inst_dia3 = WideWordProgramInstruction(op="STORE", dst="R2", src1=4)
    inst_dia3.shard = "A"
    inst_dia3.width = 32
    inst_dia4 = WideWordProgramInstruction(op="STORE", dst="R2", src1=8)
    inst_dia4.shard = "A"
    inst_dia4.width = 32
    suite.append({
        "case_id": "mem_pred_unsafe_store_diamond",
        "description": "Branch diamond with STORE, must skip",
        "program": [
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "target"),
            inst_dia3,
            ("JMP", "end"),
            "target:",
            inst_dia4,
            "end:",
            ("HALT",)
        ]
    })
    
    # Case 9: Mixed program: ALU prelude + independent memory ops + predicated diamond + compacted loop + scheduled epilogue
    inst_mix1 = WideWordProgramInstruction(op="LOAD", dst="R8", src1=10)
    inst_mix1.shard = "A"
    inst_mix1.width = 32
    inst_mix2 = WideWordProgramInstruction(op="LOAD", dst="R9", src1=20)
    inst_mix2.shard = "B"
    inst_mix2.width = 32
    inst_mix_dia1 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=30)
    inst_mix_dia1.shard = "A"
    inst_mix_dia1.width = 32
    inst_mix_dia2 = WideWordProgramInstruction(op="LOAD", dst="R2", src1=40)
    inst_mix_dia2.shard = "A"
    inst_mix_dia2.width = 32
    suite.append({
        "case_id": "mem_mixed_full_optimization",
        "description": "ALU prelude + independent memory ops + predicated diamond + compacted loop + scheduled epilogue",
        "program": [
            ("MOV", "R10", 100),
            ("MOV", "R11", 200),
            inst_mix1,
            inst_mix2,
            ("MOV", "R1", 1),
            ("CMP", "R1", 0),
            ("JZ", "else_label"),
            inst_mix_dia1,
            ("JMP", "end_label"),
            "else_label:",
            inst_mix_dia2,
            "end_label:",
        ] + make_shift_add_multiply_program(5, 4)[:-1] + [
            ("ADD", "R12", "R10", "R11"),
            ("HALT",)
        ]
    })
    
    # 10. V1 Candidate Opcode cases
    # Case 1: SELECT true
    suite.append({
        "case_id": "v1_select_true",
        "description": "v1 SELECT conditional assignment (true path)",
        "program": [
            ("MOV", "R2", 1),
            ("SELECT", "R1", "R2", 100, 200),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R2", 1),
            ("CMP", "R2", 0),
            ("JNZ", "L_true"),
            ("LOAD_IMM", "R1", 200),
            ("JMP", "L_end"),
            "L_true:",
            ("LOAD_IMM", "R1", 100),
            "L_end:",
            ("HALT",)
        ]
    })

    # Case 2: SELECT false
    suite.append({
        "case_id": "v1_select_false",
        "description": "v1 SELECT conditional assignment (false path)",
        "program": [
            ("MOV", "R2", 0),
            ("SELECT", "R1", "R2", 100, 200),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R2", 0),
            ("CMP", "R2", 0),
            ("JNZ", "L_true"),
            ("LOAD_IMM", "R1", 200),
            ("JMP", "L_end"),
            "L_true:",
            ("LOAD_IMM", "R1", 100),
            "L_end:",
            ("HALT",)
        ]
    })

    # Case 3: CMOVZ taken
    suite.append({
        "case_id": "v1_cmovz_taken",
        "description": "v1 CMOVZ conditional move (Z=1 path)",
        "program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 0),
            ("CMP", "R2", 0),
            ("CMOVZ", "R1", 200),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 0),
            ("CMP", "R2", 0),
            ("JNZ", "L_skip"),
            ("LOAD_IMM", "R1", 200),
            "L_skip:",
            ("HALT",)
        ]
    })

    # Case 4: CMOVZ not taken
    suite.append({
        "case_id": "v1_cmovz_not_taken",
        "description": "v1 CMOVZ conditional move (Z=0 path)",
        "program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 1),
            ("CMP", "R2", 0),
            ("CMOVZ", "R1", 200),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 1),
            ("CMP", "R2", 0),
            ("JNZ", "L_skip"),
            ("LOAD_IMM", "R1", 200),
            "L_skip:",
            ("HALT",)
        ]
    })

    # Case 5: CMOVC taken
    suite.append({
        "case_id": "v1_cmovc_taken",
        "description": "v1 CMOVC conditional move (C=1 path)",
        "program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 0xFFFFFFFF if width == 32 else 0xFFFFFFFFFFFFFFFF),
            ("ADD", "R2", "R2", 1),
            ("CMOVC", "R1", 200),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 0xFFFFFFFF if width == 32 else 0xFFFFFFFFFFFFFFFF),
            ("ADD", "R2", "R2", 1),
            ("JNC", "L_skip"),
            ("LOAD_IMM", "R1", 200),
            "L_skip:",
            ("HALT",)
        ]
    })

    # Case 6: CMOVB taken if borrow flag exists
    suite.append({
        "case_id": "v1_cmovb_taken",
        "description": "v1 CMOVB conditional move (B=1 path)",
        "program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 5),
            ("SUB", "R2", "R2", 10),
            ("CMOVB", "R1", 200),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 5),
            ("SUB", "R2", "R2", 10),
            ("JNB", "L_skip"),
            ("LOAD_IMM", "R1", 200),
            "L_skip:",
            ("HALT",)
        ]
    })

    # Case 7: PLOAD_RO safe static addresses
    suite.append({
        "case_id": "v1_pload_ro_static",
        "description": "v1 PLOAD_RO conditional load with static addresses",
        "program": [
            ("LOAD_IMM", "R4", 42),
            ("STORE", "R4", 10),
            ("LOAD_IMM", "R5", 99),
            ("STORE", "R5", 20),
            ("MOV", "R2", 1),
            ("PLOAD_RO", "R1", "R2", 10, 20),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R4", 42),
            ("STORE", "R4", 10),
            ("LOAD_IMM", "R5", 99),
            ("STORE", "R5", 20),
            ("MOV", "R2", 1),
            ("CMP", "R2", 0),
            ("JNZ", "L_true"),
            ("LOAD_IMM", "R1", 20),
            ("LOAD", "R1", "R1"),
            ("JMP", "L_end"),
            "L_true:",
            ("LOAD_IMM", "R1", 10),
            ("LOAD", "R1", "R1"),
            "L_end:",
            ("HALT",)
        ]
    })

    # Case 8: PLOAD_RO dynamic address rejected
    suite.append({
        "case_id": "v1_pload_ro_dynamic_rejected",
        "description": "v1 PLOAD_RO conditional load with dynamic addresses (rejected)",
        "program": [
            ("MOV", "R2", 1),
            ("MOV", "R3", 10),
            ("MOV", "R4", 20),
            ("PLOAD_RO", "R1", "R2", "R3", "R4"),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R2", 1),
            ("MOV", "R3", 10),
            ("MOV", "R4", 20),
            ("PLOAD_RO", "R1", "R2", "R3", "R4"),
            ("HALT",)
        ]
    })

    # Case 9: PREFIX_ADD carry-heavy values
    suite.append({
        "case_id": "v1_prefix_add",
        "description": "v1 PREFIX_ADD carry-heavy wide-word addition",
        "program": [
            ("MOV", "R2", 0xFFFFFFFF if width == 32 else 0xFFFFFFFFFFFFFFFF),
            ("PREFIX_ADD", "R1", "R2", 1),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R2", 0xFFFFFFFF if width == 32 else 0xFFFFFFFFFFFFFFFF),
            ("ADD", "R1", "R2", 1),
            ("HALT",)
        ]
    })

    # Case 10: PREFIX_SUB borrow-heavy values
    suite.append({
        "case_id": "v1_prefix_sub",
        "description": "v1 PREFIX_SUB borrow-heavy wide-word subtraction",
        "program": [
            ("MOV", "R2", 5),
            ("PREFIX_SUB", "R1", "R2", 10),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("MOV", "R2", 5),
            ("SUB", "R1", "R2", 10),
            ("HALT",)
        ]
    })

    # New Vector & Channel Candidate cases
    # Case 12: VEC_PACK
    v1_vec_pack_prog = [
        ("MOV", "R2", 0x12),
        ("MOV", "R3", 0x34),
        ("MOV", "R4", 0x56),
        ("MOV", "R5", 0x78),
        ("VEC_PACK", "R1", "R2", "R3", "R4", "R5"),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_pack_u32",
        "description": "v1 VEC_PACK pack scalar lanes into register",
        "program": v1_vec_pack_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_pack_prog, width)
    })

    # Case 13: VEC_UNPACK
    v1_vec_unpack_prog = [
        ("LOAD_IMM", "R1", 0x78563412),
        ("VEC_UNPACK", "R1", "R2", "R3", "R4", "R5"),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_unpack_u32",
        "description": "v1 VEC_UNPACK unpack lanes from register",
        "program": v1_vec_unpack_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_unpack_prog, width)
    })

    # Case 14: VEC_BROADCAST
    v1_vec_broadcast_prog = [
        ("MOV", "R2", 0x34),
        ("VEC_BROADCAST", "R1", "R2"),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_broadcast_u32",
        "description": "v1 VEC_BROADCAST broadcast scalar into all lanes",
        "program": v1_vec_broadcast_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_broadcast_prog, width)
    })

    # Case 15: VEC_EXTRACT lane 0
    v1_vec_extract_lane0_prog = [
        ("LOAD_IMM", "R2", 0x78563412),
        ("VEC_EXTRACT", "R1", "R2", 0),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_extract_lane0",
        "description": "v1 VEC_EXTRACT extract lane 0",
        "program": v1_vec_extract_lane0_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_extract_lane0_prog, width)
    })

    # Case 16: VEC_EXTRACT lane 3
    v1_vec_extract_lane3_prog = [
        ("LOAD_IMM", "R2", 0x78563412),
        ("VEC_EXTRACT", "R1", "R2", 3),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_extract_lane3",
        "description": "v1 VEC_EXTRACT extract lane 3",
        "program": v1_vec_extract_lane3_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_extract_lane3_prog, width)
    })

    # Case 17: VEC_INSERT lane 2
    v1_vec_insert_lane2_prog = [
        ("LOAD_IMM", "R2", 0x78563412),
        ("MOV", "R3", 0x99),
        ("VEC_INSERT", "R1", "R2", 2, "R3"),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_insert_lane2",
        "description": "v1 VEC_INSERT replace lane 2 with scalar",
        "program": v1_vec_insert_lane2_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_insert_lane2_prog, width)
    })

    # Case 18: VEC_LANE_ADD mask all
    v1_vec_lane_add_mask_all_prog = [
        ("LOAD_IMM", "R2", 0x04030201),
        ("LOAD_IMM", "R3", 0x10203040),
        ("VEC_LANE_ADD", "R1", "R2", "R3", 0xF),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_lane_add_mask_all",
        "description": "v1 VEC_LANE_ADD add all lanes with carry isolation",
        "program": v1_vec_lane_add_mask_all_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_lane_add_mask_all_prog, width)
    })

    # Case 19: VEC_LANE_ADD mask partial
    v1_vec_lane_add_mask_partial_prog = [
        ("LOAD_IMM", "R2", 0x04030201),
        ("LOAD_IMM", "R3", 0x10203040),
        ("VEC_LANE_ADD", "R1", "R2", "R3", 0x5),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_lane_add_mask_partial",
        "description": "v1 VEC_LANE_ADD add partial lanes with carry isolation",
        "program": v1_vec_lane_add_mask_partial_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_lane_add_mask_partial_prog, width)
    })

    # Case 20: VEC_LANE_SUB mask all
    v1_vec_lane_sub_mask_all_prog = [
        ("LOAD_IMM", "R2", 0x10203040),
        ("LOAD_IMM", "R3", 0x04030201),
        ("VEC_LANE_SUB", "R1", "R2", "R3", 0xF),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_lane_sub_mask_all",
        "description": "v1 VEC_LANE_SUB subtract all lanes with borrow isolation",
        "program": v1_vec_lane_sub_mask_all_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_lane_sub_mask_all_prog, width)
    })

    # Case 21: VEC_MASK_SELECT
    v1_vec_mask_select_prog = [
        ("LOAD_IMM", "R2", 0x11223344),
        ("LOAD_IMM", "R3", 0x55667788),
        ("MOV", "R4", 0xA),
        ("VEC_MASK_SELECT", "R1", "R4", "R2", "R3"),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_vec_mask_select",
        "description": "v1 VEC_MASK_SELECT select lanes conditionally",
        "program": v1_vec_mask_select_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_vec_mask_select_prog, width)
    })

    # Case 22: WG_CHAN_FENCE
    v1_wg_chan_fence_barrier_prog = [
        ("LOAD_IMM", "R2", 42),
        ("WG_CHAN_FENCE",),
        ("MOV", "R1", "R2"),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_wg_chan_fence_barrier",
        "description": "v1 WG_CHAN_FENCE waveguide channel fence ordering barrier",
        "program": v1_wg_chan_fence_barrier_prog,
        "v0_equivalent_program": get_lowered_v0_equivalent(v1_wg_chan_fence_barrier_prog, width)
    })

    # Case 23: Negative channel send rejected
    v1_wg_chan_send_rejected_prog = [
        ("WG_CHAN_SEND", 1, "R2"),
        ("HALT",)
    ]
    suite.append({
        "case_id": "v1_wg_chan_send_rejected",
        "description": "v1 WG_CHAN_SEND dynamic channel send rejected",
        "program": v1_wg_chan_send_rejected_prog,
        "v0_equivalent_program": v1_wg_chan_send_rejected_prog
    })

    # Case 11: Mixed v1 candidate program
    inst_mix_l1 = WideWordProgramInstruction(op="LOAD", dst="R8", src1=10)
    inst_mix_l1.shard = "A"
    inst_mix_l1.width = 32
    inst_mix_l2 = WideWordProgramInstruction(op="LOAD", dst="R9", src1=20)
    inst_mix_l2.shard = "B"
    inst_mix_l2.width = 32
    
    inst_equiv_l1 = WideWordProgramInstruction(op="LOAD", dst="R8", src1=10)
    inst_equiv_l1.shard = "A"
    inst_equiv_l1.width = 32
    inst_equiv_l2 = WideWordProgramInstruction(op="LOAD", dst="R9", src1=20)
    inst_equiv_l2.shard = "B"
    inst_equiv_l2.width = 32
    
    suite.append({
        "case_id": "v1_mixed_full_program",
        "description": "ALU prelude + independent memory ops + v1 SELECT + compacted multiply loop + scheduled epilogue",
        "program": [
            ("LOAD_IMM", "R4", 42),
            ("STORE", "R4", 10),
            ("LOAD_IMM", "R5", 99),
            ("STORE", "R5", 20),
            ("MOV", "R10", 100),
            ("MOV", "R11", 200),
            ("PREFIX_ADD", "R12", "R10", 5),
            inst_mix_l1,
            inst_mix_l2,
            ("MOV", "R2", 1),
            ("SELECT", "R1", "R2", "R8", "R9"),
        ] + make_shift_add_multiply_program(5, 4)[:-1] + [
            ("ADD", "R13", "R3", "R12"),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R4", 42),
            ("STORE", "R4", 10),
            ("LOAD_IMM", "R5", 99),
            ("STORE", "R5", 20),
            ("MOV", "R10", 100),
            ("MOV", "R11", 200),
            ("ADD", "R12", "R10", 5),
            inst_equiv_l1,
            inst_equiv_l2,
            ("MOV", "R2", 1),
            ("CMP", "R2", 0),
            ("JNZ", "L_true"),
            ("MOV", "R1", "R9"),
            ("JMP", "L_end"),
            "L_true:",
            ("MOV", "R1", "R8"),
            "L_end:",
        ] + make_shift_add_multiply_program(5, 4)[:-1] + [
            ("ADD", "R13", "R3", "R12"),
            ("HALT",)
        ]
    })

    # New waveguide channel and acceleration benchmark cases
    suite.append({
        "case_id": "v1_wg_chan_send_basic",
        "description": "v1 WG_CHAN_SEND basic channel send",
        "program": [
            ("LOAD_IMM", "R2", 100),
            ("WG_CHAN_SEND", 2, "R2"),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_recv_after_send",
        "description": "v1 WG_CHAN_RECV reading a previously sent channel value",
        "program": [
            ("LOAD_IMM", "R2", 200),
            ("WG_CHAN_SEND", 1, "R2"),
            ("WG_CHAN_RECV", "R3", 1),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_recv_empty",
        "description": "v1 WG_CHAN_RECV reading an empty/uninitialized channel",
        "program": [
            ("WG_CHAN_RECV", "R3", 3),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_route_taken",
        "description": "v1 WG_CHAN_ROUTE taken when route_mask is non-zero",
        "program": [
            ("LOAD_IMM", "R2", 300),
            ("WG_CHAN_SEND", 4, "R2"),
            ("LOAD_IMM", "R5", 1),
            ("WG_CHAN_ROUTE", 5, 4, "R5"),
            ("WG_CHAN_RECV", "R3", 5),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_route_not_taken",
        "description": "v1 WG_CHAN_ROUTE not taken when route_mask is zero",
        "program": [
            ("LOAD_IMM", "R2", 400),
            ("WG_CHAN_SEND", 4, "R2"),
            ("LOAD_IMM", "R5", 0),
            ("WG_CHAN_ROUTE", 6, 4, "R5"),
            ("WG_CHAN_RECV", "R3", 6),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_fence_ordering",
        "description": "v1 WG_CHAN_FENCE barrier serialization",
        "program": [
            ("LOAD_IMM", "R2", 500),
            ("WG_CHAN_SEND", 0, "R2"),
            ("WG_CHAN_FENCE",),
            ("WG_CHAN_RECV", "R3", 0),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_invalid_channel_rejected",
        "description": "v1 WG_CHAN_SEND invalid channel ID out of bounds rejected",
        "program": [
            ("LOAD_IMM", "R2", 600),
            ("WG_CHAN_SEND", 99, "R2"),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_disabled_rejected",
        "description": "v1 channel instructions rejected when enable_waveguide_channel_state=False",
        "program": [
            ("LOAD_IMM", "R2", 700),
            ("WG_CHAN_SEND", 1, "R2"),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_wg_chan_mixed_program",
        "description": "mixed program with alu and channel operations",
        "program": [
            ("LOAD_IMM", "R2", 800),
            ("WG_CHAN_SEND", 0, "R2"),
            ("WG_CHAN_RECV", "R3", 0),
            ("ADD", "R1", "R3", 10),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "accel_benchmark_batch_serial_equivalence",
        "description": "verify batch benchmark acceleration equivalence",
        "program": [("MOV", "R1", 1), ("HALT",)]
    })

    suite.append({
        "case_id": "v1_chan_independent_sends_batch",
        "description": "v1 channel independent sends batching",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("LOAD_IMM", "R2", 20),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 10),
            ("LOAD_IMM", "R2", 20),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_independent_recvs_batch",
        "description": "v1 channel independent receives batching into different registers",
        "program": [
            ("WG_CHAN_RECV", "R3", 0),
            ("WG_CHAN_RECV", "R4", 1),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("WG_CHAN_RECV", "R3", 0),
            ("WG_CHAN_RECV", "R4", 1),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_send_recv_different_channels_batch",
        "description": "v1 channel send and receive on different channels batching",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_RECV", "R4", 1),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_RECV", "R4", 1),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_send_recv_same_channel_no_batch",
        "description": "v1 channel send and receive on same channel cannot batch",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_RECV", "R4", 0),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_RECV", "R4", 0),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_route_independent_batch",
        "description": "v1 channel route and independent send batching",
        "program": [
            ("LOAD_IMM", "R1", 1),
            ("WG_CHAN_ROUTE", 1, 0, "R1"),
            ("LOAD_IMM", "R3", 30),
            ("WG_CHAN_SEND", 3, "R3"),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 1),
            ("WG_CHAN_ROUTE", 1, 0, "R1"),
            ("LOAD_IMM", "R3", 30),
            ("WG_CHAN_SEND", 3, "R3"),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_route_conflict_no_batch",
        "description": "v1 channel route conflict on channel write cannot batch",
        "program": [
            ("LOAD_IMM", "R1", 1),
            ("WG_CHAN_ROUTE", 1, 0, "R1"),
            ("LOAD_IMM", "R3", 30),
            ("WG_CHAN_SEND", 1, "R3"),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 1),
            ("WG_CHAN_ROUTE", 1, 0, "R1"),
            ("LOAD_IMM", "R3", 30),
            ("WG_CHAN_SEND", 1, "R3"),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_fence_splits_wavefront",
        "description": "v1 channel fence splits wavefront serialization",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_FENCE",),
            ("WG_CHAN_RECV", "R2", 0),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_FENCE",),
            ("WG_CHAN_RECV", "R2", 0),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_mixed_kernel_pipeline",
        "description": "v1 mixed channel operations kernel pipeline",
        "program": [
            ("LOAD_IMM", "R1", 100),
            ("WG_CHAN_SEND", 0, "R1"),
            ("LOAD_IMM", "R2", 200),
            ("WG_CHAN_SEND", 3, "R2"),
            ("LOAD_IMM", "R5", 1),
            ("WG_CHAN_ROUTE", 1, 0, "R5"),
            ("WG_CHAN_RECV", "R3", 1),
            ("WG_CHAN_RECV", "R4", 3),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 100),
            ("WG_CHAN_SEND", 0, "R1"),
            ("LOAD_IMM", "R2", 200),
            ("WG_CHAN_SEND", 3, "R2"),
            ("LOAD_IMM", "R5", 1),
            ("WG_CHAN_ROUTE", 1, 0, "R5"),
            ("WG_CHAN_RECV", "R3", 1),
            ("WG_CHAN_RECV", "R4", 3),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "v1_chan_dependency_disabled_matches_barrier_mode",
        "description": "v1 channel independence analysis disabled behaves as barrier",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("LOAD_IMM", "R2", 20),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("HALT",)
        ],
        "v0_equivalent_program": [
            ("LOAD_IMM", "R1", 10),
            ("LOAD_IMM", "R2", 20),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("HALT",)
        ]
    })
    suite.append({
        "case_id": "v1_kernel_channel_parallel_load",
        "description": "kernel channel parallel load matching sends and receives",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("LOAD_IMM", "R2", 20),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("WG_CHAN_RECV", "R3", 0),
            ("WG_CHAN_RECV", "R4", 1),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    suite.append({
        "case_id": "v1_kernel_channel_fanout",
        "description": "kernel channel fanout matching send, routes, and receives",
        "program": [
            ("LOAD_IMM", "R1", 42),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_ROUTE", 1, 0, 1),
            ("WG_CHAN_ROUTE", 2, 0, 1),
            ("WG_CHAN_RECV", "R3", 1),
            ("WG_CHAN_RECV", "R4", 2),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    suite.append({
        "case_id": "v1_kernel_channel_fence_order",
        "description": "kernel channel fence order matching send, fence, and receive",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_FENCE",),
            ("WG_CHAN_RECV", "R2", 0),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    suite.append({
        "case_id": "v1_kernel_channel_gather",
        "description": "kernel channel gather matching sends, receives, and VEC_PACK",
        "program": [
            ("LOAD_IMM", "R1", 11),
            ("LOAD_IMM", "R2", 22),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("WG_CHAN_RECV", "R3", 0),
            ("WG_CHAN_RECV", "R4", 1),
            ("VEC_PACK", "R5", None, ("R3", "R4", 0, 0)),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    suite.append({
        "case_id": "v1_kernel_channel_route_chain",
        "description": "kernel channel route chain matching send, route chain, and receive",
        "program": [
            ("LOAD_IMM", "R1", 99),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_ROUTE", 1, 0, 1),
            ("WG_CHAN_ROUTE", 2, 1, 1),
            ("WG_CHAN_RECV", "R3", 2),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    suite.append({
        "case_id": "v1_kernel_disabled_matches_channel_dependency_mode",
        "description": "kernel recognition disabled behaves as channel dependency mode",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("LOAD_IMM", "R2", 20),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("WG_CHAN_RECV", "R3", 0),
            ("WG_CHAN_RECV", "R4", 1),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": False
    })

    suite.append({
        "case_id": "v1_kernel_partial_match_skipped",
        "description": "kernel partial match is skipped safely",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("WG_CHAN_SEND", 0, "R1"),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    suite.append({
        "case_id": "v1_kernel_malformed_dynamic_channel_skipped",
        "description": "kernel malformed dynamic channel ID is skipped safely",
        "program": [
            ("LOAD_IMM", "R1", 10),
            ("LOAD_IMM", "R5", 0),
            ("WG_CHAN_SEND", "R5", "R1"),
            ("WG_CHAN_RECV", "R3", "R5"),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    suite.append({
        "case_id": "v1_kernel_gather_with_insert",
        "description": "kernel channel gather with VEC_INSERT sequence",
        "program": [
            ("LOAD_IMM", "R1", 50),
            ("LOAD_IMM", "R2", 60),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_SEND", 1, "R2"),
            ("WG_CHAN_RECV", "R3", 0),
            ("WG_CHAN_RECV", "R4", 1),
            ("LOAD_IMM", "R5", 0),
            ("VEC_INSERT", "R6", "R5", (0, "R3")),
            ("VEC_INSERT", "R7", "R6", (1, "R4")),
            ("HALT",)
        ],
        "enable_channel_kernel_recognition": True
    })

    # 10. Cost model and autotuning benchmark cases
    suite.append({
        "case_id": "cost_model_raw_vs_full_optimized",
        "description": "Cost model evaluation comparing raw vs full optimized ALU sequences",
        "program": [
            ("MOV", "R1", 100),
            ("MOV", "R2", 200),
            ("ADD", "R3", "R1", 10),
            ("XOR", "R4", "R2", 0xFF),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "cost_model_channel_dependency_vs_kernelized",
        "description": "Cost model evaluation comparing channel dependency vs kernelized patterns",
        "program": [
            ("LOAD_IMM", "R1", 42),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_RECV", "R2", 0),
            ("HALT",)
        ]
    })
    
    suite.append({
        "case_id": "cost_model_route_chain_rejection",
        "description": "Cost model rejects invalid route chain forms",
        "program": [
            ("WG_CHAN_ROUTE", 99, 0, 0xFF),  # Invalid destination channel (out of bounds)
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "cost_model_kernel_fanout_selection",
        "description": "Cost model handles kernel fanout pattern selection",
        "program": [
            ("LOAD_IMM", "R1", 50),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_RECV", "R2", 0),
            ("WG_CHAN_RECV", "R3", 0),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "autotune_strict_only_selects_raw",
        "description": "Autotune STRICT_ONLY policy selects raw strict mode",
        "program": [
            ("MOV", "R1", 10),
            ("ADD", "R2", "R1", 20),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "autotune_lowest_cycles_selects_safe_fastest",
        "description": "Autotune LOWEST_SIMULATED_CYCLES selects the fastest safe form",
        "program": [
            ("MOV", "R1", 10),
            ("MOV", "R2", 20),
            ("ADD", "R3", "R1", "R2"),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "autotune_lowest_trace_selects_smallest_trace",
        "description": "Autotune LOWEST_TRACE_FOOTPRINT selects the smallest safe trace form",
        "program": [
            ("MOV", "R1", 10),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "autotune_kernel_preferred_safe",
        "description": "Autotune KERNEL_PREFERRED_SAFE prefers channelized kernels if safe",
        "program": [
            ("LOAD_IMM", "R1", 30),
            ("WG_CHAN_SEND", 0, "R1"),
            ("WG_CHAN_RECV", "R2", 0),
            ("HALT",)
        ]
    })

    suite.append({
        "case_id": "autotune_disabled_matches_current_behavior",
        "description": "Autotune disabled mode preserves current behavior",
        "program": [
            ("MOV", "R1", 10),
            ("HALT",)
        ]
    })

    return suite

def run_waveguide_benchmark_case(
    case: Dict[str, Any],
    width: int
) -> Dict[str, Any]:
    """
    Executes a benchmark case across four optimization modes and compiles results.
    """
    program = case["program"]
    case_id = case["case_id"]
    description = case["description"]
    is_v1_case = case_id.startswith("v1_")
    v0_equiv_program = case.get("v0_equivalent_program")
    
    # Reference run for v1 cases to verify correctness against v0 equivalent
    raw_v0_equiv_report = None
    raw_v0_equiv_state = None
    if is_v1_case and v0_equiv_program:
        v0_state = build_waveguide_control_memory_state(width=width)
        v0_config = WaveguideControlMemoryBridgeConfig(
            width=width,
            optimization_profile="RAW_STRICT"
        )
        v0_config.enable_micro_isa_v1_candidates = False
        v0_config.micro_isa_version = "v0"
        try:
            raw_v0_equiv_report = execute_waveguide_control_memory_program(v0_equiv_program, v0_state, v0_config)
            raw_v0_equiv_state = {
                "success": raw_v0_equiv_report.success,
                "registers": dict(v0_state.registers),
                "flags": dict(v0_state.flags),
                "memory": dict(v0_state.memory.cells),
                "pc": v0_state.pc,
                "cycles": len(raw_v0_equiv_report.trace_steps)
            }
        except Exception as e:
            raw_v0_equiv_state = {
                "success": False,
                "error": str(e),
                "registers": {},
                "flags": {},
                "memory": {},
                "pc": 0,
                "cycles": 0
            }
            
    modes = {
        "raw_strict": {
            "optimization_profile": "RAW_STRICT",
        },
        "compacted_only": {
            "optimization_profile": "SAFE_LOCAL",
        },
        "scheduled_only": {
            "enable_branch_predication": False,
            "enable_pipeline_compaction": False,
            "enable_scoreboard_scheduling": True,
            "enable_memory_alias_analysis": False,
        },
        "compacted_and_scheduled": {
            "enable_branch_predication": False,
            "enable_pipeline_compaction": True,
            "enable_scoreboard_scheduling": True,
            "enable_memory_alias_analysis": False,
        },
        "predicated_only": {
            "enable_branch_predication": True,
            "enable_pipeline_compaction": False,
            "enable_scoreboard_scheduling": False,
            "enable_memory_alias_analysis": False,
        },
        "predicated_compacted_scheduled": {
            "optimization_profile": "SAFE_CONTROL",
        },
        "memory_alias_only": {
            "optimization_profile": "SAFE_MEMORY",
        },
        "full_optimized": {
            "optimization_profile": "FULL_SAFE_OPTIMIZED",
        }
    }
    
    mode_reports = {}
    
    for mode_name, config_flags in modes.items():
        state = build_waveguide_control_memory_state(width=width)
        profile_name = config_flags.get("optimization_profile")
        if profile_name:
            config = WaveguideControlMemoryBridgeConfig(
                width=width,
                optimization_profile=profile_name
            )
        else:
            config = WaveguideControlMemoryBridgeConfig(
                width=width,
                enable_branch_predication=config_flags["enable_branch_predication"],
                enable_pipeline_compaction=config_flags["enable_pipeline_compaction"],
                enable_scoreboard_scheduling=config_flags["enable_scoreboard_scheduling"],
                enable_memory_alias_analysis=config_flags.get("enable_memory_alias_analysis", False)
            )
            
        # Enable v1 candidates for all test modes in v1 cases
        if is_v1_case:
            config.enable_micro_isa_v1_candidates = True
            config.micro_isa_version = "v1"
            if (case_id.startswith("v1_wg_chan_") or case_id.startswith("v1_chan_") or case_id.startswith("v1_kernel_")) and case_id != "v1_wg_chan_disabled_rejected":
                config.enable_waveguide_channel_state = True
                if case_id != "v1_chan_dependency_disabled_matches_barrier_mode" and case_id != "v1_kernel_disabled_matches_channel_dependency_mode":
                    if config.enable_scoreboard_scheduling:
                        config.enable_channel_independence_analysis = True
                if case_id.startswith("v1_kernel_") and case_id != "v1_kernel_disabled_matches_channel_dependency_mode":
                    config.enable_channel_kernel_recognition = True
            
        try:
            report = execute_waveguide_control_memory_program(program, state, config)
            
            # Extract cycle count based on mode specifics
            if not report.success:
                cycles = 9999
            else:
                if mode_name == "raw_strict":
                    cycles = len(report.trace_steps)
                elif mode_name == "compacted_only":
                    savings = report.pipeline_compaction_report["cycle_savings"] if report.pipeline_compaction_report else 0
                    cycles = len(report.trace_steps) - savings
                elif mode_name in ("predicated_only", "memory_alias_only"):
                    savings = report.branch_predication_report["cycle_savings"] if report.branch_predication_report else 0
                    cycles = len(report.trace_steps) - savings
                elif mode_name in ("scheduled_only", "compacted_and_scheduled", "predicated_compacted_scheduled", "full_optimized"):
                    cycles = report.scoreboard_scheduler_report["scheduled_cycle_estimate"] if report.scoreboard_scheduler_report else len(report.trace_steps)
                    
            # Trace verification
            trace_ok = False
            trace_error = ""
            if report.success:
                program_len = len(report.trace_steps)
                if report.pass_manager_report and "raw_instruction_count" in report.pass_manager_report:
                    program_len = report.pass_manager_report["raw_instruction_count"]
                md_ok, md_err = validate_waveguide_trace_metadata(report.trace_steps, program_len, width, report.pass_manager_report)
                if not md_ok:
                    trace_error = f"Metadata validation failed: {md_err}"
                else:
                    rep_ok, rep_err, rep_state = replay_waveguide_execution_trace(
                        width, report.trace_steps,
                        enable_channel_independence_analysis=config.enable_channel_independence_analysis
                    )
                    if not rep_ok:
                        trace_error = f"Trace replay failed: {rep_err}"
                    else:
                        trace_ok = True
                        
            mode_reports[mode_name] = {
                "success": report.success,
                "cycles": cycles,
                "registers": dict(state.registers),
                "flags": dict(state.flags),
                "memory": dict(state.memory.cells),
                "pc": state.pc,
                "trace_len": len(report.trace_steps),
                "trace_valid": trace_ok,
                "trace_error": trace_error,
                "profile_id": report.pass_manager_report.get("profile_id") if report.pass_manager_report else "CUSTOM",
                "pass_manager_report": report.pass_manager_report
            }
        except TimeoutError:
            mode_reports[mode_name] = {
                "success": False,
                "error": "TimeoutError",
                "cycles": 0,
                "registers": {},
                "flags": {},
                "memory": {},
                "pc": 0,
                "trace_len": 0,
                "trace_valid": False,
                "trace_error": "TimeoutError occurred"
            }
        except Exception as e:
            mode_reports[mode_name] = {
                "success": False,
                "error": str(e),
                "cycles": 0,
                "registers": {},
                "flags": {},
                "memory": {},
                "pc": 0,
                "trace_len": 0,
                "trace_valid": False,
                "trace_error": f"Exception raised: {str(e)}"
            }
            
    # Check semantic equivalence across successful runs
    equivalence = {
        "compacted_only": True,
        "scheduled_only": True,
        "compacted_and_scheduled": True,
        "predicated_only": True,
        "predicated_compacted_scheduled": True,
        "memory_alias_only": True,
        "full_optimized": True
    }
    cycle_savings = {
        "compacted_only": 0,
        "scheduled_only": 0,
        "compacted_and_scheduled": 0,
        "predicated_only": 0,
        "predicated_compacted_scheduled": 0,
        "memory_alias_only": 0,
        "full_optimized": 0
    }
    skipped_optimizations = []
    
    # Reference states
    ref_success = False
    ref_regs = {}
    ref_flags = {}
    ref_mem = {}
    ref_pc = 0
    ref_cycles = 0
    ref_error = None
    
    if is_v1_case and raw_v0_equiv_state is not None and not (case_id.startswith("v1_wg_chan_") or case_id.startswith("v1_chan_") or case_id.startswith("v1_kernel_")):
        ref_success = raw_v0_equiv_state["success"]
        ref_regs = raw_v0_equiv_state.get("registers", {})
        ref_flags = raw_v0_equiv_state.get("flags", {})
        ref_mem = raw_v0_equiv_state.get("memory", {})
        ref_pc = raw_v0_equiv_state.get("pc", 0)
        ref_cycles = raw_v0_equiv_state.get("cycles", 0)
        ref_error = raw_v0_equiv_state.get("error")
    else:
        raw = mode_reports.get("raw_strict", {})
        ref_success = raw.get("success", False)
        ref_regs = raw.get("registers", {})
        ref_flags = raw.get("flags", {})
        ref_mem = raw.get("memory", {})
        ref_pc = raw.get("pc", 0)
        ref_cycles = raw.get("cycles", 0)
        ref_error = raw.get("error")

    if ref_success:
        # If it's a v1 case, check raw_strict equivalence against reference
        if is_v1_case:
            raw_target = mode_reports.get("raw_strict", {})
            if not raw_target.get("success", False):
                for mode in equivalence:
                    equivalence[mode] = False
            else:
                raw_eq = (
                    raw_target["registers"] == ref_regs and
                    raw_target["flags"] == ref_flags and
                    raw_target["memory"] == ref_mem and
                    raw_target["pc"] == ref_pc
                )
                if not raw_eq:
                    for mode in equivalence:
                        equivalence[mode] = False
                        
        # Now check all optimization modes against reference state
        for mode in ("compacted_only", "scheduled_only", "compacted_and_scheduled", "predicated_only", "predicated_compacted_scheduled", "memory_alias_only", "full_optimized"):
            if is_v1_case and not equivalence[mode]:
                continue
                
            target = mode_reports.get(mode, {})
            if not target.get("success", False):
                if target.get("error") == "TimeoutError" and ref_error == "TimeoutError":
                    equivalence[mode] = True
                else:
                    equivalence[mode] = False
            else:
                eq_reg = (ref_regs == target["registers"])
                eq_flag = (ref_flags == target["flags"])
                eq_mem = (ref_mem == target["memory"])
                eq_pc = (ref_pc == target["pc"])
                
                is_eq = eq_reg and eq_flag and eq_mem and eq_pc
                equivalence[mode] = is_eq
                
                raw_c = mode_reports.get("raw_strict", {}).get("cycles", ref_cycles)
                cycle_savings[mode] = max(0, raw_c - target["cycles"])
    else:
        for mode in ("compacted_only", "scheduled_only", "compacted_and_scheduled", "predicated_only", "predicated_compacted_scheduled", "memory_alias_only", "full_optimized"):
            target = mode_reports.get(mode, {})
            if not target.get("success", False):
                equivalence[mode] = True
            else:
                equivalence[mode] = False
                
    # Detect dynamic barriers or skipped optimizations
    if "barrier" in case_id or "uncompactable" in case_id:
        skipped_optimizations.append("expected barrier block")
        
    trace_metadata_present = all(r.get("trace_valid", False) for r in mode_reports.values() if r.get("success", False))
    
    res = {
        "case_id": case_id,
        "description": description,
        "bit_width": width,
        "modes": mode_reports,
        "equivalence": equivalence,
        "cycle_savings": cycle_savings,
        "skipped_optimizations": skipped_optimizations,
        "trace_metadata_present": trace_metadata_present
    }
    
    if is_v1_case:
        candidate_opcode = None
        from sol_micro_isa_v1_candidates import V1_CANDIDATE_OPCODES
        for inst in program:
            op = None
            if isinstance(inst, (tuple, list)) and len(inst) > 0 and isinstance(inst[0], str):
                op = inst[0].upper()
            elif hasattr(inst, "op") and isinstance(inst.op, str):
                op = inst.op.upper()
            if op and op in V1_CANDIDATE_OPCODES:
                candidate_opcode = op
                break
                
        lowering_strategy = "unknown"
        pm_rep = mode_reports.get("raw_strict", {}).get("pass_manager_report")
        if pm_rep and pm_rep.get("v1_lowering_metadata"):
            for m in pm_rep["v1_lowering_metadata"]:
                if m.get("lowering_strategy"):
                    lowering_strategy = m["lowering_strategy"]
                    break
                    
        res["v1_details"] = {
            "v1_candidate_case_id": case_id,
            "candidate_opcode": candidate_opcode,
            "equivalent_v0_reference_case": case_id + "_v0_equiv",
            "lowering_strategy": lowering_strategy,
            "trace_replay_verdict": "pass" if trace_metadata_present else "fail",
            "cycle_comparison": {
                "v0_equivalent_raw": ref_cycles,
                "v1_lowered_raw": mode_reports.get("raw_strict", {}).get("cycles", 0),
                "v1_lowered_full_optimized": mode_reports.get("full_optimized", {}).get("cycles", 0)
            }
        }
        
    return res

def run_waveguide_optimization_matrix(
    widths: List[int] = [32, 64]
) -> Dict[str, Any]:
    """
    Runs the complete optimization benchmark suite across specified widths.
    """
    matrix_report = {
        "widths": widths,
        "cases": []
    }
    
    for w in widths:
        suite = build_waveguide_benchmark_suite(w)
        for case in suite:
            case_rep = run_waveguide_benchmark_case(case, w)
            matrix_report["cases"].append(case_rep)
            
    return matrix_report

def summarize_waveguide_benchmark_report(
    matrix_report: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Serializes and aggregates benchmark report results.
    """
    total_cases = len(matrix_report["cases"])
    equivalent_count = 0
    total_savings_compacted = 0
    total_savings_scheduled = 0
    total_savings_combined = 0
    total_savings_predicated = 0
    total_savings_full = 0
    total_savings_memory = 0
    total_savings_full_opt = 0
    
    cases_summary = []
    
    for c in matrix_report["cases"]:
        modes = c["modes"]
        eq = c["equivalence"]
        savings = c["cycle_savings"]
        
        all_eq = all(eq.values())
        if all_eq:
            equivalent_count += 1
            
        total_savings_compacted += savings.get("compacted_only", 0)
        total_savings_scheduled += savings.get("scheduled_only", 0)
        total_savings_combined += savings.get("compacted_and_scheduled", 0)
        total_savings_predicated += savings.get("predicated_only", 0)
        total_savings_full += savings.get("predicated_compacted_scheduled", 0)
        total_savings_memory += savings.get("memory_alias_only", 0)
        total_savings_full_opt += savings.get("full_optimized", 0)
        
        entry = {
            "case_id": c["case_id"],
            "bit_width": c["bit_width"],
            "all_modes_semantically_equivalent": all_eq,
            "raw_cycles": modes.get("raw_strict", {}).get("cycles", 0),
            "compacted_cycles": modes.get("compacted_only", {}).get("cycles", 0),
            "scheduled_cycles": modes.get("scheduled_only", {}).get("cycles", 0),
            "combined_cycles": modes.get("compacted_and_scheduled", {}).get("cycles", 0),
            "predicated_cycles": modes.get("predicated_only", {}).get("cycles", 0),
            "full_opt_cycles": modes.get("predicated_compacted_scheduled", {}).get("cycles", 0),
            "memory_alias_cycles": modes.get("memory_alias_only", {}).get("cycles", 0),
            "full_optimized_cycles": modes.get("full_optimized", {}).get("cycles", 0),
            "cycle_savings": savings,
            "trace_metadata_present": c["trace_metadata_present"]
        }
        if "v1_details" in c:
            entry["v1_details"] = c["v1_details"]
        cases_summary.append(entry)
        
    return {
        "total_cases_run": total_cases,
        "all_modes_verified_equivalent": equivalent_count == total_cases,
        "equivalent_cases_count": equivalent_count,
        "aggregated_cycle_savings": {
            "compacted_only": total_savings_compacted,
            "scheduled_only": total_savings_scheduled,
            "compacted_and_scheduled": total_savings_combined,
            "predicated_only": total_savings_predicated,
            "predicated_compacted_scheduled": total_savings_full,
            "memory_alias_only": total_savings_memory,
            "full_optimized": total_savings_full_opt
        },
        "cases": cases_summary
    }

def export_waveguide_benchmark_report(
    matrix_report: Dict[str, Any],
    filepath: str
) -> None:
    """
    Exports matrix report to a JSON file.
    """
    with open(filepath, "w") as f:
        json.dump(matrix_report, f, indent=4)

def run_waveguide_optimization_matrix_batch(
    cases: List[Dict[str, Any]],
    acceleration_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates benchmark cases across widths in a batch, using simulation acceleration if enabled.
    """
    from sol_waveguide_simulation_acceleration import (
        build_waveguide_acceleration_config,
        run_waveguide_benchmark_batch_serial,
        run_waveguide_benchmark_batch_accelerated,
        summarize_waveguide_acceleration_report,
        validate_waveguide_acceleration_equivalence
    )
    
    cfg = acceleration_config if acceleration_config else build_waveguide_acceleration_config()
    
    def run_single(item: Dict[str, Any]) -> Dict[str, Any]:
        case = item["case"]
        width = item["width"]
        res = run_waveguide_benchmark_case(case, width)
        return res

    serial_results = run_waveguide_benchmark_batch_serial(cases, run_single)
    
    parallel_used = False
    workers = 1
    if cfg.get("enable_offline_benchmark_parallelism", False):
        workers = cfg.get("max_workers", 1)
        if workers > 1:
            parallel_used = True
            accel_results = run_waveguide_benchmark_batch_accelerated(cases, run_single, max_workers=workers)
            eq = validate_waveguide_acceleration_equivalence(serial_results, accel_results)
            if not eq:
                raise ValueError("Serial and Accelerated benchmark results are not equivalent!")
            results = accel_results
        else:
            results = serial_results
    else:
        results = serial_results
        
    if cfg.get("deterministic_result_ordering", True):
        results.sort(key=lambda x: (x["case_id"], x["bit_width"]))
        
    accel_report = summarize_waveguide_acceleration_report(cfg, "offline_benchmark_batch")
    
    return {
        "success": True,
        "cases": results,
        "acceleration_metadata": accel_report
    }
