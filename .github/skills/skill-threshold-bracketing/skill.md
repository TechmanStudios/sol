---
name: SOL Threshold Bracketing
description: Bracket transition thresholds and map ridges with reproducible runs.
---

# Skill: Threshold Bracketing (Ridge Mapping)
## Purpose
Estimate where a probability transition occurs without overfitting.

## Inputs
- table of P(outcome) vs knob (e.g., multB)
- rep counts per cell

## Procedure
1) Sort knob levels ascending.
2) Identify bands:
   - LOW band: P near 0
   - HIGH band: P near 1
   - TRANSITION band: between them
3) Define a bracket:
   - lower_bound = max knob where P <= p_low
   - upper_bound = min knob where P >= p_high
   (choose p_low/p_high like 0.2/0.8 or 0.1/0.9 depending on noise)
4) Report:
   - bracket range
   - slope proxy (delta P / delta knob across transition)
   - sample sizes and uncertainty

## Outputs
- threshold bracket table + statement in analysis report

## Gotchas
- detectors saturating makes bracketing meaningless
