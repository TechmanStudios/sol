# RUN BUNDLE — h-002 (2026-02-13 21:23)

## Identity
- seriesName: h-002
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
- Runtime: 9.42s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| damping=0.05 | 0.804756 | 6.9661 | 45.2555 | 128 | 13.7375 | 1 |
| damping=0.1 | 0.802231 | 6.8776 | 42.8623 | 128 | 13.1314 | 1 |
| damping=0.2 | 0.797864 | 6.7007 | 38.4997 | 128 | 11.9771 | 1 |
| damping=0.5 | 0.790732 | 6.1673 | 28.1416 | 110 | 8.9417 | 1 |

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
