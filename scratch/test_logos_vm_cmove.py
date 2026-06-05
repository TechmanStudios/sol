#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL LogosVM Conditional Move & Gated Assignment Verification (Level 6: Basic Software)
=====================================================================================
Verifies the execution of physical CMOVE instructions and compiler COND_ASSIGN
statements on the register ALU.
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
from logos_compiler import LogosCompiler
from test_logos_vm import LogosVM

def build_group() -> ManifoldGroup:
    # Compile 4 semantic basins:
    # Basin_A (cond), Basin_B (true_val), Basin_Cin (false_val), Basin_SUM (out)
    nodes_a, edges_a, basin_a = UniversalManifold.build_semantic_basin("Basin_A", num_nodes=10, start_idx=0)
    nodes_b, edges_b, basin_b = UniversalManifold.build_semantic_basin("Basin_B", num_nodes=10, start_idx=10)
    nodes_cin, edges_cin, basin_cin = UniversalManifold.build_semantic_basin("Basin_Cin", num_nodes=10, start_idx=20)
    nodes_sum, edges_sum, basin_sum = UniversalManifold.build_semantic_basin("Basin_SUM", num_nodes=10, start_idx=30)
    
    semantic = SemanticManifold(
        nodes=nodes_a + nodes_b + nodes_cin + nodes_sum,
        edges=edges_a + edges_b + edges_cin + edges_sum,
        basins=[basin_a, basin_b, basin_cin, basin_sum]
    )
    
    # Load processing core
    processing = ProcessingManifold()
    
    return ManifoldGroup(semantic, processing, c_press=1.0, damping=0.01)

def run_cmove_trial(cond_active: bool, program: list[Instruction]) -> list[dict]:
    group = build_group()
    
    # Prime inputs:
    # cond = cond_active, true_val = active (1), false_val = collapsed (0)
    group.prime_basin("Basin_A", active=cond_active)
    group.prime_basin("Basin_B", active=True)
    group.prime_basin("Basin_Cin", active=False)
    group.prime_basin("Basin_SUM", active=False)
    
    # Prime registers to clean default state
    group.prime_register('A', active=False)
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    sequencer = MicroInstructionSequencer(group)
    vm = LogosVM(sequencer)
    
    history = vm.run(program)
    return history

def evaluate_cmove() -> tuple[dict, bool]:
    results = []
    suite_ok = True
    
    print("==========================================================================")
    print("  SOL LOGOSVM CONDITIONAL MOVE (CMOVE) VERIFICATION SUITE")
    print("==========================================================================")
    
    # Compile the COND_ASSIGN statement
    compiler = LogosCompiler()
    inputs = {"cond": "Basin_A", "true_val": "Basin_B", "false_val": "Basin_Cin"}
    outputs = {"out": "Basin_SUM"}
    statements = [
        ("COND_ASSIGN", "out", "cond", "true_val", "false_val"),
        ("STORE", "out", "Basin_SUM")
    ]
    
    program = compiler.compile(inputs, outputs, statements)
    print(f"Compiled program ({len(program)} instructions):")
    for i, inst in enumerate(program):
        print(f"  {i+1}. {inst.op} {inst.args}")
        
    # Run both condition branches
    for cond_state in (0, 1):
        cond_active = (cond_state == 1)
        print(f"\nRunning Trial: Condition Active = {cond_active}")
        history = run_cmove_trial(cond_active, program)
        
        # Expected outputs:
        # If cond_active: out should copy true_val (1) -> Basin_SUM = 1.
        # If not cond_active: out should remain false_val (0) -> Basin_SUM = 0.
        expected_sum = 1 if cond_active else 0
        got_sum = history[-1]["basin_d_state"]
        
        passed_logical = (got_sum == expected_sum)
        
        # Mass preservation check on active registers
        mass_ok = True
        a_mass = history[-1]["rho_reg_a"]
        b_mass = history[-1]["rho_reg_b"]
        c_mass = history[-1]["rho_reg_c"]
        d_mass = history[-1]["rho_reg_d"]
        
        if history[-1]["reg_a_state"] == 1.0 and a_mass < 14.0: mass_ok = False
        if history[-1]["reg_b_state"] == 1.0 and b_mass < 14.0: mass_ok = False
        if history[-1]["reg_c_state"] == 1.0 and c_mass < 14.0: mass_ok = False
        if history[-1]["reg_d_state"] == 1.0 and d_mass < 14.0: mass_ok = False
        
        trial_passed = passed_logical and mass_ok
        if not trial_passed:
            suite_ok = False
            
        print(f"  Got Basin_SUM State: {got_sum} | Expected: {expected_sum} | Status: {'OK' if passed_logical else 'FAIL'}")
        print(f"  Register Masses: A={a_mass:.2f}, B={b_mass:.2f}, C={c_mass:.2f}, D={d_mass:.2f} | Mass OK: {mass_ok}")
        print(f"  Trial Verdict: {'PASSED' if trial_passed else 'FAILED'}")
        
        results.append({
            "cond_active": cond_active,
            "expected_sum": expected_sum,
            "basin_sum_stored": got_sum,
            "mass_a": a_mass,
            "mass_b": b_mass,
            "mass_c": c_mass,
            "mass_d": d_mass,
            "passed": trial_passed
        })
        
    return {"results": results, "suite_passed": suite_ok}, suite_ok

def write_reports(report_data: dict, suite_passed: bool):
    report_dir = sol_root / "solResearch" / "nextBestTest"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON raw results
    json_path = report_dir / "logos_vm_cmove_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
        
    # Generate MD report
    report_md = [
        "# SOL LogosVM Conditional Move (CMOVE) Report",
        "",
        "This report verifies physical conditional moves and compiler gated assignments on LogosVM.",
        "",
        "## 1. Experimental Verdict",
        "",
        f"**Overall Suite Status**: **{'PASSED' if suite_passed else 'FAILED'}**",
        "",
        "## 2. Gated Assignment Verification Measurements",
        "",
        "| Condition Active | Expected SUM | Got Basin SUM | Status |",
        "| :---: | :---: | :---: | :---: |"
    ]
    
    for t in report_data["results"]:
        status_str = "OK" if t["passed"] else "FAIL"
        report_md.append(
            f"| {t['cond_active']} | {t['expected_sum']} | {t['basin_sum_stored']} | {status_str} |"
        )
        
    report_md.extend([
        "",
        "## 3. Analysis & Key Discoveries",
        "- **Zero-Jump Branchless Execution**: By utilizing physical Psi-Transistor gated pathways, we execute conditional assignment statements (`COND_ASSIGN`) without requiring software program branching jumps.",
        "- **Autonomic Gating Control**: The sequencer dynamically sets edge conductances based on the condition register's belief state, allowing mass copy only when the condition is active."
    ])
    
    md_path = report_dir / "logos_vm_cmove_report.md"
    md_path.write_text("\n".join(report_md) + "\n", encoding="utf-8")
    
    print(f"\nRaw results saved to: {json_path}")
    print(f"MD report generated at: {md_path}")

if __name__ == "__main__":
    report_data, passed = evaluate_cmove()
    write_reports(report_data, passed)
    if passed:
        print("\nLogosVM CMOVE Verification: ALL PASSED!")
        sys.exit(0)
    else:
        print("\nLogosVM CMOVE Verification: FAILED.")
        sys.exit(1)
