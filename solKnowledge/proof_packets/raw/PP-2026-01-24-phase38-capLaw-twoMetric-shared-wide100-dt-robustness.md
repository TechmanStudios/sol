# Proof Packet — Phase 3.8 CapLaw twoMetric_SHARED (wide100 dt robustness)

## CLAIM
In the Phase 3.8 wide100 twoMetric_SHARED dt sweep, the dt-normalized peak-edge outflux metric changes by ~11% and mean retention changes by ~4% from dt=0.08 to dt=0.16 under the same cap-law configuration, indicating coarse-scale dt robustness.

## EVIDENCE
- Run IDs:
  - Aggregated in the shared summary export; each row is a dt condition for a 100-target wide set.
- Export files:
  - `solData/testResults/sol_capLaw_twoMetric_SHARED_summary.csv`
- Key metrics (from the export above; dt rows with columns `max_rPeak` (peak-edge metric), `mean_ret` (mean retentionEnd), `mean_pMean`, `max_pMax`):
  - dt=0.08:
    - `max_rPeak = 0.07220995222690492`
    - `mean_ret = 0.952438537824689`
    - `mean_pMean = 0.342726070119947`
    - `max_pMax = 47.85290302723389`
  - dt=0.16:
    - `max_rPeak = 0.08038190038969957` (Δ ≈ +11.32% vs dt=0.08)
    - `mean_ret = 0.9127819964071494` (Δ ≈ -4.16% vs dt=0.08)
    - `mean_pMean = 0.3464175259368846` (Δ ≈ +1.08% vs dt=0.08)
    - `max_pMax = 47.74734641217319` (Δ ≈ -0.22% vs dt=0.08)
- Notes about detector windows/definitions:
  - rd23 describes `max_rPeak` as the dt-normalized peak-edge metric (`outfluxRate_peakEdge`).

## ASSUMPTIONS
- baselineMode:
  - Baseline restore is not recorded in this export; treat as unknown.
- dt/damp/pressC/capLawHash:
  - The cap-law family is described in rd23 as a degree-power capacitance law with `kDtGamma = 0` at this checkpoint.
  - Other run parameters (pressC/damp) are not recorded in this summary export; treat as unknown.
- dashboard/harness version:
  - Not recorded in the export; treat as unknown.
- detector window positions:
  - Assumes the same measurement window was used across the dt runs (not recorded here).
- session conditions:
  - Assumes the 100-target list and baseline state were held constant across dt.

## FALSIFY
- Re-run the same wide100 dt sweep under snapshot/restore and compare the same summary metrics.
- Falsification signature: large divergence in `max_rPeak` or `mean_ret` across dt that is not explained by configuration or baseline drift.

## STATUS
supported

## SOURCES
- [rd23.md](solKnowledge/working/rd23.md#L1)
