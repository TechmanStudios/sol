# Phase-layer ridge bands (locked) — 2026-01-27

Purpose: lock a stable, audit-backed definition for the two micro-ridge neighborhoods around damping ≈ 12.888 (step = 5e-05), using high-rep interleaved confirmations.

## Definition

**Ridge band** here means: a short damping interval where adjacent sample points (spaced by 5e-05) show consistent *alternating* behavior in pass@budget and boundary scoring (passJump ≈ 0.2), across high replication.

- Budget definition: pass@budget is evaluated at ≥1200 steps.
- Replication definition: 120 runs/point, interleaved via chunk=5.

## Ridge band A (lower micro-ridge neighborhood)

Range: **12.88765 → 12.88780** (step 5e-05)

Observed lanes (pass@budget ≥1200):

- Higher lane: 12.88765 and 12.88775 (pass@budget = 0.8)
- Lower lane: 12.88770 and 12.88780 (pass@budget = 0.6)

Evidence batch:
- solData/testResults/phase_layers/adaptive_20260127-034332-792/
  - phase_layer/phase_layer_trace_report.md
  - phase_layer/phase_layer_trace_agg.csv
  - adaptive_summary.md

Detected boundaries (passJump≈0.2) in that batch:
- 12.88765 → 12.88770
- 12.88770 → 12.88775
- 12.88775 → 12.88780

## Ridge band B (upper micro-ridge neighborhood)

Range: **12.88790 → 12.88810** (step 5e-05)

Observed lanes (pass@budget ≥1200):

- Higher lane: 12.88790 and 12.88805 (pass@budget = 0.6)
- Lower lane: 12.88795, 12.88800, 12.88810 (pass@budget = 0.4)

Evidence batch:
- solData/testResults/phase_layers/adaptive_20260127-040547-907/
  - phase_layer/phase_layer_trace_report.md
  - phase_layer/phase_layer_trace_agg.csv
  - adaptive_summary.md

Detected boundaries (passJump≈0.2) in that batch:
- 12.88790 → 12.88795
- 12.88800 → 12.88805
- 12.88805 → 12.88810

## Precision / slider audit note

These ridge-band runs are *physics-direct* damping injections (not slider-driven).

Practical implication:
- UI slider quantization can make manual “precise” damping impossible, but automation passes damping directly into the engine and the traces carry provenance fields to confirm it.
