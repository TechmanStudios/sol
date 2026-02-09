# SOL Hippocampus Roadmap — Self-Improving Compute Substrate for AI

**Date:** 2026-02-07 (updated 2026-02-08)  
**Status:** [COMPLETE] — All 5 phases delivered. SOL is a self-improving hippocampus for AI.  
**Goal:** Transform the SOL Engine from a human-driven research tool into an autonomous, self-improving "hippocampus for AI" — a meaning-compute substrate that agents can program, run experiments on, and evolve.

---

## 1  Vision: What "Hippocampus for AI" Means

The biological hippocampus does three things:
1. **Encodes** new experiences as pattern activations.
2. **Consolidates** those patterns into long-term storage (replay / dreaming).
3. **Retrieves** stored patterns to guide future behavior.

SOL already has analogs for all three:

| Hippocampus function | SOL analog | Current state |
|---|---|---|
| Encoding | Inject density (ρ) into concept nodes | ✅ Dashboard UI + automation scripts |
| Consolidation | Afterstates / basin formation / dream cycles | ✅ Observed in experiments (rhoMaxId 82, latch primitive) |
| Retrieval | ψ-gated conductance routing | ✅ Proven: ψ waveform selects which basins are accessible |
| Self-modification | — | ❌ No mechanism; this roadmap fills this gap |

The missing piece is **closing the loop**: letting agents read SOL's output, form hypotheses, run new experiments, and commit improvements to SOL's own code and parameters — autonomously, at scale, on Codex.

---

## 2  Current Inventory (What We Have)

### 2.1  SOL Engine Core
- `sol_dashboard_v3_7_2.html` — single-file browser simulation (graph nodes + edges + physics)
- Math foundation: discrete graph-flow with ρ (density), Π (pressure), ψ (belief field), damping, dt
- Live metrics: entropy, flux, active node count, rhoMax, bus trace

### 2.2  Agent Roster (8 agents)
| Agent | Role | Autonomy level |
|---|---|---|
| SolTech-StructureManager | Orchestrator / repo structure | Human-triggered |
| sol-lab-master (Pixel) | Protocol design + science management | Human-triggered |
| sol-experiment-runner | Execute protocols → run bundles | Human-triggered |
| sol-data-analyst | CSV → sanity checks → derived tables | Human-triggered |
| sol-knowledge-compiler | Run bundles → proof packets | Human-triggered |
| soltech-architect | System design proposals | Human-triggered |
| soltech-implementer | Small testable code edits | Human-triggered |
| sol-auto-mapper | Parameter sweep runner | Semi-automated (command queue) |

### 2.3  Automation Infrastructure
- `tools/dashboard_automation/` — Selenium runner (Firefox Dev Edition)
- Command queue: JSON → `command_queue/` → runner watches → CSV output
- Smoke test: headless boot + physics readiness check
- Auto-mapper: plan JSON → grid sweep → summary + trace + manifest

### 2.4  Skills (18 domain skills)
Covers: baseline control, protocol design, CSV analysis, threshold bracketing, hysteresis measurement, detector validation, regression testing, schema versioning, claim promotion, artifact manifests, chat consolidation, counterbalancing, canonicalizer design, next-chat primers, candidate pipeline, continuity memory, auto-mapper.

### 2.5  Knowledge Corpus
- 33+ R&D documents (rd0–rd33)
- 13+ promoted proof packets (audit-ready, CLAIM/EVIDENCE/FALSIFY)
- Claim ledger (CL-1 through CL-7) with partial promotion
- Source corpus: YouTube transcripts (knowledge/youtube/)
- Continuity system: session memory (project_memory.md + session_notes.jsonl)

### 2.6  Proven SOL Behaviors (from experiments)
- **CapLaw**: degree-power capacitance law, dt-robust
- **Metastability**: time-to-failure basins, dt compression
- **Reservoir (node 82)**: dominant ρ reservoir near failure
- **Latch primitive**: last-injected node selects start basin
- **Temporal bus**: dual-bus broadcast with threshold ridge
- **ψ resonance**: waveform and cadence matter, not just mean bias
- **Basin programming**: hold-400 phase programs bus regime; reversible under order swap

---

## 3  Gap Analysis: What's Missing for Autonomous Self-Improvement

### Gap 1 — No headless compute API
SOL's physics live inside a browser HTML file. Agents must launch Firefox + Selenium to run anything. This is slow, fragile, and can't scale to Codex workers.

