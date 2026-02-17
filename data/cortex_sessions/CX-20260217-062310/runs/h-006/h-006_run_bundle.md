# RUN BUNDLE — h-006 (2026-02-17 06:24)

## Identity
- seriesName: h-006
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
Does dt compress time-to-failure in headless sol-core as it does in the dashboard?

## Invariants
- c_press: 0.1
- damping: 0.2
- rng_seed: 42

## Knobs (independent variables)
- dt: [0.08, 0.1, 0.12, 0.16, 0.2]

## Injections
- grail: 50 at step 0

## Protocol
- Steps per condition: 500
- Reps per condition: 5
- Metrics every: 10 steps
- Baseline: fresh

## Results Summary
- Total conditions: 5
- Total reps: 25
- Total steps simulated: 12500
- Runtime: 34.56s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| dt=0.08 | 0.988419 | 0.6273 | 27.6785 | 127 | 0.2393 | 43 |
| dt=0.1 | 0.990593 | 0.1949 | 22.5005 | 127 | 0.1772 | 22 |
| dt=0.12 | 0.992042 | 0.0882 | 18.3509 | 127 | 0.1424 | 58 |
| dt=0.16 | 0.994120 | 0.0385 | 12.2512 | 0 | 0.0936 | 138 |
| dt=0.2 | 0.995563 | 0.0232 | 8.1617 | 0 | 0.0620 | 31 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 3 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.78 <= injected=50.00

## Falsifiers
- Time-to-failure is constant across dt values
- Relationship is non-monotonic (failure time increases then decreases)

## Deviations / Incidents
- (none — automated run)
