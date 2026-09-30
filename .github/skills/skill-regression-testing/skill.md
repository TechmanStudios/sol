---
name: SOL Regression Testing
description: Ensure dashboard/harness changes do not rewrite empirical reality.
---

# Skill: Regression Testing (Science-Safe Refactors)
## Purpose
Ensure dashboard/harness changes do not rewrite empirical reality.

## Inputs
- a stable benchmark protocol
- old vs new dashboard/harness versions

## Procedure
1) Run benchmark on old version (or use stored benchmark outputs).
2) Run benchmark on new version under identical invariants.
3) Compare:
   - key distributions
   - timing ranges
   - detector behavior/clipping
4) If differences appear:
   - classify: bug / intended change / incidental drift
   - document in engineering deltas and update claims if needed

## Outputs
- regression report (pass/fail + evidence)
- updated release notes/behavioral delta

## Gotchas
- mixing baseline modes between versions invalidates the regression
