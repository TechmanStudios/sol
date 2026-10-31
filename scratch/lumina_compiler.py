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
from typing import Any, ClassVar

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import Instruction
from logos_compiler import CompiledLogosProgram, LogosCompiler


class ComponentInstance:
    """Bound instance of a library sub-component."""
    def __init__(self, name: str, agent_cls: type['LuminaAgent'], inputs: dict[str, str], outputs: dict[str, str], source_code: str):
        self.name = name
        self.agent_cls = agent_cls
        self.inputs = inputs
        self.outputs = outputs
        self.source_code = source_code

    def run(self):
        """Placeholder stub for AST visitor inlining."""


def _is_component_instance(obj: Any) -> bool:
    return isinstance(obj, ComponentInstance) or (
        getattr(type(obj), "__name__", "") == "ComponentInstance"
        and hasattr(obj, "agent_cls")
        and hasattr(obj, "inputs")
        and hasattr(obj, "outputs")
    )


class ComponentASTTransformer(ast.NodeTransformer):
    """Rewrites sub-component AST to map local self attributes to parent variable names."""
    def __init__(self, instance_name: str, inputs_map: dict[str, str], outputs_map: dict[str, str], sub_inputs: dict[str, str], sub_outputs: dict[str, str]):
        self.instance_name = instance_name
        self.inputs_map = inputs_map
        self.outputs_map = outputs_map
        self.sub_inputs = sub_inputs
        self.sub_outputs = sub_outputs

    def visit_Attribute(self, node: ast.Attribute):
        node = self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            attr = node.attr
            if attr in ("nudge", "settle", "assert_mass", "use_component"):
                return node
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
        return node


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
        self._component_seq = 0
        if hasattr(self, "components") and isinstance(self.components, dict):
            for alias, comp_spec in dict(self.components).items():
                self._bind_component_spec(str(alias), comp_spec)
        self.configure()

    def _bind_component_spec(self, alias: str, comp_spec: Any) -> ComponentInstance:
        """Bind a declarative component class, ComponentInstance, or library name under alias."""
        if isinstance(comp_spec, ComponentInstance):
            self._components[alias] = comp_spec
            setattr(self, alias, comp_spec)
            return comp_spec
        if isinstance(comp_spec, str):
            inst = self.use_component(comp_spec, inputs={}, outputs={}, instance_name=alias)
            setattr(self, alias, inst)
            return inst
        if isinstance(comp_spec, type) and issubclass(comp_spec, LuminaAgent):
            sub_agent = comp_spec()
            try:
                code = inspect.getsource(comp_spec)
            except (OSError, TypeError):
                code = getattr(comp_spec, "_source", "")
            in_map = {k: f"{alias}_{k}" for k in sub_agent.inputs}
            out_map = {k: f"{alias}_{k}" for k in sub_agent.outputs}
            inst = ComponentInstance(alias, comp_spec, in_map, out_map, code)
            self._components[alias] = inst
            setattr(self, alias, inst)
            for attr_name, attr_val in sub_agent.__dict__.items():
                if _is_component_instance(attr_val):
                    def _remap(w: str, _in=in_map, _out=out_map, _al=alias) -> str:
                        return _in.get(w) or _out.get(w) or f"{_al}_{w}"
                    prefixed_name = f"{alias}_{attr_name}"
                    rebound = ComponentInstance(
                        prefixed_name,
                        attr_val.agent_cls,
                        {k: _remap(v) for k, v in attr_val.inputs.items()},
                        {k: _remap(v) for k, v in attr_val.outputs.items()},
                        attr_val.source_code,
                    )
                    setattr(self, prefixed_name, rebound)
            return inst
        raise ValueError(f"Unsupported declarative component specification for '{alias}': {comp_spec!r}")

    def configure(self):
        """Map symbolic variables to physical memory attractor basins."""

    def flow(self):
        """Logic execution flow."""

    # Helper stubs for static analysis / typing
    def nudge(self, basin: str, amount: float):
        pass

    def settle(self, steps: int):
        pass

    def assert_mass(self, reg: str, min_mass: float):
        pass

    def use_component(
        self,
        component_name: str,
        inputs: dict[str, str],
        outputs: dict[str, str],
        instance_name: str | None = None,
    ) -> ComponentInstance:
        """Register and load a verified sub-component from the library with unique instance scoping."""
        from coding_library.library_agent import LuminaLibraryAgent
        lib = LuminaLibraryAgent()
        code = lib.load_component(component_name)
        if not code:
            raise ValueError(f"Component '{component_name}' not found in Coding Library.")
            
        local_vars = {}
        exec_globals = {
            "LuminaAgent": LuminaAgent,
            "LuminaCompiler": globals().get("LuminaCompiler")
        }
        exec(code, exec_globals, local_vars)  # noqa: S102

        agent_cls = None
        for val in local_vars.values():
            if isinstance(val, type) and issubclass(val, LuminaAgent) and val != LuminaAgent:
                agent_cls = val
                break
                
        if not agent_cls:
            raise ValueError(f"No LuminaAgent subclass found for component '{component_name}'.")
            
        sub_agent = agent_cls()

        if instance_name:
            alias = instance_name
        elif component_name not in self._components:
            alias = component_name
        else:
            self._component_seq += 1
            alias = f"{component_name}_{self._component_seq}"

        eff_inputs = {k: (inputs.get(k) or f"{alias}_{k}") for k in sub_agent.inputs}
        eff_inputs.update(inputs)
        eff_outputs = {k: (outputs.get(k) or f"{alias}_{k}") for k in sub_agent.outputs}
        eff_outputs.update(outputs)

        instance = ComponentInstance(alias, agent_cls, eff_inputs, eff_outputs, code)
        self._components[alias] = instance
        
        # Bind nested child components under unique prefixed names
        for attr_name, attr_val in sub_agent.__dict__.items():
            if _is_component_instance(attr_val):
                def _remap(w: str) -> str:
                    return eff_inputs.get(w) or eff_outputs.get(w) or f"{alias}_{w}"
                prefixed_name = f"{alias}_{attr_name}"
                rebound = ComponentInstance(
                    prefixed_name,
                    attr_val.agent_cls,
                    {k: _remap(v) for k, v in attr_val.inputs.items()},
                    {k: _remap(v) for k, v in attr_val.outputs.items()},
                    attr_val.source_code,
                )
                setattr(self, prefixed_name, rebound)
                
        return instance


