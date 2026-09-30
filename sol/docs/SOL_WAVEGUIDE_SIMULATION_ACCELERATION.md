# SOL Waveguide Simulation Performance Acceleration

This document outlines the architecture, configuration options, and safety rules of the simulation performance acceleration bridge in the SOL Engine.

## Purpose & Boundaries

The simulation performance acceleration bridge introduces safe optimization tools to speed up offline benchmark and trace-replay workflows without introducing non-determinism or violating the sequential regression harness.

### Allowed Optimizations
- **Trace allocation optimization**: string interning, deduplication, and template caching to reduce memory overhead.
- **Compact trace modes**: stripping massive debug dumps (e.g. step-by-step register and memory state copies) on performance critical paths.
- **Deterministic batching**: executing multiple test cases sequentially or in parallel under isolated runtimes.
- **Offline parallel benchmark/replay evaluation**: utilizing thread pools for concurrent execution of independent test/replay cases.
- **Aggregated result sorting**: ensuring deterministic ordering of batch outputs.

### Forbidden Practices
- Parallel execution of `pytest` regression suites (which must remain strictly sequential).
- Non-deterministic core instruction execution.
- Shared mutable simulation state across parallel worker processes or threads.
- Sockets, network communication, background thread processes, or async hooks during execution.

## Acceleration Configuration

The acceleration bridge is configured via a conservative configuration object:

```json
{
    "enable_simulation_acceleration": false,
    "enable_compact_trace_mode": false,
    "enable_trace_metadata_template_cache": true,
    "enable_offline_benchmark_parallelism": false,
    "enable_offline_trace_replay_parallelism": false,
    "max_workers": 1,
    "deterministic_result_ordering": true,
    "worker_state_isolation": true
}
```

## Trace Allocation Optimization

### 1. String Interning
Repeated opcode names, register IDs, and metadata strings are interned using Python's `sys.intern()` to reduce heap size and garbage collection overhead during large runs.

### 2. Compact Trace Mode
When `enable_compact_trace_mode` is enabled, large trace arrays and dumps (such as register files and memory snapshots) are omitted from the trace history, keeping only execution verdicts and cycle stats.

### 3. Template Metadata Caching
Repetitive scheduler wavefront hazards, memory alias metadata dictionaries, channel metadata, channel dependency analysis results, and channelized kernel descriptors are frozen and cached, allowing multiple trace steps to share the same immutable objects.

## Offline Parallel evaluation

For batch matrix benchmarks and trace replay audits, users can enable offline parallelism:
- **Matrix benchmark batching**: `run_waveguide_optimization_matrix_batch` runs multiple bit-width cases concurrently.
- **Trace replay batching**: `run_waveguide_trace_replay_batch` audits multiple traces concurrently.
- **Equivalence Verification**: The parallel aggregator verifies that parallel results match sequential runs exactly for all semantic fields (omitting wall-clock timing metrics).
