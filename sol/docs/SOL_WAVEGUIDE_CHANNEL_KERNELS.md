# SOL Waveguide Channelized Microprogram Kernels

This document outlines the architecture, specifications, safety guarantees, and scheduling interactions of the **SOL Channelized Microprogram Kernel Library + Pattern Recognizer Bridge**.

---

## 1. Overview and Purpose

The Channelized Microprogram Kernel Library and Pattern Recognizer form a static optimization bridge in the SOL Waveguide compiler and runtime fabric. They serve as a **recognition and reporting mechanism** for recurring, safe waveguide channel communication and dataflow motifs in v1 programs. 

### Core Principle
**Channelized kernels do not create new execution semantics.** Instead, they identify and validate existing deterministic channel and register transfer patterns:
1. Detect contiguous instruction sequences that represent known motifs.
2. Group them under structured **Kernel Descriptors**.
3. Propagate this information to the scoreboard scheduler and trace replayer.
4. Schedule them safely using existing v1/v0 execution paths, preserving strict serial execution semantics.

If a sequence cannot be safely matched or validated, the recognizer skips it and leaves the original instruction stream unchanged.

---

## 2. Kernel Descriptor Schema

Every recognized kernel span produces a deterministic metadata descriptor in the compiler pass manager:

```json
{
  "kernel_id": "channel_parallel_load",
  "kernel_version": "v1.experimental",
  "pc_range": [2, 5],
  "input_channels": [0, 1],
  "output_channels": [0, 1],
  "input_registers": ["R1", "R2"],
  "output_registers": ["R3", "R4"],
  "contains_fence": false,
  "requires_channel_state": true,
  "requires_channel_dependency_analysis": true,
  "lowering_strategy": "existing_v1_channel_ops",
  "scheduler_policy": "dependency_checked_wavefronts",
  "semantic_equivalence_required": true,
  "sandbox_only": true
}
```

---

## 3. Supported Kernel Patterns

### Kernel A: `channel_parallel_load`
*   **Signature**: Contiguous block of $N$ `WG_CHAN_SEND` instructions followed by $N$ `WG_CHAN_RECV` instructions on matching distinct channels.
*   **Axiom**: Independent channel sends can batch, and independent channel receives can batch if destination registers differ.
*   **Safety Rule**: All channel IDs must be static. Final registers and channel state must match serial execution exactly.

### Kernel B: `channel_fanout`
*   **Signature**: One `WG_CHAN_SEND` on a source channel, followed by $K$ `WG_CHAN_ROUTE` instructions copying data from the source channel to $K$ destination channels, followed by $K$ `WG_CHAN_RECV` instructions on the destination channels.
*   **Axiom**: One source channel fans out into multiple destination channels.
*   **Safety Rule**: Routes and receives may batch only if channel dependency hazard analysis permits. Destination registers must be distinct.

### Kernel C: `channel_fence_order`
*   **Signature**: A sequence of `WG_CHAN_SEND`, `WG_CHAN_FENCE`, and `WG_CHAN_RECV` on the same channel.
*   **Axiom**: The fence enforces strict global ordering.
*   **Safety Rule**: No optimization or batching is allowed across the `WG_CHAN_FENCE` boundary.

### Kernel D: `channel_gather`
*   **Signature**: A `channel_parallel_load` pattern feeding a vector lane assembly sequence (e.g. `VEC_PACK` or `VEC_INSERT`).
*   **Axiom**: Channels feed a vector register layout.
*   **Safety Rule**: Only recognized when vector instructions lower safely and do not violate read-after-write register constraints.

### Kernel E: `channel_route_chain`
*   **Signature**: A sequence of dependent routes (e.g., SEND to $ch_0$, ROUTE $ch_0 \to ch_1$, ROUTE $ch_1 \to ch_2$, RECV from $ch_2$).
*   **Axiom**: Sequential route dependency.
*   **Safety Rule**: Serves as a negative scheduling proof to prevent the scheduler from over-batching dependent steps.

---

## 4. Skipped and Unsafe Patterns

The recognizer will explicitly log and skip candidates with a documented reason under the following circumstances:
*   **Dynamic Channel IDs**: Channel indices determined dynamically by registers (e.g., `WG_CHAN_SEND R5, R1`) are rejected with `dynamic_channel_id_unsupported`.
*   **Partial Matches**: Incomplete motifs (e.g., a send with no receive, or a mismatch in channels) are skipped.
*   **Disabled in Config**: When `enable_channel_kernel_recognition` is `False`, all matches are skipped with `disabled_in_config`.
*   **Hazard Conflict**: If register allocation writes conflict or route dependencies collide, the kernel is marked as unsafe and skipped.

---

## 5. Scoreboard Scheduler and Replay Auditing

### Scoreboard Scheduling
*   The scheduler does not bypass channel hazard checks. It continues to use the **Channel Dependency Analysis** as the source of truth.
*   Recognized kernel spans are annotated in scheduler metadata. Fences act as hard wavefront boundaries; no batching is permitted across a kernel fence.

### Trace Replay Audits
The Trace Replayer performs validation on trace step metadata:
1.  Verifies kernel PC ranges are valid and contiguous.
2.  Ensures input/output channels match actual operations.
3.  Enforces that fences split kernel wavefront regions correctly.
4.  Rejects malformed kernel descriptors and disabled configurations emitting metadata.

---

## 6. Simulation Acceleration and Safety Caveats

*   **Sandbox-Only Execution**: All channel operations remain simulated in a deterministic software sandbox. No external physical I/O or network communications are performed.
*   **Sequential Acceleration**: Benchmark acceleration compares compacted execution plans against raw serial execution plans. Serial and accelerated batches remain deterministic and identical.
*   **Parallelism Exclusion**: No parallel pytest workers or multi-threaded executions are used to protect execution ordering.
