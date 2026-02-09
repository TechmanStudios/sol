# SolTech-StructureManager Project Instructions

These instructions describe the Sol engine workspace and how SolTech-StructureManager agents should work inside it.
SolTech-StructureManager acts as the structure manager that orchestrates agent composition and workflows.

## General working style
- Prefer small, testable changes.
- Keep experiments isolated; promote reusable code into `tools/`.
- Document a minimal run recipe (inputs → steps → expected outputs).

## Project scope
- Project name: Sol Engine (Sol)
- Primary goal: research and development workflows for the Sol engine and related tooling.
- Source corpus (temporary): knowledge/youtube (YouTube transcript corpus pulled on 2026-01-23).
- Derived knowledge home: solKnowledge (working notes, consolidations, and proof packets).
- Future corpus: to be added later (leave room for expansion).

## Operating rules
- Prefer existing conventions in this repository.
- When referencing sources, cite files from knowledge/youtube by file path and include timestamps when present in the transcript.
- Keep changes small, testable, and scoped to a single step where possible.

## Agent instruction model (from YouTube reference)
- System prompt order: base system rules → custom instructions → custom agent instructions (agents are applied last in the system prompt).
- Prompt files: injected into the user prompt (not the system prompt) and used as reusable, short workflows.
- Skills: progressively loaded; only name/description appears in the first pass, and the agent loads skill contents/scripts/templates only when needed.

## When to use what
- Instructions: always-on project guidance and constraints.
- Prompt files: reusable short prompts or workflows.
- Custom agents: persistent behavior/workflow overrides.
- Skills: bundled instruction + scripts/templates for specialized tasks.

## Project layout conventions
- .github/instructions: project-level instructions (this file).
- .github/agents: agents and subagents.
- .github/prompts: reusable prompt files and templates.
- .github/skills: skill bundles (skill.md + scripts + templates).
- tools/: reusable CLI scripts (continuity, graph generation, etc.).
- knowledge/continuity/: repo-backed memory (project_memory.md + session_notes.jsonl).
- knowledge/skill_candidates/: staging area for candidate skills before promotion.

## Workflow guidance
- Start with planning (prompt file) → generate an implementation checklist → implement in small, testable steps.
- If context grows large, prefer starting a fresh chat session and re-attaching the minimal necessary artifacts.

## Current reference corpus
- knowledge/youtube/youtube_0XoXNG65rfg_en_auto.md
- knowledge/youtube/youtube_fabAI1OKKww_en_auto.md

## Derived knowledge location
- solKnowledge/working: active investigations and scratchpads
- solKnowledge/consolidated: curated summaries and canonical artifacts
- solKnowledge/proof_packets: master LEDGER.md + domains/ for domain packets + raw/ for audit trail

## Notes
- If you need more context, ask for clarification or request additional sources.
- Specialized “lab technician” agents will be added later for focused R&D tasks.
