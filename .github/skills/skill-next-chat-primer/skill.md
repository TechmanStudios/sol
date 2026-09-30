---
name: SOL Next Chat Primer
description: Start a fresh chat with minimal context drift and clean continuity.
---

# Skill: Next Chat Primer (Continuity Starter)
## Purpose
Start a new chat session with clean context and minimal drift.

## Inputs
- last run series summary
- open questions
- next planned experiments

## Procedure
1) Write a compact “checkpoint” header:
   - last completed run series
   - what is believed stable
   - what remains unknown
2) Include the next run plan (IDs, protocols, invariants).
3) Include guardrails:
   - baseline discipline
   - evidence vs interpretation tags
   - [UNKNOWN] rule

## Outputs
- next-chat start prompt + next steps

## Gotchas
- avoid including speculative mechanism as fact
