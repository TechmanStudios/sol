#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL LogosVM & Branching Verification (Level 6: Basic Software)
==============================================================
Verifies the execution of conditional control flow branching (LogosVM)
on the stateful register ALU.
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

class LogosVM:
    """
    LogosVM:
    Wraps the micro-instruction sequencer with program pointer control,
    conditional jumps, and a procedural call stack with analog context switching.
    """
    def __init__(self, sequencer: MicroInstructionSequencer):
        self.sequencer = sequencer
        self.pc = 0
        self.stack = []
        
    def _save_registers(self) -> dict:
        state = {}
        group = self.sequencer.group
        for reg in ['A', 'B', 'C', 'D']:
            host = group.get_node(f"S_R{reg}")
            bat = group.get_node(f"S_R{reg}_B")
            state[reg] = {
                "host": {
                    "psi": host["psi"],
                    "psi_bias": host["psi_bias"],
                    "rho": host["rho"]
                },
                "bat": {
                    "psi": bat["psi"],
                    "psi_bias": bat["psi_bias"],
                    "rho": bat["rho"],
                    "b_state": bat.get("b_state"),
                    "b_charge": bat.get("b_charge")
                }
            }
        return state

    def _restore_registers(self, state: dict):
        group = self.sequencer.group
        for reg in ['A', 'B', 'C', 'D']:
            reg_state = state[reg]
            host = group.get_node(f"S_R{reg}")
            bat = group.get_node(f"S_R{reg}_B")
            
            host["psi"] = reg_state["host"]["psi"]
            host["psi_bias"] = reg_state["host"]["psi_bias"]
            host["rho"] = reg_state["host"]["rho"]
            
            bat["psi"] = reg_state["bat"]["psi"]
            bat["psi_bias"] = reg_state["bat"]["psi_bias"]
            bat["rho"] = reg_state["bat"]["rho"]
            if "b_state" in reg_state["bat"]:
                bat["b_state"] = reg_state["bat"]["b_state"]
            if "b_charge" in reg_state["bat"]:
                bat["b_charge"] = reg_state["bat"]["b_charge"]

    def run(self, program: list[Instruction]) -> list[dict]:
        # Pre-pass: Resolve labels
        labels = {}
        resolved_prog = []
        idx = 0
        for inst in program:
            if inst.op.upper() == "LABEL":
                labels[inst.args[0]] = idx
            else:
                resolved_prog.append(inst)
                idx += 1
                
        self.pc = 0
        self.stack = []
        self.sequencer.history = []
        
        while self.pc < len(resolved_prog):
            inst = resolved_prog[self.pc]
            op = inst.op.upper()
            
            # Check for Level 6 jump/procedural instructions
            if op == "JUMP":
                label = inst.args[0]
                self.pc = labels[label]
                continue
            elif op == "JUMP_IF_ACTIVE":
                reg, label = inst.args[0], inst.args[1]
                bat_state = self.sequencer.group.get_node(f"S_R{reg}_B")["b_state"]
                if bat_state == 1:
                    self.pc = labels[label]
                    continue
            elif op == "JUMP_IF_COLLAPSED":
                reg, label = inst.args[0], inst.args[1]
                bat_state = self.sequencer.group.get_node(f"S_R{reg}_B")["b_state"]
                if bat_state == -1:
                    self.pc = labels[label]
                    continue
            elif op == "CALL":
                label = inst.args[0]
                # Push return PC and a backup of all physical register nodes
                self.stack.append((self.pc + 1, self._save_registers()))
                self.pc = labels[label]
                continue
            elif op == "RET":
                if not self.stack:
                    raise RuntimeError("LogosVM stack underflow on RET instruction")
                return_pc, saved_state = self.stack.pop()
                self._restore_registers(saved_state)
                self.pc = return_pc
                continue
            
            # Execute Level 5 instruction
            self.sequencer.execute_instruction(inst)
            self.pc += 1
            
        return self.sequencer.history

def build_group() -> ManifoldGroup:
    # Compile 4 semantic basins (Basin_A, Basin_B, Basin_Cin, Basin_SUM)
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

