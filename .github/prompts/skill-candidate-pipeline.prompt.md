# Skill Candidate Pipeline (Reusable)

Use this workflow when an agent observes a stable, repeatable pattern and wants to package it as a *candidate skill* without modifying authoritative skills.

Rules
- Do NOT edit existing `.github/skills/*` directly.
- Create a candidate folder and provide evidence + trigger.
- Keep it short and auditable: one candidate per insight.

Steps
1) Name the candidate
- Create a slug (kebab-case), e.g. `ridge-band-detector`.
- Provide a one-line description.

2) Create the candidate folder
- Use the CLI:
  - `python .github/skills/skill-candidate-pipeline/scripts/create_skill_candidate.py --dest knowledge/skill_candidates --slug <slug> --title "<Title>" --description "<desc>" --domain general --tag <tag>`

3) Fill in evidence
- Add links to raw bundles/manifests/tables.
- State how to reproduce the observation.

4) Define the trigger
- Write a crisp, testable condition.
- Include at least one failure mode / counterexample.

5) Propose promotion
- Summarize: why this should become a real skill, where it applies, and what it would automate.
- Do NOT promote automatically; request review.

SOL research note
- For SOL-specific candidates, set `--dest knowledge/skill_candidates` and `--domain sol`.
