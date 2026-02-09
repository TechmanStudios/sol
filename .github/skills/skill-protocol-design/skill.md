---
name: SOL Protocol Design
description: Design experiments that isolate causality and produce promotable outputs.
---

# Skill: Protocol Design (SOL)
## Purpose
Design an experiment that isolates causality and produces outputs suitable for claim promotion.

## Inputs
- one-sentence question
- candidate knobs
- invariants (or [UNKNOWN])
- constraints (runtime, reps, file size)

## Procedure
1) Translate the question into a measurable dependent variable:
   - threshold? timing? winner probability? basin selection?
2) Choose ONE primary knob (unless mapping a control surface).
3) Declare invariants explicitly:
   - dt, damp, pressC, capLawHash, baseline mode, detector windows
4) Add controls:
   - baseline control (restore vs hard reset if needed)
   - order control (AB/BA if order effects plausible)
   - detector window shift check
   - cross-session repeat if stability is a goal
5) Write step-by-step protocol with labeling rules.
6) Specify expected exports and derived tables.
7) Define falsifiers (what would disprove your intended interpretation).

## Outputs
- experiment protocol doc using .github/prompts/experiment-protocol-template.md
- run plan with labeling and export expectations

## Gotchas
- sweeping two knobs without declaring a surface map
- forgetting baseline mode (fatal)
- detector clipping manufacturing thresholds

## Example
Design a ridge scan over multB with 40 reps/cell, fixed dt/damp/pressC, AB/BA order, window shift check.
