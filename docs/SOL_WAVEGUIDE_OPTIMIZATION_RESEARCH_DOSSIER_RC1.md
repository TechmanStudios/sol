# SOL Waveguide Optimization Research Dossier (RC1)

This dossier acts as a release-candidate checkpoint for the strict PDM/waveguide backend, its optimization framework, and the Micro-ISA v1 experimental candidate layer. It provides an engineering reference, proof metrics, and compliance guidelines for the SOL waveguide engine.

## 1. Executive Summary

The SOL Waveguide Optimization stack provides a deterministic, verified framework for compiling, optimizing, and verifying programs written for the SOL Micro-ISA. The release candidate (RC1) solidifies a stable compilation target with the `pdm_waveguide_microcoded_strict` backend. RC1 integrates pipeline compaction, prefix carry routing, superblock scoreboard scheduling, branch-diamond predication, and memory alias analysis. The architecture is verified through a rigorous dual-rail execution proof framework, comparing simulator traces against a golden ISA reference interpreter.

## 2. Scope and Sandbox Caveat

> [!IMPORTANT]
> **SANDBOX CAVEAT & SCOPE LIMITATION**
> All execution, simulation, trace replay, and validation described in this dossier and implemented in the SOL Engine codebase are strictly software-simulated shadow/sandbox executions.
> - There is no physical or quantum-hardware execution path.
> - No quantum or solid-state waveguide hardware binding is claimed or supported.
> - The codebase acts as a deterministic software model for compiler research and validation only.

## 3. Stable Micro-ISA v0 Compliance

Micro-ISA v0 remains the stable compliance target of the SOL engine. 
- All 21 standard v0 instructions (including register moves, comparisons, branches, loads, stores, and arithmetic/logical operations) are supported.
- Compliance is evaluated via the Micro-ISA compliance suite.
- The `pdm_waveguide_microcoded_strict` backend achieves `full_compliance` with the v0 target, guaranteeing bit-equivalent execution matching the scalar compliance model.
- Compliance verification is strictly separated from experimental v1 features.

## 4. Strict PDM/Waveguide Backend Architecture

The strict backend (`pdm_waveguide_microcoded_strict`) implements a cycle-accurate model of a parallel waveguide execution fabric:
- Wide-word instruction words execute over multiple lanes.
- Each lane computes operations independently unless synchronized by explicit routing fabrics.
- Pipeline hazard detection and execution safety are verified at the microcode level.
- Out-of-order execution features are managed by compiler scoreboard scheduling rather than hardware runtime scheduling.

## 5. Control-Memory Bridge

The Control-Memory Bridge (`sol_waveguide_control_memory_bridge.py`) serves as the core runtime interface:
- It maintains the registers, flags, program counters (PCs), and memory state.
- It exposes configuration flags for pipeline compaction, scoreboard scheduling, branch predication, and memory alias analysis.
- It implements execution step functions, executing instruction packets in parallel wavefronts.
- It records detailed cycle-by-cycle execution trace steps, containing before/after states, registers, flags, and applied optimization metadata.

## 6. Pipeline Compaction and Prefix Carry Routing

- **Pipeline Compaction** (`sol_waveguide_pipeline_compaction.py`): Compacts sequential independent instructions into unified wide-word operations. It uses data dependency dependency-graph analysis to merge instruction fields without introducing hazard states.
- **Prefix Carry/Borrow Routing** (`sol_interlane_prefix_carry.py`): Performs fast multi-lane carry propagation using a prefix carry network. It computes carry-out signals for wide addition/subtraction, resolving multi-lane carry sequences in \(O(\log N)\) gate delays.

## 7. Scoreboard Superblock Scheduling

The Scoreboard Scheduler (`sol_waveguide_scoreboard_scheduler.py`):
- Groups instructions into independent basic blocks (superblocks) bounded by branch targets or memory fences.
- Constructs data dependency hazard graphs.
- Schedules instruction execution across multiple wavefronts.
- Respects read-after-write (RAW), write-after-read (WAR), and write-after-write (WAW) hazards, ensuring serial equivalence.

## 8. Branch-Diamond Predication

Branch-Diamond Predication (`sol_waveguide_predication.py`):
- Detects conditional branch patterns forming structured "diamonds" (if-then or if-then-else structures).
- Replaces conditional branches with predicated execution or conditional-select instructions (`SELECT`, `CMOV*`).
- Eliminates branch bubbles and pipeline hazards for safe conditional sequences.
- Rejects nested branches or diamonds containing memory writes to ensure strict safety.

## 9. Memory Alias and Shard Range Analysis

Memory Alias Analysis (`sol_waveguide_memory_alias.py`):
- Evaluates static address ranges for read/write instructions.
- Divides memory space into independent "shards" (ranges).
- Proves no-alias conditions for concurrent load/store operations.
- Unlocks scoreboard scheduling across memory accesses when no alias hazard exists, preventing scheduling serialization.

## 10. Optimization Profiles and Pass Manager

