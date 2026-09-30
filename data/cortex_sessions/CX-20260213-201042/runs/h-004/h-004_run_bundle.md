# RUN BUNDLE — h-004 (2026-02-13 15:11)

## Identity
- seriesName: h-004
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
Do different injection targets produce distinct basin formations?

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
- Steps per condition: 200
- Reps per condition: 3
- Metrics every: 5 steps
- Baseline: fresh

## Results Summary
- Total conditions: 1
- Total reps: 3
- Total steps simulated: 600
- Runtime: 2.29s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.797864 | 6.7007 | 38.4997 | 128 | 11.9771 | 1 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 4 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.79 <= injected=50.00

## Falsifiers
- All injection targets produce identical metric trajectories
- RhoMaxId is always the same regardless of injection target

## Notes
Comparing targets: ['grail', 'consciousness', 'gravity', 'entropy']
Manual: run separately for each target in ['grail', 'consciousness', 'gravity', 'entropy']

## Deviations / Incidents
- (none — automated run)
