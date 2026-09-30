# Scale-Ready Checklist (Future High-Parallel Runs)

Use this tiny checklist before any high-parallel/GPU-class run so results remain comparable with current constrained-hardware baselines.

## When to apply
- Planning multi-GPU or high-concurrency sweeps
- Upgrading model/provider infra for many simultaneous advisor calls
- Migrating the same protocol to faster hardware

## Checklist (must-pass)
1. **Baseline lock**
   - Keep protocol knobs aligned with baseline or explicitly mark deltas.
   - Record script commit hash and baseline run IDs used for comparison.
2. **Comparability contract**
   - Preserve core metrics: emergence hit-rate, sweeps-to-first-emergence, best boundary strength, advisor success/applied/fallback, latency summary.
   - Preserve naming/export schema; if changed, publish a field-mapping table.
3. **Parallel execution manifest**
   - Record concurrency: worker count, GPU/CPU class, provider/model route, max in-flight advisor calls.
   - Record throttling/rate-limit settings and retry/fallback policy.
4. **Determinism controls**
   - Track seed strategy (fixed/rotating), sweep ordering policy, and shuffle policy.
   - Declare anything intentionally nondeterministic.
5. **Cost + reliability envelope**
   - Capture cost per run family and advisor error/timeout rates.
   - Define abort thresholds for provider instability.
6. **Promotion gate**
   - Only claim speedup if median improvement is shown across matched budgets and seeds.

## Minimal manifest stub
```json
{
  "run_family": "phonon_micro_rsi_parallel_v1",
  "baseline_reference": ["20260214-211730"],
  "script_commit": "<git-sha>",
  "compute": {
    "gpu_class": "<value>",
    "workers": 0,
    "max_inflight_advisor_calls": 0
  },
  "provider": {
    "route": "<model-route>",
    "retry_policy": "<policy>",
    "fallback_enabled": true
  },
  "comparability": {
    "matched_seed_budget": true,
    "matched_sweep_budget": true,
    "schema_changes": []
  }
}
```

## Agent handoff note
When routing to `sol-experiment-runner`, `sol-data-analyst`, or `sol-knowledge-compiler`, include: “Apply `.github/prompts/scale-ready-checklist.prompt.md` first.”