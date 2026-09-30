# SOL Waveguide Channel Dependency Analysis & Scheduling Bridge

## Purpose

The **SOL Waveguide Channel Dependency Analysis & Scheduling Bridge** extends the deterministic sandbox channel state model with static hazard and dependency detection. This allows the scoreboard scheduler to safely batch independent channel operations into single wavefronts, accelerating simulation performance while preserving strict sequential execution semantics.

## Relationship to Sandbox Channel State

This bridge refines the behavior of the experimental waveguide channel operations (`WG_CHAN_SEND`, `WG_CHAN_RECV`, `WG_CHAN_ROUTE`, `WG_CHAN_FENCE`). In previous versions, any waveguide channel operation was treated as a hard barrier. With this bridge, operations that do not conflict on their read/write channel sets or register outputs are scheduled to run in parallel in the same wavefront.

## Channel Read/Write Sets

Each waveguide channel instruction is statically parsed to build its channel and register access sets:

*   **`WG_CHAN_SEND channel=C`**:
    *   Writes channel `C`.
    *   Reads register `src`.
*   **`WG_CHAN_RECV channel=C`**:
    *   Reads channel `C`.
    *   Writes register `dst`.
*   **`WG_CHAN_ROUTE dst=D src=S`**:
    *   Reads channel `S`.
    *   Writes channel `D`.
    *   Reads route mask register/value.
*   **`WG_CHAN_FENCE`**:
    *   Acts as a global ordering barrier.

## Channel Hazard Classifications

The scheduler classifies hazards between any two channel operations using a conservative model:

1.  **`NO_CHANNEL_HAZARD`**: No overlapping channel or register reads/writes. Batching is safe.
2.  **`CHANNEL_RAW`**: Read After Write conflict on a channel (e.g., `SEND ch0` followed by `RECV ch0`).
3.  **`CHANNEL_WAR`**: Write After Read conflict on a channel (e.g., `RECV ch0` followed by `SEND ch0`).
4.  **`CHANNEL_WAW`**: Write After Write conflict on a channel (e.g., `SEND ch0` followed by `SEND ch0`).
5.  **`CHANNEL_ROUTE_CONFLICT`**: Read/Read overlap on the same channel (e.g., `RECV ch0` and `ROUTE ch1, ch0`). Read-Read operations cannot batch to prevent non-deterministic wavefront evaluation order.
6.  **`CHANNEL_GLOBAL_FENCE`**: Overlap with `WG_CHAN_FENCE`. Splits wavefront execution.
7.  **`CHANNEL_UNKNOWN`**: Overlap on dynamic/unresolved register channels or register destination conflicts.

## Scheduler Batching Rules

*   **Allowed**:
    *   `SEND ch0` with `SEND ch1`
    *   `RECV ch0` with `RECV ch1` (if destination registers differ)
    *   `SEND ch0` with `RECV ch1`
    *   `ROUTE ch0→ch1` with `SEND ch3`
    *   `ROUTE ch0→ch1` with `RECV ch3`
*   **Forbidden**:
    *   `SEND ch0` with `RECV ch0`
    *   `SEND ch0` with `SEND ch0`
    *   `RECV ch0` with `ROUTE ch0→ch1`
    *   `ROUTE ch0→ch1` with `SEND ch1`
    *   Any operation crossing `WG_CHAN_FENCE`
    *   Unknown/dynamic channel IDs
    *   Register write conflicts from concurrent receives

## Fence Behavior

`WG_CHAN_FENCE` remains a hard global ordering barrier. It cannot share a wavefront with any other instructions. It separates superblocks and forces the completion of all prior channel accesses before any subsequent accesses are initiated.

## Trace Metadata

When channel scheduling is active, scheduler trace metadata includes:

```json
{
    "channel_dependency_analysis_enabled": true,
    "channel_wavefront_id": 3,
    "channel_ops_batched": ["WG_CHAN_SEND", "WG_CHAN_RECV"],
    "channel_hazards_checked": true,
    "channel_hazard_result": "NO_CHANNEL_HAZARD"
}
```

## Trace Replay Validation

The trace replayer validates:
1.  Well-formedness of channel scheduler metadata.
2.  Conflict-free scheduling in every wavefront (no hazard exists between any two batched channel ops).
3.  That `WG_CHAN_FENCE` is the sole instruction in its wavefront.
4.  That final registers, memory, and channel state snapshots exactly match the sequential strict execution reference.

## Channelized Microprogram Kernels

The compiler leverages the [SOL Waveguide Channelized Microprogram Kernel Library](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_CHANNEL_KERNELS.md) to detect recurring motifs. The pattern recognizer identifies sequences matching five canonical kernels:
1.  **`channel_parallel_load`**: Independent sends followed by matching receives.
2.  **`channel_fanout`**: A single send fanning out to multiple channels via routes.
3.  **`channel_fence_order`**: Ordering boundary enforcement using a fence.
4.  **`channel_gather`**: Channel feeds combined into vector lane assemblies.
5.  **`channel_route_chain`**: Sequential route dependency checks.

## Safety Limitations

Channel independence analysis is strictly static and conservative. If channel IDs cannot be statically resolved (e.g., they reside in registers), the scheduler treats the operation as a barrier.

## Sandbox Caveat

Execution remains software-simulated shadow/sandbox only. No physical waveguide hardware execution paths are assumed or claimed.
