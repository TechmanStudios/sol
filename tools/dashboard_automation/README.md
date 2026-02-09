# SOL Dashboard Automation (Firefox Dev Edition)

This folder contains a small runner that lets agents (and you) drive SOL dashboard experiments inside **Firefox Developer Edition**, and ensure experiment CSVs are saved into `solData/testResults/` (not `C:\Users\<you>\Downloads`).

## Why this exists
Firefox (including Dev Edition) does **not** allow in-page JavaScript to choose an arbitrary folder for downloads. The reliable approach is:
- Keep the dashboard exporting results via normal browser downloads (e.g. `<a download>`)
- Configure the **browser profile** used for automated tests so the download directory is `solData/testResults/`

## Prereqs
- Python environment for `sol/`
- `selenium` installed
- Firefox Developer Edition installed

Optional:
- Set env var `FIREFOX_DEV_EXE` to your Dev Edition binary, typically:
  - `C:\Program Files\Firefox Developer Edition\firefox.exe`

## Install Selenium
From `g:\docs\TechmanStudios\sol`:

- `pip install selenium`

Selenium 4+ uses Selenium Manager and will usually fetch/resolve `geckodriver` automatically.

## Run a sweep (interactive)
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev`

Then type:
- `run` to execute one sweep (downloads 2 CSV files)
- `quit`

## Run for a fixed time (hands-off)
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --auto --duration-min 30`

## Agent-friendly mode: command queue (hands-off + interactive via files)
This is the mode that best supports “chat with agents → enqueue runs → browser executes → CSV lands in solData”.

1) Start the runner in watch mode:
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --watch-commands`

This watches:
- `solData/testResults/command_queue/` for `*.json`

And writes:
- CSV downloads to `solData/testResults/`
- Processed commands to `solData/testResults/command_done/`
- Results JSON to `solData/testResults/command_results/`

2) Enqueue a command JSON (from another terminal, or an agent):
- `python tools/dashboard_automation/enqueue_command.py --runs 3 --out-prefix sol_mechSweep --params-json "{\"steps\":2000}"`

Quick smoke test (fast, single dt/damp) to verify end-to-end wiring:
- `python tools/dashboard_automation/enqueue_command.py --preset smoke --out-prefix smoke_001`

Automation smoke (no downloads): verify dashboard boot + physics readiness.
- Enqueue:
  - `python tools/dashboard_automation/enqueue_smoke_command.py --name smoke_boot_001 --steps 5`
- Run one-shot (headless recommended):
  - `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --headless --command-file solData\\testResults\\command_queue\\smoke_boot_001.json`

Notes:
- Command kind: `sol.dashboard.smoke.v1`
- Produces no CSV/JSON downloads; results are written to `solData/testResults/command_results/` by the runner.

Optional dashboard knob overrides (applied to `SOLDashboard.config` before the sweep):
- `python tools/dashboard_automation/enqueue_command.py --preset smoke --out-prefix smoke_capOff --dashboard-config-json "{\"capLaw\":{\"enabled\":false}}"`

### One-shot (no watcher)
If you want to run exactly one command file without keeping a watcher process open:
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --command-file solData/testResults/command_queue/your_command.json`

## SOL Auto Mapper (plan runner)
This runner also supports executing SOL Auto Mapper plans (downloads 3 artifacts: summary.csv, trace.csv, manifest.json).

Enqueue an auto-map command:
- `python tools/dashboard_automation/enqueue_auto_map_command.py --plan-json "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\templates\\smoke_mapping_plan.example.json" --pack-path "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\scripts\\sol_auto_mapper_pack.js" --name autoMap_smoke_001`

Or use the built-in smoke preset:
- `python tools/dashboard_automation/enqueue_auto_map_command.py --preset smoke --pack-path "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\scripts\\sol_auto_mapper_pack.js" --name autoMap_smoke_001`

Run it one-shot (headless recommended):
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --headless --command-file solData/testResults/command_queue/autoMap_smoke_001.json`

Notes:
- The command kind is `sol.dashboard.auto_map.v1`.
- The pack path can be provided either in the command JSON (`packPath`) or via `run_dashboard_sweep.py --auto-map-pack`.

### Master plans (multiple sweeps + combined MASTER)
If you want the sequential multi-sweep master run (`solAutoMap.runMaster(masterPlan)`), use:
- `python tools/dashboard_automation/enqueue_auto_map_master_command.py --master-plan-json "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\templates\\master_mapping_plan.v2.json" --pack-path "g:\\aiAgents\\.github\\skills\\sol-auto-mapper\\scripts\\sol_auto_mapper_pack.js" --name autoMap_master_v2_overnight --timeout-s 25200`

Then run headless:
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --headless --command-file solData/testResults/command_queue/autoMap_master_v2_overnight.json`

