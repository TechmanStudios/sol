# RUN BUNDLE — h-008 (2026-02-14 02:11)

## Identity
- seriesName: h-008
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
At what value of injection does the system behavior qualitatively change?

## Invariants
- dt: 0.12
- c_press: 0.1
- damping: 0.2
- rng_seed: 42

## Knobs (independent variables)
- injection: [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]

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
- Runtime: 45.93s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| injection=0.05 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.1 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.15 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.2 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.25 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.3 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.4 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |
| injection=0.5 | 0.985735 | 1.3110 | 29.9921 | 127 | 0.3820 | 132 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 4 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.79 <= injected=50.00

## Falsifiers
- No transition detected across entire range
- Transition is not reproducible across reps

## Deviations / Incidents
- (none — automated run)
