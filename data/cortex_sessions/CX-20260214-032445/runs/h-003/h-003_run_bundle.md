# RUN BUNDLE — h-003 (2026-02-13 22:25)

## Identity
- seriesName: h-003
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
Can headless sol-core reproduce: ?

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
- Steps per condition: 300
- Reps per condition: 5
- Metrics every: 5 steps
- Baseline: fresh

## Results Summary
- Total conditions: 1
- Total reps: 5
- Total steps simulated: 1500
- Runtime: 5.66s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 4 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.79 <= injected=50.00

## Falsifiers
- Headless results qualitatively differ from dashboard results
- Metrics trend in opposite direction from original claim

## Notes
Replicating unknown

## Deviations / Incidents
- (none — automated run)
