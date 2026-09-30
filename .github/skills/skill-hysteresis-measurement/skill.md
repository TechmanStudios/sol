---
name: SOL Hysteresis Measurement
description: Measure up-sweep vs down-sweep differences under matched conditions.
---

# Skill: Hysteresis Measurement
## Purpose
Measure whether up-sweep and down-sweep differ under matched conditions.

## Inputs
- up-sweep probability curve vs knob
- down-sweep probability curve vs knob
- baseline and dwell details

## Procedure
1) Verify matched dwell time per step.
2) Verify baseline handling is identical between sweeps (or explicitly studied).
3) Estimate thresholds independently for up and down using bracketing.
4) Hysteresis width = threshold_down - threshold_up (sign matters; define convention).
5) Validate with order controls (AB/BA or repeated alternating sweeps).

## Outputs
- hysteresis width estimate with protocol dependence notes

## Gotchas
- mismatched dwell breaks the claim
- “session age” differences can mimic hysteresis
