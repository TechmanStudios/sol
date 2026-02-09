# SOL Auto Mapper - Master Sweep Plan (Draft v2)

This is the proposed "master sweep" for SOL dashboard v3_7_2 using the SOL Auto Mapper pack.

## Canonical plan file

- Plan JSON: g:\aiAgents\.github\skills\sol-auto-mapper\templates\master_mapping_plan.v2.json
- Design notes: g:\aiAgents\.github\skills\sol-auto-mapper\templates\master_mapping_plan.v2.notes.md

## What this master sweep tries to accomplish

- Cover the core manifold axes (damping, pressureC, injection, dt, window length, flux-class).
- Include a bounded sample of additional modeled knobs found in dashboard v3_7_2 (belief bias, psi, phase, semantic decay).
- Keep default collection *coarse* so we can discover ridge/band structure before densifying.

## Key defaults (for review)

- basins: [64, 79, 82, 90]
- replicates: 3 (ridge sweeps)
- durationMs: 20000 (20s)
- everyMs: 250
- dt: 0.12
- strict stepping: true (physics.step(dt, pressC, damping) required)

Sizing target:
- Total runtime is tuned for an overnight run (roughly ~8 hours at 20s per run, plus overhead).
- Strategy: increase replicates and 2D resolution before increasing duration.

## Sweep classes (in order)

Core:
- core_damping
- core_pressureC
- core_injectAmount
- core_dt
- core_duration
- core_flux_class

Modeled knobs (bounded):
- modeled_beliefBias
- modeled_psi
- modeled_phase
- modeled_semanticDecay

Ridge/band discovery (2D scans):
- ridge_scan_pressC_x_damping
- ridge_scan_injectAmount_x_damping

## What I need from you

- Confirm the basin IDs you want as defaults.
- Confirm the default window length (20s) is acceptable for coarse ridge discovery.
- Decide whether modeled knobs belong in v2 or should move to v3.

Once you confirm, we can run this headless and then stage the raw bundles + candidate packet(s).
