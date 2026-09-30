name: SOL Auto Mapper
description: Runs repeatable mapping sweeps on the SOL manifold (dashboard), producing raw run bundles + optional organized folders.

Goal:
- Generate lots of *raw*, comparable data about how manifold variables respond as parameters change.
- Keep it reproducible: same baseline → sweep → recorded outputs.
- Defer deeper analysis: store raw, then optionally organize into an "analyze" staging area.

Workflow (recommended):
1. Pick or edit a mapping plan
    - Single sweep: `templates/mapping_plan.example.json` (runs one grid)
    - Master (multiple sweeps, sequential): `templates/master_mapping_plan.example.json`
   - Decide your axes (e.g., damping, pressureC, injectAmount) and replicates.
2. Run the mapping pack in the SOL dashboard
   - Open a SOL dashboard (the manifold UI) in your browser.
   - Paste: `scripts/sol_auto_mapper_pack.js` into the browser console.
    - Load your plan into a JS variable:
       - `plan` (single) → `await solAutoMap.runPlan(plan)`
       - `masterPlan` (master) → `await solAutoMap.runMaster(masterPlan)`
   - The pack downloads files to your default downloads folder:
       - Single:
          - `solAutoMap__<plan>__<iso>__summary.csv`
          - `solAutoMap__<plan>__<iso>__trace.csv`
          - `solAutoMap__<plan>__<iso>__manifest.json`
       - Master (per sweep class + combined MASTER):
          - `solAutoMap__<master>__<iso>__<sweep>__summary.csv`
          - `solAutoMap__<master>__<iso>__<sweep>__trace.csv`
          - `solAutoMap__<master>__<iso>__<sweep>__manifest.json`
          - `solAutoMap__<master>__<iso>__MASTER__summary.csv` (combined)
          - `solAutoMap__<master>__<iso>__MASTER__trace.csv` (combined)
          - `solAutoMap__<master>__<iso>__MASTER__manifest.json` (combined)
3. Organize downloaded artifacts into run-bundle folders (optional)
   - Use: `scripts/organize_sol_auto_map_runs.py`
   - Example:
     - `python scripts/organize_sol_auto_map_runs.py --src "$env:USERPROFILE\Downloads" --dest "solData/auto_map"`

Notes:
- This skill assumes the SOL dashboard exposes physics via `SOLDashboard.state.physics` (or `window.solver`) similarly to existing Phase 3.11 scripts.
- The mapping pack freezes the live UI stepping (sets `dtCap=0`) while it runs, then restores it.
- The mapping pack does NOT drive UI sliders. It writes directly to the physics engine to avoid slider quantization/rounding.
- By default it runs in **strict step mode** (`engine.strictStepParams=true`): if the physics engine cannot be stepped with explicit `(dt, pressC, damping)` parameters, the run fails rather than silently falling back to UI-derived state.
- Sweepable knobs (via each sweep's `grid`):
   - Damping / friction ($\alpha$): `damping` (also accepts `baseDamp` / `damp`)
   - Pressure coefficient (controls $p=\Pi(\rho;\psi)$ in practice): `pressureC` (also accepts `pressC`)
   - Injection source term ($s_\rho$): `injectAmount`
   - Integrator step: `dt`
   - Observation: `durationMs`, `everyMs`
   - Flux measurement class ($j$): `includeBackgroundEdges`
   - Belief slider semantics (dashboard v3_7_2): `beliefBias` in [-1, 1]
     - Applies: `globalBias=bias` and `conductanceGamma=bias*App.config.beliefGammaMax`

- Advanced dashboard-modeled variables (v3_7_2) supported via per-run overrides:
   - Plan/sweep defaults: `appConfigOverrides`, `physicsOverrides`
   - Per grid-point: `appConfig`, `physics`
   - Overrides use dotted paths (e.g., `phaseCfg.omega`, `semanticCfg.decayRate`, `capLaw.enabled`).
   - These are applied after baseline restore and are automatically restored after the run.

References:
- scripts/sol_auto_mapper_pack.js
- scripts/organize_sol_auto_map_runs.py
- templates/mapping_plan.example.json
- templates/smoke_mapping_plan.example.json
- templates/master_mapping_plan.example.json
- templates/smoke_master_mapping_plan.example.json
