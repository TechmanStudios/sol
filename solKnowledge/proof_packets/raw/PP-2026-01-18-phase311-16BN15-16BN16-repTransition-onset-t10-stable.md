# Proof Packet — repTransition onset t=10 stable (Phase 3.11 BN15/BN16)

## CLAIM
In BN15 and BN16, the repTransition readout has a stable early dominance onset: the first read tick where mean `p114` exceeds 0.5 is consistently `t=10` across dirs, passes, and holds.

## EVIDENCE
- Run IDs:
  - 16BN15 (`schema`: `sol_phase311_16bn15_holdOrderSwap_v1`)
  - 16BN16 (`schema`: `sol_phase311_16bn16_holdOrderSwapCounterbalance_v1`)
- Export files:
  - `..._repTransition_curve.csv` for each run (listed in the source note)
- Key metrics (repTransition_curve):
  - For every (dir, passLabel, hold) group in BN15 and BN16: `p114_onset_gt0.5 = 10`.
  - Example aggregate markers (mean `p114`):
    - hold=0: `mean p114_t10 ≈ 0.99–1.00`
    - hold=81: `mean p114_t10 = 1.00`
    - hold=400: `mean p114_t10 ≈ 0.99–1.00`

## ASSUMPTIONS
- baselineMode:
  - `baselineModeUsed = SOLBaseline.restore`
- dt/damp/pressC/capLawHash:
  - `pressCUsed = 2.0`, `dampUsed = 20`, `capLawHash = 53c2811e`
- dashboard/harness version:
  - Not explicitly stated in the source note; treat as unknown unless verified.
- detector window positions:
  - The readTicks schedule includes `t=10` and `p114_onset_gt0.5` is computed from the same definition across all groups.
- session conditions:
  - Assumes no hidden per-pass manipulation of readTicks or computation code.

## FALSIFY
- Change the readTicks schedule (add earlier ticks, e.g., 2, 4, 6, 8) and confirm whether the onset remains at t=10 or shifts earlier.

## STATUS
supported

## SOURCES
- [rd33.md](solKnowledge/working/rd33.md#L1)
