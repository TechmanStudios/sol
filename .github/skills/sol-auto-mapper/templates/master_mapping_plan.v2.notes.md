# Master Mapping Plan v2 (Design Notes)

This file explains the intent and sizing of master_mapping_plan.v2.json.

## Goal

Produce a *coarse but broad* raw dataset for ridge/band discovery across the core SOL manifold axes, while also sampling a small set of dashboard-modeled knobs that were identified in v3_7_2.

This is not the “final master atlas.” It is the first pass that should be:
- numerically faithful (strict physics stepping, no slider quantization)
- large enough to show stable ridge/band structure
- small enough to run in ~1–2 hours on a single headless session

Update (v2 tuned for overnight): this revision targets ~6 hours and prioritizes
replicates (variance estimates) and 2D ridge/band resolution over longer windows.

## Defaults (why)

- durationMs=20000 is a coarse mapping window: long enough for early regime separation, short enough to keep run time bounded.
- replicates=3 by default: ridge discovery benefits from variance estimates more than longer windows.
- basins=[64,79,82,90]: representative injection targets; adjust based on which nodes/basins you consider canonical.

Sampling resolution:
- everyMs=250 reduces trace bloat while still capturing regime dynamics.

## What durationMs means (runner semantics)

In `scripts/sol_auto_mapper_pack.js`, each run does:

- `tickCount = floor(durationMs / everyMs)`
- For each tick: wait (wall-clock) until the next `everyMs` deadline, then call `physics.step(dt, pressC, damping)` once and record a sample.

So `durationMs` controls both:
- the *wall-clock observation window*, and
- the *number of physics steps* per run (roughly `durationMs / everyMs`).

## Suggested presets

These are intended as “copy/paste” overrides for `defaults` when you want faster daytime mapping vs slower overnight mapping.

### Preset: Tight (daytime / coarse ridge discovery)

- replicates: 2
- measurement: `durationMs=20000`, `everyMs=200`, `dt=0.12`
- timing: `timingMode="tight"`, `spinWaitMs=2.0`

Why: ~100 samples/run; good signal at low cost.

### Preset: Safe overnight (slower, more separation)

- replicates: 3
- measurement: `durationMs=60000`, `everyMs=200`, `dt=0.12`
- timing: `timingMode="relaxed"` (reduces CPU busy-wait overnight)

Why: ~300 samples/run and higher replication; better for late-onset divergence and stabilizing boundary rankings.

## Sweep classes

Core axes (high priority):
- dt
- durationMs
- includeBackgroundEdges

Ridge/band discovery (high priority):
- pressureC x damping (2D scan)
- injectAmount x damping (2D scan)

Note: even though the 1D curves can be reconstructed by slicing the 2D surfaces, we still include
explicit 1D sweeps (core_damping/core_pressureC/core_injectAmount) as a simpler baseline readout.

Modeled knobs (smaller, bounded):
- beliefBias (globalBias + conductanceGamma semantics)
- psi dynamics (psiDiffusion / psiRelaxBase)
- phase gating (phaseCfg.*)
- semantic mass decay (semanticCfg.decayRate)

## Run-count sizing (back-of-envelope)

Total runs per sweep = |gridPoints| × |basins| × replicates.

Ridge scans (rep=3, basins=4):
- ridge_scan_pressC_x_damping: 49×4×3 = 588
- ridge_scan_injectAmount_x_damping: 42×4×3 = 504

Core 1D sweeps (rep=3, basins=4):
- core_damping: 7×4×3 = 84
- core_pressureC: 6×4×3 = 72
- core_injectAmount: 5×4×3 = 60

Support sweeps (replicates reduced, basins reduced):
- core_dt (basins=2, rep=2): 3×2×2 = 12
- core_duration (basins=2, rep=1): 3×2×1 = 6
- core_flux_class (basins=2, rep=1): 2×2×1 = 4
- modeled_beliefBias (basins=2, rep=1): 5×2×1 = 10

Modeled knobs (rep=1, basins reduced to 2):
- modeled_psi: 3×2×1 = 6
- modeled_phase: 3×2×1 = 6
- modeled_semanticDecay: 3×2×1 = 6

Estimated total runs: 1368.
At 20s each (coarse window), that's ~7.6 hours wall-clock plus overhead.

## Suggested next step after review

After you inspect the master plan, the next iteration is usually:
1) run v2 once to find ridge/band regions
2) add a follow-up plan that densifies the grid only near discovered transition bands
3) add AB/BA counterbalance sweeps for the most sensitive axes to rule out order/history confounds
