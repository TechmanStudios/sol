# SOL Waveguide Optimization Research Dossier (RC2)

This dossier acts as the release-candidate engineering reference for the governed execution stack of the SOL waveguide engine (RC2), covering the optimizer, sandbox channel model, cost model, autotuner, and replay validation framework.

## 1. Executive Summary

The SOL Waveguide governed execution stack (RC2) provides a deterministic, verified compiler-optimization and policy framework for the `pdm_waveguide_microcoded_strict` backend. RC2 builds on the pipeline foundation of RC1 by integrating sandbox channels, static channel dependency analysis, channelized microprogram kernels, a deterministic kernel cost model, and a policy-driven autotuner. All optimizations are verified through a strict trace replay audit framework.

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
- The `pdm_waveguide_microcoded_strict` backend achieves `full_compliance` with the v0 target, guaranteeing bit-equivalent execution matching the scalar compliance model.
- Compliance verification is strictly separated from experimental v1 features.

## 4. Strict PDM/Waveguide Backend Architecture

The strict backend (`pdm_waveguide_microcoded_strict`) implements a cycle-accurate model of a parallel waveguide execution fabric:
- Wide-word instruction words execute over multiple lanes.
- Each lane computes operations independently unless synchronized by explicit routing fabrics.
- Out-of-order execution features are managed by compiler scoreboard scheduling rather than hardware runtime scheduling.

## 5. Control-Memory Bridge

The Control-Memory Bridge (`sol_waveguide_control_memory_bridge.py`) serves as the core runtime interface:
- It maintains the registers, flags, program counters (PCs), and memory state.
- It exposes configuration flags for pipeline compaction, scoreboard scheduling, branch predication, memory alias analysis, cost model, and deterministic autotuning.
- It records detailed execution trace steps, containing before/after states, registers, flags, and applied optimization, cost, or autotuning metadata.

## 6. Pipeline Compaction and Prefix Carry Routing

- **Pipeline Compaction** (`sol_waveguide_pipeline_compaction.py`): Compacts sequential independent instructions into parallel wavefronts.
- **Prefix Carry/Borrow Routing** (`sol_interlane_prefix_carry.py`): Performs fast multi-lane carry propagation using a prefix carry network.

## 7. Scoreboard Superblock Scheduling

The Scoreboard Scheduler (`sol_waveguide_scoreboard_scheduler.py`):
- Groups instructions into superblocks bounded by branch targets or memory fences.
- Constructs data dependency hazard graphs.
- Schedules instruction execution across multiple wavefronts.
- Respects read-after-write (RAW), write-after-read (WAR), and write-after-write (WAW) hazards, ensuring serial equivalence.

## 8. Branch-Diamond Predication

Branch-Diamond Predication (`sol_waveguide_predication.py`):
- Detects conditional branch patterns forming structured "diamonds".
- Replaces conditional branches with predicated execution or conditional-select instructions (`SELECT`, `CMOV*`).
- Rejects nested branches or diamonds containing memory writes to ensure safety.

## 9. Memory Alias and Shard Range Analysis

Memory Alias Analysis (`sol_waveguide_memory_alias.py`):
- Evaluates static address ranges for read/write instructions.
- Divides memory space into independent "shards" (ranges).
- Proves no-alias conditions for concurrent load/store operations to unlock scheduling concurrency.

## 10. Sandbox Channel State & Transition Model

The Waveguide Channel State (`sol_waveguide_channel_state.py`) implements a software-simulated, sandbox-local channel state model:
- Configures a fixed number of communication channels (default 8) with deterministic bit-widths.
- Models transitions for `WG_CHAN_SEND`, `WG_CHAN_RECV`, `WG_CHAN_ROUTE`, and `WG_CHAN_FENCE` instructions.
- Enforces bounded channel access, send masking, and empty receive policies (`zero_with_empty_flag` or `sign_extend`) in a software-simulated sandbox environment, isolating executions from external I/O.

## 11. Channel Dependency Analysis

Waveguide Channel Dependency Analysis (`sol_waveguide_channel_dependency.py`):
- Identifies RAW, WAR, and WAW hazards over communication channels.
- Calculates channel synchronization barriers.
- Prevents scheduler from batching parallel operations on the same channel unless they are proven to be independent.
- Treats `WG_CHAN_FENCE` as a global sync barrier.

## 12. Channelized Microprogram Kernels

The Channelized Kernel Library (`sol_waveguide_channel_kernel_library.py`) and Recognizer (`sol_waveguide_channel_kernel_recognizer.py`):
- Register canonical channel communication and dataflow motifs (`channel_parallel_load`, `channel_fanout`, `channel_fence_order`, `channel_gather`, `channel_route_chain`).
- Statically scan programs to recognize these motifs.
- Tag malformed or incomplete channel sequences with explicit skip reasons.

## 13. Deterministic Cost Model & Autotuner

The Cost Model (`sol_waveguide_kernel_cost_model.py`) and Autotuning Policy (`sol_waveguide_autotuning_policy.py`) provide a deterministic flight planner:
- Computes costs based on simulated cycles, wavefront counts, barriers, and trace metadata footprints.
- Does not use wall-clock timing.
- Enforces policies: `STRICT_ONLY`, `SAFEST_OPTIMIZED`, `LOWEST_SIMULATED_CYCLES`, `LOWEST_TRACE_FOOTPRINT`, `KERNEL_PREFERRED_SAFE`, and `DEBUG_EXPLAIN`.
- Reject unsafe or unsupported execution forms and ranks candidate profiles using deterministic tie-breaking rules.

## 14. Optimization Profiles and Pass Manager

The Pass Manager (`sol_waveguide_optimization_pass_manager.py`) orchestrates passes in a strict canonical order:
1. `program_adaptation`
2. `v1_candidate_lowering`
3. `memory_alias_analysis`
4. `channel_dependency_analysis`
5. `channel_kernel_recognition`
6. `branch_predication`
7. `pipeline_compaction`
8. `scoreboard_scheduling`
9. `execution_plan_validation`
10. `cost_model_evaluation`
11. `deterministic_policy_selection`
12. `trace_metadata_preparation`

## 15. Benchmark and Trace Replay Harness

- **Benchmark Harness** (`sol_waveguide_optimization_benchmark.py`): Evaluates execution correctness and cycles across 109 cases.
- **Trace Replay Audit** (`sol_waveguide_trace_replay.py`): Audits execution traces against emulation, validating that cost model and autotuning metadata match compiler decisions and rejecting unsafe forms.
