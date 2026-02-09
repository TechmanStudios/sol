# Proof Packet — Phase 3.11.16bc baselineRestore vs hardResetPerTrial (metric shift)

## CLAIM
In Phase 3.11.16bc, the hardResetPerTrial v1 run produces substantially larger bus peak magnitudes and later bus capture ticks than the baselineRestore v1 run under the same recorded press/damp/capLaw settings.

## EVIDENCE
- Run IDs:
  - `sol_phase311_16bcA_baselineRestore_v1_2026-01-17T23-36-46-534Z`
  - `sol_phase311_16bcB_hardResetPerTrial_v1_2026-01-17T23-40-41-965Z`
- Export files:
  - `solData/testResults/sol_phase311_16bcA_baselineRestore_v1_2026-01-17T23-36-46-534Z_2026-01-17T23-40-41-927Z_MASTER_summary.csv`
  - `solData/testResults/sol_phase311_16bcB_hardResetPerTrial_v1_2026-01-17T23-40-41-965Z_2026-01-17T23-51-52-414Z_MASTER_summary.csv`
- Key metrics (computed over all rows in each export; both have 520 rows):
  - Shared recorded settings (first-row check; consistent across the exports):
    - `pressCUsed = 2`
    - `dampUsed = 20`
    - `capLawHash = 53c2811e`
    - `baselineModeUsed = SOLBaseline.restore`
  - Mean bus peak magnitudes:
    - baselineRestore: mean `peakAbs114_bus = 0.784742`, mean `peakAbs136_bus = 0.775039`
    - hardResetPerTrial: mean `peakAbs114_bus = 1.756568`, mean `peakAbs136_bus = 1.713307`
  - Mean capture ticks:
    - baselineRestore: mean `captureTick_114 = 8.090385`, mean `captureTick_136 = 13.119231`
    - hardResetPerTrial: mean `captureTick_114 = 8.932692`, mean `captureTick_136 = 19.765385`
  - Winner counts (`winner_peakBus`):
    - baselineRestore: `114` = 416, `136` = 104
    - hardResetPerTrial: `114` = 435, `136` = 85

## ASSUMPTIONS
- baselineMode:
  - Both exports record `baselineModeUsed = SOLBaseline.restore`.
- dt/damp/pressC/capLawHash:
  - `pressCUsed`, `dampUsed`, and `capLawHash` are explicitly recorded and match.
  - dt is not recorded as a column in these exports; treat as unknown.
- dashboard/harness version:
  - Not recorded in these exports; treat as unknown.
- detector window positions:
  - Assumes `captureTick_*` and peak metrics are computed consistently across the two schemas.
- session conditions:
  - The run tags imply different reset semantics (`baselineRestore` vs `hardResetPerTrial`); this packet treats that as the independent variable.

## FALSIFY
- Re-run the paired protocols back-to-back under the same baseline snapshot and settings and compare the same summary metrics.
- Falsification signature: hardResetPerTrial does not show a meaningful upward shift in `peakAbs*_bus` or `captureTick_136` relative to baselineRestore.

## STATUS
supported

## SOURCES
- [sol_fullResearch_MASTER_PROOF_CLEAN.md](solKnowledge/working/sol_fullResearch_MASTER_PROOF_CLEAN.md#L34)
