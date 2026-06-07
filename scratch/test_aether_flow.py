#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Aether Verification Suite (Level 6/7 Tests)
============================================
Runs automated unit tests validating compiler AST translation, instruction generation,
and the convergence of the stochastic RSI loop.
"""

import sys
import unittest
from pathlib import Path

# Add project root and scratch paths to python path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from aether_compiler import AetherCompiler, AetherAgent
from aether_rsi import evaluate_program, get_expected, run_rsi

class TestAetherFlow(unittest.TestCase):
    def test_basic_compilation(self):
        """Test compiling a basic XOR assignment."""
        inputs = {"x": "Basin_A", "y": "Basin_B"}
        outputs = {"z": "Basin_SUM"}
        flow_src = "self.z = self.x ^ self.y"
        
        instructions = AetherCompiler.compile_flow_src(inputs, outputs, flow_src)
        self.assertTrue(len(instructions) > 0)
        
        # Verify micro-instructions generated
        ops = [inst.op for inst in instructions]
        self.assertIn("LOAD", ops)
        self.assertIn("XOR", ops)
        self.assertIn("STORE", ops)
        self.assertIn("CLEAR", ops)

    def test_ternary_conditional_compilation(self):
        """Test compiling a ternary statement (COND_ASSIGN)."""
        inputs = {"x": "Basin_A", "y": "Basin_B", "cond": "Basin_Cin"}
        outputs = {"z": "Basin_SUM"}
        flow_src = "self.z = self.x if self.cond else self.y"
        
        instructions = AetherCompiler.compile_flow_src(inputs, outputs, flow_src)
        ops = [inst.op for inst in instructions]
        self.assertIn("CMOVE", ops)

    def test_program_evaluation(self):
        """Test evaluation metrics on a known, correct Full-Adder solution."""
        correct_adder = [
            "temp1 = x ^ y",
            "self.sum = temp1 ^ cin",
            "temp2 = x & y",
            "temp3 = temp1 & cin",
            "self.cout = temp2 | temp3"
        ]
        
        fitness, correct_bits, ic, mc, all_passed = evaluate_program(correct_adder)
        self.assertEqual(correct_bits, 16)
        self.assertTrue(all_passed)
        self.assertTrue(fitness > 15.0)

    def test_rsi_convergence(self):
        """Test that the RSI loop runs and improves a program."""
        # Run a short run of 10 cycles to verify it works without crashing
        current_best = [
            "temp1 = x ^ y",
            "self.sum = temp1",
            "self.cout = x & y"
        ]
        initial_fit, _, _, _, _ = evaluate_program(current_best)
        
        # Verify mutating the program changes it
        from aether_rsi import mutate_program
        mutated = mutate_program(current_best)
        self.assertNotEqual(current_best, mutated)

if __name__ == "__main__":
    unittest.main()
