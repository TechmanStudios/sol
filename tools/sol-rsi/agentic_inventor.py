#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL RSI Agentic Code Inventor
===============================
An LLM-driven agent that autonomously designs, compiles, tests, and recursively
optimizes Lumina code running on the SOL substrate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Resolve paths
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))

from client import SolLLM
from hybrid_subsystem_framework import (
    Instruction,
    ManifoldGroup,
    MicroInstructionSequencer,
    ProcessingManifold,
    SemanticManifold,
    UniversalManifold,
)
from lumina_compiler import LuminaAgent, LuminaCompiler
from test_logos_vm import LogosVM

# MicroInstructionSequencer natively supports NUDGE, SETTLE, ASSERT_MASS, and pure_wave execution.

# ---------------------------------------------------------------------------
# Task Definitions & Validation
# ---------------------------------------------------------------------------

TASKS = {
    "xor_gate": {
        "inputs": {"x": "Basin_A", "y": "Basin_B"},
        "outputs": {"z": "Basin_SUM"},
        "input_space": [(0, 0), (1, 0), (0, 1), (1, 1)],
        "expected_fn": lambda x, y: (x ^ y,),
        "verify_fn": lambda got, exp: got[0] == exp[0],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_SUM", 20)],
    },
    "half_adder": {
        "inputs": {"x": "Basin_A", "y": "Basin_B"},
        "outputs": {"sum": "Basin_SUM", "cout": "Basin_Cout"},
        "input_space": [(0, 0), (1, 0), (0, 1), (1, 1)],
        "expected_fn": lambda x, y: (x ^ y, x & y),
        "verify_fn": lambda got, exp: got[0] == exp[0] and got[1] == exp[1],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_SUM", 20), ("Basin_Cout", 30)],
    },
    "full_adder": {
        "inputs": {"x": "Basin_A", "y": "Basin_B", "cin": "Basin_Cin"},
        "outputs": {"sum": "Basin_SUM", "cout": "Basin_Cout"},
        "input_space": [
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
            (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1),
        ],
        "expected_fn": lambda x, y, cin: (x ^ y ^ cin, (x & y) | (cin & (x ^ y))),
        "verify_fn": lambda got, exp: got[0] == exp[0] and got[1] == exp[1],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_Cin", 20), ("Basin_SUM", 30), ("Basin_Cout", 40)],
    },
    "hierarchical_full_adder": {
        "inputs": {"x": "Basin_A", "y": "Basin_B", "cin": "Basin_Cin"},
        "outputs": {"sum": "Basin_SUM", "cout": "Basin_Cout"},
        "input_space": [
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
            (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1),
        ],
        "expected_fn": lambda x, y, cin: (x ^ y ^ cin, (x & y) | (cin & (x ^ y))),
        "verify_fn": lambda got, exp: got[0] == exp[0] and got[1] == exp[1],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_Cin", 20), ("Basin_SUM", 30), ("Basin_Cout", 40)],
    },
    "multiplexer": {
        "inputs": {"a": "Basin_A", "b": "Basin_B", "sel": "Basin_Sel"},
        "outputs": {"out": "Basin_Out"},
        "input_space": [
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
            (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1),
        ],
        "expected_fn": lambda a, b, sel: (b if sel else a,),
        "verify_fn": lambda got, exp: got[0] == exp[0],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_Sel", 20), ("Basin_Out", 30)],
    },
    "sr_latch": {
        "inputs": {"s": "Basin_S", "r": "Basin_R"},
        "outputs": {"q": "Basin_Q", "qbar": "Basin_Qbar"},
        "is_sequential": True,
        "sequence": [
            # ((s, r), (expected_q, expected_qbar))
            ((1, 0), (1, 0)),  # Set -> Q=1, Qbar=0
            ((0, 0), (1, 0)),  # Hold (Memory) -> Q=1, Qbar=0
            ((0, 1), (0, 1)),  # Reset -> Q=0, Qbar=1
            ((0, 0), (0, 1)),  # Hold (Memory) -> Q=0, Qbar=1
            ((1, 0), (1, 0)),  # Set -> Q=1, Qbar=0
            ((0, 0), (1, 0)),  # Hold (Memory) -> Q=1, Qbar=0
        ],
        "basins_def": [("Basin_S", 0), ("Basin_R", 10), ("Basin_Q", 20), ("Basin_Qbar", 30)],
    },
}


