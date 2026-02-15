# SOL Agent Routing — Soft Triggers (Heuristics)

These “soft triggers” are lightweight *conversation cues* that help route a task to the most appropriate SOL custom agent.

Important:
- Nothing is “listening” or running automatically in the background.
- This is not an event system.
- It’s simply a shared convention: when you say certain kinds of things, I will *choose* the best-fit agent (or ask a quick clarifying question if it’s ambiguous).

## Override
If you want to force a choice, just say:
- `Use agent: sol-data-analyst` (or any agent name)
- `Use SolTech-StructureManager for this`

## Disambiguation prompt (if multiple triggers apply)
If a request spans phases, I may ask:
- “Do you want this treated as a run/protocol, analysis, or promotion/proof-packet step?”

---

## Agent → Soft triggers

### sol-experiment-runner
Use when the work is about executing a protocol consistently and producing a Run Bundle.
- Keywords/phrases: “run”, “execute”, “perform the protocol”, “collect runs”, “generate a run bundle”, “sweep”, “counterbalance”, “AB/BA”, “bracket thresholds”, “hysteresis run”, “automation/runbook”.
- Typical outputs: run logs, run bundle folder/artifacts, structured run metadata.

### sol-data-analyst
Use when the work is about analysis, derived metrics, sanity checks, and compact tables/plots.
- Keywords/phrases: “analyze”, “compute metrics”, “summarize results”, “sanity check”, “statistics”, “regression”, “plot”, “CSV analysis”, “compare runs”, “detect drift”, “variance”, “confidence”.
- Typical outputs: tables, charts, derived CSVs, short interpretation notes.

### sol-knowledge-compiler
Use when the work is about turning runs/analysis into canonical, audit-ready knowledge.
- Keywords/phrases: “compile”, “promote”, “proof packet”, “claim ledger”, “canonical”, “consolidate”, “audit-ready”, “traceability”, “evidence”, “promotable”.
- Typical outputs: proof packets, consolidated summaries, claim promotions with references.

### sol-lab-master
Use when the work spans multiple stages (protocol → run → analysis → promotion), or when you want an orchestrated end-to-end workflow.
- Keywords/phrases: “orchestrate”, “end-to-end”, “from protocol to proof packet”, “run + analyze + compile”, “full workflow”, “lab session”.
- Typical outputs: coordinated sequence of artifacts and a clear handoff.

---

### soltech-research
Use when you want research-style work: summarizing sources, extracting requirements, or scoping.
- Keywords/phrases: “research”, “summarize sources”, “extract requirements”, “what does the repo do”, “find prior art”, “scan docs”, “review transcripts”, “identify constraints”.
- Typical outputs: requirements lists, source summaries, constraints, open questions.

### soltech-architect
Use when you want architecture or file-structure proposals.
- Keywords/phrases: “design”, “architecture”, “system layout”, “refactor plan”, “module boundaries”, “folder structure”, “API shape”, “data model”, “interface”.
- Typical outputs: proposed structure, diagrams, design notes, migration steps.

### soltech-implementer
Use when you want small, testable code edits applied precisely.
- Keywords/phrases: “implement”, “patch”, “fix this bug”, “add a script”, “update the tool”, “wire this up”, “make a small change”, “minimal diff”.
- Typical outputs: concrete code changes, small focused commits worth of work.

---

### SolTech-StructureManager
Use when you want explicit agent composition / workflow orchestration aligned to this repo’s structure conventions (instructions/prompts/skills), or when you’re building/maintaining the SOL workflow framework itself.
- Keywords/phrases: “structure manager”, “orchestrate agents”, “which prompt file”, “which skill”, “update the kit graph”, “workflow template”, “governance”.
- Typical outputs: routing decisions, prompt/skill selections, structured workflows.
- Scale-up cues: “parallel infra”, “GPU migration”, “many simultaneous calls”, “throughput scaling”, “scale-ready checklist”.
- Required behavior on scale-up cues: apply `.github/prompts/scale-ready-checklist.prompt.md` and then route to `sol-lab-master` or `sol-experiment-runner` as appropriate.

### Plan
Use when you want a multi-step plan before implementation (especially for ambiguous or multi-phase work).
- Keywords/phrases: “make a plan”, “outline steps”, “roadmap”, “break this down”, “phase this”, “what’s the checklist”.
- Typical outputs: actionable, verifiable steps with ordering and checkpoints.
### continuity
Use when the work involves maintaining repo-backed memory across chat sessions.
- Keywords/phrases: "remember", "continuity", "project memory", "session notes", "what did we do last time", "pick up where we left off", "end of chat", "save context".
- Typical outputs: updated project_memory.md, session_notes.jsonl entries, continuity summaries.

### sol-auto-mapper
Use when the work involves automated parameter sweeps on the SOL manifold/dashboard.
- Keywords/phrases: "mapping sweep", "auto map", "parameter sweep", "grid scan", "run plan", "master plan", "mapping pack", "ridge scan", "raw run bundles".
- Typical outputs: mapping plans (JSON), raw run bundles (CSV/JSON), organized run folders.
---

## Helpful “intent tags” (optional)
These aren’t required, but they make routing nearly perfect:
- “Treat this as **RUN** …”
- “Treat this as **ANALYSIS** …”
- “Treat this as **PROMOTION** …”
- “Treat this as **ARCH/DESIGN** …”
- “Treat this as **IMPLEMENTATION** …”
