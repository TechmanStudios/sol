#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Aether Compiler (Level 6/7 Hybrid Logic Compiler)
=================================================
Parses object-oriented Python-based Aether agents using AST visitor traversal
and compiles them down to optimal, register-allocated SOL ALU micro-instructions.
"""

import ast
import inspect
import sys
from pathlib import Path
from typing import Type

# Add project root and scratch paths to python path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from logos_compiler import LogosCompiler
from hybrid_subsystem_framework import Instruction

class AetherAgent:
    """
    Base class for Aether Agents. Subclasses define configure() to map variables to basins,
    and flow() containing the Python statements mapping the logic.
    """
    def __init__(self):
        self.inputs = {}
        self.outputs = {}
        self.configure()

    def configure(self):
        """Map symbolic variables to physical memory attractor basins."""
        pass

    def flow(self):
        """Logic execution flow."""
        pass


class AetherASTVisitor(ast.NodeVisitor):
    """AST visitor to transform a Python function definition into Logos compiler statements."""
    def __init__(self, agent_instance: AetherAgent):
        self.agent = agent_instance
        self.statements = []
        self.label_counter = 0
        self.temp_counter = 0

    def _next_label(self, prefix: str = "L") -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def _next_temp(self) -> str:
        self.temp_counter += 1
        return f"aether_tmp_{self.temp_counter}"

    def visit_Assign(self, node: ast.Assign):
        # Handle self.target = expr
        if len(node.targets) != 1:
            raise ValueError("Multiple assignment targets not supported in Aether flow.")
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
                # Variable assignment (copy): we compile copy through a dummy COND_ASSIGN to dest_var
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
            # Ternary logic: body if test else orelse
            cond = self._visit_expression(expr.test)
            true_val = self._visit_expression(expr.body)
            false_val = self._visit_expression(expr.orelse)
            var_name = dest_var if dest_var else self._next_temp()
            self.statements.append(("COND_ASSIGN", var_name, cond, true_val, false_val))
            return var_name

        raise ValueError(f"Unsupported Aether expression format: {ast.dump(expr)}")

    def visit_If(self, node: ast.If):
        cond_var = self._visit_expression(node.test)
        true_label = self._next_label("L_TRUE")
        end_label = self._next_label("L_END")
        
        # Jump to true branch if active
        self.statements.append(("JUMP_IF_ACTIVE", cond_var, true_label))
        
        # False branch (Else)
        for stmt in node.orelse:
            self.visit(stmt)
        self.statements.append(("JUMP", end_label))
        
        # True branch
        self.statements.append(("LABEL", true_label))
        for stmt in node.body:
            self.visit(stmt)
            
        self.statements.append(("LABEL", end_label))


class AetherCompiler:
    """Aether Compiler: Orchestrates class inspection, AST extraction, and compilation."""
    @staticmethod
    def compile_agent(agent_cls: Type[AetherAgent]) -> list[Instruction]:
        # Instantiate agent to run configure()
        agent = agent_cls()
        
        import textwrap
        flow_src = textwrap.dedent(inspect.getsource(agent_cls.flow))
        
        parsed_ast = ast.parse(flow_src)
        
        # Traverse AST nodes
        visitor = AetherASTVisitor(agent)
        func_def = parsed_ast.body[0]
        if not isinstance(func_def, ast.FunctionDef):
            raise TypeError("Expected function definition inside parsed AST.")
            
        for stmt in func_def.body:
            visitor.visit(stmt)
            
        logos = LogosCompiler()
        return logos.compile(agent.inputs, agent.outputs, visitor.statements)

    @staticmethod
    def compile_flow_src(inputs: dict[str, str], outputs: dict[str, str], flow_src: str) -> list[Instruction]:
        import textwrap
        flow_src = textwrap.dedent(flow_src)
        if not flow_src.strip().startswith("def "):
            indented = "\n".join("    " + line for line in flow_src.splitlines())
            flow_src = f"def flow(self):\n{indented}"
            
        parsed_ast = ast.parse(flow_src)
        agent = type("MockAgent", (), {"inputs": inputs.copy(), "outputs": outputs.copy()})()
        visitor = AetherASTVisitor(agent)
        func_def = parsed_ast.body[0]
        for stmt in func_def.body:
            visitor.visit(stmt)
            
        logos = LogosCompiler()
        return logos.compile(inputs, outputs, visitor.statements)

if __name__ == "__main__":
    # Test local compilation
    class SimpleXorAgent(AetherAgent):
        def configure(self):
            self.inputs = {"x": "Basin_A", "y": "Basin_B"}
            self.outputs = {"z": "Basin_SUM"}
        def flow(self):
            self.z = self.x ^ self.y
            
    insts = AetherCompiler.compile_agent(SimpleXorAgent)
    print("Test Compilation Success! Generated instructions:")
    for idx, inst in enumerate(insts):
        print(f"  {idx+1}. {inst.op} {inst.args}")
