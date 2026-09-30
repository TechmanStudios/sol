# SOL Universe Agent Kit (v0.1)
*A long-form, copy/paste-ready bundle of **agents**, **instructions**, **prompts**, and **skills** for running SOL as a lab-grade program inside VS Code.*

This document is designed so you can:
- Copy each **FILE block** into your repo under `.github/agents/`, `.github/instructions/`, `.github/prompts/`, `.github/skills/`
- Keep all agents aligned on the same epistemics + provenance rules
- Chain: **Runner → Analyst → Compiler**, with **Lab Master** orchestrating

---

## Table of Contents
1. [Repo Layout](#repo-layout)
2. [How to Use This Kit in VS Code](#how-to-use-this-kit-in-vs-code)
3. [Shared Standards](#shared-standards-instructions-files)
4. [Agents](#agents)
5. [Prompts](#prompts)
6. [Skills](#skills)
7. [Pipeline Contract](#pipeline-contract-run-bundle--analysis-pack--promotion)
8. [Appendix: Checklists and “Gotchas”](#appendix-checklists-and-gotchas)

---

## Repo Layout

Recommended structure:

```text
.github/
  agents/
    sol-lab-master.md
    sol-experiment-runner.md
    sol-data-analyst.md
    sol-knowledge-compiler.md

  instructions/
    sol-operating-charter.md
    sol-style-and-epistemics.md
    sol-proof-packet-standard.md
    sol-baseline-discipline.md
    sol-artifact-provenance.md
    sol-run-naming-and-exports.md
    sol-ui-neutral-scripting.md
    sol-progress-and-help.md
    sol-consolidation-standards.md

  prompts/
    experiment-protocol-template.md
    run-bundle-template.md
    analysis-request-template.md
    consolidation-template.md
    master-log-insert-template.md
    claim-promotion-checklist.md
    incident-report-template.md
    regression-benchmark-template.md

  skills/
    skill-protocol-design.md
    skill-baseline-control.md
    skill-counterbalancing.md
    skill-detector-validation.md
    skill-csv-analysis-python.md
    skill-threshold-bracketing.md
    skill-hysteresis-measurement.md
    skill-canonicalizer-design.md
    skill-claim-ledger-promotion.md
    skill-artifact-manifest-update.md
    skill-schema-versioning.md
    skill-regression-testing.md
    skill-chat-consolidation.md
    skill-next-chat-primer.md

How to Use This Kit in VS Code
Typical setup pattern
    Choose an agent from .github/agents/ as the active persona for a session.
    Ensure each agent “knows” the shared standards by referencing (or pasting) key instruction files from .github/instructions/.
    Use prompts from .github/prompts/ as structured input contracts to reduce drift and increase repeatability.
    Use .github/skills/ as standard operating procedures (SOPs) the agent follows when performing common tasks.

Operational flow (recommended)
    1. Lab Master drafts protocol + controls + falsifiers.
    2. Experiment Runner executes + exports + emits a Run Bundle.
    3. Data Analyst turns exports into derived tables + sanity checks.
    4. Knowledge Compiler produces RN/RD + proof packets + master-log insert + manifest updates.