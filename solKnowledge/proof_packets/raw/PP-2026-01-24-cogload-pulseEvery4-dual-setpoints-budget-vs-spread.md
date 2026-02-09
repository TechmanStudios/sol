# Proof Packet — Cognitive load (pulseEvery=4) reveals dual setpoints: budget-crossing vs spread-favoring basin

## CLAIM
For the distributed multi-agent cognitive-load configuration at approxInjectRate=0.75 (injectAmount=1.0, agentCount=6, targetsPerPulse=3, pulseEvery=4), the adaptive branching loop reveals two distinct, decision-relevant damping setpoints:

1) **Budget-crossing setpoint** near damping ≈ **1.869131165–1.86913117** (inside micro-grid bracket), where `minFailStep` crosses the 1200-step runtime budget, but pressure stress/spikes can jump sharply.

2) **Spread-favoring basin** near damping ≈ **1.196**, where `rhoEffN` is slightly higher and pressure spikes are lower, but the run typically fails **short** of the 1200-step budget (i.e., it is a viable choice for a relaxed budget like 1000, not for 1200).

This demonstrates a practical controller tradeoff: enforcing the 1200-step compute-window constraint pushes the system away from the low-stress/high-spread basin and onto the budget-crossing boundary.

## EVIDENCE
- Adaptive branching run root:
  - `solData/testResults/adaptive_cognitive_load/20260124-232226-883/`
  - Branch modes (budget/spike/spread) and window decisions are recorded in:
    - `solData/testResults/adaptive_cognitive_load/20260124-232226-883/journal.json`

- **Budget-crossing boundary (branch b0, iter 12)**
  - Compare report:
    - `solData/testResults/adaptive_cognitive_load/20260124-232226-883/iter_12/b0/compare/cognitive_load_compare.md`
  - Observations (distributed, approxRate=0.75):
    - At damping 1.86912… → `minFailStep=1195`, `peakPMax≈9.29`, `peakRhoSum≈463.7`, `rhoEffN≈64.08`
    - At damping 1.86915… → `minFailStep=1267`, `peakPMax≈16.92`, `peakRhoSum≈673.1`, `rhoEffN≈64.08`
  - Interpretation:
    - A very small damping change around ~1.869 triggers a **large** spike/mass jump while also flipping across the 1200-step budget.

- **Spread-favoring basin (branch b2, iter 12)**
  - Compare report:
    - `solData/testResults/adaptive_cognitive_load/20260124-232226-883/iter_12/b2/compare/cognitive_load_compare.md`
  - Observations (distributed, approxRate=0.75):
    - Around damping 1.1960… → `rhoEffN≈65.26` (higher than the budget-crossing branch), `peakPMax≈7.82` (lower), but `minFailStep=1015` (fails short of 1200)
    - Around damping 1.1972… → `minFailStep=1195` (still short of 1200), `peakPMax≈9.58`, `rhoEffN≈65.26`
  - Interpretation:
    - This region offers **higher spread and lower spikes**, but cannot satisfy the 1200-step budget in these samples.

- Replication bundle (5 repeats per point; same two windows)
  - Root:
    - `solData/testResults/cogload_replications/20260125-004836-692/`
  - Window A (spread basin) compare report:
    - `solData/testResults/cogload_replications/20260125-004836-692/window_A_1196_spread/compare/cognitive_load_compare.md`
    - Confirms the spread-favoring basin remains below the 1200-step budget in this window (e.g., `minFailStep=1015` at ~1.1960…), with higher `rhoEffN` and lower spikes than the budget boundary.
  - Window B (budget boundary) compare report:
    - `solData/testResults/cogload_replications/20260125-004836-692/window_B_1869_budget/compare/cognitive_load_compare.md`
    - Confirms the sharp budget-crossing boundary near ~1.86915 persists, alongside the spike/mass jump.

- Replication bundle (20 repeats per point; widened windows)
  - Root:
    - `solData/testResults/cogload_replications/20260125-005644-007/`
  - Window A widened (1.195–1.199) compare report:
    - `solData/testResults/cogload_replications/20260125-005644-007/window_A_1196_spread/compare/cognitive_load_compare.md`
    - Shows the spread-favoring region at lower damping (1.195–1.197) still fails short of the 1200-step budget (`minFailStep=1015`), then shifts to `minFailStep=1195` by damping 1.198–1.199 (still short of 1200).
  - Window B widened (1.8689–1.8693) compare report:
    - `solData/testResults/cogload_replications/20260125-005644-007/window_B_1869_budget/compare/cognitive_load_compare.md`
    - Tightens the boundary location: at damping 1.86912 → `minFailStep=1195` (below budget) and at 1.86914 → `minFailStep=1267` (above budget), with a large spike/mass jump across the same narrow interval.

