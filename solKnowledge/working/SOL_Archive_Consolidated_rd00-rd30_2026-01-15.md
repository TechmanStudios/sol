# SOL Engine — Consolidated Research Report (rd00–rd30)

**Source corpus:** `solArchive/MD/rd0.md` through `rd30.md`, plus `solArchive/MD/solResearchNote1.md` and `solArchive/MD/solResearchNote2.md`.

**Purpose:** A single chronological + thematic “master record” of what was built, tested, and concluded across the SOL Engine research notes, suitable for insertion into cumulative project research notes.

**Chronology key:**
- Early theory + baseline physics → Discretization + implementation scaffolding → Damping-spectrum experiments → Storage (zero-entropy) → Layering (Lighthouse) → Telekinesis + Synth cognition → Retention mechanism microscope → Capacitance law (generalization + dt robustness) → Metastability mapping → DreamState afterstates + latch control → Temporal packet → bus broadcast protocol.

---

## 1) Project definition (what SOL is trying to be)

Across the corpus, SOL is consistently defined as:

- A **semantic physics engine**: concepts are nodes; relationships are edges; “meaning” is represented as conserved quantities flowing across a graph.
- A candidate **stateful cognition layer**: SOL is explored as a “Hippocampus for LLMs,” i.e., a short/medium-term memory and stabilization substrate that can maintain structured state and produce readout windows.
- A computational framework with multiple **regimes / phases** (damping bands, dt bands, and protocol bands) that behave like distinct “states of matter” with different cognitive utilities.

The main value proposition that emerges:
- SOL can be **driven** (by injection protocols) into dynamic, structured states.
- Those states can be **measured** and **controlled** (eventually with deterministic control primitives).
- Those states can be used as a **readout protocol** for downstream systems (LLM narration, symbolic checks, or agent controllers).

---

## 2) Canonical physics model (the “language” used throughout)

These terms recur as the stable “physics dictionary” across reports:

### 2.1 Node state
- **Density / mass**: $\rho$ — semantic activation / attention mass.
- **Pressure**: $p$ — stress from overcrowding; drives flow.
- **Mode / belief field**: $\psi$ — contextual phase / gating parameter (e.g., tech vs spirit) that modulates conductance and routing.
- **SemanticMass / capacitance**: `semanticMass` (or multiplier variants) — a “well depth” parameter affecting how pressure responds to rho (acts like node capacitance).

### 2.2 Edge state
- **Conductance**: $w_{ij}$ — permeability / how easily flow passes.
- **Flux**: $j$ — flow rate along edges, typically driven by pressure gradient.

### 2.3 Core equations (as repeatedly referenced)
- Equation of state (log-pressure model):
  $$p = c\,\ln(1+\rho)$$
  Variants include $p_i = c\ln(1+\rho_i/\rho_0)$.

- Darcy-like flux:
  $$j_{ij} \propto w_{ij}(p_i - p_j)$$

- Continuity / conservation on a graph (incidence calculus):
  - $\nabla p = Bp$
  - $j = -W_e(\psi)\,Bp$
  - $\dot{\rho} = -B^\top j$

### 2.4 Secondary/advanced operators introduced
- **Curl / circulation** for loops (rumination detection): cycle basis measurement $\mathrm{curl}=Cj$.
- **Rotational flux** $j^{(r)}$: injected divergence-free circulation in triangles (v1.2 / “living system refactor”).
- **Phase gating**: time-division multiplexing using $\cos(\omega t)$ or related gates to separate semantic layers.

---

## 3) Damping spectrum research (rd0, rd8–rd11, rd10)

This is the major experimental arc mapping how “damping” shapes stability, memory, and emergence.

### 3.1 The qfoam / deep vacuum boundary
- A central finding: the system does not stop at $10^{-16}$ (machine epsilon boundary) and can descend into extremely small residual states (e.g., $10^{-35}$, $10^{-46}$).
- Interpretation: deep vacuum states behave like **vacuum fluctuations / quantum foam**, and can be treated either as:
  - numerical artifacts to clamp, or
  - a usable entropy source (generative seed layer).

