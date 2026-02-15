# SOL — Self-Organizing Logos  
**README_SOL**

---

## 1. Overview

**SOL (Self-Organizing Logos)** is a conceptual and technical framework for building *meaning-centric*, self-organizing AI systems.

Instead of treating models as isolated black boxes, SOL treats an AI system as a living, evolving *domain*:  
a network of concepts, narratives, tools, and agents that continuously reorganize themselves around user intent, context, and long-term coherence.

At a practical level, SOL aims to be:

- A **semantic substrate** for AI agents and tools (how they share concepts and structure meaning).
- A **runtime and protocol** for self-organizing behaviors (how the system adapts and reconfigures itself).
- An **open environment** where these ideas can be iterated on collaboratively and transparently.

This README covers:

1. The **SOL artifact** (what SOL *is* in concrete terms).  
2. The **current status** of SOL (what exists today and what’s still emerging).  
3. The **OSE vision** — an open-source environment for evolving SOL as a shared, living project.

---

## 2. Conceptual Foundations

SOL is grounded in a few key theoretical ideas:

### 2.1 Self-Organizing Systems

The system is designed to reconfigure its own structure (concept graphs, agent roles, workflows) in response to:

- Use and interaction patterns  
- Feedback and corrections  
- New data and new domains

### 2.2 Logos as Organizing Principle

“Logos” here means *structured meaning* — the patterns, distinctions, and narratives that make a domain coherent.

SOL treats logos as:

- Something you can **encode** (as graphs, schemas, and embeddings),
- **Inspect** (via visualization, querying, and metrics),
- **Evolve** (through iterative refinement and self-organization).

### 2.3 Hybrid Symbolic + Sub-Symbolic Representation

SOL assumes that robust, interpretable behavior needs both:

- **Sub-symbolic**: embeddings, vector search, statistical profiles, neural models.  
- **Symbolic**: explicit nodes, edges, rules, schemas, and constraints.

SOL’s domain model is designed so these two layers stay in sync, instead of drifting apart.

### 2.4 Multi-Scale Organization

Concepts exist at multiple scales:

- Tokens → utterances → concepts → domains → mythologies / worldviews

SOL’s job is to keep those scales in conversation:

- Local interactions influence global structure.  
- Global constraints and narratives shape local behavior.

---

## 3. The SOL Artifact

The “SOL artifact” is the combination of:

1. A **domain model** (how knowledge and meaning are structured),  
2. A **runtime** (how agents and tools operate on that structure), and  
3. A **set of conventions / protocols** (how you plug data, models, and interfaces into it).

### 3.1 Domain Model: Self-Organizing Semantic Graph

The SOL domain model is a **self-organizing semantic graph**.

#### 3.1.1 Nodes

Nodes represent:

- **Concepts**  
  e.g., “forgiveness”, “gradient descent”, “ritual”, “feedback loop”.

- **Practices / procedures**  
  e.g., “guided reflection”, “stepwise analysis”, “integration protocol”.

- **Personas / agents**  
  e.g., “teacher”, “critic”, “integrator”, “explorer”.

- **Contexts / states**  
  e.g., “exploration mode”, “debug mode”, “integration phase”.

Each node can support **multiple representations**:

- **Symbolic view**  
  - Definitions, tags, type annotations, constraints, structured metadata.

- **Sub-symbolic view**  
  - Embeddings and statistical profiles derived from usage and context.

- **Narrative view**  
  - Stories, examples, user journeys where the node plays a role.

#### 3.1.2 Edges

Edges encode relationships such as:

- *is-a / kind-of* (taxonomy)  
- *supports / contradicts / refines* (argumentation)  
- *precedes / depends-on* (workflows, sequences)  
- *resonates-with / mirrors* (analogy, metaphor, pattern similarity)

These edge types let SOL model both rigorous structures and softer, analogical connections.

#### 3.1.3 Self-Organization Hooks

The graph is designed for:

- **Automatic clustering and re-clustering** based on usage patterns.  
- **Emergent hot zones** where user activity is high or shifting.  
- **Change suggestions** such as:
  - Merge/split nodes,
  - Re-type relationships,
  - Promote frequently co-occurring patterns into first-class concepts.

Human maintainers remain in the loop, but the system does a lot of the “what needs cleaning up?” discovery.

---

### 3.2 Runtime: Logos Engine

On top of the domain model lives the **SOL runtime** — the “logos engine.”

Its responsibilities include:

#### 3.2.1 Agent Orchestration

Coordinate multiple specialized agents that:

- Share the same domain model,  
- Declare the concepts and tools they operate on,  
- Negotiate outputs through a shared protocol.

Examples of SOL agents:

- **Teacher**: explains, guides, educates.  
- **Critic**: evaluates coherence, flags contradictions.  
- **Integrator**: links new information into existing structures.  
- **Explorer**: generates speculative connections and creative mappings.

#### 3.2.2 Context Shaping