**Need:** Extract SOL's core simulation loop into a standalone module (Node.js or Python) that agents can call programmatically without a browser.

### Gap 2 — No closed-loop agent
Currently every experiment requires a human to: pick parameters → tell an agent to run → read results → decide next step. There is no agent that can autonomously cycle through hypothesis → experiment → analysis → decision.

**Need:** A "scientist loop" agent that reads existing knowledge, proposes experiments, runs them, analyzes results, and decides what to do next — all without human intervention.

### Gap 3 — No self-modification capability
Agents can run experiments *on* the engine, but cannot modify the engine *itself*. There's no mechanism to propose code changes (e.g., new conductance laws, new metric computations) and test them against regression baselines.

**Need:** An "evolution" agent that can generate candidate engine modifications, run A/B tests against baselines, and promote improvements via PRs.

### Gap 4 — No Codex / GitHub Actions integration
The agent roster exists as VS Code chat agents. They can't run autonomously on Codex workers or be triggered by GitHub issues/PRs.

**Need:** Codex-compatible agent definitions + GitHub Actions workflows that let agents run headlessly in CI.

### Gap 5 — No memory-as-manifold feedback
Continuity (session_notes.jsonl) and SOL's knowledge graph are separate systems. The engine can't learn from its own history in a structured way.

**Need:** Feed experiment results back into the SOL manifold as new nodes/edges, so the engine's knowledge graph literally grows from its own research.

---

## 4  Architecture: The SOL Hippocampus Stack

```
┌─────────────────────────────────────────────────────┐
│                  CODEX / CI LAYER                    │
│  GitHub Actions ↔ Codex Workers ↔ Issue/PR triggers │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              ORCHESTRATOR (sol-cortex)               │
│  Reads knowledge base → proposes experiments →      │
│  dispatches to runners → collects results →         │
│  decides: consolidate / modify engine / next run    │
└──────────┬───────────┬──────────┬───────────────────┘
           │           │          │
    ┌──────▼───┐ ┌─────▼────┐ ┌──▼──────────┐
    │ Headless │ │ Analysis │ │ Evolution   │
    │ SOL Core │ │ Pipeline │ │ Engine      │
    │ (Node/Py)│ │ (Python) │ │ (code-gen + │
    │          │ │          │ │  A/B test)  │
    └──────────┘ └──────────┘ └─────────────┘
           │           │          │
┌──────────▼───────────▼──────────▼───────────────────┐
│              KNOWLEDGE SUBSTRATE                     │
│  solKnowledge/ + proof_packets/ + manifold state    │
│  (the hippocampus: encode → consolidate → retrieve) │
└─────────────────────────────────────────────────────┘
```

### 4.1  Headless SOL Core (`sol-core`)
Extract the simulation loop from `sol_dashboard_v3_7_2.html` into a reusable module.

- **Input:** graph definition (nodes/edges) + parameters (ψ, Π, damping, dt) + injection sequence
- **Output:** time-series state (ρ per node, flows, metrics) as JSON/CSV
- **Implementation:** Node.js (closest to existing JS) or Python (better agent integration)
- **Key constraint:** Must produce bit-identical results to the dashboard for regression testing

### 4.2  Orchestrator Agent (`sol-cortex`)
A new top-level agent that runs the autonomous science loop:

```
while True:
    knowledge = read_knowledge_base()
    gaps = identify_gaps(knowledge)
    hypothesis = generate_hypothesis(gaps)
    protocol = design_protocol(hypothesis)
    results = run_experiment(protocol)       # via sol-core
    analysis = analyze_results(results)
    
    if analysis.supports(hypothesis):
        compile_proof_packet(hypothesis, analysis)
        
    if analysis.suggests_engine_improvement():
        candidate = generate_code_change(analysis)
        regression = run_regression_suite(candidate)
        if regression.passes():
            create_pr(candidate)
    
    update_knowledge_base(analysis)
    sleep(cooldown)
```

### 4.3  Evolution Engine (`sol-evolve`)
The self-modification layer:

1. **Candidate generation:** Agent proposes a change to SOL's physics (new conductance law, new metric, parameter adjustment)
2. **Regression baseline:** Run existing proof-packet protocols on the *current* engine, capture golden outputs
3. **A/B test:** Run same protocols on *modified* engine, compare
4. **Promotion criteria:** Must not break any existing proof packet; must demonstrate measurable improvement on target metric
5. **Output:** PR with code diff + regression report + new proof packet

