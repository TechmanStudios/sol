---
name: SOL Chat Consolidation
description: Compress long sessions into canonical artifacts without losing auditability.
---

# Skill: Chat Consolidation (Long Chat → Canonical Artifacts)
## Purpose
Compress a long session into RN/RD + master-log inserts without losing auditability.

## Inputs
- chat text
- any run IDs and filenames mentioned
- target outputs (RN/RD, master insert, next primer)

## Procedure
1) Extract all run IDs, filenames, and parameter values.
2) Build chronology with [UNKNOWN] where missing.
3) Separate findings into tagged blocks.
4) Create proof packets only where evidence is explicit.
5) Produce artifact inventory (local vs external).
6) Provide promotion checklist + next actions.

## Outputs
- RN/RD note
- master-log insert snippet
- manifest update suggestions

## Gotchas
- never “complete” missing run settings from memory