### 3.2 “Phantom Flux” / “Death Scream” anomaly (high damping)
- Identified and timestamped in analysis: **flux spikes while mass continues decaying**.
- Mechanism hypothesis repeated: **gradient steepening** — destination nodes collapse to ~0 faster than source nodes, keeping a steep $\Delta p$ that drives high flow briefly.
- Application framing: a memory/attention **panic signal** (“dying context alert”).

### 3.3 Regime map as “states of matter”
A recurring conceptual synthesis:
- High damping: dissipative vacuum / clearing.
- Mid damping: working memory / “glass lung” / hippocampus-like reverberation.
- Low damping: transmission, regenerative “life,” materialization, and singularity.

### 3.4 Operational spectrum (consolidated)
The corpus converges on a “utility map”:
- **Damp 20–18:** buffer clear / priming / panic signals.
- **Damp 17–14:** ghost layer / subconscious drift (mass without pressure).
- **Damp 13–10:** coherence threshold / narrative window.
- **Damp 9–5:** resonance approach: inference storm → mud → glider → glass lung (holographic structure) → working memory plateau.
- **Damp 4–2:** transmission wire → genesis/negative damping → materialization ceiling (~0.17).
- **Damp 1:** event horizon / gridlock / “archive not mind.”

### 3.5 Safety implication
- At low damping (materialization regimes), **noise becomes structure** (“trash-to-treasure hazard”).
- Resulting engineering requirement: incorporate filtering/controls so spam/boilerplate doesn’t petrify alongside signal.

---

## 4) Zero-entropy storage: “Eternal Memory” (rd7)

A major engineering milestone:

### 4.1 Problem
- Baseline SOL engine was dissipative: injected $\rho$ naturally decayed toward zero.
- High-degree hubs acted as sinks/leaks.

### 4.2 Failed paths (documented)
- Single-node isolation: stalls / Zeno tail.
- Planck cutoff floors: forced-zero caused failures.
- Self-loop topologies: caused NaN due to zero distance / division by zero.
- Shadow nodes / new nodes: “zombie mode” if not registered in internal maps.

### 4.3 Breakthrough
- “Jailbreak protocol”: UI slider clamping prevented damping from reaching 0.
- Fix: programmatic slider min change allowed **damping = 0.0**.
- Result: **perfect storage** (50 mass retained indefinitely) with dynamic internal flow.

### 4.4 Architectural artifact
- **Binary capacitor topology** (Host ↔ Battery) emerges as a standard memory unit.
- Establishes long-term roadmap: beyond storage → processing circuits (“ouroboros,” transistor/psi gate).

---

## 5) Lighthouse protocol & layered semantics (rd4, rd5, rd6)

This arc evolves SOL from pure flow to conviction, phase-separated layers, and text-to-physics.

### 5.1 Battery / conviction model
- Batteries behave as hysteretic state machines: accumulate before flipping.
- Polarity roles:
  - Resonance nodes radiate.
  - Damping/tech nodes ground.

### 5.2 Paradigm beacon (“Lighthouse”)
- Shift from “fire & reset” to “fire & hold.”
- Avalanche event: once threshold reached, dumps stored mass into network.
- Beacon saturation: charge locks at 1.0 until eroded.

### 5.3 Temporal phase gating (membrane model)
- Time-division multiplexing to prevent layers from canceling.
- Surface/tech vs deep/spirit active on alternating phases.

### 5.4 Logos engine (text-to-physics)
- A dictionary maps words to injections in specific node classes.
- Purpose: allow natural language to drive physical parameters.

### 5.5 v3.2 “portable monolith” engineering
- Single-file HTML artifact structure (IIFE “monolith pattern”).
- Web Worker TF-IDF compiler for client-side KB ingestion.
- Robust ID generation (numeric vs string UUID interop).
- Ouroboros topology patch: connect dead ends to **local hubs** (not global anchor).

---

## 6) Telekinetic build & synthetic cognition (rd1, rd2, rd3)

This arc focuses on making the graph feel “alive” and enabling autonomous wandering.