def _discover_program_basins(
    base_basins_def: list[tuple[str, int]],
    program: list[Instruction],
) -> list[tuple[str, int]]:
    """Appends any dynamically allocated scratch or auxiliary basins referenced in program."""
    basins_def = list(base_basins_def)
    known = {b_name for b_name, _ in basins_def}
    next_idx = max((start_idx + 10 for _, start_idx in basins_def), default=0)

    extra_names: list[str] = []
    alloc_map = getattr(program, "allocated_scratch_basins", None)
    if isinstance(alloc_map, dict):
        for b_name in alloc_map.values():
            if isinstance(b_name, str) and b_name not in known and b_name not in extra_names:
                extra_names.append(b_name)

    for inst in program:
        op = inst.op.upper()
        if op in ("LOAD", "STORE") and len(inst.args) >= 2:
            b_name = str(inst.args[1])
            if b_name.startswith("Basin_") and b_name not in known and b_name not in extra_names:
                extra_names.append(b_name)
        elif op in ("NUDGE", "ASSERT_MASS") and len(inst.args) >= 1:
            b_name = str(inst.args[0])
            if b_name.startswith("Basin_") and b_name not in known and b_name not in extra_names:
                extra_names.append(b_name)

    for b_name in extra_names:
        basins_def.append((b_name, next_idx))
        known.add(b_name)
        next_idx += 10

    return basins_def


def _read_basin_state(record: dict, basin_name: str, basins_def: list[tuple[str, int]]) -> int:
    basin_states = record.get("basin_states")
    if isinstance(basin_states, dict) and basin_name in basin_states:
        return int(basin_states[basin_name])
    b_idx = [b[0] for b in basins_def].index(basin_name)
    state_key = f"basin_{chr(97 + b_idx)}_state"
    return int(record.get(state_key, 0))


def build_custom_group(basins_def: list[tuple[str, int]], pure_wave: bool = False) -> ManifoldGroup:
    nodes = []
    edges = []
    basins = []
    for b_name, start_idx in basins_def:
        b_nodes, b_edges, b_cfg = UniversalManifold.build_semantic_basin(
            b_name, num_nodes=10, start_idx=start_idx, pure_wave=pure_wave
        )
        nodes.extend(b_nodes)
        edges.extend(b_edges)
        basins.append(b_cfg)

    semantic = SemanticManifold(nodes=nodes, edges=edges, basins=basins)
    processing = ProcessingManifold(pure_wave=pure_wave)
    return ManifoldGroup(semantic, processing, c_press=1.0, damping=0.01, pure_wave=pure_wave)