Notes:
- The command kind is `sol.dashboard.auto_map_master.v1`.
- This will download 3 files per sweep plus 3 combined MASTER files (so expect many downloads).

## Note: automation mode
The runner loads the dashboard with `?automation=1`, which disables visualization and the live `requestAnimationFrame` loop to prevent Firefox script timeouts during long runs.

In automation mode, the dashboard is intended to be offline-friendly (no visualization dependencies required).

### Command file format
Minimal example:
```json
{
  "kind": "sol.dashboard.sweep.v1",
  "dashboard": "sol_dashboard_v3_7_2.html",
  "outPrefix": "sol_mechSweep",
  "runs": 1,
  "timeoutS": 600,
  "params": {"steps": 2000}
}
```

Optional: override dashboard `App.config` values before the sweep runs:
```json
{
  "kind": "sol.dashboard.sweep.v1",
  "dashboard": "sol_dashboard_v3_7_2.html",
  "outPrefix": "sol_cfgSweep",
  "runs": 1,
  "timeoutS": 900,
  "dashboardConfig": {
    "capLaw": {"enabled": true, "alpha": 0.9},
    "experiments": {"battery": {"leakLambda": 0.12}}
  },
  "params": {"steps": 4000}
}
```

## Change which dashboard loads
- `python tools/dashboard_automation/run_dashboard_sweep.py --dashboard sol_dashboard_v3_7_2.html --firefox-dev`

## Override sweep params
The runner injects and calls `solEngine/mechanismTraceSweep_v1.js` (`window.solMechanismTraceSweepV1`).

You can pass JSON overrides (merged into the sweep params passed to `run()` or `mechanismTraceSweep()`):
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --auto --params-json "{\"steps\":2000,\"outPrefix\":\"myRun\"}"`

## Omnibus sweep batch generator
To generate a staged long-form “omnibus” batch (Phase A/B/C/D templates) based on the canonical dashboard and the math foundation PDF:

- `python tools/dashboard_automation/generate_omnibus_commands.py`

Phase C is now expanded into AB/BA counterbalanced interaction probes (guardrail × bleed) so you can sanity-check order effects.
If you want to generate only certain phases (and keep Phase C early even with small `--limit`), use:

- `python tools/dashboard_automation/generate_omnibus_commands.py --phases A,C,D --limit 25`

This writes commands into a timestamped staging folder under `solData/testResults/omnibus_batches/`.
If you want to enqueue directly into the live queue (use with care if the watcher is running):

- `python tools/dashboard_automation/generate_omnibus_commands.py --enqueue`

## Cognitive load sweep batch ("load → infinity")
To probe what happens as a cognitive-load proxy scales upward, generate a staged batch that sweeps a “multi-agent write load” knob.

Operationalization (matches the “many fast AIs writing into the semantic manifold” picture):
- Treat each AI as a writer that injects density (ρ) into some target concept node.
- Treat speed as pulse frequency (`pulseEvery` steps between pulses).
- Treat concurrency as `targetsPerPulse` (how many distinct target nodes get injected per pulse).

A useful scalar summary is an approximate injection rate:
- `approxInjectRate ≈ injectAmount * targetsPerPulse / pulseEvery`

As this increases, we expect regime changes (e.g., saturation/no-contrast, runaway pressure, basin lock-in). The analyzer aggregates those.

### Scenario presets ("what are agents?")
Use `--scenario` to run several generalized interpretations without committing yet:
- `distributed` (default): multiple targets, up to `targetsPerPulse` writers each pulse.
- `concentrated`: all writes go to `--target-id` (many processes hammer one concept).
- `roaming`: one write per pulse, cycling through `--agent-target-ids` (single attention cursor moving fast).
- `burstAll`: all agents write every pulse (`targetsPerPulse = agentCount`).

1) Generate a staged batch folder:
- `python tools/dashboard_automation/generate_cognitive_load_commands.py`

Optional tuning (examples):
- Sweep injection magnitude (single-agent-style):
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --load-knob injectAmount --inject-start 1 --inject-factor 2 --inject-max 4096 --max-terms 13`

