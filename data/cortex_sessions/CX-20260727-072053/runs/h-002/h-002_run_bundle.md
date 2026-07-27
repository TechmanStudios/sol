# RUN BUNDLE — h-002 (2026-07-27 07:22)

## Identity
- seriesName: h-002
- engine: sol-core (headless Python)
- baselineModeUsed: fresh
- operator: sol-core auto_run
- rng_seed: 42

## Question
How does psi_diffusion affect entropy distribution and basin selection?

## Invariants
- dt: 0.12
- c_press: 0.1
- damping: 0.2
- rng_seed: 42

## Knobs (independent variables)
- psi_diffusion: [0.2, 0.4, 0.6, 0.8, 1.0]

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
- Runtime: 24.84s

## Final Metrics by Condition

| Condition | Entropy | Flux | Mass | Active | RhoMax | RhoMaxNode |
| --- | --- | --- | --- | --- | --- | --- |
| psi_diffusion=0.2 | 0.985731 | 1.3114 | 29.9935 | 127 | 0.3823 | 132 |
| psi_diffusion=0.4 | 0.985731 | 1.3114 | 29.9935 | 127 | 0.3823 | 132 |
| psi_diffusion=0.6 | 0.985731 | 1.3114 | 29.9935 | 127 | 0.3823 | 132 |
| psi_diffusion=0.8 | 0.985731 | 1.3114 | 29.9935 | 127 | 0.3823 | 132 |
| psi_diffusion=1.0 | 0.985731 | 1.3114 | 29.9935 | 127 | 0.3823 | 132 |

## Sanity Checks
- Overall: PASS
- ✓ baseline_declared: Baseline mode: fresh
- ✓ invariants: All 4 invariants constant
- ✓ no_nan: No NaN/Inf values found
- ✓ entropy_bounds: Entropy in [0,1] for all steps
- ✓ mass_conservation: Mass bounded: max=49.79 <= injected=50.00

## Falsifiers
- Entropy is invariant to psi_diffusion changes
- RhoMaxId distribution is identical across all values

## Deviations / Incidents
- (none — automated run)
