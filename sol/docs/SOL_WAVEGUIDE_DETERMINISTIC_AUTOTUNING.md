# SOL Waveguide Deterministic Autotuning Policy

This document describes the autotuning policy layer and selection rules for the SOL Waveguide Microprogram Kernel execution forms.

## 1. Policy Modes

The autotuner evaluates cost model reports and selects the execution form based on the active policy mode:
*   **`STRICT_ONLY`**: Always select raw strict execution.
*   **`SAFEST_OPTIMIZED`**: Select the lowest-risk optimized form with verified equivalence.
*   **`LOWEST_SIMULATED_CYCLES`**: Select the safe form with the fewest deterministic simulated cycles.
*   **`LOWEST_TRACE_FOOTPRINT`**: Select the safe form with the smallest trace footprint.
*   **`KERNEL_PREFERRED_SAFE`**: Prefer recognized kernel forms when they are equivalent and not more expensive.
*   **`DEBUG_EXPLAIN`**: Emit full comparison reports without aggressive selection.

## 2. Selection and Tie-Breaking

If multiple candidates have identical simulated cycle and barrier counts, ties are broken deterministically using:
1.  **Trace Footprint**: Prefer the candidate with the smaller trace metadata footprint.
2.  **Aggressiveness Index**: Prefer the less aggressive candidate form, ordered as:
    `raw_strict` < `safe_local` < `safe_memory` < `safe_control` < `full_safe_optimized` < `v1_lowered_full_safe` < `channel_dependency` < `channel_kernelized`

## 3. Sandbox Caveat

> [!WARNING]
> All autotuning and optimization selection remains strictly inside the software-simulated shadow/sandbox environment. No physical hardware adaptation takes place.
