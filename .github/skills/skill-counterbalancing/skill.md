---
name: SOL Counterbalancing (AB/BA)
description: Detect order/history confounds with balanced run ordering.
---

# Skill: Counterbalancing (AB/BA) for Order Effects
## Purpose
Test whether history/order drives differences instead of the intended knob.

## Inputs
- two conditions A and B (or pass labels)
- protocol schedule

## Procedure
1) Run AB: execute A then B with matched dwell and identical invariants.
2) Run BA: execute B then A under the same rules.
3) Compare:
   - A vs B within AB
   - A vs B within BA
   - A(AB) vs A(BA), B(AB) vs B(BA)
4) Interpret:
   - stable A/B across order → label effect
   - flips with order → history effect
   - macro stable but timing shifts → subtle drift

## Outputs
- a small AB/BA comparison table
- a confound verdict in analysis report

## Gotchas
- mismatched dwell time breaks the test
- baseline restore not identical breaks the test
