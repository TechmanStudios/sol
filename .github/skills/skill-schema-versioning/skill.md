---
name: SOL Schema Versioning
description: Prevent silent schema/semantic drift in exports and detectors.
---

# Skill: Schema Versioning (Instrument Change Discipline)
## Purpose
Avoid silent changes in CSV columns/semantics that invalidate comparisons.

## Inputs
- old export schema (columns/definitions)
- new export schema
- dashboard/harness version changes

## Procedure
1) Diff column sets:
   - added/removed/renamed
2) For shared columns, verify semantics didn’t change (units, meaning, windowing).
3) If semantics changed:
   - bump schema version name
   - document behavioral delta
   - run regression benchmark protocol
4) Update analysis scripts to detect schema version.

## Outputs
- schema change log
- updated protocol notes and regression benchmark results

## Gotchas
- “same column name” does not guarantee same meaning
