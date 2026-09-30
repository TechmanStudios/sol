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

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Resolve paths
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))
sys.path.insert(0, str(sol_root / "tools" / "sol-llm"))

from lumina_compiler import LuminaCompiler, LuminaAgent
from client import SolLLM
from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer
)
from test_logos_vm import LogosVM

# ---------------------------------------------------------------------------
# Monkey-patching the Sequencer to support Lumina custom instructions
# ---------------------------------------------------------------------------

original_execute = MicroInstructionSequencer.execute_instruction

def patched_execute_instruction(self, inst: Instruction):
    op = inst.op.upper()
    if op == "NUDGE":
        basin_name, amount = inst.args[0], inst.args[1]
        basin = self.group.semantic.basins[basin_name]
        hub = self.group.get_node(basin.hub_id)
        hub["rho"] += amount
    elif op == "SETTLE":
        steps = inst.args[0]
        for _ in range(steps):
            self.group.step(self.dt)
            self.record_telemetry()
    elif op == "ASSERT_MASS":
        reg, min_mass = inst.args[0], inst.args[1]
        bat_node = self.group.get_node(f"S_R{reg}_B")
        host_node = self.group.get_node(f"S_R{reg}")
        current_mass = host_node["rho"] + bat_node["rho"]
        if current_mass < min_mass:
            raise AssertionError(f"Mass preservation failure on Register {reg}: expected >= {min_mass}, got {current_mass}")
    else:
        original_execute(self, inst)

MicroInstructionSequencer.execute_instruction = patched_execute_instruction

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
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_SUM", 20)]
    },
    "half_adder": {
        "inputs": {"x": "Basin_A", "y": "Basin_B"},
        "outputs": {"sum": "Basin_SUM", "cout": "Basin_Cout"},
        "input_space": [(0, 0), (1, 0), (0, 1), (1, 1)],
        "expected_fn": lambda x, y: (x ^ y, x & y),
        "verify_fn": lambda got, exp: got[0] == exp[0] and got[1] == exp[1],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_SUM", 20), ("Basin_Cout", 30)]
    },
    "full_adder": {
        "inputs": {"x": "Basin_A", "y": "Basin_B", "cin": "Basin_Cin"},
        "outputs": {"sum": "Basin_SUM", "cout": "Basin_Cout"},
        "input_space": [
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
            (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)
        ],
        "expected_fn": lambda x, y, cin: (x ^ y ^ cin, (x & y) | (cin & (x ^ y))),
        "verify_fn": lambda got, exp: got[0] == exp[0] and got[1] == exp[1],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_Cin", 20), ("Basin_SUM", 30), ("Basin_Cout", 40)]
    },
    "multiplexer": {
        "inputs": {"a": "Basin_A", "b": "Basin_B", "sel": "Basin_Sel"},
        "outputs": {"out": "Basin_Out"},
        "input_space": [
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
            (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)
        ],
        "expected_fn": lambda a, b, sel: (b if sel else a,),
        "verify_fn": lambda got, exp: got[0] == exp[0],
        "basins_def": [("Basin_A", 0), ("Basin_B", 10), ("Basin_Sel", 20), ("Basin_Out", 30)]
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
            ((0, 0), (0, 1))   # Hold (Memory) -> Q=0, Qbar=1
        ],
        "basins_def": [("Basin_S", 0), ("Basin_R", 10), ("Basin_Q", 20), ("Basin_Qbar", 30)]
    }
}

def build_custom_group(basins_def: List[Tuple[str, int]]) -> ManifoldGroup:
    nodes = []
    edges = []
    basins = []
    for b_name, start_idx in basins_def:
        b_nodes, b_edges, b_cfg = UniversalManifold.build_semantic_basin(b_name, num_nodes=10, start_idx=start_idx)
        nodes.extend(b_nodes)
        edges.extend(b_edges)
        basins.append(b_cfg)
    
    semantic = SemanticManifold(nodes=nodes, edges=edges, basins=basins)
    processing = ProcessingManifold()
    return ManifoldGroup(semantic, processing, c_press=1.0, damping=0.01)