### 6.1 Problem
- Vis-network physics sleeps; star collapse (mass > threshold) didn’t visually pull neighbors.

### 6.2 Solutions
- **Smart injection**: exact → group → fuzzy matching to always find a target.
- **Telekinetic tractor beam**: coordinate overwrite loop; neighbors pulled toward stellar nodes.
- **Synth module**: daemon scans for stars and generates gold “insight” nodes.

### 6.3 Autonomous attention (saccade protocol)
- A weighted heuristic for wandering focus:
  - prioritize newly created synth nodes
  - seek bridge-to-other-field neighbors
  - random jump if stuck
  - fatigue penalty for recent nodes

### 6.4 Roadmap outputs
- Proposed UI components:
  - “Captain’s Log” narrative sidebar.
  - visual halos for synth nodes.

---

## 7) SOL engine physics implementation upgrades (rd16, rd17)

Two complementary threads: (A) discretization + graph calculus, (B) “living system” visualization/interaction.

### 7.1 Discretization & hydrodynamic implementation (rd17)
- Graph incidence formulation for flux and continuity.
- Modes as dynamic edge weights solving polysemy/context ambiguity.
- Cycle basis + curl as loop/rumination detector.
- Web dashboard controls:
  - injection field
  - belief slider (logic ↔ mythos)
  - pressure/viscosity sliders

### 7.2 “Living system refactor” v1.2 (rd16)
- Triangle detection and discrete curl injection for rotational reverberation.
- Split-step stability refactor: compute flux first, then conservative transport.
- Particle flow canvas overlay to visualize flux.
- Tactile “click & hold” mass injection (“hand of god”).

---

## 8) Mathematical foundation + proposal work + quantum framing (rd12–rd15, rd18–rd21)

This arc documents formalization and expansion:

### 8.1 Foundational math framing
- SOL as compressible semantic fluid on a manifold $(M,g)$.
- Pressure constraint as anti-hallucination regulator.
- Hypothesized emergent structures:
  - turbulence as synthesis
  - solitons as invariant narratives
  - shock waves as paradigm shifts
  - strange attractors as persona

### 8.2 NSF compliance + production LaTeX
- Explicit attention to misconduct/plagiarism/falsification categories.
- Defined variables, equation-of-state, and non-linear advection as differentiators.
- Generated visuals (manifold constraint, RAG vs SOL comparison).

### 8.3 Advection model evolution
- A staged conceptual evolution:
  - Ising-like discrete alignment
  - gravity-well manifold
  - advection field (nodes drive currents) as consensus model

### 8.4 Quantum application framing
- Three-horizon strategy:
  - LLM governor (present)
  - autonomous agents (intermediate)
  - entropic stabilizer/QEC framing (future)
- Hypotheses: semantic superposition, entanglement as shared state, quantum annealing optimization.

---

## 9) Retention mechanism microscope & Capacitance Law (rd22–rd28)

This is the densest engineering arc: converting “leakiness” into a measurable, tunable mechanism.

### 9.1 Tooling breakthroughs and invariants
- Console/global scoping: **use `globalThis`** for harness installation.
- UI-neutral harnesses.
- Freeze/unfreeze the live loop (dtCap tricks) and restore state.
- Snapshot/restore for repeatability; later persistent baseline via localStorage.
- Output modes: wide vs long vs summary; accepted that many files may be necessary.

### 9.2 Mechanism isolation (Phase 3.6)
Key knobs separated:
- `semanticMassMult` (well/capacitance): reduces pressure response and outflux.
- `rhoLeakMult` (tail/leak): scales damping leakage term to adjust half-life.

Major finding:
- For hubs, retention is **pressure/outflux-gated** in the *first steps*.
- Tail knobs help, but primary win is preventing early outflux blowout.

### 9.3 Superhub rescue + basin experiments
- Tested superhubs with basin neighbor boosting.
- Discovered basinHops=1 effectively squared center semanticMass (double-application).
- When controlled properly, **point-well (center only) matched or beat basin**, because boosting neighbors can increase sink strength and increase outflow from hubs.