Maintain a **rich context object**, including:

- User state (goals, preferences, session history),  
- Active concepts, edges, and narratives from the graph,  
- Current mode (exploration, deep dive, integration, debugging, etc.),  
- Provenance of the current conversation (where knowledge came from).

This context is passed into every SOL-aware agent and tool.

#### 3.2.3 Reflective Loops

Support cycles where the system:

1. Generates content, guidance, or transformations.  
2. Evaluates its own output against SOL constraints and goals.  
3. Updates:
   - The domain graph (nodes/edges/weights),  
   - Agent hints and policies,  
   - Tool selection strategies.

These loops enable **self-organization over time**.

#### 3.2.4 Tool Integration

SOL provides adapters to:

- LLMs (remote APIs, local models),  
- Vector stores / knowledge bases,  
- External APIs (speech-to-text, scheduling, visualization, etc.).

All of these tools speak through a **shared SOL context interface** rather than ad-hoc glue code.

---

### 3.3 Data & Memory

SOL treats data and memory as an ongoing conversation rather than static storage.

#### 3.3.1 Primary Corpus Ingestion

- Source texts / transcripts are:
  - Chunked and embedded,  
  - Mapped into the domain graph (nodes + edges),  
  - Annotated with provenance and trust metadata.

#### 3.3.2 Usage-Based Refinement

- SOL records which concepts and agents are triggered in which situations.  
- These patterns feed into:
  - Clustering and de-clustering,  
  - Node definition improvements,  
  - Suggestions for refactors (e.g., merging similar nodes).

#### 3.3.3 Layered Memory

- **Ephemeral memory**  
  - Short-term dialog context and working memory.

- **Session memory**  
  - Medium-term state within a user’s session or storyline.

- **Domain memory**  
  - Long-term updates to the SOL graph and domain definitions.

Only domain-level updates modify the shared, persistent “logos” of the system.

---

### 3.4 Tooling and Conventions

To keep things from devolving into chaos, SOL defines:

- A **standard context object**  
  - Passed through all agents and tools for consistent semantics.

- **Canonical IDs and naming conventions**  
  - For concepts, relations, and agents.

- **Versioning** of:
  - Domain schema,  
  - Graph snapshots,  
  - Agent configurations and policies.

Target realizations:

- A **Python library** (e.g. `sol_core`) embeddable in other projects.  
- A **service layer** exposing SOL via REST/WebSocket/gRPC APIs.

---

## 4. Current Status

SOL is in an **early-stage / pre-1.0** phase. The core architecture is conceptually clear; the implementation is partial and evolving.

### 4.1 What Exists Today

Current pieces (conceptual + experimental):

- **Core conceptual spec**
  - Working definition of SOL as a self-organizing, meaning-centric domain framework.  
  - Informal description of nodes, edges, and multi-layer representations.  
  - Principles for reflective loops and self-organization.

- **Early data pipeline experiments**
  - Ingestion via Whisper + LLMs.  
  - Initial chunking and embedding of source corpora.  
  - Primitive concept graphs seeded from real content.

- **Prototype interaction layer**
  - Custom GPT / agent setups that simulate parts of SOL:
    - Distinct roles (teacher, analyst, integrator, critic),  
    - Limited self-reflection (second-pass critiques, “meta” modes).

- **Code and notebooks**
  - Experimental code for:
    - Embedding and retrieval,  
    - Graph management (using existing graph/vector tools),  
    - Simple orchestration patterns and context passing.

These pieces demonstrate the *pattern* of SOL, but are not yet packaged as a coherent, versioned library.

### 4.2 In Progress / Near-Term Work

Near-term development priorities:

- **Formalizing the domain schema**
  - Move from informal concept sketches to explicit data models (e.g. Pydantic/dataclasses).  
  - Define core relation types and graph constraints.

- **Defining the SOL context protocol**
  - A standard request/response + context object for SOL-aware agents/tools.  
  - Minimal but extensible: user info, active nodes, mode, provenance, etc.

- **Extracting reusable components**
  - Identify stable parts of current experiments and factor them into `sol_core`-style modules:
    - Ingestion,  
    - Mapping & tagging,  
    - Retrieval,  
    - Reflection & evaluation.

### 4.3 Known Gaps

Before SOL can be considered stable as an artifact:

- No canonical **reference implementation** yet (the `sol_core` package is still conceptual).  
- No formal **versioned spec** for domain and runtime.  
- No **deployment story** (containers, infra templates, etc.).  
- No defined **public API** or SDK for external integrators.

These gaps are the main focus for the upcoming implementation passes and for the open-source environment.

---

## 5. OSE Vision — Open Source Environment for SOL

The **OSE (Open Source Environment)** is how SOL will live as a shared ecosystem rather than a private experiment.

### 5.1 Design Principles

The OSE is guided by:

- **Transparency**  
  - Clear documentation of architecture, assumptions, and limitations.