def run_branch_trial(A_active: bool) -> list[dict]:
    group = build_group()
    
    # Prime inputs
    group.prime_basin("Basin_A", active=A_active)
    group.prime_basin("Basin_B", active=False)
    group.prime_basin("Basin_Cin", active=True)  # Cin is active (1) to use as high dummy value
    group.prime_basin("Basin_SUM", active=False)
    
    # Prime registers
    group.prime_register('A', active=False)
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    
    sequencer = MicroInstructionSequencer(group)
    vm = LogosVM(sequencer)
    
    # Branching program:
    # If A is active, jump to L_ACTIVE (clears C to 0).
    # Otherwise, load active Cin into C, then jump to L_EXIT.
    program = [
        Instruction("LOAD", ['A', "Basin_A"]),
        Instruction("JUMP_IF_ACTIVE", ['A', "L_ACTIVE"]),
        
        # If A is collapsed (A = 0):
        Instruction("LOAD", ['C', "Basin_Cin"]),
        Instruction("JUMP", ["L_EXIT"]),
        
        # If A is active (A = 1):
        Instruction("LABEL", ["L_ACTIVE"]),
        Instruction("CLEAR", ['C']),
        
        Instruction("LABEL", ["L_EXIT"]),
        Instruction("STORE", ['C', "Basin_SUM"])
    ]
    
    history = vm.run(program)
    return history

def evaluate_vm() -> tuple[dict, bool]:
    results = []
    suite_ok = True
    
    print("==========================================================================")
    print("  SOL LOGOSVM CONTROL FLOW BRANCHING SUITE")
    print("==========================================================================")
    
    # Test both branch directions
    for A in (0, 1):
        print(f"\nRunning Branch Trial: Input A={A}")
        history = run_branch_trial(A_active=(A == 1))
        
        # Expected outputs:
        # If A == 1: branches to L_ACTIVE, clears C -> SUM should be 0.
        # If A == 0: executes LOAD C, Cin=1 -> SUM should be 1.
        expected_sum = 0 if A == 1 else 1
        
        basin_sum_stored = history[-1]["basin_d_state"] == expected_sum
        passed = basin_sum_stored
        if not passed:
            suite_ok = False
            
        print(f"  Got Basin_SUM: {history[-1]['basin_d_state']} | Expected: {expected_sum} | Status: {'PASSED' if passed else 'FAILED'}")
        
        results.append({
            "input_a": A,
            "expected_sum": expected_sum,
            "basin_sum_stored": history[-1]["basin_d_state"],
            "passed": passed
        })
        
    return {"results": results, "suite_passed": suite_ok}, suite_ok

def write_reports(report_data: dict, suite_passed: bool):
    report_dir = sol_root / "solResearch" / "nextBestTest"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON raw results
    json_path = report_dir / "logos_vm_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
        
    # Generate MD report
    report_md = [
        "# SOL LogosVM Branching Verification Report",
        "",
        "This report verifies control flow branching (JUMP and JUMP_IF_ACTIVE) on the Level 6 basic software runtime.",
        "",
        "## 1. Experimental Verdict",
        "",
        f"**Overall Suite Status**: **{'PASSED' if suite_passed else 'FAILED'}**",
        "",
        "## 2. Control Flow Branching Truth Table",
        "",
        "| Input A (Condition) | Expected SUM | Got Basin SUM | Branch Path Taken | Status |",
        "| :---: | :---: | :---: | :---: | :---: |"
    ]
    
    for t in report_data["results"]:
        status_str = "OK" if t["passed"] else "FAIL"
        path_taken = "L_ACTIVE (Clears C)" if t["input_a"] == 1 else "Default (Loads Cin)"
        report_md.append(
            f"| {t['input_a']} | {t['expected_sum']} | {t['basin_sum_stored']} | {path_taken} | {status_str} |"
        )
        
    report_md.extend([
        "",
        "## 3. Key Observations",
        "- **Dynamic Branch Execution**: The LogosVM successfully monitors physical register states (`b_state`) at runtime, adjusting its execution pointer to jump instructions dynamically.",
        "- **Analog Conditional Integration**: Conditional branching binds physical register belief directly to symbolic software execution logic, bridging analog state spaces with discrete software program structures."
    ])
    
    md_path = report_dir / "logos_vm_report.md"
    md_path.write_text("\n".join(report_md) + "\n", encoding="utf-8")
    
    print(f"\nRaw results saved to: {json_path}")
    print(f"MD report generated at: {md_path}")

if __name__ == "__main__":
    report_data, passed = evaluate_vm()
    write_reports(report_data, passed)
    if passed:
        print("\nLogosVM Verification: ALL PASSED!")
        sys.exit(0)
    else:
        print("\nLogosVM Verification: FAILED.")
        sys.exit(1)
