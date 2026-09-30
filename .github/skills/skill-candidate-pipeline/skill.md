name: Skill Candidate Pipeline
description: Proposes new reusable skills/prompts from run evidence via an auditable candidate→promotion workflow (no silent self-modification).

Goal
- Let agents capture emergent insights as *candidate skills* without mutating authoritative skills.
- Keep everything traceable: candidate → evidence → promotion decision.

Core rules
- Candidates go under a dedicated staging area (default): `knowledge/skill_candidates/_candidates/<slug>/`.
- Agents may create candidate folders and drafts, but should not write directly into `.github/skills/<official-skill>/`.
- Promotion is explicit (human or reviewer-agent): copy/move from `_candidates` to official skill locations.

What a candidate contains
- `skill.md` — draft skill definition (name/description + intended use)
- `EVIDENCE.md` — links to raw data, run bundles, summaries
- `TRIGGER.md` — the data-defined condition that caused the candidate to be proposed
- `candidate_manifest.json` — metadata (timestamps, tags, source runs)

Recommended workflow
1) During a run or analysis, detect a stable, repeatable pattern.
2) Create a candidate folder with the CLI:
   - `python .github/skills/skill-candidate-pipeline/scripts/create_skill_candidate.py --dest knowledge/skill_candidates --slug <slug> --title "..." --description "..." --domain general`
3) Fill in `EVIDENCE.md` with file links to raw bundles and any derived tables.
4) Fill in `TRIGGER.md` with a crisp criterion and counterexamples.
5) Promote only after review.

SOL-specific staging (this research project)
- Use: `knowledge/skill_candidates/_candidates/<slug>/`
- This keeps SOL discoveries co-located with proof packets and consolidated research.

References
- scripts/create_skill_candidate.py
- templates/*
