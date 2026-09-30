---
name: SOL Detector Validation
description: Ensure detectors measure reality, not manufactured thresholds.
---

# Skill: Detector Validation (Window/Clipping Checks)
## Purpose
Ensure detectors are measuring reality, not manufacturing thresholds.

## Inputs
- detector definition and window positions (or code reference)
- repTransition curve or timing trace exports

## Procedure
1) Identify potential clipping:
   - detector always fires early/late
   - saturates to max/min tick
2) Shift windows (or adjust “lateStartTick”) and re-run a small control block.
3) Confirm key results (threshold location, winner distribution) are stable to window shifts.
4) If unstable:
   - mark result provisional
   - revise detector or pick a more robust metric

## Outputs
- detector sanity check section in analysis report
- a stability statement: “stable/unstable to window shifts”

## Gotchas
- claiming ridge sharpness when detector is saturating
