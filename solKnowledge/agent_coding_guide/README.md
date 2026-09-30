# SOL Engine Coding Guide for AI Agents

Welcome, Agent. This guide compiles the syntax, timing rules, and register scheduling strategies required to compile and execute program code on the **SOL Level 5 Hybrid Sub-system Register ALU**. 

As an agent, you must write code that operates within the physical constraints of coupled analog-semantic manifolds.

---

## 1. Hardware Overview (The 4-Register Core)

The CPU core consists of exactly **4 stateful registers** communicating through a central summing bus (`P_Sum`):

| Register | Type | Primary Role |
| :--- | :--- | :--- |
| **Register A** (`S_RA`) | Input / General | Left-hand input for logical operations, copy target. |
| **Register B** (`S_RB`) | Input / General | Right-hand input for logical operations, copy target. |
| **Register C** (`S_RC`) | Accumulator | Default destination for logic operations, copy source. |
| **Register D** (`S_RD`) | Accumulator | Secondary destination for carry operations. |

> [!WARNING]
> All logical operations (OR, AND, XOR, OR_MS, etc.) **must** read their inputs from Registers A and B. You cannot run operations directly on C and D.

---

## 2. Micro-Instruction Set Reference

Each instruction executes across a specific number of simulation steps (using a baseline $dt = 0.05$):

### A. LOAD `reg`, `basin_name` (55 Steps)
* **Syntax**: `Instruction("LOAD", [reg, basin_name])`
* **Execution**: Opens the routing gate for `reg` and establishes a wormhole connecting `basin_name` to `P_Sum` to transfer belief and mass into the target register.
* **Timing**: 40 steps write phase + 15 steps settling phase.

### B. STORE `reg`, `basin_name` (50 Steps)
* **Syntax**: `Instruction("STORE", [reg, basin_name])`
* **Execution**: Opens the routing gate for `reg` and establishes a wormhole from `P_Sum` to `basin_name` to write the register state back to memory.
* **Timing**: 30 steps write phase + 20 steps holding phase.

### C. Logical Gates: `OP` [`dest_reg`] (55 Steps)
* **Ops**: `OR`, `AND`, `OR_MS`, `AND_MS`, `XOR`, `XNOR`, `NOT`, `NAND`, `NOR`
* **Syntax**: `Instruction("XOR", ["C"])`
* **Execution**:
  - `OR`/`AND` (Physical threshold logic): Uses analog summation at `P_Sum` based on logical bias.
  - `*_MS` / `XOR` (Mixed-signal logic): Sequencer reads `S_RA_B` and `S_RB_B` battery states and directly drives the `dest_reg`.
* **Timing**: 30 steps compute phase + 25 steps settling phase.

### D. COPY `src`, `dest` (45 Steps)
* **Syntax**: `Instruction("COPY", [src, dest])`
* **Execution**: Routes the state of `src` register through `P_Sum` into `dest` register.
* **Timing**: 30 steps routing phase + 15 steps holding phase.

### E. CLEAR `reg` (30 Steps)
* **Syntax**: `Instruction("CLEAR", [reg])`
* **Execution**: Grounds the register battery, actively draining mass to $0.0$ and collapsing belief to $-1.0$.
* **Timing**: 30 steps collapse phase.

### F. RESET_CORE (20 Steps)
* **Syntax**: `Instruction("RESET_CORE", [])`
* **Execution**: Grounds the summing junction `P_Sum` and all routing gates, clearing residual fluxes. Normalizes Register A and B masses back to nominal levels (`40.0` host mass, `20.0` battery mass).
* **Mandatory Usage**: Must be executed before running physical `AND` threshold operations to prevent false triggers from accumulated mass.

---

## 3. Register Scheduling & Reuse Strategies

Because the CPU has only 4 registers and inputs must be read from A and B, you must use **time-multiplexed register reuse** to compile complex logic like Adders.

### The Full-Adder Register Reuse Pattern
To compute `SUM = A XOR B XOR Cin` and `Cout = (A AND B) OR (Cin AND (A XOR B))`:

1. **LOAD inputs**: Load $A \to A$ and $B \to B$.
2. **Compute intermediate gates**:
   - `XOR C` $\implies$ Register C holds $A \oplus B$.
   - `AND_MS D` $\implies$ Register D holds $A \cdot B$ (CARRY 1).
3. **Register Reuse (Freeing B)**:
   - We must compute $(A \oplus B) \oplus C_{in}$. But inputs must be in A and B.
   - Copy $C \to A$ (Register A now holds $A \oplus B$).
   - Clear Register C.
   - Load $C_{in} \to B$ (Register B now holds $C_{in}$).
   - `XOR C` $\implies$ Register C now holds SUM.
4. **Early Store**:
   - Store C to `Basin_SUM` early to free up Register C for the next carry step.
   - Clear Register C.
5. **Compute Cout**:
   - `AND_MS C` $\implies$ Register C holds $C_{in} \cdot (A \oplus B)$ (CARRY 2).
   - Copy $C \to A$ (A holds CARRY 2) and $D \to B$ (B holds CARRY 1).
   - Clear C and D.
   - `OR_MS D` $\implies$ Register D holds Cout.
   - Store D to `Basin_Cout`.

---

## 4. Verification Checklists for AI Agents

When verifying your program in a python test script:
- **Mass Preservation**: Assert that all active registers (whose batteries are in state `1`) retain mass $\ge 14.0$ units at the end of the program:
  ```python
  assert history[-1]["rho_reg_a"] >= 14.0
  ```
- **Semantic Insulation**: Assert that source basins did not change state during execution:
  ```python
  assert history[-1]["basin_a_state"] == A_initial
  ```
- **Timing Alignment**: Adjust your history index checks to account for `CLEAR` taking 30 steps instead of 50 steps.
