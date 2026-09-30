---
name: SOL External Artifact Manifest Updates
description: Maintain traceability when bulky artifacts live outside the repo.
---

# Skill: External Artifact Manifest Updates
## Purpose
Maintain traceability when bulky artifacts live outside the repo.

## Inputs
- list of external files (paths or storage location)
- run IDs and patterns
- which writeups reference them

## Procedure
1) Add entries with:
   - artifact name/pattern
   - storage location
   - associated run IDs/series
   - brief description (what it contains)
2) Ensure each RN/RD note’s artifact inventory matches manifest coverage.
3) Reject orphan references: if a note references a file not in repo or manifest, mark [UNKNOWN] until fixed.

## Outputs
- manifest entries ready to paste

## Gotchas
- part files without a manifest can become irrecoverable