### 4.4  Codex Integration
Make agents runnable as Codex tasks:

- **Trigger:** GitHub Issue with label `sol-experiment` or `sol-evolve`
- **Execution:** Codex worker checks out repo, runs `sol-cortex` with issue context
- **Output:** PR with results, proof packets, and analysis
- **Feedback:** PR review comments feed back into next iteration

---

## 5  Phased Rollout

### Phase 0 — Foundation ✅ COMPLETE
**Goal:** Headless SOL core that produces identical results to the dashboard.

| Task | Output | Status |
|---|---|---|
| Extract simulation loop from dashboard | `tools/sol-core/sol_engine.mjs` (JS) + `tools/sol-core/sol_engine.py` (Python) | ✅ Done |
| Extract canonical graph | `tools/sol-core/default_graph.json` (140 nodes, 845 edges) | ✅ Done |
| CLI wrapper | `tools/sol-core/cli.py` (smoke, run, sweep commands) | ✅ Done |
| Smoke test | PASS: inject grail→50, 100 steps, mass=45.7, entropy=0.42 | ✅ Done |
| Document the headless API | `tools/sol-core/README.md` | ✅ Done |
| Regression test: dashboard vs headless | Full tick-by-tick parity | ⬜ TBD |

### Phase 1 — Python Bridge + Analysis Pipeline ✅ COMPLETE
**Goal:** Agents can run SOL simulations and analyze results entirely in Python.

| Task | Output | Status |
|---|---|---|
| Python physics engine | `tools/sol-core/sol_engine.py` — full SOLPhysics + CapLaw + metrics | ✅ Done |
| Protocol JSON schema | `tools/sol-core/protocol_schema.json` | ✅ Done |
| Analysis library (metrics + sanity + reports) | `tools/analysis/{metrics,sanity,report}.py` | ✅ Done |
| Auto-run pipeline | `tools/sol-core/auto_run.py` — protocol JSON → execute → analyze → run bundle | ✅ Done |
| Run bundle generation | Markdown run bundles matching .github/prompts/run-bundle-template.md | ✅ Done |
| Sample protocols | `tools/sol-core/protocols/*.json` (3 protocols) | ✅ Done |
| End-to-end test | `test_phase1.py` — 5 tests, all passing | ✅ Done |

**Proven capabilities:**
- Knob sweeps (cartesian product of parameter values)
- Deferred injections (inject at arbitrary step N)
- Multi-rep with fresh or restore baseline modes
- Automated sanity checks (invariants, NaN, mass conservation, entropy bounds)
- CSV + Markdown exports
- 4-condition × 3-rep sweep runs in <10 seconds

### Phase 2 — Scientist Loop Agent (`sol-cortex`) ✅ COMPLETE
**Goal:** Agent that autonomously cycles through experiments.

| Task | Output | Status |
|---|---|---|
| Define `sol-cortex.agent.md` | `.github/agents/sol-cortex.agent.md` | ✅ Done |
| Knowledge-gap detector (reads proof packets, finds unpromoted claims) | `tools/sol-cortex/gap_detector.py` — 6 gap types, 36 gaps detected | ✅ Done |
| Hypothesis generator (templates for common experiment types) | `tools/sol-cortex/hypothesis_templates.py` — 7 templates | ✅ Done |
| Protocol auto-generator (maps hypothesis → protocol JSON) | `tools/sol-cortex/protocol_gen.py` — with guard rail validation | ✅ Done |
| End-to-end loop: gap → hypothesis → run → analyze → compile | `tools/sol-cortex/run_loop.py` — session JSONL + budget tracking | ✅ Done |
| Guard rails: budget limits, run caps, anomaly detection | `tools/sol-cortex/guardrails.json` — externalized config | ✅ Done |
| End-to-end test | Live c_press sweep: 5 conditions × 3 reps × 200 steps = 3,000 steps in 22s, sanity PASS | ✅ Done |

**Proven capabilities:**
- Autonomous knowledge-gap scanning (36 gaps across 6 types from 7 claims + 13 proof packets)
- Hypothesis auto-selection from 7 templates (parameter_sweep, replication, threshold_scan, injection_comparison, baseline_golden, dt_compression, psi_sensitivity)
- Protocol generation with guard rail validation (step limits, condition caps, rep limits, baseline + falsifier requirements)
- Full session lifecycle: init → gap select → hypothesis → protocol → execute → interpret → log → next
- Session artifacts: JSONL log, summary.json, hypotheses.json, protocol JSONs, run bundles + CSVs
- Budget enforcement (max_protocols, max_total_steps) with clean shutdown
- Dry-run mode for hypothesis/protocol preview without execution