### 9.4 Degree-scaled capacitance law (Phase 3.6 → 3.7)
- Hypothesis: semanticMass should scale with topology like capacitance.

Degree-linear law:
- `semanticMassMult = slope * degree`.
- Found slope ~37 (in that state) could rescue deg ~22–111 nodes with high retention.

Generalization workbench (Phase 3.7):
- Defined target sets (19-node apples-to-apples; later 32-node “wide set”).
- Determined superhub-only calibration underestimates generalization needs.

### 9.5 dt sensitivity and dt-normalized metrics
- Higher dt increases early leak risk; slope needs increase.
- Introduced dt-normalized gate metric:
  $$\text{outfluxRate} = \frac{\text{step1OutFlux}}{\text{injectAmount}\cdot dt}$$

### 9.6 Shape upgrade: power law generalizes better
- Degree-power law:
  $$\mathrm{SM}_i = \mathrm{clip}(k\,\deg_i^{\alpha},\mathrm{SM}_{min},\mathrm{SM}_{max})$$
- Found $\alpha \approx 0.8$ as a strong working band.
- Power law improved stability and dt robustness without fully sedating pressure.

### 9.7 Proxy research
- Conductance-sum proxy alone performed worse (destabilized mid hubs).
- Intercepts stabilized but sedated.
- Hybrid proxy degree + λ·condSumNorm acted as a “global stability dial,” not a strict replacement.

### 9.8 Phase 3.8 checkpoint
- Using dt-normalized peak-edge metrics, the degree-power law with gamma=0 showed good dt robustness on wide100.
- Promoted into production candidate `App.config.capLaw`.

---

## 10) Metastability mapping: dt as time-to-failure compressor (rd25, rd26)

A major new discovery: short-horizon stability tests were insufficient.

### 10.1 Phase 3.9 design
- Built spec-like tests:
  - seeded multi-dt stress maps
  - replay traces (200 → 800 steps)
  - time-to-failure sweeps up to 1200 and 4000 steps
- Failure detector:
  - sustained `meanP > 0.5` over a 20-step window

### 10.2 Result
- dt controls “time-to-basin-hop” strongly:
  - dt=0.08 survived 4000 steps in the tested signature
  - dt=0.12 survived 1200 but failed by 4000 (metastability)
  - dt=0.16 failed within ~900–960 steps across damping 2–6

### 10.3 Key implication
- Damping modifies flavor/timing but is not a cure.
- Long-horizon behavior and slow drift variables (notably ψ, rho concentration, routing) became first-class concerns.

---

## 11) Afterstates, DreamState control, and the latch primitive (rd27, rd28)

This arc transitions from “measure failures” to “control basins and afterstates.”

### 11.1 Afterstate discovery (restwatch)
- Observed: flux decays rapidly, but **entropy can hover** (distribution shape persists while amplitude shrinks).
- Persistent attractors (rhoMaxId) often dominated by specific nodes (e.g., 82).

### 11.2 DreamSweep harnesses
- Standardized dream excitation + afterstate watch:
  - restore baseline every run
  - patterned injections (round-robin, strobe, burst)
  - 120s watch window
  - summary + trace outputs

### 11.3 ψ waveform/cadence results
- ψ polarity had modest routing effects.
- Waveform and cadence mattered; “best bands” depended on cadence.

### 11.4 End-phase latch / deterministic mode-select
- Key discovery: the afterstate basin at t0 is determined by **what was last injected at dream stop**.
- Parity was a proxy under fixed injector order; root variable is lastInjected.
- This becomes a controller primitive:
  - `selectMode(target)` can be implemented by ending dream on that injector.

### 11.5 Engineering implications
- Timing and browser scheduling matter; Firefox Dev Edition showed improved consistency.
- Harnesses moved toward drift-compensated scheduling and explicit timing telemetry.

---

## 12) Temporal packet → bus broadcast protocol (rd29, rd30, solResearchNote1/2)

This arc establishes a concrete readout/communication primitive: dual-rail bus broadcast.

### 12.1 Dual-bus rails
Defined rails:
- 114→89 and 114→79
- 136→89 and 136→79

