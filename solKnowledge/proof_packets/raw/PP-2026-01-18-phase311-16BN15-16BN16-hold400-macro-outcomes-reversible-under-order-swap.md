# Proof Packet — Macro outcomes reversible under hold-order swap (Phase 3.11 BN15/BN16)

## CLAIM
For the key long-hold regime (`betweenRepTicks_hold = 400`), swapping hold order between passes does not materially change macro outcomes: the `winner_peakBus` distributions remain stable across passes, even when the overall pass order is reversed (BN15 AB vs BN16 BA).

## EVIDENCE
- Run IDs:
  - 16BN15 (`schema`: `sol_phase311_16bn15_holdOrderSwap_v1`)
  - 16BN16 (`schema`: `sol_phase311_16bn16_holdOrderSwapCounterbalance_v1`)
- Export files:
  - `..._MASTER_summary.csv` for each run (see sources)
- Key metrics (MASTER_summary; winner counts out of 20 reps per (dir, pass, hold)):
  - BN15 hold=400: identical across passes within each dir
    - down: A `114:15 / 136:5`, B `114:15 / 136:5`
    - up: A `114:16 / 136:4`, B `114:16 / 136:4`
  - BN16 hold=400: identical across passes within each dir
    - down: A `114:16 / 136:4`, B `114:16 / 136:4`
    - up: A `114:16 / 136:4`, B `114:16 / 136:4`
  - Additional note in source: deltas in `fracTicks_busDom114` between B and A are small (~±0.006 per (dir, hold)) and not regime-flipping.

## ASSUMPTIONS
- baselineMode:
  - `baselineModeUsed = SOLBaseline.restore` (both runs)
- dt/damp/pressC/capLawHash:
  - `pressCUsed = 2.0`, `dampUsed = 20`, `capLawHash = 53c2811e` (both runs)
- dashboard/harness version:
  - Not explicitly stated in the source note; treat as unknown unless verified.
- detector window positions:
  - Assumes the same winner computation (`winner_peakBus`) across both runs.
- session conditions:
  - Counterbalance design is explicit: BN15 (A first, B second), BN16 (B first, A second).

## FALSIFY
- Increase repsPerCondition (e.g., 100) to test whether small differences accumulate into drift.
- Insert a controlled washout between passes (nonzero `betweenConditionSettleTicks`) and check whether macro invariance persists.

## STATUS
robust

## SOURCES
- [rd33.md](solKnowledge/working/rd33.md#L1)
