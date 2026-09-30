---
name: SOL Analysis Request Template
description: Structured request for analyzing SOL exports into sanity checks and derived results.
model: GPT-5.2
agent: sol-data-analyst
---

# ANALYSIS REQUEST (SOL)

## What I want answered
- primary question:
- secondary questions:

## Inputs provided
- summary export:
- busTrace export:
- repTransition export:
- run bundle:
- detector definitions/windows: (or [UNKNOWN])

## Constraints
- prioritize: (threshold bracket | timing | winner probability | basin selection)
- required plots: (yes/no)
- output formats: (Markdown report + derived CSV tables + optional Python script)

## Required sanity checks
- invariants check
- sample size check
- detector clipping check
- order-effect confounds check (if applicable)
