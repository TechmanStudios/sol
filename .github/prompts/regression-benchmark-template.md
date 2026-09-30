---
name: SOL Regression Benchmark Template
description: Template to define regression benchmarks that detect behavior drift after dashboard or harness changes.
model: GPT-5.2
agent: sol-lab-master
---

# REGRESSION BENCHMARK (SOL)

## Purpose
Confirm that dashboard/harness changes did not rewrite behavior.

## Benchmark protocol
- baselineModeUsed:
- invariants (dt/damp/pressC/capLawHash):
- injection schedule:
- reps:
- detector windows:

## Expected outputs
- expected range of key metrics:
- expected winner distributions:
- expected timing ranges:

## Pass/fail criteria
- fail if:
  - metric definitions changed without documentation
  - output distributions drift beyond tolerance bands
  - detector clipping appears where it didn’t before