- **Modularity**  
  - Separate layers (spec, core, agents, viz, pipelines) so contributors can work where they’re strongest.

- **Pluralism with coherence**  
  - Multiple domain mappings and extensions are welcome, as long as they respect core SOL contracts (types, protocols, constraints).

- **Ethical orientation**  
  - SOL is explicitly oriented toward constructive, reflective, user-centric applications.

### 5.2 Repository & Project Structure (Proposed)

A possible OSE layout:

- `sol-spec`  
  - Formal specs: domain model, runtime contracts, context schema.  
  - RFCs for new relation types, modes, or protocols.

- `sol-core`  
  - Reference implementation of:
    - Domain graph engine,  
    - Context manager,  
    - Basic orchestration runtime.

- `sol-agents`  
  - Reusable agent templates and policies (teacher, critic, integrator, explorer, etc.).

- `sol-pipelines`  
  - Ingestion, ETL flows, and corpus-specific adapters.

- `sol-viz`  
  - Visualization and debugging tools for SOL graphs and flows.

- `sol-examples`  
  - End-to-end demos integrating SOL into concrete applications:
    - Mentoring systems,  
    - Research assistants,  
    - Reflective journaling / self-inquiry tools, etc.

Each repo is independently versioned but aligned with a global **`sol-spec`** version to maintain compatibility.

### 5.3 Governance & Contribution

Proposed governance model:

- **Core maintainers**  
  - Steward `sol-spec`, `sol-core`, and the overall roadmap.

- **RFC process**  
  - Significant changes (new core types, relation kinds, or runtime behaviors) go through an open proposal + discussion cycle.

- **Working groups / SIGs** (Special Interest Groups)  
  - Domain modeling  
  - Agent design  
  - UX & visualization  
  - Ethics & safety  
  - Integrations and tooling

- **Contribution paths**
  - Bug fixes & small improvements  
  - New agents and agent templates  
  - New domain mappings and corpora  
  - New visualizations and debugging tools

### 5.4 Licensing & Interoperability (Directional)

Licensing intent (not final):

- **Permissive license** (e.g. Apache 2.0 / MIT) for core components to encourage adoption.  
- Optional “ethical overlays” for certain higher-level packages if needed.

Interoperability goals:

- **Language-agnostic interfaces** via HTTP/gRPC/WebSockets.  
- **Explicit schema definitions** (JSON Schema / OpenAPI / JSON-LD) for SOL concepts and context objects.  
- **Integration adapters** for major ecosystems (Python, JS/TS, etc.).

---

## 6. Long-Term Direction

Longer-term, SOL aims to become:

- A **reference pattern** for building self-organizing, meaning-centric AI systems.  
- A **shared substrate** across multiple projects and domains that want:
  - Long-lived semantics,  
  - Reflective agents,  
  - Transparent and inspectable reasoning structures.

The Open Source Environment is where this evolves in public:

- Specs, code, and domain knowledge  
- Iterating together into a mature, reusable, and deeply interoperable SOL ecosystem.

---

## 7. Practical Operations (VS Code Default + External Watch Option)

For SOL testing and experiments, the default operational pattern is:

1. launch inside **VS Code Terminal** (new tab),
2. keep logs visible in that VS Code terminal tab,
3. use external watch windows only when explicitly requested,
4. avoid overlapping duplicate runs.

### 7.1 Standard RSI launch (VS Code terminal default)

Use the RSI launcher (runs inline in the current VS Code terminal by default):

```powershell
tools/sol-rsi/run_persistent.ps1 -Cycles 6 -BudgetHours 6
```

Optional (open external watch window):

```powershell
tools/sol-rsi/run_persistent.ps1 -Cycles 6 -BudgetHours 6 -WatchExternal
```

From VS Code Tasks:

- `RSI: Persistent (VS Code Tab)` → default run in VS Code terminal tab
- `RSI: Persistent (External Watch)` → starts an external PowerShell watch window

### 7.2 Generic external launcher (any Sol experiment)

Use the generic launcher to run any command in a separate external window:

```powershell
tools/launch_external_experiment.ps1 -Command "tools/sol-rsi/run_persistent.ps1 -Cycles 6 -BudgetHours 6"
```

Example for a one-off RSI cycle:

```powershell
tools/launch_external_experiment.ps1 -Command "G:/docs/TechmanStudios/sol/.venv/Scripts/python.exe tools/sol-rsi/rsi_engine.py --mode cron --cycles 1 --safe-llm"
```

### 7.3 Access model (external window vs VS Code Copilot)

External PowerShell experiments run as normal local processes and have:

- the same file-system access as your user account,
- access to `.env`/environment variables available to that process,
- access to all repo files and scripts under this workspace.

They do **not** have Copilot chat/tool context (for example, no direct access to the internal terminal-session IDs or chat memory).

Operationally: they can run the same Sol code, but they are not the Copilot runtime itself.

---

*End of README_SOL*