- **Optimization Profiles** (`sol_waveguide_optimization_profile.py`): Defines configurations ranging from `RAW_STRICT` (no optimizations) to `FULL_SAFE_OPTIMIZED` and `V1_CANDIDATE_EXPERIMENTAL`.
- **Pass Manager** (`sol_waveguide_optimization_pass_manager.py`): Orchestrates compiler passes in a strict canonical order:
  1. `program_adaptation`
  2. `v1_candidate_lowering`
  3. `memory_alias_analysis`
  4. `branch_predication`
  5. `pipeline_compaction`
  6. `scoreboard_scheduling`
  7. `execution_plan_validation`
  8. `trace_metadata_preparation`
- Checks subsequence alignment and enforces ordering constraints.

## 11. Benchmark and Trace Replay Harness

- **Benchmark Harness** (`sol_waveguide_optimization_benchmark.py`): Evaluates cycle counts and execution correctness across a diverse suite of 58 benchmark cases under varying optimization profiles.
- **Trace Replay Audit** (`sol_waveguide_trace_replay.py`): Replays recorded execution traces against local emulation, validating that intermediate states match the trace and rejecting any malformed optimization metadata.

## 12. Micro-ISA v1 Candidate Lowering

Micro-ISA v1 candidates are optional and disabled by default. The lowering module (`sol_micro_isa_v1_lowering.py`):
- Translates v1 candidate opcodes into equivalent v0 instruction sequences before optimization and scheduling.
- Emits detailed trace mapping metadata linking the original v1 candidate instruction to its lowered v0 components.
- Integrates lowered sequences directly into compaction, scheduling, and validation passes.

## 13. Micro-ISA v1 Formal Spec and Extension Matrix

- **Formal Specification** (`sol_micro_isa_v1_spec.py`): Defines maturity levels, operand schemas, semantics, and safety constraints for each v1 candidate.
- **Extension Compliance Matrix** (`sol_micro_isa_v1_capability_matrix.py`): Classifies v1 support tiers across backends (e.g. `emulated` vs. `unsupported`).
- The matrix is audited separately from stable v0 compliance to prevent false promotion.

## 14. Lane/Vector Candidate Extension

The v1 candidate layer includes guarded lane/vector operations:
- `VEC_PACK` / `VEC_UNPACK`: Pack/unpack scalar lane values.
- `VEC_BROADCAST` / `VEC_EXTRACT` / `VEC_INSERT`: Replicate and manipulate lanes.
- `VEC_LANE_ADD` / `VEC_LANE_SUB` / `VEC_LANE_AND` / `VEC_LANE_OR` / `VEC_LANE_XOR`: Guarded vector operations.
- `VEC_MASK_SELECT`: Per-lane conditional select under mask.
- Lowering transforms these operations into scalar bit shift, mask, and ALU operations, preserving strict lane-carry isolation.

## 15. Waveguide Channel Candidate Safety Model
 
- Unsafe channel operations (`WG_CHAN_SEND`, `WG_CHAN_RECV`, `WG_CHAN_ROUTE`) are rejected by default. However, when `enable_waveguide_channel_state` is explicitly enabled, they execute under a strict, bounded, deterministic sandbox-only channel state model.
- `WG_CHAN_FENCE` remains supported as a deterministic ordering barrier. All channel operations behave as scheduling barriers, preventing scoreboard scheduling reordering across their boundaries.

## 16. Representative Cycle Savings

Representative cycles savings from benchmark runs demonstrate the efficacy of the optimization stack:
- **Compacted Only**: 15–25% cycle reduction.
- **Scheduled Only**: 10–20% cycle reduction.
- **Compacted and Scheduled**: 20–35% cycle reduction.
- All optimized runs maintain bit-equivalent register and memory outputs compared to unoptimized runs.

## 17. Test and Regression Summary

- The regression suite is run sequentially using `pytest`.
- Parallel pytest workers (`-n`) are disabled.
- Standard regression results: All 862 tests pass.
- Manifest validation tests verify the consistency of release candidate metadata and documentation presence.

## 18. Known Limitations
 
1. **Sandbox-Only Waveguide Channels**: Bounded channel state emulates sending and receiving, but no physical external I/O, sockets, files, networks, or hardware hooks exist. Operations remain strictly sandbox-local and software-simulated.
2. **Simple Branch Diamonds**: Predication only targets single branch diamonds. Nested branch conditions or diamonds containing memory store operations are skipped.
3. **Local Scoreblocks**: Scoreboard scheduling is restricted to straight-line code regions (superblocks) separated by branches, jumps, or explicit fence instructions.
4. **Software Emulation**: No real hardware execution is supported. The compiler and execution engine operate in a sandboxed, simulated environment only.

## 19. Next Research Directions

1. **Extended Predication Diamonds**: Generalize the predication pass to support simple nested conditional paths.
2. **Loop Unrolling Integration**: Research loop unrolling techniques to feed larger instruction windows into the scoreboard scheduler.
3. **Refined Alias Analysis**: Improve memory alias range detection using pointer stride analysis.

## 20. RC1 Addendum: Sandbox Channel State + Simulation Acceleration Bridge
 
An engineering extension has been integrated to support:
1. **Deterministic Sandbox Channel State**: Bounded sandbox channels (default 8, 32-bit width) with deterministic route copying, send masking, and empty receive policies.
2. **Simulation Acceleration Harness**: Serial-safe trace allocation optimizations, string interning, template metadata reuse, compact trace modes, and optional offline parallel benchmark/trace replay batch execution. All core simulator cycles and pytest regression runs remain strictly sequential and deterministic.
