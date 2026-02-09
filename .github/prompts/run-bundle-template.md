---
name: SOL Run Bundle Template
description: Template to record a run series (identity, invariants, knobs, protocol, exports, deviations) for audit.
model: GPT-5.2
agent: sol-experiment-runner
---

# RUN BUNDLE — <seriesName> (<date>)

## Identity
- seriesName:
- runIDs:
- dashboardVersion:
- harnessSchema:
- baselineModeUsed:
- operator:

## Question
(one sentence)

## Invariants (must be fixed)
- dt:
- damp:
- pressC:
- capLawHash:
- detectorWindows:
- repsPerCell:

## Knobs (independent variables)
- …

## Protocol (step-by-step)
1)
2)
3)

## Exports
- MASTER_summary:
- MASTER_busTrace:
- repTransition_curve:
- other:

## Deviations / Incidents
- (none) OR list changes, crashes, restarts, manual interventions

## Notes
- anything that will matter during analysis/compilation

## External artifact registration
If any exports are stored outside the repo, list:
- externalArchivePath:
- manifestEntryNeeded: yes/no
- referencedPatterns:
