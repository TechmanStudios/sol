# self_train package

Role-separated scaffold for SOL self-improvement loops.

- Keep policy mutation bounded and reversible.
- Execute real `sol-core` protocol runs per task.
- Support per-task runtime overrides (`steps`, `reps`, `metrics_every`, `baseline`).
- Score candidate policies on both anchor tasks and broader explore tasks.
- Promote only if gate thresholds pass.
- Persist baseline/candidate per-task diagnostic snapshots under each generation.

Use `../self_train_loop.py` as the CLI entrypoint.

Examples:

- `python tools/sol-evolve/self_train_loop.py --generations 3 --mode fast`
- `python tools/sol-evolve/self_train_loop.py --generations 3 --mode full`
- `python tools/sol-evolve/self_train_loop.py --generations 3 --mode overnight`

GitHub Actions (mobile-friendly trigger):

- Run workflow `.github/workflows/sol-self-train.yml` with `workflow_dispatch` inputs.
- For one-tap mobile launch, run `.github/workflows/sol-self-train-overnight.yml` (no inputs).
- For daytime attended runs, run `.github/workflows/sol-self-train-fast.yml` and pick `chain_depth` (`quick`, `standard`, `extended`, `ultra-extended`).
