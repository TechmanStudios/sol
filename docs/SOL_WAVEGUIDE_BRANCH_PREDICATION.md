# SOL Waveguide Branch-Diamond Predication + Conditional Select Lowering Bridge

This document details the architectural design, implementation, and verification of the **SOL Waveguide Branch-Diamond Predication + Conditional Select Lowering Bridge** optimization pass.

## Purpose

Branch-heavy code regions introduce significant control-flow overhead due to serial evaluation of status flags, program-counter redirects, and wavefront barriers. 

The Branch-Diamond Predication pass optimizes small, side-effect-free control-flow diamonds by collapsing branch transitions into branchless, deterministic conditional-select execution plans. This behaves like a waveguide multiplexer (MUX): both paths exist symbolically, but only the predicate-selected register writes commit to the final architectural state.

## Supported Branch-Diamond Patterns

The pass conservatively targets three standard control-flow geometries:

### Pattern A: Single-Arm Conditional Skip
```text
flag producer
JZ/JNZ target_label
then-arm: register-only ALU operations
target_label:
```
* **Lowering**: If the condition resolves to taken (meaning skip), the then-arm is bypassed. If not taken, the then-arm is executed. Branch instruction cycle overhead is bypassed.

### Pattern B: If/Else Diamond
```text
flag producer
JZ/JNZ else_label
then-arm: register-only ALU operations
JMP end_label
else_label:
else-arm: register-only ALU operations
end_label:
```
* **Lowering**: The branch condition evaluates the predicate. If `False` (condition not taken), the then-arm executes and the else-arm is bypassed. If `True` (condition taken), the else-arm executes and the then-arm is bypassed. Unconditional `JMP` and conditional branch overheads are eliminated.

### Pattern C: Conditional Move-Like Region
A specialization of Pattern A where a single register value is updated conditionally.

---

## Safety Barriers

To preserve strict serial semantics exactly, the optimizer enforces conservative safety barriers. A diamond **must not** be predicated if any of the following are detected:

1. **Memory Side-Effects**: Any `LOAD` or `STORE` operations inside the arms.
2. **Dynamic Addressing**: Any pointer arithmetic or memory accesses.
3. **Unknown Opcodes**: Any instructions not in the verified ALU/Register set.
4. **Nested Branching**: Any internal control flow (`JMP`, `JZ`, etc.).
5. **Control Stopping**: Any `HALT` instructions.
6. **External Flag Visibility**: Any flags written inside the arm that are read downstream before being overwritten.
7. **Loops**: Backwards loop jumps.

If any check fails, the pass skips predication, logs an explicit reason in `skipped_diamonds`, and falls back to standard strict microcoded execution.

---

## Predicate Mask Semantics

Predication evaluates branch conditions against the CPU status flags using the existing branch control logic (`evaluate_waveguide_branch_condition`):
- `JZ`, `JNZ` (Zero flag)
- `JC`, `JNC` (Carry flag)
- `JB`, `JNB` (Borrow flag)

The predicate evaluation results in a boolean `taken` state:
- If `taken` is `False`, the then-arm instructions commit.
- If `taken` is `True`, the then-arm is skipped (Pattern A) or the else-arm instructions commit (Pattern B).

---

## Conditional Select Lowering & Cycle Counting

Under predication, the cycle cost is calculated as the sum of executed instructions inside the active arm:
- Branch instructions (`JZ`, `JNZ`, `JMP`) are treated as MUX routing overhead and consume **zero** cycles.
- If no instructions are executed (taken skip in Pattern A), the pass charges `1` cycle for condition evaluation.

This yields significant latency reductions:
- **Pattern A (Taken)**: 1 cycle (previously 1 for JZ + 0 for skipped arm)
- **Pattern A (Not Taken)**: `num_then_instructions` (previously 1 for JZ + `num_then_instructions`)
- **Pattern B (Then Selected)**: `num_then_instructions` (previously 1 for JZ + `num_then_instructions` + 1 for JMP)
- **Pattern B (Else Selected)**: `num_else_instructions` (previously 1 for JZ + `num_else_instructions`)

---

## Trace Replay Auditing & Metadata

Each predicated trace step attaches `predication_metadata` containing:
- `predication_enabled` (`True`)
- `diamond_id` (Unique ID)
- `condition_opcode` (e.g. `JZ`)
- `predicate_value` (Boolean branch outcome)
- `original_condition_pc` (PC of JZ/JNZ)
- `then_pc_range` / `else_pc_range` (Arm boundaries)
- `merge_pc` (Convergence point)
- `lowering_strategy` (`"conditional_select"`)
- `registers_merged` (Written register names)
- `flags_merged` (Boolean indicating flag mutation)
- `memory_effects` (`False`)

The Trace Replay Auditor (`validate_predication_trace_metadata`) asserts:
- Correct strategy name.
- Absence of memory effects.
- That only instructions in the active arm were executed, and skipped arms contain zero trace steps.

---

## Benchmark Modes

Two new modes are added to the optimization benchmark matrix:

1. **`PREDICATED_ONLY`**:
   - `enable_branch_predication`: `True`
   - `enable_pipeline_compaction`: `False`
   - `enable_scoreboard_scheduling`: `False`

2. **`PREDICATED_COMPACTED_SCHEDULED`**:
   - `enable_branch_predication`: `True`
   - `enable_pipeline_compaction`: `True`
   - `enable_scoreboard_scheduling`: `True`

---

## Disabling Predication

To disable predication globally, configure the execution bridge:
```python
config = WaveguideControlMemoryBridgeConfig(
    width=32,
    enable_branch_predication=False
)
```

---

## Verification

To run predication-specific tests:
```bash
.venv\Scripts\pytest tests/test_waveguide_branch_predication.py -v
```

All execution remains software-simulated sandboxed validation. No physical hardware or quantum registers are mutated.
