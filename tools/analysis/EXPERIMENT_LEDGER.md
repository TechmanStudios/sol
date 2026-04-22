# Experiment Ledger Engine (v1)

This engine builds a generalized ledger index across experiments using a normalized schema.

## Current adapters

- `self_train` (from `data/sol_self_train_runs`)
- `resonance` (from `data/thinking_engine_resonance` + `data/thinking_engine_resonance_phase2`)
- `rsi` (from `data/rsi` ledger streams)
- `cortex` (from `data/cortex_sessions`)
- `dream` (from `data/dream_sessions/DS-*`, see "Dream-specific outputs" below)

## Outputs

- `data/experiment_ledger/records.jsonl` — normalized record stream
- `data/experiment_ledger/index.json` — aggregate index for pipeline consumers
- `data/experiment_ledger/ledger.md` — human-readable summary
- `data/experiment_ledger/dream_findings.json` — cross-night dream findings (machine readable)
- `data/experiment_ledger/dream_ledger.md` — compact human-readable nightly dream report

Promoted dream findings are also written into solKnowledge:

- `solKnowledge/working/dream_findings_candidates.md` — single-night anomalies / follow-up candidates
- `solKnowledge/consolidated/dream_findings.md` — findings stable across multiple nights or source cortex sessions (proof-packet candidates)

## Dream-specific outputs

The dream adapter ingests each `data/dream_sessions/DS-*/` folder
(`summary.json`, `dream_log.jsonl`, `basin_signatures.json`) and emits one
`ExperimentRecord` per session. Records are tagged with dream-specific
emergence signals (`new_basin_discovered`, `basin_reinforced`,
`reinforcement_dominant`, `stable_basin_present`, `dominant_rho_persistent`,
`cross_source_basin_transfer`, `high_replay_yield`) and unknown-mechanics
flags (`decay_dominant`, `no_basins_observed`, `top_node_set_drift`,
`entropy_band_drift`).

A separate cross-night aggregator produces `DreamFinding` rows in seven
finding classes prioritized for transfer-oriented hypotheses:

1. `recurring_basin` — the same basin `mass_hash` recurring across nights / source sessions.
2. `recurring_source` — source cortex sessions that keep reappearing in nightly replays.
3. `replay_yield_correlation` — Pearson correlation between mean replay score and stable-basin share.
4. `reinforcement_decay_balance` — discovered + reinforced vs decayed basins across nights.
5. `top_node_set_persistence` — top-node tuples recurring across nights.
6. `entropy_band_persistence` — entropy bands present on multiple nights.
7. `basin_turnover` — nights where the dominant basin shifted vs the previous night.

Findings are flagged `is_stable` when they recur across multiple nights or
multiple source sessions, and `promote_to_canonical` only when they additionally
clear a stricter multi-night threshold. Single-night anomalies stay as
follow-up candidates rather than canonical claims.

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
	--cortex-root data/cortex_sessions \
	--dream-root data/dream_sessions \
	--solknowledge-root solKnowledge
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
