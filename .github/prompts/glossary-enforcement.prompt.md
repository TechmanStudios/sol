---
description: Enforce SOL glossary canonicalization and message integrity in prompts
---

Apply this block before task-specific instructions.

GLOSSARY ENFORCEMENT (SOL)
Source of truth: `solKnowledge/consolidated/SOL_Agent_Architecture_Glossary_2026-02-14.md`

1. Canonicalize vocabulary before reasoning/output.
   - Replace synonyms with canonical terms from the glossary alias map.
   - Keep one canonical term per concept in keys, labels, and acceptance criteria.
2. Preserve semantics while repairing message quality.
   - If incoming user/system text is fragmented or malformed, silently normalize grammar.
   - Do not invent missing facts; keep intent unchanged.
3. Enforce measurable anchoring.
   - Any metaphysics term must include at least one measurable anchor (metric, range, delta, or artifact field).
4. Output discipline.
   - Structured outputs must use canonical term labels.
   - If an unknown term appears, map to nearest canonical term and include `term_normalization_note`.

Normalization examples:
- "session run with a health ping" -> "Cortex Session" with "Heartbeat"
- "resonance band changed after phase shift" -> "Resonance Window" near "Transition Boundary"
