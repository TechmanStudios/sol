# SOL Waveguide Memory Alias + Shard Range Analysis Bridge

This document specifies the design, architecture, and behavior of the **SOL Waveguide Memory Alias + Shard Range Analysis Bridge**. This analysis pass is designed for the strict PDM/waveguide microcoded backend (`pdm_waveguide_microcoded_strict`). It enables the optimizer stack to safely reason about memory operand relationships, shard boundaries, static ranges, and scheduling/predication opportunities without changing serial correctness.

---

## 1. Purpose

The Scoreboard Scheduler and Branch Predication engines natively treat memory accesses conservatively. By default, any `LOAD` or `STORE` instruction acts as a hard boundary (hazard barrier). This bridge introduces deterministic memory range and shard analysis to:
- Identify when different memory operations access disjoint shard address spaces.
- Prove that two accesses to the same shard do not overlap (disjoint static address ranges).
- Classify alias relationships to safely unlock reordering, parallel batching, and branch predication.

---

## 2. Memory Access Model

The memory model parses memory instructions (`LOAD` and `STORE`) to build metadata including:
- **PC**: The program counter of the instruction.
- **Opcode**: Either `LOAD` or `STORE`.
- **Access Kind**: `"read"` for `LOAD` or `"write"` for `STORE`.
- **Shard ID**: Shards represent isolated memory domains. If not explicitly specified on the instruction, the default is `"default"`.
- **Address & Address Kind**: The base memory address, classified as `"static"` (integer literals) or `"dynamic"` (register-indirect, e.g., `R1`).
- **Width**: The access width in bits (e.g., 32 or 64).
- **Range Bounds**: A computed address range `[range_start, range_end]`.

---

## 3. Address and Range Units

Addressing in the SOL Waveguide memory model uses cell-indexed or byte-indexed ranges. The range math is defined as:
- **Range Start**: `address`
- **Range End**: `address + (width_bits / 8) - 1` (with a minimum size of 1 byte/cell).

Example:
A 32-bit `LOAD` starting at static address `4` accesses bytes/cells in the range `[4, 7]`.

---

## 4. Shard Model

Memory is split into distinct, isolated shards. Shards are completely disjoint address spaces. 
- **Shard Isolation**: An access to `shard=A` and an access to `shard=B` are guaranteed never to alias, regardless of their addresses or ranges.
- **Cross-Shard Independence**: Shard isolation allows the scheduler to execute memory operations targeting different shards in parallel or in arbitrary orders without hazard checks.

---

## 5. Alias Classification

The alias classification engine compares two memory accesses and classifies their relationship into one of the following:

- **`NO_ALIAS`**:
  - The accesses target different shards.
  - The accesses target the same shard but have completely disjoint static address ranges (e.g. `[4, 7]` and `[8, 11]`).
- **`MUST_ALIAS`**:
  - The accesses target the same shard, have identical starting addresses, and identical access widths (e.g., `LOAD` and `STORE` both targeting `address=4` with `width=32`).
- **`MAY_ALIAS`**:
  - The accesses target the same shard and have overlapping ranges, but starting addresses or widths differ (e.g., a 64-bit access at `0` and a 32-bit access at `4`).
- **`UNKNOWN_ALIAS`**:
  - One or both accesses use dynamic addresses (e.g. register-indirect).
  - The shard ID or range bounds cannot be statically determined.

---

## 6. Scheduler Integration

The Scoreboard Scheduler incorporates the memory alias analysis in its hazard checks:
- **Disjoint Memory Parallelism**: `LOAD`s and `STORE`s can be batched together in the same wavefront or reordered only when they are proven to have a `NO_ALIAS` relationship.
- **Conflict Prevention**: If a `LOAD` and a `STORE` (or two `STORE`s) have a `MUST_ALIAS` or `MAY_ALIAS` relationship, they are classified as hazards, and a scheduling barrier is enforced to preserve sequential ordering.
- **Dynamic Address Barriers**: Any dynamic address or unknown alias forces a hard scheduling barrier, terminating the current wavefront batch.

---

## 7. Predication Integration