class LuminaASTVisitor(ast.NodeVisitor):
    """AST visitor to transform a Python function definition into Logos intermediate statements."""
    def __init__(self, agent_instance: LuminaAgent, pure_wave: bool = False):
        self.agent = agent_instance
        self.pure_wave = bool(pure_wave)
        self.statements = []
        self.component_scope_basins: dict[str, str] = {}
        self.label_counter = 0
        self.temp_counter = 0

    def _next_label(self, prefix: str = "L") -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def _next_temp(self) -> str:
        self.temp_counter += 1
        return f"lumina_tmp_{self.temp_counter}"

    def _parse_subscript(self, sub_node: ast.Subscript) -> tuple[str, Any, bool]:
        """Parses self.arr[idx] / self.arr[msb, lsb] / self.arr[2] into (array_prefix, index_spec, is_const)."""
        if isinstance(sub_node.value, ast.Attribute) and isinstance(sub_node.value.value, ast.Name) and sub_node.value.value.id == "self":
            raw_arr = sub_node.value.attr
        elif isinstance(sub_node.value, ast.Name):
            raw_arr = sub_node.value.id
        else:
            raise ValueError(f"Unsupported subscript base in Lumina flow: {ast.dump(sub_node)}")

        mapped = self.agent.inputs.get(raw_arr) or self.agent.outputs.get(raw_arr)
        if mapped:
            array_prefix = mapped.removeprefix("Basin_")
        else:
            elem0 = (
                self.agent.inputs.get(f"{raw_arr}_0")
                or self.agent.outputs.get(f"{raw_arr}_0")
                or self.agent.inputs.get(f"{raw_arr}0")
                or self.agent.outputs.get(f"{raw_arr}0")
            )
            if elem0:
                stripped = elem0.removeprefix("Basin_")
                array_prefix = stripped.removesuffix("0")
            else:
                array_prefix = raw_arr

        slc = sub_node.slice
        if isinstance(slc, ast.Index):  # Python <3.9 compatibility guard
            slc = slc.value

        if isinstance(slc, ast.Constant) and isinstance(slc.value, int):
            return array_prefix, int(slc.value), True

        if isinstance(slc, ast.Tuple):
            if all(isinstance(elt, ast.Constant) and isinstance(elt.value, int) for elt in slc.elts):
                idx_val = 0
                for elt in slc.elts:
                    idx_val = (idx_val << 1) | (int(elt.value) & 1)
                return array_prefix, idx_val, True
            addr_vars = [self._visit_expression(elt) for elt in slc.elts]
            return array_prefix, addr_vars, False

        addr_var = self._visit_expression(slc)
        return array_prefix, addr_var, False

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            raise ValueError("Multiple assignment targets not supported in Lumina flow.")
        target = node.targets[0]
        if isinstance(target, ast.Subscript):
            expr_val = self._visit_expression(node.value)
            array_prefix, index_spec, is_const = self._parse_subscript(target)
            if is_const:
                self.statements.append(("STORE", expr_val, f"Basin_{array_prefix}{index_spec}"))
            else:
                self.statements.append(("STORE_INDIRECT", expr_val, array_prefix, index_spec))
            return

        target_name = self._resolve_target(target)
        # Allow dynamic inline self.ha = self.use_component(...) inside flow() if written there
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "self"
            and node.value.func.attr == "use_component"
        ):
            comp_inst = self._eval_use_component_call(node.value, instance_name=target_name)
            setattr(self.agent, target_name, comp_inst)
            return

        expr_val = self._visit_expression(node.value, target_name)
        
        if target_name in self.agent.outputs:
            self.statements.append(("STORE", target_name, self.agent.outputs[target_name]))

    def _eval_use_component_call(self, call: ast.Call, instance_name: str | None = None) -> ComponentInstance:
        comp_name = self._resolve_constant(call.args[0])
        in_map = None
        out_map = None
        if len(call.args) >= 2:
            in_map = ast.literal_eval(call.args[1])
        if len(call.args) >= 3:
            out_map = ast.literal_eval(call.args[2])
        for kw in call.keywords:
            if kw.arg == "inputs":
                in_map = ast.literal_eval(kw.value)
            elif kw.arg == "outputs":
                out_map = ast.literal_eval(kw.value)
            elif kw.arg == "instance_name" and instance_name is None:
                instance_name = self._resolve_constant(kw.value)
        return self.agent.use_component(comp_name, inputs=in_map or {}, outputs=out_map or {}, instance_name=instance_name)

    def _resolve_target(self, node: ast.AST) -> str:
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "self"
        ):
            comp_alias = node.value.attr
            port_name = node.attr
            comp_inst = getattr(self.agent, comp_alias, None)
            if _is_component_instance(comp_inst):
                return comp_inst.inputs.get(port_name) or comp_inst.outputs.get(port_name) or f"{comp_alias}_{port_name}"
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return node.attr
        elif isinstance(node, ast.Name):
            return node.id
        raise ValueError(f"Unsupported assignment target: {ast.dump(node)}")

    def _visit_expression(self, expr: ast.AST, dest_var: str | None = None) -> str:
        if (
            isinstance(expr, ast.Attribute)
            and isinstance(expr.value, ast.Attribute)
            and isinstance(expr.value.value, ast.Name)
            and expr.value.value.id == "self"
        ):
            comp_alias = expr.value.attr
            port_name = expr.attr
            comp_inst = getattr(self.agent, comp_alias, None)
            if _is_component_instance(comp_inst):
                var_name = comp_inst.outputs.get(port_name) or comp_inst.inputs.get(port_name) or f"{comp_alias}_{port_name}"
                if dest_var:
                    self.statements.append(("COND_ASSIGN", dest_var, var_name, var_name, var_name))
                return var_name
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
        elif isinstance(expr, ast.Subscript):
            array_prefix, index_spec, is_const = self._parse_subscript(expr)
            var_name = dest_var if dest_var else self._next_temp()
            if is_const:
                self.statements.append(("LOAD", var_name, f"Basin_{array_prefix}{index_spec}"))
            else:
                self.statements.append(("LOAD_INDIRECT", var_name, array_prefix, index_spec))
            return var_name

        elif isinstance(expr, ast.BinOp):
            left = self._visit_expression(expr.left)
            right = self._visit_expression(expr.right)
            
            if self.pure_wave:
                op_map = {
                    ast.BitXor: "XOR_WAVE",
                    ast.BitAnd: "AND_WAVE",
                    ast.BitOr: "OR_WAVE",
                }
            else:
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
            not_op = "NOT_WAVE" if self.pure_wave else "NOT"
            self.statements.append(("OP", var_name, not_op, operand, operand))
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
        
        cond_inv = self._next_temp()
        not_op = "NOT_WAVE" if self.pure_wave else "NOT"
        self.statements.append(("OP", cond_inv, not_op, cond_var, cond_var))
        
        self.statements.append(("JUMP_IF_ACTIVE", cond_inv, end_label))
        
        for stmt in node.body:
            self.visit(stmt)
            
        self.statements.append(("JUMP", start_label))
        self.statements.append(("LABEL", end_label))

    def visit_Expr(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            call = node.value
            # Sub-component run(), e.g. self.ha1.run()
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Attribute):
                inner_attr = call.func.value
                if isinstance(inner_attr.value, ast.Name) and inner_attr.value.id == "self":
                    instance_name = inner_attr.attr
                    method_name = call.func.attr
                    if method_name == "run" and hasattr(self.agent, instance_name):
                        comp_inst = getattr(self.agent, instance_name)
                        if _is_component_instance(comp_inst):
                            self._inline_component(comp_inst, instance_alias=instance_name)
                            return
            # Chained inline self.use_component(...).run()
            elif (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "run"
                and isinstance(call.func.value, ast.Call)
                and isinstance(call.func.value.func, ast.Attribute)
                and isinstance(call.func.value.func.value, ast.Name)
                and call.func.value.func.value.id == "self"
                and call.func.value.func.attr == "use_component"
            ):
                comp_inst = self._eval_use_component_call(call.func.value)
                self._inline_component(comp_inst, instance_alias=comp_inst.name)
                return
            # Standard self helper calls (nudge, settle, assert_mass) or direct self.comp() invocation
            elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == "self":
                method_name = call.func.attr
                if method_name in ("nudge", "settle", "assert_mass"):
                    args = [self._resolve_constant(arg) for arg in call.args]
                    self.statements.append((method_name.upper(), *args))
                    return
                if hasattr(self.agent, method_name):
                    comp_inst = getattr(self.agent, method_name)
                    if _is_component_instance(comp_inst):
                        self._inline_component(comp_inst, instance_alias=method_name)
                        return
        self.generic_visit(node)

    def _inline_component(self, comp_inst: ComponentInstance, instance_alias: str | None = None):
        import textwrap
        alias = instance_alias or comp_inst.name
        try:
            flow_src = textwrap.dedent(inspect.getsource(comp_inst.agent_cls.flow))
        except (OSError, TypeError):
            if hasattr(comp_inst.agent_cls, "_source"):
                flow_src = comp_inst.agent_cls._source
            else:
                flow_src = comp_inst.source_code
            
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
        
        sub_agent = comp_inst.agent_cls()
        for port_k in (*sub_agent.inputs.keys(), *sub_agent.outputs.keys()):
            self.component_scope_basins.setdefault(f"{alias}_{port_k}", f"Basin_{alias}_{port_k}")

        # Recursively bind any nested sub-components under alias_<child_attr>
        for child_attr, child_inst in sub_agent.__dict__.items():
            if _is_component_instance(child_inst):
                def _remap(w: str) -> str:
                    return comp_inst.inputs.get(w) or comp_inst.outputs.get(w) or f"{alias}_{w}"
                nested_alias = f"{alias}_{child_attr}"
                rebound_child = ComponentInstance(
                    nested_alias,
                    child_inst.agent_cls,
                    {k: _remap(v) for k, v in child_inst.inputs.items()},
                    {k: _remap(v) for k, v in child_inst.outputs.items()},
                    child_inst.source_code,
                )
                setattr(self.agent, nested_alias, rebound_child)
        
        transformer = ComponentASTTransformer(
            instance_name=alias,
            inputs_map=comp_inst.inputs,
            outputs_map=comp_inst.outputs,
            sub_inputs=sub_agent.inputs,
            sub_outputs=sub_agent.outputs
        )
        transformed_func = transformer.visit(func_def)
        
        for stmt in transformed_func.body:
            self.visit(stmt)

    def _resolve_constant(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif hasattr(ast, "Num") and isinstance(node, ast.Num):
            return node.n
        elif hasattr(ast, "Str") and isinstance(node, ast.Str):
            return node.s
        raise ValueError(f"Lumina analog helper call arguments must be constants: {ast.dump(node)}")


class LuminaLogosCompiler(LogosCompiler):
    """
    Extended Logos Compiler supporting Lumina analog/verification instructions
    (NUDGE, SETTLE, ASSERT_MASS), input-basin insulation, and automatic scratch-basin spilling.
    """
    def compile(
        self,
        inputs: dict[str, str],
        outputs: dict[str, str],
        statements: list[tuple],
        subroutines: dict[str, dict] | None = None,
        pure_wave: bool = False,
        preallocated_scratch_basins: dict[str, str] | None = None,
    ) -> CompiledLogosProgram:
        return super().compile(
            inputs,
            outputs,
            statements,
            subroutines=subroutines,
            pure_wave=pure_wave,
            preallocated_scratch_basins=preallocated_scratch_basins,
        )


class StaticVerificationError(Exception):
    """Exception raised when static analysis detects a safety violation (e.g. mass preservation breach)."""


class StaticMassSentinel:
    """
    Symbolically checks compiled Logos instructions across straight-line code AND CFG loop
    back-edges (both unrolled bounded checks and monotone cycle-gain fixed-point projection)
    to prove register and semantic-basin mass safety bounds (>= 14.0).
    """

    MIN_MASS_THRESHOLD: float = 14.0
    _EXACT_REG_ALIASES: ClassVar[dict[str, set[str]]] = {
        reg: {reg, f"R{reg}", f"S_R{reg}", f"S_R{reg}_B", f"Register_{reg}", f"Basin_R{reg}"}
        for reg in ("A", "B", "C", "D")
    }
    _ALL_REG_ALIASES: ClassVar[set[str]] = set().union(*_EXACT_REG_ALIASES.values())
    _GATE_OPS: ClassVar[set[str]] = {
        "OR", "AND", "OR_MS", "AND_MS", "NOT", "NAND", "NOR", "XOR", "XNOR",
        "OR_WAVE", "AND_WAVE", "NOT_WAVE", "NAND_WAVE", "NOR_WAVE", "XOR_WAVE", "XNOR_WAVE",
    }

    @classmethod
    def verify(
        cls,
        instructions: list[Instruction],
        damping: float = 0.01,
        max_loop_unroll: int = 8,
    ) -> bool:
        registers = {"A": 15.0, "B": 15.0, "C": 15.0, "D": 15.0}
        active_registers = {"A": False, "B": False, "C": False, "D": False}
        reg_basins: dict[str, set[str]] = {"A": set(), "B": set(), "C": set(), "D": set()}
        basin_masses: dict[str, float] = {}
        active_basins: set[str] = set()

        label_to_idx: dict[str, int] = {}
        for idx, inst in enumerate(instructions):
            if inst.op.upper() == "LABEL" and inst.args:
                label_to_idx[str(inst.args[0])] = idx

        backedge_counts: dict[tuple[int, int], int] = {}
        backedge_snapshots: dict[
            tuple[int, int],
            tuple[dict[str, bool], dict[str, float], set[str], dict[str, float]],
        ] = {}
        pc = 0
        steps_executed = 0
        max_total_steps = max(256, len(instructions) * (max_loop_unroll + 4))

        while pc < len(instructions) and steps_executed < max_total_steps:
            steps_executed += 1
            inst = instructions[pc]
            op = inst.op.upper()
            args = inst.args

            if op == "LOAD":
                reg = str(args[0])
                basin = str(args[1])
                active_registers[reg] = True
                reg_basins[reg] = {basin}
                basin_masses.setdefault(basin, 15.0)
                active_basins.add(basin)
                registers[reg] = basin_masses[basin]
            elif op == "LOAD_INDIRECT":
                reg = str(args[0])
                prefix = str(args[1])
                pseudo_basin = f"Basin_{prefix}*"
                active_registers[reg] = True
                reg_basins[reg] = {pseudo_basin}
                basin_masses.setdefault(pseudo_basin, 15.0)
                active_basins.add(pseudo_basin)
                registers[reg] = basin_masses[pseudo_basin]
            elif op == "STORE":
                reg = str(args[0])
                basin = str(args[1])
                reg_basins[reg].add(basin)
                if active_registers[reg]:
                    basin_masses[basin] = registers[reg]
                else:
                    basin_masses.setdefault(basin, 15.0)
                active_basins.add(basin)
            elif op == "STORE_INDIRECT":
                reg = str(args[0])
                prefix = str(args[1])
                pseudo_basin = f"Basin_{prefix}*"
                reg_basins[reg].add(pseudo_basin)
                if active_registers[reg]:
                    basin_masses[pseudo_basin] = registers[reg]
                else:
                    basin_masses.setdefault(pseudo_basin, 15.0)
                active_basins.add(pseudo_basin)
            elif op == "CLEAR":
                reg = str(args[0])
                active_registers[reg] = False
                registers[reg] = 15.0
                reg_basins[reg] = set()
            elif op == "COPY":
                src, dest = str(args[0]), str(args[1])
                registers[dest] = registers[src]
                active_registers[dest] = active_registers[src]
                reg_basins[dest] = set(reg_basins[src])
            elif op == "CMOVE":
                dest, src = str(args[0]), str(args[1])
                if active_registers[dest] and active_registers[src]:
                    registers[dest] = min(registers[dest], registers[src])
                elif active_registers[src]:
                    registers[dest] = registers[src]
                active_registers[dest] = active_registers[dest] or active_registers[src]
                reg_basins[dest] = reg_basins[dest] | reg_basins[src]
            elif op in cls._GATE_OPS:
                dest = str(args[0]) if args else "C"
                if op in ("NOT", "NOT_WAVE"):
                    src_r = str(args[1]) if len(args) > 1 else "A"
                    registers[dest] = registers[src_r] if active_registers[src_r] else 15.0
                    reg_basins[dest] = set(reg_basins[src_r])
                else:
                    src_masses = [registers[r] for r in ("A", "B") if active_registers[r]]
                    registers[dest] = min(src_masses) if src_masses else 15.0
                    reg_basins[dest] = reg_basins["A"] | reg_basins["B"]
                active_registers[dest] = True
            elif op == "NUDGE":
                target = str(args[0])
                amount = float(args[1])
                for reg in ("A", "B", "C", "D"):
                    if target in cls._EXACT_REG_ALIASES[reg] or target in reg_basins[reg]:
                        registers[reg] += amount
                if target not in cls._ALL_REG_ALIASES:
                    basin_masses[target] = basin_masses.get(target, 15.0) + amount
                    active_basins.add(target)
                    # Also match wildcard array prefix if target is Basin_X0 vs Basin_X*
                    for b_key in list(basin_masses.keys()):
                        if b_key.endswith("*") and target.startswith(b_key[:-1]):
                            basin_masses[b_key] += amount
            elif op == "SETTLE":
                steps = int(args[0])
                drain = damping * steps
                for reg in ("A", "B", "C", "D"):
                    if active_registers[reg]:
                        registers[reg] = max(0.0, registers[reg] - drain)
                for b_name in active_basins:
                    basin_masses[b_name] = max(0.0, basin_masses[b_name] - drain)

            # Verify active registers and active basins mass floor (>= 14.0)
            for reg in ("A", "B", "C", "D"):
                if active_registers[reg] and registers[reg] < 14.0:
                    raise StaticVerificationError(
                        f"Static verification failure: instruction '{inst.op} {', '.join(map(str, inst.args))}' at index {pc} "
                        f"drains Register {reg} mass to {registers[reg]:.2f} (< 14.0)."
                    )
            for b_name in sorted(active_basins):
                if basin_masses[b_name] < 14.0:
                    raise StaticVerificationError(
                        f"Static verification failure: instruction '{inst.op} {', '.join(map(str, inst.args))}' at index {pc} "
                        f"drains Basin {b_name} mass across CFG execution/loop back-edge to {basin_masses[b_name]:.2f} (< 14.0)."
                    )

            # Follow CFG loop back-edges and detect strictly negative net cycle mass gain (unbounded slow drain)
            if op in ("JUMP", "JUMP_IF_ACTIVE"):
                target_label = str(args[0]) if op == "JUMP" else str(args[1])
                if target_label in label_to_idx:
                    target_idx = label_to_idx[target_label]
                    if target_idx < pc:
                        edge_key = (pc, target_idx)
                        count = backedge_counts.get(edge_key, 0)
                        if count >= 1 and edge_key in backedge_snapshots:
                            prev_active_regs, prev_regs, prev_active_basins, prev_basins = backedge_snapshots[edge_key]
                            for reg in ("A", "B", "C", "D"):
                                if active_registers[reg] and prev_active_regs.get(reg, False):
                                    delta_r = registers[reg] - prev_regs[reg]
                                    if delta_r < -1e-9:
                                        raise StaticVerificationError(
                                            f"Static verification failure: loop back-edge at index {pc} -> {target_idx} "
                                            f"has negative net cycle mass gain ({delta_r:.4f}/iter) on active Register {reg} "
                                            f"(current {registers[reg]:.2f}, inevitably drains < 14.0)."
                                        )
                            for b_name in sorted(active_basins & prev_active_basins):
                                delta_b = basin_masses[b_name] - prev_basins[b_name]
                                if delta_b < -1e-9:
                                    raise StaticVerificationError(
                                        f"Static verification failure: loop back-edge at index {pc} -> {target_idx} "
                                        f"has negative net cycle mass gain ({delta_b:.4f}/iter) on Basin {b_name} "
                                        f"(current {basin_masses[b_name]:.2f}, inevitably drains < 14.0)."
                                    )
                        backedge_snapshots[edge_key] = (
                            dict(active_registers),
                            dict(registers),
                            set(active_basins),
                            dict(basin_masses),
                        )
                        if count < max_loop_unroll:
                            backedge_counts[edge_key] = count + 1
                            pc = target_idx
                            continue

            pc += 1

        return True


class LuminaCompiler:
    """Orchestrates class inspection, AST extraction, and Lumina compilation."""
    @staticmethod
    def compile_agent(
        agent_cls: type[LuminaAgent],
        verify_mass: bool = True,
        pure_wave: bool = False,
        damping: float = 0.01,
    ) -> CompiledLogosProgram:
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
        return LuminaCompiler.compile_flow_src(
            agent.inputs,
            agent.outputs,
            flow_src,
            agent=agent,
            verify_mass=verify_mass,
            pure_wave=pure_wave,
            damping=damping,
        )

    @staticmethod
    def compile_flow_src(
        inputs: dict[str, str],
        outputs: dict[str, str],
        flow_src: str,
        agent: LuminaAgent | None = None,
        components: dict[str, Any] | None = None,
        verify_mass: bool = True,
        pure_wave: bool = False,
        damping: float = 0.01,
    ) -> CompiledLogosProgram:
        import textwrap
        flow_src = textwrap.dedent(flow_src)
        if not flow_src.strip().startswith("def "):
            indented = "\n".join("    " + line for line in flow_src.splitlines())
            flow_src = f"def flow(self):\n{indented}"
            
        parsed_ast = ast.parse(flow_src)
        if agent is None:
            agent = type("MockAgent", (LuminaAgent,), {"inputs": inputs.copy(), "outputs": outputs.copy()})()
        if components:
            for alias, comp_spec in components.items():
                agent._bind_component_spec(str(alias), comp_spec)
        visitor = LuminaASTVisitor(agent, pure_wave=pure_wave)
        func_def = parsed_ast.body[0]
        for stmt in func_def.body:
            visitor.visit(stmt)
            
        compiler = LuminaLogosCompiler()
        program = compiler.compile(
            inputs,
            outputs,
            visitor.statements,
            pure_wave=pure_wave,
            preallocated_scratch_basins=visitor.component_scope_basins,
        )
        for k_var, b_val in visitor.component_scope_basins.items():
            program.allocated_scratch_basins.setdefault(k_var, b_val)
        
        if verify_mass:
            StaticMassSentinel.verify(program, damping=damping)
            
        return program