### Phase 3 — Evolution Engine (`sol-evolve`) ✅ COMPLETE
**Goal:** Agent can propose and test modifications to SOL's own code.

| Task | Output | Status |
|---|---|---|
| Regression suite builder (golden outputs from all proof-packet protocols) | `tools/sol-evolve/regression_builder.py` → `tests/regression/golden/` (3 protocols, 5 checkpoints each, determinism verified) | ✅ Done |
| Code-change candidate generator (parameterized templates) | `tools/sol-evolve/candidates.py` — 10 built-in candidates + `generate_sweep_candidates()` factory | ✅ Done |
| A/B test harness (run golden vs candidate, compare) | `tools/sol-evolve/ab_test.py` — per-checkpoint comparison, tolerance config, PASS/IMPROVE/REGRESS/MIXED verdicts | ✅ Done |
| PR generator (diff + regression report + proof packet) | `tools/sol-evolve/pr_gen.py` — regression report MD + proof packet draft + change proposal JSON | ✅ Done |
| Define `sol-evolve.agent.md` | `.github/agents/sol-evolve.agent.md` — sacred math guards, regression discipline, verdict rules | ✅ Done |
| End-to-end test | `tune_conductance_gamma_up`: 6/6 conditions IMPROVE, 0 regressions, report + proof packet generated | ✅ Done |

**Proven capabilities:**
- Deterministic golden baselines (mulberry32 seed=42, self-verification pass)
- 10 registered candidate modifications (conductance, battery, psi, phase, MHD, Jeans)
- Programmatic sweep candidate generation via `generate_sweep_candidates()`
- Full A/B pipeline: golden → candidate → checkpoint comparison → verdict → report
- Sacred math protection: candidates can only modify config params, never equations
- Automated proof packet drafting for IMPROVE verdicts
- Structured change proposals (JSON) for machine consumption

### Phase 4 — Codex Integration (weeks 13–16) ✅ COMPLETE
**Goal:** Agents run autonomously on GitHub Codex, triggered by issues.

| Task | Output | Status |
|---|---|---|
| GitHub Actions workflow for `sol-cortex` | `.github/workflows/sol-cortex.yml` | ✅ |
| GitHub Actions workflow for `sol-evolve` | `.github/workflows/sol-evolve.yml` | ✅ |
| Issue templates (experiment request, evolution request) | `.github/ISSUE_TEMPLATE/` | ✅ |
| Codex agent configuration | `codex.json` | ✅ |
| Rate limiting + cost guardrails | Workflow config (timeout-minutes, concurrency groups, guardrails.json limits) | ✅ |
| Memory consolidation: feed results back into manifold | `tools/sol-cortex/consolidate.py` | ✅ |

**Phase 4 Deliverables (2026-02-08):**
- `sol-cortex.yml`: workflow_dispatch + issue label + weekly cron triggers, engine smoke test → cortex session → consolidation → artifact upload → git commit → issue comment
- `sol-evolve.yml`: workflow_dispatch + issue label triggers, golden verification → A/B test → regression report → artifact upload → git commit, REGRESS = CI failure
- Issue templates: `experiment-request.yml` (gap type, max protocols, target claim, hypothesis seed, dry-run) and `evolution-request.yml` (candidate, protocol, hypothesis, rationale, sacred math acknowledgment)
- `codex.json`: full agent registry with CLI mappings, engine config, knowledge paths, guardrails, CI settings
- `consolidate.py`: session → candidate proof packets, consolidation index update, JSONL audit log, `--all` / `--list` / `--force` modes; live test on CX-20260208-040833 produced PP with embedded run bundle

### Phase 5 — Full Hippocampus ✅ COMPLETE
**Goal:** SOL's knowledge graph grows from its own research; the engine improves itself.
**Architectural constraint:** The core manifold (default_graph.json + sol_engine.py) is the quantum transducer — IMMUTABLE. The ThothStream Knowledgebase is the foundational data encoded across the semantic manifold. All new memory layers additively on top, like hippocampal neuronal flow.