def run_trial(
    task_name: str,
    inputs_val: Any,
    program: list[Instruction],
    *,
    pure_wave: Any = None,
    detect_sr_hazard: bool = False,
    wave_threshold_offset: float = 0.0,
    custom_task: Any = None,
) -> tuple[list[dict], bool, str]:
    task = custom_task if custom_task is not None else TASKS[task_name]
    effective_pure_wave = bool(getattr(program, "pure_wave", False)) if pure_wave is None else bool(pure_wave)
    basins_def = _discover_program_basins(task["basins_def"], program)
    group = build_custom_group(basins_def, pure_wave=effective_pure_wave)

    # Prime all non-input / scratch / output basins to clean default state initially
    for b_name, _ in basins_def:
        group.prime_basin(b_name, active=False)

    for reg in ('A', 'B', 'C', 'D'):
        group.prime_register(reg, active=False)

    sequencer = MicroInstructionSequencer(
        group,
        pure_wave=effective_pure_wave,
        wave_threshold_offset=wave_threshold_offset,
        record_substep_telemetry=False,
    )
    vm = LogosVM(sequencer)

    if task.get("is_sequential"):
        full_history = []
        for step_idx, (in_val, exp_val) in enumerate(task["sequence"]):
            input_keys = list(task["inputs"].keys())
            for idx, key in enumerate(input_keys):
                group.prime_basin(task["inputs"][key], active=(in_val[idx] == 1))

            try:
                history = vm.run(program)
                if not history:
                    return [], False, f"Step {step_idx}: Execution empty history"
                full_history.extend(history)
            except (AssertionError, IndexError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError) as e:
                return [], False, f"Step {step_idx}: Sequencer VM execution error: {e}"

            out_keys = list(task["outputs"].keys())
            got_vals = [
                _read_basin_state(history[-1], task["outputs"][out_name], basins_def)
                for out_name in out_keys
            ]

            if detect_sr_hazard and len(got_vals) >= 2 and got_vals[0] == got_vals[1]:
                full_history[-1]["python_boolean_shortcuts_used"] = sequencer.python_boolean_shortcuts_used
                full_history[-1]["wave_gate_telemetry"] = list(sequencer.wave_gate_telemetry)
                return (
                    full_history,
                    False,
                    f"Step {step_idx} (Inputs {in_val}): Bistability complement hazard Q==Qbar ({got_vals}) detected",
                )

            if got_vals != list(exp_val):
                full_history[-1]["python_boolean_shortcuts_used"] = sequencer.python_boolean_shortcuts_used
                full_history[-1]["wave_gate_telemetry"] = list(sequencer.wave_gate_telemetry)
                return full_history, False, f"Step {step_idx} (Inputs {in_val}): Expected {exp_val}, got {got_vals}"

        if effective_pure_wave and sequencer.python_boolean_shortcuts_used != 0:
            return (
                full_history,
                False,
                f"Pure-wave contract breach: python_boolean_shortcuts_used={sequencer.python_boolean_shortcuts_used} != 0",
            )

        for reg in ('A', 'B', 'C', 'D'):
            reg_active = full_history[-1].get(f"reg_{reg.lower()}_state", 0.0) == 1.0
            if reg_active:
                reg_mass = full_history[-1].get(f"rho_reg_{reg.lower()}", 0.0)
                if reg_mass < 14.0:
                    return full_history, False, f"Mass preservation breach: active Register {reg} mass is {reg_mass:.2f} (< 14.0)"

        full_history[-1]["python_boolean_shortcuts_used"] = sequencer.python_boolean_shortcuts_used
        full_history[-1]["wave_gate_telemetry"] = list(sequencer.wave_gate_telemetry)
        return full_history, True, "All sequential verification checks passed!"

    else:
        input_keys = list(task["inputs"].keys())
        for idx, key in enumerate(input_keys):
            group.prime_basin(task["inputs"][key], active=(inputs_val[idx] == 1))

        try:
            history = vm.run(program)
            if not history:
                return [], False, "Execution empty history"
        except (AssertionError, IndexError, KeyError, RuntimeError, TypeError, ValueError, ZeroDivisionError) as e:
            return [], False, f"Sequencer VM execution error: {e}"

        history[-1]["python_boolean_shortcuts_used"] = sequencer.python_boolean_shortcuts_used
        history[-1]["wave_gate_telemetry"] = list(sequencer.wave_gate_telemetry)

        if effective_pure_wave and sequencer.python_boolean_shortcuts_used != 0:
            return (
                history,
                False,
                f"Pure-wave contract breach: python_boolean_shortcuts_used={sequencer.python_boolean_shortcuts_used} != 0",
            )

        out_keys = list(task["outputs"].keys())
        got_vals = [
            _read_basin_state(history[-1], task["outputs"][out_name], basins_def)
            for out_name in out_keys
        ]

        expected_vals = task["expected_fn"](*inputs_val)
        logical_ok = task["verify_fn"](got_vals, expected_vals)

        if not logical_ok:
            return history, False, f"Expected {expected_vals}, got {got_vals}"

        for idx, key in enumerate(input_keys):
            basin_name = task["inputs"][key]
            got_in = _read_basin_state(history[-1], basin_name, basins_def)
            if got_in != inputs_val[idx]:
                return history, False, f"Insulation breach: input {key} ({basin_name}) changed to {got_in}"

        for reg in ('A', 'B', 'C', 'D'):
            reg_active = history[-1].get(f"reg_{reg.lower()}_state", 0.0) == 1.0
            if reg_active:
                reg_mass = history[-1].get(f"rho_reg_{reg.lower()}", 0.0)
                if reg_mass < 14.0:
                    return history, False, f"Mass preservation breach: active Register {reg} mass is {reg_mass:.2f} (< 14.0)"

        return history, True, "All verification checks passed!"

# ---------------------------------------------------------------------------
# RSI Loop & LLM Orchestration
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are LuminaCreator, an autonomous agentic code inventing agent for the SOL engine substrate.
Lumina is a programming language for writing agents and logic running on the SOL physical manifold.

