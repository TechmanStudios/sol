#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL LogosVM Loop & State-Machine Verification (Level 6: Basic Software)
=======================================================================
Verifies a 2-pass dynamic loop where register battery states (A and B)
control iteration execution.
"""

import sys
import os
import json
from pathlib import Path

# Add project root and scratch paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer
)
from test_logos_vm import LogosVM, build_group

def run_loop_program() -> list[dict]:
    group = build_group()
    
    # Prime inputs: A and B both active (representing 2 loop iterations)
    group.prime_basin("Basin_A", active=True)
    group.prime_basin("Basin_B", active=True)
    group.prime_basin("Basin_Cin", active=False)
    group.prime_basin("Basin_SUM", active=False)
    
    # Prime registers to clean default state
    group.prime_register('A', active=False)
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    
    sequencer = MicroInstructionSequencer(group)
    vm = LogosVM(sequencer)
    
    # Loop program:
    # 1. Load active Basin_A -> Register A, active Basin_B -> Register B.
    # 2. Start loop checking:
    #    - If A is active, jump to ITER_1.
    #    - If B is active, jump to ITER_2.
    #    - Else jump to LOOP_EXIT.
    # 3. ITER_1: Increment C (by running OR on it), clear A, jump back to start.
    # 4. ITER_2: Increment C again (by running OR on it), clear B, jump back to start.
    program = [
        Instruction("LOAD", ['A', "Basin_A"]),          # Load loop counter 1
        Instruction("LOAD", ['B', "Basin_B"]),          # Load loop counter 2
        
        Instruction("LABEL", ["LOOP_START"]),
        Instruction("JUMP_IF_ACTIVE", ['A', "ITER_1"]),
        Instruction("JUMP_IF_ACTIVE", ['B', "ITER_2"]),
        Instruction("JUMP", ["LOOP_EXIT"]),
        
        Instruction("LABEL", ["ITER_1"]),
        Instruction("OR_MS", ['C']),                    # Simulate loop body work on C
        Instruction("CLEAR", ['A']),                    # Clear counter 1
        Instruction("JUMP", ["LOOP_START"]),
        
        Instruction("LABEL", ["ITER_2"]),
        Instruction("OR_MS", ['C']),                    # Simulate loop body work on C
        Instruction("CLEAR", ['B']),                    # Clear counter 2
        Instruction("JUMP", ["LOOP_START"]),
        
        Instruction("LABEL", ["LOOP_EXIT"]),
        Instruction("STORE", ['C', "Basin_SUM"])
    ]
    
    history = vm.run(program)
    return history

def evaluate_loop() -> tuple[dict, bool]:
    print("==========================================================================")
    print("  SOL LOGOSVM DYNAMIC LOOPING VERIFICATION SUITE")
    print("==========================================================================")
    
    history = run_loop_program()
    
    # Let's verify the execution trajectory:
    # Initial: A = 1, B = 1, C = -1
    # Iter 1: Jumps to ITER_1, runs OR_MS on C (C becomes 1), clears A (A becomes -1)
    # Iter 2: Jumps to ITER_2, runs OR_MS on C (C remains 1), clears B (B becomes -1)
    # Iter 3: Jumps to LOOP_EXIT, stores C -> Basin_SUM (SUM becomes 1)
    
    # Let's check history states:
    # We want to verify that at the end of execution:
    # - Register A and B are collapsed (-1.0)
    # - Basin_SUM is active (1.0)
    got_sum = history[-1]["basin_d_state"]
    reg_a_final = history[-1]["reg_a_state"]
    reg_b_final = history[-1]["reg_b_state"]
    
    passed_logical = (got_sum == 1)
    counters_collapsed = (reg_a_final == -1.0) and (reg_b_final == -1.0)
    
    passed = passed_logical and counters_collapsed
    
    print(f"  Got Basin_SUM State: {got_sum} | Expected: 1 | Status: {'OK' if passed_logical else 'FAIL'}")
    print(f"  Final Register A State: {reg_a_final} | Expected: -1.0 | Status: {'OK' if reg_a_final == -1.0 else 'FAIL'}")
    print(f"  Final Register B State: {reg_b_final} | Expected: -1.0 | Status: {'OK' if reg_b_final == -1.0 else 'FAIL'}")
    print(f"\n  Loop Verdict: {'PASSED' if passed else 'FAILED'}")
    
    result_data = {
        "expected_sum": 1,
        "got_sum": got_sum,
        "reg_a_final": reg_a_final,
        "reg_b_final": reg_b_final,
        "passed": passed
    }
    
    return result_data, passed

def write_reports(report_data: dict, suite_passed: bool):
    report_dir = sol_root / "solResearch" / "nextBestTest"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON raw results
    json_path = report_dir / "logos_vm_loop_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
        
    # Generate MD report
    report_md = [
        "# SOL LogosVM Loop Verification Report",
        "",
        "This report verifies the execution of register-state-driven counter loops on the Level 6 basic software VM runtime.",
        "",
        "## 1. Experimental Verdict",
        "",
        f"**Overall Suite Status**: **{'PASSED' if suite_passed else 'FAILED'}**",
        "",
        "## 2. Loop Execution Measurements",
        "",
        "| Metric | Expected Value | Got Value | Status |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Basin SUM State** | `1` | `{report_data['got_sum']}` | {'OK' if report_data['got_sum'] == 1 else 'FAIL'} |",
        f"| **Register A State** | `-1.0` | `{report_data['reg_a_final']}` | {'OK' if report_data['reg_a_final'] == -1.0 else 'FAIL'} |",
        f"| **Register B State** | `-1.0` | `{report_data['reg_b_final']}` | {'OK' if report_data['reg_b_final'] == -1.0 else 'FAIL'} |",
        "",
        "## 3. Analysis & Key Observations",
        "- **Register-Driven State Machines**: Using register battery states as active conditional flags enables writing standard assembly-like loops in the SOL basic software layer.",
        "- **Autonomic Counter Decrement**: Executing `CLEAR` instructions on the registers inside the loop body acts as a decrement operator, collapsing the conditional jump flag and cleanly terminating the loop."
    ]
    
    md_path = report_dir / "logos_vm_loop_report.md"
    md_path.write_text("\n".join(report_md) + "\n", encoding="utf-8")
    
    print(f"\nRaw results saved to: {json_path}")
    print(f"MD report generated at: {md_path}")

if __name__ == "__main__":
    report_data, passed = evaluate_loop()
    write_reports(report_data, passed)
    if passed:
        print("\nLogosVM Loop Verification: ALL PASSED!")
        sys.exit(0)
    else:
        print("\nLogosVM Loop Verification: FAILED.")
        sys.exit(1)
