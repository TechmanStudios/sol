# SolTech Scaffold

This folder contains the SolTech structure-manager scaffold based on the VS Code custom agents + instructions + prompts + skills structure referenced in the YouTube videos.

## Structure
- .github/instructions/: project-level custom instructions
- .github/prompts/: reusable prompt files
- .github/agents/: custom agents and subagents
- .github/skills/: bundled skills with scripts and templates

## Primary agent
- SolTech-StructureManager (see .github/agents/soltech-structure-manager.agent.md)

## Primary skill
- soltech-structure-manager-knowledge

## Agent roster

SolTech agents:
- SolTech-StructureManager (primary orchestrator)
- soltech-research (source reading + requirement extraction)
- soltech-architect (system design + file structure)
- soltech-implementer (small, testable code changes)

SOL lab agents:
- sol-lab-master (orchestrates SOL research workflows)
- sol-experiment-runner (executes protocols + run bundles)
- sol-data-analyst (sanity checks + derived metrics)
- sol-knowledge-compiler (audit-ready knowledge compilation)

Utility agents (consolidated from aiAgents):
- continuity (repo-backed memory across chat sessions)
- sol-auto-mapper (automated SOL manifold parameter sweeps)

Handoff graph (typical):
- SolTech-StructureManager → sol-lab-master → sol-experiment-runner → sol-data-analyst → sol-knowledge-compiler
- SolTech-StructureManager → continuity (session memory)
- SolTech-StructureManager → sol-auto-mapper (mapping sweeps)

## Instruction set
- sol-style-and-epistemics.md
- sol-proof-packet-standard.md
- sol-baseline-discipline.md
- sol-artifact-provenance.md

## Skills (consolidated)
SOL domain skills:
- skill-artifact-manifest-update, skill-baseline-control, skill-canonicalizer-design
- skill-chat-consolidation, skill-claim-ledger-promotion, skill-counterbalancing
- skill-csv-analysis-python, skill-detector-validation, skill-hysteresis-measurement
- skill-next-chat-primer, skill-protocol-design, skill-regression-testing
- skill-schema-versioning, skill-threshold-bracketing
- soltech-structure-manager-knowledge

Utility skills (from aiAgents):
- continuity-memory (repo-backed session memory + CLI)
- skill-candidate-pipeline (propose → evidence → promote workflow)
- sol-auto-mapper (automated parameter sweep runner + organizer)

## Supporting tools
- tools/continuity/ — continuity CLI (init, add, search, tail, refresh)
- tools/graph_github_kit.py — kit graph generator
- tools/dashboard_automation/ — dashboard test tooling

## Primary reference (temporary)
Raw source corpus:
- knowledge/youtube

Derived knowledge (working + consolidated + proof packets):
- solKnowledge/

## Next steps
- Add the full SolTech reference corpus when available.
- Iterate on agent prompts and skills as Sol engine workflows evolve.
- Add specialized “lab technician” agents for focused R&D workflows.