Your task is to write a single LuminaAgent subclass containing configure() and flow() methods.
Lumina syntax and design guidelines:
1. Subclass LuminaAgent.
2. configure() maps variable names to their physical memory basins.
3. flow() defines execution logic.
4. Supported logic operators: ^ (XOR), & (AND), | (OR), ~ (NOT).
5. Ternary conditionals: value_if_true if condition else value_if_false.
6. Support control flow using `while condition:` loops.
7. Support analog and assertion helpers:
   - self.nudge("Basin_SUM", 5.0) -> Increments basin hub mass. First argument is basin name (string constant), second is float constant.
   - self.settle(10) -> Steps the simulator without register actions. Argument is integer constant.
   - self.assert_mass("C", 14.0) -> Asserts register mass preservation. First argument is register name "A", "B", "C", or "D" (string constant), second is float constant.
8. ALL variables are symbolic wrappers for physical basins. Do NOT assign raw numbers/constants to variables. Assign one variable to another, e.g., `self.z = self.x`.
9. The flow() method should ONLY implement the logic mapping the inputs to outputs. Do NOT attempt to test inputs or define test cases (such as self.x = 0 or self.x = self.one) inside flow(). E.g. the inputs are primed and tested externally by the trial runner. Keep flow() simple, elegant and focused on the math/logical expression.
10. All arguments to self.nudge, self.settle, and self.assert_mass must be raw constants. Do NOT pass variables, attributes, or expressions to these functions.
11. For sequential/stateful tasks (like sr_latch), you can read a variable's state from your own output (e.g., `self.q = self.s | (self.q & ~self.r)`). The compiler translates these self-referential reads into dynamic state feedback loops reading from and writing to the same physical attractor basin.

Example:
```python
from lumina_compiler import LuminaAgent

class DynamicAgent(LuminaAgent):
    def configure(self):
        self.inputs = {"x": "Basin_A", "y": "Basin_B"}
        self.outputs = {"z": "Basin_SUM"}

    def flow(self):
        self.z = self.x ^ self.y
```

Return ONLY the code block inside a python markdown fence (```python ... ```). Do not include any conversational explanation.
"""

def extract_code(llm_response: str) -> str:
    lines = llm_response.splitlines()
    code_lines = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```python"):
            in_code = True
            continue
        if line.strip().startswith("```") and in_code:
            in_code = False
            break
        if in_code:
            code_lines.append(line)
    return "\n".join(code_lines)

def run_rsi_loop(
    task_name: str,
    max_cycles: int = 5,
    *,
    pure_wave: bool = False,
    persist_ledger: bool = True,
) -> tuple[bool, str]:
    if task_name not in TASKS:
        print(f"Unknown task: {task_name}")
        return False, ""

    print(f"[START] Initializing RSI Agentic Code Inventor for task: {task_name} (pure_wave={pure_wave})")
    task = TASKS[task_name]

    # Initialize SolLLM
    try:
        llm = SolLLM()
    except (ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError) as e:
        print(f"[ERROR] Failed to load LLM client: {e}. Please ensure GITHUB_TOKEN is configured.")
        return False, ""

    prompt = f"""Write a LuminaAgent to implement the '{task_name}' logic.
