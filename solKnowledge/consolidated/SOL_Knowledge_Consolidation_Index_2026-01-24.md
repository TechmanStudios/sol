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

## Cortex Session: CX-20260211-171412 (consolidated 2026-02-11)

- [PP-2026-02-11-cortex-CX-20260211-171412-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-171412-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-171412-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-171412-h-002-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-171412-h-003-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-171412-h-003-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-171412-h-004-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-171412-h-004-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-171412-h-005-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-171412-h-005-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260211-185612 (consolidated 2026-02-11)

- [PP-2026-02-11-cortex-CX-20260211-185612-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-185612-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-185612-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-185612-h-002-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-185612-h-003-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-185612-h-003-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-185612-h-004-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-185612-h-004-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-185612-h-005-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-185612-h-005-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260211-190125 (consolidated 2026-02-11)

- [PP-2026-02-11-cortex-CX-20260211-190125-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190125-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190125-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190125-h-002-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190125-h-003-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190125-h-003-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190125-h-004-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190125-h-004-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190125-h-005-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190125-h-005-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260211-190808 (consolidated 2026-02-11)

- [PP-2026-02-11-cortex-CX-20260211-190808-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190808-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190808-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190808-h-002-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190808-h-003-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190808-h-003-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190808-h-004-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190808-h-004-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-11-cortex-CX-20260211-190808-h-005-damping.md](solKnowledge/proof_packets/PP-2026-02-11-cortex-CX-20260211-190808-h-005-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260212-023605 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-023605-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-023605-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-023605-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-023605-h-002-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-023605-h-003-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-023605-h-003-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-023605-h-004-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-023605-h-004-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-023605-h-005-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-023605-h-005-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260212-031340 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-031340-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-031340-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-031340-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-031340-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-031340-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-031340-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-031340-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-031340-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-031340-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-031340-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260212-032105 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-032105-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032105-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032105-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032105-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032105-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032105-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032105-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032105-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032105-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032105-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260212-032759 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-032759-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032759-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032759-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032759-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032759-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032759-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032759-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032759-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-032759-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-032759-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260212-033330 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-033330-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-033330-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-033330-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-033330-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-033330-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-033330-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-033330-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-033330-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-033330-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-033330-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260212-034732 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-034732-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-034732-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-034732-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-034732-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-034732-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-034732-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-034732-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-034732-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-034732-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-034732-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: CL-6 | Sanity: PASS
  - Gap: CL-6 (Robust): End-phase latch primitive = lastInjected at dream stop selects start basin — no proof packet found

## Cortex Session: CX-20260212-052151 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-052151-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the turbulent regime (damping 0–10) contain any internal micro-transitions detectable only at higher resolution or with alternative observables?

- [PP-2026-02-12-cortex-CX-20260212-052151-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: How do flux and mass decay rates scale with damping within the turbulent regime, and are these rates topology-dependent?

- [PP-2026-02-12-cortex-CX-20260212-052151-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the monotonic decline in entropy and flux observed in the low-damping regime persist up to the transition zone (damping 10–15), or does it platea

- [PP-2026-02-12-cortex-CX-20260212-052151-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What specific topological features of the 140-node graph modulate the rate of flux decline under small damping increases?

- [PP-2026-02-12-cortex-CX-20260212-052151-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: CL-1 | Sanity: PASS
  - Gap: CL-1 (Robust): Baseline restore is non-negotiable for comparability — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-052151-h-006-dt.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-006-dt.md)
  - Question: Does dt compress time-to-failure in headless sol-core as it does in the dashboard?
  - Claim: CL-2 | Sanity: PASS
  - Gap: CL-2 (Supported): Degree-power anchored CapLaw generalizes beyond superhubs and is dt-robust at coarse scale — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-052151-h-007-psi_diffusion.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-007-psi_diffusion.md)
  - Question: How does psi_diffusion affect entropy distribution and basin selection?
  - Claim: CL-3 | Sanity: PASS
  - Gap: CL-3 (Robust): The system exhibits metastability; dt compresses time-to-failure into runaway mean-pressure basins — no proof packet found

- [PP-2026-02-12-cortex-CX-20260212-052151-h-008-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-052151-h-008-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: CL-4 | Sanity: PASS
  - Gap: CL-4 (Supported): Node 82 acts like a dominant ρ reservoir near failure/afterstates (rhoMaxId) — no proof packet found

## Cortex Session: CX-20260212-070748 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-070748-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the turbulent regime (damping 0–10) contain any internal micro-transitions detectable only at higher resolution or with alternative observables?

- [PP-2026-02-12-cortex-CX-20260212-070748-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: How do flux and mass decay rates scale with damping within the turbulent regime, and are these rates topology-dependent?

- [PP-2026-02-12-cortex-CX-20260212-070748-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the monotonic decline in entropy and flux observed in the low-damping regime persist up to the transition zone (damping 10–15), or does it platea

- [PP-2026-02-12-cortex-CX-20260212-070748-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What specific topological features of the 140-node graph modulate the rate of flux decline under small damping increases?

- [PP-2026-02-12-cortex-CX-20260212-070748-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What is the microscopic mechanism underlying the abrupt phonon mode collapse at the critical damping threshold?

- [PP-2026-02-12-cortex-CX-20260212-070748-h-006-dt.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-006-dt.md)
  - Question: Does dt compress time-to-failure in headless sol-core as it does in the dashboard?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the invariance of the collapse point hold under more extensive topology modifications or in different graph configurations?

- [PP-2026-02-12-cortex-CX-20260212-070748-h-007-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-007-damping.md)
  - Question: How does damping affect entropy distribution and basin selection?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Can the phase transition be characterized analytically or via spectral theory to predict the critical damping value?

- [PP-2026-02-12-cortex-CX-20260212-070748-h-012-topology.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-070748-h-012-topology.md)
  - Question: At what value of topology does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Can the invariance of the collapse threshold be proven analytically for arbitrary topology modifications?

## Cortex Session: CX-20260212-074704 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-074704-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the turbulent regime (damping 0–10) contain any internal micro-transitions detectable only at higher resolution or with alternative observables?

- [PP-2026-02-12-cortex-CX-20260212-074704-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: How do flux and mass decay rates scale with damping within the turbulent regime, and are these rates topology-dependent?

- [PP-2026-02-12-cortex-CX-20260212-074704-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the monotonic decline in entropy and flux observed in the low-damping regime persist up to the transition zone (damping 10–15), or does it platea

- [PP-2026-02-12-cortex-CX-20260212-074704-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What specific topological features of the 140-node graph modulate the rate of flux decline under small damping increases?

- [PP-2026-02-12-cortex-CX-20260212-074704-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What is the microscopic mechanism underlying the abrupt phonon mode collapse at the critical damping threshold?

- [PP-2026-02-12-cortex-CX-20260212-074704-h-006-dt.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-006-dt.md)
  - Question: Does dt compress time-to-failure in headless sol-core as it does in the dashboard?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the invariance of the collapse point hold under more extensive topology modifications or in different graph configurations?

- [PP-2026-02-12-cortex-CX-20260212-074704-h-007-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-007-damping.md)
  - Question: How does damping affect entropy distribution and basin selection?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Can the phase transition be characterized analytically or via spectral theory to predict the critical damping value?

- [PP-2026-02-12-cortex-CX-20260212-074704-h-012-topology.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-074704-h-012-topology.md)
  - Question: At what value of topology does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Can the invariance of the collapse threshold be proven analytically for arbitrary topology modifications?

## Cortex Session: CX-20260212-082639 (consolidated 2026-02-12)

- [PP-2026-02-12-cortex-CX-20260212-082639-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the turbulent regime (damping 0–10) contain any internal micro-transitions detectable only at higher resolution or with alternative observables?

- [PP-2026-02-12-cortex-CX-20260212-082639-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: How do flux and mass decay rates scale with damping within the turbulent regime, and are these rates topology-dependent?

- [PP-2026-02-12-cortex-CX-20260212-082639-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the monotonic decline in entropy and flux observed in the low-damping regime persist up to the transition zone (damping 10–15), or does it platea

- [PP-2026-02-12-cortex-CX-20260212-082639-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What specific topological features of the 140-node graph modulate the rate of flux decline under small damping increases?

- [PP-2026-02-12-cortex-CX-20260212-082639-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What is the microscopic mechanism underlying the abrupt phonon mode collapse at the critical damping threshold?

- [PP-2026-02-12-cortex-CX-20260212-082639-h-006-dt.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-006-dt.md)
  - Question: Does dt compress time-to-failure in headless sol-core as it does in the dashboard?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does the invariance of the collapse point hold under more extensive topology modifications or in different graph configurations?

- [PP-2026-02-12-cortex-CX-20260212-082639-h-007-damping.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-007-damping.md)
  - Question: How does damping affect entropy distribution and basin selection?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Can the phase transition be characterized analytically or via spectral theory to predict the critical damping value?

- [PP-2026-02-12-cortex-CX-20260212-082639-h-012-topology.md](solKnowledge/proof_packets/PP-2026-02-12-cortex-CX-20260212-082639-h-012-topology.md)
  - Question: At what value of topology does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Can the invariance of the collapse threshold be proven analytically for arbitrary topology modifications?

## Cortex Session: CX-20260216-063358 (consolidated 2026-02-16)

- [PP-2026-02-16-cortex-CX-20260216-063358-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-16-cortex-CX-20260216-063358-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-02-16-cortex-CX-20260216-063358-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-16-cortex-CX-20260216-063358-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-02-16-cortex-CX-20260216-063358-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-16-cortex-CX-20260216-063358-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260217-013501 (consolidated 2026-02-17)

- [PP-2026-02-17-cortex-CX-20260217-013501-h-001-c_press.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-013501-h-001-c_press.md)
  - Question: How does c_press affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: c_press: Pressure coefficient — not swept in headless

- [PP-2026-02-17-cortex-CX-20260217-013501-h-002-dt.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-013501-h-002-dt.md)
  - Question: Does dt compress time-to-failure in headless sol-core as it does in the dashboard?
  - Claim: exploratory | Sanity: PASS
  - Gap: dt: Time step — proven in dashboard, not headless

- [PP-2026-02-17-cortex-CX-20260217-013501-h-003-psi_diffusion.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-013501-h-003-psi_diffusion.md)
  - Question: How does psi_diffusion affect entropy distribution and basin selection?
  - Claim: exploratory | Sanity: PASS
  - Gap: psi_diffusion: Psi diffusion rate — never swept systematically

- [PP-2026-02-17-cortex-CX-20260217-013501-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-013501-h-004-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: conductance_gamma: Conductance psi-sensitivity — never swept

## Cortex Session: CX-20260217-062310 (consolidated 2026-02-17)

- [PP-2026-02-17-cortex-CX-20260217-062310-h-001-None.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-001-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-031340-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-032105-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-003-damping.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-003-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-032759-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-004-None.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-004-None.md)
  - Question: Do different injection targets produce distinct basin formations?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-033330-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-005-None.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-005-None.md)
  - Question: What are the canonical metric outputs for standard injection protocols?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-034732-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-006-dt.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-006-dt.md)
  - Question: Does dt compress time-to-failure in headless sol-core as it does in the dashboard?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-052151-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-007-psi_diffusion.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-007-psi_diffusion.md)
  - Question: How does psi_diffusion affect entropy distribution and basin selection?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-070748-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-008-None.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-008-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-074704-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-009-None.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-009-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-082639-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

- [PP-2026-02-17-cortex-CX-20260217-062310-h-010-None.md](solKnowledge/proof_packets/PP-2026-02-17-cortex-CX-20260217-062310-h-010-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: PP-2026-02-12-cortex-CX-20260212-084916-h-003-None.md: has UNKNOWN fields — ['Replicating unknown']

## Cortex Session: CX-20260223-063438 (consolidated 2026-02-23)

- [PP-2026-02-23-cortex-CX-20260223-063438-h-001-damping.md](solKnowledge/proof_packets/PP-2026-02-23-cortex-CX-20260223-063438-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-02-23-cortex-CX-20260223-063438-h-002-damping.md](solKnowledge/proof_packets/PP-2026-02-23-cortex-CX-20260223-063438-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-02-23-cortex-CX-20260223-063438-h-003-None.md](solKnowledge/proof_packets/PP-2026-02-23-cortex-CX-20260223-063438-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260302-062850 (consolidated 2026-03-02)

- [PP-2026-03-02-cortex-CX-20260302-062850-h-001-damping.md](solKnowledge/proof_packets/PP-2026-03-02-cortex-CX-20260302-062850-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-03-02-cortex-CX-20260302-062850-h-002-damping.md](solKnowledge/proof_packets/PP-2026-03-02-cortex-CX-20260302-062850-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-03-02-cortex-CX-20260302-062850-h-003-None.md](solKnowledge/proof_packets/PP-2026-03-02-cortex-CX-20260302-062850-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260309-063136 (consolidated 2026-03-09)

- [PP-2026-03-09-cortex-CX-20260309-063136-h-001-damping.md](solKnowledge/proof_packets/PP-2026-03-09-cortex-CX-20260309-063136-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-03-09-cortex-CX-20260309-063136-h-002-damping.md](solKnowledge/proof_packets/PP-2026-03-09-cortex-CX-20260309-063136-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-03-09-cortex-CX-20260309-063136-h-003-None.md](solKnowledge/proof_packets/PP-2026-03-09-cortex-CX-20260309-063136-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260316-064244 (consolidated 2026-03-16)

- [PP-2026-03-16-cortex-CX-20260316-064244-h-001-damping.md](solKnowledge/proof_packets/PP-2026-03-16-cortex-CX-20260316-064244-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-03-16-cortex-CX-20260316-064244-h-002-damping.md](solKnowledge/proof_packets/PP-2026-03-16-cortex-CX-20260316-064244-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-03-16-cortex-CX-20260316-064244-h-003-None.md](solKnowledge/proof_packets/PP-2026-03-16-cortex-CX-20260316-064244-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260323-063706 (consolidated 2026-03-23)

- [PP-2026-03-23-cortex-CX-20260323-063706-h-001-damping.md](solKnowledge/proof_packets/PP-2026-03-23-cortex-CX-20260323-063706-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-03-23-cortex-CX-20260323-063706-h-002-damping.md](solKnowledge/proof_packets/PP-2026-03-23-cortex-CX-20260323-063706-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-03-23-cortex-CX-20260323-063706-h-003-None.md](solKnowledge/proof_packets/PP-2026-03-23-cortex-CX-20260323-063706-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260330-064835 (consolidated 2026-03-30)

- [PP-2026-03-30-cortex-CX-20260330-064835-h-001-damping.md](solKnowledge/proof_packets/PP-2026-03-30-cortex-CX-20260330-064835-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-03-30-cortex-CX-20260330-064835-h-002-damping.md](solKnowledge/proof_packets/PP-2026-03-30-cortex-CX-20260330-064835-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-03-30-cortex-CX-20260330-064835-h-003-None.md](solKnowledge/proof_packets/PP-2026-03-30-cortex-CX-20260330-064835-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260406-064925 (consolidated 2026-04-06)

- [PP-2026-04-06-cortex-CX-20260406-064925-h-001-damping.md](solKnowledge/proof_packets/PP-2026-04-06-cortex-CX-20260406-064925-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-04-06-cortex-CX-20260406-064925-h-002-damping.md](solKnowledge/proof_packets/PP-2026-04-06-cortex-CX-20260406-064925-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-04-06-cortex-CX-20260406-064925-h-003-None.md](solKnowledge/proof_packets/PP-2026-04-06-cortex-CX-20260406-064925-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?

## Cortex Session: CX-20260413-065651 (consolidated 2026-04-13)

- [PP-2026-04-13-cortex-CX-20260413-065651-h-001-damping.md](solKnowledge/proof_packets/PP-2026-04-13-cortex-CX-20260413-065651-h-001-damping.md)
  - Question: At what value of damping does the system behavior qualitatively change?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: Does basin migration (RhoMaxNode 132→43) at damping=0.5 signal the beginning of a topological reorganization?

- [PP-2026-04-13-cortex-CX-20260413-065651-h-002-damping.md](solKnowledge/proof_packets/PP-2026-04-13-cortex-CX-20260413-065651-h-002-damping.md)
  - Question: How does damping affect entropy, flux, and mass over 200 steps?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: What happens in the unexplored gap between damping=0.5 and the known critical threshold?

- [PP-2026-04-13-cortex-CX-20260413-065651-h-003-None.md](solKnowledge/proof_packets/PP-2026-04-13-cortex-CX-20260413-065651-h-003-None.md)
  - Question: Can headless sol-core reproduce: ?
  - Claim: exploratory | Sanity: PASS
  - Gap: Open Q: At what timescale does damping sensitivity transition from sub-linear to the steeper scaling observed at 300 steps?
