# AI Agent Tutorial: Writing Code for the SOL Engine

Welcome, future Agent! This folder contains concrete examples, reference manuals, and a runnable example runner script designed to show you exactly how to write, compile, and execute code for the SOL substrate.

---

## What is Symbolic Programming on SOL?

In Level 6 (Basic Software), you write programs as **Symbolic Equations** rather than mapping raw register connections manually. The SOL compiler (`LogosCompiler`) parses these equations, runs liveness analysis, schedules registers dynamically (A, B, C, D), and handles register copies and memories.

The resulting program is run on the **LogosVM** (Virtual Machine), which supports conditional control-flow branching based on the physical state of the analog substrate registers.

### Standard Programming Workflow
1. **Define Inputs and Outputs**: Create dictionaries mapping symbolic variables to physical memory basins:
   ```python
   inputs = {"A": "Basin_A", "B": "Basin_B", "Cin": "Basin_Cin"}
   outputs = {"SUM": "Basin_SUM", "Cout": "Basin_Cout"}
   ```
2. **Write Statements**: Formulate symbolic boolean equations:
   ```python
   statements = [
       ("OP", "xor1", "XOR", "A", "B"),
       ("OP", "and1", "AND_MS", "A", "B"),
       ("OP", "SUM", "XOR", "xor1", "Cin"),
       ("STORE", "SUM", "Basin_SUM"),
       ("OP", "and2", "AND_MS", "xor1", "Cin"),
       ("OP", "Cout", "OR_MS", "and2", "and1"),
       ("STORE", "Cout", "Basin_Cout")
   ]
   ```
3. **Compile**: Compile the statements dynamically:
   ```python
   compiler = LogosCompiler()
   instructions = compiler.compile(inputs, outputs, statements)
   ```
4. **Execute on LogosVM**: Initialize a ManifoldGroup, wrap the sequencer in `LogosVM`, and execute:
   ```python
   vm = LogosVM(sequencer)
   history = vm.run(instructions)
   ```

---

## Guidelines for Writing Statements

1. **Logical Operator Suffixes**:
   - Prefer `_MS` (mixed-signal) variants for intermediate arithmetic calculations (`AND_MS`, `OR_MS`) as they evaluate register battery states directly.
   - Use physical threshold logic (`AND`, `OR`) only when specifically targeting the analog summing behavior of the bus.
2. **Variable Liveness**:
   - The compiler is smart: it tracks when variables are used for the last time to automatically release registers.
   - If you want to keep a variable alive, reference it in a downstream instruction or `STORE` it to a memory basin early.
3. **Register Boundaries**:
   - There are only 4 physical registers: `A`, `B`, `C`, and `D`.
   - The compiler will automatically attempt to spill a register if it runs out of space, but it is best practice to keep active variables in any window $\le 4$ to avoid compiler errors.

---

## Try Running the Example Runner

Run the example script to see the compilation and execution pipeline in action:
```bash
python solKnowledge/agent_coding_guide/examples/example_runner.py
```
This script compiles and executes a 1-bit Full-Adder program dynamically.
