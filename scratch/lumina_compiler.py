#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Lumina Compiler (Level 6/7 Advanced Substrate Compiler)
=========================================================
Parses object-oriented Python-based Lumina agents using AST visitor traversal.
Supports advanced control-flow constructs (loops) and analog assertions/nudges.
Compiles down to register-allocated SOL ALU micro-instructions.
"""

import ast
import inspect
import sys
from pathlib import Path
from typing import Type, Any, Optional

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from logos_compiler import LogosCompiler
from hybrid_subsystem_framework import Instruction

class ComponentInstance:
    """Bound instance of a library sub-component."""
    def __init__(self, name: str, agent_cls: Type['LuminaAgent'], inputs: dict[str, str], outputs: dict[str, str], source_code: str):
        self.name = name
        self.agent_cls = agent_cls
        self.inputs = inputs
        self.outputs = outputs
        self.source_code = source_code

    def run(self):
        """Placeholder stub for AST visitor inlining."""
        pass


class ComponentASTTransformer(ast.NodeTransformer):
    """Rewrites sub-component AST to map local self attributes to parent variable names."""
    def __init__(self, instance_name: str, inputs_map: dict[str, str], outputs_map: dict[str, str], sub_inputs: dict[str, str], sub_outputs: dict[str, str]):
        self.instance_name = instance_name
        self.inputs_map = inputs_map
        self.outputs_map = outputs_map
        self.sub_inputs = sub_inputs
        self.sub_outputs = sub_outputs

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            attr = node.attr
            if attr in self.inputs_map:
                mapped = self.inputs_map[attr]
            elif attr in self.outputs_map:
                mapped = self.outputs_map[attr]
            else:
                mapped = f"{self.instance_name}_{attr}"
            return ast.Attribute(
                value=ast.Name(id="self", ctx=ast.Load()),
                attr=mapped,
                ctx=node.ctx
            )
        return self.generic_visit(node)


class LuminaAgent:
    """
    Base class for Lumina Agents. Subclasses define configure() to map variables to basins,
    and flow() containing Python statements mapping the logic.
    """
    def __init__(self):
        if not hasattr(self, "inputs") or not self.inputs:
            self.inputs = {}
        if not hasattr(self, "outputs") or not self.outputs:
            self.outputs = {}
        self._components = {}
        self.configure()

    def configure(self):
        """Map symbolic variables to physical memory attractor basins."""
        pass

    def flow(self):
        """Logic execution flow."""
        pass

    # Helper stubs for static analysis / typing
    def nudge(self, basin: str, amount: float):
        pass

    def settle(self, steps: int):
        pass

    def assert_mass(self, reg: str, min_mass: float):
        pass

    def use_component(self, component_name: str, inputs: dict[str, str], outputs: dict[str, str]) -> ComponentInstance:
        """Register and load a verified sub-component from the library."""
        from coding_library.library_agent import LuminaLibraryAgent
        lib = LuminaLibraryAgent()
        code = lib.load_component(component_name)
        if not code:
            raise ValueError(f"Component '{component_name}' not found in Coding Library.")
            
        # Execute the code to extract the agent class
        local_vars = {}
        exec_globals = {
            "LuminaAgent": LuminaAgent,
            "LuminaCompiler": globals().get("LuminaCompiler")
        }
        exec(code, exec_globals, local_vars)
        
        agent_cls = None
        for name, val in local_vars.items():
            if isinstance(val, type) and issubclass(val, LuminaAgent) and val != LuminaAgent:
                agent_cls = val
                break
                
        if not agent_cls:
            raise ValueError(f"No LuminaAgent subclass found for component '{component_name}'.")
            
        # Instantiate sub-agent to register its own sub-components and variables
        sub_agent = agent_cls()
        
        instance = ComponentInstance(component_name, agent_cls, inputs, outputs, code)
        self._components[component_name] = instance
        
        # Copy any sub-component instances to parent, prefixed
        for attr_name, attr_val in sub_agent.__dict__.items():
            if isinstance(attr_val, ComponentInstance):
                prefixed_name = f"{component_name}_{attr_name}"
                setattr(self, prefixed_name, attr_val)
                
        return instance


class LuminaASTVisitor(ast.NodeVisitor):
    """AST visitor to transform a Python function definition into Logos intermediate statements."""
    def __init__(self, agent_instance: LuminaAgent):
        self.agent = agent_instance
        self.statements = []
        self.label_counter = 0
        self.temp_counter = 0

    def _next_label(self, prefix: str = "L") -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def _next_temp(self) -> str:
        self.temp_counter += 1
        return f"lumina_tmp_{self.temp_counter}"

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            raise ValueError("Multiple assignment targets not supported in Lumina flow.")
        target_name = self._resolve_target(node.targets[0])
        expr_val = self._visit_expression(node.value, target_name)
        
        # If target_name is in outputs, explicitly compile a STORE operation
        if target_name in self.agent.outputs:
            self.statements.append(("STORE", target_name, self.agent.outputs[target_name]))

    def _resolve_target(self, node: ast.AST) -> str:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return node.attr
        elif isinstance(node, ast.Name):
            return node.id
        raise ValueError(f"Unsupported assignment target: {ast.dump(node)}")

    def _visit_expression(self, expr: ast.AST, dest_var: str = None) -> str:
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id == "self":
            var_name = expr.attr
            if dest_var:
                self.statements.append(("COND_ASSIGN", dest_var, var_name, var_name, var_name))
            return var_name
        elif isinstance(expr, ast.Name):
            var_name = expr.id
            if dest_var:
                self.statements.append(("COND_ASSIGN", dest_var, var_name, var_name, var_name))
            return var_name

        elif isinstance(expr, ast.BinOp):
            left = self._visit_expression(expr.left)
            right = self._visit_expression(expr.right)
            
            # Map operator classes to SOL mixed-signal logic gates
            op_map = {
                ast.BitXor: "XOR",
                ast.BitAnd: "AND_MS",
                ast.BitOr: "OR_MS",
            }
            op_type = type(expr.op)
            if op_type not in op_map:
                raise ValueError(f"Unsupported binary operator: {op_type}")
            
            op_name = op_map[op_type]
            var_name = dest_var if dest_var else self._next_temp()
            self.statements.append(("OP", var_name, op_name, left, right))
            return var_name

        elif isinstance(expr, ast.UnaryOp) and isinstance(expr.op, (ast.Invert, ast.Not)):
            operand = self._visit_expression(expr.operand)
            var_name = dest_var if dest_var else self._next_temp()
            self.statements.append(("OP", var_name, "NOT", operand, operand))
            return var_name

        elif isinstance(expr, ast.IfExp):
            cond = self._visit_expression(expr.test)
            true_val = self._visit_expression(expr.body)
            false_val = self._visit_expression(expr.orelse)
            var_name = dest_var if dest_var else self._next_temp()
            self.statements.append(("COND_ASSIGN", var_name, cond, true_val, false_val))
            return var_name

        raise ValueError(f"Unsupported Lumina expression format: {ast.dump(expr)}")

    def visit_If(self, node: ast.If):
        cond_var = self._visit_expression(node.test)
        true_label = self._next_label("L_TRUE")
        end_label = self._next_label("L_END")
        
        self.statements.append(("JUMP_IF_ACTIVE", cond_var, true_label))
        
        for stmt in node.orelse:
            self.visit(stmt)
        self.statements.append(("JUMP", end_label))
        
        self.statements.append(("LABEL", true_label))
        for stmt in node.body:
            self.visit(stmt)
            
        self.statements.append(("LABEL", end_label))

    def visit_While(self, node: ast.While):
        start_label = self._next_label("L_LOOP_START")
        end_label = self._next_label("L_LOOP_END")
        
        self.statements.append(("LABEL", start_label))
        cond_var = self._visit_expression(node.test)
        
        # Invert condition to exit loop
        cond_inv = self._next_temp()
        self.statements.append(("OP", cond_inv, "NOT", cond_var, cond_var))
        
        self.statements.append(("JUMP_IF_ACTIVE", cond_inv, end_label))
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.statements.append(("JUMP", start_label))
        self.statements.append(("LABEL", end_label))

    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            call = node.value
            # Check if it is a call to a sub-component run(), e.g. self.ha1.run()
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Attribute):
                inner_attr = call.func.value
                if isinstance(inner_attr.value, ast.Name) and inner_attr.value.id == "self":
                    instance_name = inner_attr.attr
                    method_name = call.func.attr
                    if method_name == "run" and hasattr(self.agent, instance_name):
                        comp_inst = getattr(self.agent, instance_name)
                        if isinstance(comp_inst, ComponentInstance):
                            self._inline_component(comp_inst)
                            return
            # Standard self helper calls (nudge, settle, assert_mass)
            elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == "self":
                method_name = call.func.attr
                if method_name in ("nudge", "settle", "assert_mass"):
                    args = [self._resolve_constant(arg) for arg in call.args]
                    self.statements.append((method_name.upper(), *args))
                    return
        self.generic_visit(node)

    def _inline_component(self, comp_inst: ComponentInstance):
        import textwrap
        # Get the flow method source code
        try:
            flow_src = textwrap.dedent(inspect.getsource(comp_inst.agent_cls.flow))
        except (OSError, TypeError):
            if hasattr(comp_inst.agent_cls, "_source"):
                flow_src = comp_inst.agent_cls._source
            else:
                flow_src = comp_inst.source_code
            
            # Extract flow method
            parsed = ast.parse(flow_src)
            for node in ast.walk(parsed):
                if isinstance(node, ast.FunctionDef) and node.name == "flow":
                    flow_src = ast.unparse(node)
                    break
            else:
                raise ValueError(f"Could not find flow() method in component '{comp_inst.name}' source.")
                
        if not flow_src.strip().startswith("def "):
            indented = "\n".join("    " + line for line in flow_src.splitlines())
            flow_src = f"def flow(self):\n{indented}"
            
        parsed_ast = ast.parse(flow_src)
        func_def = parsed_ast.body[0]
        
        # Instantiate sub-agent to get its inputs and outputs lists
        sub_agent = comp_inst.agent_cls()
        
        # Transform the AST
        transformer = ComponentASTTransformer(
            instance_name=comp_inst.name,
            inputs_map=comp_inst.inputs,
            outputs_map=comp_inst.outputs,
            sub_inputs=sub_agent.inputs,
            sub_outputs=sub_agent.outputs
        )
        transformed_func = transformer.visit(func_def)
        
        # Visit statements of the transformed function definition
        for stmt in transformed_func.body:
            self.visit(stmt)

    def _resolve_constant(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
        raise ValueError(f"Lumina analog helper call arguments must be constants: {ast.dump(node)}")


class LuminaLogosCompiler(LogosCompiler):
    """
    Extended Logos Compiler supporting Lumina analog/verification instructions
    which pass through register-allocation safely.
    """
    def _allocate_to_register(self, var: str, target_reg: str, idx: int, statements: list, program: list) -> str:
        """Ensures that var is loaded in target_reg, evacuating target_reg first if necessary."""
        current_reg = next((r for r, v in self.register_map.items() if v == var), None)
        if current_reg == target_reg:
            return target_reg
            
        val_in_target = self.register_map[target_reg]
        if val_in_target and self._is_live(val_in_target, idx):
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
                    raise RuntimeError(f"Register spill failed at stmt {idx}: {statements[idx]} | No free register to save {val_in_target}")
                    
        if current_reg:
            program.append(Instruction("COPY", [current_reg, target_reg]))
            self.register_map[current_reg] = None
        else:
            basin = self.var_sources.get(var) or self.var_destinations.get(var)
            if not basin:
                raise ValueError(f"Unknown variable source for {var}")
            program.append(Instruction("LOAD", [target_reg, basin]))
            
        self._set_register_var(target_reg, var)
        return target_reg

    def compile(self, inputs: dict[str, str], outputs: dict[str, str], statements: list[tuple], subroutines: dict[str, dict] = None) -> list[Instruction]:
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
            op_type = stmt[0]
            
            if op_type == "NUDGE":
                program.append(Instruction("NUDGE", [stmt[1], stmt[2]]))
            elif op_type == "SETTLE":
                program.append(Instruction("SETTLE", [stmt[1]]))
            elif op_type == "ASSERT_MASS":
                program.append(Instruction("ASSERT_MASS", [stmt[1], stmt[2]]))
            elif op_type == "OP":
                dest_var, op_name, src1, src2 = stmt[1], stmt[2], stmt[3], stmt[4]
                self._allocate_to_register(src1, 'A', idx, statements, program)
                self._allocate_to_register(src2, 'B', idx, statements, program)
                
                dest_reg = 'C' if op_name not in ("AND", "AND_MS") else 'D'
                if self.register_map[dest_reg] and self._is_live(self.register_map[dest_reg], idx):
                    dying_vars = set()
                    if src1 and not self._is_live(src1, idx):
                        dying_vars.add(src1)
                    if src2 and not self._is_live(src2, idx):
                        dying_vars.add(src2)
                        
                    candidate_regs = ['C', 'D'] if dest_reg == 'C' else ['D', 'C']
                    
                    def get_reg_cost(r):
                        v = self.register_map[r]
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
                
                if val_in_dest:
                    program.append(Instruction("CLEAR", [dest_reg]))
                
                program.append(Instruction(op_name, [dest_reg]))
                self._set_register_var(dest_reg, dest_var)
                
            elif op_type == "STORE":
                src_var, dest_basin = stmt[1], stmt[2]
                reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                if not reg_src:
                    basin = self.var_sources.get(src_var)
                    if not basin:
                        raise ValueError(f"Cannot store variable {src_var}: Not loaded in any register and no input source defined")
                    
                    reg_src = self._find_free_register(idx, statements) or 'C'
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
                
            elif op_type in ("RETURN", "RET"):
                program.append(Instruction("RET", []))
                
            elif op_type == "COND_ASSIGN":
                dest_var, cond_var, true_var, false_var = stmt[1], stmt[2], stmt[3], stmt[4]
                self._allocate_to_register(cond_var, 'A', idx, statements, program)
                self._allocate_to_register(true_var, 'B', idx, statements, program)
                self._allocate_to_register(false_var, 'C', idx, statements, program)
                
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
                
                program.append(Instruction("COPY", ['C', dest_reg]))
                program.append(Instruction("CMOVE", [dest_reg, 'B', 'A']))
                self._set_register_var(dest_reg, dest_var)
                
            elif op_type == "LOAD_INDIRECT":
                dest_var, array_prefix, addr_var = stmt[1], stmt[2], stmt[3]
                if isinstance(addr_var, (list, tuple)):
                    self._allocate_to_register(addr_var[0], 'C', idx, statements, program)
                    self._allocate_to_register(addr_var[1], 'D', idx, statements, program)
                    reg_addr = ['C', 'D']
                else:
                    self._allocate_to_register(addr_var, 'D', idx, statements, program)
                    reg_addr = 'D'
                    
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
                reg_src = next((r for r, v in self.register_map.items() if v == src_var), None)
                if not reg_src:
                    raise ValueError(f"Cannot store variable {src_var}: Not loaded in any register")
                    
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
                if reg_src is not None and not self._is_live(src_var, idx):
                    program.append(Instruction("CLEAR", [reg_src]))
                    self.register_map[reg_src] = None

            elif op_type == "LABEL":
                self._spill_all_registers(idx, statements, program)
                program.append(Instruction("LABEL", [stmt[1]]))

            elif op_type == "JUMP":
                self._spill_all_registers(idx, statements, program)
                program.append(Instruction("JUMP", [stmt[1]]))

            elif op_type == "JUMP_IF_ACTIVE":
                cond_var, label_name = stmt[1], stmt[2]
                reg_cond = next((r for r, v in self.register_map.items() if v == cond_var), None)
                if not reg_cond:
                    reg_cond = self._allocate_to_register(cond_var, 'A', idx, statements, program)
                
                for reg in ['A', 'B', 'C', 'D']:
                    if reg != reg_cond:
                        var = self.register_map[reg]
                        if var is not None:
                            if self._is_live(var, idx):
                                spill_basin = self.var_destinations.get(var) or self.var_sources.get(var)
                                if spill_basin:
                                    program.append(Instruction("STORE", [reg, spill_basin]))
                                else:
                                    raise RuntimeError(f"Register spill failed during boundary sync for variable '{var}' at statement {idx}")
                            program.append(Instruction("CLEAR", [reg]))
                            self.register_map[reg] = None
                
                program.append(Instruction("JUMP_IF_ACTIVE", [reg_cond, label_name]))
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
                    reg_var = self._find_free_register(idx, statements) or 'C'
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
                program.append(Instruction("CLEAR", [reg_var]))
                if self._is_live(var_name, idx):
                    self.register_map[reg_var] = var_name

        program.append(Instruction("CLEAR", ["A"]))
        program.append(Instruction("CLEAR", ["B"]))
        program.append(Instruction("CLEAR", ["C"]))
        program.append(Instruction("CLEAR", ["D"]))
        
        if subroutines:
            program.append(Instruction("JUMP", ["L_COMPILER_EXIT"]))
            for sub_name, sub_def in subroutines.items():
                sub_compiler = LuminaLogosCompiler()
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


class StaticVerificationError(Exception):
    """Exception raised when static analysis detects a safety violation (e.g. mass preservation breach)."""
    pass


class StaticMassSentinel:
    """Symbolically checks compiled Logos instructions to prove register mass safety bounds."""
    
    @staticmethod
    def verify(instructions: list[Instruction], damping: float = 0.01) -> bool:
        registers = {"A": 15.0, "B": 15.0, "C": 15.0, "D": 15.0}
        active_registers = {"A": False, "B": False, "C": False, "D": False}
        
        for idx, inst in enumerate(instructions):
            op = inst.op.upper()
            args = inst.args
            
            if op == "LOAD":
                reg = args[0]
                active_registers[reg] = True
            elif op == "CLEAR":
                reg = args[0]
                active_registers[reg] = False
                registers[reg] = 15.0  # Reset mass when cleared
            elif op == "COPY":
                src, dest = args[0], args[1]
                registers[dest] = registers[src]
                active_registers[dest] = active_registers[src]
            elif op == "CMOVE":
                dest, src, cond = args[0], args[1], args[2]
                registers[dest] = min(registers[dest], registers[src])
                active_registers[dest] = active_registers[dest] or active_registers[src]
            elif op == "NUDGE":
                basin = args[0]
                amount = float(args[1])
                for reg in ('A', 'B', 'C', 'D'):
                    if reg in basin or f"R{reg}" in basin:
                        registers[reg] += amount
            elif op == "SETTLE":
                steps = int(args[0])
                for reg in ('A', 'B', 'C', 'D'):
                    if active_registers[reg]:
                        registers[reg] = max(0.0, registers[reg] - damping * steps)
                        
            # Verify active registers bounds
            for reg in ('A', 'B', 'C', 'D'):
                if active_registers[reg] and registers[reg] < 14.0:
                    raise StaticVerificationError(
                        f"Static verification failure: instruction '{inst.op} {', '.join(map(str, inst.args))}' at index {idx} "
                        f"drains Register {reg} mass to {registers[reg]:.2f} (< 14.0)."
                    )
                    
        return True


class LuminaCompiler:
    """Orchestrates class inspection, AST extraction, and Lumina compilation."""
    @staticmethod
    def compile_agent(agent_cls: Type[LuminaAgent], verify_mass: bool = True) -> list[Instruction]:
        agent = agent_cls()
        import textwrap
        try:
            flow_src = textwrap.dedent(inspect.getsource(agent_cls.flow))
        except (OSError, TypeError):
            if hasattr(agent_cls, "_source"):
                parsed = ast.parse(agent_cls._source)
                for node in ast.walk(parsed):
                    if isinstance(node, ast.FunctionDef) and node.name == "flow":
                        flow_src = ast.unparse(node)
                        break
                else:
                    raise ValueError("Could not find flow() method in dynamic agent source.")
            else:
                raise OSError("Could not get source code. Please set '_source' attribute on dynamically executed class.")
        return LuminaCompiler.compile_flow_src(agent.inputs, agent.outputs, flow_src, agent=agent, verify_mass=verify_mass)

    @staticmethod
    def compile_flow_src(inputs: dict[str, str], outputs: dict[str, str], flow_src: str, agent: Optional[LuminaAgent] = None, verify_mass: bool = True) -> list[Instruction]:
        import textwrap
        flow_src = textwrap.dedent(flow_src)
        if not flow_src.strip().startswith("def "):
            indented = "\n".join("    " + line for line in flow_src.splitlines())
            flow_src = f"def flow(self):\n{indented}"
            
        parsed_ast = ast.parse(flow_src)
        if agent is None:
            agent = type("MockAgent", (LuminaAgent,), {"inputs": inputs.copy(), "outputs": outputs.copy()})()
        visitor = LuminaASTVisitor(agent)
        func_def = parsed_ast.body[0]
        for stmt in func_def.body:
            visitor.visit(stmt)
            
        compiler = LuminaLogosCompiler()
        program = compiler.compile(inputs, outputs, visitor.statements)
        
        if verify_mass:
            StaticMassSentinel.verify(program)
            
        return program
