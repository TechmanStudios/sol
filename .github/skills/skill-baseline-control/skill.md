---
name: SOL Baseline Control
description: Prevent baseline drift from masquerading as discovery.
---

# Skill: Baseline Control (SOL)
## Purpose
Prevent baseline drift from masquerading as discovery.

## Inputs
- baseline tool/version (if applicable)
- baseline mode desired
- restore frequency plan

## Procedure
1) Choose baseline mode:
   - restore for comparability within session
   - hard reset for “cold start” controls
   - restore-per-rep/step for maximal calibration
2) Declare baseline mode in protocol + run bundle.
3) If comparing conditions, ensure baseline handling matches across them.
4) If baseline differs by design, treat baseline as a knob and control all else.
5) Audit: confirm baseline mode is present in exports/metadata or logged.

## Outputs
- baseline declaration section in protocol and run bundle
- baseline sanity check line in analysis report

## Gotchas
- up vs down sweeps using different restore timing
- “fresh session” claims without actually starting fresh