- Sweep agent count (more simultaneous writers):
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --load-knob agentCount --agent-target-ids "64,82,79,12,13,14" --agent-max 6`

- Sweep pulse frequency (faster writes; smaller `pulseEvery` => higher load):
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --load-knob pulseEvery --pulse-every-start 64 --pulse-every-factor 0.5 --pulse-every-min 1`

- Sweep damping (change resonance/stability while holding injection fixed):
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --load-knob damping --damping 4 --damping-sweep-start 1 --damping-sweep-factor 2 --damping-sweep-max 16`

- Compare mappings quickly (same sweep, different scenarios):
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --scenario concentrated --load-knob pulseEvery --pulse-every-start 64 --pulse-every-factor 0.5 --pulse-every-min 1 --target-id 64`
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --scenario roaming --load-knob pulseEvery --pulse-every-start 64 --pulse-every-factor 0.5 --pulse-every-min 1 --agent-target-ids "64,82,79" --agent-count 3`
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --scenario distributed --load-knob pulseEvery --pulse-every-start 64 --pulse-every-factor 0.5 --pulse-every-min 1 --agent-target-ids "64,82,79" --agent-count 3 --targets-per-pulse 2`

- Baseline run shape:
  - `python tools/dashboard_automation/generate_cognitive_load_commands.py --steps 6000 --damping 4 --dt 0.12 --press-slider 200`


2) Run the batch (single Firefox session):
The generator prints the exact `run_dashboard_sweep.py` command to use, including `--run-command-dir`, `--command-done-dir`, and `--command-results-dir`.

3) Analyze:
- `python tools/dashboard_automation/analyze_cognitive_load_sweep.py --batch-dir <batch_folder>`

This writes:
- `<batch_folder>/cognitive_load_readout.csv`
- `<batch_folder>/cognitive_load_readout.md`

4) Compare multiple batches (combined table + plot):
- `python tools/dashboard_automation/analyze_cognitive_load_compare.py --batch-dirs <batch_folder_1> <batch_folder_2> <batch_folder_3> --out-dir <output_folder>`

Optional controller tuning (objective C):
- `--c-bandwidth-tol 0.02` (default) treats bandwidths within 2% as equivalent and then prefers lower spike/stress (`peakPMax`, `peakMeanP`) when picking C damping setpoints.
- `--include-pure-c` adds a second controller column (C0) that uses bandwidth-at-all-cost (`tol=0.0`) so you can compare spike-aware C vs pure bandwidth C in one report.

This writes to `<output_folder>`:
- `cognitive_load_compare.csv`
- `cognitive_load_compare.md`
- `cognitive_load_compare_minFailStep.svg`
- `cognitive_load_compare_peakPMax.svg`
- `cognitive_load_compare_peakMeanP.svg`
- `cognitive_load_compare_rhoEffN.svg`
- `cognitive_load_compare_peakRhoSum.svg`

Tip: if you omit `--out-dir`, the script will create a timestamped folder under `solData/testResults/cognitive_load_compare/`.

## Adaptive cognitive-load loop (branching + multi-objective)
If you want the tooling to *propose the next tests* automatically (while keeping a full audit trail), use:

- `python tools/dashboard_automation/adaptive_cognitive_load_loop.py --include-compare --include-pure-c`

This creates a timestamped folder under `solData/testResults/adaptive_cognitive_load/` with:
- `iter_XX/` folders (each iteration)
- `journal.json` (the decision trail: chosen windows, reasons, compare links)

Key features:
- **Branching**: multiple damping windows explored in parallel (default `--branches 3` with `--branch-modes budget,spike,spread`).
- **Multi-objective bracketing**: the next window can target budget crossings *and* sharp changes in spikes/stress/spread.
- **Occasional widening**: periodically expands an exploratory branch to avoid collapsing too narrowly.
- **Headless runner**: the loop always invokes the dashboard runner with `--headless` for faster unattended runs.

## Manual (no automation)
If you’re running experiments by hand in Firefox Dev Edition, set:
- **Settings → General → Files and Applications → Downloads → Save files to:**
  - `g:\docs\TechmanStudios\sol\solData\testResults`

That ensures exported CSVs land where SOL agents can pick them up.

## Agent runbook
For a protocol-minded checklist (baseline control, AB/BA, long-form sweep phases, labeling rules), see:
- `.github/prompts/dashboard-runner-runbook.md`
