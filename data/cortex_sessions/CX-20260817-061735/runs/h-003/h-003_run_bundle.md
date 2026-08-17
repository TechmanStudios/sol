# RUN BUNDLE — h-003 (2026-08-17 06:17)

## Identity
- seriesName: h-003
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
What are the canonical metric outputs for standard injection protocols?

## Invariants
- dt: 0.12
- c_press: 0.1
- damping: 0.2
- rng_seed: 42

## Knobs (independent variables)
- (none — single-condition run)

## Injections
- grail: 50 at step 0

## Protocol
- Steps per condition: 500
- Reps per condition: 1
- Metrics every: 10 steps
- Baseline: fresh

## Results Summary
- Total conditions: 1
- Total reps: 1
- Total steps simulated: 500
- Runtime: 2.43s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.992041 | 0.0883 | 18.3521 | 127 | 0.1424 | 58 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 4 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.67 <= injected=50.00

## Falsifiers
- Output changes between identical runs with same seed (non-determinism)

## Notes
Golden baseline for Phase 3 regression suite. Single rep, high step count, full trace.

## Deviations / Incidents
- (none — automated run)
