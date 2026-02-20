# SOL Agent Architecture Glossary (2026-02-14)

Purpose: provide a shared vocabulary for SOL operators, agents, and tooling so prompts, logs, and proof artifacts use terms consistently.

Scope: terms are defined as used in this repository and current runtime workflows.

Interpretation note: “metaphysics” terms in this project are used as an interpretation layer over measurable run artifacts (metrics, basins, transitions), not as a replacement for empirical checks.

## Prompt robustness canonicalization

Use this section to normalize prompt language before execution and parsing.

### Canonicalization rules
- Prefer canonical term labels below over free synonyms.
- Keep one canonical token per concept in structured prompts.
- If multiple synonyms are present, map them to one canonical term before writing JSON.
- Keep interpretation terms (metaphysics) linked to at least one measurable metric.

### Compact prompt template block (copy/paste)

Use this block in agent system prompts or reusable prompt files to enforce glossary normalization automatically.

```text
GLOSSARY ENFORCEMENT (SOL)
Source of truth: solKnowledge/consolidated/SOL_Agent_Architecture_Glossary_2026-02-14.md

1) Canonicalize vocabulary before reasoning/output:
	- Replace synonyms with canonical terms from the glossary alias map.
	- Keep one canonical term per concept in keys, labels, and acceptance criteria.
2) Preserve semantics while repairing message quality:
	- If incoming user/system text is fragmented or malformed, silently normalize grammar.
	- Do not invent missing facts; keep intent unchanged.
3) Enforce measurable anchoring:
	- Any metaphysics term must include at least one measurable anchor (metric, range, delta, or artifact field).
4) Output discipline:
	- Structured outputs must use canonical term labels.
	- If an unknown term appears, map to nearest canonical term and include `term_normalization_note`.

Normalization examples:
- "session run with a health ping" -> "Cortex Session" with "Heartbeat"
- "resonance band changed after phase shift" -> "Resonance Window" near "Transition Boundary"
```

### Alias map (synonym → canonical)

| Synonym / phrase | Canonical term |
| --- | --- |
| run, pass, iteration block | Cycle |
| session, cortex run | Cortex Session |
| health ping, liveness | Heartbeat |
| packet, evidence bundle | Proof Packet |
| draft packet | CANDIDATE |
| approved packet | PROMOTED |
| strict object output | Strict JSON Mode |
| markdown+json, mixed output | Hybrid Mode |
| parse recovery, parse retry | Parse-Aware Fallback |
| resonance window, resonance band | Resonance Window |
| attractor, sink state | Basin |
| phase shift, boundary crossing | Transition Boundary |
| dream-stop state, rest latch state | Dream Afterstate |
| latch primitive, end-phase latch | Latch Primitive |
| grail target | Grail Injection |
| coherence score | Thought Vibration |
| semantic coupling | Semantic Entanglement |
| possibility bandwidth | Manifold Potential |
| routing cue, keyword cue, soft keyword | Soft Trigger |
| runtime trigger, delegation trigger | Adaptive Trigger |
| throughput stall, execution stall, no-protocols-run | Velocity Drop |
| budget overrun, timeout overrun, elapsed over budget | Resource Overrun |
| rerun this stage, retry this stage | Stage Retry |
| trust score log, reliability ledger | Trust Ledger |
| stage contract, delegation spec | Delegation Contract |
| run/protocol intent | RUN Intent Tag |
| analysis intent, metrics intent | ANALYSIS Intent Tag |
| promotion intent, proof packet intent | PROMOTION Intent Tag |

## Core SOL concepts

### SOL (Self-Organizing Logos)
Meaning-centric architecture where concepts, processes, and agent outputs are modeled as an evolving semantic system rather than isolated model calls.

### Logos Engine
Runtime layer that orchestrates SOL-aware agent/tool behavior against shared context and constraints.

### SOL Context Object
The normalized context payload passed into tools/agents (active goals, artifacts, state, provenance, mode).

### Node
A first-class semantic entity in the SOL model (concept, process, persona, state, or artifact anchor).

### Edge
Typed relationship between nodes (e.g., supports, contradicts, depends-on, refines, resonates-with).

### Self-Organization
System tendency to restructure local/global semantics over time based on usage, constraints, and outcomes.

### Reflective Loop
Generate → evaluate → adapt cycle used to improve outputs and update strategy/policies.

## Routing and delegation terms

### Soft Trigger
Lightweight routing cue (usually a keyword/phrase in user text) used to select the best-fit agent/workflow path.

### Adaptive Trigger
Runtime trigger emitted from stage execution outcomes (for example sanity failures, stalls, or overruns) to drive retry/adaptation decisions.

### Delegation Contract
Contract-first stage specification including objective, falsifier, verifier, criticality, reversibility, budget, and authority scope.

### Trust Ledger
Stage reliability store tracking pass/fail history, trigger pressure, and trust score used for adaptive thresholding.

