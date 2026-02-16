# self_train package

Role-separated scaffold for SOL self-improvement loops.

- Keep policy mutation bounded and reversible.
- Execute real `sol-core` protocol runs per task.
- Support per-task runtime overrides (`steps`, `reps`, `metrics_every`, `baseline`).
- Score candidate policies on both anchor tasks and broader explore tasks.
- Promote only if gate thresholds pass.
- Persist baseline/candidate per-task diagnostic snapshots under each generation.

Use `../self_train_loop.py` as the CLI entrypoint.
Canonical cross-device launcher: `../self_train_run.py`

Examples:

- `python tools/sol-evolve/self_train_loop.py --generations 3 --mode fast`
- `python tools/sol-evolve/self_train_loop.py --generations 3 --mode full`
- `python tools/sol-evolve/self_train_loop.py --generations 3 --mode overnight`

GitHub Actions (mobile-friendly trigger):

- Run workflow `.github/workflows/sol-self-train.yml` with `workflow_dispatch` inputs.
- For one-tap mobile launch, run `.github/workflows/sol-self-train-overnight.yml` (no inputs).
- For daytime attended runs, run `.github/workflows/sol-self-train-fast.yml` and pick `chain_depth` (`quick`, `standard`, `extended`, `ultra-extended`).
- For generalized source tagging, workflows include `run_source` (`phone` / `desktop`) in artifact names.

Synchronization model:

- Local and GitHub runs are written under `data/sol_self_train_runs/<source>/<mode>/<run_id_or_stamp>/`.
- Workflow runs auto-commit outputs to repo so `git pull` syncs phone-triggered experiments locally.
- GitHub artifacts can also be pulled directly into local data roots with:
	- `python tools/analysis/sync_github_artifacts.py`
	- This archives all matching SOL workflow artifacts under `data/pipeline_runs/github_actions_artifacts/`.
	- For `self-train-*` artifacts, it also ingests runs to canonical paths under `data/sol_self_train_runs/github-actions/<mode>/<run_id>/`.
	- To activate only for phone-triggered runs, use:
		- `python tools/analysis/sync_github_artifacts.py --required-run-source phone`
	- Use watch mode for auto-sync while VS Code is open:
		- `python tools/analysis/sync_github_artifacts.py --watch --interval-sec 600 --required-run-source phone`
	- Watch mode can be stopped cleanly by creating stop flag file:
		- `data/pipeline_runs/github_artifact_sync.stop`
	- The watcher can clear stale stop flags on startup via:
		- `--clear-stop-flag`

Consolidation:

- `python tools/sol-evolve/self_train_consolidate.py`
- Outputs ledger files in `data/sol_self_train_runs/_ledger/` for promotion/pipeline review.
- `python tools/analysis/experiment_ledger.py`
- Outputs generalized artifacts in `data/experiment_ledger/` for cross-experiment indexing (`self_train` + `resonance` adapters currently).

Workflow behavior:

- Self-train workflows auto-update both ledgers before committing outputs.
