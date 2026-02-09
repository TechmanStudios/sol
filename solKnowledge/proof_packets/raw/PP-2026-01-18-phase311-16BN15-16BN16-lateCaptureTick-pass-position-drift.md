# Proof Packet — lateCaptureTick shifts track pass-position drift (Phase 3.11 BN15/BN16)

## CLAIM
Shifts in `lateCaptureTick_114_primary` are primarily driven by pass-position / time-in-session effects rather than a stable order-label effect (A vs B): when pass order is reversed (BN16), the sign of the “second minus first pass” delta flips for holds 0 and 81.

## EVIDENCE
- Run IDs:
  - 16BN15 (`schema`: `sol_phase311_16bn15_holdOrderSwap_v1`)
  - 16BN16 (`schema`: `sol_phase311_16bn16_holdOrderSwapCounterbalance_v1`)
- Export files:
  - `..._MASTER_summary.csv` for each run (see sources)
- Key metrics (MASTER_summary; mean delta = passPosition2 − passPosition1, averaged across dirs):
  - BN15 (A first, B second):
    - hold=0: `+1.300`
    - hold=81: `−1.700`
    - hold=400: `−1.150`
  - BN16 (B first, A second):
    - hold=0: `−3.275` (sign flips vs BN15)
    - hold=81: `+1.550` (sign flips vs BN15)
    - hold=400: `−0.700` (same sign as BN15; smaller magnitude)

## ASSUMPTIONS
- baselineMode:
  - `baselineModeUsed = SOLBaseline.restore`
- dt/damp/pressC/capLawHash:
  - `pressCUsed = 2.0`, `dampUsed = 20`, `capLawHash = 53c2811e`
- dashboard/harness version:
  - Not explicitly stated in the source note; treat as unknown unless verified.
- detector window positions:
  - `lateCaptureTick_114_primary` is computed consistently across runs.
- session conditions:
  - The AB/BA counterbalance is sufficient to distinguish label effects from pass-position effects.

## FALSIFY
- Repeat additional AB/BA pairs and check whether sign-flips persist for holds 0 and 81.
- Add a hard reset between dirs (or rerun in a fresh session) to separate within-session drift from protocol effects.

## STATUS
supported

## SOURCES
- [rd33.md](solKnowledge/working/rd33.md#L1)
