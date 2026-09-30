---
name: SOL Dashboard Runner Runbook
description: Run interactive + hands-off + command-queue dashboard experiments in Firefox Dev Edition, with CSV results written into solData/testResults for agent ingestion.
---

# SOL Dashboard Runner Runbook (Agents + Humans)

## Scope
This runbook covers running JavaScript experiments in the SOL dashboard (Firefox Developer Edition) using:
- interactive CLI mode
- hands-off timed mode
- command-queue mode (agent-friendly)

It is designed to:
- preserve baseline control (avoid accidental drift)
- produce reproducible sweeps
- write all CSV outputs into `solData/testResults/`
- emit machine-readable run metadata for downstream agents (data analyst / lab master / knowledge compiler)

Agent routing note:
- If you want to intentionally route work to a specific agent (or understand how I’ll choose by default), see `sol-agent-routing-soft-triggers.md`.

## Required invariants (declare every time)
When you run comparisons or sweeps, always declare the invariants you are holding fixed:
- dashboard file (e.g. `sol_dashboard_v3_7_2.html`)
- sweep script version (`solEngine/mechanismTraceSweep_v1.js` → `window.solMechanismTraceSweepV1.version` in console)
- baseline mode (restore vs hard reset) and restore frequency
- time budget + number of reps
- download directory (must be `solData/testResults/`)

Baseline control requirement:
- If comparing conditions, baseline handling must match across conditions.

## Where outputs go
All exports should land under:
- `solData/testResults/` (CSV files)
- `solData/testResults/command_results/` (results JSON)
- `solData/testResults/command_done/` (archived command JSON)

## Runner entrypoints
Runner (Selenium + Firefox profile download-dir override):
- `tools/dashboard_automation/run_dashboard_sweep.py`

Command enqueue helper:
- `tools/dashboard_automation/enqueue_command.py`

## Modes

### 1) Interactive mode (manual approval loop)
Use when you want a tight chat loop:
- “try this knob” → “go” → run 1 sweep → inspect output → adjust

Command:
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev`

Terminal commands supported:
- `run` → executes one sweep and downloads two CSVs
- `quit`

### 2) Hands-off timed mode (fire-and-forget)
Use when you already know the sweep parameters and want continuous sampling:

Command:
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --auto --duration-min 240`

Rules:
- Choose an `--out-prefix` that is unique to the experiment question.
- Prefer smaller individual runs repeated many times rather than one giant run (easier to diagnose and resume).

### 3) Command-queue mode (agent-friendly)
Use when an agent (or you) should be able to schedule runs without interacting with a live terminal.

Start watcher:
- `python tools/dashboard_automation/run_dashboard_sweep.py --firefox-dev --watch-commands`

Enqueue commands:
- `python tools/dashboard_automation/enqueue_command.py --runs 3 --out-prefix sol_mechSweep --params-json "{\"steps\":2000}"`

Contract:
- drop `*.json` into `solData/testResults/command_queue/`
- watcher processes oldest-first
- watcher writes a `*_result_*.json` into `command_results/`

## Command file schema
Kind:
- `sol.dashboard.sweep.v1`

Example:
```json
{
  "kind": "sol.dashboard.sweep.v1",
   "dashboard": "sol_dashboard_v3_7_2.html",
  "outPrefix": "sol_mechSweep",
  "runs": 5,
  "timeoutS": 900,
  "params": {
    "steps": 2000,
    "dt": 0.01,
    "mode": "logic"
  }
}
```

Notes:
- `params` is passed through to `window.solMechanismTraceSweepV1.run(params)`.
- Use `runs` to repeat the same condition N times (replicates).

## Protocol design guidance (for long-form sweeps)
Long sweeps should be treated as protocol work, not “just run everything”.

### Step 0 — define the question
Write a one-sentence question.
Examples:
- “Which knobs shift the system into a new basin?”
- “Which knobs control time-to-emergence under fixed baseline?”

### Step 1 — choose sweep type
Pick one:
1) **Single-knob ridge scan** (recommended default)
   - vary one knob across a range
   - hold everything else invariant
2) **Control surface map** (expensive)
   - vary two knobs across a grid
   - explicitly label as a surface map
3) **Exploratory omnibus sweep** (very expensive)
   - use for discovery only
   - follow-up with focused ridge scans

### Step 2 — baseline control
Declare one baseline strategy and keep it consistent:
- restore baseline every run (strong comparability)
- hard reset between runs (cold start control)

If you change baseline strategy, treat it as a knob.

### Step 3 — order control (AB/BA)
If you suspect history effects:
- run AB then BA with matched dwell time and identical invariants

### Step 4 — sweep phases (hours-to-day runs)
For “general sweeps overview of every variable”, use phases:

**Phase A: Inventory + bounds (quick)**
- list candidate knobs
- pick plausible bounds and step sizes
- run 1–3 reps per bound to validate runtime and stability

**Phase B: Coarse scan (discovery)**
- coarse step sizes across wide ranges
- log potential transitions (spikes, regime changes, new attractors)

**Phase C: Bracketing (precision)**
- tighten around boundaries where transitions appear
- increase reps

**Phase D: Stability + replication (promotion-ready)**
- repeat best candidates across sessions / fresh starts
- confirm order independence or quantify history effects

## Labeling rules (so agents can find things later)
Use a consistent `outPrefix` pattern:
- `{study}_{dashboard}_{date}_{tag}`

Examples:
- `ridge_dt_v3_20260124_A`
- `surface_dtXdamp_v3_20260124_coarse`

Also ensure the command JSON includes:
- dashboard
- params (full)
- runs
- timeoutS

## Operational tips for day-long runs
- Prefer command-queue mode so you can schedule additional runs while the browser is busy.
- Keep per-run outputs bounded (avoid single giant traces).
- If a run fails or times out, preserve the failed command JSON; enqueue a reduced version to isolate the issue.

## Hand-off to analysis / knowledge agents
After runs complete:
- Data analyst reads CSVs in `solData/testResults/` and writes summary tables.
- Lab master compiles a run bundle using `.github/prompts/run-bundle-template.md`.
- Knowledge compiler only promotes claims that can be traced to the CSV outputs + protocol declarations.
