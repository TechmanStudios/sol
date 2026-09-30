# Proof Packet — Hold=400 programs bus regime (Phase 3.11 BN15/BN16)

## CLAIM
Under Phase 3.11 conditions (BN15+BN16), setting `betweenRepTicks_hold = 400` reliably shifts the system into a distinct bus-outcome regime versus holds `0` or `81`, including higher frequency of `winner_peakBus = 136`, reduced 114 dominance fraction, reduced bus dominance entropy, and larger peak bus magnitudes.

## EVIDENCE
- Run IDs:
  - 16BN15 (`schema`: `sol_phase311_16bn15_holdOrderSwap_v1`)
  - 16BN16 (`schema`: `sol_phase311_16bn16_holdOrderSwapCounterbalance_v1`)
- Export files:
  - `sol_phase311_16bn15_holdOrderSwap_v1_2026-01-18T15-10-44-626Z_2026-01-18T15-14-36-836Z_MASTER_summary.csv`
  - `sol_phase311_16bn16_holdOrderSwapCounterbalance_v1_2026-01-18T22-19-10-909Z_2026-01-18T22-22-53-955Z_MASTER_summary.csv`
  - Each run also lists `..._MASTER_busTrace.csv` and `..._repTransition_curve.csv`
- Key metrics (MASTER_summary; combined across BN15+BN16, n=160 reps per hold):
  - `p136 = P(winner_peakBus=136)`
    - hold=0: `p136 = 0.01875` (3/160)
    - hold=81: `p136 = 0.01875` (3/160)
    - hold=400: `p136 = 0.21250` (34/160)
  - `mean fracTicks_busDom114`
    - hold=0: `0.204473`
    - hold=81: `0.201559`
    - hold=400: `0.190446`
  - `mean busDomEntropy_bits`
    - hold=0: `0.730077`
    - hold=81: `0.723927`
    - hold=400: `0.701569`
  - `mean lateCaptureTick_114_primary`
    - hold=0: `127.856`
    - hold=81: `114.362`
    - hold=400: `96.275`
  - `mean peakAbs114_bus`, `mean peakAbs136_bus`
    - hold=0: `1.447`, `1.401`
    - hold=81: `1.895`, `1.834`
    - hold=400: `4.048`, `3.863`

## ASSUMPTIONS
- baselineMode:
  - `baselineModeUsed = SOLBaseline.restore` (both runs)
- dt/damp/pressC/capLawHash:
  - `pressCUsed = 2.0` (constant)
  - `dampUsed = 20` (constant)
  - `capLawHash = 53c2811e` (constant)
- dashboard/harness version:
  - Not explicitly stated in the source note; treat as unknown unless verified.
- detector window positions:
  - Winner/entropy/dominance computed from the same MASTER_summary schema across runs.
- session conditions:
  - A/B pass ordering is counterbalanced (BN15 is AB; BN16 is BA).

## FALSIFY
- Change only the hold set (e.g., `{0, 81, 200, 400, 800}`) and test whether regime shifts scale smoothly with hold or show thresholds.
- Repeat the BN15/BN16 pair at different `dampUsed` (e.g., 18, 22) to see whether the hold=400 regime persists.

## STATUS
robust

## SOURCES
- [rd33.md](solKnowledge/working/rd33.md#L1)
