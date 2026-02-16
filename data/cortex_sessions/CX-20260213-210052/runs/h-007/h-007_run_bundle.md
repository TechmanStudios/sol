# RUN BUNDLE — h-007 (2026-02-13 16:03)

## Identity
- seriesName: h-007
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
How does injection affect entropy distribution and basin selection?

## Invariants
- dt: 0.12
- c_press: 0.1
- damping: 0.2
- rng_seed: 42

## Knobs (independent variables)
- injection: [0.2, 0.4, 0.6, 0.8, 1.0]

## Injections
- grail: 50 at step 0

## Protocol
- Steps per condition: 300
- Reps per condition: 3
- Metrics every: 5 steps
- Baseline: fresh

## Results Summary
- Total conditions: 5
- Total reps: 15
- Total steps simulated: 4500
- Runtime: 17.28s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| injection=0.2 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.4 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.6 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.8 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=1.0 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 4 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.79 <= injected=50.00

## Falsifiers
- Entropy is invariant to injection changes
- RhoMaxId distribution is identical across all values

## Deviations / Incidents
- (none — automated run)
