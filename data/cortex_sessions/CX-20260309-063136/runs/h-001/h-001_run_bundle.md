# RUN BUNDLE — h-001 (2026-03-09 06:32)

## Identity
- seriesName: h-001
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
At what value of damping does the system behavior qualitatively change?

## Invariants
- dt: 0.12
- c_press: 0.1
- rng_seed: 42

## Knobs (independent variables)
- damping: [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]

## Injections
- grail: 50 at step 0

## Protocol
- Steps per condition: 300
- Reps per condition: 5
- Metrics every: 5 steps
- Baseline: fresh

## Results Summary
- Total conditions: 8
- Total reps: 40
- Total steps simulated: 12000
- Runtime: 32.93s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| damping=0.05 | 0.985451 | 2.3524 | 41.5223 | 128 | 0.6366 | 132 |
| damping=0.1 | 0.985260 | 1.8322 | 37.2642 | 128 | 0.5430 | 132 |
| damping=0.15 | 0.985404 | 1.4988 | 33.4324 | 127 | 0.4572 | 132 |
| damping=0.2 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| damping=0.25 | 0.986131 | 1.1774 | 26.9116 | 127 | 0.3180 | 132 |
| damping=0.3 | 0.986467 | 1.0470 | 24.1514 | 127 | 0.2647 | 132 |
| damping=0.4 | 0.986925 | 0.8094 | 19.4601 | 127 | 0.1859 | 132 |
| damping=0.5 | 0.987173 | 0.6070 | 15.6820 | 118 | 0.1464 | 43 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 3 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.95 <= injected=50.00

## Falsifiers
- No transition detected across entire range
- Transition is not reproducible across reps

## Deviations / Incidents
- (none — automated run)
