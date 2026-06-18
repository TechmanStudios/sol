# SOL Waveguide Scoreboard Scheduler

This document specifies the design, architecture, and behavior of the **SOL Waveguide Scoreboard Superblock Execution Bridge**. The scheduler is a deterministic whole-program scheduling pass designed for the strict PDM/waveguide microcoded backend (`pdm_waveguide_microcoded_strict`). It groups independent instructions into safe parallel wavefront batches while preserving exact serial execution semantics, register outputs, flags, memory behavior, program-counter behavior, and trace auditability.

---

## 1. Purpose

The physical execution path of instructions through the PDM/waveguide simulation runs sequentially by default. The Scoreboard Scheduler extends latency optimization beyond local loop/prefix-carry compaction by analyzing instruction dependencies across entire basic blocks or superblocks. It schedules independent instructions into concurrent wavefronts, achieving significant cycle count reductions without violating strict serial semantics.

---

## 2. Relationship to Pipeline Compaction

The Scoreboard Scheduler and Pipeline Compaction Bridge function as complementary optimization layers:
1. **Pipeline Compaction** operates locally to compress sequential microcoded loop patterns (like shift-add multiplication or division).
2. **Scoreboard Scheduler** operates globally across the program, splitting it into superblocks.
3. Compacted loop windows are treated by the scheduler as single, schedulable units (unifying their internal register, flag, and memory dependencies) to ensure they are safely scheduled in relation to surrounding instructions.
4. Cycle counts in the execution report reflect savings from both layers when both are enabled.

---

## 3. Hazard Model

To ensure correctness, the scheduler builds dependency metadata for each instruction. The analyzer tracks:
- **Register Dependencies**: Read-After-Write (RAW), Write-After-Read (WAR), and Write-After-Write (WAW) hazards on registers `R0` through `R15`.
- **Flag Dependencies**: Hazards on zero, carry, overflow, sign, and borrow flags. ALU instructions write flags, which are then checked against flag-consuming branches or conditional instructions.
- **Memory Dependencies**: RAW, WAR, and WAW hazards on static memory addresses.
- **Control Flow & Barriers**: Operations that change the program counter (branches, jumps, HALT) or dynamic memory operations with register-indirect addresses are treated as strict barriers.

Instruction metadata is represented as:
```python
{
    "pc": 12,
    "opcode": "ADD",
    "reads_registers": ["R1", "R2"],
    "writes_registers": ["R3"],
    "reads_flags": [],
    "writes_flags": ["zero", "carry", "overflow", "sign", "borrow"],
    "reads_memory": [],
    "writes_memory": [],
    "changes_pc": False,
    "is_barrier": False,
    "reason": None,
}
```

---

## 4. Superblock Definition

A **superblock** is a linear sequence of instructions and compacted loop windows that does not cross any control-flow boundaries or unsafe operations. A superblock is terminated immediately when the scheduler encounters any of the following:
- Any branch or jump (`JMP`, `JZ`, `JNZ`, `JC`, `JNC`, `JB`, `JNB`)
- A `HALT` instruction
- Any unknown or unsupported instruction
- Any dynamic memory access (`LOAD` or `STORE` using register-based indirect addressing), which presents safety/aliasing ambiguity
- Any explicit trace boundary

Speculation across branches is strictly forbidden to preserve deterministic register, memory, and flag states.

---

## 5. Wavefront Batch Scheduling Rules

Within each safe superblock, the scheduler groups instructions into wavefront batches. Each batch represents a set of instructions that can execute in parallel during the same clock cycle.

Scheduling follows these strict rules:
1. **No Intrabatch Register Write Conflicts**: No instruction in a wavefront batch may write to a register that is read or written by another instruction in the same batch.
2. **No Intrabatch Register Read/Write Conflicts**: No instruction in a wavefront batch may read from a register that is written by another instruction in the same batch.
3. **No Intrabatch Flag Conflicts**: No instruction in a batch may consume flags that are written by another instruction in the same batch.
4. **No Intrabatch Memory Conflicts**: No two memory operations in the same batch may reference overlapping memory locations or involve dynamic addressing.
5. **Deterministic PC Ordering**: To guarantee absolute trace auditability and determinism, wavefront scheduling order and instruction batch assignment remain strictly bound to the original PC order.

---

## 6. Safety Barriers

If safety is uncertain, the scheduler always falls back to the existing strict serial/compacted execution path. 
For example:
- Unresolved memory addresses terminate the superblock to prevent hazard violations.
- Unknown instructions are marked as hard barriers, forcing sequential execution.
- If flag-producing instructions precede flag-consuming branches, they are partitioned into different batches/superblocks to guarantee correct branch resolution.

---

## 7. How to Disable Scheduling

Scoreboard scheduling is enabled by default. It can be disabled to run raw strict execution or compaction-only execution by setting `enable_scoreboard_scheduling` to `False` in the configuration:

```python
from sol_waveguide_control_memory_bridge import WaveguideControlMemoryBridgeConfig

# Disable scheduling to run compaction only
config = WaveguideControlMemoryBridgeConfig(
    width=64,
    enable_pipeline_compaction=True,
    enable_scoreboard_scheduling=False
)
```

---

## 8. Verification Commands

Verify the scoreboard scheduler and ensure zero regressions by running the test suite sequentially:

```bash
# Run scoreboard-specific scheduler tests
pytest tests/test_waveguide_scoreboard_scheduler.py -v

# Run compaction tests
pytest tests/test_waveguide_pipeline_compaction.py -v

# Run control-memory bridge tests
pytest tests/test_waveguide_control_memory_bridge.py -v

# Run strict backend execution proof tests
pytest tests/test_strict_backend_execution_proof.py -v

# Run full system regression
pytest
```

> [!IMPORTANT]
> **Sequential Execution Constraint**: Do not run tests in parallel (e.g., using `pytest -n` or xdist). Sequential execution is required to protect CPU and memory stability.

---

## 9. Sandbox Caveat

All scoreboard scheduling and wavefront execution cycle savings are validated within the software-simulated sandbox environment. These optimizations reflect theoretical throughput improvements on simulated PDM/waveguide architectures and do not mutate active physical or quantum quantum-aligned hardware execution states.
