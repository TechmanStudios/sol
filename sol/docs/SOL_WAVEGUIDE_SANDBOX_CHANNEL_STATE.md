# SOL Waveguide Sandbox Channel State

This document describes the design, architecture, and safety model of the sandbox-only waveguide channel state introduced in the V1 extension candidate layer of the SOL Engine.

## Core Principle: Sandbox-Only Safety

The waveguide channel state is implemented **strictly as a simulated sandbox-local state**. There is no physical hardware binding, no network interface, no file descriptor access, and no asynchronous multithreaded runtime environment.

All channel operations are deterministic, isolated, and bounded. If simulation acceleration is disabled, channel state transitions and executions behave exactly sequentially.

> [!IMPORTANT]
> - Channel state is disabled by default.
> - Channel operations require both `enable_micro_isa_v1_candidates=True` and `enable_waveguide_channel_state=True` to be explicitly set in the config.
> - If `enable_waveguide_channel_state` is False, `WG_CHAN_SEND`, `WG_CHAN_RECV`, and `WG_CHAN_ROUTE` remain rejected.

## State Model

The sandbox channel state is represented by a bounded dictionary containing:

```python
{
    "channels": {
        0: {"valid": False, "value": 0},
        1: {"valid": False, "value": 0},
        ...
    },
    "width_bits": 32,
    "channel_count": 8,
    "overflow_policy": "mask",
    "recv_empty_policy": "zero_with_empty_flag",
    "clear_on_recv": False,
    "empty_flag_triggered": False
}
```

## Operation Semantics

### 1. `WG_CHAN_SEND channel, src`
- Validates that `channel` is within bounds `[0, channel_count - 1]`.
- Masks the `src` register value to the configured bit width (`width_bits`).
- Sets the target channel's valid bit to `True`.
- Overwrites the existing channel value deterministically.
- **No external I/O** is triggered.

### 2. `WG_CHAN_RECV dst, channel`
- Validates that `channel` is within bounds.
- If the channel is valid (populated):
  - Reads the value into the `dst` register.
  - If `clear_on_recv` is True, resets the channel valid bit to `False` and value to `0`.
- If empty (unpopulated):
  - Writes `0` to the `dst` register.
  - Sets the `empty_flag_triggered` metadata flag to `True`.

### 3. `WG_CHAN_ROUTE dst_channel, src_channel, route_mask`
- Validates destination and source channel IDs.
- If the `route_mask` is non-zero:
  - Copies the value and valid bit from `src_channel` to `dst_channel`.
- If the `route_mask` is zero:
  - The destination channel remains unchanged.

### 4. `WG_CHAN_FENCE`
- Serves as a deterministic ordering barrier.
- No register, memory, or channel value mutations.
- Forces the scheduler to preserve sequential program ordering across the barrier boundary.

## Scheduler Interaction

To prevent race conditions and preserve deterministic execution:
- `WG_CHAN_FENCE` remains a hard superblock and global ordering barrier.
- When `enable_channel_independence_analysis` is enabled, the scoreboard scheduler uses static dependency and hazard analysis to parallel-batch independent channel operations (e.g. sends on different channels) into single wavefronts.
- Overlapping channel read/write sets or register write conflicts are conservatively treated as hazards (RAW, WAR, WAW, or Read-Read Route conflicts) and split into separate wavefronts.
- When `enable_channel_kernel_recognition` is enabled, the compiler applies pattern recognition (see [SOL Waveguide Channelized Microprogram Kernels](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_CHANNEL_KERNELS.md)) to identify structured communication motifs (such as `channel_parallel_load` or `channel_fanout`) to ensure kernel execution paths comply with strict serial reference execution.
