---
name: SOL Canonicalizer Design
description: Create repeatable state-prep routines that pin readouts or select basins.
---

# Skill: Canonicalizer Design (State-Prep Pipelines)
## Purpose
Create a repeatable state-prep routine that pins a readout or selects a basin reliably.

## Inputs
- target readout metric (e.g., late-phase tick180 node)
- candidate prep steps (pulses, holds, settle times)
- baseline policy

## Procedure
1) Treat state-prep as a trajectory (anneal/settle/quench), not a scalar reset.
2) Draft a pipeline:
   - baseline restore
   - precondition pulse(s)
   - lock pulse(s)
   - settle windows
   - measurement window
3) Validate:
   - within-session repeatability (blocks)
   - cross-session repeatability (fresh sessions)
   - basin addressability (can choose LOW vs HIGH intentionally)
4) Write a proof packet only after controls pass.

## Outputs
- canonicalizer protocol + validation table
- proof packet(s) for stability and addressability

## Gotchas
- “works once” is not canonicalization
- direction-conditional behavior must be explicitly documented
