# SOL Instruction Cheat Sheet & Timing Reference

This document compiles the micro-instructions available on the **SOL Level 6 Basic Software / Level 5 Micro-sequencer** substrate.

---

## 1. Data Transfer Instructions

### LOAD `reg`, `basin`
* **Purpose**: Load analog belief and mass from a memory basin into a register.
* **Duration**: 55 steps (40 compute + 15 settle).
* **Syntax**: `Instruction("LOAD", ["A", "Basin_A"])`

### STORE `reg`, `basin`
* **Purpose**: Store analog belief and mass from a register back to a memory basin.
* **Duration**: 50 steps (30 compute + 20 settle).
* **Syntax**: `Instruction("STORE", ["C", "Basin_SUM"])`

### COPY `src`, `dest`
* **Purpose**: Transfer belief and mass from a source register to a destination register.
* **Duration**: 45 steps (30 compute + 15 settle).
* **Syntax**: `Instruction("COPY", ["C", "A"])`

### CLEAR `reg`
* **Purpose**: Discharge register mass and collapse belief state to -1 (empty/inactive).
* **Duration**: 30 steps.
* **Syntax**: `Instruction("CLEAR", ["A"])`

### RESET_CORE
* **Purpose**: Clear summing bus edge fluxes and reset input registers to nominal masses.
* **Duration**: 20 steps.
* **Syntax**: `Instruction("RESET_CORE", [])`
* **Rule**: Run before physical `AND` gate configurations to prevent false triggers from lingering mass.

---

## 2. Logical Instructions (Registers A & B $\to$ Dest)

Logical instructions read inputs from Registers A and B, computing results into a destination register.

| Instruction | Type | Dest | Description |
| :--- | :--- | :---: | :--- |
| `OR` | Physical | C | Threshold logic; checks if combined input mass triggers dest battery. |
| `AND` | Physical | D | Threshold logic; requires combined mass of both inputs to trigger dest battery. |
| `OR_MS` | Mixed-Signal | C/D | Checks input battery states and directly drives dest register belief. |
| `AND_MS` | Mixed-Signal | C/D | Checks input battery states and directly drives dest register belief. |
| `XOR` | Mixed-Signal | C/D | Checks if input battery states are mismatched (`A != B`). |
| `XNOR` | Mixed-Signal | C/D | Checks if input battery states are matched (`A == B`). |
| `NOT` | Mixed-Signal | C/D | Computes logical NOT of Register A. |
| `NAND` | Mixed-Signal | C/D | Computes logical NOT of (A AND B). |
| `NOR` | Mixed-Signal | C/D | Computes logical NOT of (A OR B). |

* **Duration**: 55 steps (30 compute + 25 settle).
* **Syntax**: `Instruction("XOR", ["C"])` or `Instruction("AND_MS", ["D"])`

---

## 3. Control Flow Branching Instructions

Branching instructions control the program counter (`pc`) in `LogosVM`. They do not advance time on the physical substrate (they execute in 0 steps at the software layer).

### LABEL `name`
* **Purpose**: Define a jump target label.
* **Syntax**: `Instruction("LABEL", ["MY_LABEL"])`

### JUMP `name`
* **Purpose**: Jump unconditionally to `MY_LABEL`.
* **Syntax**: `Instruction("JUMP", ["MY_LABEL"])`

### JUMP_IF_ACTIVE `reg`, `name`
* **Purpose**: Jump to `MY_LABEL` if Register `reg`'s battery state is active (`state == 1`).
* **Syntax**: `Instruction("JUMP_IF_ACTIVE", ["A", "MY_LABEL"])`

### JUMP_IF_COLLAPSED `reg`, `name`
* **Purpose**: Jump to `MY_LABEL` if Register `reg`'s battery state is collapsed (`state == -1`).
* **Syntax**: `Instruction("JUMP_IF_COLLAPSED", ["A", "MY_LABEL"])`
