# SOL Waveguide Optimization Profile + Pass Manager Bridge

This document specifies the design, architecture, and behavior of the **SOL Waveguide Optimization Profile + Pass Manager Bridge**. This architecture-hardening layer is designed for the strict PDM/waveguide microcoded backend (`pdm_waveguide_microcoded_strict`). It centralizes optimizer configuration, enforces safe pass ordering, produces unified optimization reports, and simplifies trace replay and verification auditing.

## Release Candidate Checkpoint (RC1)
For the comprehensive release candidate specifications, mappings, and proof ledger, see:
- [SOL Waveguide Optimization Research Dossier (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC1.md)
- [SOL Waveguide Architecture Map (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC1.md)
- [SOL Waveguide Proof Ledger (RC1)](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC1.md)
- [SOL Waveguide Release Candidate Manifest JSON](file:///G:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_RC1_MANIFEST.json)

---


## 1. Purpose

As the number of waveguide optimization passes grows (loop compaction, scoreboard scheduling, branch predication, and memory alias analysis), managing their configuration and dependencies manually becomes error-prone. 
The Pass Manager Bridge coordinates these passes in a strict, canonical order. Named Optimization Profiles allow developers and operators to specify coarse-grained performance/correctness profiles that map deterministically to individual pass config flags.

---

## 2. Available Profiles

The following named profiles are officially supported:

- **`RAW_STRICT`**: All optimizations disabled. Simulates raw sequential instruction stepping.
- **`SAFE_LOCAL`**: Pipeline compaction (e.g., multiplication and division loop folding) enabled; scheduling, predication, and memory alias analysis disabled.
- **`SAFE_CONTROL`**: Branch-diamond predication, pipeline compaction, and scoreboard scheduling enabled. Memory alias analysis is disabled.
- **`SAFE_MEMORY`**: Memory alias analysis and scoreboard scheduling enabled. The scheduler uses proven `NO_ALIAS` ranges to parallelize memory operations. Branch predication is disabled.
- **`FULL_SAFE_OPTIMIZED`**: All optimizations (compaction, scheduling, predication, and memory alias analysis) enabled.
- **`BENCHMARK_MATRIX`**: Similar to `FULL_SAFE_OPTIMIZED`, used for running performance diagnostics.
- **`DEBUG_TRACE_AUDIT`**: Similar to `FULL_SAFE_OPTIMIZED`, but configures trace replay metadata to be maximally verbose.
- **`V1_CANDIDATE_EXPERIMENTAL`**: Enables v1 candidate lowering along with all v0 waveguide optimizations (compaction, scheduling, predication, and memory alias analysis).

---

## 3. Canonical Pass Order

The Pass Manager enforces a strict canonical pass order. Any pipeline that deviates from this order is flagged and rejected with a `ValueError` to prevent invalid dependency graphs (e.g., trying to run the scoreboard scheduler before resolving branch-diamond or compaction offsets):

1. **`program_adaptation`**: Parses and normalizes raw instruction tuples and defines label offsets.
2. **`v1_candidate_lowering`**: Lowers enabled experimental v1 candidate instructions into standard v0 instructions.
3. **`memory_alias_analysis`**: Statically parses memory operands and builds address ranges.
4. **`branch_predication`**: Scans branches and lowers conditional skip/diamond geometries.
5. **`pipeline_compaction`**: Folds sequential shift-add loops.
6. **`scoreboard_scheduling`**: Partition instructions into basic blocks and wavefront batches.
7. **`execution_plan_validation`**: Assures that pass results are internally consistent.
8. **`trace_metadata_preparation`**: Serializes unified pass reports.

---

## 4. Relation to Optimizer Flags

Named profiles resolve to explicit boolean flags inside `WaveguideControlMemoryBridgeConfig`. 

Developers can instantiate the configuration using either the named profile or individual overrides:
```python
from sol_waveguide_control_memory_bridge import WaveguideControlMemoryBridgeConfig

# Using a named profile
config_profile = WaveguideControlMemoryBridgeConfig(
    width=32,
    optimization_profile="FULL_SAFE_OPTIMIZED"
)

# Individual flag overrides remain fully supported for backward compatibility
config_manual = WaveguideControlMemoryBridgeConfig(
    width=32,
    enable_pipeline_compaction=True,
    enable_scoreboard_scheduling=False
)
```

---

## 5. Safety Model

The Pass Manager enforces correctness using the following rules:
- **Dependency Guarding**: Scoreboard scheduling cannot run unless instruction adaptation has run first. If memory scheduling is enabled, it requires memory alias metadata.
- **Speculation Restriction**: Speculating memory stores across branch boundaries remains strictly forbidden.
- **Ambiguity Barriers**: Any dynamic register-indirect memory address or unknown branch diamond forces sequential boundaries, bypassing scheduling optimizations.

---

## 6. Unified Report Schema

Each waveguide program execution returns a `pass_manager_report` containing the following schema:
```json
{
    "profile_id": "FULL_SAFE_OPTIMIZED",
    "passes": [
        {
            "pass_id": "program_adaptation",
            "enabled": true,
            "applied": true,
            "skipped": false,
            "skip_reasons": [],
            "changed_plan": true,
            "metadata_keys": ["labels", "clean_instructions"]
        },
        {
            "pass_id": "memory_alias_analysis",
            "enabled": true,
            "applied": true,
            "skipped": false,
            "skip_reasons": [],
            "changed_plan": false,
            "metadata_keys": ["memory_alias_metadata"]
        }
    ],
    "raw_instruction_count": 5,
    "optimized_plan_units": 7,
    "estimated_raw_cycles": 5,
    "estimated_optimized_cycles": 3,
    "cycle_savings": 2,
    "semantic_equivalence_required": true,
    "trace_replay_required": true
}
```

---

## 7. Trace Replay Integration

The trace replay auditor verifies:
- That the pass order listed in the report is valid.
- That no disabled passes emitted active metadata (e.g., if predication is disabled in the profile, no step can have `predication_metadata`).
- That active metadata keys match the enabled passes.

Validation is performed by calling:
```python
from sol_waveguide_trace_replay import validate_waveguide_trace_metadata

ok, err = validate_waveguide_trace_metadata(
    trace_steps, 
    program_len, 
    width, 
    pass_manager_report
)
```

---

## 8. Benchmark Integration

The Optimization Benchmark Harness maps its legacy mode dictionaries directly to named profiles (`RAW_STRICT`, `SAFE_LOCAL`, `SAFE_CONTROL`, `SAFE_MEMORY`, `FULL_SAFE_OPTIMIZED`). Benchmark matrix reports include the active Profile ID, enabled passes list, and cycle deltas.

---

## 9. Sandbox Caveat

> [!NOTE]
> All pass manager executions, optimizations, and validations run strictly in a simulated sandbox environment. No physical mutation of hardware registers or memory cells occurs.
