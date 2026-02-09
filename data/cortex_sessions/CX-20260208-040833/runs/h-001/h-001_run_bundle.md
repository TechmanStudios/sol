# RUN BUNDLE — h-001 (2026-02-07 23:08)

## Identity
- seriesName: h-001
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
How does c_press affect entropy, flux, and mass over 200 steps?

## Invariants
- dt: 0.12
- damping: 0.2
- rng_seed: 42

## Knobs (independent variables)
- c_press: [0.01, 0.05, 0.1, 0.2, 0.5]

## Injections
- grail: 50 at step 0

## Protocol
- Steps per condition: 200
- Reps per condition: 3
- Metrics every: 5 steps
- Baseline: fresh

## Results Summary
- Total conditions: 5
- Total reps: 15
- Total steps simulated: 3000
- Runtime: 22.44s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| c_press=0.01 | 0.122450 | 0.7748 | 45.6276 | 3 | 42.2604 | 1 |
| c_press=0.05 | 0.483735 | 3.8608 | 44.6745 | 105 | 28.6456 | 1 |
| c_press=0.1 | 0.797864 | 6.7007 | 38.4997 | 128 | 11.9771 | 1 |
| c_press=0.2 | 0.990017 | 0.9183 | 33.1158 | 128 | 0.2706 | 118 |
| c_press=0.5 | 0.996289 | 0.4103 | 31.9023 | 139 | 0.2421 | 90 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 3 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.79 <= injected=50.00

## Falsifiers
- All c_press values produce identical results (no sensitivity)
- Higher c_press produces non-monotonic response without explanation

## Deviations / Incidents
- (none — automated run)
