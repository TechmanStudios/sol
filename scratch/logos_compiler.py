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

import sys
from pathlib import Path

# Add project root and scratch paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import Instruction


class CompiledLogosProgram(list):
    """List of compiled Logos Instructions carrying scratch-basin and pure-wave metadata."""

    def __init__(
        self,
        instructions: list[Instruction] | None = None,
        allocated_scratch_basins: dict[str, str] | None = None,
        pure_wave: bool = False,
    ):
        super().__init__(instructions or [])
        self.allocated_scratch_basins: dict[str, str] = dict(allocated_scratch_basins or {})
        self.pure_wave: bool = bool(pure_wave)


class LogosCompiler:
    """
    Logos Compiler (Level 6):
    Compiles symbolic variables, control loops, and equations into register-allocated micro-instructions.
    Uses iterative data-flow analysis to optimize register reuse across jumps and labels,
    automatically spilling excess live temporaries to Basin_Scratch_0..K when all 4 registers are live.
    """
    def __init__(self):
        # Register map: maps physical registers to active variables
        self.register_map = {'A': None, 'B': None, 'C': None, 'D': None}
        # Registers whose physical memristive battery may be non-cleared (-1)
        self.physically_dirty: set[str] = set()
        # Variable sources: maps variable name to current source semantic basin
        self.var_sources = {}
        # Variable destinations: maps variable name to output semantic basin
        self.var_destinations = {}
        # Original input basins and read-only input variable names (must never be overwritten by spill STOREs)
        self.input_basins_by_var: dict[str, str] = {}
        self.read_only_input_vars: set[str] = set()
        # Dynamically allocated scratch basins for spilled temporaries (>4 live variables)
        self.allocated_scratch_basins: dict[str, str] = {}
        self._reserved_basin_names: set[str] = set()
        self._compile_count: int = 0
        # Variables modified since their last load or spill store
        self.dirty_vars: set[str] = set()
        self._pending_store_reg_alias: tuple[str, str] | None = None
        # Live in/out sets for each statement index
        self.live_in = []
        self.live_out = []

    def _needs_spill_store(self, var: str) -> bool:
        """Returns False if var is clean in its current backing basin or holds an unmodified read-only input."""
        if var not in self.dirty_vars and bool(self.var_sources.get(var)):
            return False
        return not (
            var in self.read_only_input_vars
            and var not in self.allocated_scratch_basins
            and self.var_sources.get(var) == self.input_basins_by_var.get(var)
        )

    def _get_or_alloc_spill_basin(self, var: str) -> str:
        """Returns output/scratch basin for var, never returning a read-only input basin as a STORE target."""
        if var in self.var_destinations:
            existing = self.var_destinations[var]
            self.var_sources.setdefault(var, existing)
            return existing
        if var in self.allocated_scratch_basins:
            basin = self.allocated_scratch_basins[var]
            self.var_sources[var] = basin
            return basin
        if var not in self.read_only_input_vars and var in self.var_sources:
            return self.var_sources[var]
        used = (
            set(self._reserved_basin_names)
            | set(self.input_basins_by_var.values())
            | set(self.var_sources.values())
            | set(self.var_destinations.values())
            | set(self.allocated_scratch_basins.values())
        )
        k = len(self.allocated_scratch_basins)
        while f"Basin_Scratch_{k}" in used:
            k += 1
        basin = f"Basin_Scratch_{k}"
        self.allocated_scratch_basins[var] = basin
        self.var_sources[var] = basin
        return basin

    def _clear_reg(self, reg: str, program: list) -> None:
        program.append(Instruction("CLEAR", [reg]))
        self.register_map[reg] = None
        self.physically_dirty.discard(reg)

    def _prepare_reg_for_write(self, reg: str, program: list, pure_wave: bool) -> None:
        """Ensures legacy memristive register batteries start cleared before write ops that cannot quench 1->0."""
        if not pure_wave and reg in self.physically_dirty:
            program.append(Instruction("CLEAR", [reg]))
            self.physically_dirty.discard(reg)
        self.register_map[reg] = None

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
                    
        self.live_in = live_in
        self.live_out = live_out

    def _is_live(self, var: str, current_idx: int) -> bool:
        """Determines if a variable is live at statement current_idx (either live after, or used by it)."""
        if current_idx < len(self.live_out):
            return var in self.live_out[current_idx] or var in self.stmt_inputs[current_idx]
        return False

    def _find_free_register(self, current_idx: int, statements: list, exclude_reg: str | None = None) -> str | None:
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

    def _used_before_block_end(self, var: str, start_idx: int, statements: list) -> bool:
        """Returns True if var is read by a statement after start_idx before the next LABEL or unconditional JUMP."""
        for k in range(start_idx + 1, len(statements)):
            op_k = statements[k][0]
            if op_k in ("LABEL", "JUMP", "RETURN", "RET"):
                return False
            if k < len(self.stmt_inputs) and var in self.stmt_inputs[k]:
                return True
        return False

    def _evacuate_live_reg(
        self,
        reg: str,
        val: str,
        idx: int,
        statements: list,
        program: list,
        pure_wave: bool,
        exclude_reg: str | None = None,
        allowed_free_regs: tuple[str, ...] | None = None,
        used_in_current_stmt: bool = False,
    ) -> None:
        other_reg = next((r for r, v in self.register_map.items() if r != reg and v == val), None)
        if other_reg is not None:
            self.register_map[reg] = None
            return

        if (
            pure_wave
            and not used_in_current_stmt
            and not self._used_before_block_end(val, idx, statements)
            and (
                val in self.var_destinations or val in self.allocated_scratch_basins or not self._needs_spill_store(val)
            )
        ):
            if self._needs_spill_store(val):
                spill_basin = self._get_or_alloc_spill_basin(val)
                program.append(Instruction("STORE", [reg, spill_basin]))
                self.dirty_vars.discard(val)
            self.register_map[reg] = None
            return

        free_reg = None
        if allowed_free_regs is not None:
            for cand in allowed_free_regs:
                if cand != reg and cand != exclude_reg and (
                    self.register_map[cand] is None or not self._is_live(self.register_map[cand], idx)
                ):
                    free_reg = cand
                    break
        else:
            free_reg = self._find_free_register(idx, statements, exclude_reg=exclude_reg or reg)
            if free_reg == reg:
                free_reg = None

        if free_reg:
            self._prepare_reg_for_write(free_reg, program, pure_wave)
            program.append(Instruction("COPY", [reg, free_reg]))
            self.register_map[free_reg] = val
            self.physically_dirty.add(free_reg)
            self.register_map[reg] = None
        else:
            if self._needs_spill_store(val):
                spill_basin = self._get_or_alloc_spill_basin(val)
                program.append(Instruction("STORE", [reg, spill_basin]))
                self.dirty_vars.discard(val)
            self.register_map[reg] = None

    def _allocate_to_register(
        self,
        var: str,
        target_reg: str,
        idx: int,
        statements: list,
        program: list,
        pure_wave: bool = False,
    ) -> str:
        """Ensures that var is loaded in target_reg, evacuating target_reg first if necessary."""
        current_reg = next((r for r, v in self.register_map.items() if v == var), None)
        if current_reg == target_reg:
            return target_reg

        # target_reg needs to be freed if it holds a live variable
        val_in_target = self.register_map[target_reg]
        if val_in_target and self._is_live(val_in_target, idx):
            self._evacuate_live_reg(
                target_reg,
                val_in_target,
                idx,
                statements,
                program,
                pure_wave,
                exclude_reg=current_reg,
                used_in_current_stmt=(idx < len(self.stmt_inputs) and val_in_target in self.stmt_inputs[idx]),
            )

        # Now target_reg is free. Prepare it and load or copy var into it.
        self._prepare_reg_for_write(target_reg, program, pure_wave)
        if current_reg:
            program.append(Instruction("COPY", [current_reg, target_reg]))
            self.register_map[current_reg] = None
        else:
            basin = self.var_sources.get(var) or self.var_destinations.get(var)
            if not basin:
                raise ValueError(f"Unknown variable source for {var}")
            program.append(Instruction("LOAD", [target_reg, basin]))

        self.physically_dirty.add(target_reg)
        self._set_register_var(target_reg, var, is_def=False)
        return target_reg

    def _spill_all_registers(
        self,
        idx: int,
        statements: list,
        program: list,
        pure_wave: bool = False,
        use_live_out_only: bool = False,
        emit_clears: bool = True,
    ):
        """Spills all currently mapped live variables to their memory basins and clears the register map."""
        spilled_vars: set[str] = set()
        for reg in ['A', 'B', 'C', 'D']:
            var = self.register_map[reg]
            if var is not None:
                is_live_here = (var in self.live_out[idx]) if use_live_out_only else self._is_live(var, idx)
                if is_live_here and var not in spilled_vars and self._needs_spill_store(var):
                    spill_basin = self._get_or_alloc_spill_basin(var)
                    program.append(Instruction("STORE", [reg, spill_basin]))
                    self.dirty_vars.discard(var)
                    spilled_vars.add(var)
                if emit_clears:
                    self._clear_reg(reg, program)
                else:
                    self.register_map[reg] = None
            elif not pure_wave and reg in self.physically_dirty:
                if emit_clears:
                    self._clear_reg(reg, program)

    def _set_register_var(self, dest_reg: str, dest_var: str, is_def: bool = False):
        """Maps dest_var to dest_reg, detaching read-only input basins when dest_var is redefined."""
        if is_def:
            self.dirty_vars.add(dest_var)
        if (
            is_def
            and dest_var in self.read_only_input_vars
            and self.var_sources.get(dest_var) == self.input_basins_by_var.get(dest_var)
        ):
            self.var_sources.pop(dest_var, None)
        for r, v in list(self.register_map.items()):
            if v == dest_var and r != dest_reg:
                self.register_map[r] = None
        self.register_map[dest_reg] = dest_var

    def compile(
        self,
        inputs: dict[str, str],
        outputs: dict[str, str],
        statements: list[tuple],
        subroutines: dict[str, dict] | None = None,
        pure_wave: bool = False,
        preallocated_scratch_basins: dict[str, str] | None = None,
    ) -> CompiledLogosProgram:
        """
        Compiles a high-level list of statements into Level 5/6 instructions.
        """
        preseeded = dict(preallocated_scratch_basins or {})
        if self._compile_count == 0 and self.allocated_scratch_basins:
            for k_var, b_val in self.allocated_scratch_basins.items():
                preseeded.setdefault(k_var, b_val)
        self._compile_count += 1

        self.register_map = {'A': None, 'B': None, 'C': None, 'D': None}
        self.physically_dirty = set()
        self.dirty_vars = set()
        self._pending_store_reg_alias = None
        self.input_basins_by_var = inputs.copy()
        self.read_only_input_vars = set(inputs.keys()) - set(outputs.keys())
        self.var_sources = inputs.copy()
        self.var_destinations = outputs.copy()
        self.allocated_scratch_basins = dict(preseeded)
        for k_var, b_val in self.allocated_scratch_basins.items():
            if k_var not in self.var_sources and k_var not in self.var_destinations:
                self.var_sources[k_var] = b_val

        cond_jump_targets = {
            stmt[2] for stmt in statements if stmt[0] == "JUMP_IF_ACTIVE" and len(stmt) > 2
        }

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

        # Pre-copy read-only input variables that are mutated inside loops into dedicated scratch basins
        # so backward jumps read the updated loop state without overwriting insulated input basins.
        label_positions: dict[str, int] = {}
        has_backedge = False
        redefined_vars: set[str] = set()
        for s_idx, st in enumerate(statements):
            s_op = st[0]
            if s_op == "LABEL" and len(st) > 1:
                label_positions[str(st[1])] = s_idx
            elif s_op == "JUMP" and len(st) > 1 and str(st[1]) in label_positions or s_op in ("JUMP_IF_ACTIVE", "JUMP_IF_COLLAPSED") and len(st) > 2 and str(st[2]) in label_positions:
                has_backedge = True
            elif s_op in ("OP", "COND_ASSIGN", "LOAD_INDIRECT", "CLEAR_VAR") and len(st) > 1:
                redefined_vars.add(str(st[1]))

        loop_shadow_basin_map: dict[str, str] = {}
        if has_backedge:
            for ro_var in sorted(self.read_only_input_vars):
                if ro_var in redefined_vars and ro_var in self.input_basins_by_var:
                    orig_in_basin = self.input_basins_by_var[ro_var]
                    self.var_sources.pop(ro_var, None)
                    scratch_b = self._get_or_alloc_spill_basin(ro_var)
                    loop_shadow_basin_map[ro_var] = scratch_b
                    loop_shadow_basin_map[orig_in_basin] = scratch_b
                    if not self.live_in or ro_var in self.live_in[0]:
                        self._prepare_reg_for_write('A', program, pure_wave)
                        program.append(Instruction("LOAD", ['A', orig_in_basin]))
                        program.append(Instruction("STORE", ['A', scratch_b]))
                        self._clear_reg('A', program)

        _reg_and_wildcard_targets = {
            "A", "B", "C", "D", "ALL", "*", "Basin_ALL",
            "RA", "RB", "RC", "RD", "S_RA", "S_RB", "S_RC", "S_RD",
            "S_RA_B", "S_RB_B", "S_RC_B", "S_RD_B",
            "Register_A", "Register_B", "Register_C", "Register_D",
        }

        def _resolve_analog_target(raw_target: str) -> str:
            if has_backedge and raw_target in loop_shadow_basin_map:
                return loop_shadow_basin_map[raw_target]
            if raw_target not in _reg_and_wildcard_targets and not raw_target.startswith("Basin_"):
                resolved = (
                    self.allocated_scratch_basins.get(raw_target)
                    or self.var_destinations.get(raw_target)
                    or self.var_sources.get(raw_target)
                )
                if resolved:
                    return resolved
            return raw_target

        for idx, stmt in enumerate(statements):
            op_type = stmt[0]

            if op_type == "NUDGE":
                nudge_target = _resolve_analog_target(str(stmt[1]))
                program.append(Instruction("NUDGE", [nudge_target, stmt[2]]))
            elif op_type == "SETTLE":
                program.append(Instruction("SETTLE", [stmt[1]]))
            elif op_type == "ASSERT_MASS":
                assert_target = _resolve_analog_target(str(stmt[1]))
                program.append(Instruction("ASSERT_MASS", [assert_target, stmt[2]]))
            elif op_type == "OP":
                dest_var, op_name, src1, src2 = stmt[1], stmt[2], stmt[3], stmt[4]
                is_unary_not = op_name in ("NOT", "NOT_WAVE")

                # 1. Allocate src1 into Register A
                self._allocate_to_register(src1, 'A', idx, statements, program, pure_wave=pure_wave)

                # 2. Allocate src2 into Register B (unless unary NOT / NOT_WAVE)
                if not is_unary_not:
                    if src2 == src1:
                        val_in_b = self.register_map['B']
                        if val_in_b and val_in_b != src1 and self._is_live(val_in_b, idx):
                            self._evacuate_live_reg(
                                'B',
                                val_in_b,
                                idx,
                                statements,
                                program,
                                pure_wave,
                                exclude_reg='A',
                            )
                        self._prepare_reg_for_write('B', program, pure_wave)
                        program.append(Instruction("COPY", ['A', 'B']))
                        self.physically_dirty.add('B')
                        self.register_map['A'] = src1
                        self.register_map['B'] = src2
                    else:
                        # Protect Register A while allocating src2 into B
                        saved_a = self.register_map['A']
                        self._allocate_to_register(src2, 'B', idx, statements, program, pure_wave=pure_wave)
                        if self.register_map['A'] != saved_a:
                            self._allocate_to_register(src1, 'A', idx, statements, program, pure_wave=pure_wave)

                # 3. Find a destination register for the output (C or D preferred, or A/B for in-place/aligned pure-wave loop ops)
                next_op_stmt = statements[idx + 1] if (idx + 1 < len(statements)) else None
                if pure_wave and has_backedge and dest_var == src1:
                    dest_reg = 'A'
                elif (
                    pure_wave
                    and has_backedge
                    and not is_unary_not
                    and next_op_stmt is not None
                    and next_op_stmt[0] == "OP"
                    and next_op_stmt[4] == dest_var
                    and dest_var not in self.live_out[idx + 1]
                    and not self._used_before_block_end(src2, idx, statements)
                    and not self._needs_spill_store(src2)
                ):
                    dest_reg = 'B'
                else:
                    dest_reg = 'C' if op_name not in ("AND", "AND_MS", "AND_WAVE") else 'D'
                    if self.register_map[dest_reg] and self._is_live(self.register_map[dest_reg], idx):
                        dying_vars = set()
                        if src1 and not self._is_live(src1, idx):
                            dying_vars.add(src1)
                        if src2 and not self._is_live(src2, idx):
                            dying_vars.add(src2)

                        candidate_regs = ['C', 'D'] if dest_reg == 'C' else ['D', 'C']

                        def get_reg_cost(
                            r,
                            _src1=src1,
                            _src2=src2,
                            _idx=idx,
                            _dying_vars=dying_vars,
                        ):
                            v = self.register_map[r]
                            if r == 'A' and v == _src1 and _src1 in self.live_out[_idx]:
                                return 100
                            if r == 'B' and v == _src2 and _src2 in self.live_out[_idx]:
                                return 100
                            if v is None:
                                return 0
                            if v in _dying_vars:
                                return 1
                            if not self._is_live(v, _idx):
                                return 2
                            if self.var_destinations.get(v) or self.var_sources.get(v):
                                return 3
                            return 4

                        dest_reg = min(candidate_regs, key=get_reg_cost)

                # Check if dest_reg contains a live variable, evacuate if necessary
                val_in_dest = self.register_map[dest_reg]
                if (
                    val_in_dest
                    and val_in_dest != dest_var
                    and val_in_dest in self.live_out[idx]
                ):
                    self._evacuate_live_reg(
                        dest_reg,
                        val_in_dest,
                        idx,
                        statements,
                        program,
                        pure_wave,
                        allowed_free_regs=('C', 'D'),
                    )

                # Emit CLEAR on destination register if it held a value or is physically dirty in legacy mode
                if (val_in_dest and not (pure_wave and has_backedge)) or (not pure_wave and dest_reg in self.physically_dirty):
                    self._clear_reg(dest_reg, program)

                # Emit the gate operation
                if is_unary_not:
                    program.append(Instruction(op_name, [dest_reg, 'A']))
                else:
                    program.append(Instruction(op_name, [dest_reg]))
                self.physically_dirty.add(dest_reg)
                self._set_register_var(dest_reg, dest_var, is_def=True)

            elif op_type == "STORE":
                src_var, dest_basin = stmt[1], stmt[2]
                alias_pair = self._pending_store_reg_alias
                self._pending_store_reg_alias = None
                if alias_pair is not None and alias_pair[0] == src_var and self.register_map.get(alias_pair[1]) is not None:
                    reg_src = alias_pair[1]
                else:
                    reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                if not reg_src:
                    basin = self.var_sources.get(src_var) or self.var_destinations.get(src_var)
                    if not basin:
                        raise ValueError(f"Cannot store variable {src_var}: Not loaded in any register and no input source defined")

                    reg_src = self._find_free_register(idx, statements) or 'C'
                    val_in_reg = self.register_map[reg_src]
                    if val_in_reg and self._is_live(val_in_reg, idx):
                        self._evacuate_live_reg(
                            reg_src,
                            val_in_reg,
                            idx,
                            statements,
                            program,
                            pure_wave,
                            exclude_reg=reg_src,
                        )
                    self._prepare_reg_for_write(reg_src, program, pure_wave)
                    program.append(Instruction("LOAD", [reg_src, basin]))
                    self.physically_dirty.add(reg_src)
                    self.register_map[reg_src] = src_var

                program.append(Instruction("STORE", [reg_src, dest_basin]))
                self.dirty_vars.discard(src_var)
                if src_var not in self.read_only_input_vars:
                    self.var_sources.setdefault(src_var, dest_basin)

            elif op_type == "LOAD":
                dest_var, source_basin = stmt[1], stmt[2]
                candidate_regs = ['C', 'D', 'A', 'B']

                def get_reg_cost(r, _idx=idx):
                    v = self.register_map[r]
                    if v is None:
                        return 0
                    if not self._is_live(v, _idx):
                        return 1
                    if self.var_destinations.get(v) or self.var_sources.get(v):
                        return 2
                    return 3

                dest_reg = min(candidate_regs, key=get_reg_cost)
                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and val_in_dest in self.live_out[idx]:
                    self._evacuate_live_reg(
                        dest_reg,
                        val_in_dest,
                        idx,
                        statements,
                        program,
                        pure_wave,
                        exclude_reg=dest_reg,
                    )
                self._prepare_reg_for_write(dest_reg, program, pure_wave)
                program.append(Instruction("LOAD", [dest_reg, source_basin]))
                self.physically_dirty.add(dest_reg)
                is_redef = not (
                    dest_var in self.read_only_input_vars
                    and source_basin == self.input_basins_by_var.get(dest_var)
                )
                self._set_register_var(dest_reg, dest_var, is_def=is_redef)
                self.dirty_vars.discard(dest_var)
                self.var_sources[dest_var] = source_basin

            elif op_type == "CALL_SUB":
                sub_name = stmt[1]
                program.append(Instruction("CALL", [sub_name]))
                if not pure_wave:
                    self.physically_dirty.update({'A', 'B', 'C', 'D'})

            elif op_type == "RETURN" or op_type == "RET":
                program.append(Instruction("RET", []))

            elif op_type == "COND_ASSIGN":
                dest_var, cond_var, true_var, false_var = stmt[1], stmt[2], stmt[3], stmt[4]

                if true_var == false_var:
                    src_var = true_var
                    reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                    if not reg_src:
                        candidate_regs = ['C', 'D', 'A', 'B']

                        def get_copy_src_cost(r, _idx=idx):
                            v = self.register_map[r]
                            if v is None:
                                return 0
                            if not self._is_live(v, _idx):
                                return 1
                            if self.var_destinations.get(v) or self.var_sources.get(v):
                                return 2
                            return 3

                        target_src_reg = min(candidate_regs, key=get_copy_src_cost)
                        reg_src = self._allocate_to_register(
                            src_var, target_src_reg, idx, statements, program, pure_wave=pure_wave
                        )

                    if dest_var == src_var:
                        continue

                    next_stmt = statements[idx + 1] if (idx + 1 < len(statements)) else None
                    if (
                        next_stmt is not None
                        and next_stmt[0] == "STORE"
                        and next_stmt[1] == dest_var
                        and dest_var not in self.live_out[idx + 1]
                    ):
                        if src_var in self.live_out[idx]:
                            self._pending_store_reg_alias = (dest_var, reg_src)
                        else:
                            self._set_register_var(reg_src, dest_var, is_def=True)
                        continue

                    if src_var not in self.live_out[idx]:
                        self._set_register_var(reg_src, dest_var, is_def=True)
                        continue

                    candidate_dest_regs = [r for r in ['C', 'D', 'A', 'B'] if r != reg_src]

                    def get_copy_dest_cost(r, _idx=idx):
                        v = self.register_map[r]
                        if v is None:
                            return 0
                        if not self._is_live(v, _idx):
                            return 1
                        if self.var_destinations.get(v) or self.var_sources.get(v):
                            return 2
                        return 3

                    dest_reg = min(candidate_dest_regs, key=get_copy_dest_cost)
                    val_in_dest = self.register_map[dest_reg]
                    if val_in_dest and val_in_dest in self.live_out[idx]:
                        self._evacuate_live_reg(
                            dest_reg,
                            val_in_dest,
                            idx,
                            statements,
                            program,
                            pure_wave,
                            exclude_reg=reg_src,
                        )
                    self._prepare_reg_for_write(dest_reg, program, pure_wave)
                    program.append(Instruction("COPY", [reg_src, dest_reg]))
                    self.physically_dirty.add(dest_reg)
                    self._set_register_var(dest_reg, dest_var, is_def=True)
                    continue

                # Evacuate any unrelated live variable in D before we lock A, B, C
                val_in_d = self.register_map['D']
                if val_in_d and val_in_d not in (cond_var, true_var, false_var) and val_in_d in self.live_out[idx]:
                    if self._needs_spill_store(val_in_d):
                        spill_basin = self._get_or_alloc_spill_basin(val_in_d)
                        program.append(Instruction("STORE", ['D', spill_basin]))
                        self.dirty_vars.discard(val_in_d)
                    self.register_map['D'] = None

                # Allocate inputs to registers A, B, C respectively, handling repeated operand aliases cleanly
                self._allocate_to_register(cond_var, 'A', idx, statements, program, pure_wave=pure_wave)
                if true_var == cond_var:
                    val_in_b = self.register_map['B']
                    if (
                        val_in_b
                        and val_in_b != cond_var
                        and self._is_live(val_in_b, idx)
                        and self._needs_spill_store(val_in_b)
                    ):
                        spill_basin = self._get_or_alloc_spill_basin(val_in_b)
                        program.append(Instruction("STORE", ['B', spill_basin]))
                        self.dirty_vars.discard(val_in_b)
                    self._prepare_reg_for_write('B', program, pure_wave)
                    program.append(Instruction("COPY", ['A', 'B']))
                    self.physically_dirty.add('B')
                    self.register_map['A'] = cond_var
                    self.register_map['B'] = true_var
                else:
                    self._allocate_to_register(true_var, 'B', idx, statements, program, pure_wave=pure_wave)
                    if self.register_map['A'] != cond_var:
                        self._allocate_to_register(cond_var, 'A', idx, statements, program, pure_wave=pure_wave)

                if false_var in (cond_var, true_var):
                    src_alias_reg = 'A' if false_var == cond_var else 'B'
                    val_in_c = self.register_map['C']
                    if (
                        val_in_c
                        and val_in_c != false_var
                        and self._is_live(val_in_c, idx)
                        and self._needs_spill_store(val_in_c)
                    ):
                        spill_basin = self._get_or_alloc_spill_basin(val_in_c)
                        program.append(Instruction("STORE", ['C', spill_basin]))
                        self.dirty_vars.discard(val_in_c)
                    self._prepare_reg_for_write('C', program, pure_wave)
                    program.append(Instruction("COPY", [src_alias_reg, 'C']))
                    self.physically_dirty.add('C')
                    self.register_map['C'] = false_var
                else:
                    self._allocate_to_register(false_var, 'C', idx, statements, program, pure_wave=pure_wave)
                    if self.register_map['A'] != cond_var:
                        self._allocate_to_register(cond_var, 'A', idx, statements, program, pure_wave=pure_wave)
                    if self.register_map['B'] != true_var:
                        self._allocate_to_register(true_var, 'B', idx, statements, program, pure_wave=pure_wave)

                dest_reg = 'D'
                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and val_in_dest in self.live_out[idx]:
                    other_reg = next((r for r, v in self.register_map.items() if r != dest_reg and v == val_in_dest), None)
                    if other_reg is None and self._needs_spill_store(val_in_dest):
                        spill_basin = self._get_or_alloc_spill_basin(val_in_dest)
                        program.append(Instruction("STORE", [dest_reg, spill_basin]))
                        self.dirty_vars.discard(val_in_dest)
                    self.register_map[dest_reg] = None

                self._prepare_reg_for_write(dest_reg, program, pure_wave)
                # Emit COPY false_var -> dest_reg
                program.append(Instruction("COPY", ['C', dest_reg]))
                # Emit CMOVE dest_reg, true_var, cond_var (which are B and A respectively)
                program.append(Instruction("CMOVE", [dest_reg, 'B', 'A']))
                self.physically_dirty.add(dest_reg)

                self._set_register_var(dest_reg, dest_var, is_def=True)

            elif op_type == "LOAD_INDIRECT":
                dest_var, array_prefix, addr_var = stmt[1], stmt[2], stmt[3]

                if isinstance(addr_var, (list, tuple)):
                    self._allocate_to_register(addr_var[0], 'C', idx, statements, program, pure_wave=pure_wave)
                    self._allocate_to_register(addr_var[1], 'D', idx, statements, program, pure_wave=pure_wave)
                    if self.register_map['C'] != addr_var[0]:
                        self._allocate_to_register(addr_var[0], 'C', idx, statements, program, pure_wave=pure_wave)
                    reg_addr = ['C', 'D']
                else:
                    self._allocate_to_register(addr_var, 'D', idx, statements, program, pure_wave=pure_wave)
                    reg_addr = 'D'

                forbidden_regs = reg_addr if isinstance(reg_addr, list) else [reg_addr]
                candidate_regs = [r for r in ['A', 'B', 'C', 'D'] if r not in forbidden_regs]

                def get_reg_cost(r, _idx=idx):
                    v = self.register_map[r]
                    if v is None:
                        return 0
                    if not self._is_live(v, _idx):
                        return 1
                    if self.var_destinations.get(v) or self.var_sources.get(v):
                        return 2
                    return 3

                dest_reg = min(candidate_regs, key=get_reg_cost)

                val_in_dest = self.register_map[dest_reg]
                if val_in_dest and val_in_dest in self.live_out[idx]:
                    self._evacuate_live_reg(
                        dest_reg,
                        val_in_dest,
                        idx,
                        statements,
                        program,
                        pure_wave,
                        allowed_free_regs=tuple(candidate_regs),
                    )

                self._prepare_reg_for_write(dest_reg, program, pure_wave)
                program.append(Instruction("LOAD_INDIRECT", [dest_reg, array_prefix, reg_addr]))
                self.physically_dirty.add(dest_reg)
                self._set_register_var(dest_reg, dest_var, is_def=True)

            elif op_type == "STORE_INDIRECT":
                src_var, array_prefix, addr_var = stmt[1], stmt[2], stmt[3]

                reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                if not reg_src:
                    basin = self.var_sources.get(src_var) or self.var_destinations.get(src_var)
                    if not basin:
                        raise ValueError(f"Cannot store variable {src_var}: Not loaded in any register")
                    reg_src = self._allocate_to_register(src_var, 'A', idx, statements, program, pure_wave=pure_wave)

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
                    self._allocate_to_register(src_var, target_reg, idx, statements, program, pure_wave=pure_wave)
                    reg_src = target_reg

                if isinstance(addr_var, (list, tuple)):
                    self._allocate_to_register(addr_var[0], 'C', idx, statements, program, pure_wave=pure_wave)
                    self._allocate_to_register(addr_var[1], 'D', idx, statements, program, pure_wave=pure_wave)
                    reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                    if not reg_src:
                        reg_src = self._allocate_to_register(src_var, 'A', idx, statements, program, pure_wave=pure_wave)
                    reg_addr = ['C', 'D']
                else:
                    self._allocate_to_register(addr_var, 'D', idx, statements, program, pure_wave=pure_wave)
                    reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                    if not reg_src:
                        reg_src = self._allocate_to_register(src_var, 'A', idx, statements, program, pure_wave=pure_wave)
                    reg_addr = 'D'

                program.append(Instruction("STORE_INDIRECT", [reg_src, array_prefix, reg_addr]))

                if reg_src is not None and src_var not in self.live_out[idx]:
                    self._clear_reg(reg_src, program)

            elif op_type == "LABEL":
                self._spill_all_registers(
                    idx,
                    statements,
                    program,
                    pure_wave=pure_wave,
                    emit_clears=not (pure_wave and has_backedge),
                )
                label_name = stmt[1]
                program.append(Instruction("LABEL", [label_name]))
                if label_name in cond_jump_targets:
                    self.physically_dirty.update({'A', 'B', 'C', 'D'})

            elif op_type == "JUMP":
                self._spill_all_registers(
                    idx,
                    statements,
                    program,
                    pure_wave=pure_wave,
                    use_live_out_only=True,
                    emit_clears=not (pure_wave and has_backedge),
                )
                label_name = stmt[1]
                program.append(Instruction("JUMP", [label_name]))

            elif op_type == "JUMP_IF_ACTIVE":
                cond_var, label_name = stmt[1], stmt[2]
                reg_cond = next((r for r, v in self.register_map.items() if v == cond_var), None)
                if not reg_cond:
                    reg_cond = self._allocate_to_register(cond_var, 'A', idx, statements, program, pure_wave=pure_wave)

                fallthrough_live = self.live_in[idx + 1] if (idx + 1 < len(self.live_in)) else set()
                spilled_vars: set[str] = set()
                for reg in ['A', 'B', 'C', 'D']:
                    if reg != reg_cond:
                        var = self.register_map[reg]
                        if var is not None:
                            if var in self.live_out[idx] and var not in spilled_vars and self._needs_spill_store(var):
                                spill_basin = self._get_or_alloc_spill_basin(var)
                                program.append(Instruction("STORE", [reg, spill_basin]))
                                self.dirty_vars.discard(var)
                                spilled_vars.add(var)
                            if pure_wave and var in fallthrough_live:
                                pass
                            elif not (pure_wave and has_backedge):
                                self._clear_reg(reg, program)
                            else:
                                self.register_map[reg] = None
                        elif not pure_wave and reg in self.physically_dirty:
                            self._clear_reg(reg, program)

                # Spill reg_cond BEFORE JUMP_IF_ACTIVE so taken-branch targets read the live condition value
                var = self.register_map[reg_cond]
                if var is not None and var in self.live_out[idx] and var not in spilled_vars and self._needs_spill_store(var):
                    spill_basin = self._get_or_alloc_spill_basin(var)
                    program.append(Instruction("STORE", [reg_cond, spill_basin]))
                    self.dirty_vars.discard(var)
                    spilled_vars.add(var)

                program.append(Instruction("JUMP_IF_ACTIVE", [reg_cond, label_name]))
                if not (pure_wave and has_backedge):
                    self._clear_reg(reg_cond, program)
                else:
                    self.register_map[reg_cond] = None

            elif op_type == "CLEAR_VAR":
                var_name = stmt[1]
                reg_var = next((r for r, v in self.register_map.items() if v == var_name), None)
                if not reg_var:
                    reg_var = self._find_free_register(idx, statements) or 'C'
                    val_in_reg = self.register_map[reg_var]
                    if val_in_reg and self._is_live(val_in_reg, idx):
                        self._evacuate_live_reg(
                            reg_var,
                            val_in_reg,
                            idx,
                            statements,
                            program,
                            pure_wave,
                            exclude_reg=reg_var,
                        )

                self._clear_reg(reg_var, program)
                if var_name in self.live_out[idx]:
                    self._set_register_var(reg_var, var_name, is_def=True)

        # Guarantee all registers collapse to -1 cleanly at program termination
        program.append(Instruction("CLEAR", ["A"]))
        program.append(Instruction("CLEAR", ["B"]))
        program.append(Instruction("CLEAR", ["C"]))
        program.append(Instruction("CLEAR", ["D"]))

        if subroutines:
            program.append(Instruction("JUMP", ["L_COMPILER_EXIT"]))
            global_used_basins = (
                set(self._reserved_basin_names)
                | set(self.input_basins_by_var.values())
                | set(self.var_sources.values())
                | set(self.var_destinations.values())
                | set(self.allocated_scratch_basins.values())
            )
            for sub_name, sub_def in subroutines.items():
                sub_compiler = type(self)()
                sub_compiler._reserved_basin_names = set(global_used_basins)
                sub_insts = sub_compiler.compile(
                    sub_def.get("inputs", {}),
                    sub_def.get("outputs", {}),
                    sub_def.get("statements", []),
                    pure_wave=pure_wave,
                )
                for k, v in sub_compiler.allocated_scratch_basins.items():
                    self.allocated_scratch_basins.setdefault(f"{sub_name}_{k}", v)
                    global_used_basins.add(v)
                program.append(Instruction("LABEL", [sub_name]))
                program.extend(sub_insts)
                if not sub_insts or sub_insts[-1].op.upper() not in ("RET", "RETURN"):
                    program.append(Instruction("RET", []))
            program.append(Instruction("LABEL", ["L_COMPILER_EXIT"]))

        return CompiledLogosProgram(
            program,
            allocated_scratch_basins=self.allocated_scratch_basins,
            pure_wave=pure_wave,
        )

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