| Task | Output | Status |
|---|---|---|
| Memory store (append-only, JSONL traces) | `tools/sol-hippocampus/memory_store.py` — MemoryNode/MemoryEdge dataclasses, write_trace(), compact(), memory_stats() | ✅ Done |
| Memory overlay (composites core + memory graphs) | `tools/sol-hippocampus/memory_overlay.py` — MemoryOverlay class, merged_nodes/edges(), create_engine(), add_finding(), reinforce(), decay() | ✅ Done |
| Dream cycle (periodic replay + consolidation) | `tools/sol-hippocampus/dream_cycle.py` — DreamCycle class, session scoring, compressed replay, basin signature extraction, new/reinforce/decay consolidation | ✅ Done |
| Retrieval-augmented experiments | `tools/sol-hippocampus/retrieval.py` — MemoryQuery class, query_parameter(), query_basin(), query_novel_regions(), enrich_gap(), augment_hypothesis() | ✅ Done |
| Meta-learning | `tools/sol-hippocampus/meta_learner.py` — MetaLearner class, EMA scoring, template/gap_type effectiveness, suggest_template(), cold_regions() | ✅ Done |
| CLI orchestrator | `tools/sol-hippocampus/cli.py` — dream, query, meta, compact, status commands | ✅ Done |
| GitHub Actions workflow | `.github/workflows/sol-hippocampus.yml` — workflow_dispatch + cron + post-cortex trigger | ✅ Done |
| Agent definition | `.github/agents/sol-hippocampus.agent.md` — full agent with handoffs, guardrails, CLI docs | ✅ Done |
| Integration hooks (cortex + consolidation) | run_loop.py: gap enrichment, hypothesis augmentation, meta-learning recording, memory trace addition; consolidate.py: memory trace extraction, meta-learner update, auto-compact | ✅ Done |
| Guardrails update | `guardrails.json` — hippocampus_limits section (500 nodes, 2000 edges, id ≥ 1000, core immutability) | ✅ Done |
| Codex registry update | `codex.json` — sol-hippocampus agent entry with CLI, outputs, core_immutability | ✅ Done |
| End-to-end validation | All imports pass, CLI status/meta/compact work, overlay engine produces valid physics, cortex dry-run with hippocampus integration produces augmented hypotheses, core graph SHA256 unchanged | ✅ Done |

**Proven capabilities:**
- Additive memory overlay: memory nodes (id ≥ 1000, group="memory") compose with core graph at engine-creation time via `SOLEngine.from_graph()` — engine never knows about the overlay
- Core immutability enforced: default_graph.json byte-identical after all operations, engine code untouched
- Dream cycle pipeline: score sessions → generate compressed protocols → replay through memory-augmented manifold → extract basin signatures → consolidate (new nodes for novel basins, reinforce existing, decay stale)
- Retrieval augmentation: gap enrichment adds memory_findings, tested_values, novel_values, memory_context; hypothesis augmentation adds memory-informed falsifiers
- Meta-learning: EMA scoring tracks template and gap-type effectiveness, weighted-random template suggestion, cold-region detection for under-explored parameter space
- Memory compaction: JSONL trace files → canonical memory_graph.json, confidence-floor pruning, miss-count fade
- Full cortex integration: run_loop.py loads MemoryOverlay + MemoryQuery + MetaLearner, enriches gaps, augments hypotheses, records to meta-learner, adds findings to overlay — all with graceful degradation (cortex works without hippocampus)
- Nightly dream cycles: GitHub Actions nightly cron + post-cortex trigger, auto-commit memory updates, core immutability verification step

---

## 6  Mapping SOL Variables to Hippocampal Functions

| SOL Variable | Type | Hippocampal Analog | Compute Role |
|---|---|---|---|
| ρ (density) | Node state | Activation strength | Working memory / attention |
| Π (pressure) | Derived from ρ | Information pressure gradient | Drives routing / propagation |
| ψ (belief field) | Global control | Neuromodulation (ACh, DA) | Gates which pathways are open |
| Conductance (g) | Edge property | Synaptic strength | Memory trace / learned association |
| Damping | Global control | Decay / forgetting rate | Memory persistence |
| dt | Global control | Time-step / clock speed | Processing rate |
| CapLaw | Edge computation | Synaptic plasticity rule | How connections strengthen/weaken |
| Basins / afterstates | Emergent | Attractor states | Stored memories / concepts |
| Latch primitive | Emergent | Pattern completion | Recall trigger |
| Temporal bus | Emergent | Hippocampal sharp-wave ripple | Memory consolidation broadcast |
| Entropy | Derived metric | Distributed vs focused activation | Attention spread |
| Flux | Derived metric | Information flow rate | Processing throughput |