def run_trial(task_name: str, inputs_val: Any, program: List[Instruction]) -> Tuple[List[dict], bool, str]:
    task = TASKS[task_name]
    group = build_custom_group(task["basins_def"])
    
    # Prime outputs to clean default state initially
    for key in task["outputs"]:
        group.prime_basin(task["outputs"][key], active=False)
        
    for reg in ('A', 'B', 'C', 'D'):
        group.prime_register(reg, active=False)
        
    sequencer = MicroInstructionSequencer(group)
    vm = LogosVM(sequencer)
    
    if task.get("is_sequential"):
        full_history = []
        for step_idx, (in_val, exp_val) in enumerate(task["sequence"]):
            # Prime inputs for this transition step
            input_keys = list(task["inputs"].keys())
            for idx, key in enumerate(input_keys):
                group.prime_basin(task["inputs"][key], active=(in_val[idx] == 1))
                
            try:
                history = vm.run(program)
                if not history:
                    return [], False, f"Step {step_idx}: Execution empty history"
                full_history.extend(history)
            except Exception as e:
                return [], False, f"Step {step_idx}: Sequencer VM execution error: {e}"
                
            # Verify outputs for this step
            out_keys = list(task["outputs"].keys())
            got_vals = []
            for out_name in out_keys:
                basin_name = task["outputs"][out_name]
                b_idx = [b[0] for b in task["basins_def"]].index(basin_name)
                state_key = f"basin_{chr(97 + b_idx)}_state"
                got_vals.append(history[-1].get(state_key, 0))
                
            if got_vals != list(exp_val):
                return full_history, False, f"Step {step_idx} (Inputs {in_val}): Expected {exp_val}, got {got_vals}"
                
        # Mass preservation check on active registers in the final step
        for reg in ('A', 'B', 'C', 'D'):
            reg_active = full_history[-1].get(f"reg_{reg.lower()}_state", 0.0) == 1.0
            if reg_active:
                reg_mass = full_history[-1].get(f"rho_reg_{reg.lower()}", 0.0)
                if reg_mass < 14.0:
                    return full_history, False, f"Mass preservation breach: active Register {reg} mass is {reg_mass:.2f} (< 14.0)"
                    
        return full_history, True, "All sequential verification checks passed!"
        
    else:
        # Combinational task
        # Prime inputs
        input_keys = list(task["inputs"].keys())
        for idx, key in enumerate(input_keys):
            group.prime_basin(task["inputs"][key], active=(inputs_val[idx] == 1))
            
        try:
            history = vm.run(program)
            if not history:
                return [], False, "Execution empty history"
        except Exception as e:
            return [], False, f"Sequencer VM execution error: {e}"
            
        # Verify outputs
        out_keys = list(task["outputs"].keys())
        got_vals = []
        for out_name in out_keys:
            basin_name = task["outputs"][out_name]
            b_idx = [b[0] for b in task["basins_def"]].index(basin_name)
            state_key = f"basin_{chr(97 + b_idx)}_state"
            got_vals.append(history[-1].get(state_key, 0))
            
        expected_vals = task["expected_fn"](*inputs_val)
        logical_ok = task["verify_fn"](got_vals, expected_vals)
        
        if not logical_ok:
            return history, False, f"Expected {expected_vals}, got {got_vals}"
            
        # Insulation check: check inputs are not modified
        for idx, key in enumerate(input_keys):
            basin_name = task["inputs"][key]
            b_idx = [b[0] for b in task["basins_def"]].index(basin_name)
            state_key = f"basin_{chr(97 + b_idx)}_state"
            if history[-1].get(state_key, 0) != inputs_val[idx]:
                return history, False, f"Insulation breach: input {key} ({basin_name}) changed to {history[-1].get(state_key, 0)}"
                
        # Mass check: active registers retain mass
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

def run_rsi_loop(task_name: str, max_cycles: int = 5) -> Tuple[bool, str]:
    if task_name not in TASKS:
        print(f"Unknown task: {task_name}")
        return False, ""
        
    print(f"[START] Initializing RSI Agentic Code Inventor for task: {task_name}")
    task = TASKS[task_name]
    
    # Initialize SolLLM
    try:
        llm = SolLLM()
    except Exception as e:
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
            local_vars = {}
            # Import LuminaAgent inside execution namespace
            exec_globals = {"LuminaAgent": LuminaAgent, "LuminaCompiler": LuminaCompiler}
            exec(code, exec_globals, local_vars)
            
            # Find the LuminaAgent subclass
            agent_cls = None
            for name, val in local_vars.items():
                if isinstance(val, type) and issubclass(val, LuminaAgent) and val != LuminaAgent:
                    agent_cls = val
                    break
            
            if not agent_cls:
                raise ValueError("No subclass of LuminaAgent found in code.")
                
            agent_cls._source = code
            program = LuminaCompiler.compile_agent(agent_cls)
            print(f"Generated {len(program)} instructions successfully.")
        except Exception as e:
            err_msg = f"Compilation Error: {e}"
            print(f"[ERROR] {err_msg}")
            try:
                from coding_library.experts import LuminaExpertTeam
                expert_team = LuminaExpertTeam()
                expert_advice = expert_team.ask_expert("compiler", f"Here is the code that failed to compile:\n```python\n{code}\n```\nError message:\n{err_msg}", context_details={"task": task_name, "error": err_msg})
                print(f"[EXPERT CONSULTATION] Advice from Compiler Expert:\n{expert_advice}\n")
                advice_str = f"\n\nExpert Recommendation:\n{expert_advice}"
            except Exception as ex:
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
            history, ok, msg = run_trial(task_name, None, program)
            if not ok:
                passed_all = False
                trial_err = msg
                print(f"[ERROR] {trial_err}")
        else:
            # Run multiple combinational truth-table inputs
            for trial_input in task["input_space"]:
                history, ok, msg = run_trial(task_name, trial_input, program)
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
            except Exception as ex:
                advice_str = ""
            prompt = f"Lumina agent failed verification tests with error:\n{trial_err}{advice_str}\n\nHere was your code:\n```python\n{code}\n```\nPlease fix the logical/physical verification errors."
            history_log.append({"cycle": cycle, "status": "VERIFICATION_FAIL", "error": trial_err, "code": code})
            
    # Save ledger entries
    ledger_path = sol_root / "data" / "rsi" / "inventor_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        log_entry = {
            "task": task_name,
            "cycles_run": len(history_log),
            "success": any(h["status"] == "SUCCESS" for h in history_log),
            "final_status": history_log[-1]["status"] if history_log else "NO_ATTEMPTS",
            "history": history_log
        }
        f.write(json.dumps(log_entry) + "\n")
        
    return log_entry["success"], compiled_code

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SOL RSI Agentic Code Inventor")
    ap.add_argument("--task", default="half_adder", choices=list(TASKS.keys()), help="Target task to solve")
    ap.add_argument("--cycles", type=int, default=5, help="Maximum mutation refinement cycles")
    args = ap.parse_args()
    
    success, code = run_rsi_loop(args.task, args.cycles)
    sys.exit(0 if success else 1)
