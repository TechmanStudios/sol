# SOL Waveguide Optimization Benchmark & Trace Replay Harness

This document describes the design, methodology, and verification steps of the **SOL Waveguide Optimization Benchmark + Trace Replay Harness**. This harness serves as a calibrated test stand (a dynamometer) for evaluating the latency savings of the pipeline compaction and scoreboard scheduling bridges on simulated PDM/waveguide architectures.

## Release Candidate Checkpoint (RC1)
For the comprehensive release candidate specifications, mappings, and proof ledger, see:
- [SOL Waveguide Optimization Research Dossier (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC1.md)
- [SOL Waveguide Architecture Map (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC1.md)
- [SOL Waveguide Proof Ledger (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC1.md)
- [SOL Waveguide Release Candidate Manifest JSON](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_RC1_MANIFEST.json)

---


## 1. Purpose

The Optimization Benchmark and Trace Replay Harness is a proof/measurement bridge designed to:
1. **Quantify optimization benefits**: Measure exact cycle-latency reductions of optimizations (local loop compaction, scoreboard superblock scheduling, and combined passes) relative to a raw unoptimized baseline.
2. **Enforce semantic equivalence**: Verify that optimization passes do not alter register final states, flags, memory cell contents, or PC transitions.
3. **Audit trace validity**: Provide trace-replay auditing to verify that execution metadata and step-by-step state transitions are consistent and compliant with Micro-ISA v0 semantics.

---

## 2. Benchmark Optimization Modes

Each canonical benchmark program is evaluated under four distinct modes:
- **Raw Strict**: Runs execution step-by-step with compaction and scheduling disabled.
- **Compacted Only**: Runs execution with pipeline compaction enabled, substituting microcoded ALU loops (multiplication, division) with fast prefix-carry logic.
- **Scheduled Only**: Runs execution with superblock wavefront scheduling enabled, grouping independent operations into parallel wavefronts.
- **Compacted & Scheduled**: Runs execution with both pipeline compaction and scoreboard scheduling enabled. Compacted loop windows are scheduled as single units.

---

## 3. Benchmark Case Families

The benchmark suite includes 32 canonical programs representing various instruction mixes and dependencies:
1. **Straight-line ALU**: Independent sequences, dependent register chains, and mixed operations.
2. **Flag Behavior**: Zero, carry, sign, overflow, and borrow-producing instructions.
3. **Branch Behavior**: Unconditional jumps, conditional branch-taken and branch-not-taken transitions, and flag-conditioned branches.
4. **Memory Behavior**: Basic `LOAD`/`STORE`, LOAD-after-STORE to same address, independent memory operations, and register-indirect dynamic memory barriers.
5. **Wide-Word Arithmetic**: Carry-heavy addition/subtraction, multiplication loops, and restoring division loops with different operand sizes and boundary values (including division by zero).
6. **Loop Patterns**: Compactable multiplication loops, compactable division loops, generic uncompactable loops, and branch loops that restrict scheduling.
7. **Mixed Whole-Program**: Complex combinations of ALU, memory shards, loop compaction, and branching.

---

## 4. Deterministic Cycle-Latency Methodology

To avoid timing instability on physical hardware:
- Latency is measured in **deterministic simulated cycles**, not wall-clock time.
- Each serial instruction execution counts as **1 cycle**.
- Compacted loops execute at a latency of **1 cycle per iteration** plus a flat log-scale overhead.
- Superblock wavefront execution counts as **1 cycle per wavefront batch**.
- Compacted loops scheduled inside wavefront batches consume their computed compacted cycle count.

---

## 5. Trace Replay Audit Methodology

Trace replay acts as a dynamic auditor:
1. **State transition reconstruction**: Starting from a clean virtual state, the replayer executes instructions recorded in the trace step-by-step.
2. **State assertions**: For each step, it verifies that computed results, memory addresses/values, flags, and PC transitions match the recorded trace.
3. **Metadata verification**:
   - Audits prefix-carry metadata (`strategy`, `lanes`, `resolved_carries`, `final_carry_out`, `signals`) for consistency with the word width.
   - Audits scheduler metadata (`scheduler_enabled`, `wavefront_id`, `batch_index`, `original_pcs`, `hazards_checked`, `barrier_reason`) to ensure the current step lies within the assigned wavefront PC range.

---

## 6. How to Run the Benchmark

To run the benchmarking suite and generate execution statistics, use the pytest framework or invoke the runner:

```bash
# Run benchmark tests and trace replay validation
pytest tests/test_waveguide_optimization_benchmark.py -v

# Run entire waveguide validation tests
pytest tests/test_waveguide_scoreboard_scheduler.py -v
pytest tests/test_waveguide_pipeline_compaction.py -v
pytest tests/test_waveguide_control_memory_bridge.py -v
pytest
```

---

## 7. Sandbox Caveat

All cycle measurements, latency benchmarks, and trace-replay validations are evaluated within the software-simulated sandbox environment. Optimization metrics reflect theoretical throughput on simulated architectures and do not represent mutations to active physical or quantum quantum-aligned hardware execution states.