Branch predication converts branch-diamond control flow into data-flow selectors. Before this bridge, all branch diamonds containing memory operations were rejected.
- **Read-Only Predication**: When memory alias analysis is enabled, branch diamonds containing read-only `LOAD` operations can be predicated if:
  - All loads inside the branch arms target static, valid addresses.
  - The memory reads are side-effect-free.
  - No writes (`STORE` instructions) are present inside either arm of the diamond.
- **Write Speculation Restriction**: Diamonds containing `STORE` instructions remain strictly rejected. Memory writes are never speculated.

---

## 8. Safety Barriers

Ambiguous or unsafe memory configurations are skipped with explicit reasons. The safety model enforces the following barriers:
- **Dynamic Address Barrier**: Register-indirect addressing is skipped with `skip_reason="dynamic_address_unknown_alias"`.
- **Negative Address Barrier**: Out-of-bounds negative static addresses are skipped with `skip_reason="negative_address_out_of_bounds"`.
- **Malformed Metadata Rejection**: Malformed or inconsistent range metadata detected during validation triggers immediate verification failures.

---

## 9. Trace Metadata

When memory alias analysis is enabled, executed trace steps contain memory metadata under `memory_alias_metadata`.

For optimized/valid accesses:
```json
{
    "memory_alias_analysis_enabled": true,
    "memory_accesses": [
        {
            "pc": 7,
            "opcode": "LOAD",
            "access_kind": "read",
            "shard_id": "default",
            "address": 4,
            "address_kind": "static",
            "width_bits": 32,
            "range_start": 4,
            "range_end": 7,
            "is_dynamic": false,
            "is_barrier": false,
            "barrier_reason": null
        }
    ],
    "alias_classification": "NO_ALIAS",
    "memory_reorder_safe": true,
    "shard_id": "default",
    "range_start": 4,
    "range_end": 7
}
```

For skipped/barrier accesses:
```json
{
    "memory_alias_analysis_enabled": true,
    "memory_reorder_safe": false,
    "skip_reason": "dynamic_address_unknown_alias"
}
```

---

## 10. Benchmark Cases

The Optimization Benchmark Harness defines the following memory optimization test scenarios:
1. **`independent_static_loads`**: Multiple static loads to disjoint ranges in the same shard (verifies batching).
2. **`independent_static_stores_diff_shards`**: Stores to different shards (verifies batching across shards).
3. **`load_after_store_hazard`**: Same-address load-after-store (verifies hazard preservation).
4. **`store_after_load_hazard`**: Same-address store-after-load (verifies hazard preservation).
5. **`overlapping_static_ranges`**: Overlapping address ranges in the same shard (verifies hazard preservation).
6. **`dynamic_address_barrier`**: Dynamic register-indirect address (verifies barrier enforcement).
7. **`read_only_diamond_predication`**: Branch diamond containing read-only static loads (verifies predication).
8. **`unsafe_diamond_with_store`**: Branch diamond containing a store (verifies rejection).
9. **`mixed_optimized_program`**: A complex program combining ALU instructions, independent memory operations, and branch diamonds (verifies full stack composition).

---

## 11. How to Disable Memory Alias Analysis

Memory alias analysis is optional. By default, it is disabled unless explicitly enabled in the `WaveguideControlMemoryBridgeConfig`. 

To enable/disable it:
```python
from sol_waveguide_control_memory_bridge import WaveguideControlMemoryBridgeConfig

# Enable memory alias analysis
config = WaveguideControlMemoryBridgeConfig(
    enable_memory_alias_analysis=True
)

# Disable memory alias analysis (reverts memory ops to hard barriers)
config_disabled = WaveguideControlMemoryBridgeConfig(
    enable_memory_alias_analysis=False
)
```

---

## 12. Verification Commands

Run the sequential test suite:
```bash
# Run memory alias analysis unit tests
pytest tests/test_waveguide_memory_alias.py -v

# Run the optimization benchmark containing memory scenarios
pytest tests/test_waveguide_optimization_benchmark.py -v

# Run full sequential regression suite
pytest
```

---

## 13. Sandbox Caveat

> [!NOTE]
> All memory alias optimizations and execution flows run strictly in a simulated sandbox environment. No physical mutation of system hardware occurs.
