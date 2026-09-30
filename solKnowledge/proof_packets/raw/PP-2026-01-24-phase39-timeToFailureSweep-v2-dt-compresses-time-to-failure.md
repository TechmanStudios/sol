# Proof Packet — Phase 3.9 time-to-failure sweep v2 (dt compresses time-to-failure)

## CLAIM
In Phase 3.9 time-to-failure sweep v2 (1200-step runs), dt=0.08 produces zero failures while dt=0.12 and dt=0.16 produce 100% failures via the same runaway mean-pressure detector under matched signature controls.

## EVIDENCE
- Run IDs:
  - Sweep is aggregated in the export file; per-condition runs are represented as rows with `mode`, `dtTest`, and `damping`.
- Export files:
  - `solData/testResults/sol_phase39_timeToFailureSweep_v2_dt0.08-0.12-0.16_d2-3-4-5-6_steps1200_id64_20260104_180741.csv`
- Key metrics (from the export above; columns: `mode`, `dtTest`, `damping`, `failed`, `failStep`, `failReason`):
  - `mode=noPulse`
    - dt=0.08: failures `0/5` (damping 2–6)
    - dt=0.12: failures `5/5` with `failReason = sustained meanP>0.5 (20)`; `failStep` min/mean/max = `1107 / 1119.0 / 1133`
    - dt=0.16: failures `5/5` with `failReason = sustained meanP>0.5 (20)`; `failStep` min/mean/max = `547 / 640.6 / 685`
  - `mode=pulse100` (same dt × damping grid)
    - dt=0.08: failures `0/5`
    - dt=0.12: failures `5/5` with `failReason = sustained meanP>0.5 (20)`; `failStep` min/mean/max = `1103 / 1119.8 / 1132`
    - dt=0.16: failures `5/5` with `failReason = sustained meanP>0.5 (20)`; `failStep` min/mean/max = `444 / 618.4 / 681`
- Notes about detector windows/definitions:
  - The detector is encoded in `failReason` as `sustained meanP>0.5 (20)`.

## ASSUMPTIONS
- baselineMode:
  - Assumed baseline snapshot/restore was used (called out as a Phase 3.9 control), but not recorded as a column in this export.
- dt/damp/pressC/capLawHash:
  - `dtTest` is explicitly recorded as 0.08/0.12/0.16.
  - `damping` is explicitly recorded as 2–6.
  - `pressC forced = 20` is asserted in the Phase 3.9 design note; not recorded as a column in this export.
- dashboard/harness version:
  - Not recorded in the export; treat as unknown.
- detector window positions:
  - Detector uses a sustained window length of 20 steps (from `failReason`).
- session conditions:
  - Assumed single sweep executed under a consistent baseline key and signature controls.

## FALSIFY
- Re-run the same dt × damping grid with the same drift signature and failure detector.
- Falsification signature: any condition at dt≥0.12 that reaches 1200 steps with `failed=0` under the same detector and controls.

## STATUS
robust

## SOURCES
- [rd25.md](solKnowledge/working/rd25.md#L30)
