# SOL Knowledge — Consolidation Index (as of 2026-01-24)

Purpose: provide a stable, navigable map of the current SOL R&D knowledge that lives in `solKnowledge/working/`, and enumerate extracted proof packets (audit-ready) promoted to `solKnowledge/proof_packets/`.

## Canonical master consolidations (verbatim stitched)
- Master (chat reports + rd0–rd30 + claim ledger scaffolding):
  - [sol_fullResearch_MASTER_PROOF_CLEAN.md](solKnowledge/working/sol_fullResearch_MASTER_PROOF_CLEAN.md)
- Prior stitched archives / readable variants (if you need alternate renderings):
  - [SOL_Archive_Consolidated_rd00-rd30_2026-01-15.md](solKnowledge/working/SOL_Archive_Consolidated_rd00-rd30_2026-01-15.md)
  - [SOL_Full_Detailed_Report_rd0-rd30_2026-01-16.md](solKnowledge/working/SOL_Full_Detailed_Report_rd0-rd30_2026-01-16.md)
  - [SOL_Full_Narrative_Readable_Report_rd0-rd30_plus_rd1_1_2026-01-16.md](solKnowledge/working/SOL_Full_Narrative_Readable_Report_rd0-rd30_plus_rd1_1_2026-01-16.md)
  - [sol_fullResearch_rd0_rd30_TAGGED.md](solKnowledge/working/sol_fullResearch_rd0_rd30_TAGGED.md)

## Newer R&D notes not included in the rd0–rd30 master stitch
- Phase 3.11 follow-ons / protocol + dataset expansions:
  - [rd31.md](solKnowledge/working/rd31.md)
  - [rd32.md](solKnowledge/working/rd32.md)
  - [rd33.md](solKnowledge/working/rd33.md)

## Phase-layer ridge bands
- [phase_layer_ridge_bands_2026-01-27.md](phase_layer_ridge_bands_2026-01-27.md)

## Research notes
- [solResearchNote1.md](solKnowledge/working/solResearchNote1.md)
- [solResearchNote2.md](solKnowledge/working/solResearchNote2.md)

## External artifacts manifest (traceability for bulky exports)
- [sol_external_artifacts_manifest.md](solKnowledge/working/sol_external_artifacts_manifest.md)

## Extracted proof packets (promoted)
These were extracted from [rd33.md](solKnowledge/working/rd33.md) and normalized to the SOL Proof Packet Standard.

- [PP-2026-01-18-phase311-16BN15-16BN16-hold400-programs-bus-regime.md](solKnowledge/proof_packets/PP-2026-01-18-phase311-16BN15-16BN16-hold400-programs-bus-regime.md)
- [PP-2026-01-18-phase311-16BN15-16BN16-hold400-macro-outcomes-reversible-under-order-swap.md](solKnowledge/proof_packets/PP-2026-01-18-phase311-16BN15-16BN16-hold400-macro-outcomes-reversible-under-order-swap.md)
- [PP-2026-01-18-phase311-16BN15-16BN16-lateCaptureTick-pass-position-drift.md](solKnowledge/proof_packets/PP-2026-01-18-phase311-16BN15-16BN16-lateCaptureTick-pass-position-drift.md)
- [PP-2026-01-18-phase311-16BN15-16BN16-repTransition-onset-t10-stable.md](solKnowledge/proof_packets/PP-2026-01-18-phase311-16BN15-16BN16-repTransition-onset-t10-stable.md)

Additional proof packets were promoted by tying claim-ledger items to on-disk CSV exports in `solData/testResults/`.

- [PP-2026-01-24-phase38-capLaw-twoMetric-shared-wide100-dt-robustness.md](solKnowledge/proof_packets/PP-2026-01-24-phase38-capLaw-twoMetric-shared-wide100-dt-robustness.md)
- [PP-2026-01-24-phase39-timeToFailureSweep-v2-dt-compresses-time-to-failure.md](solKnowledge/proof_packets/PP-2026-01-24-phase39-timeToFailureSweep-v2-dt-compresses-time-to-failure.md)
- [PP-2026-01-24-latchIdentity-lastInjector-selects-start-basin.md](solKnowledge/proof_packets/PP-2026-01-24-latchIdentity-lastInjector-selects-start-basin.md)
- [PP-2026-01-24-phase311-16l-ridgeScan-ampD-threshold.md](solKnowledge/proof_packets/PP-2026-01-24-phase311-16l-ridgeScan-ampD-threshold.md)
- [PP-2026-01-24-phase311-16bc-baselineRestore-vs-hardResetPerTrial-metric-shift.md](solKnowledge/proof_packets/PP-2026-01-24-phase311-16bc-baselineRestore-vs-hardResetPerTrial-metric-shift.md)
- [PP-2026-01-24-dreamAfterstate-rest-rhoMaxId82-dominant.md](solKnowledge/proof_packets/PP-2026-01-24-dreamAfterstate-rest-rhoMaxId82-dominant.md)

- [PP-2026-01-24-psiResonanceA-square-freqHz-affects-rho90-frac.md](solKnowledge/proof_packets/PP-2026-01-24-psiResonanceA-square-freqHz-affects-rho90-frac.md)

## Notes / next promotion candidates
- [sol_fullResearch_MASTER_PROOF_CLEAN.md](solKnowledge/working/sol_fullResearch_MASTER_PROOF_CLEAN.md) contains a top-level claim ledger (CL-1…CL-7). Some items now have promoted proof packets; others still need evidence-anchored promotion.
- CL-2/CL-3/CL-4/CL-5/CL-6/CL-7 now have at least one associated proof packet promoted from explicit CSV exports.
- Remaining: CL-1 (baseline restore comparability) and additional subclaims under CL-7.

## Cortex Session: CX-20260208-040833 (consolidated 2026-02-08)

- [PP-2026-02-08-cortex-CX-20260208-040833-h-001-c_press.md](solKnowledge/proof_packets/PP-2026-02-08-cortex-CX-20260208-040833-h-001-c_press.md)
  - Question: How does c_press affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: c_press: Pressure coefficient — not swept in headless

## Cortex Session: CX-20260208-051904 (consolidated 2026-02-08)

- [PP-2026-02-08-cortex-CX-20260208-051904-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-08-cortex-CX-20260208-051904-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-08-cortex-CX-20260208-051904-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-08-cortex-CX-20260208-051904-h-002-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

## Cortex Session: CX-20260208-055037 (consolidated 2026-02-08)

- [PP-2026-02-08-cortex-CX-20260208-055037-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-08-cortex-CX-20260208-055037-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found
