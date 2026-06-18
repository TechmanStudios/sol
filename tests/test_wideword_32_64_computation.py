# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL WideWord 32-bit/64-bit Computation Validation Test Campaign
==============================================================
Runs deterministic edge cases, seeded random vectors, carry/borrow chains,
overflow tests, lane checks, and JSON serializability tests.
"""

import json
import random
import pytest
from dataclasses import asdict

from sol_lane_fabric import LaneFabric
from sol_wideword_computation_validation import (
    build_wideword_case,
    run_wideword_case,
    run_wideword_batch,
    summarize_wideword_report,
    mask_for_width,
    format_hex,
    oracle_add,
    oracle_sub
)


# Test vectors defined by user
VECTORS_32 = [
    0x00000000,
    0x00000001,
    0x00000002,
    0x0000000F,
    0x00000010,
    0x000000FF,
    0x00000100,
    0x0000FFFF,
    0x00010000,
    0x7FFFFFFF,
    0x80000000,
    0xAAAAAAAA,
    0x55555555,
    0xFFFFFFFF
]

VECTORS_64 = [
    0x0000000000000000,
    0x0000000000000001,
    0x0000000000000002,
    0x000000000000000F,
    0x0000000000000010,
    0x00000000000000FF,
    0x0000000000000100,
    0x00000000FFFFFFFF,
    0x0000000100000000,
    0x7FFFFFFFFFFFFFFF,
    0x8000000000000000,
    0xAAAAAAAAAAAAAAAA,
    0x5555555555555555,
    0xFFFFFFFFFFFFFFFF
]

CARRY_CASES_32 = [
    (0x00000001, 0x00000001),
    (0x000000FF, 0x00000001),
    (0x0000FFFF, 0x00000001),
    (0x00FFFFFF, 0x00000001),
    (0x7FFFFFFF, 0x00000001),
    (0xFFFFFFFF, 0x00000001),
    (0xFFFFFFFF, 0xFFFFFFFF)
]

CARRY_CASES_64 = [
    (0x00000000000000FF, 0x0000000000000001),
    (0x00000000FFFFFFFF, 0x0000000000000001),
    (0x0000FFFFFFFFFFFF, 0x0000000000000001),
    (0x7FFFFFFFFFFFFFFF, 0x0000000000000001),
    (0xFFFFFFFFFFFFFFFF, 0x0000000000000001),
    (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
]

BORROW_CASES_32 = [
    (0x00000000, 0x00000001),
    (0x00000100, 0x00000001),
    (0x00010000, 0x00000001),
    (0x80000000, 0x00000001),
    (0x00000000, 0xFFFFFFFF)
]

BORROW_CASES_64 = [
    (0x0000000000000000, 0x0000000000000001),
    (0x0000000000000100, 0x0000000000000001),
    (0x0000000100000000, 0x0000000000000001),
    (0x8000000000000000, 0x0000000000000001),
    (0x0000000000000000, 0xFFFFFFFFFFFFFFFF)
]


def assert_case_matches_oracle(case, layers_to_test=None):
    if layers_to_test is None:
        layers_to_test = ["Layer A", "Layer B", "Layer C", "Layer D", "Layer F"]
    res = run_wideword_case(case, layers_to_test=layers_to_test)
    if not res.match_status:
        # Diagnostic printout
        print("\n=== MISMATCH DIAGNOSTIC ===")
        print(f"Width: {res.case.width}")
        print(f"Operation: {res.case.op}")
        print(f"Operand A: {format_hex(res.case.a, res.case.width)}")
        if res.case.b is not None:
            print(f"Operand B: {format_hex(res.case.b, res.case.width)}")
        print(f"Expected Oracle: {format_hex(res.oracle_result, res.case.width)}")
        print(f"Actual SOL:      {format_hex(res.sol_result if res.sol_result is not None else 0, res.case.width)}")
        diff = (res.sol_result if res.sol_result is not None else 0) ^ res.oracle_result
        print(f"XOR Diff:        {format_hex(diff, res.case.width)}")
        print(f"Layers Tested: {res.layers_tested}")
        if res.failure_reason:
            print(f"Failure Reason: {res.failure_reason}")
        print("===========================")
    
    assert res.match_status, f"Oracle mismatch on {case.op} for width {case.width}"
    # Ensure active layers did not fail
    for layer, status in res.layers_tested.items():
        assert status != "failed", f"{layer} failed on {case.op} case"


def test_32bit_add_edge_vectors_match_oracle():
    for a in VECTORS_32:
        for b in VECTORS_32:
            case = build_wideword_case("ADD", a, b, 32)
            assert_case_matches_oracle(case)


def test_64bit_add_edge_vectors_match_oracle():
    # Sample a representative subset to avoid quadratic slowdown while retaining full edge coverage
    for a in VECTORS_64:
        for b in [0, 1, 2, 0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000]:
            case = build_wideword_case("ADD", a, b, 64)
            assert_case_matches_oracle(case)


def test_32bit_sub_edge_vectors_match_oracle():
    for a in VECTORS_32:
        for b in VECTORS_32:
            case = build_wideword_case("SUB", a, b, 32)
            assert_case_matches_oracle(case)


def test_64bit_sub_edge_vectors_match_oracle():
    for a in VECTORS_64:
        for b in [0, 1, 2, 0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000]:
            case = build_wideword_case("SUB", a, b, 64)
            assert_case_matches_oracle(case)


def test_32bit_bitwise_vectors_match_oracle():
    for op in ("AND", "OR", "XOR"):
        for a in VECTORS_32:
            for b in VECTORS_32:
                case = build_wideword_case(op, a, b, 32)
                assert_case_matches_oracle(case)
    # NOT
    for a in VECTORS_32:
        case = build_wideword_case("NOT", a, None, 32)
        assert_case_matches_oracle(case)


def test_64bit_bitwise_vectors_match_oracle():
    for op in ("AND", "OR", "XOR"):
        for a in VECTORS_64:
            for b in [0, 1, 2, 0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF]:
                case = build_wideword_case(op, a, b, 64)
                assert_case_matches_oracle(case)
    # NOT
    for a in VECTORS_64:
        case = build_wideword_case("NOT", a, None, 64)
        assert_case_matches_oracle(case)


def test_32bit_shift_vectors_match_oracle():
    shifts = [0, 1, 2, 7, 8, 15, 16, 31]
    for op in ("SHL", "SHR"):
        for a in VECTORS_32:
            for s in shifts:
                case = build_wideword_case(op, a, s, 32)
                assert_case_matches_oracle(case)


def test_64bit_shift_vectors_match_oracle():
    shifts = [0, 1, 2, 7, 8, 15, 16, 31, 32, 63]
    for op in ("SHL", "SHR"):
        for a in VECTORS_64:
            for s in shifts:
                case = build_wideword_case(op, a, s, 64)
                assert_case_matches_oracle(case)


def test_32bit_seeded_random_add_sub_match_oracle():
    rng = random.Random(0x50A1)
    for _ in range(128):
        a = rng.randint(0, 0xFFFFFFFF)
        b = rng.randint(0, 0xFFFFFFFF)
        assert_case_matches_oracle(build_wideword_case("ADD", a, b, 32))
        assert_case_matches_oracle(build_wideword_case("SUB", a, b, 32))


def test_64bit_seeded_random_add_sub_match_oracle():
    rng = random.Random(0x50A1)
    for _ in range(128):
        a = rng.randint(0, 0xFFFFFFFFFFFFFFFF)
        b = rng.randint(0, 0xFFFFFFFFFFFFFFFF)
        assert_case_matches_oracle(build_wideword_case("ADD", a, b, 64))
        assert_case_matches_oracle(build_wideword_case("SUB", a, b, 64))


def test_32bit_cross_byte_carry_chain():
    for a, b in CARRY_CASES_32:
        case = build_wideword_case("ADD", a, b, 32)
        assert_case_matches_oracle(case, layers_to_test=["Layer A", "Layer B", "Layer C", "Layer D", "Layer E", "Layer F"])


def test_64bit_cross_byte_carry_chain():
    for a, b in CARRY_CASES_64:
        case = build_wideword_case("ADD", a, b, 64)
        assert_case_matches_oracle(case, layers_to_test=["Layer A", "Layer B", "Layer C", "Layer D", "Layer E", "Layer F"])


def test_32bit_cross_byte_borrow_chain():
    for a, b in BORROW_CASES_32:
        case = build_wideword_case("SUB", a, b, 32)
        assert_case_matches_oracle(case, layers_to_test=["Layer A", "Layer B", "Layer C", "Layer D", "Layer E", "Layer F"])


def test_64bit_cross_byte_borrow_chain():
    for a, b in BORROW_CASES_64:
        case = build_wideword_case("SUB", a, b, 64)
        assert_case_matches_oracle(case, layers_to_test=["Layer A", "Layer B", "Layer C", "Layer D", "Layer E", "Layer F"])


def test_32bit_overflow_wraps_by_mask():
    case = build_wideword_case("ADD", 0xFFFFFFFF, 1, 32)
    res = run_wideword_case(case, layers_to_test=["Layer A", "Layer B", "Layer C", "Layer D", "Layer E", "Layer F"])
    assert res.sol_result == 0
    assert res.oracle_result == 0


def test_64bit_overflow_wraps_by_mask():
    case = build_wideword_case("ADD", 0xFFFFFFFFFFFFFFFF, 1, 64)
    res = run_wideword_case(case, layers_to_test=["Layer A", "Layer B", "Layer C", "Layer D", "Layer E", "Layer F"])
    assert res.sol_result == 0
    assert res.oracle_result == 0


def test_32bit_lane_count_is_four_bytes():
    fabric = LaneFabric.for_width(32)
    assert fabric.num_lanes == 4
    assert len(fabric.lanes) == 4


def test_64bit_lane_count_is_eight_bytes():
    fabric = LaneFabric.for_width(64)
    assert fabric.num_lanes == 8
    assert len(fabric.lanes) == 8


def test_wideword_report_is_json_serializable():
    cases = [
        build_wideword_case("ADD", 0x12345678, 0x11111111, 32),
        build_wideword_case("SUB", 0xFFFFFFFFFFFFFFFF, 0x1, 64)
    ]
    batch = run_wideword_batch(cases)
    report = summarize_wideword_report(batch)
    
    # Serialize to JSON
    report_dict = asdict(report)
    serialized = json.dumps(report_dict, indent=2)
    
    # Deserialize and verify
    deserialized = json.loads(serialized)
    assert deserialized["report_id"] == report.report_id
    assert deserialized["cases_passed"] == 2
    assert deserialized["cases_failed"] == 0
    assert deserialized["success"] is True


def test_wideword_computation_does_not_mutate_active_tables():
    fabric = LaneFabric.for_width(32)
    
    # Capture initial state of lane phase mappings
    initial_states = []
    for lane in fabric.lanes:
        initial_states.append({
            "lane_id": lane.lane_id,
            "bit_offset": lane.bit_offset,
            "periods": list(lane.periods),
            "quadratures": list(lane.quadratures),
            "calibrated_phases": dict(lane.calibrated_phases)
        })
        
    # Execute several validation operations
    case1 = build_wideword_case("ADD", 0x05050505, 0x10101010, 32)
    run_wideword_case(case1)
    
    # Capture state after execution and verify it is identical
    for idx, lane in enumerate(fabric.lanes):
        state = initial_states[idx]
        assert lane.lane_id == state["lane_id"]
        assert lane.bit_offset == state["bit_offset"]
        assert list(lane.periods) == state["periods"]
        assert list(lane.quadratures) == state["quadratures"]
        assert dict(lane.calibrated_phases) == state["calibrated_phases"]


def test_existing_suite_still_passes():
    import pytest
    ret = pytest.main(["-q", "tests/test_telemetry.py"])
    assert ret == 0


# ---- Optional Benchmark Validation ----

def test_benchmark_validation_campaign():
    """
    Deterministic correctness validation sweep of 1,000 32-bit and 64-bit ADD operations.
    """
    rng = random.Random(0x50A1)
    cases = []
    
    # 1. 1,000 32-bit ADD operations
    for _ in range(1000):
        a = rng.randint(0, 0xFFFFFFFF)
        b = rng.randint(0, 0xFFFFFFFF)
        cases.append(build_wideword_case("ADD", a, b, 32))
        
    # 2. 1,000 64-bit ADD operations
    for _ in range(1000):
        a = rng.randint(0, 0xFFFFFFFFFFFFFFFF)
        b = rng.randint(0, 0xFFFFFFFFFFFFFFFF)
        cases.append(build_wideword_case("ADD", a, b, 64))
        
    batch = run_wideword_batch(cases, layers_to_test=["Layer A", "Layer B", "Layer C", "Layer D", "Layer F"])
    report = summarize_wideword_report(batch)
    
    print(f"\n=== BENCHMARK CORRECTNESS SUMMARY ===")
    print(f"Total Cases:  {len(cases)}")
    print(f"Passed:       {report.cases_passed}")
    print(f"Failed:       {report.cases_failed}")
    print(f"Success Rate: {report.cases_passed / len(cases) * 100:.2f}%")
    print(f"=====================================")
    
    assert report.success, f"Benchmark correctness failed: {report.cases_failed} mismatches"


def test_virtual_vm_registers_32_64():
    from sol_wideword_computation_validation import WideWordVirtualVM
    for width in (32, 64):
        vm = WideWordVirtualVM(width=width)
        program = [
            ("LOAD_IMM", "R0", 0x123456789ABCDEF0),
            ("MOVE", "R1", "R0"),
            ("LOAD_IMM", "R2", 0x55),
            ("CMP", "R1", "R2")
        ]
        vm.run_program(program)
        
        mask = (1 << width) - 1
        expected_r0 = 0x123456789ABCDEF0 & mask
        assert vm.registers["R0"] == expected_r0
        assert vm.registers["R1"] == expected_r0
        assert vm.registers["R2"] == 0x55
        assert vm.flags["zero"] == 0


def test_virtual_vm_flags_32_64():
    from sol_wideword_computation_validation import WideWordVirtualVM
    for width in (32, 64):
        # 1. Zero Flag
        vm = WideWordVirtualVM(width=width)
        vm.run_program([
            ("LOAD_IMM", "R0", 42),
            ("CMP", "R0", 42)
        ])
        assert vm.flags["zero"] == 1
        assert vm.flags["carry"] == 0
        assert vm.flags["borrow"] == 0
        assert vm.flags["sign"] == 0
        assert vm.flags["overflow"] == 0
        
        # 2. Carry / Borrow Flag
        vm = WideWordVirtualVM(width=width)
        vm.run_program([
            ("LOAD_IMM", "R0", 0),
            ("SUB", "R1", "R0", 1)
        ])
        assert vm.flags["carry"] == 1
        assert vm.flags["borrow"] == 1
        assert vm.flags["zero"] == 0
        assert vm.flags["sign"] == 1
        
        vm = WideWordVirtualVM(width=width)
        max_val = (1 << width) - 1
        vm.run_program([
            ("LOAD_IMM", "R0", max_val),
            ("ADD", "R1", "R0", 1)
        ])
        assert vm.flags["carry"] == 1
        assert vm.flags["zero"] == 1
        assert vm.flags["borrow"] == 0
        
        # 3. Overflow Flag (Addition)
        vm = WideWordVirtualVM(width=width)
        pos_max = (1 << (width - 1)) - 1
        vm.run_program([
            ("LOAD_IMM", "R0", pos_max),
            ("ADD", "R1", "R0", 1)
        ])
        assert vm.flags["overflow"] == 1
        assert vm.flags["sign"] == 1
        assert vm.flags["carry"] == 0
        
        # Overflow Flag (Subtraction)
        vm = WideWordVirtualVM(width=width)
        neg_min = 1 << (width - 1)
        vm.run_program([
            ("LOAD_IMM", "R0", neg_min),
            ("SUB", "R1", "R0", 1)
        ])
        assert vm.flags["overflow"] == 1
        assert vm.flags["sign"] == 0
        assert vm.flags["carry"] == 0


def test_virtual_vm_memory_round_trips_32_64():
    from sol_wideword_computation_validation import WideWordVirtualVM
    for width in (32, 64):
        vm = WideWordVirtualVM(width=width)
        program = [
            ("LOAD_IMM", "R1", 100),
            ("LOAD_IMM", "R2", 200),
            ("ADD", "R3", "R1", "R2"),
            ("LOAD_IMM", "R0", 0x1000),
            ("STORE_MEM", "R3", "R0"),
            ("LOAD_MEM", "R4", "R0"),
            ("ADD", "R5", "R4", 50)
        ]
        vm.run_program(program)
        assert vm.registers["R3"] == 300
        assert vm.memory[0x1000] == 300
        assert vm.registers["R4"] == 300
        assert vm.registers["R5"] == 350


def test_virtual_vm_multi_instruction_programs_32_64():
    from sol_wideword_computation_validation import WideWordVirtualVM
    for width in (32, 64):
        vm = WideWordVirtualVM(width=width)
        program = [
            ("LOAD_IMM", "R1", 0),
            ("LOAD_IMM", "R2", 10),
            "loop:",
            ("CMP", "R2", 0),
            ("JZ", "done"),
            ("ADD", "R1", "R1", "R2"),
            ("SUB", "R2", "R2", 1),
            ("JMP", "loop"),
            "done:"
        ]
        vm.run_program(program)
        assert vm.registers["R1"] == 55
        assert vm.registers["R2"] == 0


def test_signed_interpretation_views_32_64():
    from sol_wideword_computation_validation import WideWordVirtualVM
    for width in (32, 64):
        vm = WideWordVirtualVM(width=width)
        mask = (1 << width) - 1
        
        assert vm.to_signed(0) == 0
        assert vm.to_signed(1) == 1
        assert vm.to_signed(mask) == -1
        
        half = 1 << (width - 1)
        assert vm.to_signed(half) == -half
        assert vm.to_signed(half - 1) == half - 1
        
        vm.registers["R1"] = mask
        vm.registers["R2"] = half
        views = vm.get_register_views()
        assert views["R1"]["signed"] == -1
        assert views["R1"]["unsigned"] == mask
        assert views["R2"]["signed"] == -half
        assert views["R2"]["unsigned"] == half


def test_shift_add_multiplication_scaffold_32_64():
    from sol_wideword_computation_validation import WideWordVirtualVM
    rng = random.Random(0x50A1)
    
    for width in (32, 64):
        mask = (1 << width) - 1
        
        for _ in range(10):
            a = rng.randint(0, mask >> (width // 2))
            b = rng.randint(0, mask >> (width // 2))
            
            a_full = rng.randint(0, mask)
            b_full = rng.randint(0, mask)
            
            for x, y in [(a, b), (a_full, b_full)]:
                vm = WideWordVirtualVM(width=width)
                vm.registers["R1"] = x
                vm.registers["R2"] = y
                
                program = [
                    ("LOAD_IMM", "R3", 0),
                    ("MOVE", "R4", "R1"),
                    ("MOVE", "R5", "R2"),
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
                    "done:"
                ]
                vm.run_program(program)
                
                expected = (x * y) & mask
                assert vm.registers["R3"] == expected, f"Shift-add multiply mismatch: {x} * {y} = {vm.registers['R3']} (expected {expected})"