### Stage Retry
A bounded re-execution strategy applied when adaptive triggers indicate recoverable failure conditions.

### Velocity Drop
Trigger indicating throughput collapse (commonly no protocols executed in non-dry cortex execution).

### Resource Overrun
Trigger indicating stage elapsed time exceeded declared budget limits.

### RUN Intent Tag
Optional routing tag indicating protocol execution intent (run/sweep/counterbalance/run-bundle production).

### ANALYSIS Intent Tag
Optional routing tag indicating analysis intent (metrics/sanity/statistics/drift interpretation).

### PROMOTION Intent Tag
Optional routing tag indicating knowledge promotion intent (proof packet/claim ledger/canonical consolidation).

## Operator and workflow terms

### Cortex Session
An analysis run producing hypotheses/claims/questions and packetizable outputs (session IDs like `CX-...`).

### RSI Engine
Iterative run controller for recurrent analysis/execution cycles with guardrails and ledgered outputs.

### Cycle
One full RSI iteration including planning/execution/evaluation with logged outcome artifacts.

### Heartbeat
`data/rsi/heartbeat.json` status signal for liveness/progress of the currently active RSI run.

### Pipeline Verdict
Pass/fail style outcome for cycle-level quality gates (sanity/constraints/checks).

### Run Bundle
Structured experiment payload capturing identity, question, invariants, knobs, injections, protocol, results, and sanity checks.

### Invariant
Parameter held constant across compared conditions (for example `dt`, `c_press`, `rng_seed`).

### Knob
Parameter intentionally varied to test sensitivity or thresholds (for example `damping`, `dt`, `injection`).

### Baseline Mode
Initialization policy for repeated trials; commonly `fresh` in current runs.

### Open Question
Unresolved item captured for next cycles or later consolidation/promotion.

## Knowledge and evidence terms

### Claim
Testable statement extracted from runs/sessions, usually mapped to a claim ledger ID.

### Claim Ledger
Canonical list of claims and status transitions (often referenced as `CL-*`).

### Proof Packet
Audit-ready artifact that binds question → method → evidence → claim mapping.

### CANDIDATE (proof packet status)
Packet is drafted/extracted but not fully operator-promoted.

### PROMOTED (proof packet status)
Packet has passed operator review and is accepted as stable evidence in the repository workflow.

### Consolidation
Step that compiles and normalizes run/session outputs into navigable knowledge artifacts.

## Dynamics and metaphysics terms (operationalized)

### Resonance Window
A parameter region where `resonance_index` is consistently elevated relative to neighboring settings.

### Thought Vibration
Dimension score representing stability and quality of evolving cognitive-state patterns under a run profile.

### Semantic Entanglement
Dimension score representing coupling strength among semantic components during a run.

### Manifold Potential
Dimension score representing available future-state diversity/expansion under current conditions.

### Phonon Memory
Dimension score representing persistence of oscillatory/structural memory effects through time.

### Basin
Attractor-like endpoint regime identified by metrics such as `RhoMaxNode`, entropy level, and activity profile.

### Transition Boundary
Parameter point or interval where basin identity or macro-regime changes qualitatively.

### Grail Injection
Canonical shorthand for injections targeted at `grail` (often `grail → 50`), used as a standard probe setup.

### Dream Afterstate
Post-run state used to characterize end-phase carryover behavior before next-start selection.

### Latch Primitive
Mechanism where late-phase/end-phase state (for example last-injected context) influences next-start basin selection.

### Topological Reorganization
Observed regime shift where dominant node/basin identity migrates (for example `RhoMaxNode` changes across nearby knobs).

## LLM reliability and parsing terms

### Strict JSON Mode
Primary output contract requiring valid JSON payloads for deterministic downstream parsing.

### Hybrid Mode (Markdown + JSON)
Fallback-compatible mode where responses may include narrative framing plus a machine-extractable JSON block.

### Parse-Aware Fallback
Retry/escalation logic that treats parse failures as recoverable and attempts alternate extraction paths.

### LLM Lock File
File-based mutual exclusion marker to prevent overlapping LLM request sections in concurrent flows.

### Autotune (timeout)
Adaptive timeout/cooldown adjustments based on observed call success/failure behavior.

## Prompt writing guidance

- Use canonical terms in schema keys and acceptance criteria.
- Pair metaphysics terms with measurable anchors (example: “resonance window” + damping range + score deltas).
- Prefer explicit knob/invariant lists in prompts to reduce drift.
- Ask for run-bundle-compatible output when requesting experiment synthesis.
- For quick reuse, inject `.github/prompts/glossary-enforcement.prompt.md` at prompt start.

## Operational conventions

- Prefer these definitions in prompts, checklists, and session notes.
- If a term changes behaviorally, update this glossary first, then update downstream docs.
- New terms should be added only when they are operationally used by at least one tool/runbook.
