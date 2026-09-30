# SOL Baseline Discipline (Calibration Ritual)

## Why baseline matters
Baseline handling is the biggest lever on repeatability. Treat it like calibrating lab instruments.

## Baseline modes (declare explicitly)
- restore: restore a stored snapshot between conditions or runs
- hard reset: reset to a cold start state per condition/run
- restore-per-step / restore-per-rep: higher-frequency restore discipline

If baseline handling changes, it is an independent variable.

## Required baseline metadata
Every run bundle must declare:
- baselineModeUsed: (restore/hard reset/etc.)
- baselineSnapshotID or timestamp if applicable
- restore frequency (between blocks? between reps? between steps?)

## Baseline sanity checks
Before analysis/promotion:
- confirm baseline mode is consistent across compared conditions
- if not consistent, treat differences as confounded unless explicitly studied

## Practical warning
Hysteresis claims die instantly if baseline handling differs between up vs down sweeps.
