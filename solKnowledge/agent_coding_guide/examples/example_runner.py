#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Example Runner for AI Agents
================================
Demonstrates how to compile dynamic symbolic equations using LogosCompiler 
and execute the compiled program on the LogosVM.
"""

import sys
from pathlib import Path

# Add project root and scratch paths to python path
sol_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

try:
    from logos_compiler import LogosCompiler
    from test_logos_vm import LogosVM, build_group
    from hybrid_subsystem_framework import MicroInstructionSequencer, Instruction
except ImportError as e:
    print(f"ImportError: {e}")
    print("Please make sure you are running this script from the project root or virtual environment.")
    sys.exit(1)

def run_agent_example():
    print("==========================================================================")
    # 1. Instantiate the Compiler
    print("[1] Initializing LogosCompiler...")
    compiler = LogosCompiler()
    
    # 2. Define inputs, outputs, and symbolic equations
    # We will compute: C = A XOR B
    inputs = {"A": "Basin_A", "B": "Basin_B"}
    outputs = {"SUM": "Basin_SUM"}
    
    # High-level statements
    statements = [
        ("OP", "SUM", "XOR", "A", "B"),
        ("STORE", "SUM", "Basin_SUM")
    ]
    
    # 3. Compile statements into register-allocated micro-instructions
    print("[2] Compiling symbolic equations to micro-instructions...")
    instructions = compiler.compile(inputs, outputs, statements)
    print("Generated instructions:")
    for i, inst in enumerate(instructions):
        print(f"  {i+1}. {inst.op} {inst.args}")
        
    # 4. Build the physical substrate group
    print("\n[3] Building physical substrate (ManifoldGroup)...")
    group = build_group()
    
    # Prime inputs: A = 1 (active), B = 0 (collapsed)
    print("  Priming inputs: Input A = 1, Input B = 0 (Expected SUM = 1)")
    group.prime_basin("Basin_A", active=True)
    group.prime_basin("Basin_B", active=False)
    
    # Prime registers to clean default state
    group.prime_register('A', active=False)
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    
    # 5. Initialize the Sequencer and LogosVM
    sequencer = MicroInstructionSequencer(group)
    vm = LogosVM(sequencer)
    
    # 6. Execute the compiled instructions on the VM
    print("\n[4] Executing instructions on LogosVM...")
    history = vm.run(instructions)
    
    # 7. Check the resulting state of the accumulator and destination basin
    final_reg_c_state = group.get_node("S_RC_B")["b_state"]
    final_basin_sum_state = history[-1]["basin_d_state"]  # Basin_SUM is the 4th basin (index D)
    
    print("\n[5] Execution Complete. Final State:")
    print(f"  Register C Battery State: {final_reg_c_state}")
    print(f"  Basin_SUM State: {final_basin_sum_state}")
    
    # Validate result
    expected_sum = 1
    if final_basin_sum_state == expected_sum:
        print("\nVerification: SUCCESS!")
    else:
        print("\nVerification: FAILED. Expected Basin_SUM to be 1.")
        sys.exit(1)

if __name__ == "__main__":
    run_agent_example()
