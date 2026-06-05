#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Logos Compiler (Level 6: Basic Software)
============================================
A symbolic compiler that takes high-level program descriptions, performs CFG-aware
liveness analysis and register allocation (Registers A, B, C, D), and generates optimal 
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
    Compiles symbolic variables, control loops, and equations into register-allocated micro-instructions.
    Uses iterative data-flow analysis to optimize register reuse across jumps and labels.
    """
    def __init__(self):
        # Register map: maps physical registers to active variables
        self.register_map = {'A': None, 'B': None, 'C': None, 'D': None}
        # Variable sources: maps variable name to source semantic basin
        self.var_sources = {}
        # Variable destinations: maps variable name to output semantic basin
        self.var_destinations = {}
        # Live out sets for each statement index
        self.live_out = []

    def _compute_liveness(self, statements: list):
        """Computes live-in and live-out variable sets for each statement using iterative data-flow analysis."""
        # Step 1: Find all label statement indices
        label_indices = {}
        for idx, stmt in enumerate(statements):
            if stmt[0] == "LABEL":
                label_indices[stmt[1]] = idx
                
        # Step 2: Build successors list
        successors = [[] for _ in range(len(statements))]
        for idx, stmt in enumerate(statements):
            op_type = stmt[0]
            if op_type == "JUMP":
                target = stmt[1]
                if target in label_indices:
                    successors[idx].append(label_indices[target])
            elif op_type == "JUMP_IF_ACTIVE":
                target = stmt[2]
                if target in label_indices:
                    successors[idx].append(label_indices[target])
                if idx + 1 < len(statements):
                    successors[idx].append(idx + 1)
            elif op_type == "RETURN" or op_type == "RET":
                # Ends execution of this block
                pass
            else:
                if idx + 1 < len(statements):
                    successors[idx].append(idx + 1)
                    
        # Step 3: Define uses and defs for each statement
        use = [set() for _ in range(len(statements))]
        defn = [set() for _ in range(len(statements))]
        for idx, stmt in enumerate(statements):
            op_type = stmt[0]
            if op_type == "OP":
                dest_var, _, src1, src2 = stmt[1], stmt[2], stmt[3], stmt[4]
                use[idx].add(src1)
                use[idx].add(src2)
                defn[idx].add(dest_var)
            elif op_type == "STORE":
                src_var = stmt[1]
                use[idx].add(src_var)
            elif op_type == "LOAD":
                dest_var = stmt[1]
                defn[idx].add(dest_var)
            elif op_type == "COND_ASSIGN":
                dest_var, cond_var, true_var, false_var = stmt[1], stmt[2], stmt[3], stmt[4]
                use[idx].add(cond_var)
                use[idx].add(true_var)
                use[idx].add(false_var)
                defn[idx].add(dest_var)
            elif op_type == "LOAD_INDIRECT":
                dest_var, _, addr_var = stmt[1], stmt[2], stmt[3]
                if isinstance(addr_var, (list, tuple)):
                    for v in addr_var:
                        use[idx].add(v)
                else:
                    use[idx].add(addr_var)
                defn[idx].add(dest_var)
            elif op_type == "STORE_INDIRECT":
                src_var, _, addr_var = stmt[1], stmt[2], stmt[3]
                use[idx].add(src_var)
                if isinstance(addr_var, (list, tuple)):
                    for v in addr_var:
                        use[idx].add(v)
                else:
                    use[idx].add(addr_var)
            elif op_type == "JUMP_IF_ACTIVE":
                cond_var = stmt[1]
                use[idx].add(cond_var)
            elif op_type == "CLEAR_VAR":
                var = stmt[1]
                defn[idx].add(var)

        # Step 4: Iterative data flow analysis
        live_in = [set() for _ in range(len(statements))]
        live_out = [set() for _ in range(len(statements))]
        
        changed = True
        while changed:
            changed = False
            for idx in reversed(range(len(statements))):
                # live_out[idx] = union of live_in of all successors
                new_live_out = set()
                for succ in successors[idx]:
                    new_live_out.update(live_in[succ])
                
                if new_live_out != live_out[idx]:
                    live_out[idx] = new_live_out
                    changed = True
                    
                # live_in[idx] = use[idx] U (live_out[idx] \ defn[idx])
                new_live_in = use[idx].union(live_out[idx].difference(defn[idx]))
                if new_live_in != live_in[idx]:
                    live_in[idx] = new_live_in
                    changed = True
                    
        self.live_out = live_out

    def _is_live(self, var: str, current_idx: int) -> bool:
        """Determines if a variable is live at statement current_idx (either live after, or used by it)."""
        if current_idx < len(self.live_out):
            return var in self.live_out[current_idx] or var in self.stmt_inputs[current_idx]
        return False

    def _find_free_register(self, current_idx: int, statements: list, exclude_reg: Optional[str] = None) -> Optional[str]:
        """Finds an empty register, or one holding a non-live variable, excluding exclude_reg."""
        # Prefer empty registers
        for reg in ['C', 'D', 'A', 'B']:
            if reg != exclude_reg and self.register_map[reg] is None:
                return reg
        # Fallback to non-live variables
        for reg in ['C', 'D', 'A', 'B']:
            if reg != exclude_reg:
                v = self.register_map[reg]
                if v and not self._is_live(v, current_idx):
                    return reg
        return None

    def _allocate_to_register(self, var: str, target_reg: str, idx: int, statements: list, program: list) -> str:
        """Ensures that var is loaded in target_reg, evacuating target_reg first if necessary."""
        current_reg = next((r for r, v in self.register_map.items() if v == var), None)
        if current_reg == target_reg:
            return target_reg
            
        # target_reg needs to be freed if it holds a live variable
        val_in_target = self.register_map[target_reg]
        if val_in_target and self._is_live(val_in_target, idx):
            # Evacuate it
            free_reg = self._find_free_register(idx, statements, exclude_reg=current_reg)
            if free_reg:
                program.append(Instruction("COPY", [target_reg, free_reg]))
                self.register_map[free_reg] = val_in_target
                self.register_map[target_reg] = None
            else:
                spill_basin = self.var_destinations.get(val_in_target) or self.var_sources.get(val_in_target)
                if spill_basin:
                    program.append(Instruction("STORE", [target_reg, spill_basin]))
                    self.register_map[target_reg] = None
                else:
                    raise RuntimeError(f"Register spill failed at stmt {idx}: {statements[idx]} | No free register to save {val_in_target} | Register Map: {self.register_map} | Live Out: {self.live_out[idx]}")
                    
        # Now target_reg is free. Load or copy var into it.
        if current_reg:
            program.append(Instruction("COPY", [current_reg, target_reg]))
            self.register_map[current_reg] = None
        else:
            basin = self.var_sources.get(var)
            if not basin:
                raise ValueError(f"Unknown variable source for {var}")
            program.append(Instruction("LOAD", [target_reg, basin]))
            
        self._set_register_var(target_reg, var)
        return target_reg

    def _spill_all_registers(self, idx: int, statements: list, program: list):
        """Spills all currently mapped variables to their memory basins and clears the register map."""
        for reg in ['A', 'B', 'C', 'D']:
            var = self.register_map[reg]
            if var is not None:
                if self._is_live(var, idx):
                    spill_basin = self.var_destinations.get(var) or self.var_sources.get(var)
                    if spill_basin:
                        program.append(Instruction("STORE", [reg, spill_basin]))
                    else:
                        raise RuntimeError(f"Register spill failed during boundary sync for variable '{var}' (not in inputs or outputs maps) at statement {idx}: {statements[idx]}")
                program.append(Instruction("CLEAR", [reg]))
                self.register_map[reg] = None

    def _set_register_var(self, dest_reg: str, dest_var: str):
        """Maps dest_var to dest_reg, ensuring no other register still maps to dest_var."""
        for r, v in list(self.register_map.items()):
            if v == dest_var and r != dest_reg:
                self.register_map[r] = None
        self.register_map[dest_reg] = dest_var

    def compile(self, inputs: dict[str, str], outputs: dict[str, str], statements: list[tuple], subroutines: dict[str, dict] = None) -> list[Instruction]:
        """
        Compiles a high-level list of statements into Level 5/6 instructions.
        """
        self.register_map = {'A': None, 'B': None, 'C': None, 'D': None}
        self.var_sources = inputs.copy()
        self.var_destinations = outputs.copy()
        
        # Precompute input operands for each statement
        self.stmt_inputs = []
        for stmt in statements:
            inputs_set = set()
            op_type = stmt[0]
            if op_type == "OP":
                inputs_set.add(stmt[3])
                inputs_set.add(stmt[4])
            elif op_type == "COND_ASSIGN":
                inputs_set.add(stmt[2])
                inputs_set.add(stmt[3])
                inputs_set.add(stmt[4])
            elif op_type == "STORE":
                inputs_set.add(stmt[1])
            elif op_type == "STORE_INDIRECT":
                inputs_set.add(stmt[1])
                addr = stmt[3]
                if isinstance(addr, (list, tuple)):
                    inputs_set.update(addr)
                else:
                    inputs_set.add(addr)
            elif op_type == "LOAD_INDIRECT":
                addr = stmt[3]
                if isinstance(addr, (list, tuple)):
                    inputs_set.update(addr)
                else:
                    inputs_set.add(addr)
            elif op_type == "JUMP_IF_ACTIVE":
                inputs_set.add(stmt[1])
            self.stmt_inputs.append(inputs_set)
            
        # Precompute CFG-aware liveness sets
        self._compute_liveness(statements)
        
        program = []
        
        for idx, stmt in enumerate(statements):
            print(f"DEBUG: Stmt {idx}: {stmt} | Reg Map Before: {self.register_map}")
            op_type = stmt[0]
            
            if op_type == "OP":
                dest_var, op_name, src1, src2 = stmt[1], stmt[2], stmt[3], stmt[4]
                
                # 1. Allocate src1 into Register A
                self._allocate_to_register(src1, 'A', idx, statements, program)
                
                # 2. Allocate src2 into Register B
                self._allocate_to_register(src2, 'B', idx, statements, program)
                
                # 3. Find a destination register for the output (C or D preferred, but dynamic if busy)
                dest_reg = 'C' if op_name not in ("AND", "AND_MS") else 'D'
                if self.register_map[dest_reg] and self._is_live(self.register_map[dest_reg], idx):
                    # Preferred is busy with a live variable. Let's look for a better one!
                    dying_vars = set()
                    if src1 and not self._is_live(src1, idx):
                        dying_vars.add(src1)
                    if src2 and not self._is_live(src2, idx):
                        dying_vars.add(src2)
                        
                    candidate_regs = ['C', 'D'] if dest_reg == 'C' else ['D', 'C']
                    
                    def get_reg_cost(r):
                        v = self.register_map[r]
                        # Don't overwrite active operands if they are live AFTER the statement
                        if r == 'A' and v == src1 and src1 in self.live_out[idx]:
                            return 100
                        if r == 'B' and v == src2 and src2 in self.live_out[idx]:
                            return 100
                        if v is None:
                            return 0
                        if v in dying_vars:
                            return 1
                        if not self._is_live(v, idx):
                            return 2
                        if self.var_destinations.get(v) or self.var_sources.get(v):
                            return 3
                        return 4
                        
                    dest_reg = min(candidate_regs, key=get_reg_cost)
                
                # Check if dest_reg contains a live variable, evacuate if necessary
                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and val_in_dest in self.live_out[idx]:
                    other_reg = next((r for r, v in self.register_map.items() if r != dest_reg and v == val_in_dest), None)
                    if other_reg is None:
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", [dest_reg, free_reg]))
                            self.register_map[free_reg] = val_in_dest
                            self.register_map[dest_reg] = None
                        else:
                            spill_basin = self.var_destinations.get(val_in_dest) or self.var_sources.get(val_in_dest)
                            if spill_basin:
                                program.append(Instruction("STORE", [dest_reg, spill_basin]))
                                self.register_map[dest_reg] = None
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_dest}")
                
                # Emit CLEAR on destination register if it had a value
                if val_in_dest:
                    program.append(Instruction("CLEAR", [dest_reg]))
                
                # Emit the gate operation
                program.append(Instruction(op_name, [dest_reg]))
                self._set_register_var(dest_reg, dest_var)
                
            elif op_type == "STORE":
                src_var, dest_basin = stmt[1], stmt[2]
                reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                if not reg_src:
                    # Automatically load from source basin if defined in inputs
                    basin = self.var_sources.get(src_var)
                    if not basin:
                        raise ValueError(f"Cannot store variable {src_var}: Not loaded in any register and no input source defined")
                    
                    reg_src = self._find_free_register(idx, statements) or 'C'
                    # Ensure reg_src is evacuated
                    val_in_reg = self.register_map[reg_src]
                    if val_in_reg and self._is_live(val_in_reg, idx):
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", [reg_src, free_reg]))
                            self.register_map[free_reg] = val_in_reg
                            self.register_map[reg_src] = None
                        else:
                            spill_basin = self.var_destinations.get(val_in_reg) or self.var_sources.get(val_in_reg)
                            if spill_basin:
                                program.append(Instruction("STORE", [reg_src, spill_basin]))
                                self.register_map[reg_src] = None
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_reg}")
                    program.append(Instruction("LOAD", [reg_src, basin]))
                    self.register_map[reg_src] = src_var
                
                program.append(Instruction("STORE", [reg_src, dest_basin]))
                
                # If variable is no longer live, clear it
                if not self._is_live(src_var, idx):
                    program.append(Instruction("CLEAR", [reg_src]))
                    self.register_map[reg_src] = None
                    
            elif op_type == "LOAD":
                dest_var, source_basin = stmt[1], stmt[2]
                candidate_regs = ['C', 'D', 'A', 'B']
                def get_reg_cost(r):
                    v = self.register_map[r]
                    if v is None:
                        return 0
                    if not self._is_live(v, idx):
                        return 1
                    if self.var_destinations.get(v) or self.var_sources.get(v):
                        return 2
                    return 3
                dest_reg = min(candidate_regs, key=get_reg_cost)
                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and val_in_dest in self.live_out[idx]:
                    other_reg = next((r for r, v in self.register_map.items() if r != dest_reg and v == val_in_dest), None)
                    if other_reg is None:
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", [dest_reg, free_reg]))
                            self.register_map[free_reg] = val_in_dest
                            self.register_map[dest_reg] = None
                        else:
                            spill_basin = self.var_destinations.get(val_in_dest) or self.var_sources.get(val_in_dest)
                            if spill_basin:
                                program.append(Instruction("STORE", [dest_reg, spill_basin]))
                                self.register_map[dest_reg] = None
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_dest}")
                program.append(Instruction("LOAD", [dest_reg, source_basin]))
                self._set_register_var(dest_reg, dest_var)
                
            elif op_type == "CALL_SUB":
                sub_name = stmt[1]
                program.append(Instruction("CALL", [sub_name]))
                
            elif op_type == "RETURN" or op_type == "RET":
                program.append(Instruction("RET", []))
                
            elif op_type == "COND_ASSIGN":
                dest_var, cond_var, true_var, false_var = stmt[1], stmt[2], stmt[3], stmt[4]
                
                # Allocate inputs to registers A, B, C respectively
                self._allocate_to_register(cond_var, 'A', idx, statements, program)
                self._allocate_to_register(true_var, 'B', idx, statements, program)
                self._allocate_to_register(false_var, 'C', idx, statements, program)
                
                # Find destination register D
                dest_reg = 'D'
                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and val_in_dest in self.live_out[idx]:
                    other_reg = next((r for r, v in self.register_map.items() if r != dest_reg and v == val_in_dest), None)
                    if other_reg is None:
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", [dest_reg, free_reg]))
                            self.register_map[free_reg] = val_in_dest
                            self.register_map[dest_reg] = None
                        else:
                            spill_basin = self.var_destinations.get(val_in_dest) or self.var_sources.get(val_in_dest)
                            if spill_basin:
                                program.append(Instruction("STORE", [dest_reg, spill_basin]))
                                self.register_map[dest_reg] = None
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_dest}")
                
                # Emit COPY false_var -> dest_reg
                program.append(Instruction("COPY", ['C', dest_reg]))
                # Emit CMOVE dest_reg, true_var, cond_var (which are B and A respectively)
                program.append(Instruction("CMOVE", [dest_reg, 'B', 'A']))
                
                self._set_register_var(dest_reg, dest_var)
                
            elif op_type == "LOAD_INDIRECT":
                dest_var, array_prefix, addr_var = stmt[1], stmt[2], stmt[3]
                
                # Allocate address register(s)
                if isinstance(addr_var, (list, tuple)):
                    # 2-bit pointer addressing: allocate MSB to C, LSB to D
                    self._allocate_to_register(addr_var[0], 'C', idx, statements, program)
                    self._allocate_to_register(addr_var[1], 'D', idx, statements, program)
                    reg_addr = ['C', 'D']
                else:
                    self._allocate_to_register(addr_var, 'D', idx, statements, program)
                    reg_addr = 'D'
                    
                # Allocate destination register (A or B preferred if 2-bit, or A/B/C if 1-bit)
                forbidden_regs = reg_addr if isinstance(reg_addr, list) else [reg_addr]
                candidate_regs = [r for r in ['A', 'B', 'C', 'D'] if r not in forbidden_regs]
                def get_reg_cost(r):
                    v = self.register_map[r]
                    if v is None:
                        return 0
                    if not self._is_live(v, idx):
                        return 1
                    if self.var_destinations.get(v) or self.var_sources.get(v):
                        return 2
                    return 3
                dest_reg = min(candidate_regs, key=get_reg_cost)

                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and val_in_dest in self.live_out[idx]:
                    other_reg = next((r for r, v in self.register_map.items() if r != dest_reg and v == val_in_dest), None)
                    if other_reg is None:
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", [dest_reg, free_reg]))
                            self.register_map[free_reg] = val_in_dest
                            self.register_map[dest_reg] = None
                        else:
                            spill_basin = self.var_destinations.get(val_in_dest) or self.var_sources.get(val_in_dest)
                            if spill_basin:
                                program.append(Instruction("STORE", [dest_reg, spill_basin]))
                                self.register_map[dest_reg] = None
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_dest}")
                
                program.append(Instruction("LOAD_INDIRECT", [dest_reg, array_prefix, reg_addr]))
                self._set_register_var(dest_reg, dest_var)
                
            elif op_type == "STORE_INDIRECT":
                src_var, array_prefix, addr_var = stmt[1], stmt[2], stmt[3]
                
                # Locate src_var register
                reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                if not reg_src:
                    raise ValueError(f"Cannot store variable {src_var}: Not loaded in any register")
                    
                # Ensure src_var is not in any register that will be used by addr_var
                forbidden_regs = ['C', 'D'] if isinstance(addr_var, (list, tuple)) else ['D']
                if reg_src in forbidden_regs:
                    safe_regs = [r for r in ['A', 'B', 'C'] if r not in forbidden_regs]
                    target_reg = None
                    for r in safe_regs:
                        if self.register_map[r] is None:
                            target_reg = r
                            break
                    if not target_reg:
                        for r in safe_regs:
                            if not self._is_live(self.register_map[r] or "", idx):
                                target_reg = r
                                break
                    if not target_reg:
                        target_reg = safe_regs[0]
                    self._allocate_to_register(src_var, target_reg, idx, statements, program)
                    reg_src = target_reg

                # Allocate address register(s)
                if isinstance(addr_var, (list, tuple)):
                    self._allocate_to_register(addr_var[0], 'C', idx, statements, program)
                    self._allocate_to_register(addr_var[1], 'D', idx, statements, program)
                    reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                    reg_addr = ['C', 'D']
                else:
                    self._allocate_to_register(addr_var, 'D', idx, statements, program)
                    reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                    reg_addr = 'D'
                    
                program.append(Instruction("STORE_INDIRECT", [reg_src, array_prefix, reg_addr]))
                
                # If variable is no longer live, clear it
                if reg_src is not None and not self._is_live(src_var, idx):
                    program.append(Instruction("CLEAR", [reg_src]))
                    self.register_map[reg_src] = None

            elif op_type == "LABEL":
                self._spill_all_registers(idx, statements, program)
                label_name = stmt[1]
                program.append(Instruction("LABEL", [label_name]))

            elif op_type == "JUMP":
                self._spill_all_registers(idx, statements, program)
                label_name = stmt[1]
                program.append(Instruction("JUMP", [label_name]))

            elif op_type == "JUMP_IF_ACTIVE":
                cond_var, label_name = stmt[1], stmt[2]
                reg_cond = next((r for r, v in self.register_map.items() if v == cond_var), None)
                if not reg_cond:
                    reg_cond = self._allocate_to_register(cond_var, 'A', idx, statements, program)
                
                # Spill/clear all registers except reg_cond
                for reg in ['A', 'B', 'C', 'D']:
                    if reg != reg_cond:
                        var = self.register_map[reg]
                        if var is not None:
                            if self._is_live(var, idx):
                                spill_basin = self.var_destinations.get(var) or self.var_sources.get(var)
                                if spill_basin:
                                    program.append(Instruction("STORE", [reg, spill_basin]))
                                else:
                                    raise RuntimeError(f"Register spill failed during boundary sync for variable '{var}' (not in inputs or outputs maps) at statement {idx}: {statements[idx]}")
                            program.append(Instruction("CLEAR", [reg]))
                            self.register_map[reg] = None
                
                program.append(Instruction("JUMP_IF_ACTIVE", [reg_cond, label_name]))
                
                # Clear the condition register as well so the fall-through starts clean
                var = self.register_map[reg_cond]
                if var is not None:
                    if self._is_live(var, idx):
                        spill_basin = self.var_destinations.get(var) or self.var_sources.get(var)
                        if spill_basin:
                            program.append(Instruction("STORE", [reg_cond, spill_basin]))
                    program.append(Instruction("CLEAR", [reg_cond]))
                    self.register_map[reg_cond] = None

            elif op_type == "CLEAR_VAR":
                var_name = stmt[1]
                reg_var = next((r for r, v in self.register_map.items() if v == var_name), None)
                if not reg_var:
                    # Allocate a free register for it
                    reg_var = self._find_free_register(idx, statements) or 'C'
                    # Ensure reg_var is evacuated
                    val_in_reg = self.register_map[reg_var]
                    if val_in_reg and self._is_live(val_in_reg, idx):
                        free_reg = self._find_free_register(idx, statements)
                        if free_reg:
                            program.append(Instruction("COPY", [reg_var, free_reg]))
                            self.register_map[free_reg] = val_in_reg
                            self.register_map[reg_var] = None
                        else:
                            spill_basin = self.var_destinations.get(val_in_reg) or self.var_sources.get(val_in_reg)
                            if spill_basin:
                                program.append(Instruction("STORE", [reg_var, spill_basin]))
                                self.register_map[reg_var] = None
                            else:
                                raise RuntimeError(f"Register spill failed: No free register to save {val_in_reg}")
                
                # Emit CLEAR and map the variable to this register
                program.append(Instruction("CLEAR", [reg_var]))
                # If the variable is still live after this statement, keep it in the register map
                if self._is_live(var_name, idx):
                    self.register_map[reg_var] = var_name
        # Guarantee all registers collapse to -1 cleanly at program termination
        program.append(Instruction("CLEAR", ["A"]))
        program.append(Instruction("CLEAR", ["B"]))
        program.append(Instruction("CLEAR", ["C"]))
        program.append(Instruction("CLEAR", ["D"]))
        
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
                if not sub_insts or sub_insts[-1].op.upper() not in ("RET", "RETURN"):
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
