# Proof Packet — Cognitive load (pulseEvery=4) damping boundary produces C vs C0 divergence

## CLAIM
For the distributed multi-agent cognitive-load configuration at approxInjectRate=0.75 (injectAmount=1.0, agentCount=6, targetsPerPulse=3, pulseEvery=4), there is a sharp damping boundary near ~1.87 where time-to-failure jumps across the runtime budget (1200 steps). This boundary forces throughput objective **C** (spike-aware, near-best bandwidth) to diverge from **C0** (pure bandwidth-at-all-cost).

## EVIDENCE
- Divergence report (C vs C0 setpoints at pulseEvery=4):
  - `solData/testResults/cognitive_load_compare/20260125-025042/cognitive_load_compare.md`
  - Controller setpoints table row (distributed, pulseEvery=4, approxRate=0.75):
    - C selects damping **1.8311** with bandwidth **896.25** (i.e., 0.75 × 1195)
    - C0 selects damping **6.9849** with bandwidth **900.00** (i.e., 0.75 × 1200)
    - Same row shows a hard jump in `minFailStep` from **1195** (below budget) to **1267** (above budget) as damping increases.

- Adaptive 10-iteration loop run (automatically brackets the budget crossing):
  - Root: `solData/testResults/adaptive_cognitive_load/20260124-230323/`
  - Journal decisions: `solData/testResults/adaptive_cognitive_load/20260124-230323/journal.json`
    - Iter 1 brackets [1.7, 2.05] due to “crosses budget 1200”.
    - Iter 10 converges to ~[1.869129, 1.869133], repeatedly selecting the same crossing pair.
  - Iteration 1 readout shows the jump in `minFailStep` at fixed load:
    - `solData/testResults/adaptive_cognitive_load/20260124-230323/iter_01/cognitive_load_readout.csv`
    - Example adjacent points (distributed, approxRate=0.75):
      - damping=1.75 → minFailStep=1195
      - damping=2.00 → minFailStep=1267

## ASSUMPTIONS
- Baseline state and initial conditions:
  - Not explicitly pinned/recorded in the CSV readouts; assume consistent baseline across points within each batch.
- Dashboard + harness version:
  - Commands were generated/run against `sol_dashboard_v3_7_2.html` (as recorded by automation tooling), but internal dashboard state and any implicit defaults beyond the command params are assumed stable.
- Determinism / variance:
  - Each point was run with runs=1; treat the boundary location as an estimate until replicated.

## FALSIFY
- Repeat the pulseEvery=4 damping sweep with identical parameters (including baseline prep) and verify:
  - The budget crossing persists (minFailStep below 1200 at damping <~1.87 and above 1200 at damping >~1.87).
  - The C vs C0 divergence persists in the controller setpoints table when `--include-pure-c` is enabled.
- Falsification signature:
  - No sharp boundary exists (minFailStep varies smoothly or never crosses 1200), or C and C0 pick the same damping under the same selection rules.

## STATUS
supported

## SOURCES
- `solData/testResults/cognitive_load_compare/20260125-025042/cognitive_load_compare.md`
- `solData/testResults/adaptive_cognitive_load/20260124-230323/journal.json`
- `solData/testResults/adaptive_cognitive_load/20260124-230323/iter_01/cognitive_load_readout.csv`
