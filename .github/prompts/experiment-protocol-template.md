---
name: SOL Experiment Protocol Template
description: Protocol template for designing repeatable SOL experiments with invariants, controls, and falsifiers.
model: GPT-5.2
agent: sol-lab-master
---

# EXPERIMENT PROTOCOL TEMPLATE (SOL)

## Identity
- seriesName:
- intendedRunIDs: [UNKNOWN if not assigned]
- dashboardVersion:
- harnessSchema:
- baselineModeUsed:

## Question (one sentence)
…

## Invariants (must remain fixed)
- dt:
- damp:
- pressC:
- capLawHash:
- detectorWindows:
- repsPerCell:
- sessionCondition: (fresh session? continued session?)

## Knobs (independent variables)
- …

## Protocol (step-by-step)
1)
2)
3)

## Controls (required)
- baseline control:
- order counterbalance (AB/BA):
- detector window shift check:
- cross-session repeat (if relevant):

## Expected Outputs (exports)
- *_MASTER_summary.csv
- *_MASTER_busTrace.csv
- *_repTransition_curve.csv

## Success Criteria
What would count as “works”?

## Falsifiers
What result would prove we’re fooling ourselves?

## Notes / Risks
- detector clipping risk:
- session drift risk:
- file size risk:
