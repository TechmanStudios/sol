# SOL Waveguide Microprogram Kernel Cost Model

This document outlines the purpose, architecture, deterministic metrics, and safety checks for the SOL Waveguide Microprogram Kernel Cost Model.

## 1. Purpose

The Cost Model statically analyzes and estimates execution costs across multiple equivalent execution forms. Rather than relying on non-deterministic wall-clock timing, the cost model leverages deterministic simulated metrics to evaluate compiler configurations and optimization passes.

## 2. Deterministic Cost Dimensions

The cost model evaluates candidates across a set of deterministic dimensions:
*   **simulated_cycles**: The number of instruction cycles when scheduled.
*   **wavefront_count**: The number of parallel instruction wavefronts.
*   **barrier_count**: The count of synchronization barriers (e.g. `WG_CHAN_FENCE`).
*   **compacted_windows**: The number of safely compacted instruction sequences.
*   **scheduled_batches**: The count of batched scoreboard scheduler tasks.
*   **recognized_kernels**: The count of communication motifs matched to the kernel library.
*   **trace_steps**: The count of instruction steps that would be logged in execution.
*   **trace_metadata_weight**: Estimated storage footprint weight of the trace step metadata.

## 3. Safety and Execution-Form Candidates

Eight candidates are evaluated statically:
1.  `raw_strict`
2.  `safe_local`
3.  `safe_memory`
4.  `safe_control`
5.  `full_safe_optimized`
6.  `v1_lowered_full_safe`
7.  `channel_dependency`
8.  `channel_kernelized`

Forms containing unsupported features (e.g., channel operations when `enable_waveguide_channel_state` is False, or v1 candidates when v1 support is disabled) are assigned an `unsupported_penalty` of `1,000,000` cycles and marked unsafe.

## 4. Replay Validation and Sandbox Caveat

> [!IMPORTANT]
> - All execution forms remain software-simulated shadow/sandbox execution only. No physical or hardware backend binding exists.
> - Trace replay validation verifies that the selected form in trace metadata matches the candidates list, is safe and equivalent, and matches the pass manager report structure.