Inputs: {task['inputs']}
Outputs: {task['outputs']}
This should calculate the expected outputs for all input combinations.
"""

    history_log = []
    compiled_code = ""

    for cycle in range(1, max_cycles + 1):
        print(f"\n--- RSI Cycle {cycle}/{max_cycles} ---")
        response = llm.complete(prompt, system=SYSTEM_PROMPT, task="code_generation")

        if not response.success:
            print(f"[ERROR] LLM completion call failed: {response.error}")
            break

        code = extract_code(response.content)
        if not code.strip():
            print("[ERROR] Failed to extract Python code block from LLM response. Retrying...")
            prompt += "\nError: You did not return code inside a ```python ``` block. Please fix this."
            continue

        print("Generated Lumina code candidate:")
        print("--------------------------------")
        print(code)
        print("--------------------------------")

        # 1. Compile the code
        # Write to a temporary string and compile
        print("Compiling code to register-allocated instructions...")
        try:
            # We mock the class definition by executing it in a local dict
            local_vars: dict[str, Any] = {}
            # Import LuminaAgent inside execution namespace
            exec_globals = {"LuminaAgent": LuminaAgent, "LuminaCompiler": LuminaCompiler}
            exec(code, exec_globals, local_vars)  # noqa: S102

            # Find the LuminaAgent subclass
            agent_cls = None
            for val in local_vars.values():
                if isinstance(val, type) and issubclass(val, LuminaAgent) and val != LuminaAgent:
                    agent_cls = val
                    break

            if not agent_cls:
                raise ValueError("No subclass of LuminaAgent found in code.")

            agent_cls._source = code
            program = LuminaCompiler.compile_agent(agent_cls, pure_wave=pure_wave)
            print(f"Generated {len(program)} instructions successfully.")
        except (AttributeError, ImportError, KeyError, NameError, RuntimeError, SyntaxError, TypeError, ValueError) as e:
            err_msg = f"Compilation Error: {e}"
            print(f"[ERROR] {err_msg}")
            try:
                from coding_library.experts import LuminaExpertTeam
                expert_team = LuminaExpertTeam()
                expert_advice = expert_team.ask_expert("compiler", f"Here is the code that failed to compile:\n```python\n{code}\n```\nError message:\n{err_msg}", context_details={"task": task_name, "error": err_msg})
                print(f"[EXPERT CONSULTATION] Advice from Compiler Expert:\n{expert_advice}\n")
                advice_str = f"\n\nExpert Recommendation:\n{expert_advice}"
            except (AttributeError, ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError):
                advice_str = ""
            prompt = f"Lumina compilation failed with error:\n{err_msg}{advice_str}\n\nHere was your code:\n```python\n{code}\n```\nPlease fix this compilation issue."
            history_log.append({"cycle": cycle, "status": "COMPILE_FAIL", "error": err_msg, "code": code})
            continue

        # 2. Run verification trials on the VM
        print("Running physical verification trials...")
        passed_all = True
        trial_err = ""

        if task.get("is_sequential"):
            # Run the single sequential transition sequence
            _history, ok, msg = run_trial(task_name, None, program, pure_wave=pure_wave)
            if not ok:
                passed_all = False
                trial_err = msg
                print(f"[ERROR] {trial_err}")
        else:
            # Run multiple combinational truth-table inputs
            for trial_input in task["input_space"]:
                _history, ok, msg = run_trial(task_name, trial_input, program, pure_wave=pure_wave)
                if not ok:
                    passed_all = False
                    trial_err = f"Failed on input {trial_input}: {msg}"
                    print(f"[ERROR] {trial_err}")
                    break

        if passed_all:
            print("[SUCCESS] Lumina Agent passed all truth-table verification, mass preservation, and insulation checks!")
            compiled_code = code
            history_log.append({"cycle": cycle, "status": "SUCCESS", "code": code})
            break
        else:
            try:
                from coding_library.experts import LuminaExpertTeam
                expert_team = LuminaExpertTeam()
                expert_to_ask = "substrate" if "mass" in trial_err.lower() or "preservation" in trial_err.lower() else "synthesis"
                expert_advice = expert_team.ask_expert(expert_to_ask, f"Here is the code that failed verification:\n```python\n{code}\n```\nVerification error:\n{trial_err}", context_details={"task": task_name, "error": trial_err})
                print(f"[EXPERT CONSULTATION] Advice from {expert_to_ask.capitalize()} Expert:\n{expert_advice}\n")
                advice_str = f"\n\nExpert Recommendation ({expert_to_ask.capitalize()} Expert):\n{expert_advice}"
            except (AttributeError, ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError):
                advice_str = ""
            prompt = f"Lumina agent failed verification tests with error:\n{trial_err}{advice_str}\n\nHere was your code:\n```python\n{code}\n```\nPlease fix the logical/physical verification errors."
            history_log.append({"cycle": cycle, "status": "VERIFICATION_FAIL", "error": trial_err, "code": code})
            
    log_entry = {
        "task": task_name,
        "pure_wave": pure_wave,
        "cycles_run": len(history_log),
        "success": any(h["status"] == "SUCCESS" for h in history_log),
        "final_status": history_log[-1]["status"] if history_log else "NO_ATTEMPTS",
        "history": history_log,
    }
    if persist_ledger:
        ledger_path = sol_root / "data" / "rsi" / "inventor_ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        
    return log_entry["success"], compiled_code

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SOL RSI Agentic Code Inventor")
    ap.add_argument("--task", default="half_adder", choices=list(TASKS.keys()), help="Target task to solve")
    ap.add_argument("--cycles", type=int, default=5, help="Maximum mutation refinement cycles")
    ap.add_argument("--pure-wave", action="store_true", help="Compile and verify using pure wave-interference cavities")
    args = ap.parse_args()
    
    success, code = run_rsi_loop(args.task, args.cycles, pure_wave=args.pure_wave)
    sys.exit(0 if success else 1)
