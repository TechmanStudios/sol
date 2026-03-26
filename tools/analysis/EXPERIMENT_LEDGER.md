# Experiment Ledger Engine (v1)

This engine builds a generalized ledger index across experiments using a normalized schema.

## Current adapters

- `self_train` (from `data/sol_self_train_runs`)
- `resonance` (from `data/thinking_engine_resonance` + `data/thinking_engine_resonance_phase2`)
- `rsi` (from `data/rsi` ledger streams)
- `cortex` (from `data/cortex_sessions`)

## Outputs

- `data/experiment_ledger/records.jsonl` — normalized record stream
- `data/experiment_ledger/index.json` — aggregate index for pipeline consumers
- `data/experiment_ledger/ledger.md` — human-readable summary

Record annotations also summarize:

- `knowledge_domains` — manifold/domain tags inferred from experiment content
- `potential_emergence` — heuristic emergence signals worth follow-up
- `unknown_mechanics` — unresolved mechanics/open-question flags

## Local-only generated data

These run-output folders are intentionally local-only (git-ignored) and should not be committed:

- `data/sol_self_train/`
- `data/sol_self_train_fast_task_launch_smoke/`
- `data/sol_self_train_mode_fast_smoke/`
- `data/sol_self_train_mode_full_smoke/`
- `data/sol_self_train_mode_overnight_smoke/`
- `data/sol_self_train_phase2_smoke/`
- `data/sol_self_train_real_smoke/`
- `data/sol_self_train_runs/`
- `data/sol_self_train_smoke/`
- `data/sol_self_train_task_launch_smoke/`

## Run

```powershell
python tools/analysis/experiment_ledger.py
```

Optional roots:

```powershell
python tools/analysis/experiment_ledger.py \
	--self-train-root data/sol_self_train_runs \
	--resonance-phase1-root data/thinking_engine_resonance \
	--resonance-phase2-root data/thinking_engine_resonance_phase2 \
	--rsi-root data/rsi \
	--cortex-root data/cortex_sessions
```

## Schema (record)

- `experiment`
- `source`
- `mode`
- `run_id`
- `generation`
- `accepted`
- `metrics` (experiment-specific numeric deltas/scores)
- `reason`
- `summary_path`

## Extension pattern

Add additional adapters that emit `ExperimentRecord` rows, then include them in index aggregation.
