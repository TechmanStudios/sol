# Proof Packet — Phase 3.11.16l ridge scan (sharp ampD threshold)

## CLAIM
In Phase 3.11.16l ridge scan at fixed ampB=4, ampD=5.5 is metastable (mixed `none`/`bothOn`) while ampD≥5.75 yields `bothOn` in every replicate.

## EVIDENCE
- Run IDs:
  - Sweep is aggregated in the export file; each row is one replicate with `ampB`, `ampD`, and outcome columns.
- Export files:
  - `solData/testResults/sol_phase311_16l_ridgeScanOnsetDelay_v1_2026-01-11T19-18-35-047Z_2026-01-11T19-43-03-964Z_MASTER_summary.csv`
- Key metrics (from the export above; columns: `ampB`, `ampD`, `outcome`, onset/peak columns):
  - Outcome counts by `ampD` (n=12 reps per `ampD`):
    - ampD=5.5: `bothOn` = 4, `none` = 8
    - ampD=5.75: `bothOn` = 12
    - ampD=6.0 through 8.0: `bothOn` = 12 (each)
  - Near-ridge “slow charge” behavior is visible at ampD=5.5 in successful reps where onsets occur later than t=1 (e.g., non-empty `onset114_tick` / `onset136_tick`).
- Notes about detector windows/definitions:
  - `outcome` encodes whether both bus rails crossed threshold (`bothOn`) or neither did (`none`).

## ASSUMPTIONS
- baselineMode:
  - Not recorded in this export; treat as unknown.
- dt/damp/pressC/capLawHash:
  - `dt` is recorded as `0.12` for these runs.
  - Other physics/harness parameters are not recorded in this export; treat as unknown.
- dashboard/harness version:
  - Not recorded in this export; treat as unknown.
- detector window positions:
  - Assumes onset/peak ticks are computed on the same observation window across all reps (window and tick count are recorded as `totalTicks` / `windowMs` / `everyMs`).
- session conditions:
  - Assumes the same baseline state was used across the sweep.

## FALSIFY
- Repeat the ridge scan with the same baseline and parameters and compute P(`bothOn` | `ampD`).
- Falsification signature: a repeated sweep where ampD=5.5 is consistently 100% `bothOn` or where ampD≥5.75 yields any `none` outcomes under the same controls.

## STATUS
supported

## SOURCES
- [rd29.md](solKnowledge/working/rd29.md#L1)