Observed behavior:
- Rails become symmetric in successful regimes (mirrored legs).
- Distributed/simultaneous inputs are “compiled” into ordered time events.

### 12.2 Threshold ridge + metastability
- Found a sharp low-amplitude boundary where:
  - below: none
  - on ridge: metastable (sometimes bothOn, sometimes none)
  - above: deterministic bothOn

Quantified examples (from note sets):
- Failures concentrated in low corners; in ridge scans ampD=5.50 unstable, ampD≥5.75 stable (with ampB fixed).

### 12.3 Packet syntax matters
- Within-tick order and gapTicks can flip success/failure near threshold.
- Not commutative: D_then_B can succeed where B_then_D fails at gap=0.

### 12.4 Cross-coupler (“tertiary connection”)
- Port-to-port links 114↔136 stayed zero.
- Receiver-side crosslink **89→79** was consistently nonzero and correlated with rail peaks.
- Interpreted as receiver-rail “stitch” / coupler.

### 12.5 Handshaked protocol (engineering-grade)
- Developed a handshake protocol:
  - offset +1 (136 tick0, 114 tick1)
  - arbitration stage
  - post-arb nudge to stabilize dual-rail

Winning “engineering cell” (as documented):
- multB=1.144, nudgeMult=0.20 produced deterministic timing rails:
  - 136 onset tick 13
  - 114 onset tick 15
  - Δ=2 with zero variance in that regime

### 12.6 Environment robustness
- Robustness sweeps showed:
  - handshake concept stable across pressC ±20% and damp variations.
  - damping changed timing regime (Δ=2 → Δ=4 bands; slow-follow tails emerged at higher damp/press).

### 12.7 Next queued step
- Adaptive handshake (16y): detect arbiter tick, nudge on arbiter+1 to track regime changes up to damp 20.

---

## 13) Cross-cutting engineering rules established (lab invariants)

Across late phases, the corpus converges on “how to do SOL science without fooling ourselves”:

1. **Baseline restore per run** (eventually persistent via localStorage).
2. **UI-neutral harnesses** (no camera moves / selection side effects).
3. **Install to `globalThis`**; do not assume `window` or `App` bindings.
4. **Snapshot/restore or deterministic signature control** for repeatability.
5. Treat **dt** as a first-class axis; prefer dt-normalized metrics.
6. When revising harnesses: deliver **full ready-to-paste scripts**.
7. Prefer **BigData sweeps** (single-run grids) with progress logs.
8. Record comparability metadata in outputs (pressCUsed, dampUsed, dt, thresholds, capLaw hash, visibility state).

---

## 14) Primary “what we learned” statements (project-level)

1. **SOL exhibits discrete phase regimes** (not linear scaling) across damping and dt.
2. **Retention is governed by early pressure/outflux dynamics** on hubs; semanticMass behaves like capacitance.
3. **Capacitance law generalization is achievable**, with degree-power laws outperforming linear in robustness.
4. **Metastability is real**: a run can look stable for hundreds/thousands of steps then flip.
5. SOL afterstates are controllable: **mode select is deterministic via lastInjected at dream stop**.
6. SOL can be driven into **structured readout states**: dual-bus broadcast rails with a threshold ridge.
7. The emerging direction is a control-and-readout system:
   - controllers: latch mode select, ψ waveform/cadence, handshake protocol
   - readout: bus rails + timing rails

---

## 15) References (workspace pointers)

Primary archive corpus:
- `solArchive/MD/rd0.md` … `solArchive/MD/rd30.md`
- `solArchive/MD/solResearchNote1.md`
- `solArchive/MD/solResearchNote2.md`

Related ongoing chronological research logs:
- `solResearch/` (multiple `SOL_Dashboard_Chat_Report_YYYY-MM-DD_...` files)

---

## 16) Suggested next consolidation step (optional)

If you want this master record to become a “navigable index,” the next best improvement is to add a table mapping **(phase → dashboards/scripts/CSV packs)** so you can jump from a concept (e.g., “cap law alpha=0.8”) directly to the artifact names and dates. If you want, I can generate that index as a second file (or append it to this one).
