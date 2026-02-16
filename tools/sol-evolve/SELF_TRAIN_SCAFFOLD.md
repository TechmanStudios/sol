# SOL Self-Train Scaffold (MVP)

This scaffold adds a minimal, runnable self-improvement loop to `tools/sol-evolve`.

## Module layout

- `self_train/models.py` — shared dataclasses (`Policy`, `TaskSpec`, `Proposal`, `ScoreCard`, `GateDecision`)
- `self_train/runner.py` — runner role (executes real `sol-core` protocols)
- `self_train/judge.py` — scoring role (weighted objective)
- `self_train/teacher.py` — proposal role (bounded knob mutation)
- `self_train/gatekeeper.py` — promotion gate role (anchor + full-task thresholds)
- `self_train/memory_store.py` — per-generation event log (`events.jsonl`)
- `self_train/loop.py` — orchestration for baseline → proposal → scoring → gate
- `self_train/config/tasks.json` — anchor/explore task set
- `self_train/config/self_train_config.json` — runtime config
- `self_train_loop.py` — CLI entrypoint

## Run recipe

From repository root:

```powershell
python tools/sol-evolve/self_train_loop.py --generations 3
```

Mode variants:

```powershell
python tools/sol-evolve/self_train_loop.py --generations 3 --mode fast
python tools/sol-evolve/self_train_loop.py --generations 3 --mode full
python tools/sol-evolve/self_train_loop.py --generations 3 --mode overnight
```

VS Code task:

- `Self-Train: Overnight Mode` in `.vscode/tasks.json`
- `Self-Train: Fast Mode` in `.vscode/tasks.json`
- `Self-Train: Fast Mode (Chains)` in `.vscode/tasks.json`

GitHub mobile/manual trigger:

- Workflow: `.github/workflows/sol-self-train.yml`
- Trigger via `Actions` → `SOL Self-Train` → `Run workflow`
- One-tap preset: `Actions` → `SOL Self-Train Overnight Preset` → `Run workflow` (no inputs required)
- Daytime preset with chain option: `Actions` → `SOL Self-Train Fast Preset` → choose `chain_depth` (`quick`/`standard`/`extended`/`ultra-extended`) → `Run workflow`

Outputs:

- `data/sol_self_train/policy_current.json` — active promoted policy
- `data/sol_self_train/gen_###/events.jsonl` — full generation event stream
- `data/sol_self_train/gen_###/summary.json` — compact decision summary
- `data/sol_self_train/gen_###/diagnostics/baseline_<task_id>.json` — baseline per-task protocol snapshot
- `data/sol_self_train/gen_###/diagnostics/candidate_<task_id>.json` — candidate per-task protocol snapshot

Canonical synchronized root:

- `data/sol_self_train_runs/local-desktop/<mode>/<run_stamp>/...`
- `data/sol_self_train_runs/github-actions/<mode>/<github_run_id>/...`

All self-train workflows commit their run outputs back to the repo, so a local `git pull` brings phone-triggered runs into the same canonical tree.

Consolidate for pipeline handoff:

```powershell
python tools/sol-evolve/self_train_consolidate.py
```

Artifacts:

- `data/sol_self_train_runs/_ledger/self_train_ledger.json`
- `data/sol_self_train_runs/_ledger/self_train_ledger.md`

## Task-level controls

Per task (`self_train/config/tasks.json`), optional fields in `payload`:

- `runtime_overrides`: `steps`, `reps`, `metrics_every`, `baseline`
- `protocol_overrides`: override protocol keys (supports `invariants.<key>` and `knobs.<key>`)
- `policy_overrides`: map policy knobs to explicit protocol targets

## Runtime modes

`--mode` applies predefined runtime override profiles to every task.

- `default`: use task file overrides as-is
- `fast`: all tasks `steps=60, reps=1, metrics_every=10`; anchor tasks `steps=100, reps=1, metrics_every=10`
- `full`: all tasks `steps=220, reps=2, metrics_every=5`; anchor tasks `steps=300, reps=3, metrics_every=5`
- `overnight`: all tasks `steps=500, reps=3, metrics_every=5`; anchor tasks `steps=900, reps=4, metrics_every=5`

## Notes

- This MVP intentionally mutates only policy knobs, not engine code.
- The runner executes real protocol JSONs through `tools/sol-core/auto_run.py` and derives training scores from actual run outputs.
- Policy knobs are applied as protocol overrides (`invariants.<key>` by default, or `knobs.<key>` if that knob is swept).
- Runner snapshots include `effective_protocol`, `summary`, `sanity`, `conditions`, and derived training metrics for diagnostics.
