#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Logos Compiler (Level 6: Basic Software)
============================================
A symbolic compiler that takes high-level program descriptions, performs liveness
analysis and register allocation (Registers A, B, C, D), and generates optimal 
sequences of micro-instructions.
"""

from typing import Any, Optional
import sys
from pathlib import Path

# Add project root and scratch paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import Instruction

class LogosCompiler:
    """
    Logos Compiler (Level 6):
    Compiles symbolic variables and equations into register-allocated micro-instructions.
    """
    def __init__(self):
        # Register map: maps physical registers to active variables
        self.register_map = {'A': None, 'B': None, 'C': None, 'D': None}
        # Variable sources: maps variable name to source semantic basin
        self.var_sources = {}
        # Variable destinations: maps variable name to output semantic basin
        self.var_destinations = {}
        
    def _is_live(self, var: str, current_idx: int, statements: list) -> bool:
        """Determines if a variable is referenced in any future statements."""
        for idx in range(current_idx + 1, len(statements)):
            stmt = statements[idx]
            op_type = stmt[0]
            if op_type == "OP":
                _, _, src1, src2 = stmt[1], stmt[2], stmt[3], stmt[4]
                if src1 == var or src2 == var:
                    return True
            elif op_type == "STORE":
                src_var, _ = stmt[1], stmt[2]
                if src_var == var:
                    return True
            elif op_type == "COPY":
                src_var, _ = stmt[1], stmt[2]
                if src_var == var:
                    return True
        return False

    def _find_free_register(self, current_idx: int, statements: list) -> Optional[str]:
        """Finds an empty register, or one holding a non-live variable."""
        # Prefer empty registers
        for reg in ['C', 'D', 'A', 'B']:
            if self.register_map[reg] is None:
                return reg
        # Fallback to non-live variables
        for reg in ['C', 'D', 'A', 'B']:
            v = self.register_map[reg]
            if v and not self._is_live(v, current_idx, statements):
                return reg
        return None

    def compile(self, inputs: dict[str, str], outputs: dict[str, str], statements: list[tuple], subroutines: dict[str, dict] = None) -> list[Instruction]:
        """
        Compiles a high-level list of statements into Level 5/6 instructions.
        Each statement can be:
        - ("OP", dest_var, op_name, src_var1, src_var2)
        - ("STORE", src_var, dest_basin)
        - ("CALL_SUB", sub_name)
        - ("RETURN",)
        """
        self.register_map = {'A': None, 'B': None, 'C': None, 'D': None}
        self.var_sources = inputs.copy()
        self.var_destinations = outputs.copy()
        
        program = []
        
        for idx, stmt in enumerate(statements):
            op_type = stmt[0]
            
            if op_type == "OP":
                dest_var, op_name, src1, src2 = stmt[1], stmt[2], stmt[3], stmt[4]
                
                # 1. Allocate src1 into Register A
                reg_src1 = next((r for r, v in self.register_map.items() if v == src1), None)
                if reg_src1 != 'A':
                    # If Register A is holding a live variable, we must evacuate/save it
                    val_in_a = self.register_map['A']
                    if val_in_a and self._is_live(val_in_a, idx, statements):
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", ['A', free_reg]))
                            self.register_map[free_reg] = val_in_a
                        else:
                            # Spill to memory if defined
                            spill_basin = self.var_destinations.get(val_in_a) or self.var_sources.get(val_in_a)
                            if spill_basin:
                                program.append(Instruction("STORE", ['A', spill_basin]))
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_a}")
                    
                    if reg_src1:
                        # Copy from its current register to A
                        program.append(Instruction("COPY", [reg_src1, 'A']))
                    else:
                        # Load from semantic basin
                        basin = self.var_sources.get(src1)
                        if not basin:
                            raise ValueError(f"Unknown variable source for {src1}")
                        program.append(Instruction("LOAD", ['A', basin]))
                    self.register_map['A'] = src1
                    
                # 2. Allocate src2 into Register B
                reg_src2 = next((r for r, v in self.register_map.items() if v == src2), None)
                if reg_src2 != 'B':
                    val_in_b = self.register_map['B']
                    if val_in_b and self._is_live(val_in_b, idx, statements):
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", ['B', free_reg]))
                            self.register_map[free_reg] = val_in_b
                        else:
                            spill_basin = self.var_destinations.get(val_in_b) or self.var_sources.get(val_in_b)
                            if spill_basin:
                                program.append(Instruction("STORE", ['B', spill_basin]))
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_b}")
                    
                    if reg_src2:
                        program.append(Instruction("COPY", [reg_src2, 'B']))
                    else:
                        basin = self.var_sources.get(src2)
                        if not basin:
                            raise ValueError(f"Unknown variable source for {src2}")
                        program.append(Instruction("LOAD", ['B', basin]))
                    self.register_map['B'] = src2
                
                # 3. Find a destination register for the output (C or D preferred)
                dest_reg = 'C' if op_name not in ("AND", "AND_MS") else 'D'
                # Check if dest_reg contains a live variable
                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and self._is_live(val_in_dest, idx, statements):
                    # Check if val_in_dest is already stored in another register (e.g. copied to A or B)
                    other_reg = next((r for r, v in self.register_map.items() if r != dest_reg and v == val_in_dest), None)
                    if other_reg is None:
                        # Save it to another register
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", [dest_reg, free_reg]))
                            self.register_map[free_reg] = val_in_dest
                        else:
                            spill_basin = self.var_destinations.get(val_in_dest) or self.var_sources.get(val_in_dest)
                            if spill_basin:
                                program.append(Instruction("STORE", [dest_reg, spill_basin]))
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_dest}")
                
                # Emit CLEAR on destination register if it had a value to make it clean
                if val_in_dest:
                    program.append(Instruction("CLEAR", [dest_reg]))
                
                # Emit the gate operation
                program.append(Instruction(op_name, [dest_reg]))
                self.register_map[dest_reg] = dest_var
                
            elif op_type == "STORE":
                src_var, dest_basin = stmt[1], stmt[2]
                reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                if not reg_src:
                    raise ValueError(f"Cannot store variable {src_var}: Not loaded in any register")
                
                program.append(Instruction("STORE", [reg_src, dest_basin]))
                
                # If variable is no longer live, clear it to free register
                if not self._is_live(src_var, idx, statements):
                    program.append(Instruction("CLEAR", [reg_src]))
                    self.register_map[reg_src] = None
                    
            elif op_type == "CALL_SUB":
                sub_name = stmt[1]
                program.append(Instruction("CALL", [sub_name]))
                
            elif op_type == "RETURN":
                program.append(Instruction("RET", []))
        
        if subroutines:
            program.append(Instruction("JUMP", ["L_COMPILER_EXIT"]))
            for sub_name, sub_def in subroutines.items():
                sub_compiler = LogosCompiler()
                sub_insts = sub_compiler.compile(
                    sub_def.get("inputs", {}),
                    sub_def.get("outputs", {}),
                    sub_def.get("statements", [])
                )
                program.append(Instruction("LABEL", [sub_name]))
                program.extend(sub_insts)
                if not sub_insts or sub_insts[-1].op.upper() != "RET":
                    program.append(Instruction("RET", []))
            program.append(Instruction("LABEL", ["L_COMPILER_EXIT"]))
        
        return program

if __name__ == "__main__":
    # Test compilation of a Full-Adder
    compiler = LogosCompiler()
    inputs = {"A": "Basin_A", "B": "Basin_B", "Cin": "Basin_Cin"}
    outputs = {"SUM": "Basin_SUM", "Cout": "Basin_Cout"}
    statements = [
        ("OP", "xor1", "XOR", "A", "B"),
        ("OP", "and1", "AND_MS", "A", "B"),
        ("OP", "SUM", "XOR", "xor1", "Cin"),
        ("STORE", "SUM", "Basin_SUM"),
        ("OP", "and2", "AND_MS", "xor1", "Cin"),
        ("OP", "Cout", "OR_MS", "and2", "and1"),
        ("STORE", "Cout", "Basin_Cout")
    ]
    
    instructions = compiler.compile(inputs, outputs, statements)
    print(f"Compiled program ({len(instructions)} instructions):")
    for i, inst in enumerate(instructions):
        print(f"  {i+1}. {inst.op} {inst.args}")
