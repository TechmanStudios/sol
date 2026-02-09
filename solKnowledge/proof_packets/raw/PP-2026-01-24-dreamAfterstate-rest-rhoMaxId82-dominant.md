# PP-2026-01-24 — Dream Afterstate (dt=0.12, d=4): rest-phase rhoMaxId is dominated by 82

## CLAIM
In the dream-afterstate run `sol_dream_afterstate_dt0.12_d4_2026-01-06T04-10-36-119Z.csv`, during the `rest` phase, `rhoMaxId` equals 82 in 301/317 samples (~94.95%).

## EVIDENCE
- Run IDs:
  - (Not recorded in the export filename; this packet is anchored to export filenames + in-file parameters.)
- Export files:
  - `solData/testResults/sol_dream_afterstate_dt0.12_d4_2026-01-06T04-10-36-119Z.csv`
  - Supporting context (not required for the claim): `solData/testResults/sol_rest_watch_90s_200ms_2026-01-06T03-53-25-885Z.csv`
- Key metrics (values + where in the file):
  - Filter: rows where `phase == "rest"` (column `phase`).
    - Sample count: 317 rows, spanning `tSec` 0.01 → 119.87 (column `tSec`).
    - `rhoMaxId` counts (column `rhoMaxId`):
      - 82: 301 rows
      - 90: 14 rows
      - 14: 1 row
      - 27: 1 row
  - Parameters recorded in-file for the `rest` phase:
    - `dt = 0.12` (column `dt`, constant across rest-phase rows)
    - `damping = 4` (column `damping`, constant across rest-phase rows)
    - `pressC = 20` (column `pressC`, constant across rest-phase rows)
  - Supporting context (rest-watch series): in `sol_rest_watch_90s_200ms_2026-01-06T03-53-25-885Z.csv`, `rhoMaxId` is 82 in 248/248 samples across `tSec` 0.0 → 89.82.
- Notes about detector windows/definitions:
  - Not applicable; this packet uses direct per-sample maxima identifiers (`rhoMaxId`).

## ASSUMPTIONS
- `rhoMaxId` is the index of the maximum rho component per sample, and its semantics are stable across exports.
- The `rest` phase in `sol_dream_afterstate_dt0.12_d4_2026-01-06T04-10-36-119Z.csv` corresponds to the intended afterstate/rest observation window.
- No additional conditioning (baseline mode, dashboard build) is required for interpreting `rhoMaxId` dominance within a single export.

## FALSIFY
- Run a new dream-afterstate session at the same `dt=0.12`, `damping=4`, `pressC=20`, export the same columns.
- Expected failure signature: within the `rest` phase, `rhoMaxId=82` is not the dominant id (e.g., <50% of samples), or dominance is replaced by a different stable id across the rest window.
- How it would appear in exports: `rhoMaxId` counts computed over `phase==rest` show a different top id or substantially different fraction.

## STATUS
provisional
