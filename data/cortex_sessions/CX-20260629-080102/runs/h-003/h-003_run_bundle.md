# RUN BUNDLE — h-003 (2026-06-29 08:02)

## Identity
- seriesName: h-003
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
- Runtime: 63.46s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| damping=0.05 | 0.985456 | 2.3552 | 41.5230 | 128 | 0.6369 | 132 |
| damping=0.1 | 0.985257 | 1.8342 | 37.2650 | 128 | 0.5432 | 132 |
| damping=0.15 | 0.985402 | 1.5001 | 33.4337 | 127 | 0.4575 | 132 |
| damping=0.2 | 0.985731 | 1.3114 | 29.9935 | 127 | 0.3823 | 132 |
| damping=0.25 | 0.986127 | 1.1779 | 26.9131 | 127 | 0.3182 | 132 |
| damping=0.3 | 0.986464 | 1.0475 | 24.1529 | 127 | 0.2648 | 132 |
| damping=0.4 | 0.986922 | 0.8099 | 19.4618 | 127 | 0.1860 | 132 |
| damping=0.5 | 0.987172 | 0.6074 | 15.6837 | 118 | 0.1465 | 43 |

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
