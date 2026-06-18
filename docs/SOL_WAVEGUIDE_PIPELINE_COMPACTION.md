# SOL Waveguide Pipeline Compaction

This document specifies the design, architecture, and behavior of the **SOL Waveguide Pipeline Compaction Bridge**. The compaction bridge is an optimization pass designed for the strict PDM/waveguide microcoded backend (`pdm_waveguide_microcoded_strict`). It reduces cycle latency in loops and carry propagation chains without compromising the deterministic correctness or strict backend execution rules of the SOL wide-word architecture.

---

## 1. Purpose

The physical execution path of instructions through the PDM/waveguide simulation is highly detailed and structurally complex, resulting in a large number of cycles to process multi-instruction sequences. The Pipeline Compaction Bridge optimizes these sequences by replacing long, multi-cycle microcoded chains (particularly multiplication and division loops) with mathematically equivalent, compressed parallel execution steps.

---

## 2. Scope

The Compaction Bridge applies exclusively to:
- **ALU operations** (ADD, SUB, CMP, and bitwise/shift operations) that form carry propagation chains.
- **Multiplication loops** (specifically shift-add multiplication patterns).
- **Division loops** (specifically restoring division scaffold patterns).

All compaction occurs in the shadow/sandbox software simulator layer and is guaranteed to be 100% semantically equivalent to uncompacted execution.

---

## 3. Safety Barriers

Compaction is a "reversible pressure-valve". If a microcode sequence contains any pattern that cannot be safely optimized, the compaction pass is skipped, and execution falls back to standard step-by-step PDM microcode simulation.

Compaction is strictly **skipped** (unsafe) under the following conditions:
1. **Memory Operations**: Any loop window containing `LOAD` or `STORE` instructions.
2. **Branch Turbulence**: Any loop window containing indirect branches or control flow transitions outside of the detected loop boundaries.
3. **Unknown/Unsupported Opcodes**: Any instruction within the window that does not map to the official SOL Micro-ISA v0 specification.
4. **Flag Dependents**: Flag-producing instructions whose flags are consumed outside the window in a way that cannot be determined statically.

Skipped windows are logged in the execution report's `unsafe_windows_skipped` field for traceability and auditing.

---

## 4. Parallel Prefix Carry/Borrow Routing

To compact additions, subtractions, and comparisons at the hardware-simulation boundary:
- The wide-word value is decomposed into independent **8-bit byte lanes**.
- The compaction engine constructs speculative **generate ($G$)** and **propagate ($P$)** signals across these lanes.
- A **Parallel Prefix Carry Resolver** computes all carries or borrows concurrently using log-scale lookahead routing.
- The lanes are reassembled, and flags (Zero, Carry, Sign, Overflow, Borrow) are updated to match the final result.

This approach guarantees that the resulting register values and status flags match a gold-standard Python integer oracle down to the exact bit under the current word width (32-bit or 64-bit).

---

## 5. Multiplication & Division Loop Compaction

### Shift-Add Multiplication Compaction
- **Pattern Matcher**: Detects loops composed of `AND`, `SHL`, `SHR`, `ADD`, and conditional jump instructions.
- **Optimization**: The shift-add iterations are evaluated using fast parallel prefix arithmetic, bypassing physical waveguide cycles.
- **Latency Reduction**: Simulates the execution at a latency of 1 cycle per iteration plus a flat log-scale overhead, significantly reducing cycle counts.

### Restoring Division Compaction
- **Pattern Matcher**: Detects loops composed of `CMP`, `SUB`, `ADD`, and conditional jump instructions.
- **Optimization**: The restoring division sequence is evaluated using fast subtraction and comparison steps.
- **Latency Reduction**: Reduces cycle counts to log-scale complexity. Division by zero is detected and raises a `TimeoutError` in accordance with VM specifications.

---

## 6. How to Disable Compaction

Compaction is enabled by default to optimize execution speed. It can be disabled globally or per-program by setting the `enable_pipeline_compaction` flag to `False` in the execution configuration:

```python
from sol_waveguide_control_memory_bridge import WaveguideControlMemoryBridgeConfig

# Disable compaction to run raw uncompacted microcode simulation
config = WaveguideControlMemoryBridgeConfig(
    width=64,
    enable_pipeline_compaction=False
)
```

---

## 7. Verification Commands

Verify the compaction bridge and ensure zero regressions by running the test suite sequentially:

```bash
# Run compaction-specific tests
pytest tests/test_waveguide_pipeline_compaction.py -v

# Run bridge-specific tests
pytest tests/test_waveguide_control_memory_bridge.py -v

# Run full strict backend validation
pytest tests/test_strict_backend_execution_proof.py -v

# Run full system regression
pytest
```

> [!IMPORTANT]
> **Sequential Execution Constraint**: Do not run tests in parallel (e.g., using `pytest -n` or xdist). Parallel workers can overload CPU scheduling and cause timing-sensitive verification checks to fail or hang on older hardware.

---

## 8. Sandbox Caveat

All pipeline compaction proofs and cycle savings are validated within the software-simulated sandbox environment. Compaction metrics reflect theoretical throughput optimizations on simulated PDM/waveguide architectures and do not represent mutations to active physical or quantum quantum-aligned hardware execution states.
