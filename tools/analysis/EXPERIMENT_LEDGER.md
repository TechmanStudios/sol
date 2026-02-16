# Experiment Ledger Engine (v1)

This engine builds a generalized ledger index across experiments using a normalized schema.

## Current adapters

- `self_train` (from `data/sol_self_train_runs`)

## Outputs

- `data/experiment_ledger/records.jsonl` — normalized record stream
- `data/experiment_ledger/index.json` — aggregate index for pipeline consumers
- `data/experiment_ledger/ledger.md` — human-readable summary

## Run

```powershell
python tools/analysis/experiment_ledger.py
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