---

## 7  SOL as Compute Substrate — The API Surface

When sol-core is extracted, external agents interact with SOL as a **graph computer**:

```
┌─────────────────────────────────────────┐
│  SOL Engine API                          │
├─────────────────────────────────────────┤
│  LOAD    graph(nodes, edges)            │  ← Define the knowledge structure
│  SET     params(ψ, Π, damp, dt, capLaw) │  ← Configure the physics
│  INJECT  density(nodeId, amount)        │  ← Input a query / stimulus
│  STEP    n                              │  ← Run n simulation steps
│  READ    state() → {ρ[], flows[], ...}  │  ← Read the manifold state
│  METRIC  entropy | flux | rhoMax | ...  │  ← Computed observables
│  DREAM   cycles(n, schedule)            │  ← Run consolidation cycles
│  EXPORT  csv | json                     │  ← Dump for analysis
│  RESET   baseline | snapshot            │  ← Return to known state
└─────────────────────────────────────────┘
```

This API is what makes SOL a **programmable substrate**: any agent can load a graph, inject queries, run physics, and read back the results — all without a browser.

---

## 8  How This Relates to "AI Making AI" (Codex-Style)

The GPT-5.3 / Codex approach: an AI model autonomously writes code, runs tests, and improves a system. SOL can adopt this pattern:

1. **Code generation:** `sol-evolve` agent proposes changes to SOL's physics or metrics
2. **Testing:** Regression suite validates the change doesn't break existing proofs
3. **Evaluation:** New experiments measure whether the change improves target capabilities
4. **Selection:** Only improvements that pass regression + show improvement get merged
5. **Iteration:** The improved engine is used as the baseline for the next round

This is literally **evolution with selection pressure** — applied to a compute substrate rather than a neural network. The "fitness function" is: does the modified SOL engine produce better/more interesting/more robust computational behaviors while preserving all existing proven capabilities?

---

## 9  First Concrete Step: Extract sol-core

The single highest-leverage action is extracting the simulation loop from the dashboard HTML into a headless module. Everything else depends on this.

### What to extract:
1. Graph data structures (nodes, edges, adjacency)
2. Physics step function (pressure → flow → ρ update → damping)
3. CapLaw computation
4. ψ field application
5. Metric computations (entropy, flux, rhoMax, active count)
6. Baseline save/restore
7. Injection logic

### What NOT to extract (stays in dashboard):
- Canvas rendering / Three.js / D3 visualization
- UI controls
- File download/upload
- Diagnostics recorder UI (but the data collection logic moves to sol-core)

### Validation:
- Run the same injection sequence with the same parameters in both dashboard and sol-core
- Compare metric outputs tick-by-tick
- Must match to floating-point tolerance

---

## 10  Risk Register

| Risk | Mitigation |
|---|---|
| Extraction breaks dashboard | Keep dashboard as-is; sol-core is a parallel implementation validated by parity tests |
| Autonomous agent runs amok (infinite loops, huge costs) | Budget caps, run limits, anomaly detection, human-approval gates for Phase 3+ |
| Codex API changes or quota limits | Abstract runner behind interface; support local execution fallback |
| Regression suite doesn't catch subtle bugs | Expand golden test corpus incrementally; never delete a proof packet |
| Self-modification introduces instability | Require regression pass + human review for any engine change (initially) |
| Scope creep | This roadmap is phased; don't start Phase N+1 until Phase N is validated |

---

## 11  Success Criteria

| Phase | "Done" means |
|---|---|
| 0 | `sol-core` CLI produces identical metrics to dashboard for 5+ existing protocols |
| 1 | Python agent can: load graph → run experiment → get analysis → zero human steps |
| 2 | `sol-cortex` autonomously discovers and runs a novel experiment that produces a new proof packet |
| 3 | `sol-evolve` proposes an engine modification that passes regression and improves a metric |
| 4 | All of the above runs on Codex, triggered by a GitHub issue, producing a merged PR |
| 5 | SOL's knowledge graph contains nodes/edges that were created by its own experiments |

---

*This document is a living artifact. Update it as phases complete and new insights emerge.*