- Replication bundle (20 repeats per point; micro-grid around boundary)
  - Root:
    - `solData/testResults/cogload_replications/20260125-011457-652/`
  - Window B micro-grid (1.86912–1.86914 with 5e-6 steps) compare report:
    - `solData/testResults/cogload_replications/20260125-011457-652/window_B_1869_budget/compare/cognitive_load_compare.md`
    - Further tightens the boundary: 1.86913 → `minFailStep=1195` (below budget) while 1.869135 → `minFailStep=1267` (above budget). Spike/mass metrics jump across the same interval.

- Replication bundle (20 repeats per point; micro-grid refine at 1e-6)
  - Root:
    - `solData/testResults/cogload_replications/20260125-020601-495/`
  - Window B micro-grid (1.869131–1.869134 in 1e-6 steps) compare report:
    - `solData/testResults/cogload_replications/20260125-020601-495/window_B_1869_budget/compare/cognitive_load_compare.md`
    - Refines the bracket again: 1.869131 → `minFailStep=1195` (below budget) while 1.869132 → `minFailStep=1267` (above budget), with the same large spike/mass jump.

- Replication bundle (20 repeats per point; half-step check)
  - Root:
    - `solData/testResults/cogload_replications/20260125-021140-995/`
  - Window B half-step compare report:
    - `solData/testResults/cogload_replications/20260125-021140-995/window_B_1869_budget/compare/cognitive_load_compare.md`
    - Confirms the crossing is already on the “above budget” side at 1.8691315 (`minFailStep=1267`), tightening the bracket to 1.869131–1.8691315.

- Replication bundle (20 repeats per point; fine scan inside bracket)
  - Root:
    - `solData/testResults/cogload_replications/20260125-031632-846/`
  - Window B fine scan compare report:
    - `solData/testResults/cogload_replications/20260125-031632-846/window_B_1869_budget/compare/cognitive_load_compare.md`
    - Observed transition: 1.86913115 → `minFailStep=1195` (below budget) while 1.8691312 → `minFailStep=1267` (above budget), with the characteristic spike/mass jump.

- Replication bundle (20 repeats per point; inside micro-grid)
  - Root:
    - `solData/testResults/cogload_replications/20260125-033156-710/`
  - Window B inside micro-grid compare report:
    - `solData/testResults/cogload_replications/20260125-033156-710/window_B_1869_budget/compare/cognitive_load_compare.md`
    - Refines the bracket again: 1.869131165 → `minFailStep=1195` (below budget) while 1.86913117 → `minFailStep=1267` (above budget). The spike/mass jump occurs across the same narrow interval.

## ASSUMPTIONS
- Determinism / variance:
  - Adaptive loop evidence is runs=1.
  - Replication bundle evidence includes runs=5 per point (tight windows) and runs=20 per point (widened windows); treat boundary location/metrics as more reliable within those windows, but still recommend additional replications if downstream decisions are sensitive.
- Baseline state:
  - Baseline prep is assumed consistent within a batch; baseline-pinning is not explicitly captured inside the compare reports.
- Dashboard defaults:
  - Any implicit dashboard defaults beyond the explicit command parameters are assumed stable.

## FALSIFY
- Replicate both local windows with multiple repeats per point and verify:
  - A) Near damping ~1.869, `minFailStep` crosses 1200 and the spike/mass jump persists.
  - B) Near damping ~1.196–1.198, `rhoEffN` remains higher and `peakPMax` remains lower than the ~1.869 region, while `minFailStep` remains below 1200.
- Falsification signature:
  - The ~1.196 basin meets the 1200 budget reliably (eliminating the tradeoff), or the `rhoEffN`/spike advantage disappears under replication.

## STATUS
supported (replicated; runs=20 per point; boundary micro-grid confirms bracket)

## SOURCES
- `solData/testResults/adaptive_cognitive_load/20260124-232226-883/journal.json`
- `solData/testResults/adaptive_cognitive_load/20260124-232226-883/iter_12/b0/compare/cognitive_load_compare.md`
- `solData/testResults/adaptive_cognitive_load/20260124-232226-883/iter_12/b2/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-004836-692/window_A_1196_spread/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-004836-692/window_B_1869_budget/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-005644-007/window_A_1196_spread/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-005644-007/window_B_1869_budget/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-011457-652/window_B_1869_budget/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-020601-495/window_B_1869_budget/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-021140-995/window_B_1869_budget/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-031632-846/window_B_1869_budget/compare/cognitive_load_compare.md`
- `solData/testResults/cogload_replications/20260125-033156-710/window_B_1869_budget/compare/cognitive_load_compare.md`
