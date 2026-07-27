# RUN BUNDLE — h-003 (2026-07-27 07:22)

## Identity
- seriesName: h-003
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
How does damping affect entropy, flux, and mass over 200 steps?

## Invariants
- dt: 0.12
- c_press: 0.1
- rng_seed: 42

## Knobs (independent variables)
- damping: [0.05, 0.1, 0.2, 0.5]

## Injections
- grail: 50 at step 0

## Protocol
- Steps per condition: 200
- Reps per condition: 3
- Metrics every: 5 steps
- Baseline: fresh

## Results Summary
- Total conditions: 4
- Total reps: 12
- Total steps simulated: 2400
- Runtime: 13.27s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| damping=0.05 | 0.804708 | 6.9661 | 45.2560 | 128 | 13.7403 | 1 |
| damping=0.1 | 0.802182 | 6.8776 | 42.8630 | 128 | 13.1341 | 1 |
| damping=0.2 | 0.797812 | 6.7007 | 38.5007 | 128 | 11.9797 | 1 |
| damping=0.5 | 0.790673 | 6.1674 | 28.1433 | 110 | 8.9442 | 1 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 3 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.95 <= injected=50.00

## Falsifiers
- All damping values produce identical results (no sensitivity)
- Higher damping produces non-monotonic response without explanation

## Deviations / Incidents
- (none — automated run)
